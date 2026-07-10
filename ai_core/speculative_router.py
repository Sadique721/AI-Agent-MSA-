"""
ai_core/speculative_router.py
==============================
Speculative routing: fast model answers first (shown to user immediately),
then optionally a bigger model refines it — SEQUENTIALLY, not in parallel,
to avoid doubling peak memory usage on constrained hardware.
"""
import logging
from typing import Optional, Callable
from ai_core.llm_manager import LLMManager

logger = logging.getLogger("msa.speculative_router")


class SpeculativeRouter:
    def __init__(self, llm_manager: LLMManager, fast_model: str, deep_model: Optional[str] = None):
        self.llm = llm_manager
        self.fast_model = fast_model
        self.deep_model = deep_model  # None if hardware can't support a second model

    def answer(self, prompt: str, stream_callback: Optional[Callable[[str], None]] = None,
               refine: bool = False) -> str:
        # Step 1: fast model answers immediately (always happens)
        self.llm.default_model = self.fast_model
        fast_answer = self.llm.generate(prompt, provider="ollama", stream_callback=stream_callback)

        # Step 2: optional deep refinement — only if explicitly requested AND
        # a deep model is configured AND hardware allows it (checked at init).
        if refine and self.deep_model:
            refine_prompt = (
                f"A fast draft answer was given: \"{fast_answer}\"\n\n"
                f"Original question: {prompt}\n\n"
                f"Verify this draft for correctness and improve it if needed. "
                f"If it's already correct, repeat it unchanged."
            )
            self.llm.default_model = self.deep_model
            try:
                refined = self.llm.generate(refine_prompt, provider="ollama")
                return refined or fast_answer
            except Exception as e:
                logger.warning("Deep refinement failed, keeping fast answer: %s", e)
                return fast_answer
        return fast_answer
