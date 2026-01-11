"""
Index Limits Package.

Centralized bloat protection for Cerberus indexing.

Phase: Bloat Protection System

Components:
- config: IndexLimitsConfig with env var support
- preflight: Pre-flight checks (disk, permissions)
- enforcement: Real-time limit enforcement
- validation: Post-index health checks

Usage:
    from cerberus.limits import get_limits_config, run_preflight_checks, BloatEnforcer

Default limits (conservative):
    - max_file_bytes: 1MB
    - max_symbols_per_file: 500
    - max_total_symbols: 100,000
    - max_index_size_mb: 100MB
    - max_vectors: 100,000

Override via environment:
    CERBERUS_MAX_TOTAL_SYMBOLS=500000 cerberus index .
"""

from .config import (
    IndexLimitsConfig,
    get_limits_config,
    reset_limits_config,
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_MAX_SYMBOLS_PER_FILE,
    DEFAULT_MAX_TOTAL_SYMBOLS,
    DEFAULT_MAX_INDEX_SIZE_MB,
    DEFAULT_MAX_VECTORS,
    DEFAULT_MIN_FREE_DISK_MB,
    DEFAULT_WARN_THRESHOLD,
)

from .preflight import (
    run_preflight_checks,
    PreflightResult,
)

from .enforcement import (
    BloatEnforcer,
    EnforcementResult,
    EnforcementStats,
)

from .validation import (
    validate_index_health,
    ValidationResult,
)

__all__ = [
    # Config
    "IndexLimitsConfig",
    "get_limits_config",
    "reset_limits_config",
    "DEFAULT_MAX_FILE_BYTES",
    "DEFAULT_MAX_SYMBOLS_PER_FILE",
    "DEFAULT_MAX_TOTAL_SYMBOLS",
    "DEFAULT_MAX_INDEX_SIZE_MB",
    "DEFAULT_MAX_VECTORS",
    "DEFAULT_MIN_FREE_DISK_MB",
    "DEFAULT_WARN_THRESHOLD",
    # Preflight
    "run_preflight_checks",
    "PreflightResult",
    # Enforcement
    "BloatEnforcer",
    "EnforcementResult",
    "EnforcementStats",
    # Validation
    "validate_index_health",
    "ValidationResult",
]
