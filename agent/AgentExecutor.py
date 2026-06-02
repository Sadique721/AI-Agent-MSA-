"""
agent/AgentExecutor.py
======================
Action dispatcher — translates decision engine output into real system actions.

Supported actions:
  open_app          → opens a desktop application
  shutdown          → shuts down the PC
  restart           → restarts the PC
  internet_search   → DuckDuckGo web search summary
  automation        → pyautogui-based automation (click, type, scroll)
  vision            → captures a screenshot / camera frame
  location          → returns current location info
  mobile_open_app   → opens an app on connected Android device
  mobile_make_call  → dials a number on Android device
  mobile_set_alarm  → sets alarm on Android device
  none              → no action (conversation only)
"""
import logging
import os
import platform
import subprocess
from typing import Dict

logger = logging.getLogger("msa.agent.executor")


class AgentExecutor:
    """Executes agent actions across system, mobile, web, and vision subsystems."""

    def __init__(self):
        self._system  = platform.system()   # "Windows" | "Linux" | "Darwin"
        self._mobile  = self._init_mobile()

    # ── Init ───────────────────────────────────────────────────────────────
    def _init_mobile(self):
        """Lazily connect to Android device via ADB if IP is configured."""
        try:
            ip_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mobile_ip.txt")
            if not os.path.exists(ip_file):
                return None
            with open(ip_file) as f:
                ip = f.read().strip()
            if not ip:
                return None
            from mobile_control.adb_controller import MobileController
            ctrl = MobileController(ip)
            logger.info("Mobile controller connected to %s", ip)
            return ctrl
        except Exception as e:
            logger.info("Mobile controller not available: %s", e)
            return None

    # ── Dispatch ───────────────────────────────────────────────────────────
    def execute(self, action: str, params: Dict) -> str:
        """
        Route an action to the correct handler.
        Returns a human-readable result string.
        """
        handlers = {
            "open_app":         self._open_app,
            "shutdown":         self._shutdown,
            "restart":          self._restart,
            "internet_search":  self._web_search,
            "automation":       self._automation,
            "vision":           self._vision_capture,
            "location":         self._get_location,
            "get_profile":      self._get_profile,
            "get_time":         self._get_time,
            "mobile_open_app":  self._mobile_open_app,
            "mobile_make_call": self._mobile_call,
            "mobile_set_alarm": self._mobile_alarm,
        }
        handler = handlers.get(action)
        if handler:
            try:
                return handler(params)
            except Exception as e:
                logger.error("Action '%s' failed: %s", action, e)
                return f"Action failed: {e}"
        return "No action taken."

    # ── System ─────────────────────────────────────────────────────────────
    def _open_app(self, params: Dict) -> str:
        app = params.get("app", "notepad").lower().strip()
        app_map = {
            "notepad":    "notepad.exe",
            "calculator": "calc.exe",
            "browser":    "start msedge",
            "chrome":     "start chrome",
            "cmd":        "cmd.exe",
            "settings":   "start ms-settings:",
            "vs code":    "code",
            "explorer":   "explorer.exe",
        }
        cmd = app_map.get(app, f"start {app}")
        try:
            if self._system == "Windows":
                subprocess.Popen(cmd, shell=True)
            elif self._system == "Darwin":
                subprocess.Popen(["open", "-a", app])
            else:
                subprocess.Popen([app])
            logger.info("Opened app: %s", app)
            return f"Opened {app} successfully."
        except Exception as e:
            return f"Could not open {app}: {e}"

    def _shutdown(self, params: Dict) -> str:
        delay = params.get("delay", 10)
        try:
            if self._system == "Windows":
                os.system(f"shutdown /s /t {delay}")
            else:
                os.system("shutdown now")
            return f"System will shut down in {delay} seconds."
        except Exception as e:
            return f"Shutdown failed: {e}"

    def _restart(self, params: Dict) -> str:
        delay = params.get("delay", 10)
        try:
            if self._system == "Windows":
                os.system(f"shutdown /r /t {delay}")
            else:
                os.system("reboot")
            return f"System will restart in {delay} seconds."
        except Exception as e:
            return f"Restart failed: {e}"

    # ── Web ────────────────────────────────────────────────────────────────
    def _web_search(self, params: Dict) -> str:
        query = params.get("query", "").strip()
        if not query:
            return "No search query provided."
        try:
            from backend.internet import Internet
            net = Internet()
            result = net.search_and_summarize(query)
            preview = result[:300] + "…" if len(result) > 300 else result
            logger.info("Web search for: %s", query)
            return preview or "No results found."
        except Exception as e:
            return f"Search error: {e}"

    # ── Automation ─────────────────────────────────────────────────────────
    def _automation(self, params: Dict) -> str:
        task = params.get("task", "")
        try:
            import pyautogui
            if "click" in task:
                pyautogui.click()
                return "Clicked at current cursor position."
            elif "scroll" in task:
                pyautogui.scroll(3)
                return "Scrolled down."
            return f"Automation task '{task}' received. Implement specific logic as needed."
        except ImportError:
            return "pyautogui not installed. Run: pip install pyautogui"
        except Exception as e:
            return f"Automation error: {e}"

    # ── Vision ─────────────────────────────────────────────────────────────
    def _vision_capture(self, params: Dict) -> str:
        try:
            from vision.camera import Camera
            cam = Camera()
            frame = cam.capture_frame()
            if frame is not None:
                import cv2, time
                path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    "data", f"capture_{int(time.time())}.jpg"
                )
                cv2.imwrite(path, frame)
                cam.release()
                return f"Camera frame captured and saved."
            cam.release()
            return "Camera capture failed — no frame returned."
        except ImportError:
            return "opencv-python not installed. Run: pip install opencv-python"
        except Exception as e:
            return f"Vision error: {e}"

    # ── Location ───────────────────────────────────────────────────────────
    def _get_location(self, params: Dict) -> str:
        return "Location updates are pushed by the mobile app via /api/location endpoint."

    # ── Profile ────────────────────────────────────────────────────────────
    def _get_profile(self, params: Dict) -> str:
        try:
            from config import USER_PROFILE
            p = USER_PROFILE
            skills = ", ".join(p.get("skills", []))
            return (
                f"Name: {p.get('name')} | Role: {p.get('role')} | "
                f"Study: {p.get('current_study')} | "
                f"Skills: {skills} | Project: {p.get('project')}"
            )
        except Exception as e:
            return f"Profile unavailable: {e}"

    # ── Time ───────────────────────────────────────────────────────────────
    def _get_time(self, params: Dict) -> str:
        from datetime import datetime
        now = datetime.now()
        return f"Current time is {now.strftime('%I:%M %p')} on {now.strftime('%A, %d %B %Y')}."


    def _mobile_open_app(self, params: Dict) -> str:
        if not self._mobile:
            return "No Android device connected. Set IP in mobile_ip.txt."
        pkg = params.get("package", "")
        self._mobile.open_app(pkg)
        return f"Opened {pkg} on mobile."

    def _mobile_call(self, params: Dict) -> str:
        if not self._mobile:
            return "No Android device connected."
        number = params.get("number", "")
        self._mobile.make_call(number)
        return f"Calling {number} on mobile."

    def _mobile_alarm(self, params: Dict) -> str:
        if not self._mobile:
            return "No Android device connected."
        h = params.get("hour", "0")
        m = params.get("minute", "0")
        self._mobile.set_alarm(h, m)
        return f"Alarm set for {h}:{m} on mobile."
