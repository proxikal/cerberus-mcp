from typing import List
from pathlib import Path
from cerberus.exceptions import ConfigError

# Default patterns to ignore, mimicking common global gitignore settings
DEFAULT_IGNORE_PATTERNS = [
    ".git/",
    ".gitignore",
    "__pycache__/",
    ".pytest_cache/",
    "build/",
    "dist/",
    "*.egg-info/",
    ".venv/",
    "venv/",
    "node_modules/",
    "*.pyc",
    "*.pyo",
]

WORKFLOW_MD_FILENAMES = {
    "AGENTS.md",
    "CERBERUS.md",
    "CERBERUS-COMMANDS.md",
    "CERBERUS-ARCHITECTURE.md",
    "CERBERUS-DEVELOPMENT.md",
    "CERBERUS-LEADERSHIP.md",
    "CLAUDE.md",
    "CLAUDE-WORKFLOWS.md",
    "HANDOFF.md",
    "PROJECT-GUIDE.md",
    "PROJECT-WORKFLOWS.md",
    "PROJECT-HANDOFF.md",
    "PROJECT-LEADERSHIP.md",
    "PROJECT-VPS-OPS.md",
}

WORKFLOW_MD_SUFFIXES = (
    "-GUIDE.md",
    "-WORKFLOWS.md",
    "-HANDOFF.md",
    "-LEADERSHIP.md",
    "-VPS-OPS.md",
    "-ARCHITECTURE.md",
    "-COMMANDS.md",
    "-DEVELOPMENT.md",
)


def is_workflow_markdown(file_path: Path) -> bool:
    """
    Allowlist workflow markdown files for indexing.
    """
    name = file_path.name
    if name in WORKFLOW_MD_FILENAMES:
        return True
    upper_name = name.upper()
    if upper_name.startswith("PHASE-") or upper_name.startswith("PHASE_"):
        return True
    return any(name.endswith(suffix) for suffix in WORKFLOW_MD_SUFFIXES)


def validate_ignore_patterns(patterns: List[str]) -> None:
    """
    Validate ignore patterns for scanner configuration.

    Args:
        patterns: List of gitignore-style patterns to validate.

    Raises:
        ConfigError: If patterns are invalid or malformed.
    """
    if not isinstance(patterns, list):
        raise ConfigError("Ignore patterns must be a list of strings")

    for pattern in patterns:
        if not isinstance(pattern, str):
            raise ConfigError(f"Invalid ignore pattern: {pattern} (must be a string)")
        if not pattern.strip():
            raise ConfigError("Ignore patterns cannot be empty or whitespace-only")


def validate_extensions(extensions: List[str]) -> None:
    """
    Validate file extension filters.

    Args:
        extensions: List of file extensions (e.g., ['.py', '.js'])

    Raises:
        ConfigError: If extensions are invalid.
    """
    if not isinstance(extensions, list):
        raise ConfigError("Extensions must be a list of strings")

    for ext in extensions:
        if not isinstance(ext, str):
            raise ConfigError(f"Invalid extension: {ext} (must be a string)")
        if not ext.startswith('.'):
            raise ConfigError(f"Extension '{ext}' must start with a dot (e.g., '.py')")
        if len(ext) < 2:
            raise ConfigError(f"Extension '{ext}' is too short (minimum: 2 characters)")


def validate_max_bytes(max_bytes: int) -> None:
    """
    Validate max_bytes configuration for file size filtering.

    Args:
        max_bytes: Maximum file size in bytes.

    Raises:
        ConfigError: If max_bytes is invalid.
    """
    if not isinstance(max_bytes, int):
        raise ConfigError(f"max_bytes must be an integer, got {type(max_bytes).__name__}")
    if max_bytes <= 0:
        raise ConfigError(f"max_bytes must be positive, got {max_bytes}")
