"""
Cerberus User Configuration

Hierarchical config system with global defaults + local overrides:
- Global: ~/.cerberus/config.json (cross-project settings)
- Local: .cerberus/config.json (project-specific overrides)

Config structure:
{
  "session_hooks": {
    "enabled": true,           // Enable session-end hook
    "interactive": true,        // Prompt for approval
    "batch_threshold": 0.9      // Auto-approve threshold
  },
  "index": {
    "auto_update": true,        // Enable file watcher (default: true)
    "extensions": [".py", ".ts", ".js", ".go"]
  }
}
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from cerberus.logging_config import logger


# Default configuration
DEFAULT_CONFIG = {
    "session_hooks": {
        "enabled": True,
        "interactive": True,
        "batch_threshold": 0.9
    },
    "index": {
        "auto_update": True,
        "extensions": [".py", ".ts", ".js", ".go", ".tsx", ".jsx", ".md", ".rst", ".txt"]
    }
}


class UserConfig:
    """
    Manages hierarchical user configuration.

    Load order (with override):
    1. Default config (hardcoded)
    2. Global config (~/.cerberus/config.json)
    3. Local config (.cerberus/config.json)
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize config manager.

        Args:
            project_root: Project root directory (defaults to CWD)
        """
        self.project_root = project_root or Path.cwd()
        self.global_config_path = Path.home() / ".cerberus" / "config.json"
        self.local_config_path = self.project_root / ".cerberus" / "config.json"

        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration with hierarchical override.

        Returns:
            Merged configuration dictionary
        """
        # Start with defaults
        config = DEFAULT_CONFIG.copy()

        # Load global config
        if self.global_config_path.exists():
            try:
                with open(self.global_config_path, 'r') as f:
                    global_config = json.load(f)
                    config = self._deep_merge(config, global_config)
                    logger.debug(f"Loaded global config from {self.global_config_path}")
            except Exception as e:
                logger.warning(f"Failed to load global config: {e}")

        # Load local config (overrides global)
        if self.local_config_path.exists():
            try:
                with open(self.local_config_path, 'r') as f:
                    local_config = json.load(f)
                    config = self._deep_merge(config, local_config)
                    logger.debug(f"Loaded local config from {self.local_config_path}")
            except Exception as e:
                logger.warning(f"Failed to load local config: {e}")

        return config

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries, with override taking precedence.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a config value by dot-separated key.

        Args:
            key: Dot-separated key (e.g., "session_hooks.enabled")
            default: Default value if key not found

        Returns:
            Config value

        Examples:
            config.get("session_hooks.enabled")  # True
            config.get("session_hooks.batch_threshold")  # 0.9
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set_global(self, key: str, value: Any) -> bool:
        """
        Set a global config value and save to disk.

        Args:
            key: Dot-separated key
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        return self._set_and_save(key, value, is_global=True)

    def set_local(self, key: str, value: Any) -> bool:
        """
        Set a local config value and save to disk.

        Args:
            key: Dot-separated key
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        return self._set_and_save(key, value, is_global=False)

    def _set_and_save(self, key: str, value: Any, is_global: bool) -> bool:
        """
        Set a config value and save to appropriate file.

        Args:
            key: Dot-separated key
            value: Value to set
            is_global: True for global config, False for local

        Returns:
            True if successful, False otherwise
        """
        config_path = self.global_config_path if is_global else self.local_config_path

        # Load existing config or start with empty
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load config from {config_path}: {e}")
                return False
        else:
            config = {}

        # Set the value
        keys = key.split(".")
        current = config
        for i, k in enumerate(keys[:-1]):
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

        # Save to disk
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            # Reload config
            self._config = self._load_config()

            logger.info(f"Saved {'global' if is_global else 'local'} config: {key}={value}")
            return True
        except Exception as e:
            logger.error(f"Failed to save config to {config_path}: {e}")
            return False

    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire merged configuration.

        Returns:
            Full configuration dictionary
        """
        return self._config.copy()

    def reload(self) -> None:
        """Reload configuration from disk."""
        self._config = self._load_config()


# Global singleton
_config: Optional[UserConfig] = None


def get_user_config(project_root: Optional[Path] = None) -> UserConfig:
    """
    Get the user configuration singleton.

    Args:
        project_root: Optional project root override

    Returns:
        UserConfig instance
    """
    global _config
    if project_root is not None:
        return UserConfig(project_root)
    if _config is None:
        _config = UserConfig()
    return _config


def reset_user_config() -> None:
    """Reset the global config singleton (for testing)."""
    global _config
    _config = None
