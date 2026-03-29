#!/bin/bash
echo "Installing MSA Dependencies Locally..."

# Create core dirs purely to enforce structure if empty
mkdir -p data/memory data/logs models/vosk models/speaker models/whisper.cpp models/llm models/cv

# Install standard py libs
pip install -r requirements.txt

echo "Note: Core models like Vosk and Quantized LLaMA-2 need to be manually downloaded since they are massive."
echo "1. wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip -O models/vosk/vosk-model-small-en-us-0.15.zip"
echo "2. unzip it"
echo "\nDone with local pip installations."
