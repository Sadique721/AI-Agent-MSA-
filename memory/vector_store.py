"""
memory/vector_store.py
=======================
FAISS-backed vector store for semantic long-term memory.

Stores text embeddings alongside metadata (category, timestamp, content).
Persists index + metadata to disk so memory survives restarts.

Storage files:
    data/memory/msa_vectors.faiss       — FAISS binary index
    data/memory/msa_vectors_meta.json   — metadata list (JSON)

Usage:
    store = VectorStore()
    store.add("remember my Spring Boot CRUD project", {"category": "project"})
    results = store.search("do you remember my project?", top_k=3)
    # → [{"text": "...", "category": "project", "score": 0.95, ...}]
"""

import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("msa.memory.vector_store")

_DIM = 384  # Must match EmbeddingService.dim()


class VectorStore:
    """
    Thread-safe FAISS L2 vector index with JSON metadata sidecar.

    Falls back gracefully if faiss-cpu is not installed:
    uses brute-force numpy cosine search instead.
    """

    def __init__(
        self,
        index_path: str = "data/memory/msa_vectors.faiss",
        meta_path:  str = "data/memory/msa_vectors_meta.json",
        embedding_service=None,
    ):
        from config import PROJECT_ROOT
        self.index_path = os.path.join(PROJECT_ROOT, index_path)
        self.meta_path  = os.path.join(PROJECT_ROOT, meta_path)
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        self._lock      = threading.Lock()
        self._meta: List[Dict] = []
        self._embedder  = embedding_service  # injected or lazy-loaded
        self._index     = None               # FAISS index or numpy array
        self._use_faiss = False
        self._vectors: Optional[np.ndarray] = None  # fallback store

        self._init_index()
        self._load()

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_index(self) -> None:
        """Try FAISS; fall back to numpy brute-force."""
        try:
            import faiss
            self._index     = faiss.IndexFlatL2(_DIM)
            self._use_faiss = True
            logger.info("VectorStore: using FAISS IndexFlatL2 (dim=%d).", _DIM)
        except ImportError:
            logger.warning(
                "faiss-cpu not installed — using numpy brute-force search. "
                "Run: pip install faiss-cpu"
            )
            self._vectors   = np.zeros((0, _DIM), dtype=np.float32)
            self._use_faiss = False

    def _get_embedder(self):
        """Lazy-load embedding service if not injected."""
        if self._embedder is None:
            from memory.embedding_service import EmbeddingService
            self._embedder = EmbeddingService()
        return self._embedder

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load existing index + metadata from disk."""
        # Load metadata
        if os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self._meta = json.load(f)
                logger.info("VectorStore: loaded %d metadata entries.", len(self._meta))
            except Exception as e:
                logger.warning("VectorStore metadata load error: %s", e)
                self._meta = []

        # Load FAISS index
        if self._use_faiss and os.path.exists(self.index_path):
            try:
                import faiss
                self._index = faiss.read_index(self.index_path)
                logger.info(
                    "VectorStore: FAISS index loaded (%d vectors).",
                    self._index.ntotal,
                )
            except Exception as e:
                logger.warning("VectorStore FAISS load error: %s — rebuilding.", e)
                import faiss
                self._index = faiss.IndexFlatL2(_DIM)

        # Load numpy fallback vectors
        elif not self._use_faiss and self._meta:
            np_path = self.index_path + ".npy"
            if os.path.exists(np_path):
                try:
                    self._vectors = np.load(np_path)
                    logger.info(
                        "VectorStore: numpy fallback loaded (%d vectors).",
                        len(self._vectors),
                    )
                except Exception as e:
                    logger.warning("VectorStore numpy load error: %s", e)
                    self._vectors = np.zeros((0, _DIM), dtype=np.float32)

    def _save(self) -> None:
        """Persist index + metadata to disk."""
        try:
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(self._meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("VectorStore metadata save error: %s", e)

        if self._use_faiss:
            try:
                import faiss
                faiss.write_index(self._index, self.index_path)
            except Exception as e:
                logger.error("VectorStore FAISS save error: %s", e)
        else:
            try:
                np.save(self.index_path + ".npy", self._vectors)
            except Exception as e:
                logger.error("VectorStore numpy save error: %s", e)

    # ── Public API ────────────────────────────────────────────────────────────

    def add(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Embed and store text with optional metadata.

        Args:
            text:     The text to embed and store.
            metadata: Extra fields (category, source, etc.).

        Returns:
            Index ID of the stored vector.
        """
        embedder = self._get_embedder()
        vec = embedder.embed(text).reshape(1, _DIM)

        meta_entry = {
            "text":      text,
            "timestamp": datetime.now().isoformat(),
            **(metadata or {}),
        }

        with self._lock:
            idx = len(self._meta)

            if self._use_faiss:
                self._index.add(vec)
            else:
                self._vectors = np.vstack([self._vectors, vec]) \
                    if self._vectors.shape[0] > 0 else vec

            self._meta.append(meta_entry)
            self._save()

        logger.debug("VectorStore: added entry #%d — %r", idx, text[:60])
        return idx

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Semantic similarity search.

        Args:
            query:  Natural language query.
            top_k:  Number of top results to return.

        Returns:
            List of dicts with keys: text, score, timestamp, + metadata fields.
            Sorted by relevance (best first).
        """
        if not self._meta:
            return []

        embedder  = self._get_embedder()
        query_vec = embedder.embed(query).reshape(1, _DIM)

        with self._lock:
            n = min(top_k, len(self._meta))
            if n == 0:
                return []

            if self._use_faiss:
                distances, indices = self._index.search(query_vec, n)
                raw_results = [
                    (int(indices[0][i]), float(distances[0][i]))
                    for i in range(n)
                    if indices[0][i] >= 0
                ]
            else:
                # Cosine similarity via dot product (vectors are L2-normalised)
                sims = (self._vectors @ query_vec.T).flatten()
                top_idxs = np.argsort(sims)[::-1][:n]
                raw_results = [(int(i), float(1.0 - sims[i])) for i in top_idxs]

        results = []
        for idx, dist in raw_results:
            if idx < len(self._meta):
                entry = dict(self._meta[idx])
                # Convert L2 distance to similarity score (lower=better)
                entry["score"] = round(max(0.0, 1.0 - dist / 2.0), 4)
                results.append(entry)

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def count(self) -> int:
        """Return total number of stored vectors."""
        return len(self._meta)

    def clear(self) -> None:
        """Delete all stored vectors and metadata."""
        with self._lock:
            self._meta = []
            self._init_index()
            self._save()
        logger.info("VectorStore: cleared all entries.")

    def get_by_category(self, category: str) -> List[Dict]:
        """Return all entries matching a category."""
        return [m for m in self._meta if m.get("category") == category]
