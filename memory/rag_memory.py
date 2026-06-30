"""
memory/rag_memory.py
=====================
RAG (Retrieval-Augmented Generation) Memory Adapter.
Keeps backward compatibility with original tests and modules, while under the hood
bridging to the advanced, production-grade HybridRetriever, Chunker, and SQLiteMetadataStore.
"""

import logging
import re
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import FAISS_INDEX_PATH
from embeddings.embedder import Embedder
from embeddings.reranker import Reranker
from indexes.sqlite_db import SQLiteMetadataStore
from indexes.vector_db import FAISSIndexManager
from knowledge.chunker import Chunker
from knowledge.retriever import HybridRetriever

logger = logging.getLogger("msa.memory.rag")

VALID_CATEGORIES = {
    "conversation", "task", "preference", "project", "coding", "fact",
    "coding_project", "coding_bug", "coding_review", "coding_reference",
    "coding_fix", "coding_template",
}


class RAGMemory:
    """
    Backward-compatible memory interface.
    Bridges existing calls to the upgraded Hybrid RAG subsystems.
    """

    def __init__(
        self,
        sqlite_memory=None,
        embedding_service=None,
        vector_store=None,
    ):
        self._sqlite = sqlite_memory  # Old SQLite memory instance
        self._initialized = False
        
        # Internal placeholders for upgraded subsystems
        self.embedder = None
        self.reranker = None
        self.vector_db = None
        self.metadata_db = None
        self.retriever = None
        self.chunker = None

        logger.info("RAGMemory created (legacy adapter).")

    def _ensure_init(self) -> None:
        """Initialize the new RAG subsystems if not already done."""
        if self._initialized:
            return

        # Initialize core upgraded modules
        self.embedder = Embedder()
        self.reranker = Reranker()
        self.vector_db = FAISSIndexManager()
        self.metadata_db = SQLiteMetadataStore()
        
        self.retriever = HybridRetriever(
            embedder=self.embedder,
            vector_db=self.vector_db,
            metadata_db=self.metadata_db,
            reranker=self.reranker
        )
        
        self.chunker = Chunker(embedder=self.embedder)
        self._initialized = True
        
        logger.info(
            "RAGMemory initialized with Hybrid retriever (vectors=%d, chunks=%d).",
            self.vector_db.count(),
            self.metadata_db.get_stats().get("total_chunks", 0)
        )

    def remember(self, text: str, category: str = "fact") -> bool:
        """
        Store text in the SQLite metadata store and FAISS vector store.
        """
        if not text or not text.strip():
            return False

        # Validate category
        from memory.rag_memory import VALID_CATEGORIES as LEGACY_CATEGORIES
        if category not in LEGACY_CATEGORIES:
            logger.warning("Unknown category %r — defaulting to 'fact'.", category)
            category = "fact"

        self._ensure_init()

        try:
            # Hash source based on text content since no file source is provided for raw remember calls
            import hashlib
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            pseudo_path = f"memory://remember_{text_hash[:16]}"
            
            # Chunk the content
            metadata = {
                "source": pseudo_path,
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "type": "remember_api"
            }
            chunks = self.chunker.chunk_document(text, metadata)

            for chunk in chunks:
                # Add vector
                vec = self.embedder.embed(chunk["text"])
                faiss_id = self.vector_db.add(vec)
                
                # Add metadata
                self.metadata_db.add_chunk(
                    faiss_id=faiss_id,
                    file_path=pseudo_path,
                    chunk_index=chunk["chunk_index"],
                    content=chunk["text"],
                    category=category,
                    tokens=chunk["tokens"],
                    timestamp=metadata["timestamp"],
                    metadata=metadata
                )
            
            logger.info("RAGMemory: remembered '%s' as %s.", text[:60], category)
        except Exception as e:
            logger.error("RAGMemory remember failed: %s", e)
            return False

        # Legacy persistence support for SQLite
        if self._sqlite:
            try:
                import hash_helper
            except ImportError:
                # Use standard hash fallback
                text_hash_code = hash(text)
            self._sqlite.remember_fact(f"rag:{category}:{text_hash_code}", text)

        return True

    def recall(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search memories using Hybrid Retrieval and Cross-Encoder Reranking.
        """
        if not query or not query.strip():
            return []

        self._ensure_init()

        try:
            results = self.retriever.retrieve(query, top_k=top_k)
            # Reformat to match the legacy output structure: [{text, category, score, timestamp}]
            legacy_results = []
            for r in results:
                legacy_results.append({
                    "text": r.get("text", r.get("content", "")),
                    "category": r.get("category", "fact"),
                    "score": r.get("score", 0.0),
                    "timestamp": r.get("timestamp", datetime.now().isoformat()),
                    "file_path": r.get("file_path", "")
                })
            return legacy_results
        except Exception as e:
            logger.error("RAGMemory recall failed: %s", e)
            return []

    def get_augmented_context(
        self, query: str, recent_limit: int = 5, semantic_limit: int = 3
    ) -> Dict[str, Any]:
        """
        Retrieves recent turns from SQLite and semantic context from the Hybrid Retriever.
        """
        self._ensure_init()

        # 1. Fetch recent SQLite context
        recent = []
        if self._sqlite:
            try:
                recent = self._sqlite.get_recent_context(limit=recent_limit)
            except Exception as e:
                logger.warning("RAGMemory SQLite context error: %s", e)

        # 2. Fetch semantic Hybrid Retriever context
        semantic = []
        try:
            raw_semantic = self.retriever.retrieve(query, top_k=semantic_limit)
            for r in raw_semantic:
                semantic.append({
                    "text": r.get("text", r.get("content", "")),
                    "category": r.get("category", "fact"),
                    "score": r.get("score", 0.0),
                    "timestamp": r.get("timestamp", datetime.now().isoformat())
                })
            # Filter out very low score hits (RRF score threshold check)
            semantic = [s for s in semantic if s.get("score", 0) >= 0.01]
        except Exception as e:
            logger.warning("RAGMemory semantic recall error: %s", e)

        # 3. Assemble combined context
        parts = []
        if recent:
            recent_text = " | ".join(
                f"User: {t.get('user','')} -> MSA: {t.get('assistant','')}"
                for t in recent[-3:]
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
            "recent": recent,
            "semantic": semantic,
            "combined": combined,
        }

    def remember_conversation(self, user_input: str, response: str) -> None:
        self.remember(f"User said: {user_input} | MSA replied: {response}", "conversation")

    def remember_project(self, description: str) -> None:
        self.remember(description, "project")

    def remember_preference(self, preference: str) -> None:
        self.remember(preference, "preference")

    def remember_code(self, code_description: str) -> None:
        self.remember(code_description, "coding")

    def stats(self) -> Dict[str, Any]:
        """Return memory statistics."""
        self._ensure_init()
        db_stats = self.metadata_db.get_stats()
        
        return {
            "total_vectors": self.vector_db.count(),
            "total_chunks": db_stats.get("total_chunks", 0),
            "total_files": db_stats.get("total_files", 0),
            "by_category": db_stats.get("by_category", {}),
            "semantic_enabled": self.embedder.is_semantic(),
            "backend": "FAISS" if self.vector_db._use_faiss else "numpy"
        }
