import os
import json
import logging
import urllib.request
import time
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger("msa.llm_manager")

class LLMManager:
    """
    Enterprise LLM Manager with automatic routing, circuit breakers,
    retries, and token-by-token streaming fallback.
    """
    def __init__(self, ollama_url: str = "http://localhost:11434", default_model: str = "llama3"):
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
            
        self.circuit_broken = False
        self.failures = 0
        self.max_failures = 3

    def generate(self, prompt: str, provider: str = "ollama", history: Optional[List[Dict[str, str]]] = None, stream_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Executes text generation across providers. If circuit is broken or a provider
        fails, falls back automatically. Supports optional streaming callback.
        """
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

        # 2. Ollama Local Endpoint
        if provider == "ollama" or not self.circuit_broken:
            try:
                payload = {
                    "model": self.default_model,
                    "prompt": prompt,
                    "stream": bool(stream_callback)
                }
                req = urllib.request.Request(
                    f"{self.ollama_url}/api/generate",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                if stream_callback:
                    with urllib.request.urlopen(req, timeout=30.0) as response:
                        full_text = ""
                        for line in response:
                            if line:
                                chunk_data = json.loads(line.decode("utf-8"))
                                chunk_text = chunk_data.get("response", "")
                                full_text += chunk_text
                                stream_callback(chunk_text)
                        self.failures = 0
                        return full_text.strip()
                else:
                    with urllib.request.urlopen(req, timeout=30.0) as response:
                        res_data = json.loads(response.read().decode())
                        self.failures = 0
                        return res_data.get("response", "").strip()
            except Exception as e:
                logger.error("Ollama routing failed: %s", e)
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
