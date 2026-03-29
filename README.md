# MSA – Offline AI Agent

MSA is a fully offline, local AI agent that runs on your laptop and controls your mobile device over Wi‑Fi. It listens for "Hey MSA", verifies your voice, understands Hindi/Hinglish, and can perform system actions, control apps, automate tasks, and more – all without any cloud APIs.

## Features
- Offline voice recognition (Vosk / Whisper)
- Speaker verification (only you can activate it)
- Local LLM (Llama 2) for decision making
- Multi‑device control (laptop + Android via ADB)
- Image recognition with OpenCV
- Location tracking (via mobile)
- Encrypted local storage

## Installation

1. Clone this repository.
2. Place models in the `models/` directory:
   - Vosk models: download and put in `models/vosk/`.
   - Whisper models: download and place in `models/whisper.cpp/`.
   - LLM: download a quantized GGUF model and put in `models/llm/`.
3. Run `bash scripts/install_deps.sh` to install system dependencies.
4. Install Python packages: `pip install -r requirements.txt`
5. Enrol your voice: `python scripts/train_speaker.py`
6. Start the agent: `bash run.sh`
