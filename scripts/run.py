#!/usr/bin/env python3
"""
scripts/run.py
==============
MSA Agent full runner: Flask server + wake-word loop.

FIX LOG:
  - Replaced non-existent SystemController class import with correct
    module-level function calls from scripts.system_control
  - All module inits wrapped in try/except for graceful degradation
  - record_audio() now handles sounddevice ImportError gracefully
  - Mobile controller wrapped in try/except
  - Added proper logging throughout
"""

import logging
import os
import sys
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("msa.runner")

# ---------------------------------------------------------------------------
# Lazy component holders
# ---------------------------------------------------------------------------
wake     = None
verifier = None
stt      = None
tts      = None
engine   = None
mem      = None
sec      = None
mobile   = None


# ---------------------------------------------------------------------------
def _safe_init(label: str, factory):
    """Run factory(); log and return None on failure."""
    try:
        obj = factory()
        logger.info("%s initialised OK.", label)
        return obj
    except Exception as e:
        logger.warning("%s init failed (continuing without it): %s", label, e)
        return None


# ---------------------------------------------------------------------------
def record_audio(duration: int = 5, sample_rate: int = 16000) -> bytes:
    """Record audio from microphone. Returns empty bytes if sounddevice missing."""
    try:
        import sounddevice as sd  # noqa: F401
        import numpy as np
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate,
                       channels=1, dtype="int16")
        sd.wait()
        return audio.tobytes()
    except ImportError:
        logger.warning("sounddevice not installed. Cannot record audio.")
        return b""
    except Exception as e:
        logger.error("Audio recording failed: %s", e)
        return b""


# ---------------------------------------------------------------------------
def execute_action(decision: dict) -> None:
    """Dispatch an action decision to the correct system handler."""
    action = decision.get("action", "none")
    params = decision.get("parameters", {})

    if action == "none":
        return

    if action == "open_app":
        try:
            from scripts.system_control import open_app  # module-level function
            open_app(params.get("app", "notepad"))
        except Exception as e:
            logger.error("open_app error: %s", e)

    elif action == "shutdown":
        try:
            import platform, os as _os  # noqa: F401
            if platform.system() == "Windows":
                _os.system("shutdown /s /t 10")
            else:
                _os.system("shutdown now")
        except Exception as e:
            logger.error("shutdown error: %s", e)

    elif action == "restart":
        try:
            import platform, os as _os  # noqa: F401
            if platform.system() == "Windows":
                _os.system("shutdown /r /t 10")
            else:
                _os.system("reboot")
        except Exception as e:
            logger.error("restart error: %s", e)

    elif action in ("mobile_open_app", "mobile_make_call", "mobile_set_alarm"):
        if mobile:
            try:
                if action == "mobile_open_app":
                    mobile.open_app(params.get("package", ""))
                elif action == "mobile_make_call":
                    mobile.make_call(params.get("number", ""))
                elif action == "mobile_set_alarm":
                    mobile.set_alarm(params.get("hour", "0"), params.get("minute", "0"))
            except Exception as e:
                logger.error("%s error: %s", action, e)
        else:
            logger.warning("Mobile action %s requested but no mobile device connected.", action)

    elif action == "internet_search":
        query = params.get("query", "")
        if query:
            try:
                from backend.internet import Internet
                net = Internet()
                result = net.search_and_summarize(query)
                logger.info("Search result preview: %s", result[:200])
            except Exception as e:
                logger.error("Internet search error: %s", e)


# ---------------------------------------------------------------------------
def main():
    global wake, verifier, stt, tts, engine, mem, sec, mobile

    logger.info("MSA Agent starting …")

    # Security (required for memory)
    sec = _safe_init("Security", lambda: __import__("backend.security", fromlist=["Security"]).Security())

    # Memory
    if sec:
        mem = _safe_init("Memory", lambda: __import__("memory.memory", fromlist=["Memory"]).Memory(sec))

    # Voice components
    wake     = _safe_init("WakeWordDetector", lambda: __import__("voice.wake_word", fromlist=["WakeWordDetector"]).WakeWordDetector())
    verifier = _safe_init("SpeakerVerifier",  lambda: __import__("voice.speaker_verify", fromlist=["SpeakerVerifier"]).SpeakerVerifier())
    stt      = _safe_init("STT",              lambda: __import__("voice.stt", fromlist=["STT"]).STT())
    tts      = _safe_init("TTS",              lambda: __import__("voice.tts", fromlist=["TTS"]).TTS())

    # AI engine
    engine = _safe_init("DecisionEngine", lambda: __import__("backend.decision_engine", fromlist=["DecisionEngine"]).DecisionEngine())

    # Mobile (optional)
    mobile_ip_file = os.path.join(PROJECT_ROOT, "mobile_ip.txt")
    if os.path.exists(mobile_ip_file):
        try:
            with open(mobile_ip_file) as f:
                ip = f.read().strip()
            if ip:
                mobile = _safe_init("MobileController", lambda: __import__("mobile_control.adb_controller", fromlist=["MobileController"]).MobileController(ip))
        except Exception as e:
            logger.warning("Mobile IP read error: %s", e)

    # Speaker enrollment check
    if verifier and not verifier.is_enrolled():
        logger.warning("No speaker enrolled. Run scripts/train_speaker.py first.")

    # Start Flask server in background daemon
    from backend.server import start_server
    server_thread = threading.Thread(target=start_server, name="msa-server", daemon=True)
    server_thread.start()
    logger.info("Flask server started on http://0.0.0.0:5000")

    logger.info("MSA ready. Listening for 'Hey MSA' …")

    # Main wake-word loop
    while True:
        try:
            triggered = wake.listen() if wake else False

            if not triggered:
                time.sleep(0.1)
                continue

            logger.info("Wake word detected. Recording command …")
            audio_bytes = record_audio(duration=5)

            if not audio_bytes:
                logger.warning("No audio recorded — skipping turn.")
                continue

            # Speaker verification
            if verifier and verifier.is_enrolled():
                if not verifier.verify(audio_bytes):
                    logger.warning("Speaker verification failed.")
                    if tts:
                        tts.speak("Sorry, I didn't recognize your voice.")
                    continue

            # Transcribe
            text = stt.transcribe(audio_bytes) if stt else ""
            if not text.strip():
                logger.info("Empty transcription — ignoring.")
                continue

            logger.info("You said: %r", text)

            # Decision
            context = mem.get_recent_context() if mem else []
            if engine:
                decision = engine.process_command(text, context)
            else:
                decision = {"response": f"MSA received: {text}", "action": "none", "parameters": {}}

            logger.info("Decision: %s", decision)

            # Speak response
            if tts and decision.get("response"):
                tts.speak(decision["response"])

            # Persist
            if mem:
                mem.add_conversation(text, decision.get("response", ""), decision.get("action", "none"))

            # Execute
            execute_action(decision)

            time.sleep(0.3)

        except KeyboardInterrupt:
            logger.info("Shutting down MSA Agent.")
            sys.exit(0)
        except Exception as e:
            logger.error("Main loop error: %s", e)
            time.sleep(1)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
