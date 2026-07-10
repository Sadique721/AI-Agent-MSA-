"""
memory/conversation_summarizer.py
==================================
Periodically summarizes conversations in the background to prune short-term context
and persist structural summaries into the VectorStore.
"""
import logging
from typing import List, Dict

logger = logging.getLogger("msa.memory.summarizer")

_SUMMARIZE_TRIGGER_TURNS = 20  # summarize once conversation exceeds this many turns


class ConversationSummarizer:
    def __init__(self, llm_manager, rag_memory):
        self.llm = llm_manager
        self.rag_memory = rag_memory

    def maybe_summarize(self, conversation_id: str, history: List[Dict[str, str]]) -> None:
        """Call this from the background coordinator loop, not the request path."""
        if len(history) < _SUMMARIZE_TRIGGER_TURNS:
            return
        old_turns = history[:-10]  # keep the most recent 10 turns verbatim
        transcript = "\n".join(f"{t.get('role')}: {t.get('content')}" for t in old_turns)
        prompt = (
            f"Summarize this conversation into 3-5 bullet points capturing key "
            f"facts, decisions, and context that should be remembered:\n\n{transcript}"
        )
        try:
            summary = self.llm.generate(prompt, provider="ollama")
            if summary and hasattr(self.rag_memory, "remember"):
                self.rag_memory.remember(
                    f"[Conversation Summary - {conversation_id}]\n{summary}",
                    category="conversation_summary",
                )
                logger.info("Summarized and archived %d old turns for %s", len(old_turns), conversation_id)
        except Exception as e:
            logger.warning("Conversation summarization failed: %s", e)
