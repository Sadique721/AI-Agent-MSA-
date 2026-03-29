#!/usr/bin/env python3
"""
Main entry point for MSA agent.
Runs the Flask server and the wake-word listening loop.
"""

import threading
import time
import json
import os
import sys
import base64
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from voice.wake_word import WakeWordDetector
from voice.speaker_verify import SpeakerVerifier
from voice.stt import STT
from voice.tts import TTS
from backend.decision_engine import DecisionEngine
from backend.system_control import SystemController
from mobile_control.adb_controller import MobileController
from backend.security import Security
from memory.memory import Memory
from backend.server import start_server

# Global components
wake = None
verifier = None
stt = None
tts = None
engine = None
sys_ctrl = None
mobile = None
mem = None
sec = None

def record_audio(duration=5, sample_rate=16000):
    """Record audio from microphone for given duration."""
    import sounddevice as sd
    import numpy as np
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()
    return audio.tobytes()

def main():
    global wake, verifier, stt, tts, engine, sys_ctrl, mobile, mem, sec

    print("Initializing MSA...")

    # Load security (encryption key)
    sec = Security()

    # Initialize components
    wake = WakeWordDetector()
    verifier = SpeakerVerifier()
    stt = STT()
    tts = TTS()
    engine = DecisionEngine()
    sys_ctrl = SystemController()
    mem = Memory(sec)

    # Check if speaker is enrolled
    if not verifier.is_enrolled():
        print("No speaker enrolled. Please run scripts/train_speaker.py first.")
        # Proceeding anyway for demonstration or to allow initial bootstrapping
        # sys.exit(1)

    # Connect to mobile via ADB (if IP is configured)
    mobile_ip = None
    try:
        with open("mobile_ip.txt", "r") as f:
            mobile_ip = f.read().strip()
    except:
        print("No mobile IP configured. Mobile control will be disabled.")
    if mobile_ip:
        try:
            mobile = MobileController(mobile_ip)
        except Exception as e:
            print(f"Mobile IP found but Connection failed: {e}")

    # Start Flask server in background
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    print("Server started on http://0.0.0.0:5000")

    print("MSA ready. Say 'Hey MSA' to wake me.")

    # Main loop
    while True:
        try:
            # Wait for wake word
            if wake.listen():
                print("Wake word detected. Recording command...")
                audio_bytes = record_audio(duration=5)

                # Verify speaker
                if verifier.is_enrolled() and not verifier.verify(audio_bytes):
                    print("Speaker verification failed. Ignoring.")
                    tts.speak("Sorry, I didn't recognize your voice.")
                    continue

                # Transcribe
                text = stt.transcribe(audio_bytes)
                print(f"You said: {text}")

                if not text.strip():
                    continue

                # Get context from memory
                context = mem.get_recent_context()

                # Decision
                decision = engine.process_command(text, context)
                print(f"Decision: {decision}")

                # Respond verbally
                tts.speak(decision["response"])

                # Store in memory
                mem.add_conversation(text, decision["response"], decision["action"])

                # Execute action if needed
                if decision["action"] and decision["action"] != "none":
                    params = decision.get("parameters", {})
                    if decision["action"] == "open_app":
                        sys_ctrl.open_app(params.get("app", "notepad"))
                    elif decision["action"] == "shutdown":
                        sys_ctrl.shutdown()
                    elif decision["action"] == "restart":
                        sys_ctrl.restart()
                    elif decision["action"] == "mobile_open_app":
                        if mobile:
                            mobile.open_app(params.get("package", ""))
                    elif decision["action"] == "mobile_make_call":
                        if mobile:
                            mobile.make_call(params.get("number", ""))
                    elif decision["action"] == "mobile_set_alarm":
                        if mobile:
                            mobile.set_alarm(params.get("hour", "0"), params.get("minute", "0"))

                time.sleep(0.5)
        except KeyboardInterrupt:
            print("Shutting down...")
            sys.exit(0)
        except Exception as e:
            print(f"Error in main loop: {e}")

if __name__ == "__main__":
    main()
