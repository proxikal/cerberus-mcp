"""
Suggestion generation utilities for structured error responses.

Provides fuzzy matching and intelligent suggestions for CLI errors.
"""

from typing import List, Optional
from difflib import get_close_matches


def fuzzy_match_suggestions(input_value: str, candidates: List[str], max_suggestions: int = 3, cutoff: float = 0.6) -> List[str]:
    """
    Generate fuzzy match suggestions for an input value.

    Args:
        input_value: The input that wasn't found
        candidates: List of valid options to match against
        max_suggestions: Maximum number of suggestions to return
        cutoff: Similarity threshold (0.0 to 1.0)

    Returns:
        List of suggested alternatives
    """
    if not candidates:
        return []

    # Use difflib for fuzzy matching
    matches = get_close_matches(input_value, candidates, n=max_suggestions, cutoff=cutoff)

    return matches


def symbol_suggestions(input_value: str, scan_result, max_suggestions: int = 5) -> List[str]:
    """
    Generate symbol suggestions from the scan result.

    Args:
        input_value: The symbol name that wasn't found
        scan_result: ScanResult object containing symbols
        max_suggestions: Maximum number of suggestions

    Returns:
        List of similar symbol names
    """
    try:
        # Get all unique symbol names from scan_result
        all_symbols = list(set(sym.name for sym in scan_result.symbols))

        # Use fuzzy matching to find similar symbols
        return fuzzy_match_suggestions(input_value, all_symbols, max_suggestions=max_suggestions, cutoff=0.5)
    except Exception:
        return []


def file_suggestions(input_value: str, index, max_suggestions: int = 5) -> List[str]:
    """
    Generate file path suggestions from the index.

    Args:
        input_value: The file path that wasn't found
        index: Index instance to search
        max_suggestions: Maximum number of suggestions

    Returns:
        List of similar file paths
    """
    try:
        # Get all file paths from the index
        cursor = index.connection.execute("SELECT DISTINCT file_path FROM symbols ORDER BY file_path")
        all_files = [row[0] for row in cursor.fetchall()]

        # Use fuzzy matching to find similar files
        return fuzzy_match_suggestions(input_value, all_files, max_suggestions=max_suggestions, cutoff=0.4)
    except Exception:
        return []
