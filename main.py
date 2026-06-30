import logging
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
    logger.info("MSA AI AGENT initialising …")

    # Start background daemon
    # Start V5.0 background agent coordinator
    try:
        from backend.services.background_agent_coordinator import get_background_coordinator
        coordinator = get_background_coordinator()
        coordinator.start()
        logger.info("V5.0 Background Coordinator started.")
    except Exception as e:
        logger.error("Failed to start Background Coordinator: %s", e)

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
            target=lambda: uvicorn.run("backend.gateway_server:app", host="0.0.0.0", port=8000, log_level="warning"),
            name="msa-fastapi",
            daemon=True,
        )
        fastapi_thread.start()
        logger.info("FastAPI V5.0 Gateway started on port 8000 (daemon).")
    except Exception as e:
        logger.error("Failed to start FastAPI Gateway server: %s", e)

    # Start the web server (blocks until Ctrl+C)
    logger.info("Starting Wi-Fi server on port 5000 …")
    start_server(host="0.0.0.0", port=5000)

