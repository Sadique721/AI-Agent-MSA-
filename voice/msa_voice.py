"""
voice/msa_voice.py
==================
MSA voice assistant.

Pipeline:
  Microphone → Wake Word ("hey msa") → Listen → Send to /api/execute → Speak response

Features:
  - Wake word detection (offline, no cloud)
  - Speech recognition via Google API (or Vosk offline)
  - Text-to-speech via pyttsx3 (offline)
  - Personalized greeting using USER_PROFILE
  - Runs as a daemon thread alongside the Flask server
"""

import threading
import time
import logging
import requests

logger = logging.getLogger("msa.voice")

# ─── Config ───────────────────────────────────────────────────────────────────
SERVER_URL = "http://127.0.0.1:5000/api/execute"
API_KEY    = "MSA_SECURE_123"
WAKE_WORD  = "hey msa"

# ─── TTS Engine ───────────────────────────────────────────────────────────────
_tts_engine = None

def _get_tts():
    global _tts_engine
    if _tts_engine is None:
        try:
            import pyttsx3
            _tts_engine = pyttsx3.init()
            _tts_engine.setProperty("rate", 170)
            _tts_engine.setProperty("volume", 1.0)
            # Try to pick a clear English voice
            voices = _tts_engine.getProperty("voices")
            for v in voices:
                if "english" in v.name.lower():
                    _tts_engine.setProperty("voice", v.id)
                    break
        except Exception as e:
            logger.warning("TTS engine init failed: %s", e)
    return _tts_engine


def speak(text: str) -> None:
    """Speak text using pyttsx3 (offline)."""
    logger.info("MSA: %s", text)
    try:
        print(f"\n[MSA]: {text}\n", flush=True)
    except UnicodeEncodeError:
        print(f"\n[MSA]: {text.encode('ascii', errors='replace').decode()}\n", flush=True)
    engine = _get_tts()
    if engine:
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            logger.warning("TTS speak error: %s", e)


# ─── Speech Recognition ───────────────────────────────────────────────────────
def listen(timeout: int = 5, phrase_limit: int = 6) -> str:
    """
    Record audio from microphone and return recognized text.
    Falls back to empty string on any error.
    """
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        recognizer.pause_threshold  = 0.8
        recognizer.energy_threshold = 300

        with sr.Microphone() as source:
            print("🎤 Listening…")
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
            try:
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit,
                )
            except sr.WaitTimeoutError:
                return ""

        # Try Vosk offline first, then Google
        try:
            from voice.stt import STT
            stt = STT()
            if stt.is_ready():
                text = stt.transcribe(audio.get_raw_data(convert_rate=16000, convert_width=2))
                if text:
                    return text.lower().strip()
        except Exception:
            pass

        # Fallback: Google Speech Recognition (requires internet)
        try:
            text = recognizer.recognize_google(audio)
            return text.lower().strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            logger.warning("Google STT error: %s", e)
            return ""

    except ImportError:
        logger.error("SpeechRecognition not installed. Run: pip install SpeechRecognition pyaudio")
        return ""
    except Exception as e:
        logger.error("Listen error: %s", e)
        return ""


# ─── Agent Communication ──────────────────────────────────────────────────────
def send_command(command: str) -> str:
    """Send a text command to the MSA Agent API and return the response."""
    try:
        r = requests.post(
            SERVER_URL,
            json={"command": command},
            headers={"x-api-key": API_KEY},
            timeout=10,
        )
        data = r.json()
        return data.get("response", "No response from agent.")
    except requests.exceptions.ConnectionError:
        return "Agent server not reachable. Please wait a moment."
    except Exception as e:
        return f"Error communicating with agent: {e}"


# ─── Greeting ─────────────────────────────────────────────────────────────────
def _get_greeting() -> str:
    try:
        from config import USER_PROFILE
        name = USER_PROFILE.get("name", "").split()[0]  # First name only
        return f"Hello {name}, MSA is online and ready."
    except Exception:
        return "MSA is online and ready."


# ─── PyAudio check ────────────────────────────────────────────────────────────
def _pyaudio_available() -> bool:
    """Return True if PyAudio can be imported (microphone support available)."""
    try:
        import pyaudio  # noqa: F401
        return True
    except ImportError:
        return False


# ─── Main Loop ────────────────────────────────────────────────────────────────
def msa_voice_loop() -> None:
    """
    Continuous loop:
      1. Listen for wake word ("hey msa")
      2. Acknowledge
      3. Listen for the actual command
      4. Send to agent
      5. Speak response
    """
    logger.info("MSA voice loop started. Wake word: '%s'", WAKE_WORD)
    time.sleep(2)           # Allow server to start first

    # ── Check PyAudio availability once ──────────────────────────────────────
    if not _pyaudio_available():
        logger.warning(
            "PyAudio not found — voice input disabled. "
            "Install with: pip install pyaudio  (or pipwin install pyaudio on Windows). "
            "MSA thread will idle; web UI and text commands still work."
        )
        speak("MSA voice input is unavailable. Microphone support requires PyAudio.")
        # Idle forever — do NOT spin; web UI / text commands are unaffected
        while True:
            time.sleep(30)

    speak(_get_greeting())

    while True:
        try:
            audio_text = listen(timeout=8, phrase_limit=4)

            if not audio_text:
                continue

            if WAKE_WORD in audio_text:
                logger.info("Wake word detected!")
                speak("Yes Sadique, how can I help you?")

                # Listen for actual command
                command = listen(timeout=8, phrase_limit=8)
                if not command:
                    speak("I didn't catch that. Please try again.")
                    continue

                print(f"📝 Command: {command}")
                logger.info("Command received: %s", command)

                speak("Processing your command…")
                response = send_command(command)
                speak(response)

        except KeyboardInterrupt:
            speak("Shutting down MSA. Goodbye!")
            break
        except Exception as e:
            logger.error("MSA voice loop error: %s", e)
            time.sleep(1)


# ─── Public API ───────────────────────────────────────────────────────────────
def start_msa_voice() -> threading.Thread:
    """Start the MSA voice loop as a daemon thread."""
    t = threading.Thread(target=msa_voice_loop, name="MsaVoiceThread", daemon=True)
    t.start()
    logger.info("MSA voice thread started.")
    return t


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    msa_voice_loop()
