"""
scripts/hardware_profiler.py
==============================
Detects available RAM (and GPU if present) at startup and picks the
largest model tier the hardware can actually run — instead of hardcoding
a 14B model that could crash smaller machines, or a 0.5B model that
under-uses a powerful machine.
"""
import logging
import subprocess
from typing import Dict

logger = logging.getLogger("msa.hardware_profiler")

# Conservative thresholds — leave headroom for OS + the rest of the app
_MODEL_TIERS = [
    # (min_ram_gb, chat_model,        reasoning_model,      coding_model)
    (24, "qwen2.5:14b",  "deepseek-r1:14b", "deepseek-coder-v2:16b"),
    (12, "qwen2.5:7b",   "deepseek-r1:7b",  "codellama:13b"),
    (6,  "qwen2.5:3b",   "qwen2.5:3b",      "codellama:7b"),
    (0,  "qwen2.5:0.5b", "qwen2.5:0.5b",    "qwen2.5:0.5b"),  # always-works floor
]


def detect_ram_gb() -> float:
    try:
        import psutil
        return round(psutil.virtual_memory().total / 1e9, 1)
    except Exception:
        return 4.0  # safe conservative assumption if psutil unavailable


def detect_gpu() -> bool:
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, timeout=3)
        return result.returncode == 0
    except Exception:
        return False


def recommend_model_tier() -> Dict[str, str]:
    ram_gb = detect_ram_gb()
    has_gpu = detect_gpu()
    logger.info("Hardware profile: RAM=%.1fGB, GPU=%s", ram_gb, has_gpu)

    # GPU roughly doubles the effective usable model size for a given RAM budget
    effective_gb = ram_gb * 1.5 if has_gpu else ram_gb

    for min_ram, chat_model, reasoning_model, coding_model in _MODEL_TIERS:
        if effective_gb >= min_ram:
            logger.info("Selected model tier: chat=%s reasoning=%s coding=%s",
                        chat_model, reasoning_model, coding_model)
            return {"chat": chat_model, "reasoning": reasoning_model, "coding": coding_model,
                    "ram_gb": ram_gb, "has_gpu": has_gpu}
    # Should never reach here since the last tier has min_ram=0
    return {"chat": "qwen2.5:0.5b", "reasoning": "qwen2.5:0.5b", "coding": "qwen2.5:0.5b",
            "ram_gb": ram_gb, "has_gpu": has_gpu}
