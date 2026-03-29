from cryptography.fernet import Fernet
import os

class Security:
    def __init__(self, key_file="data/encryption_key"):
        self.key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), key_file)
        # Ensure dir exists
        os.makedirs(os.path.dirname(self.key_file), exist_ok=True)
        self.key = self.load_or_generate_key()
        self.cipher = Fernet(self.key)

    def load_or_generate_key(self):
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            return key

    def encrypt(self, data):
        if isinstance(data, str):
            data = data.encode()
        return self.cipher.encrypt(data)

    def decrypt(self, token):
        if isinstance(token, str):
            token = token.encode()
        return self.cipher.decrypt(token).decode()
