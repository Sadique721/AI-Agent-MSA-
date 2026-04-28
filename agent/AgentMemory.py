"""
agent/AgentMemory.py
====================
Session-aware memory wrapper for the MSA Agent.

Wraps the encrypted SQLite Memory class and adds an in-memory
session context buffer so recent turns are available instantly
without decrypting from disk on every call.
"""
import logging
from typing import Dict, List

logger = logging.getLogger("msa.agent.memory")


class AgentMemory:
    """
    Two-tier memory:
      1. session_context  — fast in-RAM list of recent turns (current session)
      2. memory (SQLite)  — encrypted persistent store across sessions

    get_context() merges both, prioritising session turns.
    """

    def __init__(self, memory):
        """
        Args:
            memory: instance of memory.memory.Memory (encrypted SQLite store)
        """
        self.memory = memory
        self.session_context: List[Dict[str, str]] = []
        logger.info("AgentMemory initialised.")

    # ── Write ──────────────────────────────────────────────────────────────
    def add_turn(self, user_input: str, response: str, action: str) -> None:
        """Persist a conversation turn and add it to the session buffer."""
        # Persist to encrypted SQLite
        if self.memory:
            try:
                self.memory.add_conversation(user_input, response, action)
            except Exception as e:
                logger.warning("Memory persist error: %s", e)

        # Add to session buffer (keep last 20 turns)
        self.session_context.append({"user": user_input, "assistant": response})
        if len(self.session_context) > 20:
            self.session_context.pop(0)

    # ── Read ───────────────────────────────────────────────────────────────
    def get_context(self, limit: int = 5) -> List[Dict[str, str]]:
        """
        Return the last `limit` conversation pairs.
        Prefers session buffer (fast); falls back to SQLite for older turns.
        """
        if self.session_context:
            return self.session_context[-limit:]

        if self.memory:
            try:
                return self.memory.get_recent_context(limit=limit)
            except Exception as e:
                logger.warning("Memory read error: %s", e)

        return []

    # ── Stats ──────────────────────────────────────────────────────────────
    def get_stats(self) -> Dict:
        """Return memory statistics for the dashboard."""
        if self.memory:
            try:
                return self.memory.get_stats()
            except Exception as e:
                logger.warning("Memory stats error: %s", e)
        return {"total_conversations": len(self.session_context), "last_interaction": None}

    def session_length(self) -> int:
        """Number of turns in the current session."""
        return len(self.session_context)
