# MSA AI Agent - Enterprise Architecture Index

This index outlines the Volume 0-24 documentation structure for the MSA AI Agent repository, mapping existing code and future aspirational features.

| Volume | Scope | Mapping to Code / Implementation Status |
|---|---|---|
| 0 | Vision, principles, standards | Conceptual / Docs only |
| 1 | Core architecture, event bus, state machine | `backend/planner/orchestration_engine.py` / `backend/shared/event_bus.py` |
| 2 | AI Kernel — LLM router, model registry, streaming | `ai_core/llm_manager.py` / `backend/decision_engine.py` |
| 3 | Cognitive engine — CoT/ToT/reflection/confidence | `agent/ReasoningEngine.py` / `agent/reflection.py` |
| 4-5 | Multi-agent roles (CEO/Planner/Architect/...) | `agent/swarm.py` |
| 6 | Memory types (short/long/episodic/semantic) | `memory/rag_memory.py` / `memory/conversation_summarizer.py` |
| 7 | RAG — embeddings, FAISS, GraphRAG, reranking | `memory/vector_store.py` / `memory/graph_rag.py` |
| 8 | Knowledge graph — entities/relations | Partial — GraphRAG relationship queries; full KG is future work |
| 9-12 | Desktop/Vision/Voice/Browser agents | `vision/` / `voice/` / `browser_agent/` |
| 13 | Code intelligence — AST, refactoring, review | `coding/` package |
| 14 | MCP | `backend/mcp/` (extended in `backend/mcp/tool_hooks.py`) |
| 15 | Plugin SDK | `plugins/sdk/` |
| 16 | Automation/workflow | `automation/execution_engine.py` |
| 17 | Security — RBAC/vault/encryption | `backend/security.py` / `backend/vault.py` |
| 18 | Performance — caching, streaming, GPU | `scripts/hardware_profiler.py` / `backend/services/semantic_cache.py` |
| 19 | Monitoring/observability | `backend/services/analytics_engine.py` / `backend/system_monitor.py` |
| 20 | Packaging — .exe/installer | Electron builder configuration (`frontend-desktop/package.json`) |
| 21 | Testing | `tests/` (496+ unit and integration tests passing) |
| 22 | Deployment/CI-CD | Out of scope (local desktop application) |
| 23-24 | Future: mobile/robotics/IoT/federated/AGI research | Aspirational / Future milestones |
