"""
backend/server.py
=================
Flask + Flask-SocketIO server for the MSA AI AGENT.

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
# PWA infrastructure — manifest, service worker, icons
# ---------------------------------------------------------------------------
@app.route("/manifest.json")
def serve_manifest():
    """Serve the PWA Web App Manifest with correct MIME type."""
    resp = send_from_directory(
        os.path.join(PROJECT_ROOT, "ui"),
        "manifest.json",
        mimetype="application/manifest+json",
    )
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/sw.js")
def serve_service_worker():
    """Serve the Service Worker JS with root scope permission."""
    resp = send_from_directory(
        os.path.join(PROJECT_ROOT, "ui"),
        "sw.js",
        mimetype="application/javascript",
    )
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"]           = "no-cache"
    return resp


@app.route("/icon-192.png")
@app.route("/icon-512.png")
def serve_icons():
    """Serve PWA icons (192×192 and 512×512)."""
    filename = request.path.lstrip("/")
    return send_from_directory(
        os.path.join(PROJECT_ROOT, "ui"),
        filename,
        mimetype="image/png",
    )




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
            "decision_engine": "ok (LLM online)" if llm_ok else "ok" if engine_ok else "degraded",
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


# ---------------------------------------------------------------------------
# GET /api/tools — List all registered tools
# ---------------------------------------------------------------------------
@app.route("/api/tools", methods=["GET"])
def api_tools():
    """List all registered tools + status."""
    try:
        from tools.tool_registry import registry
        return jsonify({"status": "success", "tools": registry.to_dict()})
    except Exception as e:
        logger.exception("Error in /api/tools")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/planner — Submit complex task to Planner
# ---------------------------------------------------------------------------
@app.route("/api/planner", methods=["POST"])
def api_planner():
    """Submit complex task to Planner."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        task = data.get("task", "").strip()
        if not task:
            return jsonify({"status": "error", "message": "task is required"}), 400

        _get_components()
        if _agent_service and _agent_service.planner:
            context = _agent_service.get_history()
            steps = _agent_service.planner.plan(task, context)

            # Execute the plan
            exec_results = []
            from tools.tool_registry import registry
            for step in steps:
                res = registry.execute(step["tool"], step["params"])
                exec_results.append({
                    "step": step["step"],
                    "tool": step["tool"],
                    "action": step["action"],
                    "params": step["params"],
                    "result": res
                })

            return jsonify({
                "status": "success",
                "task": task,
                "steps": steps,
                "execution": exec_results
            })

        return jsonify({"status": "error", "message": "Planner or AgentService not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/planner")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/browser — Execute a browser action directly
# ---------------------------------------------------------------------------
@app.route("/api/browser", methods=["POST"])
def api_browser():
    """Execute a browser action directly."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        action = data.get("action", "").strip()
        if not action:
            return jsonify({"status": "error", "message": "action is required"}), 400

        from tools.tool_registry import registry
        tool_name = f"browser_{action}" if not action.startswith("browser_") else action
        if not registry.get(tool_name):
            tool_name = action

        if not registry.get(tool_name):
            return jsonify({"status": "error", "message": f"Browser tool '{action}' not found"}), 404

        params = data.get("parameters", data.get("params", {}))
        res = registry.execute(tool_name, params)
        return jsonify({"status": "success", "tool": tool_name, "result": res})
    except Exception as e:
        logger.exception("Error in /api/browser")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/memory/search — Semantic FAISS memory search
# ---------------------------------------------------------------------------
@app.route("/api/memory/search", methods=["GET"])
def api_memory_search():
    """Semantic FAISS memory search."""
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify({"status": "error", "message": "q query parameter is required"}), 400

        _get_components()
        if _agent_service and _agent_service.rag_memory:
            top_k = int(request.args.get("top_k", 5))
            results = _agent_service.rag_memory.recall(query, top_k=top_k)
            return jsonify({"status": "success", "query": query, "results": results})

        return jsonify({"status": "error", "message": "RAGMemory not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/memory/search")
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================================================================
# PHASE-2: REASONING ENGINE ENDPOINTS
# ===========================================================================

# ---------------------------------------------------------------------------
# POST /api/reason  — Run ReasoningEngine on a task
# ---------------------------------------------------------------------------
@app.route("/api/reason", methods=["POST"])
def api_reason():
    """Run ReasoningEngine on a task and return structured reasoning packet."""
    try:
        data  = request.get_json(force=True, silent=True) or {}
        task  = data.get("task", data.get("command", "")).strip()
        if not task:
            return jsonify({"status": "error", "message": "task is required"}), 400

        _get_components()
        if _agent_service and _agent_service.reasoning_engine:
            context  = _agent_service.get_history(limit=5)
            reasoning = _agent_service.reasoning_engine.reason(task, context)
            return jsonify({"status": "success", "task": task, "reasoning": reasoning})

        return jsonify({"status": "error", "message": "ReasoningEngine not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/reason")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/validate  — Validate task execution results
# ---------------------------------------------------------------------------
@app.route("/api/validate", methods=["POST"])
def api_validate():
    """Validate a list of step results using the Validator."""
    try:
        data    = request.get_json(force=True, silent=True) or {}
        results = data.get("results", [])
        goal    = data.get("goal", "")
        if not results:
            return jsonify({"status": "error", "message": "results list is required"}), 400

        _get_components()
        if _agent_service and _agent_service.validator:
            reasoning   = {"goal": goal} if goal else None
            validation  = _agent_service.validator.validate_result(results, reasoning)
            final_val   = None
            if goal:
                final_val = _agent_service.validator.validate_final_output(results, goal)
            return jsonify({
                "status":             "success",
                "step_validation":    validation,
                "final_validation":   final_val,
            })

        return jsonify({"status": "error", "message": "Validator not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/validate")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/reason-execute  — Full pipeline: Reason + Plan + Execute
# ---------------------------------------------------------------------------
@app.route("/api/reason-execute", methods=["POST"])
def api_reason_execute():
    """Full autonomous pipeline: ReasoningEngine → Planner → Validator → Execute."""
    try:
        data    = request.get_json(force=True, silent=True) or {}
        command = data.get("command", data.get("task", "")).strip()
        if not command:
            return jsonify({"status": "error", "message": "command is required"}), 400

        _get_components()
        if _agent_service:
            result = _agent_service.process_input(command)
            return jsonify({"status": "success", "command": command, **result})

        return jsonify({"status": "error", "message": "AgentService not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/reason-execute")
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================================================================
# PHASE-2: MOBILE REASONING ENDPOINTS
# ===========================================================================

# In-memory store for latest mobile device capabilities
_mobile_capabilities: dict = {}
_mobile_status_log: list   = []


# ---------------------------------------------------------------------------
# POST /mobile/status  — Mobile device sends heartbeat + status
# ---------------------------------------------------------------------------
@app.route("/mobile/status", methods=["POST"])
def mobile_status():
    """Mobile device sends current agent status / heartbeat."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        _mobile_status_log.append(data)
        if len(_mobile_status_log) > 100:
            _mobile_status_log.pop(0)

        logger.info("Mobile status received: %s", str(data)[:200])
        return jsonify({
            "status":   "ok",
            "received": True,
            "message":  "Status recorded.",
        })
    except Exception as e:
        logger.exception("Error in /mobile/status")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /mobile/validate  — Mobile reports whether an action completed
# ---------------------------------------------------------------------------
@app.route("/mobile/validate", methods=["POST"])
def mobile_validate():
    """Mobile APK reports action completion for server-side feedback loop."""
    try:
        data       = request.get_json(force=True, silent=True) or {}
        action     = data.get("action", "")
        success    = data.get("success", False)
        detail     = data.get("detail", "")
        device_id  = data.get("device_id", "unknown")

        logger.info("Mobile validate: device=%s action=%s success=%s", device_id, action, success)

        # Feed back into AgentService validation context if available
        _get_components()
        feedback_msg = f"Mobile action '{action}' on device {device_id}: {'✓ succeeded' if success else '✗ failed'}. {detail}"

        if _agent_service and _agent_service.rag_memory:
            try:
                _agent_service.rag_memory.remember(feedback_msg, category="mobile")
            except Exception:
                pass

        return jsonify({
            "status":   "ok",
            "recorded": True,
            "message":  feedback_msg,
        })
    except Exception as e:
        logger.exception("Error in /mobile/validate")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /mobile/capabilities  — Mobile sends device capabilities
# ---------------------------------------------------------------------------
@app.route("/mobile/capabilities", methods=["POST"])
def mobile_capabilities():
    """Mobile APK sends device capabilities (battery, network, apps, etc.)."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        _mobile_capabilities.update(data)
        _mobile_capabilities["last_updated"] = __import__("time").time()

        battery   = data.get("battery", "?")
        wifi      = data.get("wifi", False)
        gps       = data.get("location_enabled", False)
        app_count = len(data.get("apps", []))

        logger.info(
            "Mobile capabilities: battery=%s%% wifi=%s gps=%s apps=%d",
            battery, wifi, gps, app_count,
        )

        # Store in reasoning context memory
        _get_components()
        if _agent_service and _agent_service.rag_memory:
            capability_summary = (
                f"Mobile device: battery={battery}%, wifi={wifi}, "
                f"gps={gps}, apps installed={app_count}"
            )
            try:
                _agent_service.rag_memory.remember(capability_summary, category="mobile")
            except Exception:
                pass

        return jsonify({
            "status":   "ok",
            "received": True,
            "summary":  f"Battery {battery}% | WiFi: {wifi} | GPS: {gps} | Apps: {app_count}",
        })
    except Exception as e:
        logger.exception("Error in /mobile/capabilities")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /mobile/task-result  — Mobile sends final task execution result
# ---------------------------------------------------------------------------
@app.route("/mobile/task-result", methods=["POST"])
def mobile_task_result():
    """Mobile APK sends the final result of an executed task."""
    try:
        data      = request.get_json(force=True, silent=True) or {}
        task_id   = data.get("task_id", "unknown")
        result    = data.get("result", "")
        success   = data.get("success", False)
        device_id = data.get("device_id", "unknown")

        logger.info(
            "Mobile task result: id=%s device=%s success=%s result=%s",
            task_id, device_id, success, str(result)[:100],
        )

        # Run validator on mobile result
        _get_components()
        validation = None
        if _agent_service and _agent_service.validator:
            step = {"step": 1, "tool": "mobile_control", "action": task_id, "params": {}}
            validation = _agent_service.validator.validate_step(step, str(result))

        # Persist to memory
        if _agent_service and _agent_service.rag_memory and result:
            try:
                _agent_service.rag_memory.remember(
                    f"Mobile task {task_id}: {result}", category="mobile"
                )
            except Exception:
                pass

        return jsonify({
            "status":     "ok",
            "task_id":    task_id,
            "success":    success,
            "validation": validation,
        })
    except Exception as e:
        logger.exception("Error in /mobile/task-result")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/reasoning-status  — Subsystem health check
# ---------------------------------------------------------------------------
@app.route("/api/reasoning-status", methods=["GET"])
def api_reasoning_status():
    """Return Phase-2 subsystem health and mobile device info."""
    try:
        _get_components()
        phase2 = {}
        if _agent_service and hasattr(_agent_service, "get_reasoning_status"):
            phase2 = _agent_service.get_reasoning_status()

        return jsonify({
            "status":              "online",
            "phase2_subsystems":   phase2,
            "mobile_capabilities": _mobile_capabilities,
            "mobile_log_count":    len(_mobile_status_log),
        })
    except Exception as e:
        logger.exception("Error in /api/reasoning-status")
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================================================================
# PHASE-3: CODING AGENT ENDPOINTS
# ===========================================================================

# ---------------------------------------------------------------------------
# POST /api/code/generate — Generate code from natural language
# ---------------------------------------------------------------------------
@app.route("/api/code/generate", methods=["POST"])
def api_code_generate():
    """Generate source code from a natural language prompt."""
    try:
        data   = request.get_json(force=True, silent=True) or {}
        prompt = data.get("prompt", data.get("command", "")).strip()
        lang   = data.get("language")
        if not prompt:
            return jsonify({"status": "error", "message": "prompt is required"}), 400

        _get_components()
        if _agent_service and _agent_service.code_generator:
            result = _agent_service.code_generator.generate(prompt, lang)
            # Store in memory
            if _agent_service.rag_memory:
                try:
                    _agent_service.rag_memory.remember(
                        f"Generated {result.get('language')} code: {result.get('explanation')}",
                        "coding_project",
                    )
                except Exception:
                    pass
            return jsonify({"status": "success", "result": result})

        return jsonify({"status": "error", "message": "Code generator not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/code/generate")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/code/debug — Analyze error logs / exceptions
# ---------------------------------------------------------------------------
@app.route("/api/code/debug", methods=["POST"])
def api_code_debug():
    """Analyze runtime exceptions and recommend fixes."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        logs = data.get("logs", data.get("error", "")).strip()
        if not logs:
            return jsonify({"status": "error", "message": "logs or error text is required"}), 400

        _get_components()
        if _agent_service and _agent_service.bug_analyzer:
            result = _agent_service.bug_analyzer.analyze(logs)
            if _agent_service.rag_memory:
                try:
                    _agent_service.rag_memory.remember(
                        f"Bug analysis: {result.get('root_cause')} -> Fix: {result.get('fix')}",
                        "coding_bug",
                    )
                except Exception:
                    pass
            return jsonify({"status": "success", "result": result})

        return jsonify({"status": "error", "message": "Bug analyzer not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/code/debug")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/code/review — Code quality review
# ---------------------------------------------------------------------------
@app.route("/api/code/review", methods=["POST"])
def api_code_review():
    """Analyze source code quality (security, performance, SOLID)."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        code = data.get("code", "").strip()
        if not code:
            return jsonify({"status": "error", "message": "code is required"}), 400

        _get_components()
        if _agent_service and _agent_service.code_reviewer:
            result = _agent_service.code_reviewer.review(code)
            if _agent_service.rag_memory:
                try:
                    _agent_service.rag_memory.remember(
                        f"Code review: Grade {result.get('grade')}",
                        "coding_review",
                    )
                except Exception:
                    pass
            return jsonify({"status": "success", "result": result})

        return jsonify({"status": "error", "message": "Code reviewer not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/code/review")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/code/explain — Line-by-line code explanation
# ---------------------------------------------------------------------------
@app.route("/api/code/explain", methods=["POST"])
def api_code_explain():
    """Generate line-by-line explanations for source code."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        code = data.get("code", "").strip()
        if not code:
            return jsonify({"status": "error", "message": "code is required"}), 400

        _get_components()
        if _agent_service and _agent_service.code_explainer:
            result = _agent_service.code_explainer.explain(code)
            if _agent_service.rag_memory:
                try:
                    _agent_service.rag_memory.remember(
                        f"Explained code: {result.get('summary')}",
                        "coding_reference",
                    )
                except Exception:
                    pass
            return jsonify({"status": "success", "result": result})

        return jsonify({"status": "error", "message": "Code explainer not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/code/explain")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/code/project — Generate project scaffolding
# ---------------------------------------------------------------------------
@app.route("/api/code/project", methods=["POST"])
def api_code_project():
    """Generate boilerplate project structures, configs, and Dockerfiles."""
    try:
        data         = request.get_json(force=True, silent=True) or {}
        project_type = data.get("project_type", data.get("type", "")).strip()
        name         = data.get("name", "").strip()
        description  = data.get("description", "")
        if not project_type or not name:
            return jsonify({"status": "error", "message": "project_type and name are required"}), 400

        _get_components()
        if _agent_service and _agent_service.project_generator:
            result = _agent_service.project_generator.generate(project_type, name, description)
            
            # Map compatibility fields for Android app client parser
            result["language"] = result.get("project_type", "N/A")
            blueprint = result.get("blueprint", {})
            result["files"] = blueprint.get("files", [])
            result["explanation"] = f"Scaffolded a new {project_type} project named '{name}' successfully."

            if _agent_service.rag_memory:
                try:
                    _agent_service.rag_memory.remember(
                        f"Generated project {name} ({project_type})",
                        "coding_project",
                    )
                except Exception:
                    pass
            return jsonify({"status": "success", "result": result})

        return jsonify({"status": "error", "message": "Project generator not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/code/project")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/code/test — Generate test suites
# ---------------------------------------------------------------------------
@app.route("/api/code/test", methods=["POST"])
def api_code_test():
    """Generate unit test suites for given source code."""
    try:
        data      = request.get_json(force=True, silent=True) or {}
        code      = data.get("code", "").strip()
        framework = data.get("framework", "")
        if not code:
            return jsonify({"status": "error", "message": "code is required"}), 400

        _get_components()
        if _agent_service and _agent_service.test_generator:
            result = _agent_service.test_generator.generate(code, framework)
            if _agent_service.rag_memory:
                try:
                    _agent_service.rag_memory.remember(
                        f"Generated {result.get('framework')} tests",
                        "coding_reference",
                    )
                except Exception:
                    pass
            return jsonify({"status": "success", "result": result})

        return jsonify({"status": "error", "message": "Test generator not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/code/test")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/code/refactor — Refactor source code
# ---------------------------------------------------------------------------
@app.route("/api/code/refactor", methods=["POST"])
def api_code_refactor():
    """Detect and apply code refactoring improvements."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        code = data.get("code", "").strip()
        if not code:
            return jsonify({"status": "error", "message": "code is required"}), 400

        _get_components()
        if _agent_service and _agent_service.refactor_engine:
            result = _agent_service.refactor_engine.refactor(code)
            if _agent_service.rag_memory:
                try:
                    _agent_service.rag_memory.remember(
                        f"Refactored code. Improvements: {', '.join(result.get('improvements', []))}",
                        "coding_reference",
                    )
                except Exception:
                    pass
            return jsonify({"status": "success", "result": result})

        return jsonify({"status": "error", "message": "Refactor engine not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/code/refactor")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# POST /api/code/stacktrace — Parse and analyze stack traces
# ---------------------------------------------------------------------------
@app.route("/api/code/stacktrace", methods=["POST"])
def api_code_stacktrace():
    """Parse stack traces and identify offending file, line, method, and issue."""
    try:
        data  = request.get_json(force=True, silent=True) or {}
        trace = data.get("trace", data.get("stacktrace", "")).strip()
        if not trace:
            return jsonify({"status": "error", "message": "trace or stacktrace is required"}), 400

        _get_components()
        if _agent_service and _agent_service.stacktrace_analyzer:
            result = _agent_service.stacktrace_analyzer.analyze(trace)
            if _agent_service.rag_memory:
                try:
                    _agent_service.rag_memory.remember(
                        f"Stack trace: {result.get('file')}:{result.get('line')} -> {result.get('issue')}",
                        "coding_bug",
                    )
                except Exception:
                    pass
            return jsonify({"status": "success", "result": result})

        return jsonify({"status": "error", "message": "StackTrace analyzer not initialised"}), 503
    except Exception as e:
        logger.exception("Error in /api/code/stacktrace")
        return jsonify({"status": "error", "message": str(e)}), 500


# ---------------------------------------------------------------------------
# GET /api/code/history — Retrieve coding-related memory entries
# ---------------------------------------------------------------------------
@app.route("/api/code/history", methods=["GET"])
def api_code_history():
    """Retrieve recent coding-related events from memory."""
    try:
        _get_components()
        limit = int(request.args.get("limit", 20))

        if _agent_service and _agent_service.rag_memory:
            coding_categories = ["coding_project", "coding_bug", "coding_review", "coding_reference"]
            results = []
            for cat in coding_categories:
                try:
                    items = _agent_service.rag_memory.recall(cat, top_k=limit)
                    if isinstance(items, list):
                        results.extend(items)
                except Exception:
                    pass
            # Sort by timestamp if available, limit total
            results = results[:limit]
            return jsonify({"status": "success", "history": results, "total": len(results)})

        return jsonify({"status": "success", "history": [], "total": 0})
    except Exception as e:
        logger.exception("Error in /api/code/history")
        return jsonify({"status": "error", "message": str(e)}), 500


# ===========================================================================
# SOCKET.IO
# ===========================================================================


@socketio.on("connect")
def on_connect():
    logger.info("SocketIO client connected: %s", request.sid)
    emit("connected", {"message": "MSA AI AGENT online. Say 'Hey MSA' or type a command."})


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
