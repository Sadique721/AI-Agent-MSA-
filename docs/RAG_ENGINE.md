# Hybrid RAG Engine Specification — MSA V5.0

This document defines the architecture and configurations of the RAG (Retrieval-Augmented Generation) search engine in MSA V5.0.

---

## 1. Hybrid Search Architecture

The RAG agent (`agent/rag_agent.py`) combines keyword search and semantic dense vector search to achieve maximum retrieval accuracy:

1. **BM25 Search:** Scores document matching terms.
2. **Dense Vector Search:** Encodes queries via `sentence-transformers` and searches vectors inside local FAISS indices.
3. **Score Re-ranking:** Normalizes and blends search scores:
   $$\text{hybrid\_score} = w_{\text{bm25}} \cdot S_{\text{bm25}} + w_{\text{dense}} \cdot S_{\text{dense}}$$

---

## 2. Dynamic Configurations (`config/rag.yaml`)

- `chunk_size`: 512 characters.
- `chunk_overlap`: 50 characters.
- `bm25_weight`: 0.4 vs `dense_weight`: 0.6.
- `faiss_index_path`: `data/memory/msa_vectors.faiss`.
