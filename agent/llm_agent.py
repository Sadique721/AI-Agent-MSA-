"""
agent/llm_agent.py
==================
LLM Agent for MSA AI Agent V5.0.
Wraps ai_core/llm_manager.py + ai_core/ai_router.py with:
  - LiteLLM unified interface (when available)
  - Ollama local inference (primary)
  - Cloud model fallback chain
  - Token-by-token streaming via callbacks
  - Smart simulation fallback when no models available
"""
from __future__ import annotations

import logging
import os
import sys
import time
from typing import Callable, Dict, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger("msa.agent.llm")


class LLMResponse:
    def __init__(self, text: str, model: str, tokens: int = 0, duration_ms: float = 0.0, cached: bool = False):
        self.text = text
        self.model = model
        self.tokens = tokens
        self.duration_ms = duration_ms
        self.cached = cached

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "model": self.model,
            "tokens": self.tokens,
            "duration_ms": round(self.duration_ms, 2),
            "cached": self.cached,
        }


class LLMAgent:
    """
    Unified LLM execution agent.

    Priority chain:
      1. LiteLLM (if installed) → Ollama / cloud models
      2. Legacy ai_core/llm_manager.py
      3. Smart simulation fallback

    Supports streaming via stream_callback(token: str).
    """

    def __init__(self, config: Optional[Dict] = None) -> None:
        self._config = config or {}
        self._litellm = None
        self._legacy_manager = None
        self._cache: Dict[str, str] = {}

        self._load_litellm()
        if not self._litellm:
            self._load_legacy()

    def _load_litellm(self) -> None:
        try:
            import litellm  # type: ignore
            litellm.drop_params = True
            litellm.set_verbose = False
            self._litellm = litellm
            logger.info("LiteLLM loaded successfully")
        except ImportError:
            logger.debug("LiteLLM not installed — trying legacy manager")

    def _load_legacy(self) -> None:
        try:
            from ai_core.llm_manager import LLMManager
            self._legacy_manager = LLMManager()
            logger.info("Legacy LLMManager loaded")
        except Exception as e:
            logger.debug("Legacy LLMManager unavailable: %s", e)

    def _get_model(self, task_type: str, reasoning_mode: str) -> str:
        """Select best model from config."""
        try:
            from ai_core.ai_router import get_ai_router
            router = get_ai_router()
            return router.select_model(task_type=task_type, reasoning_mode=reasoning_mode)
        except Exception:
            return self._config.get("default_model", "ollama/llama3.2:3b")

    def generate(
        self,
        prompt: str,
        task_type: str = "GENERAL_QA",
        reasoning_mode: str = "balanced",
        stream_callback: Optional[Callable[[str], None]] = None,
        status_callback: Optional[Callable[[str, str], None]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Generate a response from the best available LLM."""
        start = time.time()

        # Cache check
        cache_key = f"{prompt[:200]}:{task_type}:{reasoning_mode}"
        if cache_key in self._cache:
            cached_text = self._cache[cache_key]
            if stream_callback:
                import re
                chunks = re.split(r'(\s+)', cached_text)
                for chunk in chunks:
                    if chunk:
                        stream_callback(chunk)
                        time.sleep(0.005)
            return LLMResponse(cached_text, "cache", cached=True, duration_ms=(time.time() - start) * 1000)

        if status_callback:
            status_callback("generating", "Calling language model...")

        model = self._get_model(task_type, reasoning_mode)

        # Try LiteLLM first
        if self._litellm:
            result = self._generate_litellm(prompt, model, stream_callback, max_tokens, temperature)
            if result:
                self._cache[cache_key] = result.text
                result.duration_ms = (time.time() - start) * 1000
                return result

        # Try legacy manager
        if self._legacy_manager:
            result = self._generate_legacy(prompt, stream_callback, status_callback)
            if result:
                self._cache[cache_key] = result.text
                result.duration_ms = (time.time() - start) * 1000
                return result

        # Smart simulation fallback
        if status_callback:
            status_callback("generating", "Using intelligent simulation (no LLM available)")
        fallback_text = self._smart_simulate(prompt, task_type)
        if stream_callback:
            import re
            chunks = re.split(r'(\s+)', fallback_text)
            for chunk in chunks:
                if chunk:
                    stream_callback(chunk)
                    time.sleep(0.005)
        self._cache[cache_key] = fallback_text
        return LLMResponse(fallback_text, "simulation", duration_ms=(time.time() - start) * 1000)

    def _generate_litellm(
        self, prompt: str, model: str,
        stream_callback: Optional[Callable],
        max_tokens: int, temperature: float,
    ) -> Optional[LLMResponse]:
        try:
            messages = [{"role": "user", "content": prompt}]

            if stream_callback:
                full_text = ""
                response = self._litellm.completion(
                    model=model, messages=messages,
                    max_tokens=max_tokens, temperature=temperature,
                    stream=True,
                )
                for chunk in response:
                    delta = chunk.choices[0].delta
                    token = getattr(delta, "content", None)
                    if token:
                        full_text += token
                        stream_callback(token)
                return LLMResponse(full_text.strip(), model)
            else:
                response = self._litellm.completion(
                    model=model, messages=messages,
                    max_tokens=max_tokens, temperature=temperature,
                )
                text = response.choices[0].message.content or ""
                tokens = response.usage.total_tokens if response.usage else 0
                return LLMResponse(text.strip(), model, tokens=tokens)
        except Exception as e:
            logger.warning("LiteLLM call failed (%s): %s", model, e)
            return None

    def _generate_legacy(
        self, prompt: str,
        stream_callback: Optional[Callable],
        status_callback: Optional[Callable],
    ) -> Optional[LLMResponse]:
        try:
            if hasattr(self._legacy_manager, "generate_response"):
                text = self._legacy_manager.generate_response(prompt)
            elif hasattr(self._legacy_manager, "generate"):
                text = self._legacy_manager.generate(prompt)
            else:
                return None
            if not text:
                return None
            if stream_callback:
                import re
                chunks = re.split(r'(\s+)', text)
                for chunk in chunks:
                    if chunk:
                        stream_callback(chunk)
                        time.sleep(0.005)
            return LLMResponse(text.strip(), "legacy_manager")
        except Exception as e:
            logger.warning("Legacy LLM call failed: %s", e)
            return None

    def _smart_simulate(self, prompt: str, task_type: str) -> str:
        """Context-aware simulation for when no LLM is available."""
        prompt_lower = prompt.lower()
        lines = []

        if task_type == "CODING" or any(kw in prompt_lower for kw in ["write", "code", "function", "class"]):
            lines = [
                "Here's an implementation based on your requirements:\n",
                "```python",
                "def solution():",
                '    """Auto-generated solution — connect Ollama for real code generation."""',
                "    pass  # Replace with actual implementation",
                "```",
                "\n**Note:** For production code generation, ensure Ollama is running with `ollama serve`.",
            ]
        elif any(kw in prompt_lower for kw in ["explain", "what is", "describe", "tell me"]):
            topic = prompt[:80].strip()
            lines = [
                f"**About: {topic}**\n",
                "This is a contextual explanation generated by MSA AI Agent V5.0.",
                "For detailed, accurate responses, please ensure your LLM (Ollama) is running.",
                "\nTo start Ollama: `ollama serve`",
                "To pull a model: `ollama pull llama3.2:3b`",
            ]
        else:
            lines = [
                "MSA AI Agent V5.0 is ready and processing your request.",
                f"\n**Your query:** {prompt[:100]}",
                "\n**Status:** Language model (Ollama) is not currently connected.",
                "Run `ollama serve` and `ollama pull llama3.2:3b` to enable full AI responses.",
                "\nAll other systems (memory, RAG, tools, streaming) are operational.",
            ]

        return "\n".join(lines)


# ── Module singleton ──────────────────────────────────────────────────────────
_llm_agent: Optional[LLMAgent] = None


def get_llm_agent(config: Optional[Dict] = None) -> LLMAgent:
    global _llm_agent
    if _llm_agent is None:
        _llm_agent = LLMAgent(config=config)
    return _llm_agent
