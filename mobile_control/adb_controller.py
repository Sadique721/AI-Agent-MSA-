try:
    from adb_shell.adb_device import AdbDeviceTcp
    from adb_shell.auth import keygen
except ImportError:
    AdbDeviceTcp = None

class MobileController:
    def __init__(self, ip, port=5555):
        if not AdbDeviceTcp: return
        self.device = AdbDeviceTcp(ip, port)
        try:
            self.device.connect(rsa_keys=[keygen.RsaKey()])
        except Exception as e:
            print(f"ADB Connection error: {e}")

    def open_app(self, package_name):
        """Launch an app by package name."""
        if hasattr(self, 'device'):
            self.device.shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")

    def make_call(self, number):
        """Initiate a call."""
        if hasattr(self, 'device'):
            self.device.shell(f"am start -a android.intent.action.CALL -d tel:{number}")

    def set_alarm(self, hour, minute):
        """Set an alarm."""
        if hasattr(self, 'device'):
            self.device.shell(f"am start -a android.intent.action.SET_ALARM -e android.intent.extra.alarm.HOUR {hour} -e android.intent.extra.alarm.MINUTES {minute}")

    def get_location(self):
        """Get GPS coordinates (requires location permission on device)."""
        # This might need a more complex approach, e.g., using `dumpsys location`
        if hasattr(self, 'device'):
            output = self.device.shell("dumpsys location")
            return None
        return None
