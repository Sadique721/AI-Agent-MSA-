# Architecture Specification — MSA V5.0

This document defines the high-level architecture of MSA AI Agent V5.0, detailing how the FastAPI Gateway, LangGraph StateGraph, and local desktop frontend coordinate.

---

## 1. High-Level Design

The MSA V5.0 codebase is organized as a modular monorepo:

```
msa_agent/
├── agent/                # LangGraph nodes and StateGraph workflow
├── ai_core/              # LiteLLM and AI routing engine
├── backend/              # Gateway servers, security managers, and workspace managers
├── config/               # Schema-validated environment YAML config files
├── prompts/              # Decoupled agent prompt templates
├── frontend-desktop/     # React 19 + Electron desktop overlay client
└── tests/                # Complete regression test suite
```

---

## 2. Multi-Agent Coordination Flow

Every user prompt undergoes structural processing through 7 pipeline stages:

```
[Intent Detection] ──► [Memory Recall] ──► [KG Lookup] ──► [RAG Search]
                        └──► [Tool Call] ──► [LLM Generate] ──► [Self-Critique]
```
- Each node falls back gracefully if optional resources (such as Neo4j or Qdrant) are unavailable.
