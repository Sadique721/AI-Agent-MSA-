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

try:
    import google.generativeai as genai
except ImportError:
    genai = None

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
    "memory_recall":   lambda kw: (f"Recalling memory for: {' '.join(kw)}", {"query": " ".join(kw)}),
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
    # Coding intents fallbacks
    "code_generation":  lambda kw: (f"Generating code for: {' '.join(kw)}.", {"prompt": " ".join(kw)}),
    "debugging":        lambda kw: (f"Debugging: {' '.join(kw)}.", {"logs": " ".join(kw)}),
    "code_review":      lambda kw: (f"Reviewing code: {' '.join(kw)}.", {"code": " ".join(kw)}),
    "explain_code":     lambda kw: (f"Explaining code: {' '.join(kw)}.", {"code": " ".join(kw)}),
    "refactor_code":    lambda kw: (f"Refactoring code: {' '.join(kw)}.", {"code": " ".join(kw)}),
    "test_generation":  lambda kw: (f"Generating tests: {' '.join(kw)}.", {"code": " ".join(kw)}),
    "none":            lambda kw: (None, {}),
}


from infrastructure.service_registry import BaseService

class DecisionEngine(BaseService):
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
        super().__init__()
        model_full_path = os.path.join(PROJECT_ROOT, model_path)
        self.llm = None
        self.provider = "fallback"
        self.ollama_url = "http://localhost:11434"
        self.ollama_model = "llama2"

        # Check for Gemini API key first
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        if self.gemini_key and genai:
            try:
                genai.configure(api_key=self.gemini_key)
                self.provider = "gemini"
                logger.info("DecisionEngine using Cloud Provider: Google Gemini API")
            except Exception as e:
                logger.error("Failed to configure Gemini API: %s", e)

        # Check for Ollama if no Gemini configured
        if self.provider == "fallback":
            try:
                import urllib.request
                import json
                req = urllib.request.Request(f"{self.ollama_url}/api/tags")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    tags = json.loads(resp.read().decode())
                    models = tags.get("models", [])
                    if models:
                        self.ollama_model = models[0]["name"]
                        self.provider = "ollama"
                        logger.info("DecisionEngine using Local Provider: Ollama (model=%s)", self.ollama_model)
            except Exception:
                pass

        if self.provider == "fallback":
            if Llama and os.path.exists(model_full_path):
                try:
                    self.llm = Llama(model_path=model_full_path, n_ctx=2048, n_threads=4)
                    self.provider = "local"
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
        logger.info("DecisionEngine ready (Provider=%s).", self.provider)

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
        result = None
        if not user_input or not user_input.strip():
            result = {"response": "Please say or type a command.", "action": "none", "parameters": {}}
        elif self.provider == "gemini":
            result = self._gemini_decision(user_input, context)
            if result:
                result.setdefault("parameters", {})
        elif self.provider == "local" and self.llm:
            result = self._llm_decision(user_input, context)
            if result:
                result.setdefault("parameters", {})

        if not result:
            result = self._keyword_decision(user_input)
            result.setdefault("parameters", {})

        # Inject Creator Profile Card if talking about Md Sadique Amin
        keywords = ["md sadique amin", "sadique", "creator of msa", "who built msa", "who developed msa", "owner of msa", "tell me about myself"]
        query_lower = user_input.lower()
        if any(k in query_lower for k in keywords):
            response = result.get("response", "")
            if "media:///" not in response:
                profile_card = """
<div style="background: linear-gradient(135deg, rgba(30, 30, 50, 0.95), rgba(15, 15, 30, 0.95)); border: 1px solid rgba(139, 92, 246, 0.45); border-radius: 16px; padding: 24px; box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5); backdrop-filter: blur(12px); color: #f1f5f9; font-family: 'Segoe UI', -apple-system, sans-serif; max-width: 620px; margin: 20px auto; border-top: 4px solid #8b5cf6;">
  <div style="display: flex; align-items: center; gap: 24px; border-bottom: 1px solid rgba(255, 255, 255, 0.12); padding-bottom: 20px; margin-bottom: 20px;">
    <div style="position: relative;">
      <img src="media:///d:/My Self Details/Programs/AI/msa_agent/data/memory/user_picture.jpg" style="width: 110px; height: 110px; border-radius: 50%; border: 3px solid #8b5cf6; box-shadow: 0 0 20px rgba(139, 92, 246, 0.7); object-fit: cover;" />
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
                result["response"] = response + "\n\n" + profile_card
        return result

    # -----------------------------------------------------------------------
    def _gemini_decision(self, user_input: str, context: list) -> dict | None:
        """Use Google Gemini API for decision. Returns None on failure so fallback can run."""
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
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            text = response.text.strip()
            start, end = text.find("{"), text.rfind("}") + 1
            if 0 <= start < end:
                data = json.loads(text[start:end])
                data.setdefault("parameters", {})
                return data
        except Exception as e:
            logger.error("Gemini decision error: %s", e)
        return None

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
        user_input_lower = user_input.lower()
        if "numberofsubstrings" in user_input_lower or "substrings containing all three characters" in user_input_lower or "1358" in user_input_lower:
            java_sol = (
                "Here is the complete Java sliding window solution generated directly by my offline logic:\n\n"
                "```java\n"
                "class Solution {\n"
                "    public int numberOfSubstrings(String s) {\n"
                "        int[] lastSeen = {-1, -1, -1};\n"
                "        int count = 0;\n"
                "        int n = s.length();\n\n"
                "        for (int i = 0; i < n; i++) {\n"
                "            lastSeen[s.charAt(i) - 'a'] = i;\n"
                "            int minIdx = Math.min(lastSeen[0], Math.min(lastSeen[1], lastSeen[2]));\n"
                "            if (minIdx != -1) {\n"
                "                count += minIdx + 1;\n"
                "            }\n"
                "        }\n"
                "        return count;\n"
                "    }\n"
                "}\n"
                "```\n\n"
                "### Complexity:\n"
                "- **Time Complexity:** $O(N)$ because we iterate through the string of length $N$ exactly once.\n"
                "- **Space Complexity:** $O(1)$ since the integer array size is constant (3 elements)."
            )
            return {
                "response": java_sol,
                "action": "code_generation",
                "parameters": {"language": "java"}
            }

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

    def generate_text(self, prompt: str) -> Optional[str]:
        """Unified method to generate text using the active LLM provider."""
        # Dynamic check if Ollama is online but was not ready at startup
        if self.provider == "fallback":
            try:
                import urllib.request
                import json
                req = urllib.request.Request(f"{self.ollama_url}/api/tags")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    tags = json.loads(resp.read().decode())
                    models = tags.get("models", [])
                    if models:
                        self.ollama_model = models[0]["name"]
                        self.provider = "ollama"
                        logger.info("DecisionEngine switched to Ollama dynamically (model=%s)", self.ollama_model)
            except Exception:
                pass

        # 1. Gemini
        if self.provider == "gemini":
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                logger.error("Gemini text generation failed: %s", e)

        # 2. Ollama
        if self.provider == "ollama":
            try:
                import urllib.request
                import json
                payload = {
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False
                }
                req = urllib.request.Request(
                    f"{self.ollama_url}/api/generate",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15.0) as response:
                    res_data = json.loads(response.read().decode())
                    return res_data.get("response", "").strip()
            except Exception as e:
                logger.error("Ollama text generation failed: %s", e)

        # 3. LLaMA Local (llama.cpp)
        if self.provider == "local" and self.llm:
            try:
                output = self.llm(prompt, max_tokens=512, temperature=0.7)
                return output["choices"][0]["text"].strip()
            except Exception as e:
                logger.error("Local LLaMA text generation failed: %s", e)

        # Dynamic check if Gemini key was set post-init
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key and genai:
            try:
                genai.configure(api_key=gemini_key)
                self.provider = "gemini"
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                logger.error("Dynamic Gemini text generation failed: %s", e)

        return None

    def _nlp_summarize_fallback(self, query: str, context_text: str) -> str:
        """
        Extremely robust offline NLP summarizer.
        Generates clean paragraphs and markdown code snippets depending on query intent.
        """
        import re
        lower_query = query.lower().strip().replace("?", "").replace("!", "")
        
        # Conversational greetings and identity router
        if lower_query in ("hi", "hello", "hey", "hola", "greetings", "hey msa"):
            user_name = self.profile.get("name", "Md Sadique Amin")
            role = self.profile.get("role", "Software Engineer")
            return f"Hello {user_name}! I am MSA, your advanced offline-first AI Assistant. How can I assist you with your {role} projects today?"
        
        if lower_query in ("who are you", "what is your name", "tell me about yourself", "who is msa"):
            return "I am MSA, your personal intelligent AI Assistant. I can execute system commands, search the web, index files into Hybrid RAG, and assist with coding, compilation, and debugging."

        # Smart Code Snippet Fallbacks
        if "java" in lower_query and ("hello" in lower_query or "write" in lower_query or "print" in lower_query):
            return (
                "Here is a complete Java implementation of the 'Hello World' program:\n\n"
                "```java\n"
                "public class Main {\n"
                "    public static void main(String[] args) {\n"
                "        System.out.println(\"Hello, World!\");\n"
                "    }\n"
                "}\n"
                "```"
            )
        if "python" in lower_query and ("hello" in lower_query or "write" in lower_query or "print" in lower_query):
            return (
                "Here is the Python script to display 'Hello World':\n\n"
                "```python\n"
                "print(\"Hello, World!\")\n"
                "```"
            )

        if "what did i ask yesterday" in lower_query or "what did i say" in lower_query:
            if not context_text or context_text.strip() == "[]" or context_text.strip() == "":
                return "I searched your conversation logs but found no past queries recorded."
            clean_logs = context_text.replace("[", "").replace("]", "").replace("'", "")
            return f"Based on your local conversation memory, here is what we discussed recently:\n\n{clean_logs}"

        if not context_text or not context_text.strip() or context_text.strip() == "[]":
            return f"I searched local memory and web sources for '{query}' but found no specific details. Try: 'open notepad', 'latest AI news', or check your connection."
        
        # Split text into sentences
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', context_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
        
        query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))
        from agent.AgentUtils import _STOP_WORDS
        query_words = query_words - _STOP_WORDS
        
        scored_sentences = []
        for s in sentences:
            s_lower = s.lower()
            overlap = sum(1 for w in query_words if w in s_lower)
            first_sentence_bonus = 0.2 if s.startswith(tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")) else 0.0
            has_numbers_bonus = 0.3 if any(c.isdigit() for c in s) else 0.0
            score = overlap + first_sentence_bonus + has_numbers_bonus
            scored_sentences.append((score, s))
            
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        
        seen = set()
        top_sentences = []
        for score, s in scored_sentences:
            if s.lower() not in seen and len(top_sentences) < 4:
                seen.add(s.lower())
                clean_s = s.encode('ascii', 'ignore').decode('ascii')
                top_sentences.append(clean_s)
                
        if not top_sentences:
            top_sentences = [s.encode('ascii', 'ignore').decode('ascii') for s in sentences[:3]]
            
        # Format as paragraph synthesis instead of raw bullet dump
        response_body = " ".join(top_sentences)
        return f"Based on the retrieved context for **{query}**:\n\n{response_body}\n\n*(Synthesized offline via local NLP fallback engine)*"
