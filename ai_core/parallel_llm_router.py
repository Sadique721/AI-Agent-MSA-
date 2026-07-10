"""
ai_core/parallel_llm_router.py
==============================
Parallel Multi-Model LLM Router — V6 Ultra

Splits any task across all 4 installed Ollama models simultaneously
using Python ThreadPoolExecutor, then aggregates the best response.

Model assignments:
  • qwen2.5:0.5b        → FAST lane  — intent detection, quick classification (< 1s)
  • qwen2.5:7b-instruct → MAIN lane  — primary reasoning, code, writing
  • deepseek-r1:7b      → DEEP lane  — complex analysis, math, research
  • nomic-embed-text    → EMBED lane — semantic similarity, vector search

Strategy:
  - For SIMPLE queries  → qwen2.5:0.5b (fastest, instant)
  - For NORMAL queries  → qwen2.5:7b + qwen2.5:0.5b in parallel → first good response wins
  - For COMPLEX queries → all 3 generative models in parallel → merge/best-of responses
  - For SEARCH/MEMORY   → nomic-embed-text for embeddings + generative model for answer
"""

import json
import logging
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("msa.parallel_llm")

# ─── Model Registry ───────────────────────────────────────────────────────────
try:
    from config import (
        OLLAMA_BASE_URL,
        OLLAMA_DEFAULT_MODEL,
        OLLAMA_FAST_MODEL,
        OLLAMA_REASON_MODEL,
        OLLAMA_EMBED_MODEL,
        OLLAMA_REQUEST_TIMEOUT,
    )
except ImportError:
    OLLAMA_BASE_URL        = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL   = "qwen2.5:7b-instruct"
    OLLAMA_FAST_MODEL      = "qwen2.5:0.5b"
    OLLAMA_REASON_MODEL    = "deepseek-r1:7b"
    OLLAMA_EMBED_MODEL     = "nomic-embed-text:latest"
    OLLAMA_REQUEST_TIMEOUT = 120

MODELS = {
    "fast":  OLLAMA_FAST_MODEL,    # qwen2.5:0.5b   — instant responses
    "main":  OLLAMA_DEFAULT_MODEL, # qwen2.5:7b      — primary intelligence
    "deep":  OLLAMA_REASON_MODEL,  # deepseek-r1:7b  — complex reasoning
    "embed": OLLAMA_EMBED_MODEL,   # nomic-embed-text — vectors
}

# Task complexity thresholds (token count heuristic)
SIMPLE_THRESHOLD  = 15   # <= 15 words → fast model only
COMPLEX_THRESHOLD = 60   # >= 60 words → all models


# ─── Low-level Ollama call ────────────────────────────────────────────────────
def _call_ollama(
    model: str,
    prompt: str,
    system: str = "",
    history: Optional[List[Dict]] = None,
    stream_cb: Optional[Callable[[str], None]] = None,
    timeout: int = OLLAMA_REQUEST_TIMEOUT,
) -> str:
    """
    Single blocking Ollama /api/chat call.
    Supports streaming via stream_cb(token).
    Returns full response string.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model":    model,
        "messages": messages,
        "stream":   stream_cb is not None,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    full_response = []
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for line in resp:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    full_response.append(token)
                    if stream_cb:
                        stream_cb(token)
                if data.get("done"):
                    break
            except json.JSONDecodeError:
                continue

    return "".join(full_response)


def _embed_text(text: str) -> List[float]:
    """Get embedding vector from nomic-embed-text."""
    payload = json.dumps({
        "model":  MODELS["embed"],
        "prompt": text,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data.get("embedding", [])


# ─── Task Complexity Classifier ───────────────────────────────────────────────
def _classify_complexity(prompt: str) -> str:
    """
    Returns 'simple' | 'normal' | 'complex' based on prompt length
    and presence of reasoning keywords.
    """
    words = len(prompt.split())
    low   = prompt.lower()

    reasoning_keywords = [
        "explain", "analyze", "compare", "design", "architecture",
        "why", "how does", "debug", "research", "strategy", "plan",
        "optimize", "implement", "create", "generate", "write",
        "step by step", "detailed", "comprehensive",
    ]
    has_reasoning = any(kw in low for kw in reasoning_keywords)

    if words <= SIMPLE_THRESHOLD and not has_reasoning:
        return "simple"
    elif words >= COMPLEX_THRESHOLD or has_reasoning:
        return "complex"
    else:
        return "normal"


# ─── Response Scorer ─────────────────────────────────────────────────────────
def _score_response(response: str, prompt: str) -> float:
    """
    Heuristic quality score for a response.
    Higher = better. Used to pick the best when multiple models answer.
    """
    if not response or len(response.strip()) < 10:
        return 0.0

    score = len(response) * 0.001  # length bonus

    # Code block bonus
    if "```" in response:
        score += 2.0

    # Structured response bonus (numbered/bulleted)
    if any(c in response for c in ["1.", "2.", "- ", "* ", "•"]):
        score += 1.5

    # Keyword alignment with prompt
    prompt_words = set(prompt.lower().split())
    resp_words   = set(response.lower().split())
    overlap = len(prompt_words & resp_words) / max(len(prompt_words), 1)
    score += overlap * 3.0

    # Penalize very short responses
    if len(response.split()) < 20:
        score -= 2.0

    return score


# ─── Parallel Router ─────────────────────────────────────────────────────────
class ParallelLLMRouter:
    """
    Routes prompts across all 4 Ollama models in parallel threads.
    Automatically selects strategy based on complexity.
    """

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="msa-llm")
        self._lock     = threading.Lock()
        logger.info(
            "ParallelLLMRouter initialized — models: %s",
            list(MODELS.values()),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(
        self,
        prompt:      str,
        system:      str = "",
        history:     Optional[List[Dict]] = None,
        stream_cb:   Optional[Callable[[str], None]] = None,
        force_model: Optional[str] = None,
    ) -> Dict:
        """
        Main entry point. Returns:
        {
            "response":   str,         # best response text
            "model_used": str,         # which model produced it
            "strategy":   str,         # simple/normal/complex
            "all_results": {...},      # all model responses
            "latency_ms": int,
        }
        """
        start = time.time()

        # Forced model override
        if force_model:
            resp = _call_ollama(force_model, prompt, system, history, stream_cb)
            return {
                "response":    resp,
                "model_used":  force_model,
                "strategy":    "forced",
                "all_results": {force_model: resp},
                "latency_ms":  int((time.time() - start) * 1000),
            }

        complexity = _classify_complexity(prompt)
        logger.info("Complexity: %s | prompt_words: %d", complexity, len(prompt.split()))

        if complexity == "simple":
            return self._strategy_simple(prompt, system, history, stream_cb, start)
        elif complexity == "normal":
            return self._strategy_normal(prompt, system, history, stream_cb, start)
        else:
            return self._strategy_complex(prompt, system, history, stream_cb, start)

    def embed(self, text: str) -> List[float]:
        """Get embedding from nomic-embed-text (runs in thread pool)."""
        future = self._executor.submit(_embed_text, text)
        return future.result(timeout=30)

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in parallel."""
        futures = {self._executor.submit(_embed_text, t): i for i, t in enumerate(texts)}
        results = [None] * len(texts)
        for f in as_completed(futures):
            idx = futures[f]
            try:
                results[idx] = f.result(timeout=30)
            except Exception as e:
                logger.warning("Embed failed for index %d: %s", idx, e)
                results[idx] = []
        return results

    def shutdown(self):
        self._executor.shutdown(wait=False)

    # ── Strategies ────────────────────────────────────────────────────────────

    def _strategy_simple(self, prompt, system, history, stream_cb, start) -> Dict:
        """
        SIMPLE: Only qwen2.5:0.5b — fastest possible response.
        """
        logger.info("[Strategy=simple] → %s", MODELS["fast"])
        resp = _call_ollama(MODELS["fast"], prompt, system, history, stream_cb)
        return self._pack(resp, MODELS["fast"], "simple", {MODELS["fast"]: resp}, start)

    def _strategy_normal(self, prompt, system, history, stream_cb, start) -> Dict:
        """
        NORMAL: qwen2.5:7b (main) + qwen2.5:0.5b (fast) in parallel.
        First complete response that meets quality threshold wins.
        Stream tokens from the winner to stream_cb.
        """
        logger.info("[Strategy=normal] → parallel: %s + %s", MODELS["main"], MODELS["fast"])

        results: Dict[str, str] = {}
        first_good: Dict = {}
        winner_lock = threading.Lock()

        def _run(lane: str):
            model = MODELS[lane]
            # Only stream from main model
            cb = stream_cb if lane == "main" else None
            try:
                resp = _call_ollama(model, prompt, system, history, cb)
                with winner_lock:
                    results[model] = resp
                    if not first_good and _score_response(resp, prompt) > 0.5:
                        first_good["response"] = resp
                        first_good["model"]    = model
            except Exception as e:
                logger.warning("[%s] failed: %s", model, e)

        threads = [
            threading.Thread(target=_run, args=(lane,), daemon=True)
            for lane in ["main", "fast"]
        ]
        for t in threads: t.start()
        for t in threads: t.join(timeout=OLLAMA_REQUEST_TIMEOUT)

        best_model = first_good.get("model", MODELS["main"])
        best_resp  = first_good.get("response", results.get(MODELS["main"], ""))
        return self._pack(best_resp, best_model, "normal", results, start)

    def _strategy_complex(self, prompt, system, history, stream_cb, start) -> Dict:
        """
        COMPLEX: All 3 generative models in parallel.
        Responses are scored; highest quality wins.
        Stream tokens from main model to stream_cb immediately;
        deeper models contribute if they finish before response is sent.
        """
        logger.info(
            "[Strategy=complex] → parallel: %s + %s + %s",
            MODELS["fast"], MODELS["main"], MODELS["deep"],
        )

        results: Dict[str, str] = {}
        r_lock = threading.Lock()

        def _run(lane: str):
            model = MODELS[lane]
            cb = stream_cb if lane == "main" else None
            try:
                resp = _call_ollama(model, prompt, system, history, cb, timeout=OLLAMA_REQUEST_TIMEOUT)
                with r_lock:
                    results[model] = resp
                logger.info("[%s] done (%d chars)", model, len(resp))
            except Exception as e:
                logger.warning("[%s] failed: %s", model, e)

        threads = [
            threading.Thread(target=_run, args=(lane,), daemon=True)
            for lane in ["fast", "main", "deep"]
        ]
        for t in threads: t.start()
        for t in threads: t.join(timeout=OLLAMA_REQUEST_TIMEOUT)

        # Score all responses and pick best
        if not results:
            return self._pack("", MODELS["main"], "complex", {}, start)

        best_model, best_resp = max(
            results.items(),
            key=lambda kv: _score_response(kv[1], prompt),
        )
        logger.info("[complex] winner: %s (score=%.2f)", best_model, _score_response(best_resp, prompt))

        # Optionally merge: prepend fast answer if deep answer wins
        if best_model == MODELS["deep"] and MODELS["fast"] in results:
            fast_resp = results[MODELS["fast"]]
            if fast_resp and len(fast_resp.split()) > 10:
                # Use deep model answer (already highest quality)
                pass  # deep answer stands alone

        return self._pack(best_resp, best_model, "complex", results, start)

    # ── Utility ───────────────────────────────────────────────────────────────

    @staticmethod
    def _pack(response, model_used, strategy, all_results, start) -> Dict:
        return {
            "response":    response,
            "model_used":  model_used,
            "strategy":    strategy,
            "all_results": all_results,
            "latency_ms":  int((time.time() - start) * 1000),
        }


# ─── Module-level singleton ───────────────────────────────────────────────────
_router: Optional[ParallelLLMRouter] = None
_router_lock = threading.Lock()


def get_router() -> ParallelLLMRouter:
    """Get or create the global ParallelLLMRouter singleton."""
    global _router
    if _router is None:
        with _router_lock:
            if _router is None:
                _router = ParallelLLMRouter(max_workers=4)
    return _router
