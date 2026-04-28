"""
config.py
=========
Central configuration for MSA AI Agent.
All paths, ports, and settings are defined here — import this instead of hardcoding.
"""
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# ── Model Paths ──────────────────────────────────────────────────────────────
MODEL_VOSK_PATH  = os.path.join(PROJECT_ROOT, "models", "vosk", "vosk-model-small-en-us-0.15")
MODEL_LLM_PATH   = os.path.join(PROJECT_ROOT, "models", "llm", "llama-2-7b-chat.Q4_K_M.gguf")
MODEL_SPEAKER_DIR= os.path.join(PROJECT_ROOT, "models", "speaker")

# ── Data Paths ───────────────────────────────────────────────────────────────
DB_PATH          = os.path.join(PROJECT_ROOT, "data", "memory", "msa.db")
KEY_FILE         = os.path.join(PROJECT_ROOT, "data", "encryption_key")
LOG_DIR          = os.path.join(PROJECT_ROOT, "data", "logs")
LOG_FILE         = os.path.join(LOG_DIR, "msa.log")
USER_PROFILE     = os.path.join(PROJECT_ROOT, "data", "user_profile.json")
MOBILE_IP_FILE   = os.path.join(PROJECT_ROOT, "mobile_ip.txt")

# ── Server ───────────────────────────────────────────────────────────────────
SERVER_HOST      = "0.0.0.0"
SERVER_PORT      = 5000
SECRET_KEY       = "msa-secret-key-change-in-production"

# ── Voice ────────────────────────────────────────────────────────────────────
SAMPLE_RATE      = 16000
CHUNK_SIZE       = 8000
RECORD_SECONDS   = 5
WAKE_WORD_PHRASE = "hey msa"

# ── Security ─────────────────────────────────────────────────────────────────
ENCRYPTION_ENABLED = True

# ── Mobile ADB ───────────────────────────────────────────────────────────────
MOBILE_ADB_PORT  = 5555

# ── Agent ────────────────────────────────────────────────────────────────────
CONTEXT_WINDOW   = 5    # How many past turns to include in context
MAX_KEYWORDS     = 8
