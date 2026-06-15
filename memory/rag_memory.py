"""
memory/rag_memory.py
=====================
RAG (Retrieval-Augmented Generation) Memory — combines SQLite + FAISS.

Provides:
  - remember(text, category)      → store in both SQLite and FAISS
  - recall(query, top_k)          → semantic FAISS search
  - get_augmented_context(query)  → merges recent SQLite + semantic FAISS hits

Categories:
    "conversation"   — chat history turns
    "task"           — completed tasks
    "preference"     — user preferences/settings
    "project"        — project details (Spring Boot, etc.)
    "coding"         — code snippets, patterns
    "fact"           — standalone facts to remember

Usage:
    rag = RAGMemory()
    rag.remember("My Spring Boot project uses MySQL and REST APIs", "project")
    results = rag.recall("tell me about my project")
    context = rag.get_augmented_context("do you remember my Spring Boot project?")
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("msa.memory.rag")

VALID_CATEGORIES = {
    "conversation", "task", "preference", "project", "coding", "fact",
    "coding_project", "coding_bug", "coding_review", "coding_reference",
    "coding_fix", "coding_template",
}


class RAGMemory:
    """
    Long-term semantic memory combining SQLite persistence and FAISS search.

    Args:
        sqlite_memory:      Existing Memory (SQLite) instance — optional.
        embedding_service:  EmbeddingService instance — optional (lazy-loaded).
        vector_store:       VectorStore instance — optional (lazy-loaded).
    """

    def __init__(
        self,
        sqlite_memory=None,
        embedding_service=None,
        vector_store=None,
    ):
        self._sqlite  = sqlite_memory        # memory.memory.Memory
        self._embedder = embedding_service   # memory.embedding_service.EmbeddingService
        self._store    = vector_store        # memory.vector_store.VectorStore
        self._initialized = False
        logger.info("RAGMemory created (lazy init).")

    # ── Lazy init ─────────────────────────────────────────────────────────────

    def _ensure_init(self) -> None:
        if self._initialized:
            return
        if self._embedder is None:
            from memory.embedding_service import EmbeddingService
            self._embedder = EmbeddingService()
        if self._store is None:
            from memory.vector_store import VectorStore
            self._store = VectorStore(embedding_service=self._embedder)
        self._initialized = True
        logger.info(
            "RAGMemory initialized (semantic=%s, vectors=%d).",
            self._embedder.is_semantic() if self._embedder else False,
            self._store.count() if self._store else 0,
        )

    # ── Primary API ───────────────────────────────────────────────────────────

    def remember(self, text: str, category: str = "fact") -> bool:
        """
        Store text in both SQLite (if available) and FAISS vector store.

        Args:
            text:     The content to remember.
            category: One of VALID_CATEGORIES.

        Returns:
            True if successfully stored.
        """
        if not text or not text.strip():
            return False

        if category not in VALID_CATEGORIES:
            logger.warning("Unknown category %r — defaulting to 'fact'.", category)
            category = "fact"

        self._ensure_init()

        # Store in FAISS vector store
        try:
            self._store.add(text, {"category": category})
            logger.info("RAGMemory.remember: stored [%s] %r", category, text[:60])
        except Exception as e:
            logger.error("RAGMemory vector store error: %s", e)
            return False

        # Also persist to SQLite if available
        if self._sqlite:
            try:
                self._sqlite.remember_fact(
                    f"rag:{category}:{hash(text)}", text
                )
            except Exception as e:
                logger.warning("RAGMemory SQLite persist error: %s", e)

        return True

    def recall(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Semantic similarity search over stored memories.

        Args:
            query:  Natural language query.
            top_k:  Max results to return.

        Returns:
            List of dicts sorted by relevance score (descending).
            Each dict: {text, category, score, timestamp}
        """
        if not query or not query.strip():
            return []

        self._ensure_init()

        try:
            results = self._store.search(query, top_k=top_k)
            logger.info(
                "RAGMemory.recall: query=%r → %d results.", query[:50], len(results)
            )
            return results
        except Exception as e:
            logger.error("RAGMemory recall error: %s", e)
            return []

    def get_augmented_context(
        self, query: str, recent_limit: int = 5, semantic_limit: int = 3
    ) -> Dict[str, Any]:
        """
        Build an augmented context merging recent SQLite history
        and semantically relevant FAISS memories.

        Args:
            query:          Current user query.
            recent_limit:   Number of recent SQLite turns to include.
            semantic_limit: Number of semantic FAISS matches to include.

        Returns:
            {
                "recent":   [{"user": ..., "assistant": ...}],  # SQLite turns
                "semantic": [{"text": ..., "score": ..., ...}], # FAISS hits
                "combined": str  # Single context string for LLM prompt
            }
        """
        self._ensure_init()

        # ── Recent SQLite context ─────────────────────────────────────────────
        recent = []
        if self._sqlite:
            try:
                recent = self._sqlite.get_recent_context(limit=recent_limit)
            except Exception as e:
                logger.warning("RAGMemory SQLite context error: %s", e)

        # ── Semantic FAISS context ────────────────────────────────────────────
        semantic = []
        try:
            semantic = self._store.search(query, top_k=semantic_limit)
            # Filter out low-relevance hits (score < 0.3)
            semantic = [s for s in semantic if s.get("score", 0) >= 0.3]
        except Exception as e:
            logger.warning("RAGMemory semantic recall error: %s", e)

        # ── Build combined context string ─────────────────────────────────────
        parts = []
        if recent:
            recent_text = " | ".join(
                f"User: {t.get('user','')} → MSA: {t.get('assistant','')}"
                for t in recent[-3:]  # Last 3 turns only
            )
            parts.append(f"Recent conversation: {recent_text}")

        if semantic:
            sem_text = " | ".join(
                f"[{r.get('category','fact')}] {r['text']}"
                for r in semantic
            )
            parts.append(f"Relevant memories: {sem_text}")

        combined = "\n".join(parts) if parts else ""

        return {
            "recent":   recent,
            "semantic": semantic,
            "combined": combined,
        }

    def remember_conversation(self, user_input: str, response: str) -> None:
        """Convenience: store a conversation turn in vector memory."""
        text = f"User said: {user_input} | MSA replied: {response}"
        self.remember(text, "conversation")

    def remember_project(self, description: str) -> None:
        """Convenience: store a project description."""
        self.remember(description, "project")

    def remember_preference(self, preference: str) -> None:
        """Convenience: store a user preference."""
        self.remember(preference, "preference")

    def remember_code(self, code_description: str) -> None:
        """Convenience: store a coding memory."""
        self.remember(code_description, "coding")

    def stats(self) -> Dict[str, Any]:
        """Return memory statistics."""
        self._ensure_init()
        total = self._store.count() if self._store else 0
        by_cat = {}
        for cat in VALID_CATEGORIES:
            by_cat[cat] = len(self._store.get_by_category(cat)) if self._store else 0

        return {
            "total_vectors":    total,
            "by_category":      by_cat,
            "semantic_enabled": self._embedder.is_semantic() if self._embedder else False,
            "backend":          "FAISS" if (self._store and self._store._use_faiss) else "numpy",
        }
