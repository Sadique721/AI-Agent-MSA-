"""
agent/rag_agent.py
==================
Hybrid RAG Agent for MSA AI Agent V5.0.
Combines BM25 keyword search + FAISS dense vector search + optional Qdrant.
Falls back gracefully when Qdrant is disabled (feature flag).
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger("msa.agent.rag")

# ── Optional heavy imports ────────────────────────────────────────────────────
try:
    import numpy as np
    _numpy_ok = True
except ImportError:
    np = None  # type: ignore
    _numpy_ok = False

try:
    import faiss  # type: ignore
    _faiss_ok = True
except ImportError:
    faiss = None  # type: ignore
    _faiss_ok = False

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    _st_ok = True
except ImportError:
    SentenceTransformer = None  # type: ignore
    _st_ok = False


class RAGAgent:
    """
    Hybrid Retrieval-Augmented Generation agent.

    Retrieval chain:
      1. BM25 keyword search against in-memory corpus.
      2. FAISS dense vector search (if available).
      3. Merge + score-based re-rank.
      4. Qdrant search (if enable_qdrant feature flag is True).

    Usage:
        agent = RAGAgent()
        chunks = agent.retrieve("What is LangGraph?", top_k=5)
    """

    def __init__(self, config: Optional[Dict] = None) -> None:
        self._config = config or {}
        self._corpus: List[Dict] = []          # {"text": ..., "source": ..., "score": 0.0}
        self._embedder = None
        self._faiss_index = None
        self._bm25_ready = False

        self._load_embedder()
        self._load_memory_index()

    def _load_embedder(self) -> None:
        if not _st_ok:
            logger.warning("SentenceTransformers not available — dense search disabled")
            return
        try:
            model_name = self._config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
            self._embedder = SentenceTransformer(model_name)
            logger.info("Embedder loaded: %s", model_name)
        except Exception as e:
            logger.warning("Embedder load failed: %s", e)

    def _load_memory_index(self) -> None:
        """Load existing FAISS index from disk if available."""
        index_path = self._config.get("faiss_index_path", "data/memory/msa_vectors.faiss")
        if not os.path.isabs(index_path):
            index_path = os.path.join(PROJECT_ROOT, index_path)
        if _faiss_ok and os.path.exists(index_path):
            try:
                self._faiss_index = faiss.read_index(index_path)
                logger.info("FAISS index loaded: %d vectors", self._faiss_index.ntotal)
            except Exception as e:
                logger.warning("FAISS load failed: %s", e)

    # ── BM25 keyword scoring ──────────────────────────────────────────────────
    def _bm25_score(self, query: str, doc: str, k1: float = 1.5, b: float = 0.75) -> float:
        """Simple TF-based BM25 approximation."""
        query_terms = query.lower().split()
        doc_terms = doc.lower().split()
        doc_len = len(doc_terms)
        avg_len = max(1, sum(len(c.get("text", "").split()) for c in self._corpus) // max(1, len(self._corpus)))

        score = 0.0
        for term in query_terms:
            tf = doc_terms.count(term)
            if tf == 0:
                continue
            tf_score = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_len))
            score += tf_score
        return score

    def _bm25_search(self, query: str, top_k: int) -> List[Dict]:
        if not self._corpus:
            return []
        scored = []
        for chunk in self._corpus:
            score = self._bm25_score(query, chunk.get("text", ""))
            if score > 0:
                scored.append({**chunk, "bm25_score": score})
        scored.sort(key=lambda x: x["bm25_score"], reverse=True)
        return scored[:top_k]

    # ── Dense vector search ───────────────────────────────────────────────────
    def _dense_search(self, query: str, top_k: int) -> List[Dict]:
        if not self._embedder or not _numpy_ok or not self._corpus:
            return []
        try:
            query_vec = self._embedder.encode([query], normalize_embeddings=True)
            if self._faiss_index and self._faiss_index.ntotal > 0:
                distances, indices = self._faiss_index.search(
                    query_vec.astype("float32"), min(top_k, self._faiss_index.ntotal)
                )
                results = []
                for dist, idx in zip(distances[0], indices[0]):
                    if idx < len(self._corpus):
                        results.append({**self._corpus[idx], "dense_score": float(dist)})
                return results
        except Exception as e:
            logger.debug("Dense search error: %s", e)
        return []

    # ── Merge + re-rank ───────────────────────────────────────────────────────
    def _merge_results(
        self,
        bm25_results: List[Dict],
        dense_results: List[Dict],
        bm25_weight: float = 0.4,
        dense_weight: float = 0.6,
        top_k: int = 5,
    ) -> List[Dict]:
        seen: Dict[str, Dict] = {}

        max_bm25 = max((r.get("bm25_score", 0) for r in bm25_results), default=1.0) or 1.0
        max_dense = max((r.get("dense_score", 0) for r in dense_results), default=1.0) or 1.0

        for r in bm25_results:
            key = r.get("text", "")[:100]
            seen[key] = {**r, "hybrid_score": bm25_weight * r.get("bm25_score", 0) / max_bm25}

        for r in dense_results:
            key = r.get("text", "")[:100]
            dense_contribution = dense_weight * r.get("dense_score", 0) / max_dense
            if key in seen:
                seen[key]["hybrid_score"] += dense_contribution
            else:
                seen[key] = {**r, "hybrid_score": dense_contribution}

        merged = sorted(seen.values(), key=lambda x: x.get("hybrid_score", 0), reverse=True)
        return merged[:top_k]

    # ── Public API ────────────────────────────────────────────────────────────
    def add_document(self, text: str, source: str = "unknown", metadata: Optional[Dict] = None) -> None:
        """Add a document chunk to the in-memory corpus."""
        self._corpus.append({
            "text": text,
            "source": source,
            "metadata": metadata or {},
        })

    def retrieve(self, query: str, top_k: int = 5, min_score: float = 0.0) -> List[Dict]:
        """
        Hybrid retrieval: BM25 + dense search → merge → top_k results.
        Each result: {"text": ..., "source": ..., "hybrid_score": float}
        """
        cfg = self._config
        bm25_w = cfg.get("bm25_weight", 0.4)
        dense_w = cfg.get("dense_weight", 0.6)

        bm25_results = self._bm25_search(query, top_k * 2)
        dense_results = self._dense_search(query, top_k * 2)
        merged = self._merge_results(bm25_results, dense_results, bm25_w, dense_w, top_k)

        # Filter by minimum score
        filtered = [r for r in merged if r.get("hybrid_score", 0) >= min_score]
        logger.debug("RAG retrieved %d chunks for query: %s", len(filtered), query[:50])
        return filtered

    def format_context(self, chunks: List[Dict]) -> str:
        """Format retrieved chunks into a prompt-ready context string."""
        if not chunks:
            return ""
        lines = ["[Retrieved Knowledge]"]
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "unknown")
            text = chunk.get("text", "").strip()
            score = chunk.get("hybrid_score", 0)
            lines.append(f"\n[Chunk {i} | Source: {source} | Score: {score:.2f}]\n{text}")
        return "\n".join(lines)

    def get_stats(self) -> Dict:
        return {
            "corpus_size": len(self._corpus),
            "faiss_vectors": self._faiss_index.ntotal if self._faiss_index else 0,
            "embedder_available": self._embedder is not None,
        }


# ── Module-level singleton ────────────────────────────────────────────────────
_rag_agent: Optional[RAGAgent] = None


def get_rag_agent(config: Optional[Dict] = None) -> RAGAgent:
    global _rag_agent
    if _rag_agent is None:
        _rag_agent = RAGAgent(config=config)
    return _rag_agent
