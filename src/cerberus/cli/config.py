"""
CLI Configuration

Centralized configuration for the Cerberus CLI subsystem.
"""

import os
from pathlib import Path
from typing import Optional

class CLIConfig:
    """Configuration for CLI commands"""

    # Default index path
    DEFAULT_INDEX_NAME = "cerberus.db"

    # Default batch sizes for operations
    DEFAULT_BATCH_SIZE = 100
    DEFAULT_CHUNK_SIZE = 1000

    # Default context limits
    DEFAULT_MAX_DEPTH = 3
    DEFAULT_TOKEN_LIMIT = 8000

    # Machine mode (Agent-optimized output)
    _machine_mode: Optional[bool] = None
    _show_turn_savings: bool = False
    _show_session_savings: bool = True  # Default to session savings
    _silent_metrics: bool = False

    # Daemon routing control (Phase 10 batch optimization)
    _disable_daemon: bool = False

    @classmethod
    def set_machine_mode(cls, enabled: bool) -> None:
        """Set machine mode (pure data output, no presentation)"""
        cls._machine_mode = enabled

    @classmethod
    def is_machine_mode(cls) -> bool:
        """
        Check if machine mode is active.

        Machine mode is the DEFAULT (Phase 10 spec).
        Returns False only if human mode is explicitly requested.
        """
        if cls._machine_mode is not None:
            return cls._machine_mode
        # Check environment variable for human mode opt-in
        # If CERBERUS_HUMAN_MODE is set, disable machine mode
        if os.getenv("CERBERUS_HUMAN_MODE", "").lower() in ("1", "true", "yes"):
            return False
        # Default to machine mode (Phase 10: Machine-First Protocol)
        return True

    @classmethod
    def set_show_turn_savings(cls, enabled: bool) -> None:
        """Enable per-turn savings metrics"""
        cls._show_turn_savings = enabled

    @classmethod
    def show_turn_savings(cls) -> bool:
        """Check if per-turn savings should be displayed"""
        return cls._show_turn_savings and not cls._silent_metrics

    @classmethod
    def set_show_session_savings(cls, enabled: bool) -> None:
        """Enable session savings metrics"""
        cls._show_session_savings = enabled

    @classmethod
    def show_session_savings(cls) -> bool:
        """Check if session savings should be displayed"""
        return cls._show_session_savings and not cls._silent_metrics

    @classmethod
    def set_silent_metrics(cls, enabled: bool) -> None:
        """Suppress all metric output"""
        cls._silent_metrics = enabled

    @classmethod
    def is_silent_metrics(cls) -> bool:
        """Check if metrics are suppressed"""
        # In machine mode, default to silent unless explicitly enabled
        if cls.is_machine_mode():
            return not (cls._show_turn_savings or cls._show_session_savings)
        return cls._silent_metrics

    @classmethod
    def set_disable_daemon(cls, disabled: bool) -> None:
        """Disable daemon routing (for batch subprocess optimization)"""
        cls._disable_daemon = disabled

    @classmethod
    def is_daemon_disabled(cls) -> bool:
        """Check if daemon routing is disabled"""
        return cls._disable_daemon

    @staticmethod
    def get_default_index_path(cwd: Optional[Path] = None) -> Path:
        """Get the default index path in the current working directory"""
        if cwd is None:
            cwd = Path.cwd()
        return cwd / CLIConfig.DEFAULT_INDEX_NAME
