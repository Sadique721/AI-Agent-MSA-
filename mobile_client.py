#!/usr/bin/env python3
"""
Mobile client that sends audio to laptop server over WebSocket.
Run on Android using Termux.
"""

import asyncio
import websockets
import base64
try:
    import sounddevice as sd
except ImportError:
    pass
import numpy as np
import json

async def send_audio():
    # Replace laptop IP with your actual IP or dynamically fetch
    uri = "ws://127.0.0.1:5000"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to server. Recording...")
            while True:
                # Record 5 seconds of audio
                if 'sd' in globals():
                    audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1, dtype='int16')
                    sd.wait()
                    audio_bytes = audio.tobytes()
                    b64_audio = base64.b64encode(audio_bytes).decode()
                    await websocket.send(json.dumps({"audio": b64_audio}))
                    response = await websocket.recv()
                    print("Server response:", response)
                else:
                    await asyncio.sleep(5)
    except Exception as e:
        print(f"WS error: {e}")

if __name__ == "__main__":
    asyncio.run(send_audio())
