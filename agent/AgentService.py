"""
agent/AgentService.py
=====================
Phase-2: Reasoning-Based Autonomous Agent orchestration layer.

Upgraded pipeline:
  1. Detect & normalize language (Hinglish Engine)
  2. Augment context via RAG semantic memory
  3. ReasoningEngine — goal/risk/tool analysis          [PHASE-2 NEW]
  4. Security approval check for high-risk actions      [PHASE-2 NEW]
  5. PlannerAgent — multi-step plan generation
  6. Validator + Auto-Replan loop (max 3 retries)       [PHASE-2 NEW]
  7. Execute via Tool Registry
  8. Store turn in long-term memory
  9. Return structured response dict
"""

import logging
import os
from typing import Dict, Any, List, Optional, Callable

from ai_core.llm_manager import LLMManager
from agent.AgentMemory import AgentMemory
from agent.AgentExecutor import AgentExecutor
from config import (
    ENABLE_HINGLISH_ENGINE,
    ENABLE_PLANNER,
    ENABLE_RAG_MEMORY,
    ENABLE_BROWSER_AGENT,
    ENABLE_REASONING_ENGINE,
    ENABLE_VALIDATOR,
    ENABLE_AUTO_REPLAN,
    MAX_REPLAN_RETRIES,
    ENABLE_CODING_AGENT,
)

logger = logging.getLogger("msa.agent.service")

# ── Optional DeepSeek / Llama LLM ────────────────────────────────────────────
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


_load_llm()


class AgentService:
    """
    Stateful Phase-2 orchestrator — one instance shared across all requests.
    Manages language, memory, reasoning, planning, validation, and execution.
    """

    def __init__(self, decision_engine, memory):
        self.engine   = decision_engine
        self.memory   = AgentMemory(memory)
        self.executor = AgentExecutor()
        self.llm_manager = LLMManager()

        # ── Phase-1 subsystems ──
        self.language_manager = None
        if ENABLE_HINGLISH_ENGINE:
            try:
                from language.language_manager import LanguageManager
                self.language_manager = LanguageManager()
            except Exception as e:
                logger.warning("LanguageManager init failed: %s", e)

        self.rag_memory = None
        if ENABLE_RAG_MEMORY:
            try:
                from memory.rag_memory import RAGMemory
                self.rag_memory = RAGMemory(sqlite_memory=memory)
            except Exception as e:
                logger.warning("RAGMemory init failed: %s", e)

        self.planner = None
        if ENABLE_PLANNER:
            try:
                from agent.Planner import PlannerAgent
                self.planner = PlannerAgent(language_manager=self.language_manager)
            except Exception as e:
                logger.warning("PlannerAgent init failed: %s", e)

        # ── Phase-2 subsystems ──
        self.reasoning_engine = None
        if ENABLE_REASONING_ENGINE:
            try:
                from agent.ReasoningEngine import ReasoningEngine
                self.reasoning_engine = ReasoningEngine()
            except Exception as e:
                logger.warning("ReasoningEngine init failed: %s", e)

        self.validator = None
        if ENABLE_VALIDATOR:
            try:
                from agent.Validator import Validator
                self.validator = Validator()
            except Exception as e:
                logger.warning("Validator init failed: %s", e)

        # ── Phase-3 coding subsystems ──
        self.code_generator = None
        self.bug_analyzer = None
        self.stacktrace_analyzer = None
        self.project_generator = None
        self.refactor_engine = None
        self.test_generator = None
        self.code_explainer = None
        self.code_reviewer = None

        if ENABLE_CODING_AGENT:
            try:
                from coding.CodeGenerator import CodeGenerator
                from coding.BugAnalyzer import BugAnalyzer
                from coding.StackTraceAnalyzer import StackTraceAnalyzer
                from coding.ProjectGenerator import ProjectGenerator
                from coding.RefactorEngine import RefactorEngine
                from coding.TestGenerator import TestGenerator
                from coding.CodeExplainer import CodeExplainer
                from coding.CodeReviewer import CodeReviewer

                self.code_generator = CodeGenerator(_LLM)
                self.bug_analyzer = BugAnalyzer(_LLM)
                self.stacktrace_analyzer = StackTraceAnalyzer(_LLM)
                self.project_generator = ProjectGenerator(_LLM)
                self.refactor_engine = RefactorEngine(_LLM)
                self.test_generator = TestGenerator(_LLM)
                self.code_explainer = CodeExplainer(_LLM)
                self.code_reviewer = CodeReviewer(_LLM)
                logger.info("Coding Agent subsystems initialised successfully.")
            except Exception as e:
                logger.warning("Coding Agent init failed: %s", e)

        # ── Bind tool handlers ──
        self._bind_tool_handlers()
        logger.info("AgentService Phase-2 ready.")

    # ── Tool handler binding ──────────────────────────────────────────────────

    def _bind_tool_handlers(self) -> None:
        """Connect registry tools to actual executable handlers."""
        from tools.tool_registry import registry

        # 1. System/Desktop Tools
        registry.set_handler("open_app", self.executor._open_app)

        def system_control_handler(params: Dict) -> str:
            action = params.get("action", "").lower()
            if action == "restart":
                return self.executor._restart(params)
            return self.executor._shutdown(params)

        registry.set_handler("system_control", system_control_handler)
        registry.set_handler("get_time",    self.executor._get_time)
        registry.set_handler("get_profile", self.executor._get_profile)
        registry.set_handler("automation",  self.executor._automation)

        # 2. Browser Tools
        if ENABLE_BROWSER_AGENT:
            try:
                from browser_agent.playwright_agent import PlaywrightAgent
                from browser_agent.browser_skills import search_google, search_jobs
                browser_agent = PlaywrightAgent()

                registry.set_handler("browser_navigate", lambda p: browser_agent.navigate(p.get("url")))
                registry.set_handler("browser_search",   search_google)
                registry.set_handler("browser_linkedin", search_jobs)
                registry.set_handler(
                    "browser_extract",
                    lambda p: browser_agent.extract_text(p.get("selector", "body")),
                )
            except Exception as e:
                logger.error("Failed to bind browser tools: %s", e)

        # 3. Internet search
        registry.set_handler("internet_search", self.executor._web_search)

        # 4. Memory Tools
        if ENABLE_RAG_MEMORY and self.rag_memory:
            registry.set_handler(
                "memory_remember",
                lambda p: str(self.rag_memory.remember(
                    p.get("text") or p.get("content") or "", p.get("category", "fact")
                )),
            )
            registry.set_handler(
                "memory_search",
                lambda p: str(self.rag_memory.recall(p.get("query", ""), int(p.get("top_k", 5)))),
            )

        # 5. Mobile Tools
        registry.set_handler("mobile_control", self.executor._mobile_open_app)
        registry.set_handler("mobile_call",    self.executor._mobile_call)
        registry.set_handler("mobile_alarm",   self.executor._mobile_alarm)

        # 6. Vision Tools
        registry.set_handler("vision_capture", self.executor._vision_capture)
        registry.set_handler("vision_detect",  lambda p: self.executor._vision_capture(p))

        # 7. Phase-2 Reasoning Tools
        registry.set_handler("reason_task",   self._handle_reason_task)
        registry.set_handler("validate_task", self._handle_validate_task)
        registry.set_handler("replan_task",   self._handle_replan_task)

        # 8. Phase-3 Coding Tools
        if ENABLE_CODING_AGENT:
            registry.set_handler("generate_code",      self._handle_generate_code)
            registry.set_handler("debug_code",         self._handle_debug_code)
            registry.set_handler("analyze_stacktrace", self._handle_analyze_stacktrace)
            registry.set_handler("generate_project",   self._handle_generate_project)
            registry.set_handler("refactor_code",      self._handle_refactor_code)
            registry.set_handler("generate_tests",     self._handle_generate_tests)
            registry.set_handler("explain_code",       self._handle_explain_code)
            registry.set_handler("review_code",        self._handle_review_code)

    # ── Phase-2 reasoning tool handlers ──────────────────────────────────────

    def _handle_reason_task(self, params: Dict) -> str:
        """Tool handler: run reasoning engine on a task description."""
        task = params.get("task", params.get("query", ""))
        if not task or not self.reasoning_engine:
            return "Reasoning engine not available."
        result = self.reasoning_engine.reason(task)
        import json
        return json.dumps(result, indent=2)

    def _handle_validate_task(self, params: Dict) -> str:
        """Tool handler: validate a list of step results."""
        results = params.get("results", [])
        if not self.validator:
            return "Validator not available."
        validation = self.validator.validate_result(results)
        import json
        return json.dumps(validation, indent=2)

    def _handle_replan_task(self, params: Dict) -> str:
        """Tool handler: trigger replan for a failed task."""
        task   = params.get("task", "")
        reason = params.get("reason", "previous attempt failed")
        if not task:
            return "No task provided for replan."
        return f"Replan requested for: '{task}'. Reason: {reason}"

    # ── Phase-3 coding tool handlers ─────────────────────────────────────────

    def _handle_generate_code(self, params: Dict) -> str:
        if not self.code_generator: return "Code generator not available."
        prompt = params.get("prompt", params.get("task", ""))
        lang = params.get("language")
        res = self.code_generator.generate(prompt, lang)
        import json
        if self.rag_memory:
            self.rag_memory.remember(f"Generated {res.get('language')} code: {res.get('explanation')}", "coding_project")
        return json.dumps(res, indent=2)

    def _handle_debug_code(self, params: Dict) -> str:
        if not self.bug_analyzer: return "Bug analyzer not available."
        logs = params.get("logs", params.get("error", ""))
        res = self.bug_analyzer.analyze(logs)
        import json
        if self.rag_memory:
            self.rag_memory.remember(f"Bug analysis: {res.get('root_cause')} -> Fix: {res.get('fix')}", "coding_bug")
        return json.dumps(res, indent=2)

    def _handle_analyze_stacktrace(self, params: Dict) -> str:
        if not self.stacktrace_analyzer: return "Stack trace analyzer not available."
        trace = params.get("trace", params.get("stacktrace", ""))
        res = self.stacktrace_analyzer.analyze(trace)
        import json
        if self.rag_memory:
            self.rag_memory.remember(f"Stack trace check: {res.get('file')}:{res.get('line')} -> Issue: {res.get('issue')}", "coding_bug")
        return json.dumps(res, indent=2)

    def _handle_generate_project(self, params: Dict) -> str:
        if not self.project_generator: return "Project generator not available."
        p_type = params.get("project_type", params.get("type", "springboot"))
        name = params.get("name", "my-app")
        desc = params.get("description", "")
        res = self.project_generator.generate(p_type, name, desc)
        import json
        if self.rag_memory:
            self.rag_memory.remember(f"Generated project {name} ({p_type}): {desc}", "coding_project")
        return json.dumps(res, indent=2)

    def _handle_refactor_code(self, params: Dict) -> str:
        if not self.refactor_engine: return "Refactor engine not available."
        code = params.get("code", "")
        res = self.refactor_engine.refactor(code)
        import json
        if self.rag_memory:
            self.rag_memory.remember(f"Refactored code. Improvements: {', '.join(res.get('improvements', []))}", "coding_reference")
        return json.dumps(res, indent=2)

    def _handle_generate_tests(self, params: Dict) -> str:
        if not self.test_generator: return "Test generator not available."
        code = params.get("code", "")
        fw = params.get("framework", "")
        res = self.test_generator.generate(code, fw)
        import json
        if self.rag_memory:
            self.rag_memory.remember(f"Generated {res.get('framework')} tests", "coding_reference")
        return json.dumps(res, indent=2)

    def _handle_explain_code(self, params: Dict) -> str:
        if not self.code_explainer: return "Code explainer not available."
        code = params.get("code", "")
        res = self.code_explainer.explain(code)
        import json
        if self.rag_memory:
            self.rag_memory.remember(f"Explained code: {res.get('summary')}", "coding_reference")
        return json.dumps(res, indent=2)

    def _handle_review_code(self, params: Dict) -> str:
        if not self.code_reviewer: return "Code reviewer not available."
        code = params.get("code", "")
        res = self.code_reviewer.review(code)
        import json
        if self.rag_memory:
            self.rag_memory.remember(f"Reviewed code. Grade: {res.get('grade')} | Comments: {', '.join(res.get('comments', []))}", "coding_review")
        return json.dumps(res, indent=2)

    # ── LLM fallback ─────────────────────────────────────────────────────────

    def _ask_llm(self, prompt: str) -> str:
        if _LLM:
            try:
                result = _LLM(prompt, max_tokens=200, stop=["\n\n"])
                text = result["choices"][0]["text"].strip()
                return text if text else "I'm not sure how to answer that."
            except Exception as e:
                logger.error("LLM inference error: %s", e)
        return "I understand your message but I need more context. Try: 'open notepad', 'search python', or 'my profile'."

    # ── Main pipeline ─────────────────────────────────────────────────────────

    def process_input(
        self,
        user_input: str,
        stream_callback: Optional[Callable[[str], None]] = None,
        status_callback: Optional[Callable[[str, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Phase-2 upgraded pipeline:
          1. Language detection & Hinglish normalization
          2. RAG Memory context augmentation
          3. ReasoningEngine — goal/risk/tool analysis
          4. Security: approval check for high-risk actions
          5. PlannerAgent — generate steps using reasoning context
          6. Auto-Replan loop (max MAX_REPLAN_RETRIES)
          7. Execute via Tool Registry
          8. Store turn in long-term memory
          9. Return structured response
        """
        if not user_input or not user_input.strip():
            return {
                "response":         "Please say or type a command.",
                "action":           "none",
                "parameters":       {},
                "execution_result": "",
                "status":           "success",
                "reasoning":        None,
                "validation":       None,
            }

        # ── Step 1: Language detection & Hinglish normalization ──────────────
        if status_callback:
            status_callback("thinking", "Analyzing language and intent...")
        language = "english"
        lang_res = {}
        if ENABLE_HINGLISH_ENGINE and self.language_manager:
            try:
                lang_res = self.language_manager.process(user_input)
                language = lang_res.get("language", "english")
            except Exception as e:
                logger.error("LanguageEngine error: %s", e)

        # ── Step 2: RAG Memory context augmentation ──────────────────────────
        if status_callback:
            status_callback("searching", "Searching vector database & memory...")
        context = self.memory.get_context(limit=5)
        rag_ctx = {}
        if ENABLE_RAG_MEMORY and self.rag_memory:
            try:
                rag_ctx = self.rag_memory.get_augmented_context(user_input)
                for item in rag_ctx.get("semantic", []):
                    context.insert(0, f"Memory: {item['text']} (category: {item.get('category')})")
            except Exception as e:
                logger.error("RAGMemory recall error: %s", e)

        # ── Step 3: ReasoningEngine analysis ────────────────────────────────
        if status_callback:
            status_callback("thinking", "Analyzing intent & cognitive graphs...")
        reasoning = None
        if ENABLE_REASONING_ENGINE and self.reasoning_engine:
            try:
                reasoning = self.reasoning_engine.reason(user_input, context)
                logger.info(
                    "Reasoning: goal='%s' type=%s risk=%s",
                    reasoning.get("goal", ""),
                    reasoning.get("reasoning_type", ""),
                    reasoning.get("risk_level", ""),
                )
            except Exception as e:
                logger.error("ReasoningEngine error: %s", e)

        # ── Step 4: Security — approval check for high-risk actions ──────────
        if reasoning and reasoning.get("requires_approval"):
            logger.warning("High-risk action detected — requires approval: %s", reasoning.get("goal"))
            approval_msg = self._build_approval_message(reasoning, language)
            return {
                "response":          approval_msg,
                "action":            "approval_required",
                "parameters":        {"goal": reasoning.get("goal"), "risk_level": reasoning.get("risk_level")},
                "execution_result":  "",
                "status":            "pending_approval",
                "reasoning":         reasoning,
                "validation":        None,
            }

        # ── Steps 5–7: Plan → Validate → Auto-Replan loop ───────────────────
        from tools.tool_registry import registry

        action      = "none"
        params      = {}
        response    = ""
        exec_result = ""
        validation  = None
        steps       = []

        if ENABLE_PLANNER and self.planner:
            if status_callback:
                status_callback("planning", "Generating execution blueprint...")
            try:
                steps = self.planner.plan(user_input, context)
            except Exception as e:
                logger.error("PlannerAgent error: %s", e)

        if len(steps) > 1:
            # ── Multi-step: plan → execute → validate → auto-replan ──────────
            attempt    = 0
            max_tries  = MAX_REPLAN_RETRIES if ENABLE_AUTO_REPLAN else 1
            results    = []
            current_reasoning = reasoning

            while attempt < max_tries:
                attempt += 1
                logger.info("Execution attempt %d/%d — %d steps", attempt, max_tries, len(steps))
                results = []

                for step in steps:
                    t_name   = step["tool"]
                    t_params = step["params"]
                    logger.info("  Step %d: tool=%s params=%s", step["step"], t_name, t_params)
                    if status_callback:
                        status_callback("running_tool", f"Running {t_name}...")
                    res = registry.execute(t_name, t_params)
                    results.append({
                        "step":   step["step"],
                        "tool":   t_name,
                        "action": step.get("action", ""),
                        "params": t_params,
                        "result": res,
                    })

                # Validate results
                if ENABLE_VALIDATOR and self.validator and current_reasoning:
                    try:
                        validation = self.validator.validate_result(results, current_reasoning)
                        logger.info(
                            "Validation: valid=%s score=%.2f attempt=%d",
                            validation["valid"], validation["score"], attempt,
                        )

                        if validation["valid"]:
                            break  # Success — exit replan loop

                        if attempt < max_tries and ENABLE_AUTO_REPLAN:
                            logger.info("Auto-replan triggered (attempt %d)…", attempt)
                            # Adjust reasoning for retry
                            if self.reasoning_engine:
                                current_reasoning = self.reasoning_engine.reason(
                                    user_input, context, failure_hint=validation, replan_attempt=attempt
                                )
                            # Regenerate plan with updated reasoning
                            try:
                                steps = self.planner.plan(user_input, context)
                            except Exception as e:
                                logger.error("Replan failed: %s", e)
                                break
                    except Exception as e:
                        logger.error("Validator error: %s", e)
                        break
                else:
                    break  # No validator configured — single pass

            exec_result = "\n".join(
                f"Step {r['step']} ({r['tool']}): {r['result']}" for r in results
            )
            action = "multi_step_plan"
            params = {"steps": steps}

            # Final output validation
            final_validation = None
            if ENABLE_VALIDATOR and self.validator and reasoning:
                try:
                    retrieved_chunks = []
                    if ENABLE_RAG_MEMORY and self.rag_memory:
                        try:
                            self.rag_memory._ensure_init()
                            retrieved_chunks = self.rag_memory.retriever.retrieve(user_input, top_k=5)
                        except Exception as ex:
                            logger.warning("AgentService: failed to fetch RAG chunks for validation (%s)", ex)

                    final_validation = self.validator.validate_final_output(
                        results, reasoning.get("goal", user_input), retrieved_chunks
                    )
                    logger.info(
                        "Final validation: grade=%s score=%.2f",
                        final_validation.get("grade"),
                        final_validation.get("score", 0),
                    )
                except Exception as e:
                    logger.error("Final validation error: %s", e)

            # Build response
            if language == "hinglish":
                response = (
                    f"Maine aapka multi-step plan complete kar diya hai:\n"
                    + "\n".join(f"- Step {s['step']}: {s['tool']}" for s in steps)
                )
            else:
                response = (
                    f"I have successfully completed the multi-step plan:\n"
                    + "\n".join(f"- Step {s['step']}: {s['tool']}" for s in steps)
                )
            if final_validation:
                response += f"\n\n✓ Result: {final_validation.get('feedback', '')}"
                if validation and not validation.get("valid"):
                    response += f"\n⚠ Some steps needed retry ({validation.get('passed', 0)}/{validation.get('total', 0)} succeeded)."

        else:
            # ── Single-action fallback ────────────────────────────────────────
            try:
                decision = self.engine.process_command(user_input, context)
            except Exception as e:
                logger.error("DecisionEngine error: %s", e)
                decision = {
                    "response":   f"Error processing: {e}",
                    "action":     "none",
                    "parameters": {},
                }

            action   = decision.get("action", "none")
            params   = decision.get("parameters", {})
            response = decision.get("response", "")
            exec_result = ""

            tool_name = registry.suggest_tool(action)
            if tool_name:
                if status_callback:
                    status_callback("running_tool", f"Running {tool_name}...")
                exec_result = registry.execute(tool_name, params)
                # Single-step validation
                if ENABLE_VALIDATOR and self.validator and reasoning:
                    try:
                        step_info = {"step": 1, "tool": tool_name, "action": action, "params": params}
                        step_val  = self.validator.validate_step(step_info, exec_result, reasoning)
                        validation = step_val
                        if not step_val["valid"]:
                            logger.info("Single-step validation failed: %s", step_val["reason"])
                    except Exception as e:
                        logger.error("Single-step validation error: %s", e)
            elif action and action != "none":
                exec_result = self.executor.execute(action, params)

            # RAG / Search / Conversation generation enhancement
            # If search or retrieval tool was executed, pass its output directly to LLM to formulate response
            lang_instruction = ""
            if language == "hinglish":
                lang_instruction = "Respond in Hinglish (mix of Hindi and English using Roman script)."
            elif language == "hindi":
                lang_instruction = "Respond in Hindi using Roman script."
            else:
                lang_instruction = "Respond in clear English."

            if action in ("internet_search", "browser_search", "memory_recall") and exec_result:
                if status_callback:
                    status_callback("generating", "Synthesizing retrieved context...")
                prompt = (
                    f"You are MSA, an advanced AI Assistant. {lang_instruction}\n"
                    f"Answer the user query using the retrieved context below. Be direct, clear, and verified.\n\n"
                    f"User Query: {user_input}\n"
                    f"Retrieved Content:\n{exec_result}\n\n"
                    f"Answer:"
                )
                response = self.llm_manager.generate(prompt, stream_callback=stream_callback)
            elif action == "none":
                # General conversational request — combine user profile, context, and query
                profile_context = ""
                if hasattr(self.memory, "memory_agent") and self.memory.memory_agent:
                    profile_context = str(self.memory.memory_agent.working_memory.get("owner_profile", {}))
                
                # Fetch RAG semantic context to answer general questions (e.g. explain this PDF, what is java)
                retrieved_rag = []
                if ENABLE_RAG_MEMORY and self.rag_memory:
                    try:
                        ret_data = self.rag_memory.get_augmented_context(user_input)
                        retrieved_rag = [x["text"] for x in ret_data.get("semantic", [])]
                    except Exception:
                        pass

                history_str = ""
                if isinstance(context, list):
                    for turn in context:
                        if isinstance(turn, dict):
                            history_str += f"{turn.get('role', 'user').capitalize()}: {turn.get('content', '')}\n"
                        else:
                            history_str += f"{turn}\n"
                else:
                    history_str = str(context)

                if status_callback:
                    status_callback("generating", "Generating reply...")
                prompt = (
                    f"You are MSA, an advanced AI Assistant. {lang_instruction}\n"
                    f"User Profile: {profile_context}\n"
                    f"Retrieved Knowledge:\n" + "\n".join(f"- {x}" for x in retrieved_rag) + "\n\n"
                    f"Conversation History:\n{history_str}\n"
                    f"User Query: {user_input}\n\n"
                    f"Response:"
                )
                response = self.llm_manager.generate(prompt, stream_callback=stream_callback)
            
            # If no response generated yet, fallback to template
            if not response:
                if lang_res and lang_res.get("response"):
                    response = lang_res.get("response")
                else:
                    response = f"Processed request: {action}."

            # Final validation check on dynamic single action response
            if ENABLE_VALIDATOR and self.validator and reasoning:
                try:
                    ret_chunks = [{"content": exec_result}] if exec_result else []
                    val_res = self.validator.validate_final_output(
                        [{"step": 1, "tool": tool_name or "conversation", "result": response}],
                        reasoning.get("goal", user_input),
                        ret_chunks
                    )
                    validation = val_res
                except Exception as ve:
                    logger.warning("AgentService single action validation failed: %s", ve)

        # ── Step 8: Store turn in long-term memory ───────────────────────────
        # Inject Creator Profile Card if talking about Md Sadique Amin
        keywords = ["md sadique amin", "sadique", "creator of msa", "who built msa", "who developed msa", "owner of msa", "tell me about myself"]
        query_lower = user_input.lower()
        if any(k in query_lower for k in keywords):
            if "media://" not in response:
                profile_card = """
<div style="background: linear-gradient(135deg, rgba(30, 30, 50, 0.95), rgba(15, 15, 30, 0.95)); border: 1px solid rgba(139, 92, 246, 0.45); border-radius: 16px; padding: 24px; box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5); backdrop-filter: blur(12px); color: #f1f5f9; font-family: 'Segoe UI', -apple-system, sans-serif; max-width: 620px; margin: 20px auto; border-top: 4px solid #8b5cf6;">
  <div style="display: flex; align-items: center; gap: 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.12); padding-bottom: 20px; margin-bottom: 20px;">
    <div style="position: relative;">
      <img src="media://d:/My Self Details/Programs/AI/msa_agent/data/memory/user_picture.jpg" style="width: 110px; height: 110px; border-radius: 50%; border: 3px solid #8b5cf6; box-shadow: 0 0 20px rgba(139, 92, 246, 0.7); object-fit: cover;" />
      <span style="position: absolute; bottom: 8px; right: 8px; background: #10b981; width: 16px; height: 16px; border-radius: 50%; border: 3.5px solid #1e1e32;" title="Founder & CEO"></span>
    </div>
    <div>
      <h2 style="margin: 0; font-size: 26px; font-weight: 800; background: linear-gradient(to right, #a78bfa, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Md Sadique Amin</h2>
      <p style="margin: 6px 0 0 0; color: #a78bfa; font-size: 13.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px;">Founder, CEO, CTO & CMO</p>
      <p style="margin: 4px 0 0 0; color: #94a3b8; font-size: 14px; font-weight: 550;">Full Stack Developer | AI Swarm Engineer | Data Scientist</p>
    </div>
  </div>

  <div style="margin-bottom: 20px;">
    <h3 style="margin: 0 0 10px 0; font-size: 16px; color: #f8fafc; border-left: 3px solid #f472b6; padding-left: 10px;">Executive Biography</h3>
    <p style="margin: 0; font-size: 14px; line-height: 1.6; color: #cbd5e1;">
      <strong>Md Sadique Amin</strong> is a visionary Software Developer, AI Swarm Architect, and Data Scientist based in Begusarai, Bihar. Currently pursuing a BE in Computer Science and Engineering at GEC Patan (7.9 CGPA), he specializes in building scalable enterprise cloud infrastructure, advanced multi-agent cognitive systems, Spring Boot microservices, and hybrid RAG data pipelines. He is the principal architect of the MSA AI Agent OS client.
    </p>
  </div>

  <div style="margin-bottom: 20px;">
    <h3 style="margin: 0 0 12px 0; font-size: 16px; color: #f8fafc; border-left: 3px solid #8b5cf6; padding-left: 10px;">Key Technical Armament</h3>
    <div style="display: flex; flex-wrap: wrap; gap: 8px;">
      <span style="background: rgba(139, 92, 246, 0.18); border: 1px solid rgba(139, 92, 246, 0.35); color: #d8b4fe; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;">Java / Spring Boot / Spring Cloud</span>
      <span style="background: rgba(139, 92, 246, 0.18); border: 1px solid rgba(139, 92, 246, 0.35); color: #d8b4fe; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;">Python / PyTorch / TensorFlow</span>
      <span style="background: rgba(139, 92, 246, 0.18); border: 1px solid rgba(139, 92, 246, 0.35); color: #d8b4fe; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;">FastAPI / Django / Flask</span>
      <span style="background: rgba(139, 92, 246, 0.18); border: 1px solid rgba(139, 92, 246, 0.35); color: #d8b4fe; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;">React.js / Next.js / Electron</span>
      <span style="background: rgba(139, 92, 246, 0.18); border: 1px solid rgba(139, 92, 246, 0.35); color: #d8b4fe; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;">Swarm Intelligence & Hybrid RAG</span>
      <span style="background: rgba(139, 92, 246, 0.18); border: 1px solid rgba(139, 92, 246, 0.35); color: #d8b4fe; padding: 5px 12px; border-radius: 20px; font-size: 12px; font-weight: 600;">Docker / AWS / Spark / Kafka</span>
    </div>
  </div>

  <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255, 255, 255, 0.12); padding-top: 18px; font-size: 12.5px; color: #94a3b8;">
    <span>📍 Begusarai, Bihar, India</span>
    <div style="display: flex; gap: 16px;">
      <a href="https://myportfoliositesadique.netlify.app/" target="_blank" style="color: #c084fc; text-decoration: none; font-weight: 700; border-bottom: 1px dashed rgba(192, 132, 252, 0.5);">🌐 Portfolio</a>
      <a href="https://github.com/Sadique721" target="_blank" style="color: #c084fc; text-decoration: none; font-weight: 700; border-bottom: 1px dashed rgba(192, 132, 252, 0.5);">🐙 GitHub</a>
    </div>
  </div>
</div>
"""
                response = response + "\n\n" + profile_card

        self.memory.add_turn(user_input, response, action)
        if ENABLE_RAG_MEMORY and self.rag_memory:
            try:
                self.rag_memory.remember_conversation(user_input, response)
                # Also store reasoning goal in memory
                if reasoning and reasoning.get("goal"):
                    self.rag_memory.remember(reasoning["goal"], category="goal")
            except Exception as e:
                logger.error("RAGMemory store error: %s", e)

        return {
            "response":         response,
            "action":           action,
            "parameters":       params,
            "execution_result": exec_result,
            "status":           "success",
            "reasoning":        reasoning,
            "validation":       validation,
        }

    # ── Approval message builder ──────────────────────────────────────────────

    def _build_approval_message(self, reasoning: Dict, language: str) -> str:
        goal      = reasoning.get("goal", "this action")
        risk      = reasoning.get("risk_level", "high")
        req_tools = reasoning.get("required_tools", [])
        if language == "hinglish":
            return (
                f"⚠️ Yeh action high-risk hai!\n"
                f"Goal: {goal}\n"
                f"Risk: {risk.upper()}\n"
                f"Tools needed: {', '.join(req_tools)}\n\n"
                f"Kya aap sure hain? Confirm karne ke liye 'YES confirm' type karein."
            )
        return (
            f"⚠️ This action requires your approval!\n"
            f"Goal: {goal}\n"
            f"Risk Level: {risk.upper()}\n"
            f"Tools required: {', '.join(req_tools)}\n\n"
            f"Are you sure? Type 'YES confirm' to proceed."
        )

    # ── Convenience methods ───────────────────────────────────────────────────

    def get_history(self, limit: int = 10):
        return self.memory.get_context(limit=limit)

    def get_memory_stats(self) -> Dict:
        return self.memory.get_stats()

    def get_reasoning_status(self) -> Dict:
        """Return current Phase-2 and Phase-3 subsystem status."""
        return {
            "reasoning_engine": self.reasoning_engine is not None,
            "validator":        self.validator is not None,
            "auto_replan":      ENABLE_AUTO_REPLAN,
            "max_retries":      MAX_REPLAN_RETRIES,
            "planner":          self.planner is not None,
            "rag_memory":       self.rag_memory is not None,
            "coding_agent":     ENABLE_CODING_AGENT and (self.code_generator is not None),
        }
