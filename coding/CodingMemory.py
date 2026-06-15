"""
coding/CodingMemory.py
======================
Saves and recalls coding-related project, bug, review, and template details.
"""

import logging
from typing import Dict, Any, List
from memory.rag_memory import RAGMemory

logger = logging.getLogger("msa.coding.memory")

class CodingMemory:
    """
    Manages coding-specific memory.
    Integrates with FAISS + SQLite via RAGMemory.
    Categories:
      - coding_project
      - coding_fix
      - coding_review
      - coding_reference
      - coding_template
    """
    def __init__(self, sqlite_memory=None):
        self.rag = RAGMemory(sqlite_memory=sqlite_memory)

    def store(self, prompt: str, result: Dict[str, Any], category: str) -> bool:
        """
        Stores a generated code or analysis result in memory.
        """
        if not prompt or not prompt.strip():
            return False
        explanation = result.get("explanation") or result.get("suggestion") or result.get("fix") or ""
        text = f"Prompt: {prompt} | Response: {explanation}"
        return self.rag.remember(text, category)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves relevant coding-related items from memory.
        """
        return self.rag.recall(query, top_k=top_k)

    def stats(self) -> Dict[str, Any]:
        """
        Returns memory statistics.
        """
        return self.rag.stats()
