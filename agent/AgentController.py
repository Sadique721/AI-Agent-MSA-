"""
agent/AgentController.py
========================
Flask route integration for the MSA Agent.

Registers REST endpoints on the Flask app:
  POST /api/execute      → process text command
  GET  /api/history      → conversation history
  GET  /api/status       → full agent health
  POST /api/location     → GPS update from mobile
  POST /api/search       → explicit web search

Uses AgentService as the single orchestration point.
"""
import logging
from flask import request, jsonify
from typing import Optional

logger = logging.getLogger("msa.agent.controller")


class AgentController:
    """
    Initialise once per server instance and call init_app(app)
    to register all routes.
    """

    def __init__(self, agent_service=None):
        """
        Args:
            agent_service: pre-built AgentService (optional — can be set later)
        """
        self.service: Optional[object] = agent_service

    # ── App Factory ────────────────────────────────────────────────────────
    def init_app(self, app, agent_service=None) -> None:
        """Register all routes on a Flask app instance."""
        if agent_service:
            self.service = agent_service

        app.add_url_rule("/api/execute",  view_func=self._execute,  methods=["POST"])
        app.add_url_rule("/api/history",  view_func=self._history,  methods=["GET"])
        app.add_url_rule("/api/status",   view_func=self._status,   methods=["GET"])
        app.add_url_rule("/api/location", view_func=self._location, methods=["POST"])
        app.add_url_rule("/api/search",   view_func=self._search,   methods=["POST"])
        app.add_url_rule("/api/profile",  view_func=self._profile,  methods=["GET"])
        logger.info("AgentController: routes registered (execute/history/status/location/search/profile)")

    # ── Routes ─────────────────────────────────────────────────────────────
    def _execute(self):
        """POST /api/execute — process a text command."""
        data    = request.get_json(force=True, silent=True) or {}
        command = data.get("command", "").strip()

        if not command:
            return jsonify({"status": "error", "message": "No command provided"}), 400

        if not self.service:
            return jsonify({"status": "error", "message": "Agent service not initialised"}), 503

        try:
            result = self.service.process_input(command)
            logger.info("execute — cmd=%r action=%s", command, result.get("action"))
            return jsonify({
                "status":           "success",
                "response":         result.get("response", ""),
                "action":           result.get("action", "none"),
                "parameters":       result.get("parameters", {}),
                "execution_result": result.get("execution_result", ""),
            })
        except Exception as e:
            logger.exception("Error in /api/execute")
            return jsonify({"status": "error", "message": str(e)}), 500

    def _history(self):
        """GET /api/history — recent conversation history."""
        if not self.service:
            return jsonify({"status": "ok", "history": []})
        try:
            limit   = int(request.args.get("limit", 10))
            history = self.service.get_history(limit=limit)
            return jsonify({"status": "ok", "history": history})
        except Exception as e:
            logger.exception("Error in /api/history")
            return jsonify({"status": "error", "message": str(e)}), 500

    def _status(self):
        """GET /api/status — full agent & subsystem health."""
        if not self.service:
            return jsonify({"status": "degraded", "message": "Agent not initialised"})

        engine = self.service.engine
        mem    = self.service.memory

        stt_ok    = False
        try:
            from voice.stt import STT
            stt_ok = STT().is_ready()
        except Exception:
            pass

        llm_ok    = getattr(engine, "llm", None) is not None
        engine_ok = engine is not None

        return jsonify({
            "status": "online",
            "subsystems": {
                "stt":             "ok" if stt_ok    else "degraded (model missing)",
                "decision_engine": "ok (LLM)" if llm_ok else "ok (keyword fallback)" if engine_ok else "degraded",
                "memory":          "ok" if mem else "degraded",
                "security":        "ok",
            },
            "memory_stats": mem.get_stats() if mem else {},
            "server":       "Flask-SocketIO v2.0",
            "port":         5000,
        })

    def _location(self):
        """POST /api/location — GPS update from mobile device."""
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

        logger.info("location — lat=%s lon=%s notes=%r", lat, lon, notes)
        return jsonify({
            "status":  "success",
            "message": f"Location updated: ({lat:.4f}, {lon:.4f}). {advice}",
        })

    def _search(self):
        """POST /api/search — explicit web search."""
        data  = request.get_json(force=True, silent=True) or {}
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"status": "error", "message": "query required"}), 400
        try:
            from backend.internet import Internet
            net     = Internet()
            results = net.search_and_summarize(query)
            return jsonify({"status": "ok", "query": query, "results": results})
        except Exception as e:
            logger.exception("Error in /api/search")
            return jsonify({"status": "error", "message": str(e)}), 500

    def _profile(self):
        """
        GET /api/profile — return owner profile.
        Protected by x-api-key header (MSA_SECURE_123).
        """
        from config import API_KEY, USER_PROFILE
        key = request.headers.get("x-api-key", "")
        if key != API_KEY:
            logger.warning("Unauthorized /api/profile access from %s", request.remote_addr)
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return jsonify({"status": "success", "data": USER_PROFILE})
