import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("msa.ai.guardrails")

# Injection and jailbreak detection rules
JAILBREAK_PATTERNS = [
    r"(ignore previous instructions)",
    r"(system bypass)",
    r"(you are now developer mode)",
    r"(ignore all rules)"
]

# PII Redaction pattern definitions
PII_PATTERNS = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "api_key": r"((?:key|secret|token|password)[\w\.\-\_]{10,})"
}

class SecurityGuardrails:
    """Zero-Trust input and output validation filtering."""
    def __init__(self):
        self.jailbreak_compiled = [re.compile(p, re.IGNORECASE) for p in JAILBREAK_PATTERNS]
        self.pii_compiled = {name: re.compile(p, re.IGNORECASE) for name, p in PII_PATTERNS.items()}

    def validate_input(self, text: str) -> bool:
        """Returns True if input is safe; False if jailbreak or injection detected."""
        for pattern in self.jailbreak_compiled:
            if pattern.search(text):
                logger.warning("Guardrails Alert: Jailbreak attempt blocked.")
                return False
        return True

    def redact_pii(self, text: str) -> str:
        """Masks sensitive parameters (emails, tokens) with placeholders."""
        redacted = text
        for label, pattern in self.pii_compiled.items():
            redacted = pattern.sub(f"[REDACTED_{label.upper()}]", redacted)
        return redacted
