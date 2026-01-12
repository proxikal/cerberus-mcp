"""
Configuration for Phase 11: Symbolic Editing (Mutation).

Contains all settings, thresholds, and formatter configurations.
"""

from cerberus.paths import get_paths


def get_mutation_config():
    """
    Get mutation configuration with dynamic paths.

    Paths are resolved at runtime to support .cerberus/ directory structure.
    """
    paths = get_paths()
    return {
        "backup_enabled": True,
        "backup_dir": str(paths.backups_dir),
        "auto_format_enabled": True,
        "black_line_length": 88,
        "auto_inject_imports": True,
        "syntax_check_required": True,
        "semantic_check_warning_only": True,
        "ledger_enabled": True,
        "ledger_path": str(paths.ledger_db),
    }


# For backward compatibility - returns config with current paths
MUTATION_CONFIG = get_mutation_config()

FORMATTERS = {
    "python": {
        "command": "black",
        "args": ["--quiet", "-"],
        "extensions": [".py"],
    },
    "javascript": {
        "command": "prettier",
        "args": ["--parser", "babel"],
        "extensions": [".js", ".jsx"],
    },
    "typescript": {
        "command": "prettier",
        "args": ["--parser", "typescript"],
        "extensions": [".ts", ".tsx"],
    },
}

SAFETY_THRESHOLDS = {
    "max_deletion_ratio": 0.3,  # Don't delete >30% of file
    "min_confidence": 0.8,      # Minimum confidence for auto-apply
}

INDENT_DETECTION = {
    "default_indent": "    ",  # 4 spaces
    "tab_width": 4,
    "max_sample_lines": 100,   # Lines to sample for indent detection
}
