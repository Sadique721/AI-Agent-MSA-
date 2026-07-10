"""
voice/stt.py
============
Speech-to-Text using Vosk (offline).

FIX LOG:
  - Removed brittle hardcoded absolute path fallback
  - Dynamic model path discovery: scans project root for vosk-model* dirs
  - Proper logging replacing bare print()
  - Graceful degradation when model is absent
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger("msa.voice.stt")

try:
    import vosk
    _VOSK_OK = True
except ImportError:
    _VOSK_OK = False
    logger.warning("vosk not installed. STT disabled. Run: pip install vosk")


def _find_vosk_model() -> str | None:
    """
    Dynamically locate a Vosk model directory.

    Search order:
      1. models/vosk/vosk-model-small-en-us-0.15   (standard project layout)
      2. Any directory matching vosk-model* directly under project root
      3. Any vosk-model* inside a subdirectory under project root
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 1. Canonical path
    canonical = os.path.join(project_root, "models", "vosk", "vosk-model-small-en-us-0.15")
    if os.path.isdir(canonical):
        return canonical

    # 2. Top-level vosk-model* dirs
    try:
        for entry in os.listdir(project_root):
            full = os.path.join(project_root, entry)
            if os.path.isdir(full) and entry.lower().startswith("vosk-model"):
                # May be the model itself or a wrapper dir containing the model
                inner = os.path.join(full, entry)
                if os.path.isdir(inner):
                    return inner
                return full
    except OSError:
        pass

    # 3. One level deeper
    try:
        for parent in os.listdir(project_root):
            parent_full = os.path.join(project_root, parent)
            if not os.path.isdir(parent_full):
                continue
            for child in os.listdir(parent_full):
                if child.lower().startswith("vosk-model"):
                    return os.path.join(parent_full, child)
    except OSError:
        pass

    return None


class STT:
    """Offline Speech-to-Text using Vosk KaldiRecognizer."""

    def __init__(self, model_path: str | None = None):
        self.model = None
        self.rec   = None

        if not _VOSK_OK:
            return

        resolved = model_path or _find_vosk_model()
        if not resolved or not os.path.isdir(resolved):
            logger.warning(
                "STT: Vosk model not found. Provide a model at models/vosk/ "
                "from https://alphacephei.com/vosk/models"
            )
            return

        try:
            self.model = vosk.Model(resolved)
            self.rec   = vosk.KaldiRecognizer(self.model, 16000)
            logger.info("STT: Vosk model loaded from %s", resolved)
        except Exception as e:
            logger.error("STT: Model load failed: %s", e)

    # -----------------------------------------------------------------------
    def transcribe(self, audio_bytes: bytes) -> str:
        """Convert raw 16-bit 16 kHz audio bytes to text. Returns '' on failure."""
        if self.rec is None or self.model is None:
            return ""
        try:
            if self.rec.AcceptWaveform(audio_bytes):
                result = json.loads(self.rec.Result())
                return result.get("text", "")
            partial = json.loads(self.rec.PartialResult())
            return partial.get("partial", "")
        except Exception as e:
            logger.error("STT.transcribe error: %s", e)
            return ""

    # -----------------------------------------------------------------------
    def is_ready(self) -> bool:
        return self.model is not None and self.rec is not None
