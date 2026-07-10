"""
backend/vault.py
=================
Secure in-memory + on-disk secret store. Reuses the SAME persisted
encryption key as backend/security.py (config.KEY_FILE) — secrets remain
readable across restarts, unlike a vault that generates a fresh key
every time it's instantiated.
"""
import os
import json
import logging
from typing import Optional
from cryptography.fernet import Fernet
from config import KEY_FILE

logger = logging.getLogger("msa.vault")

_VAULT_FILE = os.path.join(os.path.dirname(KEY_FILE), "vault_store.enc")


class SecureVault:
    def __init__(self):
        self.cipher = Fernet(self._load_or_create_key())
        self._store: dict = self._load_store()

    def _load_or_create_key(self) -> bytes:
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, "rb") as f:
                return f.read()
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
        with open(KEY_FILE, "wb") as f:
            f.write(key)
        return key

    def _load_store(self) -> dict:
        if os.path.exists(_VAULT_FILE):
            try:
                with open(_VAULT_FILE, "rb") as f:
                    decrypted = self.cipher.decrypt(f.read())
                    return json.loads(decrypted.decode())
            except Exception as e:
                logger.warning("Vault load failed (will start empty): %s", e)
        return {}

    def _persist(self) -> None:
        payload = json.dumps(self._store).encode()
        encrypted = self.cipher.encrypt(payload)
        with open(_VAULT_FILE, "wb") as f:
            f.write(encrypted)

    def store(self, key: str, secret: str) -> None:
        self._store[key] = secret
        self._persist()

    def retrieve(self, key: str) -> Optional[str]:
        return self._store.get(key)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._persist()
