import os
import logging
from typing import Dict, Any

logger = logging.getLogger("msa.agent.tools.gui_automation")

def execute_gui_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a desktop GUI automation action securely.
    Falls back to mock simulation if pyautogui is not installed or in headless environments.
    """
    try:
        import pyautogui  # type: ignore
        _PYAUTOGUI_OK = True
    except ImportError:
        _PYAUTOGUI_OK = False

    logger.info("Executing GUI action: %s with params: %s", action, params)

    if not _PYAUTOGUI_OK:
        return {
            "success": True,
            "status": "simulated",
            "message": f"Action '{action}' was simulated successfully."
        }

    try:
        # Failsafe will trigger if mouse is moved to any corner of the screen
        pyautogui.FAILSAFE = True

        if action == "click":
            x = int(params.get("x", 0))
            y = int(params.get("y", 0))
            pyautogui.click(x, y)
            return {"success": True, "message": f"Clicked at coordinates ({x}, {y})"}

        elif action == "type":
            text = str(params.get("text", ""))
            pyautogui.write(text, interval=0.1)
            return {"success": True, "message": "Typed text successfully"}

        elif action == "screenshot":
            filename = str(params.get("filename", "screenshot.png"))
            filename = os.path.basename(filename)
            pyautogui.screenshot(filename)
            return {"success": True, "message": f"Saved screenshot as {filename}"}

        else:
            return {"success": False, "error": f"Unknown GUI action: {action}"}

    except Exception as e:
        logger.error("GUI action failed: %s", e)
        return {"success": False, "error": str(e)}
