"""Configuration loading and auto-discovery."""
from pathlib import Path
from typing import Any, Dict, Optional
import os

try:  # Python 3.11+
    import tomllib
except ImportError:  # pragma: no cover - fallback for older environments
    import tomli as tomllib


def load_config() -> Optional[Dict[str, Any]]:
    """
    Load configuration from file.

    Priority:
    1. CERBERUS_CONFIG environment variable
    2. ./cerberus.toml (project config)
    3. ~/.config/cerberus/config.toml (user config)

    Returns:
        Configuration dict or None if no config found
    """
    config_paths = []

    env_config = os.environ.get("CERBERUS_CONFIG")
    if env_config:
        config_paths.append(Path(env_config))

    config_paths.append(Path("cerberus.toml"))
    config_paths.append(Path.home() / ".config" / "cerberus" / "config.toml")

    for path in config_paths:
        if path.exists():
            with open(path, "rb") as f:
                return tomllib.load(f)

    return None


def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a configuration value by dot-notation key.

    Example:
        get_config_value("index.path", ".cerberus/cerberus.db")
        get_config_value("limits.max_search_results", 100)
    """
    config = load_config()
    if config is None:
        return default

    parts = key.split(".")
    value = config

    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return default

    return value


DEFAULTS = {
    "index": {
        "path": ".cerberus/cerberus.db",
        "auto_update": True,  # Auto-update index on file changes
        "debounce_seconds": 3.0,  # Wait for quiet period before updating
        "watch_extensions": [".py", ".ts", ".js", ".go", ".tsx", ".jsx", ".rs", ".java"],
    },
    "memory": {
        "global_store": "~/.cerberus/memory",
        # Size limits (bytes)
        "max_profile_size": 4096,  # 4KB global preferences
        "max_context_size": 4096,  # 4KB context generation output
        "max_project_decisions_size": 10240,  # 10KB per project
        "max_total_memory_size": 262144,  # 256KB total
        # Count limits
        "max_decisions_per_project": 10,
        "max_corrections": 20,
        "max_prompts_per_project": 5,
        # Context generation limits
        "max_profile_lines": 50,
        "max_context_lines": 150,  # For full context output
        "max_decisions_in_context": 5,
        "max_corrections_in_context": 5,
        "max_prompts_in_context": 3,
        # Retention
        "max_project_age_days": 90,
    },
    "limits": {
        "max_search_results": 100,
        "max_file_size": 1_000_000,
        "max_symbols_per_file": 500,
        "max_skeleton_lines": 5000,  # Max lines for skeletonize output
        "max_blueprint_depth": 10,  # Max directory depth for blueprint
        "max_style_violations": 30,  # Max violations to return from style_check (encourages iterative fixing)
    },
    "quality": {
        "style_rules": ["black", "isort"],
        "auto_fix_on_edit": False,
    },
    "summarization": {
        "ollama_url": "http://localhost:11434",
        "model": "llama3.2",
        "max_file_size_for_summary": 50000,
    },
}


def get_memory_config() -> dict:
    """Get memory configuration with defaults."""
    config = load_config() or {}
    memory_config = config.get("memory", {})

    # Merge with defaults
    result = {**DEFAULTS["memory"]}
    result.update(memory_config)

    return result
