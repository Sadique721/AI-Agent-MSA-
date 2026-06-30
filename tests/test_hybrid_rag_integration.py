"""
tests/test_hybrid_rag_integration.py
====================================
Comprehensive unit and integration tests for the Hybrid RAG system.
Covers embeddings, knowledge parser/chunker, indexes (FAISS & SQLite),
retrieval fusions, context builder, APIs, and fallback modes.
"""

import os
import json
import tempfile
import shutil
import pytest
import numpy as np

from config import PROJECT_ROOT
from embeddings.embedder import Embedder
from embeddings.reranker import Reranker
from indexes.sqlite_db import SQLiteMetadataStore
from indexes.vector_db import FAISSIndexManager
from knowledge.parser import DocumentParser, GitHubRepositoryIndexer
from knowledge.chunker import Chunker
from knowledge.retriever import HybridRetriever
from knowledge.context_builder import ContextBuilder
from backend.server import app


# ── Embeddings Tests ─────────────────────────────────────────────────────────

def test_embedder_fallbacks_and_metrics():
    # Force fallback by loading with invalid model name
    embedder = Embedder(model_name="invalid-model-name-for-testing")
    assert embedder.is_semantic() is False
    assert embedder.dim() == 384

    # Single text embed
    vec = embedder.embed("test query string")
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (384,)
    assert not np.isnan(vec).any()

    # Batch embed
    vecs = embedder.embed_batch(["text one", "text two"])
    assert vecs.shape == (2, 384)

    # Empty inputs
    empty_vec = embedder.embed("")
    assert np.all(empty_vec == 0)


def test_reranker_fallbacks():
    # Disable Cross-Encoder to test fallback soft scoring
    reranker = Reranker(enabled=False)
    candidates = [
        {"text": "Artificial Intelligence coding agent project", "score": 0.6},
        {"text": "Banana smoothie recipe with honey", "score": 0.4}
    ]
    
    results = reranker.rerank("coding agent", candidates, top_k=2)
    assert len(results) == 2
    # The first result should be the coding agent text because of lexical match overlap
    assert "coding agent" in results[0]["text"]
    assert results[0]["score"] > results[1]["score"]


# ── Knowledge Ingestion Tests ────────────────────────────────────────────────

def test_document_parser_and_cleaner():
    parser = DocumentParser()
    
    # Text cleaning
    raw_text = "Hello \t  world!\n\n\nNew line \r here."
    clean = parser.clean_text(raw_text)
    assert clean == "Hello world!\n\nNew line \n here."

    # Parse simple TXT file
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as f:
        f.write("Project: MSA AI Agent\nDeveloper: Md Sadique Amin\n")
        temp_txt = f.name

    try:
        doc = parser.parse_file(temp_txt)
        assert "MSA AI Agent" in doc["text"]
        assert doc["metadata"]["filename"] == os.path.basename(temp_txt)
    finally:
        os.unlink(temp_txt)

    # Parse JSON
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        json.dump({"title": "RAG Design", "category": "architecture"}, f)
        temp_json = f.name

    try:
        doc = parser.parse_file(temp_json)
        assert "RAG Design" in doc["text"]
        assert doc["metadata"]["json_category"] == "architecture"
    finally:
        os.unlink(temp_json)


def test_chunker():
    chunker = Chunker(chunk_size=100, chunk_overlap=10)
    text = "This is a long sentence that is used to test character-based sliding window chunking in the hybrid RAG system."
    chunks = chunker.chunk_document(text, {"source": "test"})
    
    assert len(chunks) > 0
    assert "chunk_index" in chunks[0]
    assert chunks[0]["metadata"]["source"] == "test"


# ── Storage & Indexing Tests ───────────────────────────────────────────────

def test_sqlite_metadata_store():
    # Use temporary sqlite DB
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db = f.name

    try:
        store = SQLiteMetadataStore(db_path=temp_db)
        store.add_chunk(
            faiss_id=10,
            file_path="src/file.txt",
            chunk_index=0,
            content="Testing SQLite RAG Chunks",
            category="fact",
            tokens=4,
            timestamp="2026-06-29",
            metadata={"tag": "unit-test"}
        )

        chunk = store.get_chunk(10)
        assert chunk is not None
        assert chunk["content"] == "Testing SQLite RAG Chunks"
        assert chunk["metadata"]["tag"] == "unit-test"

        # Check hash
        store.update_file_hash("src/file.txt", "abc123hash", "2026-06-29")
        assert store.get_file_hash("src/file.txt") == "abc123hash"

        # Check stats
        stats = store.get_stats()
        assert stats["total_chunks"] == 1
        assert stats["total_files"] == 1

        # Delete file
        deleted = store.delete_chunks_for_file("src/file.txt")
        assert deleted == [10]
        assert store.get_chunk(10) is None
        # Close SQLite connection to release file lock on Windows
        store.close()
    finally:
        try:
            os.unlink(temp_db)
        except Exception:
            pass


def test_faiss_index_manager():
    # Use temporary FAISS index path
    with tempfile.NamedTemporaryFile(suffix=".faiss", delete=False) as f:
        temp_faiss = f.name

    try:
        # Load index manager
        manager = FAISSIndexManager(index_path=temp_faiss)
        vec = np.random.randn(384).astype(np.float32)
        
        idx = manager.add(vec)
        assert idx == 0
        assert manager.count() == 1

        # Search
        hits = manager.search(vec, top_k=1)
        assert len(hits) == 1
        assert hits[0][0] == 0  # Should match index 0

        # Clear
        manager.clear()
        assert manager.count() == 0
    finally:
        os.unlink(temp_faiss)
        # Clean up npy files if created
        if os.path.exists(temp_faiss + ".npy"):
            os.unlink(temp_faiss + ".npy")


# ── Retriever & Context Builder Tests ────────────────────────────────────────

def test_hybrid_retriever_and_context_builder():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f_db:
        temp_db = f_db.name
    with tempfile.NamedTemporaryFile(suffix=".faiss", delete=False) as f_faiss:
        temp_faiss = f_faiss.name

    try:
        embedder = Embedder(model_name="invalid-model-for-tests")
        vector_db = FAISSIndexManager(index_path=temp_faiss)
        meta_db = SQLiteMetadataStore(db_path=temp_db)
        reranker = Reranker(enabled=False)

        retriever = HybridRetriever(
            embedder=embedder,
            vector_db=vector_db,
            metadata_db=meta_db,
            reranker=reranker
        )

        # Inject sample chunk
        chunk_text = "Md Sadique Amin is building an offline RAG assistant"
        vec = embedder.embed(chunk_text)
        fid = vector_db.add(vec)
        meta_db.add_chunk(
            faiss_id=fid,
            file_path="bio.txt",
            chunk_index=0,
            content=chunk_text,
            category="preference",
            tokens=9,
            timestamp="2026-06-29",
            metadata={}
        )

        # Retrieve
        results = retriever.retrieve("offline RAG assistant", top_k=1)
        assert len(results) == 1
        assert "bio.txt" in results[0]["file_path"]

        # Build context
        cb = ContextBuilder(max_tokens=100)
        ctx = cb.build_context(results)
        assert "Source: bio.txt" in ctx["context_str"]
        assert "Content:" in ctx["context_str"]
        assert ctx["chunks_used"] == 1
        # Close SQLite connection
        meta_db.close()
    finally:
        try:
            os.unlink(temp_db)
        except Exception:
            pass
        try:
            os.unlink(temp_faiss)
        except Exception:
            pass
        if os.path.exists(temp_faiss + ".npy"):
            try:
                os.unlink(temp_faiss + ".npy")
            except Exception:
                pass


# ── REST API Endpoints Tests ─────────────────────────────────────────────────

def test_api_upload_search_stats_delete():
    # Setup test Flask client
    client = app.test_client()

    # Upload test file
    temp_file = tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False)
    temp_txt_path = temp_file.name
    temp_file.write("MSA AI Agent features offline Voice recognition and Hybrid RAG capabilities.\n")
    temp_file.close()  # Close immediately so other processes can access it on Windows

    try:
        # 1. Test POST /rag/upload
        with open(temp_txt_path, 'rb') as f:
            resp = client.post('/rag/upload', data={'file': (f, 'test_doc.txt')})
        assert resp.status_code == 200
        res = json.loads(resp.data)
        assert res["status"] == "success"
        uploaded_path = res["file_path"]

        # 2. Test POST /rag/index
        resp = client.post('/rag/index', json={
            "path": uploaded_path,
            "category": "fact",
            "chunk_size": 200,
            "chunk_overlap": 20
        })
        assert resp.status_code == 200
        res = json.loads(resp.data)
        assert res["status"] == "success"

        # 3. Test GET /rag/stats
        resp = client.get('/rag/stats')
        assert resp.status_code == 200
        res = json.loads(resp.data)
        assert res["total_files"] >= 1

        # 4. Test POST /rag/search
        resp = client.post('/rag/search', json={
            "query": "Voice recognition and RAG",
            "top_k": 2
        })
        assert resp.status_code == 200
        res = json.loads(resp.data)
        assert len(res["results"]) >= 1
        assert "Voice recognition" in res["results"][0]["content"]

        # 5. Test POST /rag/delete
        resp = client.post('/rag/delete', json={"file_path": uploaded_path})
        assert resp.status_code == 200
        res = json.loads(resp.data)
        assert res["status"] == "success"

    finally:
        # Close any lingering connections on stats/search databases to release locks
        try:
            from indexes.sqlite_db import SQLiteMetadataStore
            SQLiteMetadataStore().close()
        except Exception:
            pass
        try:
            os.unlink(temp_txt_path)
        except Exception:
            pass
