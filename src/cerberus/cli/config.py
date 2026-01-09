"""
CLI Configuration

Centralized configuration for the Cerberus CLI subsystem.
"""

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

    @staticmethod
    def get_default_index_path(cwd: Optional[Path] = None) -> Path:
        """Get the default index path in the current working directory"""
        if cwd is None:
            cwd = Path.cwd()
        return cwd / CLIConfig.DEFAULT_INDEX_NAME
