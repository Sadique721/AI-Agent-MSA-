"""
agent/workflow.py
==================
MSA AI Agent V5.0 — Full LangGraph Multi-Agent StateGraph.

Pipeline:
  intent_detection → memory_recall → kg_search → rag_search
       → tool_execution → llm_generation → reflection → [done]

Falls back gracefully at every node when optional services are unavailable.
Uses config/agents.yaml for per-node settings.
Uses prompts/*.md for all system prompts (via PromptLoader).
"""
from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any, Callable, Dict, List, Optional, TypedDict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger("msa.agent.workflow")

# ── Optional LangGraph ────────────────────────────────────────────────────────
try:
    from langgraph.graph import StateGraph, END  # type: ignore
    _LANGGRAPH_OK = True
except ImportError:
    _LANGGRAPH_OK = False
    END = "__end__"

    class StateGraph:  # type: ignore  # noqa: E302
        """Mock StateGraph when langgraph is not installed."""
        def __init__(self, schema): self._nodes: Dict = {}; self._entry = None
        def add_node(self, name, fn): self._nodes[name] = fn
        def add_edge(self, a, b): pass
        def add_conditional_edges(self, src, fn, mapping): pass
        def set_entry_point(self, n): self._entry = n
        def set_finish_point(self, n): pass
        def compile(self):
            nodes = self._nodes
            class _Compiled:
                def invoke(self, state):
                    current = dict(state)
                    for fn in nodes.values():
                        try:
                            current = fn(current) or current
                        except Exception as e:
                            logger.error("Node error: %s", e)
                    return current
            return _Compiled()


# ── Agent imports (graceful) ──────────────────────────────────────────────────
def _safe_import(import_fn):
    try:
        return import_fn()
    except Exception:
        return None


# ── State Schema ──────────────────────────────────────────────────────────────
class AgentState(TypedDict, total=False):
    # Input
    user_input: str
    persona: str
    reasoning_mode: str
    workspace_id: str

    # Detected intent
    intent: str
    intent_confidence: float
    intent_method: str

    # Memory
    history: List[Dict]
    memory_context: str

    # Knowledge graph
    kg_entities: List[Dict]
    kg_context: str

    # RAG
    rag_chunks: List[Dict]
    rag_context: str

    # Tool execution
    tool_results: List[Dict]
    tool_summary: str

    # LLM
    final_prompt: str
    llm_response: str
    llm_model: str

    # Reflection
    reflection_score: float
    reflection_issues: List[str]

    # Output
    response: str
    action: str
    parameters: Dict

    # Internal tracking
    status_callback: Optional[Callable]
    stream_callback: Optional[Callable]
    error: str
    timings: Dict


def _emit_status(state: AgentState, stage: str, message: str) -> None:
    cb = state.get("status_callback")
    if callable(cb):
        try:
            cb(stage, message)
        except Exception:
            pass


def _now_ms() -> float:
    return time.time() * 1000


# ── Node implementations ──────────────────────────────────────────────────────

def node_intent_detection(state: AgentState) -> AgentState:
    """Classify query intent using IntentAgent."""
    t0 = _now_ms()
    _emit_status(state, "thinking", "Detecting intent...")
    query = state.get("user_input", "")

    try:
        from agent.intent_agent import get_intent_agent
        agent = get_intent_agent()
        result = agent.classify(query)
        state["intent"] = result["intent"]
        state["intent_confidence"] = result["confidence"]
        state["intent_method"] = result["method"]
    except Exception as e:
        logger.warning("Intent detection failed: %s", e)
        state["intent"] = "GENERAL_QA"
        state["intent_confidence"] = 0.5
        state["intent_method"] = "fallback"

    state.setdefault("timings", {})["intent_ms"] = _now_ms() - t0
    logger.info("Intent: %s (%.0f%%)", state["intent"], state.get("intent_confidence", 0) * 100)
    return state


def node_memory_recall(state: AgentState) -> AgentState:
    """Retrieve relevant conversation history."""
    t0 = _now_ms()
    _emit_status(state, "thinking", "Recalling memory...")

    try:
        from backend.shared.prompt_loader import PromptLoader
        from memory.memory import Memory
        from backend.security import Security

        security = _safe_import(lambda: Security())
        memory = _safe_import(lambda: Memory(security=security))

        if memory:
            history = memory.get_recent_context(limit=10)
            state["history"] = history if isinstance(history, list) else []
            episodic = memory.get_episodic_summary()
        else:
            state["history"] = state.get("history", [])
            episodic = None

        # Format memory context using prompt template
        pl = PromptLoader.get()
        history_str = "\n".join(
            f"{h.get('role','?')}: {h.get('content','')[:200]}"
            for h in state.get("history", [])[-5:]
        )
        if episodic:
            history_str = f"[Episodic Summary] {episodic}\n\n" + history_str
        state["memory_context"] = history_str or "(no prior conversation)"
    except Exception as e:
        logger.debug("Memory recall error: %s", e)
        state["memory_context"] = "(memory unavailable)"
        state["history"] = []

    state.setdefault("timings", {})["memory_ms"] = _now_ms() - t0
    return state


def node_kg_search(state: AgentState) -> AgentState:
    """Query knowledge graph for related entities."""
    t0 = _now_ms()
    _emit_status(state, "searching", "Searching knowledge graph...")
    query = state.get("user_input", "")

    try:
        from agent.knowledge_graph_agent import get_kg_agent
        kg = get_kg_agent()
        entities = kg.search_entities(query, limit=10)
        state["kg_entities"] = entities
        state["kg_context"] = kg.format_context(entities, query)
    except Exception as e:
        logger.debug("KG search error: %s", e)
        state["kg_entities"] = []
        state["kg_context"] = ""

    state.setdefault("timings", {})["kg_ms"] = _now_ms() - t0
    return state


def node_rag_search(state: AgentState) -> AgentState:
    """Hybrid RAG retrieval: BM25 + dense vector search."""
    t0 = _now_ms()
    _emit_status(state, "searching", "Searching knowledge base...")
    query = state.get("user_input", "")

    try:
        from agent.rag_agent import get_rag_agent
        rag = get_rag_agent()
        chunks = rag.retrieve(query, top_k=5, min_score=0.0)
        state["rag_chunks"] = chunks
        state["rag_context"] = rag.format_context(chunks)
    except Exception as e:
        logger.debug("RAG search error: %s", e)
        state["rag_chunks"] = []
        state["rag_context"] = ""

    state.setdefault("timings", {})["rag_ms"] = _now_ms() - t0
    return state


def node_tool_execution(state: AgentState) -> AgentState:
    """Execute tools if the planner identified tool-requiring steps."""
    t0 = _now_ms()
    intent = state.get("intent", "GENERAL_QA")
    query = state.get("user_input", "").lower()

    # Only execute tools for system/code/search tasks
    tool_intents = {"SYSTEM_TASK", "CODING", "DEBUGGING"}
    if intent not in tool_intents:
        state["tool_results"] = []
        state["tool_summary"] = ""
        return state

    _emit_status(state, "running_tool", "Executing tools...")

    try:
        from agent.tool_agent import get_tool_agent
        tool_agent = get_tool_agent()

        tool_results = []
        # Auto-detect tool needs from query keywords
        if any(kw in query for kw in ["list files", "show files", "ls", "dir"]):
            result = tool_agent.execute_tool("filesystem_list", {"path": "."})
            tool_results.append(result.to_dict())
        elif any(kw in query for kw in ["git status", "git diff", "changes"]):
            result = tool_agent.execute_tool("git_status", {})
            tool_results.append(result.to_dict())
        elif any(kw in query for kw in ["search", "look up", "find online"]):
            result = tool_agent.execute_tool("web_search", {"query": state.get("user_input", "")})
            tool_results.append(result.to_dict())

        state["tool_results"] = tool_results
        if tool_results:
            summary_parts = []
            for r in tool_results:
                if r.get("success"):
                    summary_parts.append(f"[{r['tool']}]\n{r['output'][:500]}")
                else:
                    summary_parts.append(f"[{r['tool']}] Error: {r['error']}")
            state["tool_summary"] = "\n\n".join(summary_parts)
        else:
            state["tool_summary"] = ""
    except Exception as e:
        logger.debug("Tool execution error: %s", e)
        state["tool_results"] = []
        state["tool_summary"] = ""

    state.setdefault("timings", {})["tool_ms"] = _now_ms() - t0
    return state


def node_llm_generation(state: AgentState) -> AgentState:
    """Build the final prompt and call the LLM."""
    t0 = _now_ms()
    _emit_status(state, "generating", "Generating response...")

    # Build enriched prompt
    query = state.get("user_input", "")
    memory_ctx = state.get("memory_context", "")
    rag_ctx = state.get("rag_context", "")
    kg_ctx = state.get("kg_context", "")
    tool_summary = state.get("tool_summary", "")
    intent = state.get("intent", "GENERAL_QA")
    reasoning_mode = state.get("reasoning_mode", "balanced")
    persona = state.get("persona", "default")

    sections = [f"User: {query}"]
    if memory_ctx:
        sections.append(f"\n[Memory]\n{memory_ctx}")
    if rag_ctx:
        sections.append(f"\n[Knowledge Base]\n{rag_ctx}")
    if kg_ctx:
        sections.append(f"\n[Knowledge Graph]\n{kg_ctx}")
    if tool_summary:
        sections.append(f"\n[Tool Results]\n{tool_summary}")

    final_prompt = "\n".join(sections)
    state["final_prompt"] = final_prompt

    # Check Semantic Cache
    try:
        from backend.services.semantic_cache import SemanticCache
        cache = SemanticCache()
        cached_resp = cache.get(query)
        if cached_resp:
            state["llm_response"] = cached_resp
            state["llm_model"] = "semantic_cache"
            state.setdefault("timings", {})["llm_ms"] = _now_ms() - t0
            stream_cb = state.get("stream_callback")
            if stream_cb:
                import re
                chunks = re.split(r'(\s+)', cached_resp)
                for chunk in chunks:
                    if chunk:
                        stream_cb(chunk)
                        time.sleep(0.005)
            return state
    except Exception as e:
        logger.debug("Semantic cache lookup failed: %s", e)

    try:
        from agent.llm_agent import get_llm_agent
        llm = get_llm_agent()
        llm_resp = llm.generate(
            prompt=final_prompt,
            task_type=intent,
            reasoning_mode=reasoning_mode,
            stream_callback=state.get("stream_callback"),
            status_callback=state.get("status_callback"),
        )
        state["llm_response"] = llm_resp.text
        state["llm_model"] = llm_resp.model

        # Log request to AnalyticsEngine
        try:
            from backend.services.analytics_engine import AnalyticsEngine
            analytics = AnalyticsEngine()
            prompt_tokens = len(final_prompt) // 4
            resp_tokens = len(llm_resp.text) // 4
            latency = _now_ms() - t0
            analytics.log_request(llm_resp.model, prompt_tokens, resp_tokens, latency)
        except Exception as ae:
            logger.debug("Failed logging analytics metrics: %s", ae)

        # Save to semantic cache
        try:
            cache.set(query, llm_resp.text, model=llm_resp.model)
        except Exception as ce:
            logger.debug("Failed saving response to semantic cache: %s", ce)
    except Exception as e:
        logger.exception("LLM generation failed: %s", e)
        state["llm_response"] = f"I encountered an error generating a response: {e}"
        state["llm_model"] = "error"

    state.setdefault("timings", {})["llm_ms"] = _now_ms() - t0
    return state


def node_reflection(state: AgentState) -> AgentState:
    """Evaluate and optionally revise the LLM response."""
    t0 = _now_ms()
    reasoning_mode = state.get("reasoning_mode", "balanced")

    # Only reflect in deep/autonomous modes
    if reasoning_mode not in ("deep_thinking", "autonomous", "research"):
        state["reflection_score"] = 1.0
        state["reflection_issues"] = []
        state["response"] = state.get("llm_response", "")
        state["action"] = "langgraph_execution"
        state["parameters"] = {
            "intent": state.get("intent"),
            "model": state.get("llm_model"),
            "reflection_score": state.get("reflection_score"),
            "timings": state.get("timings", {}),
        }
        state.setdefault("timings", {})["reflection_ms"] = _now_ms() - t0
        return state

    _emit_status(state, "reflecting", "Reviewing response quality...")

    try:
        from agent.reflection_agent import get_reflection_agent
        agent = get_reflection_agent()
        query = state.get("user_input", "")
        draft = state.get("llm_response", "")
        rag_ctx = state.get("rag_context", "")
        final_response, result = agent.reflect_and_revise(query, draft, rag_ctx)
        state["reflection_score"] = result.overall_score
        state["reflection_issues"] = result.issues
        state["response"] = final_response
    except Exception as e:
        logger.debug("Reflection error: %s", e)
        state["reflection_score"] = 0.8
        state["reflection_issues"] = []
        state["response"] = state.get("llm_response", "")

    state["action"] = "langgraph_execution"
    state["parameters"] = {
        "intent": state.get("intent"),
        "model": state.get("llm_model"),
        "reflection_score": state.get("reflection_score"),
        "timings": state.get("timings", {}),
    }
    state.setdefault("timings", {})["reflection_ms"] = _now_ms() - t0
    return state


# ── Build StateGraph ──────────────────────────────────────────────────────────
def _build_workflow():
    graph = StateGraph(AgentState)

    graph.add_node("intent_detection", node_intent_detection)
    graph.add_node("memory_recall", node_memory_recall)
    graph.add_node("kg_search", node_kg_search)
    graph.add_node("rag_search", node_rag_search)
    graph.add_node("tool_execution", node_tool_execution)
    graph.add_node("llm_generation", node_llm_generation)
    graph.add_node("reflection", node_reflection)

    graph.set_entry_point("intent_detection")
    graph.add_edge("intent_detection", "memory_recall")
    graph.add_edge("memory_recall", "kg_search")
    graph.add_edge("kg_search", "rag_search")
    graph.add_edge("rag_search", "tool_execution")
    graph.add_edge("tool_execution", "llm_generation")
    graph.add_edge("llm_generation", "reflection")
    graph.add_edge("reflection", END)

    return graph.compile()


compiled_workflow = _build_workflow()


# ── Public entry point ────────────────────────────────────────────────────────
def run_agent_workflow(
    user_query: str,
    persona: str = "default",
    reasoning_mode: str = "balanced",
    workspace_id: str = "default",
    stream_callback: Optional[Callable[[str], None]] = None,
    status_callback: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, Any]:
    """
    Execute the full V5.0 agent pipeline.

    Returns:
        {
            "response": str,
            "action": str,
            "parameters": dict,
        }
    """
    initial_state: AgentState = {
        "user_input": user_query,
        "persona": persona,
        "reasoning_mode": reasoning_mode,
        "workspace_id": workspace_id,
        "stream_callback": stream_callback,
        "status_callback": status_callback,
        "history": [],
        "rag_chunks": [],
        "rag_context": "",
        "kg_entities": [],
        "kg_context": "",
        "tool_results": [],
        "tool_summary": "",
        "timings": {},
        "error": "",
        "response": "",
        "action": "langgraph_execution",
        "parameters": {},
    }

    try:
        result = compiled_workflow.invoke(initial_state)
        return {
            "response": result.get("response") or result.get("llm_response", ""),
            "action": result.get("action", "langgraph_execution"),
            "parameters": result.get("parameters", {}),
        }
    except Exception as e:
        logger.exception("Workflow execution failed: %s", e)
        return {
            "response": f"An error occurred in the agent pipeline: {e}",
            "action": "error",
            "parameters": {"error": str(e)},
        }
