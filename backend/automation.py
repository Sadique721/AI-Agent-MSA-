try:
    import pyautogui
except ImportError:
    pyautogui = None
import time
import smtplib
from email.mime.text import MIMEText

class Automation:
    def __init__(self):
        pass

    def fill_form(self, field_coords, text, consent_callback):
        """Fill form fields with given text. Consent required."""
        if pyautogui and consent_callback():
            for x, y in field_coords:
                pyautogui.click(x, y)
                pyautogui.write(text)
                time.sleep(0.5)

    def send_email(self, to, subject, body, consent_callback):
        """Send email via SMTP (configured locally)."""
        if consent_callback():
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = "msa@localhost"
            msg['To'] = to
            # Use local SMTP server (e.g., postfix) or hardcoded credentials
            # For offline, assume a local SMTP relay
            try:
                with smtplib.SMTP('localhost', 25) as server:
                    server.send_message(msg)
            except Exception as e:
                print(f"Email failed mapping to localhost: {e}")
