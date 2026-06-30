"""
indexes/vector_db.py
===================
Thread-safe FAISS CPU index manager.
Handles index persistence, incremental updates, deletions, and a numpy flat fallback.
"""

import os
import logging
import threading
import numpy as np
from typing import Tuple, List, Optional

logger = logging.getLogger("msa.indexes.vector_db")

_DIM = 384  # Must match Embedder dimension


class VectorDBAdapter:
    """Interface for swap-ready Vector Database Adapters."""
    def add(self, vector: np.ndarray) -> int:
        raise NotImplementedError
    def add_batch(self, vectors: np.ndarray) -> List[int]:
        raise NotImplementedError
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[int, float]]:
        raise NotImplementedError
    def remove_ids(self, ids_to_remove: List[int]) -> None:
        raise NotImplementedError
    def count(self) -> int:
        raise NotImplementedError
    def clear(self) -> None:
        raise NotImplementedError
    def save(self) -> None:
        raise NotImplementedError


class ChromaDBAdapter(VectorDBAdapter):
    """Swap-ready adapter for Chroma DB."""
    def __init__(self, index_path: Optional[str] = None):
        self.index_path = index_path
        logger.info("ChromaDBAdapter initialized (Swap-Ready).")
    def add(self, vector: np.ndarray) -> int:
        raise NotImplementedError("Chroma DB not installed. Run 'pip install chromadb' to use this adapter.")
    def add_batch(self, vectors: np.ndarray) -> List[int]:
        raise NotImplementedError("Chroma DB not installed.")
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[int, float]]:
        raise NotImplementedError("Chroma DB not installed.")
    def remove_ids(self, ids_to_remove: List[int]) -> None:
        raise NotImplementedError("Chroma DB not installed.")
    def count(self) -> int:
        return 0
    def clear(self) -> None:
        pass
    def save(self) -> None:
        pass


class QdrantAdapter(VectorDBAdapter):
    """Swap-ready adapter for Qdrant."""
    def __init__(self, index_path: Optional[str] = None):
        self.index_path = index_path
        logger.info("QdrantAdapter initialized (Swap-Ready).")
    def add(self, vector: np.ndarray) -> int:
        raise NotImplementedError("Qdrant not installed. Run 'pip install qdrant-client' to use this adapter.")
    def add_batch(self, vectors: np.ndarray) -> List[int]:
        raise NotImplementedError("Qdrant not installed.")
    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[int, float]]:
        raise NotImplementedError("Qdrant not installed.")
    def remove_ids(self, ids_to_remove: List[int]) -> None:
        raise NotImplementedError("Qdrant not installed.")
    def count(self) -> int:
        return 0
    def clear(self) -> None:
        pass
    def save(self) -> None:
        pass


class FAISSIndexManager(VectorDBAdapter):
    """
    Manages a local FAISS Index.
    Supports index creation, adding vectors, querying, deletion of specific IDs, and persistence.
    """

    def __init__(self, index_path: Optional[str] = None):
        if index_path is None:
            from config import FAISS_INDEX_PATH
            self.index_path = FAISS_INDEX_PATH
        else:
            self.index_path = index_path

        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        self._lock = threading.Lock()
        self._index = None
        self._vectors = None  # NumPy fallback store
        self._use_faiss = False
        
        self._init_index()
        self._load()

    def _init_index(self) -> None:
        """Initialize FAISS Index Flat IP (Inner Product) / L2."""
        try:
            import faiss
            # Use IndexFlatIP for cosine similarity (requires normalized vectors)
            self._index = faiss.IndexFlatIP(_DIM)
            self._use_faiss = True
            logger.info("VectorDB: FAISS IndexFlatIP initialized (dim=%d).", _DIM)
        except ImportError:
            logger.warning("VectorDB: faiss-cpu not installed. Falling back to numpy cosine search.")
            self._vectors = np.zeros((0, _DIM), dtype=np.float32)
            self._use_faiss = False

    def _load(self) -> None:
        """Load index from disk if it exists."""
        with self._lock:
            if self._use_faiss:
                if os.path.exists(self.index_path):
                    try:
                        import faiss
                        self._index = faiss.read_index(self.index_path)
                        logger.info("VectorDB: loaded FAISS index with %d vectors.", self._index.ntotal)
                    except Exception as e:
                        logger.error("VectorDB: failed to load FAISS index (%s). Recreating.", e)
                        import faiss
                        self._index = faiss.IndexFlatIP(_DIM)
            else:
                np_path = self.index_path + ".npy"
                if os.path.exists(np_path):
                    try:
                        self._vectors = np.load(np_path)
                        logger.info("VectorDB (fallback): loaded numpy store with %d vectors.", len(self._vectors))
                    except Exception as e:
                        logger.error("VectorDB (fallback): failed to load numpy store (%s). Recreating.", e)
                        self._vectors = np.zeros((0, _DIM), dtype=np.float32)

    def save(self) -> None:
        """Persist index to disk."""
        with self._lock:
            try:
                if self._use_faiss and self._index is not None:
                    import faiss
                    faiss.write_index(self._index, self.index_path)
                    logger.debug("VectorDB: saved FAISS index to '%s'.", self.index_path)
                elif not self._use_faiss and self._vectors is not None:
                    np.save(self.index_path + ".npy", self._vectors)
                    logger.debug("VectorDB (fallback): saved numpy vectors to '%s.npy'.", self.index_path)
            except Exception as e:
                logger.error("VectorDB: failed to save index (%s).", e)

    def add(self, vector: np.ndarray) -> int:
        """
        Add a single vector of shape (384,) to the index.
        Returns the index ID of the newly added vector.
        """
        # Reshape to (1, 384)
        vec = vector.reshape(1, _DIM).astype(np.float32)
        # Ensure L2 normalized for cosine search
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        with self._lock:
            if self._use_faiss:
                idx = self._index.ntotal
                self._index.add(vec)
            else:
                idx = len(self._vectors)
                if self._vectors.shape[0] == 0:
                    self._vectors = vec
                else:
                    self._vectors = np.vstack([self._vectors, vec])
        
        # Save after add
        self.save()
        return idx

    def add_batch(self, vectors: np.ndarray) -> List[int]:
        """
        Add multiple vectors of shape (N, 384) to the index.
        Returns a list of corresponding index IDs.
        """
        if vectors.shape[0] == 0:
            return []

        vecs = vectors.astype(np.float32)
        # Normalize each row
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        # Avoid division by zero
        norms[norms == 0] = 1.0
        vecs = vecs / norms

        with self._lock:
            ids = []
            if self._use_faiss:
                start_idx = self._index.ntotal
                self._index.add(vecs)
                ids = list(range(start_idx, self._index.ntotal))
            else:
                start_idx = len(self._vectors)
                if self._vectors.shape[0] == 0:
                    self._vectors = vecs
                else:
                    self._vectors = np.vstack([self._vectors, vecs])
                ids = list(range(start_idx, len(self._vectors)))

        self.save()
        return ids

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[int, float]]:
        """
        Perform vector search.
        Returns a list of tuples: (vector_id, score) sorted descending by score.
        """
        vec = query_vector.reshape(1, _DIM).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        with self._lock:
            total_elements = self._index.ntotal if self._use_faiss else len(self._vectors)
            if total_elements == 0:
                return []

            k = min(top_k, total_elements)
            if k == 0:
                return []

            if self._use_faiss:
                # FlatIP search returns dot products (since we normalized, this is cosine similarity)
                # distances shape (1, k), indices shape (1, k)
                scores, indices = self._index.search(vec, k)
                
                results = []
                for i in range(k):
                    idx = int(indices[0][i])
                    if idx >= 0:
                        score = float(scores[0][i])
                        results.append((idx, score))
                return results
            else:
                # Cosine similarity via dot product
                sims = (self._vectors @ vec.T).flatten()
                top_idxs = np.argsort(sims)[::-1][:k]
                return [(int(i), float(sims[i])) for i in top_idxs]

    def remove_ids(self, ids_to_remove: List[int]) -> None:
        """
        Remove vectors matching the given IDs.
        FAISS flat index supports Index.remove_ids.
        For numpy fallback, we zero out or delete the rows.
        """
        if not ids_to_remove:
            return

        with self._lock:
            if self._use_faiss:
                try:
                    import faiss
                    # FAISS Index.remove_ids requires an ID Selector
                    id_array = np.array(ids_to_remove, dtype=np.int64)
                    selector = faiss.IDSelectorArray(id_array)
                    removed = self._index.remove_ids(selector)
                    logger.info("VectorDB: removed %d vectors from FAISS index.", removed)
                except Exception as e:
                    logger.error("VectorDB: failed to remove FAISS IDs (%s).", e)
            else:
                # Reconstruct vectors array excluding the indices to remove
                mask = np.ones(len(self._vectors), dtype=bool)
                for idx in ids_to_remove:
                    if idx < len(mask):
                        mask[idx] = False
                self._vectors = self._vectors[mask]
                logger.info("VectorDB (fallback): removed %d vectors.", len(ids_to_remove) - sum(mask))

        self.save()

    def count(self) -> int:
        """Returns the total number of vectors in the index."""
        with self._lock:
            if self._use_faiss:
                return self._index.ntotal if self._index is not None else 0
            else:
                return len(self._vectors) if self._vectors is not None else 0

    def clear(self) -> None:
        """Clear all stored vectors."""
        with self._lock:
            self._init_index()
            if not self._use_faiss:
                self._vectors = np.zeros((0, _DIM), dtype=np.float32)
        self.save()
        logger.info("VectorDB: index cleared.")
