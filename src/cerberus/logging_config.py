import sys
from loguru import logger

def setup_logging(level="INFO"):
    """
    Configures the global logger with the Two-Stream Strategy.
    - Stream 1 (Human): Colorful, readable logs to the console.
    - Stream 2 (Agent): Structured JSON logs to a rotating file.
    """
    logger.remove()

    # Stream 1: Human-readable console output
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        colorize=True
    )

    # Stream 2: Machine-readable agent log file, using Loguru's native JSON serialization
    logger.add(
        "cerberus_agent.log",
        level="DEBUG",          # Capture all details for the agent
        rotation="10 MB",       # Rotate the log file when it reaches 10 MB
        retention="7 days",     # Keep logs for 7 days
        catch=True,             # Catch errors from logging itself
        serialize=True          # Natively convert records to JSON
    )

# Configure the logger on import
setup_logging()
logger.info("Logging system configured with Human and Agent streams.")
