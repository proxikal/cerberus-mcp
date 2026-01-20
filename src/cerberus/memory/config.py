"""Memory system configuration with configurable limits.

Defaults can be overridden via:
1. ~/.config/cerberus/config.toml [memory] section
2. Project cerberus.toml [memory] section
3. Environment variables CERBERUS_MEMORY_*
"""
import os
from typing import Any, Optional

# Default values (conservative but effective for most users)
MEMORY_DEFAULTS = {
    # Size limits (bytes)
    "max_profile_size": 4 * 1024,  # 4KB global preferences
    "max_context_size": 4 * 1024,  # 4KB context generation output
    "max_project_decisions_size": 10 * 1024,  # 10KB per project
    "max_total_memory_size": 256 * 1024,  # 256KB total

    # Count limits
    "max_decisions_per_project": 10,
    "max_corrections": 20,
    "max_prompts_per_project": 5,

    # Context generation limits
    "max_profile_lines": 50,
    "max_context_lines": 150,
    "max_decisions_in_context": 5,
    "max_corrections_in_context": 5,
    "max_prompts_in_context": 3,

    # Retention
    "max_project_age_days": 90,
}

# Cached config
_config_cache: Optional[dict] = None


def _load_config() -> dict:
    """Load config from file if available."""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    config = {}

    # Try to load from MCP config system
    try:
        from cerberus.mcp.config import get_memory_config
        config = get_memory_config()
    except ImportError:
        pass

    # Try standalone config files
    if not config:
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                tomllib = None

        if tomllib:
            from pathlib import Path
            config_paths = [
                Path("cerberus.toml"),
                Path.home() / ".config" / "cerberus" / "config.toml",
            ]
            for path in config_paths:
                if path.exists():
                    try:
                        with open(path, "rb") as f:
                            full_config = tomllib.load(f)
                            config = full_config.get("memory", {})
                            break
                    except Exception:
                        pass

    _config_cache = config
    return config


def get(key: str, default: Any = None) -> Any:
    """Get a memory config value.

    Args:
        key: Config key (e.g., "max_profile_size")
        default: Default if not found (uses MEMORY_DEFAULTS if None)

    Returns:
        Config value
    """
    # Check environment variable first
    env_key = f"CERBERUS_MEMORY_{key.upper()}"
    env_val = os.environ.get(env_key)
    if env_val is not None:
        # Try to convert to int if it looks like a number
        try:
            return int(env_val)
        except ValueError:
            return env_val

    # Check loaded config
    config = _load_config()
    if key in config:
        return config[key]

    # Fall back to defaults
    if default is not None:
        return default
    return MEMORY_DEFAULTS.get(key)


def reload():
    """Force reload of config (useful for testing)."""
    global _config_cache
    _config_cache = None


# Convenience accessors for commonly used limits
def max_profile_size() -> int:
    return get("max_profile_size")


def max_context_size() -> int:
    return get("max_context_size")


def max_project_decisions_size() -> int:
    return get("max_project_decisions_size")


def max_total_memory_size() -> int:
    return get("max_total_memory_size")


def max_decisions_per_project() -> int:
    return get("max_decisions_per_project")


def max_corrections() -> int:
    return get("max_corrections")


def max_prompts_per_project() -> int:
    return get("max_prompts_per_project")


def max_profile_lines() -> int:
    return get("max_profile_lines")


def max_context_lines() -> int:
    return get("max_context_lines")


def max_decisions_in_context() -> int:
    return get("max_decisions_in_context")


def max_corrections_in_context() -> int:
    return get("max_corrections_in_context")


def max_prompts_in_context() -> int:
    return get("max_prompts_in_context")


def max_project_age_days() -> int:
    return get("max_project_age_days")
