"""
Resolution package for Phase 5: Symbolic Intelligence.

Provides import resolution, type tracking, and symbol reference resolution.
"""

from .facade import resolve_imports, resolve_types, get_resolution_stats
from .resolver import ImportResolver
from .type_tracker import TypeTracker
from .config import CONFIDENCE_THRESHOLDS, RESOLUTION_CONFIG

__all__ = [
    "resolve_imports",
    "resolve_types",
    "get_resolution_stats",
    "ImportResolver",
    "TypeTracker",
    "CONFIDENCE_THRESHOLDS",
    "RESOLUTION_CONFIG",
]
