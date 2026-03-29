import cv2

class Camera:
    def __init__(self, source=0):
        self.cap = cv2.VideoCapture(source)

    def capture_frame(self):
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None

    def release(self):
        self.cap.release()
