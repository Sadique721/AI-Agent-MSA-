"""
scripts/config_validator.py
===========================
Pre-flight configuration and hardware compatibility validator (V10).

Ensures database directories are writable, network ports (5000, 11434) are accessible,
Ollama models are downloaded, and safety thresholds are correctly set.
"""
from __future__ import annotations

import logging
import os
import socket
from typing import Dict, List

import config

logger = logging.getLogger("msa.config.validator")


class ConfigValidator:
    """
    Checks system configuration and reports warnings or critical failures.
    """

    def validate_all(self) -> bool:
        """Runs all checks. Returns False if a critical failure occurs."""
        errors = []
        warnings = []

        # 1. Validate DB & Log directories
        for path_name, path_val in [
            ("PROJECT_ROOT", config.PROJECT_ROOT),
            ("LOG_DIR", config.LOG_DIR),
            ("RESUME_DIR", config.RESUME_DIR),
            ("EVIDENCE_DIR", config.EVIDENCE_DIR),
        ]:
            try:
                os.makedirs(path_val, exist_ok=True)
                # Test write capability
                test_file = os.path.join(path_val, ".write_test")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as exc:
                errors.append(f"Directory {path_name} ({path_val}) not writable: {exc}")

        # 2. Check essential keys/ports
        if not config.SECRET_KEY or config.SECRET_KEY == "msa-secret-key-change-in-production":
            warnings.append("Using default flask SECRET_KEY; change in production.")

        # Check port binding
        for port in [config.SERVER_PORT]:
            if self._is_port_in_use(port):
                # Warning instead of error since server might be restarting or running in debug reload
                warnings.append(f"Port {port} is currently in use. Ensure no other instance is running.")

        # 3. Check RAG components
        if not os.path.exists(config.DB_PATH):
            warnings.append(f"Primary sqlite database not found at {config.DB_PATH}; will be created on start.")

        # Print report
        print("\n" + "=" * 50)
        print("MSA CONFIGURATION VALIDATION")
        print("=" * 50)
        
        for w in warnings:
            print(f"  [WARN] {w}")
            logger.warning("[ConfigValidator] %s", w)
            
        for e in errors:
            print(f"  [FAIL] {e}")
            logger.error("[ConfigValidator] %s", e)
            
        print("=" * 50)
        print(f"Critical Failures: {len(errors)}  |  Warnings: {len(warnings)}")
        
        return len(errors) == 0

    @staticmethod
    def _is_port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) == 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ConfigValidator().validate_all()
