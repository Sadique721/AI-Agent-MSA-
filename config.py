"""
config.py
=========
Central configuration for MSA AI Agent.
All paths, ports, and settings are defined here — import this instead of hardcoding.
"""
import os
from typing import Set

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
# SECURITY: Never hardcode API keys. Always read from environment.
API_KEY          = os.environ.get("MSA_API_KEY", "")  # Set MSA_API_KEY in .env

# ── User Profile (safe internal storage — never sent to external APIs) ────────
# NOTE: PII (email, phone) moved to environment variables / user_profile.json
# Override via data/user_profile.json or set MSA_USER_EMAIL / MSA_USER_PHONE in .env
USER_PROFILE_DATA = {
    "name":            os.environ.get("MSA_USER_NAME", "Md Sadique Amin"),
    "role":            "Full Stack Developer | AI Engineer | Data Scientist",
    "email":           os.environ.get("MSA_USER_EMAIL", ""),  # Set in .env — never hardcode PII
    "phone":           os.environ.get("MSA_USER_PHONE", ""),  # Set in .env — never hardcode PII
    "education":       "BE (Computer Science) - Government Engineering College, Patan (7.9 CGPA) | Diploma (CS) - MANUU Polytechnic Bangalore (87.3%)",
    "current_study":   "BE CSE - GEC Patan",
    "skills": [
        "Java", "Spring Boot", "Spring Cloud", "Python", "Django", "Flask",
        "React.js", "MySQL", "MongoDB", "PostgreSQL", "Machine Learning",
        "Deep Learning", "NLP", "Computer Vision", "TensorFlow", "PyTorch",
        "Docker", "Git", "AWS", "Apache Spark", "Kafka"
    ],
    "project":         "Entitykart E-commerce, Entitykart Microservices, AI Agent MSA System, Image Recognition AI, Sentiment Analysis NLP, Predictive Analytics Dashboard, Real-time Data Streaming"
}

# Try loading user profile JSON if exists, fallback to USER_PROFILE_DATA
import json
USER_PROFILE = USER_PROFILE_DATA
if os.path.exists(USER_PROFILE_PATH):
    try:
        with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
            USER_PROFILE = json.load(f)
    except Exception:
        pass

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

# Vector Database Backend
VECTOR_BACKEND = os.environ.get("MSA_VECTOR_BACKEND", "faiss")  # "faiss" (default) or "qdrant"

# ── V7: Graph RAG (Neo4j — optional, fully local via Docker) ─────────────────
# Set ENABLE_NEO4J=true only when you have Neo4j running locally.
# If False (default), GraphRAGCore falls back to FAISS-only retrieval.
ENABLE_NEO4J      = os.environ.get("ENABLE_NEO4J", "false").lower() == "true"
NEO4J_URI         = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER        = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD    = os.environ.get("NEO4J_PASSWORD", "")

# ═══════════════════════════════════════════════════════════════════════════════
# V7: Career Intelligence Platform
# ═══════════════════════════════════════════════════════════════════════════════

ENABLE_JOB_DISCOVERY     = True
JOB_SOURCES              = ["linkedin", "indeed", "adzuna"]  # active sources
ADZUNA_APP_ID            = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_API_KEY           = os.environ.get("ADZUNA_API_KEY", "")
JOOBLE_API_KEY           = os.environ.get("JOOBLE_API_KEY", "")
JSEARCH_API_KEY          = os.environ.get("JSEARCH_API_KEY", "")  # RapidAPI JSearch
JOB_SEARCH_LOCATION      = "India"
JOB_SEARCH_DEFAULT_QUERY = "Software Engineer"
RESUME_DIR               = os.path.join(PROJECT_ROOT, "data", "resumes")
APPLICATIONS_DB          = os.path.join(PROJECT_ROOT, "data", "applications.db")
RECRUITER_CRM_DB         = os.path.join(PROJECT_ROOT, "data", "recruiter_crm.db")
COMPANY_BLACKLIST: list  = []          # list of company name strings to skip
ATS_SCORE_THRESHOLD      = 0.60        # min ATS score to auto-queue job
MATCH_SCORE_THRESHOLD    = 0.65        # min semantic match score to consider job

# ═══════════════════════════════════════════════════════════════════════════════
# V8: Autonomous Application Engine
# ═══════════════════════════════════════════════════════════════════════════════

# SAFETY: Set AUTO_APPLY_ENABLED=true only after thorough testing.
# When False (default), each application requires explicit user confirmation.
AUTO_APPLY_ENABLED       = os.environ.get("MSA_AUTO_APPLY", "false").lower() == "true"
MAX_APPLICATIONS_PER_DAY = int(os.environ.get("MSA_MAX_APPLY_PER_DAY", "20"))
EVIDENCE_DIR             = os.path.join(PROJECT_ROOT, "data", "evidence")
APPLICATION_RETRY_LIMIT  = 3           # max attempts before marking as failed
APPLICATION_RETRY_DELAY  = 5          # seconds between retries (exponential backoff base)

# ═══════════════════════════════════════════════════════════════════════════════
# V9: Recruiter CRM & Analytics
# ═══════════════════════════════════════════════════════════════════════════════

ENABLE_RECRUITER_CRM     = True
ENABLE_CAREER_ANALYTICS  = True
ENABLE_SELF_IMPROVEMENT  = True
GMAIL_OAUTH_ENABLED      = False       # Set True only if Gmail API is configured
ANALYTICS_REPORT_DIR     = os.path.join(PROJECT_ROOT, "data", "analytics")

# ═══════════════════════════════════════════════════════════════════════════════
# Ollama — Local LLM Configuration
# ═══════════════════════════════════════════════════════════════════════════════

OLLAMA_BASE_URL          = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EXE_PATH          = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Programs", "Ollama", "ollama.exe"
)

# Primary model — qwen2.5:7b-instruct (best quality of installed models)
OLLAMA_DEFAULT_MODEL     = os.environ.get("MSA_OLLAMA_MODEL", "qwen2.5:7b-instruct")

# Fast model for quick responses / classification tasks
OLLAMA_FAST_MODEL        = os.environ.get("MSA_OLLAMA_FAST_MODEL", "qwen2.5:0.5b")

# Research / deep reasoning model
OLLAMA_REASON_MODEL      = os.environ.get("MSA_OLLAMA_REASON_MODEL", "deepseek-r1:7b")

# Embedding model (used by FAISS / semantic search)
OLLAMA_EMBED_MODEL       = os.environ.get("MSA_OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")

# Timeouts
OLLAMA_REQUEST_TIMEOUT   = int(os.environ.get("MSA_OLLAMA_TIMEOUT", "120"))  # seconds
OLLAMA_STREAM            = True   # stream token-by-token to UI

# Auto-start Ollama if not running (handled by startup scripts)
OLLAMA_AUTO_START        = True
