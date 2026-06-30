# SSE Streaming Engine — MSA V5.0

This document describes the Server-Sent Events (SSE) streaming engine in MSA AI Agent V5.0.

---

## 1. Streaming Protocol

The gateway uses Server-Sent Events (SSE) via the `GET /api/v5/stream` endpoint.
This allows the client to receive real-time updates containing token chunks and pipeline status changes over a single persistent HTTP connection.

```
Client ──► (HTTP Request) ──► Server
Client ◄── (SSE Event: status: thinking) ◄── Server
Client ◄── (SSE Event: token chunk) ◄── Server
Client ◄── (SSE Event: completed payload) ◄── Server
```

---

## 2. API Format

All SSE packets use the `data:` prefix and carry stringified JSON objects:
- **Status Event:** `data: {"type": "status", "state": "thinking", "message": "Analyzing context..."}`
- **Token Event:** `data: {"type": "token", "content": "..."}`
- **Complete Event:** `data: {"type": "completed", "response": "..."}`
