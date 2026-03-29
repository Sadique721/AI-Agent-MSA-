from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import base64
import json
import os
import sys

# Adding project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.stt import STT
from backend.decision_engine import DecisionEngine
from memory.memory import Memory
from backend.security import Security

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

stt = None
engine = None
mem = None
    
@socketio.on('audio')
def handle_audio(data):
    global stt, engine, mem
    if not stt:
        stt = STT()
        engine = DecisionEngine()
        mem = Memory(Security())

    audio_bytes = base64.b64decode(data['audio'])
    text = stt.transcribe(audio_bytes)
    context = mem.get_recent_context()
    decision = engine.process_command(text, context)
    emit('response', {'text': decision['response'], 'action': decision['action'], 'params': decision.get('parameters', {})})

def start_server():
    print("SocketIO wrapper active on 5000")
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    start_server()
