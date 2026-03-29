import pyttsx3

class TTS:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)

    def speak(self, text):
        try:
            print(f"MSA Agent Speaking: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
        except RuntimeError:
            pass # handle nested runAndWait issues depending on thread
