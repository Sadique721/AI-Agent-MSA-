"""
memory/embedding_service.py
============================
Offline semantic embedding service for RAG Memory.

Uses sentence-transformers/all-MiniLM-L6-v2 (384-dim, ~80 MB one-time download).
After first download the model runs fully offline.

Fallback: TF-IDF-style hash vectors (384-dim) if sentence-transformers
          is not installed — no external dependency required.

Usage:
    svc = EmbeddingService()
    vec = svc.embed("remember my Spring Boot project")
    # → numpy float32 array shape (384,)
"""

import os
import hashlib
import logging
import re
from typing import Any, List, Optional

import numpy as np

# Force offline mode for Hugging Face hub / transformers to prevent network hanging
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

logger = logging.getLogger("msa.memory.embedding")

_EMBED_DIM = 384   # all-MiniLM-L6-v2 output dimension


class EmbeddingService:
    """
    Converts text to dense float32 vectors for semantic similarity search.

    Primary  : sentence-transformers all-MiniLM-L6-v2 (offline after download)
    Fallback : Deterministic hash-based pseudo-embeddings (always works offline)
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model     = None
        self._use_st    = False
        self._init_model()

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_model(self) -> None:
        """Try to load sentence-transformers model; fall back gracefully."""
        try:
            from sentence_transformers import SentenceTransformer
            self._model  = SentenceTransformer(self.model_name)
            self._use_st = True
            logger.info(
                "EmbeddingService: sentence-transformers model loaded (%s).",
                self.model_name,
            )
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Using hash-based fallback embeddings. "
                "Run: pip install sentence-transformers"
            )
        except Exception as e:
            logger.error(
                "EmbeddingService: model load failed (%s). "
                "Using hash-based fallback.", e,
            )

    # ── Public API ────────────────────────────────────────────────────────────

    def embed(self, text: str) -> np.ndarray:
        """
        Convert text to a 384-dim float32 embedding vector.

        Args:
            text: Any string (command, fact, conversation turn).

        Returns:
            np.ndarray of shape (384,), dtype float32.
        """
        if not text or not text.strip():
            return np.zeros(_EMBED_DIM, dtype=np.float32)

        if self._use_st and self._model is not None:
            return self._st_embed(text)
        return self._hash_embed(text)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Embed a list of texts efficiently.

        Returns:
            np.ndarray of shape (N, 384), dtype float32.
        """
        if not texts:
            return np.zeros((0, _EMBED_DIM), dtype=np.float32)

        if self._use_st and self._model is not None:
            try:
                vecs = self._model.encode(
                    texts,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                )
                return vecs.astype(np.float32)
            except Exception as e:
                logger.error("Batch ST embed error: %s", e)

        return np.array(
            [self._hash_embed(t) for t in texts], dtype=np.float32
        )

    def is_semantic(self) -> bool:
        """Return True if using real sentence-transformers (not hash fallback)."""
        return self._use_st

    def dim(self) -> int:
        """Return embedding dimension."""
        return _EMBED_DIM

    # ── Internals ─────────────────────────────────────────────────────────────

    def _st_embed(self, text: str) -> np.ndarray:
        """Embed using sentence-transformers."""
        try:
            vec = self._model.encode(
                text,
                normalize_embeddings=True,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return vec.astype(np.float32)
        except Exception as e:
            logger.error("ST embed error: %s — using hash fallback", e)
            return self._hash_embed(text)

    def _hash_embed(self, text: str) -> np.ndarray:
        """
        Deterministic pseudo-embedding using SHA-256 seeded RNG.
        Consistent: same text always produces same vector.
        Captures some lexical overlap via token-level hashing.
        """
        tokens = re.split(r"\W+", text.lower())
        vec = np.zeros(_EMBED_DIM, dtype=np.float32)

        for i, token in enumerate(tokens):
            if not token:
                continue
            seed = int(hashlib.sha256(token.encode()).hexdigest(), 16) % (2 ** 32)
            rng  = np.random.default_rng(seed)
            token_vec = rng.standard_normal(_EMBED_DIM).astype(np.float32)
            # Weight by position (earlier tokens slightly more important)
            weight = 1.0 / (1.0 + i * 0.1)
            vec += weight * token_vec

        # L2-normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec
