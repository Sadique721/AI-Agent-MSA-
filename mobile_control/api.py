"""
mobile_control/api.py
=====================
Flask Blueprint version of the mobile-control API.
(Replaces the broken FastAPI / pydantic version.)

Routes registered under the "/mobile" prefix when the blueprint is
registered on the Flask app.
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger("msa.mobile_control.api")

mobile_bp = Blueprint("mobile", __name__, url_prefix="/mobile")


# ---------------------------------------------------------------------------
# Lazy helpers — import heavy modules only when a route is actually called
# ---------------------------------------------------------------------------

def _open_app_via_scripts(app_name: str) -> str:
    """Use module-level open_app function from scripts.system_control."""
    try:
        from scripts.system_control import open_app
        return open_app(app_name)
    except Exception as e:
        logger.warning("scripts.system_control.open_app unavailable: %s", e)
        return f"Could not open {app_name}"


def _get_location_tracker():
    try:
        from mobile_control.location import LocationTracker
        return LocationTracker()
    except Exception as e:
        logger.warning("LocationTracker unavailable: %s", e)
        return None


# ---------------------------------------------------------------------------
# POST /mobile/execute
# ---------------------------------------------------------------------------

@mobile_bp.route("/execute", methods=["POST"])
def execute_command():
    """Execute a text command from mobile UI via the full AgentService pipeline."""
    data    = request.get_json(force=True, silent=True) or {}
    command = data.get("command", "").strip()

    if not command:
        return jsonify({"status": "error", "message": "No command provided"}), 400

    # ── Prefer AgentService (full AI pipeline) ──────────────────────────────
    try:
        from backend.server import _get_components
        _get_components()
        from backend.server import _agent_service        # lazy import — avoids circular dep
        if _agent_service is not None:
            result = _agent_service.process_input(command)
            logger.info("mobile/execute (AgentService) — cmd=%r action=%s", command, result.get("action"))
            return jsonify({
                "status":           "success",
                "response":         result.get("response", ""),
                "action":           result.get("action", "none"),
                "execution_result": result.get("execution_result", ""),
            })
    except Exception as e:
        logger.warning("AgentService unavailable for mobile/execute, using fallback: %s", e)

    # ── Simple fallback ─────────────────────────────────────────────────────
    response_text = ""
    cmd = command.lower()
    try:
        if "open" in cmd:
            app_name      = cmd.replace("open", "").strip() or "notepad"
            response_text = _open_app_via_scripts(app_name)
        else:
            response_text = f"MSA received: {cmd}"
    except Exception as e:
        logger.error("mobile/execute fallback error: %s", e)
        response_text = f"Error: {e}"

    return jsonify({"status": "success", "response": response_text})


# ---------------------------------------------------------------------------
# POST /mobile/location
# ---------------------------------------------------------------------------

@mobile_bp.route("/location", methods=["POST"])
def update_location():
    """Receive GPS location from mobile device."""
    data = request.get_json(force=True, silent=True) or {}
    lat   = data.get("latitude")
    lon   = data.get("longitude")
    notes = data.get("notes", "")

    if lat is None or lon is None:
        return jsonify({"status": "error", "message": "latitude and longitude required"}), 400

    result = {"status": "success", "message": f"Location updated: ({lat}, {lon})"}
    try:
        tracker = _get_location_tracker()
        if tracker and hasattr(tracker, "log_location"):
            tracker.log_location(lat, lon, notes)
    except Exception as e:
        logger.warning("Location tracker error: %s", e)

    return jsonify(result)


# ---------------------------------------------------------------------------
# GET /mobile/history
# ---------------------------------------------------------------------------

@mobile_bp.route("/history", methods=["GET"])
def get_history():
    """Retrieve recent command history (stub — delegates to main memory)."""
    return jsonify({"status": "ok", "history": []})


# ---------------------------------------------------------------------------
# GET /mobile/status
# ---------------------------------------------------------------------------

@mobile_bp.route("/status", methods=["GET"])
def mobile_status():
    """Mobile subsystem health check."""
    return jsonify({"status": "online", "mobile_control": "active", "version": "2.0"})
