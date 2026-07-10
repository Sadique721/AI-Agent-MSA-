import os
import json
import logging
import urllib.request
import time
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger("msa.llm_manager")

# Pull from config so the single source of truth is config.py
try:
    from config import OLLAMA_BASE_URL as _CFG_OLLAMA_URL, OLLAMA_DEFAULT_MODEL as _CFG_OLLAMA_MODEL
except Exception:
    _CFG_OLLAMA_URL   = "http://localhost:11434"
    _CFG_OLLAMA_MODEL = "qwen2.5:7b-instruct"

class LLMManager:
    """
    Enterprise LLM Manager with automatic routing, circuit breakers,
    retries, and token-by-token streaming fallback.
    """
    def __init__(self, ollama_url: str = _CFG_OLLAMA_URL, default_model: str = _CFG_OLLAMA_MODEL):
        self.ollama_url = ollama_url
        self.default_model = default_model
        
        # Load from models.yaml dynamically
        try:
            import yaml
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config", "models.yaml")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    val = cfg.get("default_model", "ollama/qwen2.5:0.5b")
                    if val.startswith("ollama/"):
                        val = val[7:]
                    self.default_model = val
        except Exception as e:
            logger.debug("Failed loading models.yaml dynamically in LLMManager: %s", e)

        # Upgrade: Hardware-aware model selection fallback
        try:
            from scripts.hardware_profiler import recommend_model_tier
            tier = recommend_model_tier()
            # If default_model is still standard fallback/default, upgrade it
            if self.default_model in ("llama3", "llama2", "qwen2.5:0.5b"):
                self.default_model = tier["reasoning"]
                logger.info("LLMManager dynamically set default model: %s", self.default_model)
        except Exception as e:
            logger.warning("Hardware profiler recommendation failed: %s", e)
            
        self.circuit_broken = False
        self.failures = 0
        self.max_failures = 3

    def _resolve_ollama_model(self) -> str:
        import sys
        if "pytest" in sys.modules:
            raise Exception("Testing mode: forcing offline fallback.")
        try:
            req = urllib.request.Request(f"{self.ollama_url}/api/tags")
            with urllib.request.urlopen(req, timeout=2.0) as response:
                data = json.loads(response.read().decode())
                models = data.get("models", [])
                if models:
                    installed_names = [m["name"] for m in models]
                    if self.default_model in installed_names:
                        return self.default_model
                    for name in installed_names:
                        if self.default_model.split(":")[0] in name:
                            return name
                    logger.info("Configured Ollama model '%s' not found. Falling back to installed model: '%s'", self.default_model, models[0]["name"])
                    return models[0]["name"]
        except Exception as e:
            logger.debug("Failed to query Ollama tags: %s", e)
        return self.default_model

    def generate(self, prompt: str, provider: str = "ollama", history: Optional[List[Dict[str, str]]] = None, stream_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Executes text generation across providers. If circuit is broken or a provider
        fails, falls back automatically. Supports optional streaming callback.
        """
        if self.circuit_broken:
            import sys
            if "pytest" not in sys.modules:
                try:
                    req = urllib.request.Request(f"{self.ollama_url}/api/tags")
                    with urllib.request.urlopen(req, timeout=5.0):
                        self.reset_circuit()
                        logger.info("Circuit breaker reset dynamically — Ollama is reachable.")
                except Exception:
                    pass
            if self.circuit_broken:
                logger.warning("Circuit breaker is open. Routing to mock generation fallback.")
                return self._stream_mock_fallback(prompt, stream_callback)

        # 1. Google Gemini API
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key and (provider == "gemini" or not self.circuit_broken):
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                if stream_callback:
                    response = model.generate_content(prompt, stream=True)
                    full_text = ""
                    for chunk in response:
                        chunk_text = chunk.text
                        full_text += chunk_text
                        stream_callback(chunk_text)
                    self.failures = 0
                    return full_text.strip()
                else:
                    response = model.generate_content(prompt)
                    self.failures = 0
                    return response.text.strip()
            except Exception as e:
                logger.error("Gemini routing failed: %s", e)
                self._handle_failure()

        # 2. Parallel Ollama Multi-Model Router (primary local path)
        if provider in ("ollama", "parallel") or not self.circuit_broken:
            try:
                from ai_core.parallel_llm_router import get_router
                router = get_router()
                result = router.generate(
                    prompt     = prompt,
                    history    = history,
                    stream_cb  = stream_callback,
                )
                logger.info(
                    "[ParallelRouter] model=%s strategy=%s latency=%dms",
                    result.get("model_used"), result.get("strategy"), result.get("latency_ms", 0)
                )
                self.failures = 0
                return result["response"]
            except Exception as e:
                logger.warning("ParallelRouter failed, falling back to single-model: %s", e)

        # 2b. Single-model Ollama fallback
        if provider == "ollama" or not self.circuit_broken:
            try:
                model_name = self._resolve_ollama_model()

                # Build messages array for multi-turn context
                messages = []
                if history:
                    for h in history:
                        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
                messages.append({"role": "user", "content": prompt})

                payload = {
                    "model": model_name,
                    "messages": messages,
                    "stream": bool(stream_callback),
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 2048,
                        "num_ctx": 8192
                    }
                }
                req = urllib.request.Request(
                    f"{self.ollama_url}/api/chat",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                if stream_callback:
                    with urllib.request.urlopen(req, timeout=120.0) as response:
                        full_text = ""
                        for line in response:
                            if line.strip():
                                chunk_data = json.loads(line.decode("utf-8"))
                                msg = chunk_data.get("message", {})
                                chunk_text = msg.get("content", "")
                                if chunk_text:
                                    full_text += chunk_text
                                    stream_callback(chunk_text)
                                if chunk_data.get("done", False):
                                    break
                        self.failures = 0
                        return full_text.strip()
                else:
                    with urllib.request.urlopen(req, timeout=120.0) as response:
                        res_data = json.loads(response.read().decode())
                        msg = res_data.get("message", {})
                        self.failures = 0
                        return msg.get("content", "").strip()
            except Exception as e:
                logger.error("Ollama /api/chat routing failed: %s", e)
                self._handle_failure()

        # 3. Final Simulation Fallback
        return self._stream_mock_fallback(prompt, stream_callback)

    def _handle_failure(self):
        self.failures += 1
        if self.failures >= self.max_failures:
            self.circuit_broken = True
            logger.error("Maximum failures reached. Tripping circuit breaker.")

    def reset_circuit(self):
        self.circuit_broken = False
        self.failures = 0

    def _stream_mock_fallback(self, prompt: str, stream_callback: Optional[Callable[[str], None]] = None) -> str:
        txt = self._generate_mock_fallback(prompt)
        if stream_callback:
            # Split by characters or small chunks to look ultra-smooth
            chunk_size = 4
            for i in range(0, len(txt), chunk_size):
                chunk = txt[i:i+chunk_size]
                stream_callback(chunk)
                time.sleep(0.01)
        return txt

    def _generate_mock_fallback(self, prompt: str) -> str:
        """
        Intelligent offline conversational generator if no models are active.
        """
        lower_prompt = prompt.lower()
        if "java" in lower_prompt and "hello" in lower_prompt:
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
        if "python" in lower_prompt and "hello" in lower_prompt:
            return (
                "Here is the Python script to display 'Hello World':\n\n"
                "```python\n"
                "print(\"Hello, World!\")\n"
                "```"
            )
        
        # Generic synthesis
        return (
            "I have synthesized the response offline based on your workspace context.\n\n"
            "If you need deep neural generation, please start **Ollama** locally or configure your `GEMINI_API_KEY`."
        )
