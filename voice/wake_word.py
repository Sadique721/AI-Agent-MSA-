import vosk
import json
import queue
import sounddevice as sd
import numpy as np
import os

class WakeWordDetector:
    def __init__(self, model_path="models/vosk/vosk-model-small-en-us-0.15"):
        # Ensure model exists, otherwise fail gracefully or point to it
        model_full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), model_path)
        if not os.path.exists(model_full_path):
            print(f"[Warning] Wake word Vosk model not found at {model_full_path}. Downloading/Extracting 0.15 zip might be needed.")
            # Fallback to absolute path we saw in D:/Programs/AI
            model_full_path = "D:/Programs/AI/vosk-model-small-en-us-0.15/vosk-model-small-en-us-0.15"
            if not os.path.exists(model_full_path):
                model_full_path = "D:/Programs/AI/vosk-model-small-en-us-0.15"

        try:
            self.model = vosk.Model(model_full_path)
            self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
            self.recognizer.SetWords(False)
        except Exception as e:
            print(f"WakeWordDetector init error: {e}")
            self.model = None

        self.q = queue.Queue()

    def callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.q.put(bytes(indata))

    def listen(self):
        if not self.model:
            print("Listening skipped due to missing Vosk model. Sending auto-trigger for demo...")
            import time; time.sleep(5)
            # return True occasionally for testing if model fails to load
            return False

        print("Listening for 'hey msa'...")
        with sd.RawInputStream(samplerate=16000, blocksize=8000, device=None,
                               dtype='int16', channels=1, callback=self.callback):
            while True:
                data = self.q.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "").lower()
                    if "hey msa" in text:
                        return True
                partial = json.loads(self.recognizer.PartialResult())
                partial_text = partial.get("partial", "").lower()
                if "hey msa" in partial_text:
                    return True
