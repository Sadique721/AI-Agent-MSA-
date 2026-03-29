import sqlite3
import json
import os
from datetime import datetime

class Memory:
    def __init__(self, security, db_path="data/memory/msa.db"):
        import os
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.db_path = os.path.join(base_dir, db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.sec = security
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_input TEXT,
                response TEXT,
                action TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        self.conn.commit()

    def add_conversation(self, user_input, response, action):
        encrypted_input = self.sec.encrypt(user_input).hex()
        encrypted_response = self.sec.encrypt(response).hex()
        self.conn.execute(
            "INSERT INTO conversations (timestamp, user_input, response, action) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), encrypted_input, encrypted_response, action)
        )
        self.conn.commit()

    def get_recent_context(self, limit=5):
        cursor = self.conn.execute(
            "SELECT user_input, response FROM conversations ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        rows = cursor.fetchall()
        context = []
        for enc_input, enc_response in rows:
            try:
                # Use bytes.fromhex to decode hex strings before decryption, if not empty
                user_input_bytes = bytes.fromhex(enc_input) if enc_input else b""
                response_bytes = bytes.fromhex(enc_response) if enc_response else b""
                user_input = self.sec.decrypt(user_input_bytes) if user_input_bytes else "null"
                response = self.sec.decrypt(response_bytes) if response_bytes else "null"
                context.append({"user": user_input, "assistant": response})
            except Exception as e:
                print(f"Memory crypto error: {e}")
        return context
