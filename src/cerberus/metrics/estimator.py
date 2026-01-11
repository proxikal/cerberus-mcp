"""
Estimate token counts for files.
Phase 16.2: Token baseline estimation for savings tracking.
"""
import os
from pathlib import Path


def estimate_file_tokens(file_path: str) -> int:
    """
    Estimate tokens in a file if read fully.
    Rough heuristic: 1 token ≈ 4 characters

    Args:
        file_path: Path to file

    Returns:
        Estimated token count
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return 0

        # Get file size in bytes
        size_bytes = os.path.getsize(path)

        # Estimate characters (assume UTF-8, ~1 byte per char)
        estimated_chars = size_bytes

        # Convert to tokens (1 token ≈ 4 chars)
        estimated_tokens = estimated_chars // 4

        return estimated_tokens
    except (OSError, IOError):
        return 0


def estimate_text_tokens(text: str) -> int:
    """
    Estimate tokens in a text string.

    Args:
        text: Text to estimate

    Returns:
        Estimated token count
    """
    return len(text) // 4
