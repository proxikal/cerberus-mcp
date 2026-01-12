import re
from typing import Dict

from cerberus.exceptions import ConfigError

# Mapping of file extensions to language names used in this module
SUPPORTED_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".md": "markdown",
}

# Regex patterns for finding symbols.
# We use re.MULTILINE to allow ^ to match the start of each line.
LANGUAGE_QUERIES = {
    "python": {
        "class": re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
        "function": re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
    },
    "javascript": {
        "class": re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
        "function": re.compile(r"^\s*(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
    },
    "typescript": {
        "class": re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
        "function": re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
        "interface": re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
        "enum": re.compile(r"^\s*(?:export\s+)?enum\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
        "variable": re.compile(r"^\s*(?:export\s+)?const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=", re.MULTILINE),
        "method": re.compile(r"^\s*(?:async\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*\{", re.MULTILINE),
    },
    "go": {
        "function": re.compile(r"^\s*func\s+(?:\([^)]+\)\s*)?([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
        "struct": re.compile(r"^\s*type\s+([A-Za-z_][A-Za-z0-9_]*)\s+struct", re.MULTILINE),
    },
    "markdown": {
        "section": re.compile(r"^#{1,6}\s+(.+)", re.MULTILINE),
    },
}


def validate_language_config(language: str) -> None:
    """
    Validate that a language is supported and properly configured.

    Args:
        language: The language name to validate.

    Raises:
        ConfigError: If the language is not supported or misconfigured.
    """
    if language not in LANGUAGE_QUERIES:
        supported = ", ".join(LANGUAGE_QUERIES.keys())
        raise ConfigError(
            f"Language '{language}' is not supported. Supported languages: {supported}"
        )

    queries = LANGUAGE_QUERIES[language]
    if not isinstance(queries, dict) or not queries:
        raise ConfigError(
            f"Language '{language}' has invalid or empty query patterns"
        )

    # Validate all patterns are compiled regexes
    for symbol_type, pattern in queries.items():
        if not isinstance(pattern, re.Pattern):
            raise ConfigError(
                f"Language '{language}' symbol type '{symbol_type}' has invalid regex pattern"
            )


def validate_extension(extension: str) -> str:
    """
    Validate a file extension and return its language.

    Args:
        extension: File extension (e.g., '.py', '.js')

    Returns:
        The language name for the extension.

    Raises:
        ConfigError: If the extension is not supported.
    """
    if extension not in SUPPORTED_LANGUAGES:
        supported = ", ".join(SUPPORTED_LANGUAGES.keys())
        raise ConfigError(
            f"File extension '{extension}' is not supported. Supported extensions: {supported}"
        )

    return SUPPORTED_LANGUAGES[extension]
