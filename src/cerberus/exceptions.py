# Custom exceptions for Cerberus

class CerberusError(Exception):
    """Base exception for all application-specific errors."""
    pass

class ParserError(CerberusError):
    """Raised when a file cannot be parsed by tree-sitter."""
    def __init__(self, file_path: str, message: str):
        self.file_path = file_path
        self.message = message
        super().__init__(f"Failed to parse {file_path}: {message}")

class GrammarNotFoundError(CerberusError):
    """Raised when a required tree-sitter grammar is not found."""
    def __init__(self, language: str, install_command: str):
        self.language = language
        self.install_command = install_command
        super().__init__(f"Grammar for '{language}' not found. Please install it.")

class IndexCorruptionError(CerberusError):
    """Raised if the internal index/database fails a sanity check."""
    pass

class ConfigError(CerberusError):
    """Raised for configuration-related problems."""
    pass


class IndexLimitExceeded(CerberusError):
    """Raised when an index limit is exceeded."""

    def __init__(
        self,
        limit_name: str,
        current: int,
        maximum: int,
        remediation: str = "",
    ):
        self.limit_name = limit_name
        self.current = current
        self.maximum = maximum
        self.remediation = remediation
        message = (
            f"Index limit '{limit_name}' exceeded: {current:,} > {maximum:,}."
        )
        if remediation:
            message += f" {remediation}"
        super().__init__(message)


class PreflightError(CerberusError):
    """Raised when pre-flight checks fail."""

    def __init__(self, message: str, checks: list = None):
        self.checks = checks or []
        super().__init__(message)
