"""
tests/test_rag_memory.py
========================
Unit tests for the RAG Memory system.
Tests semantic storing and retrieval of facts and project details.
"""

import pytest
from memory.rag_memory import RAGMemory


def test_rag_remember_and_recall():
    # Setup RAG memory with default/mock SQLite (passing None for simplicity)
    rag = RAGMemory(sqlite_memory=None)

    # Store a couple of facts
    rag.remember("My B.Tech graduation project is the MSA AI Agent", "project")
    rag.remember("I live in Bangalore", "preference")

    # Query for the project
    results = rag.recall("graduation project", top_k=2)

    assert len(results) > 0
    # First result should be the most semantically relevant
    best_hit = results[0]
    assert "MSA AI Agent" in best_hit["text"]
    assert best_hit["category"] == "project"


def test_context_augmentation():
    rag = RAGMemory(sqlite_memory=None)

    # Store facts
    rag.remember("Md Sadique Amin is a Software Engineer", "preference")

    # Get augmented context
    context_data = rag.get_augmented_context("who is Md Sadique Amin", recent_limit=3, semantic_limit=2)

    assert "combined" in context_data
    assert "Software Engineer" in context_data["combined"]
