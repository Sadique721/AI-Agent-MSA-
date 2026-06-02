"""
agent/AgentService.py
=====================
Core orchestration layer for the MSA Agent.

Pipeline:
  user input → DecisionEngine (LLM / keyword fallback)
             → AgentExecutor (system/mobile/web action)
             → AgentMemory (persist turn)
             → structured response dict

This is the single entry point all server routes and the wake-word
loop should call. It owns one AgentMemory and one AgentExecutor.
"""
import logging
import os
from typing import Dict, Any

from agent.AgentMemory import AgentMemory
from agent.AgentExecutor import AgentExecutor

logger = logging.getLogger("msa.agent.service")

# Try to load llama-cpp-python (optional — only if DeepSeek model exists)
_LLM = None
_LLM_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "llm", "deepseek.gguf")

def _load_llm():
    global _LLM
    if os.path.exists(_LLM_PATH):
        try:
            from llama_cpp import Llama
            _LLM = Llama(model_path=_LLM_PATH, n_ctx=2048, verbose=False)
            logger.info("DeepSeek LLM loaded from %s", _LLM_PATH)
        except ImportError:
            logger.info("llama-cpp-python not installed. LLM fallback disabled.")
        except Exception as e:
            logger.warning("LLM load error: %s", e)
    else:
        logger.info("No LLM model found at %s. Keyword fallback only.", _LLM_PATH)

_load_llm()  # Load at import time (non-blocking if model missing)


class AgentService:
    """
    Stateful orchestrator — one instance should be shared across all requests
    (held by AgentController / server.py singletons).
    """

    def __init__(self, decision_engine, memory):
        """
        Args:
            decision_engine: backend.decision_engine.DecisionEngine instance
            memory:          memory.memory.Memory instance
        """
        self.engine   = decision_engine
        self.memory   = AgentMemory(memory)
        self.executor = AgentExecutor()
        logger.info("AgentService ready.")

    def _ask_llm(self, prompt: str) -> str:
        """Use DeepSeek LLM for unknown/complex queries (if model loaded)."""
        if _LLM:
            try:
                result = _LLM(prompt, max_tokens=200, stop=["\n\n"])
                text = result["choices"][0]["text"].strip()
                return text if text else "I'm not sure how to answer that."
            except Exception as e:
                logger.error("LLM inference error: %s", e)
        return "I understand your message but I need more context. Try: 'open notepad', 'search python', or 'my profile'."

    # ── Main pipeline ──────────────────────────────────────────────────────────
    def process_input(self, user_input: str) -> Dict[str, Any]:
        """
        Full pipeline: text → decision → (optional action) → persisted → response.

        Returns a dict with keys:
            response         str   — reply to show / speak
            action           str   — action that was taken
            parameters       dict  — action parameters
            execution_result str   — result of the executed action (if any)
            status           str   — "success" | "error"
        """
        if not user_input or not user_input.strip():
            return {
                "response":         "Please say or type a command.",
                "action":           "none",
                "parameters":       {},
                "execution_result": "",
                "status":           "success",
            }

        # 1. Get recent context
        context = self.memory.get_context(limit=5)

        # 2. Decision engine (LLM or keyword fallback)
        try:
            decision = self.engine.process_command(user_input, context)
        except Exception as e:
            logger.error("DecisionEngine error: %s", e)
            decision = {
                "response":   f"I encountered an error processing your request: {e}",
                "action":     "none",
                "parameters": {},
            }

        action     = decision.get("action", "none")
        params     = decision.get("parameters", {})
        response   = decision.get("response", "")
        exec_result= ""

        # 3. Execute action (if any)
        if action and action != "none":
            exec_result = self.executor.execute(action, params)
            logger.info("Executed action=%s result=%r", action, exec_result[:80])

        # 4. Persist to memory
        self.memory.add_turn(user_input, response, action)

        return {
            "response":         response,
            "action":           action,
            "parameters":       params,
            "execution_result": exec_result,
            "status":           "success",
        }

    # ── Convenience ────────────────────────────────────────────────────────
    def get_history(self, limit: int = 10):
        """Return recent conversation history."""
        return self.memory.get_context(limit=limit)

    def get_memory_stats(self) -> Dict:
        """Return memory stats for the dashboard."""
        return self.memory.get_stats()
