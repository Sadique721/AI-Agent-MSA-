"""
backend/decision_engine.py
==========================
MSA Decision Engine — processes user commands and returns structured decisions.

Priority chain:
  1. LLaMA 2 GGUF via llama-cpp (if model file exists)
  2. Smart keyword-based fallback using AgentUtils (always works offline)

FIX LOG:
  - Added guaranteed `parameters` key in ALL return paths (was missing in mock path)
  - Replaced bare print() with logging
  - Added smart keyword-based fallback for LLM-free operation
  - Added `internet_search` and `web_search` action routing
  - Bare `except:` replaced with `except Exception`
"""

import json
import logging
import os
import sys

# ---------------------------------------------------------------------------
# Optional LLM backend
# ---------------------------------------------------------------------------
try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("msa.decision_engine")

# ---------------------------------------------------------------------------
# AgentUtils for smart fallback
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from agent.AgentUtils import parse_intent, extract_keywords, format_response
    from config import USER_PROFILE_DATA as _USER_PROFILE_DATA
    _agent_utils_ok = True
except ImportError:
    _USER_PROFILE_DATA = {"name": "Md Sadique Amin", "role": "Software Engineer"}
    _agent_utils_ok = False
    logger.warning("AgentUtils not available — using minimal fallback.")


# ---------------------------------------------------------------------------
# Smart keyword fallback responses
# ---------------------------------------------------------------------------
_OPEN_VERBS = {"open", "launch", "start", "run", "execute"}

def _open_app_handler(kw):
    # Strip trigger verbs to get the actual app name
    app_kw = [k for k in kw if k not in _OPEN_VERBS]
    app = app_kw[0] if app_kw else (kw[0] if kw else "notepad")
    return (f"Opening {app} now.", {"app": app})

_FALLBACK_RESPONSES = {
    "open_app":        _open_app_handler,
    "internet_search": lambda kw: (f"Searching for '{' '.join(kw)}' on the web.", {"query": " ".join(kw)}),
    "shutdown":        lambda kw: ("Shutting down the system. Goodbye!", {}),
    "restart":         lambda kw: ("Restarting the system now.", {}),
    "get_profile":     lambda kw: ("Fetching your profile information.", {}),
    "get_time":        lambda kw: ("Checking the current time for you.", {}),
    "mobile_make_call":lambda kw: (f"Calling {kw[0] if kw else 'contact'}.", {"number": kw[0] if kw else ""}),
    "mobile_set_alarm":lambda kw: ("Setting alarm as requested.", {"time": " ".join(kw)}),
    "mobile_open_app": lambda kw: (f"Opening {kw[0] if kw else 'app'} on mobile.", {"package": kw[0] if kw else ""}),
    "automation":      lambda kw: ("Running automation task.", {"task": " ".join(kw)}),
    "vision":          lambda kw: ("Activating camera for visual detection.", {}),
    "location":        lambda kw: ("Fetching your current location.", {}),
    "none":            lambda kw: (None, {}),
}


class DecisionEngine:
    """
    Processes user commands into structured decision dicts.

    Returns:
        {
            "response":   str,   # spoken/displayed reply
            "action":     str,   # action key
            "parameters": dict,  # action parameters
        }
    """

    def __init__(self, model_path: str = "models/llm/llama-2-7b-chat.Q4_K_M.gguf"):
        model_full_path = os.path.join(PROJECT_ROOT, model_path)
        self.llm = None

        if Llama and os.path.exists(model_full_path):
            try:
                self.llm = Llama(model_path=model_full_path, n_ctx=2048, n_threads=4)
                logger.info("LLaMA model loaded from %s", model_full_path)
            except Exception as e:
                logger.error("LLaMA load failed: %s", e)
        else:
            logger.warning(
                "LLM not found at %s or llama_cpp missing. "
                "Decision Engine using smart keyword fallback.",
                model_full_path,
            )

        self.profile = self._load_profile()
        logger.info("DecisionEngine ready (LLM=%s).", "online" if self.llm else "offline/fallback")

    # -----------------------------------------------------------------------
    def _load_profile(self) -> dict:
        profile_path = os.path.join(PROJECT_ROOT, "data", "user_profile.json")
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return _USER_PROFILE_DATA

    # -----------------------------------------------------------------------
    def process_command(self, user_input: str, context: list) -> dict:
        """
        Main entry point. Returns a decision dict with guaranteed keys:
            response, action, parameters
        """
        if not user_input or not user_input.strip():
            return {"response": "Please say or type a command.", "action": "none", "parameters": {}}

        # --- LLM path ---
        if self.llm:
            result = self._llm_decision(user_input, context)
            if result:
                result.setdefault("parameters", {})
                return result

        # --- Smart keyword fallback ---
        return self._keyword_decision(user_input)

    # -----------------------------------------------------------------------
    def _llm_decision(self, user_input: str, context: list) -> dict | None:
        """Try the LLM. Returns None on failure so fallback can run."""
        prompt = f"""You are MSA, an AI assistant. User: {self.profile.get('name')}, Role: {self.profile.get('role')}.
Context: {context}
Command: {user_input}

Respond ONLY with a JSON object:
{{
  "response": "<short reply in English or Hinglish>",
  "action": "<one of: open_app|shutdown|restart|mobile_open_app|mobile_make_call|mobile_set_alarm|automation|internet_search|vision|location|none>",
  "parameters": {{}}
}}"""
        try:
            output = self.llm(prompt, max_tokens=256, temperature=0.7, stop=["\n\n"])
            text = output["choices"][0]["text"].strip()
            start, end = text.find("{"), text.rfind("}") + 1
            if 0 <= start < end:
                data = json.loads(text[start:end])
                data.setdefault("parameters", {})
                return data
        except Exception as e:
            logger.error("LLM decision error: %s", e)
        return None

    # -----------------------------------------------------------------------
    def _keyword_decision(self, user_input: str) -> dict:
        """Smart offline fallback using AgentUtils intent + keyword extraction."""
        if _agent_utils_ok:
            intent = parse_intent(user_input)
            keywords = extract_keywords(user_input)
        else:
            intent = "none"
            keywords = user_input.lower().split()

        handler = _FALLBACK_RESPONSES.get(intent, _FALLBACK_RESPONSES["none"])
        response_text, parameters = handler(keywords)

        if response_text is None:
            # Generic conversational reply
            response_text = (
                f"I received your message: \"{user_input}\". "
                "How can I help you further? Try commands like 'open notepad', 'search python', or 'shutdown'."
            )
            intent = "none"

        logger.info("Keyword decision — intent=%s keywords=%s", intent, keywords)
        return {
            "response":   response_text,
            "action":     intent,
            "parameters": parameters,
        }
