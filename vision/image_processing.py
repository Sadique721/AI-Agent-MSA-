import cv2
import threading

class VisionAgent:
    def __init__(self):
        self.camera_index = 0

    def capture_frame(self):
        cam = cv2.VideoCapture(self.camera_index)
        if not cam.isOpened():
            return "Failed to open camera"
        
        ret, frame = cam.read()
        cam.release()
        
        if ret:
            # We would run object detection here using a local TF/OpenCV model structure
            # For now, it simply captures the frame
            filename = "vision/latest_capture.jpg"
            cv2.imwrite(filename, frame)
            return "Frame captured and saved to vision folder."
        return "Failed to grab frame"

    def detect_objects(self):
        # Placeholder for full object detection implementation
        return "Object detection capability present but model not loaded."

vision = VisionAgent()
