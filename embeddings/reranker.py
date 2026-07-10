"""
embeddings/reranker.py
======================
Production-grade Cross-Encoder reranker.
Reranks retrieved document chunks using BAAI/bge-reranker-base.
Falls back to semantic score / BM25 combined scoring if Cross-Encoder fails or is disabled.
"""

import os
import time
import logging
from typing import Any, Dict, List, Set, Tuple

# Force offline mode for Hugging Face hub / transformers to prevent network hanging
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

logger = logging.getLogger("msa.embeddings.reranker")


class Reranker:
    """
    Reranks retrieved candidate documents using a Cross-Encoder.
    Optimizes semantic alignment and helps avoid the 'lost in the middle' issue.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-base", enabled: bool = True):
        self.model_name = model_name
        self.enabled = enabled
        self._model = None
        self._loaded = False
        if self.enabled:
            self._init_model()

    def _init_model(self) -> None:
        """Load CrossEncoder model lazily/safely."""
        try:
            from sentence_transformers import CrossEncoder
            # Set max_length to 512 for reranker
            self._model = CrossEncoder(self.model_name)
            self._loaded = True
            logger.info("Reranker: loaded Cross-Encoder '%s' successfully.", self.model_name)
        except Exception as e:
            logger.warning(
                "Reranker: Cross-Encoder load failed (%s). "
                "Using fallback similarity-based soft reranker.",
                e
            )
            self._loaded = False

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Rerank retrieved chunks with the Cross-Encoder.
        Each candidate is expected to have 'text', and optionally 'score'.
        """
        if not candidates:
            return []

        start_time = time.perf_counter()

        if self.enabled and self._loaded and self._model is not None:
            try:
                pairs = [(query, c.get("text", "")) for c in candidates]
                # Predict cross-encoder scores (higher is better)
                scores = self._model.predict(pairs)
                
                # Apply scores to candidates
                reranked = []
                for idx, score in enumerate(scores):
                    cand = dict(candidates[idx])
                    # Store original score as retrieve_score, replace score with reranked score
                    cand["retrieve_score"] = cand.get("score", 0.0)
                    # Normalize cross encoder score (sigmoid or raw, bge-reranker usually outputs raw logit)
                    # Sigmoid for raw score: 1 / (1 + exp(-score))
                    import math
                    try:
                        norm_score = 1.0 / (1.0 + math.exp(-float(score)))
                    except Exception:
                        norm_score = float(score)
                    cand["score"] = round(norm_score, 4)
                    reranked.append(cand)

                # Sort by reranked score
                reranked.sort(key=lambda x: x["score"], reverse=True)
                duration = time.perf_counter() - start_time
                logger.info("Reranker: reranked %d chunks in %.4fs", len(candidates), duration)
                return reranked[:top_k]
            except Exception as e:
                logger.error("Reranker prediction error: %s. Using fallback.", e)

        # Fallback soft reranking
        # Sort candidates using a combination of their lexical overlap and original similarity score
        reranked = []
        query_words = set(query.lower().split())
        
        for cand in candidates:
            c = dict(cand)
            text = c.get("text", "").lower()
            overlap = sum(1 for w in query_words if w in text)
            overlap_ratio = overlap / len(query_words) if query_words else 0.0
            
            # Combine original score (usually 0.0-1.0) and lexical overlap ratio
            original_score = c.get("score", 0.5)
            c["retrieve_score"] = original_score
            # Combined score: 70% dense + 30% lexical overlap
            c["score"] = round(0.7 * original_score + 0.3 * overlap_ratio, 4)
            reranked.append(c)

        reranked.sort(key=lambda x: x["score"], reverse=True)
        duration = time.perf_counter() - start_time
        logger.debug("Reranker (fallback): soft reranked in %.4fs", duration)
        return reranked[:top_k]
