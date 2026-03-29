#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.speaker_verify import SpeakerVerifier
import sounddevice as sd
import soundfile as sf

def record_audio(duration=5, sample_rate=16000, filename="temp_enroll.wav"):
    print(f"Recording for {duration} seconds...")
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
    sd.wait()
    sf.write(filename, audio, sample_rate)
    return filename

def main():
    verifier = SpeakerVerifier()
    if verifier.is_enrolled():
        print("Already enrolled. To re-enroll, delete models/speaker/embedding.npy")
        return

    print("Please speak clearly for 5 seconds.")
    audio_file = record_audio()
    verifier.enroll(audio_file)
    print("Enrolment successful.")

if __name__ == "__main__":
    main()
