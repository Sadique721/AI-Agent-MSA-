"""
main.py
=======
MSA AI Agent — Primary Entry Point (thin launcher).

This file starts:
  1. A background daemon thread for future background workers
     (voice, memory sync, etc.)
  2. The Flask-SocketIO web server

FIX: start_server() previously called with (host, port) args but the old
     server.py signature accepted none.  Both are now aligned — server.py
     start_server() accepts optional host/port with sensible defaults.
"""

import logging
import threading
import time

from backend.server import start_server
from voice.msa_voice import start_msa_voice

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
    logger.info("MSA AI Agent initialising …")

    # Start background daemon
    bg_thread = threading.Thread(
        target=run_background_workers,
        name="msa-background",
        daemon=True,
    )
    bg_thread.start()
    logger.info("Background worker started (daemon).")

    # Start MSA voice assistant (daemon thread — wakes on 'hey msa')
    try:
        start_msa_voice()
        logger.info("MSA voice assistant started.")
    except Exception as e:
        logger.warning("MSA voice not available: %s", e)

    # Start the web server (blocks until Ctrl+C)
    logger.info("Starting Wi-Fi server on port 5000 …")
    start_server(host="0.0.0.0", port=5000)
