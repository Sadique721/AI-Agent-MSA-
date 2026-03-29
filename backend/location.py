class LocationTracker:
    def __init__(self):
        self.current_location = None

    def update_location(self, lat, lon):
        self.current_location = (lat, lon)

    def get_contextual_advice(self):
        """Based on location, return advice."""
        if self.current_location:
            # Use local database or geocoding offline
            # For now, just a placeholder
            return "You are near a grocery store."
        return "Location unknown."
