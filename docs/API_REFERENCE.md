# API Reference — MSA V5.0 FastAPI Gateway

This document details all REST and WebSocket/SSE endpoints provided by the **FastAPI Gateway (port 8000)** in MSA AI Agent V5.0.

---

## 1. System Liveness & Health

### `GET /api/v5/health`
- **Description:** Simple liveness probe.
- **Response:**
  ```json
  {"healthy": true, "version": "5.0.0"}
  ```

### `GET /api/v5/status`
- **Description:** Full health status check for all system components and active feature flags.
- **Response:**
  ```json
  {
    "status": "online",
    "version": "5.0.0",
    "gateway": "FastAPI V5.0",
    "subsystems": {
      "flask_backend": "online (port 5000)",
      "fastapi_gateway": "online (port 8000)",
      "agent_service": "online",
      "memory": "online",
      "decision_engine": "online",
      "config_loader": "online",
      "prompt_loader": "online"
    },
    "features": {
      "enable_kafka": false,
      "enable_speech": true,
      "enable_artifact_engine": true
    }
  }
  ```

---

## 2. Configuration & Prompts

### `GET /api/v5/config`
- **Description:** Exposes safe active environment configuration settings (excluding secrets).
- **Response:**
  ```json
  {
    "environment": "development",
    "version": "5.0.0",
    "features": { ... },
    "default_model": "ollama/llama3.2:3b"
  }
  ```

### `GET /api/v5/prompts`
- **Description:** Returns a list of all registered system prompt templates under `prompts/`.
- **Response:**
  ```json
  {"prompts": ["planner", "coder", "rag", "reflection", "memory", "reviewer", "researcher", "vision", "summarizer"]}
  ```

### `GET /api/v5/prompts/{name}`
- **Description:** Retrieves the raw text content of a prompt template by name.

---

## 3. Workspaces & Projects

### `GET /api/v5/workspaces`
- **Description:** Lists all active workspaces.

### `POST /api/v5/workspaces`
- **Description:** Creates a new workspace.
- **Request Body:**
  ```json
  {
    "name": "New Project",
    "description": "Optional description text"
  }
  ```

---

## 4. Execution & Streaming

### `POST /api/v5/execute`
- **Description:** Executes a command synchronously through the LangGraph agent pipeline.
- **Request Body:**
  ```json
  {
    "command": "Verify database connectivity",
    "persona": "developer",
    "reasoning_mode": "balanced",
    "workspace_id": "default"
  }
  ```

### `GET /api/v5/stream`
- **Description:** Server-Sent Events (SSE) streaming endpoint returning token chunks and status updates.
- **Query Params:**
  - `command` (required)
  - `persona` (optional)
  - `reasoning_mode` (optional)
- **SSE Stream Data Formats:**
  - **Token Chunk:** `data: {"type": "token", "content": "..."}`
  - **Status Update:** `data: {"type": "status", "state": "generating", "message": "..."}`
  - **Completion Payload:** `data: {"type": "completed", "response": "..."}`

### `WEBSOCKET /api/v5/ws`
- **Description:** Bidirectional real-time WebSocket for low-latency client communication.
