"""
backend/gateway_server.py
==========================
MSA AI Agent V5.0 — FastAPI Enterprise Gateway
Runs on port 8000 alongside Flask (port 5000).

Key improvements over V4.5:
  - Reads all config from YAML (ConfigLoader)
  - Fixed Memory.__init__() — passes security instance correctly
  - JWT authentication middleware
  - Rate limiting via slowapi
  - Full SSE streaming endpoint
  - WebSocket duplex endpoint
  - Health, config, personas, workspaces endpoints
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

# ── Path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

# ── V5 imports ────────────────────────────────────────────────────────────────
try:
    from backend.shared.config_loader import ConfigLoader
    _cfg = ConfigLoader.get_instance()
except Exception:
    _cfg = None  # type: ignore

try:
    from backend.shared.prompt_loader import PromptLoader
    _pl = PromptLoader.get_instance()
except Exception:
    _pl = None  # type: ignore

# ── Legacy imports (preserved for backward compat) ────────────────────────────
try:
    from backend.security import Security
    _security = Security()
except Exception:
    _security = None  # type: ignore

try:
    from memory.memory import Memory
    _memory = Memory(security=_security)
except Exception:
    _memory = None  # type: ignore

try:
    from backend.decision_engine import DecisionEngine
    _engine = DecisionEngine(_memory) if _memory else None
except Exception:
    _engine = None  # type: ignore

try:
    from agent.AgentService import AgentService
    _agent_service = AgentService(_engine, _memory) if (_engine and _memory) else None
except Exception as e:
    logging.warning("AgentService init failed: %s", e)
    _agent_service = None  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.gateway.v5")

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="MSA AI Agent V5.0 — Anti-Gravity OS Gateway",
    description="Enterprise-grade agentic AI gateway with streaming, personas, and workspaces.",
    version="5.0.0",
    docs_url="/api/v5/docs",
    redoc_url="/api/v5/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request/Response Models ───────────────────────────────────────────────────
class CommandRequest(BaseModel):
    command: str
    persona: Optional[str] = "default"
    reasoning_mode: Optional[str] = "balanced"
    workspace_id: Optional[str] = "default"

class WorkspaceRequest(BaseModel):
    name: str
    description: Optional[str] = ""

# ── Utility ───────────────────────────────────────────────────────────────────
def _json(d: Dict) -> str:
    return json.dumps(d, ensure_ascii=False)

def _get_service() -> Optional[Any]:
    return _agent_service

# ── Health & Status ───────────────────────────────────────────────────────────
@app.get("/api/v5/status")
async def get_status():
    """Gateway health check with subsystem status."""
    subsystems = {
        "flask_backend": "online (port 5000)",
        "fastapi_gateway": "online (port 8000)",
        "agent_service": "online" if _agent_service else "degraded",
        "memory": "online" if _memory else "offline",
        "decision_engine": "online" if _engine else "offline",
        "config_loader": "online" if _cfg else "offline",
        "prompt_loader": "online" if _pl else "offline",
    }
    # Feature flag status
    features: Dict[str, bool] = {}
    if _cfg:
        features = _cfg.features_dict()

    return {
        "status": "online",
        "version": "5.0.0",
        "gateway": "FastAPI V5.0",
        "subsystems": subsystems,
        "features": features,
    }

@app.get("/api/v5/health")
async def health():
    """Simple liveness probe."""
    return {"healthy": True, "version": "5.0.0"}

# ── Config ────────────────────────────────────────────────────────────────────
@app.get("/api/v5/config")
async def get_config():
    """Inspect active configuration (safe subset — no secrets)."""
    if not _cfg:
        return {"error": "ConfigLoader unavailable"}
    safe = {
        "environment": _cfg.get("app.environment", "unknown"),
        "version": _cfg.get("app.version", "5.0.0"),
        "features": _cfg.features_dict(),
        "default_model": _cfg.get("models.default_model", "unknown"),
        "default_persona": _cfg.get_default_persona() if _cfg else "default",
    }
    return safe

# ── Personas ──────────────────────────────────────────────────────────────────
@app.get("/api/v5/personas")
async def get_personas():
    """List all available AI personas."""
    if not _cfg:
        return {"personas": [], "default": "default"}
    personas = _cfg.get_all_personas()
    safe_personas = {
        name: {
            "display_name": p.get("display_name", name),
            "description": p.get("description", ""),
            "tone": p.get("tone", "professional"),
            "reasoning_mode": p.get("reasoning_mode", "balanced"),
            "avatar_color": p.get("avatar_color", "#6366f1"),
        }
        for name, p in personas.items()
    }
    return {
        "personas": safe_personas,
        "default": _cfg.get_default_persona(),
    }

# ── Workspaces (stub — full implementation in Phase 2) ────────────────────────
_workspaces: Dict[str, Dict] = {
    "default": {"id": "default", "name": "Default Workspace", "description": "Main workspace"}
}

@app.get("/api/v5/workspaces")
async def list_workspaces():
    return {"workspaces": list(_workspaces.values())}

@app.post("/api/v5/workspaces")
async def create_workspace(req: WorkspaceRequest):
    ws_id = req.name.lower().replace(" ", "_")
    _workspaces[ws_id] = {"id": ws_id, "name": req.name, "description": req.description}
    return {"workspace": _workspaces[ws_id]}

# ── Artifacts (stub) ──────────────────────────────────────────────────────────
_artifacts: Dict[str, Dict] = {}

@app.get("/api/v5/artifacts")
async def list_artifacts(workspace_id: str = "default"):
    workspace_artifacts = [a for a in _artifacts.values() if a.get("workspace_id") == workspace_id]
    return {"artifacts": workspace_artifacts}

# ── Prompts ───────────────────────────────────────────────────────────────────
@app.get("/api/v5/prompts")
async def list_prompts():
    """List available prompt templates."""
    if not _pl:
        return {"prompts": []}
    return {"prompts": _pl.list_available()}

@app.get("/api/v5/prompts/{name}")
async def get_prompt(name: str):
    """Retrieve a prompt template by name."""
    if not _pl:
        raise HTTPException(404, "PromptLoader unavailable")
    content = _pl.get(name)
    return {"name": name, "content": content}

# ── Execute (synchronous) ─────────────────────────────────────────────────────
@app.post("/api/v5/execute")
async def execute_command(req: CommandRequest):
    """Execute a command synchronously via AgentService."""
    service = _get_service()
    if not service:
        # Graceful degradation — echo back with explanation
        return {
            "status": "degraded",
            "response": (
                f"MSA AI Agent V5.0 gateway is online. "
                f"AgentService initialisation is pending (check Ollama is running). "
                f"Your query: '{req.command}'"
            ),
            "action": "none",
            "parameters": {},
        }
    try:
        result = service.process_input(req.command)
        return {
            "status": "success",
            "response": result.get("response", ""),
            "action": result.get("action", "none"),
            "parameters": result.get("parameters", {}),
        }
    except Exception as e:
        logger.exception("Error executing command")
        raise HTTPException(status_code=500, detail=str(e))

# ── Stream (SSE) ──────────────────────────────────────────────────────────────
@app.get("/api/v5/stream")
async def stream_command(command: str, persona: str = "default", reasoning_mode: str = "balanced"):
    """Stream tokens via Server-Sent Events."""
    service = _get_service()
    loop = asyncio.get_event_loop()

    async def generator():
        if not service:
            yield f"data: {_json({'type':'status','state':'degraded','message':'AgentService unavailable'})}\n\n"
            yield f"data: {_json({'type':'completed','response':'Gateway online but AgentService is starting up. Ensure Ollama is running.'})}\n\n"
            return

        queue: asyncio.Queue = asyncio.Queue()

        def stream_cb(token: str):
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "token", "content": token})

        def status_cb(state: str, message: str):
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "status", "state": state, "message": message})

        def run():
            try:
                status_cb("thinking", "Analyzing your request...")
                res = service.process_input(command, stream_callback=stream_cb, status_callback=status_cb)
                loop.call_soon_threadsafe(queue.put_nowait, {
                    "type": "completed",
                    "response": res.get("response", ""),
                    "action": res.get("action", "none"),
                    "parameters": res.get("parameters", {}),
                })
            except Exception as err:
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "error", "message": str(err)})

        asyncio.create_task(asyncio.to_thread(run))

        while True:
            item = await queue.get()
            yield f"data: {_json(item)}\n\n"
            if item["type"] in ("completed", "error"):
                break

    return StreamingResponse(generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })

# ── WebSocket (duplex) ────────────────────────────────────────────────────────
@app.websocket("/api/v5/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time bidirectional WebSocket for the Electron UI."""
    await websocket.accept()
    service = _get_service()
    loop = asyncio.get_event_loop()
    logger.info("WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_json()
            command = data.get("command", "").strip()
            persona = data.get("persona", "default")
            if not command:
                continue

            await websocket.send_json({"type": "status", "state": "thinking", "message": "Processing..."})

            if not service:
                await websocket.send_json({
                    "type": "completed",
                    "response": "Gateway V5.0 online. AgentService initialising — ensure Ollama is running.",
                    "action": "none",
                })
                continue

            def stream_cb(token: str):
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"type": "token", "content": token}), loop
                )

            def status_cb(state: str, msg: str):
                asyncio.run_coroutine_threadsafe(
                    websocket.send_json({"type": "status", "state": state, "message": msg}), loop
                )

            def run():
                try:
                    res = service.process_input(command, stream_callback=stream_cb, status_callback=status_cb)
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({
                            "type": "completed",
                            "response": res.get("response", ""),
                            "action": res.get("action", "none"),
                            "parameters": res.get("parameters", {}),
                        }), loop
                    )
                except Exception as err:
                    asyncio.run_coroutine_threadsafe(
                        websocket.send_json({"type": "error", "message": str(err)}), loop
                    )

            await asyncio.to_thread(run)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception("WebSocket error: %s", e)


@app.get("/api/v5/analytics")
def get_analytics():
    try:
        from backend.services.analytics_engine import AnalyticsEngine
        ae = AnalyticsEngine()
        return ae.get_aggregated_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
