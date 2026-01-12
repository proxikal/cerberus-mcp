"""
Index Limits Configuration.

Unified configuration for bloat protection limits.
All values configurable via CERBERUS_* environment variables.

Phase: Bloat Protection System
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


# Conservative defaults to prevent bloat
DEFAULT_MAX_FILE_BYTES = 1 * 1024 * 1024       # 1 MB per file
DEFAULT_MAX_SYMBOLS_PER_FILE = 500              # Symbols per file
DEFAULT_MAX_TOTAL_SYMBOLS = 100_000             # Total symbols in index
DEFAULT_MAX_INDEX_SIZE_MB = 100                 # SQLite DB size in MB
DEFAULT_MAX_VECTORS = 100_000                   # FAISS vector count
DEFAULT_MIN_FREE_DISK_MB = 100                  # Pre-flight disk check
DEFAULT_WARN_THRESHOLD = 0.80                   # 80% triggers warning


def _env_int(key: str, default: int) -> int:
    """Read integer from environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    """Read float from environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_bool(key: str, default: bool) -> bool:
    """Read boolean from environment variable."""
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes"):
        return True
    if value in ("false", "0", "no"):
        return False
    return default


@dataclass
class IndexLimitsConfig:
    """
    Unified index limits configuration.

    All limits are loaded from environment variables with CERBERUS_ prefix,
    or use sensible defaults to prevent unbounded growth.

    Environment Variables:
        CERBERUS_MAX_FILE_BYTES: Max bytes per file (default: 1MB)
        CERBERUS_MAX_SYMBOLS_PER_FILE: Max symbols per file (default: 500)
        CERBERUS_MAX_TOTAL_SYMBOLS: Total symbol limit (default: 100K)
        CERBERUS_MAX_INDEX_SIZE_MB: Max DB size in MB (default: 100)
        CERBERUS_MAX_VECTORS: Max FAISS vectors (default: 100K)
        CERBERUS_MIN_FREE_DISK_MB: Min free disk for pre-flight (default: 100)
        CERBERUS_WARN_THRESHOLD: Warning threshold 0.0-1.0 (default: 0.8)
        CERBERUS_LIMITS_STRICT: If "true", fail on warnings (default: false)

    Override for large projects:
        CERBERUS_MAX_TOTAL_SYMBOLS=500000 cerberus index .
    """

    # Per-file limits
    max_file_bytes: int = field(default_factory=lambda: _env_int(
        "CERBERUS_MAX_FILE_BYTES", DEFAULT_MAX_FILE_BYTES
    ))
    max_symbols_per_file: int = field(default_factory=lambda: _env_int(
        "CERBERUS_MAX_SYMBOLS_PER_FILE", DEFAULT_MAX_SYMBOLS_PER_FILE
    ))

    # Total index limits
    max_total_symbols: int = field(default_factory=lambda: _env_int(
        "CERBERUS_MAX_TOTAL_SYMBOLS", DEFAULT_MAX_TOTAL_SYMBOLS
    ))
    max_index_size_mb: int = field(default_factory=lambda: _env_int(
        "CERBERUS_MAX_INDEX_SIZE_MB", DEFAULT_MAX_INDEX_SIZE_MB
    ))
    max_vectors: int = field(default_factory=lambda: _env_int(
        "CERBERUS_MAX_VECTORS", DEFAULT_MAX_VECTORS
    ))

    # Pre-flight limits
    min_free_disk_mb: int = field(default_factory=lambda: _env_int(
        "CERBERUS_MIN_FREE_DISK_MB", DEFAULT_MIN_FREE_DISK_MB
    ))

    # Thresholds
    warn_threshold: float = field(default_factory=lambda: _env_float(
        "CERBERUS_WARN_THRESHOLD", DEFAULT_WARN_THRESHOLD
    ))

    # Behavior
    strict_mode: bool = field(default_factory=lambda: _env_bool(
        "CERBERUS_LIMITS_STRICT", False
    ))

    @property
    def max_index_size_bytes(self) -> int:
        """Convert MB limit to bytes for comparison."""
        return self.max_index_size_mb * 1024 * 1024

    @property
    def min_free_disk_bytes(self) -> int:
        """Convert MB limit to bytes for comparison."""
        return self.min_free_disk_mb * 1024 * 1024

    def get_warning_thresholds(self) -> Dict[str, int]:
        """Calculate warning thresholds for each limit."""
        return {
            "symbols_per_file": int(self.max_symbols_per_file * self.warn_threshold),
            "total_symbols": int(self.max_total_symbols * self.warn_threshold),
            "index_size_bytes": int(self.max_index_size_bytes * self.warn_threshold),
            "vectors": int(self.max_vectors * self.warn_threshold),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary (for JSON output)."""
        return {
            "max_file_bytes": self.max_file_bytes,
            "max_file_mb": round(self.max_file_bytes / (1024 * 1024), 2),
            "max_symbols_per_file": self.max_symbols_per_file,
            "max_total_symbols": self.max_total_symbols,
            "max_index_size_mb": self.max_index_size_mb,
            "max_vectors": self.max_vectors,
            "min_free_disk_mb": self.min_free_disk_mb,
            "warn_threshold": self.warn_threshold,
            "strict_mode": self.strict_mode,
        }


# Global instance for convenience
_default_config: Optional[IndexLimitsConfig] = None


def get_limits_config() -> IndexLimitsConfig:
    """Get the global limits configuration."""
    global _default_config
    if _default_config is None:
        _default_config = IndexLimitsConfig()
    return _default_config


def reset_limits_config() -> None:
    """Reset global config (useful after env var changes or for testing)."""
    global _default_config
    _default_config = None
