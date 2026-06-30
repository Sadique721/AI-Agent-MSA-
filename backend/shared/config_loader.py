"""
backend/shared/config_loader.py
================================
Singleton YAML config loader for MSA AI Agent V5.0.
Merges base config (development.yaml) with environment-specific overrides.
Supports feature flags, env-var substitution, and typed accessors.
"""
from __future__ import annotations

import os
import re
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

logger = logging.getLogger("msa.config")

# ── Locate project root ───────────────────────────────────────────────────────
_HERE = Path(__file__).resolve()
PROJECT_ROOT = _HERE.parent.parent.parent   # backend/shared/config_loader.py → root


def _resolve_env_vars(value: Any) -> Any:
    """Recursively resolve ${ENV_VAR:-default} placeholders in strings."""
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([^}:-]+)(?::-(.*?))?\}")

        def replacer(match: re.Match) -> str:
            var_name, default = match.group(1), match.group(2) or ""
            return os.environ.get(var_name, default)

        return pattern.sub(replacer, value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    return value


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dicts — override wins on conflicts."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml(path: Path) -> Dict:
    """Load a YAML file safely, return empty dict if missing."""
    if yaml is None:
        logger.warning("PyYAML not installed — using empty config")
        return {}
    if not path.exists():
        logger.debug("Config file not found: %s", path)
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Failed to load config %s: %s", path, e)
        return {}


class ConfigLoader:
    """
    Singleton configuration manager.
    Usage:
        cfg = ConfigLoader.get()
        port = cfg.get("server.fastapi_port", 8000)
        if cfg.feature("enable_kafka"):
            ...
    """

    _instance: Optional["ConfigLoader"] = None
    _config: Dict[str, Any] = {}
    _features: Dict[str, bool] = {}

    def __init__(self) -> None:
        self._reload()

    @classmethod
    def get_instance(cls) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Force reload — useful in tests."""
        cls._instance = None

    def _reload(self) -> None:
        config_dir = PROJECT_ROOT / "config"
        env = os.environ.get("MSA_ENV", "development").lower()

        # Load in order: development → env-specific → env vars
        base = _load_yaml(config_dir / "development.yaml")
        override = _load_yaml(config_dir / f"{env}.yaml") if env != "development" else {}
        merged = _deep_merge(base, override)
        self._config = _resolve_env_vars(merged)

        # Load all sub-configs
        for sub in ["models", "agents", "memory", "rag", "security", "persona"]:
            sub_cfg = _load_yaml(config_dir / f"{sub}.yaml")
            self._config.setdefault(sub, {})
            self._config[sub] = _deep_merge(self._config[sub], _resolve_env_vars(sub_cfg))

        # Load feature flags
        features_raw = _load_yaml(config_dir / "features.yaml")
        self._features = _resolve_env_vars(features_raw)

        logger.info("Config loaded — environment: %s", env)

    # ── Public accessors ──────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """
        Dot-notation accessor: cfg.get("server.fastapi_port", 8000)
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(k)
            if value is None:
                return default
        return value

    def feature(self, flag: str) -> bool:
        """Check a feature flag: cfg.feature("enable_kafka")"""
        # Also check environment variable override: ENABLE_KAFKA=true
        env_key = flag.upper()
        env_val = os.environ.get(env_key)
        if env_val is not None:
            return env_val.lower() in ("1", "true", "yes")
        return bool(self._features.get(flag, False))

    def get_persona(self, name: str) -> Optional[Dict]:
        """Get persona config by name."""
        personas = self._config.get("persona", {}).get("personas", {})
        return personas.get(name)

    def get_all_personas(self) -> Dict[str, Dict]:
        return self._config.get("persona", {}).get("personas", {})

    def get_default_persona(self) -> str:
        return self._config.get("persona", {}).get("default_persona", "default")

    def get_model_config(self, task_type: str) -> Dict:
        routing = self._config.get("models", {}).get("task_routing", {})
        task_cfg = routing.get(task_type, {})
        mode = task_cfg.get("reasoning_mode", "balanced")
        modes = self._config.get("models", {}).get("reasoning_modes", {})
        return modes.get(mode, {})

    def get_agent_config(self, agent_name: str) -> Dict:
        return self._config.get("agents", {}).get(agent_name, {})

    def get_security(self, key: str, default: Any = None) -> Any:
        sec = self._config.get("security", {})
        return sec.get(key, default)

    def project_root(self) -> Path:
        return PROJECT_ROOT

    def path(self, key: str) -> Path:
        """Get a configured path, relative to project root."""
        raw = self.get(f"paths.{key}", "")
        p = Path(raw)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        return p

    def as_dict(self) -> Dict:
        """Return full merged config (for debugging)."""
        return dict(self._config)

    def features_dict(self) -> Dict[str, bool]:
        return dict(self._features)


# ── Module-level convenience instance ────────────────────────────────────────
@lru_cache(maxsize=1)
def get_config() -> ConfigLoader:
    return ConfigLoader.get_instance()
