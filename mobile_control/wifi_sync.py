import socket
import json

class WifiSync:
    def __init__(self, host='0.0.0.0', port=5001):
        self.host = host
        self.port = port

    def send_command(self, command, params):
        """Send command to mobile client (if using a mobile app)."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port))
                s.sendall(json.dumps({"cmd": command, "params": params}).encode())
                response = s.recv(1024).decode()
                return json.loads(response)
        except Exception as e:
            return {"error": str(e)}
