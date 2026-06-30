"""
agent/AgentMemory.py
====================
Session-aware memory wrapper for the MSA Agent.
Delegates all core persistent, working, and semantic caching memory operations
to the advanced MemoryAgent orchestrator.
"""
import logging
from typing import Dict, List, Any, Optional
from agent.MemoryAgent import MemoryAgent

logger = logging.getLogger("msa.agent.memory")


class AgentMemory:
    """
    Two-tier memory delegator:
      1. session_context  — fast in-RAM list of recent turns (current session)
      2. MemoryAgent      — advanced persistent, working, semantic, and Graph RAG stores
    """

    def __init__(self, memory):
        """
        Args:
            memory: instance of memory.memory.Memory (encrypted SQLite store)
        """
        self.memory = memory
        self.session_context: List[Dict[str, str]] = []
        self.memory_agent = MemoryAgent(sqlite_memory=memory)
        logger.info("AgentMemory initialised with advanced MemoryAgent delegate.")

    # ── Write ──────────────────────────────────────────────────────────────
    def add_turn(self, user_input: str, response: str, action: str) -> None:
        """Persist a conversation turn and add it to the session buffer."""
        # Persist to encrypted SQLite
        if self.memory:
            try:
                self.memory.add_conversation(user_input, response, action)
            except Exception as e:
                logger.warning("Memory persist error: %s", e)

        # Also store turn in semantic memory via MemoryAgent
        turn_text = f"User: {user_input} | Assistant: {response}"
        self.memory_agent.remember(turn_text, category="conversation", importance=0.4)

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
        """Return combined memory agent and database statistics."""
        try:
            stats = self.memory_agent.get_stats()
            if self.memory:
                db_stats = self.memory.get_stats()
                stats["total_conversations"] = db_stats.get("total_conversations", 0)
            return stats
        except Exception as e:
            logger.warning("Memory stats retrieval failed (%s)", e)
            return {
                "total_conversations": len(self.session_context),
                "last_interaction": None
            }

    def session_length(self) -> int:
        """Number of turns in the current session."""
        return len(self.session_context)

    # ── MemoryAgent Delegation Helpers ──
    def remember(self, text: str, category: str = "fact", importance: float = 0.5) -> bool:
        return self.memory_agent.remember(text, category, importance)

    def recall(self, query: str, top_k: int = 5, category: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.memory_agent.recall(query, top_k, category)

    def add_working_memory(self, key: str, value: Any) -> None:
        self.memory_agent.add_working_memory(key, value)

    def get_working_memory(self, key: str, default: Any = None) -> Any:
        return self.memory_agent.get_working_memory(key, default)
