# RAG Engine — MSA AI Agent V4.5

Details dense semantic searches, sparse BM25 indices, and reranking parameters.

## Retrieval Strategy

- **FAISS Vectors**: Computes text embeddings using `all-MiniLM-L6-v2` for dense semantic extraction.
- **SQLite Metadata**: Runs word match filtering using SQLite sparse queries.
- **Reranker Pipeline**: Leverages cross-encoders to rank candidate chunks and select top-K components for injection.
- **Cache**: Caches FAISS vectors in memory to save execution latency.
