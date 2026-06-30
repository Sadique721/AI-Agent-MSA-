import logging
from typing import Dict, List, Any, Optional
from infrastructure.service_registry import BaseService

logger = logging.getLogger("msa.memory.store")

class MemoryStore(BaseService):
    """Repository abstraction layer for persistent SQLite memory, preferences and profile data."""
    def __init__(self, raw_sqlite_memory: Any):
        super().__init__()
        self.db = raw_sqlite_memory
        logger.info("MemoryStore repository initialised.")

    def save_preference(self, key: str, value: str) -> None:
        """Saves a preference key-value pair."""
        if self.db:
            try:
                self.db.set_preference(key, value)
            except Exception as e:
                logger.error("Failed to save preference '%s': %s", key, e)

    def get_preference(self, key: str) -> Optional[str]:
        """Retrieves a preference value."""
        if self.db:
            try:
                return self.db.get_preference(key)
            except Exception as e:
                logger.error("Failed to retrieve preference '%s': %s", key, e)
        return None

    def get_recent_turns(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent conversation turns from the SQLite database."""
        if self.db:
            try:
                return self.db.get_recent_context(limit=limit)
            except Exception as e:
                logger.error("Failed to retrieve recent context: %s", e)
        return []

    def get_all_facts(self) -> Dict[str, str]:
        """Retrieves all stored facts from the RAGMemory table."""
        if self.db:
            try:
                if hasattr(self.db, "get_all_facts"):
                    return self.db.get_all_facts()
            except Exception as e:
                logger.error("Failed to retrieve RAGMemory facts: %s", e)
        return {}
