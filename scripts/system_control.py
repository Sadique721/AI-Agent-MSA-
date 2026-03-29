import os
import subprocess

def open_app(app_name: str) -> str:
    """Opens a system app or executable"""
    apps = {
        "calculator": "calc.exe",
        "notepad": "notepad.exe",
        "browser": "start msedge", # or chrome
        "cmd": "cmd.exe",
        "settings": "start ms-settings:"
    }
    app_name = app_name.lower()
    if app_name in apps:
        os.system(apps[app_name])
        return f"Opened {app_name}"
    else:
        # Generic fallback
        os.system(f"start {app_name}")
        return f"Attempted to open {app_name}"

def set_volume(level: int):
    """Adjusts system volume (Windows)
    Requires basic nircmd or powershell script.
    """
    # Using powershell as a native fallback
    vol_script = f"(Set-AudioDevice -PlaybackVolume {level})" # Placeholder for proper PS script
    # Actually, a safer generic volume control for python needs pycaw. For now, mute/unmute is easy or using third party tool.
    return "Volume control requires specific permissions or packages like pycaw."

def perform_operation(action: str, target: str):
    if action == "open":
        return open_app(target)
    return "Unknown action"
