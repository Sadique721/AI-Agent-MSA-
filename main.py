import threading
import time
from backend.server import start_server

def run_background_workers():
    print("[MSA] Starting background agents...")
    # Will integrate voice, memory, and vision modules here
    while True:
        time.sleep(1)

if __name__ == "__main__":
    print("[MSA] Initializing MSA AI Agent...")
    
    # Thread for background AI processes
    bg_thread = threading.Thread(target=run_background_workers, daemon=True)
    bg_thread.start()

    print("[MSA] Starting Wi-Fi server on port 8000...")
    # Start the fastAPI UI/Networking server
    start_server(host="0.0.0.0", port=8000)
