"""
backend/server.py
=================
Flask + Flask-SocketIO server for the MSA AI Agent.

Responsibilities:
  - Serves the Web UI at GET /
  - Handles real-time audio/text over WebSocket (SocketIO)
  - Exposes REST endpoints:
      POST /api/execute      → text command → decision → response
      POST /api/location     → GPS update from mobile
      GET  /api/history      → recent conversation history
      GET  /api/status       → agent health check
      GET  /api/system_info  → CPU/RAM/Disk/uptime [NEW]
      POST /api/search       → web search [NEW]
  - Mobile routes via Blueprint at /mobile/*

FIX LOG:
  - Registered mobile_bp blueprint (was missing — routes returned 404)
  - Fixed api_status() safe attribute checks (prevents AttributeError)
  - Added /api/system_info using SystemMonitor [NEW]
  - Added /api/search using Internet module [NEW]
  - Added memory stats to status endpoint [NEW]
"""

import base64
import json
import logging
import os
import sys

from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("msa.server")

# ---------------------------------------------------------------------------
# Project root on sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Core imports
# ---------------------------------------------------------------------------
from voice.stt import STT                            # noqa: E402
from backend.decision_engine import DecisionEngine   # noqa: E402
from memory.memory import Memory                     # noqa: E402
from backend.security import Security                # noqa: E402
from backend.system_monitor import SystemMonitor     # noqa: E402
from agent.AgentService import AgentService          # noqa: E402

# ---------------------------------------------------------------------------
# Flask App & SocketIO
# ---------------------------------------------------------------------------
app = Flask(
    __name__,
    static_folder=os.path.join(PROJECT_ROOT, "ui"),
    template_folder=os.path.join(PROJECT_ROOT, "ui"),
)
app.config["SECRET_KEY"] = "msa-secret-key-local-only"

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ---------------------------------------------------------------------------
# FIX: Register mobile Blueprint (was never registered → 404 on /mobile/*)
# ---------------------------------------------------------------------------
try:
    from mobile_control.api import mobile_bp
    app.register_blueprint(mobile_bp)
    logger.info("mobile_bp Blueprint registered at /mobile/*")
except Exception as e:
    logger.warning("mobile_bp registration failed: %s", e)

# ---------------------------------------------------------------------------
# Lazy-initialised singletons
# ---------------------------------------------------------------------------
_stt:     STT           = None
_engine:  DecisionEngine= None
_mem:     Memory        = None
_sec:     Security      = None
_agent_service: AgentService = None
_monitor: SystemMonitor = SystemMonitor()


def _get_components():
    """Thread-safe lazy initialisation of core components."""
    global _stt, _engine, _mem, _sec, _agent_service

    if _stt is None:
        logger.info("Initialising STT, DecisionEngine, Security, Memory, AgentService …")

        try:
            _sec = Security()
        except Exception as e:
            logger.error("Security init failed: %s", e)

        try:
            _stt = STT()
        except Exception as e:
            logger.error("STT init failed: %s", e)
            _stt = None

        try:
            _engine = DecisionEngine()
        except Exception as e:
            logger.error("DecisionEngine init failed: %s", e)
            _engine = None

        try:
            _mem = Memory(_sec) if _sec else None
        except Exception as e:
            logger.error("Memory init failed: %s", e)
            _mem = None

        if _engine and _mem:
            try:
                _agent_service = AgentService(_engine, _mem)
            except Exception as e:
                logger.error("AgentService init failed: %s", e)
                _agent_service = None

    return _stt, _engine, _mem


# ===========================================================================
# ROUTES
# ===========================================================================

@app.route("/")
def serve_ui():
    """Serve the main dashboard HTML."""
    return send_from_directory(os.path.join(PROJECT_ROOT, "ui"), "index.html")


@app.route("/voice")
@app.route("/msa")
def serve_voice():
    """Serve the MSA voice UI."""
    return send_from_directory(os.path.join(PROJECT_ROOT, "ui"), "msa_voice.html")


@app.route("/app")
@app.route("/mobile")
def serve_mobile_app():
    """Serve the MSA Mobile App (responsive, works on phone + laptop)."""
    return send_from_directory(os.path.join(PROJECT_ROOT, "ui"), "mobile_app.html")


# ---------------------------------------------------------------------------
# GET /api/logs  — last N log lines for the VS Code-style console
# ---------------------------------------------------------------------------
import io as _io, collections as _col

_log_buffer: _col.deque = _col.deque(maxlen=500)   # circular in-memory log

class _DequeHandler(logging.Handler):
    """Push every log record into the in-memory deque."""
    def emit(self, record):
        _log_buffer.append({
            "level":   record.levelname,
            "name":    record.name,
            "message": self.format(record),
            "time":    record.created,
        })

# Attach to root logger once
_dq_handler = _DequeHandler()
_dq_handler.setFormatter(logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S"
))
logging.getLogger().addHandler(_dq_handler)


@app.route("/api/logs", methods=["GET"])
def api_logs():
    """Return the last N log lines for the VS Code-style in-app console."""
    try:
        limit = int(request.args.get("limit", 100))
        logs  = list(_log_buffer)[-limit:]
        return jsonify({"status": "ok", "logs": logs, "total": len(_log_buffer)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/execute
# ---------------------------------------------------------------------------
@app.route("/api/execute", methods=["POST"])
def api_execute():
    """Text command → AI decision → Action execution → JSON response."""
    try:
        data    = request.get_json(force=True, silent=True) or {}
        command = data.get("command", "").strip()
        if not command:
            return jsonify({"status": "error", "message": "No command provided"}), 400

        _get_components()

        if _agent_service:
            result = _agent_service.process_input(command)
            return jsonify(result)

        # Fallback if AgentService is not available
        context = _mem.get_recent_context() if _mem else []
        if _engine:
            decision = _engine.process_command(command, context)
        else:
            decision = {"response": f"MSA received: {command}", "action": "none", "parameters": {}}

        if _mem:
            try:
                _mem.add_conversation(command, decision["response"], decision["action"])
            except Exception as e:
                logger.warning("Memory write error: %s", e)

        logger.info("execute (fallback) — cmd=%r action=%s", command, decision.get("action"))
        return jsonify({
            "status":     "success",
            "response":   decision.get("response", ""),
            "action":     decision.get("action", "none"),
            "parameters": decision.get("parameters", {}),
        })

    except Exception as e:
        logger.exception("Error in /api/execute")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/location
# ---------------------------------------------------------------------------
@app.route("/api/location", methods=["POST"])
def api_location():
    """GPS update from mobile device."""
    try:
        data  = request.get_json(force=True, silent=True) or {}
        lat   = data.get("latitude")
        lon   = data.get("longitude")
        notes = data.get("notes", "")

        if lat is None or lon is None:
            return jsonify({"status": "error", "message": "latitude and longitude required"}), 400

        advice = "Location updated."
        try:
            from backend.location import LocationTracker
            tracker = LocationTracker()
            tracker.update_location(lat, lon)
            advice = tracker.get_contextual_advice()
        except Exception as e:
            logger.warning("LocationTracker error: %s", e)

        logger.info("location — lat=%s lon=%s", lat, lon)
        return jsonify({
            "status":  "success",
            "message": f"Location updated: ({lat:.4f}, {lon:.4f}). {advice}",
        })

    except Exception as e:
        logger.exception("Error in /api/location")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------
@app.route("/api/history", methods=["GET"])
def api_history():
    """Return last N decrypted conversations."""
    try:
        _get_components()
        limit = int(request.args.get("limit", 10))

        if _agent_service:
            history = _agent_service.get_history(limit=limit)
            return jsonify({"status": "ok", "history": history})

        if not _mem:
            return jsonify({"status": "ok", "history": []})

        history = _mem.get_recent_context(limit=limit)
        return jsonify({"status": "ok", "history": history})

    except Exception as e:
        logger.exception("Error in /api/history")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/status  (FIX: safe attribute checks)
# ---------------------------------------------------------------------------
@app.route("/api/status", methods=["GET"])
def api_status():
    """Agent health snapshot — all subsystems."""
    stt, engine, mem = _get_components()

    # FIX: safe attribute access with getattr/hasattr
    stt_ok    = stt is not None and getattr(stt, "model", None) is not None
    engine_ok = engine is not None
    llm_ok    = engine_ok and getattr(engine, "llm", None) is not None
    mem_ok    = mem is not None
    sec_ok    = _sec is not None

    if _agent_service:
        mem_stats = _agent_service.get_memory_stats()
    else:
        mem_stats = mem.get_stats() if mem else {}

    return jsonify({
        "status": "online",
        "subsystems": {
            "stt":             "ok" if stt_ok    else "degraded (model missing)",
            "decision_engine": "ok (LLM online)" if llm_ok else "ok (keyword fallback)" if engine_ok else "degraded",
            "memory":          "ok" if mem_ok    else "degraded",
            "security":        "ok" if sec_ok    else "degraded",
        },
        "memory_stats": mem_stats,
        "server": "Flask-SocketIO",
        "port":   5000,
    })


# ---------------------------------------------------------------------------
# GET /api/system_info  [NEW]
# ---------------------------------------------------------------------------
@app.route("/api/system_info", methods=["GET"])
def api_system_info():
    """Real-time CPU / RAM / Disk / uptime snapshot."""
    try:
        snapshot = _monitor.get_snapshot()
        return jsonify({"status": "ok", "data": snapshot})
    except Exception as e:
        logger.exception("Error in /api/system_info")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/search  [NEW]
# ---------------------------------------------------------------------------
@app.route("/api/search", methods=["POST"])
def api_search():
    """Web search via DuckDuckGo."""
    try:
        data  = request.get_json(force=True, silent=True) or {}
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"status": "error", "message": "query is required"}), 400

        from backend.internet import Internet
        net     = Internet()
        results = net.search_and_summarize(query)

        return jsonify({"status": "ok", "query": query, "results": results})

    except Exception as e:
        logger.exception("Error in /api/search")
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================================================================
# SOCKET.IO
# ===========================================================================

@socketio.on("connect")
def on_connect():
    logger.info("SocketIO client connected: %s", request.sid)
    emit("connected", {"message": "MSA Agent online. Say 'Hey MSA' or type a command."})


@socketio.on("disconnect")
def on_disconnect():
    logger.info("SocketIO client disconnected: %s", request.sid)


@socketio.on("audio")
def handle_audio(data):
    """Receives base64-encoded audio → transcribe → decide → execute → emit response."""
    stt, engine, mem = _get_components()

    try:
        audio_bytes = base64.b64decode(data.get("audio", ""))
    except Exception as e:
        emit("response", {"text": "Audio decode error.", "action": "none", "params": {}})
        logger.error("Audio decode failed: %s", e)
        return

    text = ""
    if stt:
        try:
            text = stt.transcribe(audio_bytes)
        except Exception as e:
            logger.error("STT error: %s", e)

    if not text:
        emit("response", {"text": "Could not transcribe audio.", "action": "none", "params": {}})
        return

    if _agent_service:
        result = _agent_service.process_input(text)
        emit("response", {
            "text":       result.get("response", ""),
            "action":     result.get("action", "none"),
            "params":     result.get("parameters", {}),
            "transcript": text,
        })
        return

    context  = mem.get_recent_context() if mem else []
    decision = _run_engine(engine, text, context)

    if mem:
        try:
            mem.add_conversation(text, decision["response"], decision["action"])
        except Exception as e:
            logger.warning("Memory write error: %s", e)

    logger.info("audio (fallback) — text=%r action=%s", text, decision.get("action"))
    emit("response", {
        "text":       decision.get("response", ""),
        "action":     decision.get("action", "none"),
        "params":     decision.get("parameters", {}),
        "transcript": text,
    })


@socketio.on("text_command")
def handle_text_command(data):
    """Plain-text command from UI chat box."""
    _get_components()
    command = data.get("command", "").strip()
    if not command:
        return

    if _agent_service:
        result = _agent_service.process_input(command)
        emit("response", {
            "text":       result.get("response", ""),
            "action":     result.get("action", "none"),
            "params":     result.get("parameters", {}),
            "transcript": command,
        })
        return

    context  = _mem.get_recent_context() if _mem else []
    decision = _run_engine(_engine, command, context)

    if _mem:
        try:
            _mem.add_conversation(command, decision["response"], decision["action"])
        except Exception as e:
            logger.warning("Memory write error: %s", e)

    logger.info("text_command (fallback) — cmd=%r action=%s", command, decision.get("action"))
    emit("response", {
        "text":       decision.get("response", ""),
        "action":     decision.get("action", "none"),
        "params":     decision.get("parameters", {}),
        "transcript": command,
    })


# ---------------------------------------------------------------------------
def _run_engine(engine, text: str, context: list) -> dict:
    """Run engine or fallback gracefully."""
    if engine:
        try:
            return engine.process_command(text, context)
        except Exception as e:
            logger.error("DecisionEngine error: %s", e)
    return {"response": f"MSA received: {text}", "action": "none", "parameters": {}}


# ===========================================================================
# Server Launcher
# ===========================================================================

def start_server(host: str = "0.0.0.0", port: int = 5000):
    """Start the MSA Flask-SocketIO server."""
    logger.info("MSA Server starting on http://%s:%d", host, port)
    socketio.run(
        app,
        host=host,
        port=port,
        allow_unsafe_werkzeug=True,
        log_output=False,
    )


if __name__ == "__main__":
    start_server()
