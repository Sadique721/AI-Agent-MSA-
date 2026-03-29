import torch
import torchaudio
import numpy as np
import os
try:
    from speechbrain.inference.speaker import SpeakerRecognition
except ImportError:
    try:
        from speechbrain.pretrained import SpeakerRecognition
    except ImportError:
        SpeakerRecognition = None


class SpeakerVerifier:
    def __init__(self, model_dir="models/speaker"):
        import os
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.model_dir = os.path.join(base_dir, model_dir)
        os.makedirs(self.model_dir, exist_ok=True)
        try:
            self.model = SpeakerRecognition.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir=self.model_dir
            )
        except Exception as e:
            print(f"SpeechBrain init failed: {e}")
            self.model = None
        
        self.enrolled_embedding = None
        self.embedding_path = os.path.join(self.model_dir, "embedding.npy")
        if os.path.exists(self.embedding_path):
            self.enrolled_embedding = np.load(self.embedding_path)

    def is_enrolled(self):
        return self.enrolled_embedding is not None

    def enroll(self, audio_path):
        """Enrol with a single audio file."""
        if not self.model: return
        signal, fs = torchaudio.load(audio_path)
        # Resample to 16kHz if needed
        if fs != 16000:
            resampler = torchaudio.transforms.Resample(fs, 16000)
            signal = resampler(signal)
        embedding = self.model.encode_batch(signal)
        self.enrolled_embedding = embedding.detach().cpu().numpy()
        np.save(self.embedding_path, self.enrolled_embedding)

    def verify(self, audio_bytes, threshold=0.75):
        """Verify against enrolled voice. audio_bytes is raw int16 data."""
        if self.enrolled_embedding is None or not self.model:
            return False
        # Convert bytes to tensor
        signal = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        signal = torch.from_numpy(signal).unsqueeze(0)
        # Assume 16kHz sample rate
        embedding = self.model.encode_batch(signal)
        score, prediction = self.model.verify_batch(
            torch.from_numpy(self.enrolled_embedding),
            embedding
        )
        return prediction.item() == 1 and score.item() > threshold
