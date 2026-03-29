import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "memory", "msa.db")
PROFILE_PATH = os.path.join(os.path.dirname(__file__), "user_profile.json")

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # Create tables for conversations and profile memory
    c.execute('''CREATE TABLE IF NOT EXISTS memory
                 (id INTEGER PRIMARY KEY, interaction TEXT, response TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                 
    c.execute('''CREATE TABLE IF NOT EXISTS profile
                 (name TEXT PRIMARY KEY, role TEXT, last_known_lat REAL, last_known_lon REAL)''')
                 
    # Initialize basic profile if not exists
    c.execute("INSERT OR IGNORE INTO profile (name, role) VALUES ('Md Sadique Amin', 'Software Engineer')")
    
    conn.commit()
    conn.close()

    # ensure basic profile json as backup for other logic
    if not os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH, "w") as f:
            json.dump({
                "name": "Md Sadique Amin",
                "role": "software engineer",
                "preferences": []
            }, f, indent=4)
            
    print("Memory database initialized.")

if __name__ == "__main__":
    init_db()
