import os
import vosk
import sys
import wave
import json

class VoiceRecognition:
    def __init__(self, model_path="models/vosk-model"):
        self.model_path = model_path
        if not os.path.exists(self.model_path):
            print(f"[MSA] Vosk model not found at {self.model_path}! Please download a lightweight model from https://alphacephei.com/vosk/models and extract it there.")
            self.model = None
        else:
            self.model = vosk.Model(self.model_path)

    def process_audio(self, filename: str):
        if not self.model:
            return "Voice model not loaded."
            
        wf = wave.open(filename, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            return "Audio file must be WAV format mono PCM."

        rec = vosk.KaldiRecognizer(self.model, wf.getframerate())
        rec.SetWords(True)

        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part_result = json.loads(rec.Result())
                if part_result.get("text", ""):
                    results.append(part_result["text"])
            
        part_result = json.loads(rec.FinalResult())
        if part_result.get("text", ""):
            results.append(part_result["text"])
        
        return " ".join(results)

vr = VoiceRecognition()
