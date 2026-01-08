"""
Incremental update module for git-aware surgical index updates.

Public API for detecting changes and updating indexes incrementally.
"""

from .facade import detect_changes, update_index_incrementally

__all__ = [
    "detect_changes",
    "update_index_incrementally",
]
