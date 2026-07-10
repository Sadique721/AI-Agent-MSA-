"""
tools/schema_validator.py
==========================
Tolerant validation and type coercion for tool execution.
"""
import json
import logging
import re
from typing import Dict, Any, Optional

logger = logging.getLogger("msa.tools.schema_validator")

# Minimal, tolerant schema check — checks presence and basic type,
# not exact structure, so small LLM formatting quirks don't cause failures.
_ACTION_SCHEMAS = {
    "internet_search":  {"query": str},
    "memory_recall":    {"query": str},
    "generate_code":    {"prompt": str, "language": str},
    "debug_code":       {"code": str},
    "system_control":   {"command": str},
}


def validate_tool_call(action: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Returns cleaned/validated parameters, or None if the call should be
    rejected (missing a truly required field). Unknown extra fields are
    kept, not stripped — LLMs sometimes add harmless extra context.
    """
    schema = _ACTION_SCHEMAS.get(action)
    if schema is None:
        return parameters  # no schema defined for this action — allow through

    cleaned = dict(parameters or {})
    for field, expected_type in schema.items():
        if field not in cleaned:
            logger.warning("Tool call '%s' missing required field '%s' - rejecting.", action, field)
            return None
        if not isinstance(cleaned[field], expected_type):
            # Try a tolerant coercion before rejecting outright
            try:
                cleaned[field] = expected_type(cleaned[field])
            except Exception:
                logger.warning("Tool call '%s' field '%s' has wrong type - rejecting.", action, field)
                return None
    return cleaned
