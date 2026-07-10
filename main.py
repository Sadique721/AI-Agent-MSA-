import logging
import os
import signal
import sys
import threading
import time

from backend.server import start_server

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("msa.main")


# ---------------------------------------------------------------------------
# Background worker (placeholder — extend as needed)
# ---------------------------------------------------------------------------
def run_background_workers() -> None:
    """
    Daemon thread for background tasks:
      - Future: periodic memory sync
      - Future: ambient voice/wake-word monitoring
      - Future: health-check pings
    """
    logger.info("Background worker thread started.")
    while True:
        # Intentionally idle — wake-word loop lives in scripts/run.py
        time.sleep(5)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import os
    os.environ["MSA_AUTO_APPROVE"] = "true"

    # ── Read ports from env (Docker overrides these) ─────────────────────
    FLASK_PORT   = int(os.environ.get("PORT", 5000))
    FASTAPI_PORT = int(os.environ.get("FASTAPI_PORT", 8000))

    # ── Graceful shutdown handler (Docker SIGTERM) ─────────────────────
    def _graceful_shutdown(signum, frame):
        logger.info("SIGTERM received — graceful shutdown initiated.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _graceful_shutdown)
    signal.signal(signal.SIGINT,  _graceful_shutdown)

    logger.info("MSA AI AGENT initialising …")
    logger.info("Flask port: %d  |  FastAPI port: %d", FLASK_PORT, FASTAPI_PORT)

    # Start background daemon
    # Start V5.0 background agent coordinator
    try:
        from backend.services.background_agent_coordinator import get_background_coordinator
        coordinator = get_background_coordinator()
        coordinator.start()
        logger.info("V5.0 Background Coordinator started.")
    except Exception as e:
        logger.error("Failed to start Background Coordinator: %s", e)

    # ── Additive: Swarm + GraphRAG + Vault + MCP hooks (V6 Ultra Pro Max) ────────
    try:
        from ai_core.llm_manager import LLMManager
        from agent.swarm import SwarmCoordinator
        from automation.execution_engine import WorkflowEngine

        _llm = LLMManager()
        _swarm = SwarmCoordinator(_llm)
        _workflow_engine = WorkflowEngine(_swarm)
        logger.info("V6 Swarm + Workflow engine initialised.")
    except Exception as e:
        logger.warning("V6 Swarm engine not available: %s", e)

    try:
        from backend.vault import SecureVault
        _vault = SecureVault()
        logger.info("Secure vault initialised (persisted key).")
    except Exception as e:
        logger.warning("Vault not available: %s", e)

    try:
        from backend.mcp.mcp_registry import MCPRegistry  # existing registry
        from backend.mcp.tool_hooks import register_local_hooks
        _mcp_registry = MCPRegistry()
        register_local_hooks(_mcp_registry)
        logger.info("MCP local tool hooks registered into existing registry.")
    except Exception as e:
        logger.warning("MCP tool hooks not available: %s", e)

    # Start MSA voice assistant (daemon thread — wakes on 'hey msa')
    # FIX: Import moved inside try block so voice module absence does NOT crash server
    try:
        from voice.msa_voice import start_msa_voice
        start_msa_voice()
        logger.info("MSA voice assistant started.")
    except Exception as e:
        logger.warning("MSA voice not available: %s", e)

    # Start the FastAPI V5.0 Gateway server (daemon thread)
    try:
        import uvicorn
        fastapi_thread = threading.Thread(
            target=lambda: uvicorn.run("backend.gateway_server:app", host="0.0.0.0", port=FASTAPI_PORT, log_level="warning"),
            name="msa-fastapi",
            daemon=True,
        )
        fastapi_thread.start()
        logger.info("FastAPI V5.0 Gateway started on port %d (daemon).", FASTAPI_PORT)
    except Exception as e:
        logger.error("Failed to start FastAPI Gateway server: %s", e)

    # Start the web server (blocks until Ctrl+C / SIGTERM)
    logger.info("Starting Flask Socket.IO server on port %d …", FLASK_PORT)
    start_server(host="0.0.0.0", port=FLASK_PORT)

