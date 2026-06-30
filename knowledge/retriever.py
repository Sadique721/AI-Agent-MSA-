"""
knowledge/retriever.py
======================
Production-grade Hybrid Retriever.
Combines Dense Semantic Search (FAISS) and Sparse Keyword Search (SQLite text BM25-style scoring)
using Reciprocal Rank Fusion (RRF), followed by Cross-Encoder Reranking.
Integrates Multi-Query variations, Parent-Child chunk resolution, Metadata Filtering, and Graph RAG.
"""

import time
import logging
import math
import collections
import re
from typing import List, Dict, Any, Optional

from embeddings.embedder import Embedder
from embeddings.reranker import Reranker
from indexes.vector_db import FAISSIndexManager
from indexes.sqlite_db import SQLiteMetadataStore
from knowledge.query_processor import QueryProcessor
from knowledge.graph_rag import GraphRAGEngine

logger = logging.getLogger("msa.knowledge.retriever")


class HybridRetriever:
    """
    Orchestrates dense + sparse search, multi-query expansion, RRF merging, parent-child expansion,
    metadata filtering, and Knowledge Graph-augmented retrieval.
    """

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        vector_db: Optional[FAISSIndexManager] = None,
        metadata_db: Optional[SQLiteMetadataStore] = None,
        reranker: Optional[Reranker] = None,
        query_processor: Optional[QueryProcessor] = None,
        graph_engine: Optional[GraphRAGEngine] = None
    ):
        self.embedder = embedder or Embedder()
        self.vector_db = vector_db or FAISSIndexManager()
        self.metadata_db = metadata_db or SQLiteMetadataStore()
        self.reranker = reranker or Reranker()
        self.query_processor = query_processor or QueryProcessor()
        self.graph_engine = graph_engine or GraphRAGEngine(graph_store=None)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        source: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        rrf_constant: int = 60,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
        enable_graph: bool = True,
        enable_multi_query: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute Hybrid Retrieval with Multi-Query, Parent-Child merge, and Graph RAG integration.
        """
        if not query or not query.strip():
            return []

        # 1. Query Rewrite and Multi-Query Processing
        target_queries = [query]
        if enable_multi_query and self.query_processor:
            try:
                # Rewrite query based on context, then generate variations
                rewritten = self.query_processor.rewrite_query(query)
                target_queries = self.query_processor.generate_multi_queries(rewritten, count=3)
            except Exception as e:
                logger.warning("Query processor failed inside retriever (%s).", e)

        start_time = time.perf_counter()
        all_candidates = {}

        # 2. Retrieve for each query variation
        for q in target_queries:
            q_candidates = self._retrieve_single(
                q,
                top_k=top_k * 2,
                category=category,
                source=source,
                filters=filters,
                rrf_constant=rrf_constant,
                dense_weight=dense_weight,
                sparse_weight=sparse_weight
            )
            for c in q_candidates:
                fid = c["faiss_id"]
                if fid not in all_candidates or c["score"] > all_candidates[fid]["score"]:
                    all_candidates[fid] = c

        candidates_list = list(all_candidates.values())

        # 3. Reranking
        rerank_start = time.perf_counter()
        final_results = self.reranker.rerank(query, candidates_list, top_k=top_k)
        rerank_latency = time.perf_counter() - rerank_start

        # 4. Parent-Child Chunk Expansion & Graph RAG Enrichment
        for res in final_results:
            meta = res.get("metadata", {})
            # If it's a child chunk, swap text with its parent context
            if meta and (meta.get("is_child") or "parent_text" in meta):
                parent_text = meta.get("parent_text")
                if parent_text:
                    res["text"] = parent_text
                    res["content"] = parent_text
                    res["tokens"] = len(parent_text.split())

        # Fetch Graph Context
        graph_ctx_str = ""
        if enable_graph and self.graph_engine:
            try:
                graph_res = self.graph_engine.retrieve_context(query)
                graph_ctx_str = graph_res.get("context_str", "")
            except Exception as e:
                logger.warning("Graph context retrieval failed (%s)", e)

        # Inject Graph context and latency metrics into the first element's metadata
        metrics = {
            "retrieval_latency": time.perf_counter() - start_time,
            "reranking_latency": rerank_latency,
            "graph_context": graph_ctx_str
        }

        for idx, res in enumerate(final_results):
            res["metrics"] = metrics
            if idx == 0 and graph_ctx_str:
                # Attach graph context to metadata of the top result
                res["graph_context"] = graph_ctx_str

        return final_results

    def _retrieve_single(
        self,
        query: str,
        top_k: int,
        category: Optional[str] = None,
        source: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        rrf_constant: int = 60,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Performs single hybrid dense + sparse query retrieval."""
        # A. Dense Search
        query_vector = self.embedder.embed(query)
        candidate_limit = max(top_k * 3, 20)
        dense_hits = self.vector_db.search(query_vector, top_k=candidate_limit)

        dense_results = []
        for vec_id, similarity in dense_hits:
            chunk = self.metadata_db.get_chunk(vec_id)
            if chunk:
                if self._match_filters(chunk, category, source, filters):
                    chunk["score"] = similarity
                    dense_results.append(chunk)

        # B. Sparse Search
        sparse_results = self._sparse_search(
            query, limit=candidate_limit, category=category, source=source, filters=filters
        )

        # C. RRF Merge
        rrf_scores = collections.defaultdict(float)
        id_to_chunk = {}

        for rank, chunk in enumerate(dense_results):
            fid = chunk["faiss_id"]
            rrf_scores[fid] += dense_weight * (1.0 / (rrf_constant + rank + 1))
            id_to_chunk[fid] = chunk

        for rank, chunk in enumerate(sparse_results):
            fid = chunk["faiss_id"]
            rrf_scores[fid] += sparse_weight * (1.0 / (rrf_constant + rank + 1))
            id_to_chunk[fid] = chunk

        fused_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        candidates = []
        for fid in fused_ids[:candidate_limit]:
            chunk = id_to_chunk[fid]
            chunk["score"] = round(rrf_scores[fid], 4)
            candidates.append(chunk)

        return candidates

    def _match_filters(
        self,
        chunk: Dict[str, Any],
        category: Optional[str] = None,
        source: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Verifies if chunk satisfies metadata and column filtering conditions."""
        # 1. Column filters
        if category and chunk.get("category") != category:
            return False
        if source and chunk.get("file_path") != source:
            return False

        # 2. Rich metadata filters
        if filters:
            meta = chunk.get("metadata")
            if not isinstance(meta, dict):
                # Retrieve from SQLite raw properties if stored as json
                meta = chunk.copy()

            for key, val in filters.items():
                # Direct check in chunk or inner metadata dict
                chunk_val = chunk.get(key, meta.get(key))
                if chunk_val is None:
                    return False
                
                # Support list match (e.g. tag match)
                if isinstance(chunk_val, list):
                    if val not in chunk_val:
                        return False
                elif str(chunk_val).lower() != str(val).lower():
                    return False

        return True

    def _sparse_search(
        self,
        query: str,
        limit: int = 20,
        category: Optional[str] = None,
        source: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """BM25-style scoring fallback over SQLite database chunks."""
        all_chunks = self.metadata_db.get_all_chunks()
        if not all_chunks:
            return []

        query_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 1]
        if not query_terms:
            return []

        doc_count = len(all_chunks)
        df = collections.defaultdict(int)
        doc_terms = []
        
        for chunk in all_chunks:
            terms = [t.lower() for t in re.findall(r"\w+", chunk["content"])]
            doc_terms.append(terms)
            unique_terms = set(terms)
            for t in unique_terms:
                df[t] += 1

        k1 = 1.5
        b = 0.75
        avg_doc_len = sum(len(d) for d in doc_terms) / doc_count if doc_count > 0 else 0

        scores = []
        for idx, chunk in enumerate(all_chunks):
            if not self._match_filters(chunk, category, source, filters):
                continue

            terms = doc_terms[idx]
            doc_len = len(terms)
            if doc_len == 0:
                continue

            score = 0.0
            tf_counts = collections.Counter(terms)

            for term in query_terms:
                if term not in tf_counts:
                    continue
                
                doc_freq = df.get(term, 0)
                idf = math.log((doc_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
                
                tf = tf_counts[term]
                tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_len / avg_doc_len)))
                
                score += idf * tf_norm

            if score > 0:
                chunk["score"] = score
                scores.append(chunk)

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:limit]
