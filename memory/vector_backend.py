"""
memory/vector_backend.py
=========================
Abstraction layer managing the default FAISS vector backend with opt-in Qdrant adapter.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger("msa.memory.vector_backend")


def get_vector_backend(config):
    """
    Returns a vector store instance based on config.VECTOR_BACKEND.
    Default remains FAISS (always works, no extra services needed).
    Qdrant is opt-in for users who want it and have it running locally
    (e.g. via `docker run -p 6333:6333 qdrant/qdrant` — still 100% local).
    """
    backend = getattr(config, "VECTOR_BACKEND", "faiss").lower()

    if backend == "qdrant":
        try:
            from qdrant_client import QdrantClient
            client = QdrantClient(host="localhost", port=6333)
            client.get_collections()  # verify it's actually reachable
            logger.info("Vector backend: Qdrant (local, port 6333)")
            return _QdrantAdapter(client)
        except Exception as e:
            logger.warning("Qdrant requested but unavailable (%s) - falling back to FAISS.", e)

    # Default / fallback: existing FAISS-based VectorStore, unchanged
    from memory.vector_store import VectorStore
    logger.info("Vector backend: FAISS (default)")
    return VectorStore()


class _QdrantAdapter:
    """Thin adapter so the rest of the app can call .add()/.search() the same way regardless of backend."""
    def __init__(self, client):
        self.client = client
        self.collection = "msa_memory"
        self._ensure_collection()

    def _ensure_collection(self):
        from qdrant_client.models import Distance, VectorParams
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection not in existing:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

    def add(self, vector: List[float], payload: Dict[str, Any] = None) -> int:
        from qdrant_client.models import PointStruct
        import uuid
        point_id = str(uuid.uuid4())
        self.client.upsert(
            collection_name=self.collection,
            points=[PointStruct(id=point_id, vector=vector, payload=payload or {})],
        )
        return point_id

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        results = self.client.search(
            collection_name=self.collection, query_vector=query_vector, limit=top_k
        )
        return [{"score": r.score, **(r.payload or {})} for r in results]
