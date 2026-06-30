"""
services/security_sandbox.py
============================
RAG Security Sandbox Service.
Implements prompt injection filtering, document upload sanitization,
HTML/JS escape filters, and malicious file content scanner.
"""

import re
import os
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("msa.services.security")

INJECTION_PATTERNS = [
    r"\bignore\b.*\binstructions\b",
    r"\byou\s+are\s+now\s+a\b",
    r"\bsystem\s+prompt\b",
    r"\bsecret\s+key\b",
    r"\bbypass\s+validation\b",
    r"\bnew\s+rule\b",
    r"\breveal\s+instructions\b",
    r"\bdo\s+not\s+follow\b",
    r"\btranslate\s+this\s+instruction\b"
]

# Suspect code execution script blocks in doc files
MALICIOUS_SHELL_PATTERNS = [
    r"<script.*?>.*?</script>",
    r"eval\s*\(",
    r"exec\s*\(",
    r"os\.system\s*\(",
    r"subprocess\.run\s*\(",
    r"base64\.b64decode\s*\(",
    r"sh\s+-c\b",
    r"/bin/bash\b",
    r"cmd\.exe\b"
]


class SecuritySandbox:
    """
    Ensures safe operations on user queries and uploaded files prior to RAG indexing or agent reasoning.
    """
    def __init__(self):
        self.injection_regexes = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
        self.malicious_regexes = [re.compile(p, re.IGNORECASE) for p in MALICIOUS_SHELL_PATTERNS]

    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Scans queries for prompt injection attempts."""
        if not query:
            return True, ""

        for rx in self.injection_regexes:
            if rx.search(query):
                logger.warning("Security Sandbox: Flagged prompt injection signature in query: '%s'", query[:120])
                return False, "Query contains flagged instructions override commands."

        return True, ""

    def sanitize_document_text(self, text: str) -> str:
        """Escapes raw HTML tags and scripting wrappers to prevent cross-site scripting (XSS) in UI."""
        if not text:
            return ""
        # Escape HTML tags
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Remove active scripts
        escaped = re.sub(r"(?i)javascript:", "escaped_js:", escaped)
        return escaped

    def scan_file_integrity(self, filepath: str) -> Tuple[bool, str]:
        """Scans file binary/text contents for malicious execution payloads prior to ingestion."""
        if not os.path.exists(filepath):
            return False, "File does not exist."

        try:
            # Check file size (cap at 100MB to avoid zip-bombs)
            size_mb = os.path.getsize(filepath) / (1024 * 1024)
            if size_mb > 100:
                logger.warning("Security Sandbox: Rejected file '%s' due to excessive size (%.2f MB)", filepath, size_mb)
                return False, "File size exceeds enterprise safety limit (100MB)."

            # Read first 1MB of file content to scan for exploits
            with open(filepath, "rb") as f:
                content = f.read(1024 * 1024)

            # Check for hidden executable signatures
            if content.startswith(b"MZ") and not filepath.endswith(".exe"):
                # PE Executable disguised as document
                return False, "File matches PE executable signatures disguised as document."
            if content.startswith(b"\x7fELF") and not filepath.endswith(".so"):
                return False, "File matches ELF binary signatures."

            # Check text representation for script injections
            try:
                text_content = content.decode("utf-8", errors="ignore")
                for rx in self.malicious_regexes:
                    if rx.search(text_content):
                        logger.warning("Security Sandbox: Flagged suspect script exploit in '%s'", filepath)
                        return False, "File contains suspect command execution / scripting segments."
            except Exception:
                pass

        except Exception as e:
            logger.error("Failed to perform security scan on '%s': %s", filepath, e)
            return False, f"Security scan failed: {e}"

        return True, ""
