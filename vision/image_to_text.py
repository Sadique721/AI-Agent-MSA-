try:
    import pytesseract
except ImportError:
    pytesseract = None
import cv2

class ImageToText:
    def __init__(self):
        pass

    def extract_text(self, image):
        if pytesseract is None:
            return "OCR module missing."
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        text = pytesseract.image_to_string(gray)
        return text.strip()
