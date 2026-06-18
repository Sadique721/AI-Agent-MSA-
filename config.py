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
USER_PROFILE_PATH = os.path.join(PROJECT_ROOT, "data", "user_profile.json")
MOBILE_IP_FILE   = os.path.join(PROJECT_ROOT, "mobile_ip.txt")

# ── Server ───────────────────────────────────────────────────────────────────
SERVER_HOST      = "0.0.0.0"
SERVER_PORT      = 5000
SECRET_KEY       = os.environ.get("MSA_SECRET_KEY", "msa-secret-key-change-in-production")

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

# ── Security ─────────────────────────────────────────────────────────────────
API_KEY          = "MSA_SECURE_123"   # Change this in production!

# ── User Profile (safe internal storage — never sent to external APIs) ────────
USER_PROFILE_DATA = {
    "name":            "Md Sadique Amin",
    "role":            "Software Engineer",
    "email":           "mdsadiqueamin721786@gmail.com",
    "phone":           "9318302850",
    "education":       "Diploma - MANUU Bangalore",
    "current_study":   "B.Tech CSE (8th Semester) - GEC Patan",
    "skills": [
        "Java", "Spring Boot", "Servlet", "JSP",
        "MySQL", "JDBC", "JavaScript",
        "Python", "AI/ML", "Data Science"
    ],
    "project": "MSA AI Agent - Offline Multi Device AI Assistant"
}

# ═══════════════════════════════════════════════════════════════════════════════
# NEW: Architecture Upgrade Feature Flags
# Set any flag to False to disable that subsystem (backward-compatible)
# ═══════════════════════════════════════════════════════════════════════════════

# Upgrade 1: Hinglish / Hindi / English Language Engine
ENABLE_HINGLISH_ENGINE = True

# Upgrade 2: Multi-step Planner Agent
ENABLE_PLANNER         = True

# Upgrade 3: RAG Memory (FAISS + SQLite semantic search)
ENABLE_RAG_MEMORY      = True

# Upgrade 4: Playwright Browser Agent
ENABLE_BROWSER_AGENT   = True

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE-2: Reasoning-Based Autonomous Agent Feature Flags
# ═══════════════════════════════════════════════════════════════════════════════

# Upgrade 5: Reasoning Engine — goal extraction, risk detection, dependency graph
ENABLE_REASONING_ENGINE  = True

# Upgrade 6: Validator — step / result / final output validation
ENABLE_VALIDATOR         = True

# Upgrade 7: Auto-Replan — retry on failure up to MAX_REPLAN_RETRIES times
ENABLE_AUTO_REPLAN       = True

# Upgrade 8: Mobile Reasoning — device capability context from Android APK
ENABLE_MOBILE_REASONING  = True

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE-3: Coding Agent Feature Flags
# ═══════════════════════════════════════════════════════════════════════════════
ENABLE_CODING_AGENT         = True
ENABLE_STACKTRACE_ANALYZER  = True
ENABLE_BUG_ANALYZER         = True
ENABLE_CODE_GENERATOR       = True
ENABLE_TEST_GENERATOR       = True
ENABLE_CODE_REVIEW          = True
ENABLE_PROJECT_GENERATOR    = True
ENABLE_REFACTOR_ENGINE      = True
ENABLE_CODE_EXPLAINER       = True

# Maximum number of replan attempts before giving up
MAX_REPLAN_RETRIES       = 3

# ── RAG Memory Paths ──────────────────────────────────────────────────────────
FAISS_INDEX_PATH  = os.path.join(PROJECT_ROOT, "data", "memory", "msa_vectors.faiss")
FAISS_META_PATH   = os.path.join(PROJECT_ROOT, "data", "memory", "msa_vectors_meta.json")
# Offline embedding model (downloads ~80 MB once, fully offline after that)
EMBEDDING_MODEL   = "sentence-transformers/all-MiniLM-L6-v2"

# ── Browser Agent Config ──────────────────────────────────────────────────────
BROWSER_HEADLESS   = False          # False = visible browser window
BROWSER_TYPE       = "chromium"     # chromium | firefox | webkit
BROWSER_TIMEOUT_MS = 30000          # 30-second page load timeout
