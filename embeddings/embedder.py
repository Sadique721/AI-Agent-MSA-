"""
embeddings/embedder.py
======================
Production-grade semantic embedding generation using SentenceTransformers.
Includes structured logging, execution timing metrics, and a robust deterministic fallback.
"""

import os
import time
import logging
import hashlib
import re
from typing import List
import numpy as np

# Force offline mode for Hugging Face hub / transformers to prevent network hanging
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

logger = logging.getLogger("msa.embeddings.embedder")

_EMBED_DIM = 384  # Dimension of all-MiniLM-L6-v2


class Embedder:
    """
    Handles text embedding generation.
    Tries loading all-MiniLM-L6-v2; falls back to hash-based vectors if unavailable.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._use_st = False
        self._init_model()

    def _init_model(self) -> None:
        """Load SentenceTransformer model with fallback."""
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._use_st = True
            logger.info("Embedder: loaded model '%s' successfully.", self.model_name)
        except Exception as e:
            logger.warning("Embedder model load failed (%s). Falling back to hash embeddings.", e)
            self._use_st = False

    def embed(self, text: str) -> np.ndarray:
        """
        Embed a single text string.
        Returns a float32 numpy array of shape (384,).
        """
        if not text or not text.strip():
            return np.zeros(_EMBED_DIM, dtype=np.float32)

        start_time = time.perf_counter()
        if self._use_st and self._model is not None:
            try:
                vec = self._model.encode(
                    text,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                duration = time.perf_counter() - start_time
                logger.debug("Embedder: single embedding generated in %.4fs", duration)
                return vec.astype(np.float32)
            except Exception as e:
                logger.error("SentenceTransformer embed error: %s. Using hash fallback.", e)

        # Fallback
        vec = self._hash_embed(text)
        duration = time.perf_counter() - start_time
        logger.debug("Embedder (fallback): single embedding generated in %.4fs", duration)
        return vec

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Embed a list of text strings efficiently.
        Returns a float32 numpy array of shape (len(texts), 384).
        """
        if not texts:
            return np.zeros((0, _EMBED_DIM), dtype=np.float32)

        start_time = time.perf_counter()
        if self._use_st and self._model is not None:
            try:
                vecs = self._model.encode(
                    texts,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    convert_to_numpy=True
                )
                duration = time.perf_counter() - start_time
                logger.info("Embedder: batch of %d embedded in %.4fs", len(texts), duration)
                return vecs.astype(np.float32)
            except Exception as e:
                logger.error("SentenceTransformer batch embed error: %s. Using hash fallback.", e)

        # Fallback
        vecs = np.array([self._hash_embed(t) for t in texts], dtype=np.float32)
        duration = time.perf_counter() - start_time
        logger.info("Embedder (fallback): batch of %d embedded in %.4fs", len(texts), duration)
        return vecs

    def dim(self) -> int:
        return _EMBED_DIM

    def is_semantic(self) -> bool:
        return self._use_st

    def _hash_embed(self, text: str) -> np.ndarray:
        """
        Deterministic seed-based hashing fallback (consistent with existing service).
        Allows offline operation without external models.
        """
        tokens = re.split(r"\W+", text.lower())
        vec = np.zeros(_EMBED_DIM, dtype=np.float32)

        for i, token in enumerate(tokens):
            if not token:
                continue
            seed = int(hashlib.sha256(token.encode()).hexdigest(), 16) % (2 ** 32)
            rng = np.random.default_rng(seed)
            token_vec = rng.standard_normal(_EMBED_DIM).astype(np.float32)
            weight = 1.0 / (1.0 + i * 0.1)
            vec += weight * token_vec

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec
