from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

# Internal Modules
from scripts.system_control import perform_operation
from scripts.web_search import agent
from voice.tts import tts_engine
from vision.image_processing import vision
from mobile_control.location import tracker
from data.memory import memory

router = APIRouter()

class CommandRequest(BaseModel):
    command: str
    target: Optional[str] = None

class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    notes: Optional[str] = ""

@router.post("/execute")
async def execute_command(req: CommandRequest):
    """Executes a text command from UI/Mobile"""
    response_text = ""
    cmd = req.command.lower()
    
    if "open" in cmd:
        target = req.target if req.target else cmd.replace("open ", "").strip()
        response_text = perform_operation("open", target)
    elif "search" in cmd:
        target = req.target if req.target else cmd.replace("search ", "").strip()
        response_text = agent.search(target)
    elif "capture" in cmd or "vision" in cmd:
        response_text = vision.capture_frame()
    else:
        # Could feed into an LLM here, for now fallback to simple echo
        response_text = f"MSA received command: {cmd}"

    # Save to memory
    memory.add_interaction(cmd, response_text)
    
    # Speak the response on the host laptop (if TTS is enabled)
    tts_engine.speak(response_text)
    
    return {"status": "success", "response": response_text}

@router.post("/location")
async def update_location(loc: LocationRequest):
    """Receives GPS location from mobile phone via Wi-Fi and stores privately."""
    result = tracker.log_location(loc.latitude, loc.longitude, loc.notes)
    return result

@router.get("/history")
async def get_history():
    """Retrieve recent conversation history."""
    return {"history": memory.get_recent_history(10)}
