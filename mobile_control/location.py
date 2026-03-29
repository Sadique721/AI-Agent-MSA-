from data.memory import memory

class LocationTracker:
    def __init__(self):
        pass

    def log_location(self, lat: float, lon: float, notes: str = ""):
        # Save securely to local SQLite DB
        memory.add_location(lat, lon, notes)
        return {"status": "success", "message": "Location saved locally."}

tracker = LocationTracker()
