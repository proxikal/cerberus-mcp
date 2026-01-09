import sys
import os
from pathlib import Path
from loguru import logger

def setup_logging(level="INFO", suppress_console=None):
    """
    Configures the global logger with the Two-Stream Strategy.
    - Stream 1 (Human): Colorful, readable logs to the console.
    - Stream 2 (Agent): Structured JSON logs to a rotating file in .logs/ directory.

    Args:
        level: Logging level (default: INFO)
        suppress_console: If True, suppress console logging. If None, check CERBERUS_MACHINE_MODE env var.
    """
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

    # Stream 2: Machine-readable agent log file in .logs/ directory
    # Create logs directory if it doesn't exist
    log_dir = Path(".logs")
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / "cerberus_agent.log",
        level="DEBUG",          # Capture all details for the agent
        rotation="50 MB",       # Rotate at 50MB (increased from 10MB)
        retention="3 days",     # Keep logs for 3 days (reduced from 7)
        catch=True,             # Catch errors from logging itself
        serialize=True          # Natively convert records to JSON
    )

# Configure the logger on import (will check env var for machine mode)
setup_logging()
