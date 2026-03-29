import subprocess
import os
import platform

class SystemController:
    def __init__(self):
        self.system = platform.system()

    def open_app(self, app_name):
        app_map = {
            "chrome": "google-chrome" if self.system == "Linux" else "chrome",
            "vs code": "code",
            "terminal": "gnome-terminal" if self.system == "Linux" else "cmd",
        }
        cmd = app_map.get(app_name.lower())
        if cmd:
            subprocess.Popen([cmd])
        else:
            # Fallback: try to run as is
            subprocess.Popen([app_name], shell=True)

    def shutdown(self):
        if self.system == "Windows":
            os.system("shutdown /s /t 1")
        elif self.system == "Linux":
            os.system("shutdown now")
        # macOS similar

    def restart(self):
        if self.system == "Windows":
            os.system("shutdown /r /t 1")
        elif self.system == "Linux":
            os.system("reboot")
