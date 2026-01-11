import sys
import os
from pathlib import Path
from loguru import logger

# Flag to track if logging has been configured
_logging_configured = False


def setup_logging(level="INFO", suppress_console=None, enable_file_logging=None):
    """
    Configures the global logger.

    By default, only console logging is enabled. File logging is opt-in via
    CERBERUS_FILE_LOGGING=1 environment variable or enable_file_logging=True.

    Args:
        level: Logging level (default: INFO)
        suppress_console: If True, suppress console logging. If None, check CERBERUS_MACHINE_MODE env var.
        enable_file_logging: If True, enable file logging. If None, check CERBERUS_FILE_LOGGING env var.
    """
    global _logging_configured

    # Only configure once to avoid duplicate handlers
    if _logging_configured:
        return
    _logging_configured = True

    logger.remove()

    # Check if console logging should be suppressed
    if suppress_console is None:
        suppress_console = os.getenv("CERBERUS_MACHINE_MODE", "").lower() in ("1", "true", "yes")

    # Stream 1: Human-readable console output (only if not suppressed)
    if not suppress_console:
        logger.add(
            sys.stderr,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            colorize=True
        )

    # Stream 2: File logging is OPT-IN only (disabled by default)
    # Enable via CERBERUS_FILE_LOGGING=1 or enable_file_logging=True
    if enable_file_logging is None:
        enable_file_logging = os.getenv("CERBERUS_FILE_LOGGING", "").lower() in ("1", "true", "yes")

    if enable_file_logging:
        # Use .cerberus/logs/ directory
        from cerberus.paths import get_paths
        paths = get_paths()
        paths.ensure_dirs()
        log_dir = paths.logs_dir

        logger.add(
            log_dir / "cerberus.log",
            level="INFO",           # INFO level only (not DEBUG)
            rotation="10 MB",       # Rotate at 10MB
            retention="1 day",      # Keep logs for 1 day only
            compression="gz",       # Compress old logs
            catch=True,
            serialize=False         # Plain text, not JSON (smaller)
        )


# Configure the logger on import (will check env var for machine mode)
setup_logging()
