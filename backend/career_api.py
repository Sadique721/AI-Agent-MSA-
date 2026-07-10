"""
backend/career_api.py
=====================
Career OS REST API (V7-V10)

Can be used two ways:
  1. As a Flask Blueprint (registered on the main Flask app in server.py)
  2. As a standalone WSGI/ASGI app run by uvicorn (see __main__ block and 'app' export)

Endpoints:
    GET  /health                              → career sub-system health
    GET  /api/career/analytics                → funnel stats + response rate
    GET  /api/career/applications             → list all application records
    GET  /api/career/applications/<id>        → single application detail
    POST /api/career/applications/<id>/confirm → confirm queued application
    GET  /api/career/crm/contacts             → list CRM contacts
    POST /api/career/crm/contacts             → add new recruiter contact
    GET  /api/career/crm/followups            → pending follow-ups
"""
import logging
import os
from flask import Blueprint, Flask, jsonify, request

logger = logging.getLogger("msa.career_api")

# ── Flask Blueprint (used when registered into main Flask server) ─────────────
career_bp = Blueprint("career", __name__)

# ── Standalone Flask app (used when run directly by uvicorn via WSGI bridge) ──
# docker-compose runs: uvicorn backend.career_api:app --port 8082
# We create a Flask app and expose it as ASGI 'app' for uvicorn compatibility.
_flask_app = Flask(__name__)
_flask_app.register_blueprint(career_bp, url_prefix="/api/career")

# Health route on the root (for Docker healthcheck: GET /health)
@_flask_app.route("/health")
def root_health():
    return jsonify({"status": "healthy", "service": "msa-career-api", "version": "9.0.0"})

# ASGI wrapper so uvicorn can run this Flask WSGI app
try:
    from asgiref.wsgi import WsgiToAsgi  # type: ignore
    app = WsgiToAsgi(_flask_app)
    logger.info("Career API running as ASGI app (via asgiref)")
except ImportError:
    # Fallback: expose Flask WSGI app directly
    # NOTE: add asgiref to requirements.txt for uvicorn compatibility
    logger.warning("asgiref not installed — career API running in WSGI-only mode")
    app = _flask_app  # type: ignore[assignment]


# ─── Lazy singletons ─────────────────────────────────────────────────────────

_analytics = None
_crm = None
_app_engine = None


def _get_analytics():
    global _analytics
    if _analytics is None:
        from career.analytics import CareerAnalytics
        _analytics = CareerAnalytics()
    return _analytics


def _get_crm():
    global _crm
    if _crm is None:
        from career.recruiter_crm import RecruiterCRM
        _crm = RecruiterCRM()
    return _crm


def _get_app_engine():
    global _app_engine
    if _app_engine is None:
        from career.application_engine import ApplicationEngine
        _app_engine = ApplicationEngine()
    return _app_engine


# ─── Analytics endpoints ──────────────────────────────────────────────────────

@career_bp.route("/analytics", methods=["GET"])
def career_analytics():
    """Return funnel stats and response rate."""
    try:
        analytics = _get_analytics()
        funnel = analytics.get_funnel_stats()
        rates = analytics.get_response_rates()
        return jsonify({
            "funnel": funnel,
            "response_rate": rates.get("response_rate", 0.0),
            "total_applied": rates.get("total_applied", 0),
        })
    except Exception as exc:
        logger.error("career_analytics failed: %s", exc)
        return jsonify({"funnel": {}, "response_rate": 0, "total_applied": 0}), 200


# ─── Applications endpoints ───────────────────────────────────────────────────

@career_bp.route("/applications", methods=["GET"])
def list_applications():
    """Return all application records ordered by applied_at DESC."""
    try:
        engine = _get_app_engine()
        rows = engine._db.execute(
            "SELECT * FROM applications ORDER BY applied_at DESC LIMIT 100"
        ).fetchall()
        cols = [d[0] for d in engine._db.execute("SELECT * FROM applications LIMIT 0").description]
        return jsonify([dict(zip(cols, r)) for r in rows])
    except Exception as exc:
        logger.error("list_applications failed: %s", exc)
        return jsonify([]), 200


@career_bp.route("/applications/<job_id>", methods=["GET"])
def get_application(job_id):
    """Return a single application record by job_id."""
    try:
        engine = _get_app_engine()
        record = engine._load_record(job_id)
        if record is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(record.__dict__)
    except Exception as exc:
        logger.error("get_application failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


@career_bp.route("/applications/<job_id>/confirm", methods=["POST"])
def confirm_application(job_id):
    """Approve a 'queued' application and submit it via the ApplicationEngine."""
    try:
        engine = _get_app_engine()
        record = engine._load_record(job_id)
        if record is None:
            return jsonify({"error": "application not found"}), 404
        if record.status != "queued":
            return jsonify({"error": f"Application is in '{record.status}' state, not 'queued'"}), 400
        from career.job_models import JobListing
        job = JobListing(
            title=record.notes or "Unknown",
            company="",
            location="",
            url="",
            source="",
        )
        job.id = job_id
        result = engine.apply(job, force=True)
        return jsonify({"status": result.status, "notes": result.notes})
    except Exception as exc:
        logger.error("confirm_application failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ─── CRM endpoints ────────────────────────────────────────────────────────────

@career_bp.route("/crm/contacts", methods=["GET"])
def list_contacts():
    """Return all recruiter contacts."""
    try:
        crm = _get_crm()
        contacts = crm.list_contacts()
        return jsonify([c.__dict__ for c in contacts])
    except Exception as exc:
        logger.error("list_contacts failed: %s", exc)
        return jsonify([]), 200


@career_bp.route("/crm/contacts", methods=["POST"])
def add_contact():
    """Add a new recruiter contact."""
    try:
        data = request.get_json(force=True)
        from career.job_models import RecruiterContact
        contact = RecruiterContact(
            name=data.get("name", ""),
            company=data.get("company", ""),
            email=data.get("email"),
            linkedin_url=data.get("linkedin_url"),
            phone=data.get("phone"),
            notes=data.get("notes", ""),
        )
        crm = _get_crm()
        crm.add_contact(contact)
        return jsonify({"id": contact.id, "name": contact.name}), 201
    except Exception as exc:
        logger.error("add_contact failed: %s", exc)
        return jsonify({"error": str(exc)}), 500


@career_bp.route("/crm/followups", methods=["GET"])
def pending_followups():
    """Return all pending (due today or earlier) follow-ups."""
    try:
        crm = _get_crm()
        return jsonify(crm.get_pending_followups())
    except Exception as exc:
        logger.error("pending_followups failed: %s", exc)
        return jsonify([]), 200


# ─── Health ───────────────────────────────────────────────────────────────────

@career_bp.route("/health", methods=["GET"])
def career_health():
    """Career sub-system health check."""
    services = {}
    try:
        _get_analytics()
        services["analytics_db"] = "ok"
    except Exception as e:
        services["analytics_db"] = f"error: {e}"

    try:
        _get_crm()
        services["crm_db"] = "ok"
    except Exception as e:
        services["crm_db"] = f"error: {e}"

    try:
        _get_app_engine()
        services["application_engine"] = "ok"
    except Exception as e:
        services["application_engine"] = f"error: {e}"

    status = "healthy" if all(v == "ok" for v in services.values()) else "degraded"
    return jsonify({"status": status, "services": services})


# ─── Standalone entrypoint ────────────────────────────────────────────────────

if __name__ == "__main__":
    # For local dev: python -m backend.career_api
    port = int(os.environ.get("CAREER_API_PORT", "8082"))
    _flask_app.run(host="0.0.0.0", port=port, debug=False)
