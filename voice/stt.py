import vosk
import json
import numpy as np

class STT:
    def __init__(self, model_path="models/vosk/vosk-model-small-en-us-0.15"):
        import os
        model_full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), model_path)
        if not os.path.exists(model_full_path):
            # fallback
            model_full_path = "D:/Programs/AI/vosk-model-small-en-us-0.15/vosk-model-small-en-us-0.15"
            if not os.path.exists(model_full_path):
                print(f"[Warning] STT Vosk model missing at {model_full_path}. STT will return empty.")
                self.model = None
                return

        self.model = vosk.Model(model_full_path)
        self.rec = vosk.KaldiRecognizer(self.model, 16000)

    def transcribe(self, audio_bytes):
        """Convert audio bytes to text."""
        if not hasattr(self, 'rec') or self.model is None:
            return ""
            
        if self.rec.AcceptWaveform(audio_bytes):
            result = json.loads(self.rec.Result())
            return result.get("text", "")
        return ""
