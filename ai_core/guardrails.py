"""
ai_core/guardrails.py — MSA AI Agent Security Guardrails
=========================================================
Zero-Trust input/output validation, PII redaction, prompt injection
defense, and LLM output sanitization.

Round 2 Audit Fix: Expanded from 41 lines to comprehensive guardrails
covering OWASP LLM Top 10 attack vectors.
"""
import re
import json
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.ai.guardrails")

# ── Jailbreak / Prompt Injection Patterns (OWASP LLM01) ─────────────────────
# Covers: role confusion, instruction override, DAN, Developer Mode, etc.
JAILBREAK_PATTERNS = [
    r"ignore\s+(previous|all|prior|above|system)\s+(instructions?|prompts?|rules?|context)",
    r"you\s+are\s+now\s+(developer|admin|root|unrestricted|jailbroken)",
    r"(system|bypass|override|disable)\s+(safety|filter|guardrail|restriction)",
    r"pretend\s+(you|that)\s+(are|have\s+no)\s+(rules?|restrictions?|limits?)",
    r"DAN\s+mode|do\s+anything\s+now",
    r"act\s+as\s+(an?\s+)?(unrestricted|evil|uncensored|jailbroken|hacked)\s+(AI|assistant|model|bot)",
    r"from\s+now\s+on\s+(ignore|forget|discard)\s+(your|all)\s+(training|instructions?|rules?)",
    r"repeat\s+after\s+me.*ignore",
    r"translate\s+the\s+following.*ignore",
    r"summarize.*then\s+execute",
    r"base64\s*(decode|encode|encoded)",  # Encoded payload injection
    r"<\s*script\s*>",                    # XSS in prompts
    r"\bexec\s*\(",                       # Code injection attempt
    r"__import__\s*\(",                   # Python code injection
    r"subprocess\s*\.",                   # OS command in prompt
    r"os\.system\s*\(",                   # OS execution attempt
    r"curl\s+https?://",                  # SSRF via prompt
    r"wget\s+https?://",                  # SSRF via prompt
]

# ── Prompt Leakage Attempts (OWASP LLM07) ────────────────────────────────────
PROMPT_LEAKAGE_PATTERNS = [
    r"(show|print|reveal|repeat|output|display|give\s+me)\s+(your|the)\s+(system|initial|base|original)\s+prompt",
    r"what\s+(is|are|was)\s+your\s+(instructions?|initial\s+prompt|system\s+message)",
    r"(ignore|skip)\s+(the|your)\s+system\s+prompt",
    r"what\s+(did|does)\s+your\s+developer\s+tell\s+you",
    r"(show|reveal|leak)\s+(your|the)\s+(context|configuration|settings)",
]

# ── PII Redaction Patterns (GDPR / PDPA compliance) ──────────────────────────
PII_PATTERNS = {
    "email":       r"[\w\.\-]+@[\w\.\-]+\.\w+",
    "phone_in":    r"(\+91[-\s]?)?\d{10}",                   # Indian phone
    "phone_us":    r"(\+1[-\s]?)?\(?\d{3}\)?[-\s]\d{3}[-\s]\d{4}",
    "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    "api_key":     r"(?:key|secret|token|password|bearer|authorization)[_\-\s=:\"']+[\w\-\.]{16,}",
    "jwt_token":   r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+",
    "ip_address":  r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
    "aadhaar":     r"\b\d{4}\s\d{4}\s\d{4}\b",               # Aadhaar number
}

# ── Dangerous Output Patterns (Model generates harmful content) ───────────────
DANGEROUS_OUTPUT_PATTERNS = [
    r"(sudo\s+rm\s+-rf|rm\s+-rf\s+/)",   # Destructive shell commands
    r"DROP\s+TABLE|DROP\s+DATABASE",       # SQL destructive ops in response
    r"format\s+c:",                         # Disk formatting
    r"del\s+/s\s+/q",                      # Windows delete all
]


class SecurityGuardrails:
    """
    Zero-Trust input and output validation for LLM I/O.

    Protects against:
    - Prompt injection (OWASP LLM01)
    - Sensitive information disclosure (OWASP LLM06)
    - System prompt leakage (OWASP LLM07)
    - Insecure output handling (OWASP LLM02)
    - PII leakage in responses
    """

    def __init__(self):
        self._jailbreak     = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in JAILBREAK_PATTERNS]
        self._leakage       = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in PROMPT_LEAKAGE_PATTERNS]
        self._pii           = {n: re.compile(p, re.IGNORECASE) for n, p in PII_PATTERNS.items()}
        self._dangerous_out = [re.compile(p, re.IGNORECASE) for p in DANGEROUS_OUTPUT_PATTERNS]
        self._blocked_count = 0

    # ── Input Validation ─────────────────────────────────────────────────────
    def validate_input(self, text: str) -> tuple[bool, Optional[str]]:
        """
        Validates user input before it reaches the LLM.

        Returns:
            (True, None) if input is safe
            (False, reason) if blocked
        """
        if not isinstance(text, str):
            return False, "Input must be a string"

        if len(text) > 32_000:
            return False, "Input exceeds maximum length (32000 chars)"

        # Check for jailbreak attempts
        for pattern in self._jailbreak:
            if pattern.search(text):
                self._blocked_count += 1
                logger.warning("🛡️  Guardrails BLOCKED jailbreak attempt [#%d]", self._blocked_count)
                return False, "Request contains prohibited content and was blocked."

        # Check for prompt leakage attempts
        for pattern in self._leakage:
            if pattern.search(text):
                self._blocked_count += 1
                logger.warning("🛡️  Guardrails BLOCKED prompt leakage attempt [#%d]", self._blocked_count)
                return False, "Request attempts to access system internals and was blocked."

        return True, None

    # ── Output Validation ────────────────────────────────────────────────────
    def validate_output(self, text: str) -> tuple[str, list[str]]:
        """
        Validates and sanitizes LLM output before it reaches the user.

        Returns:
            (sanitized_text, list_of_warnings)
        """
        warnings = []

        # Check for dangerous commands in output
        for pattern in self._dangerous_out:
            if pattern.search(text):
                warnings.append("Output contained potentially dangerous command — review before executing")
                logger.warning("⚠️  Guardrails WARNING: Dangerous pattern in LLM output")

        # Redact any PII that slipped through
        sanitized = self.redact_pii(text)

        return sanitized, warnings

    # ── PII Redaction ────────────────────────────────────────────────────────
    def redact_pii(self, text: str) -> str:
        """Redacts all detected PII from text with placeholder labels."""
        redacted = text
        for label, pattern in self._pii.items():
            redacted = pattern.sub(f"[REDACTED_{label.upper()}]", redacted)
        return redacted

    # ── JSON Output Validation ───────────────────────────────────────────────
    def validate_json_output(self, text: str) -> tuple[Optional[dict], Optional[str]]:
        """
        Validates that LLM structured output is valid JSON.

        Returns:
            (parsed_dict, None) on success
            (None, error_message) on failure
        """
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if json_match:
            text = json_match.group(1)

        try:
            result = json.loads(text.strip())
            return result, None
        except json.JSONDecodeError as e:
            return None, f"LLM returned invalid JSON: {e}"

    # ── Statistics ───────────────────────────────────────────────────────────
    def get_stats(self) -> dict:
        """Returns guardrails statistics for monitoring."""
        return {"blocked_requests": self._blocked_count}
