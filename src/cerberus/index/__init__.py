"""
Public API for the indexing subsystem.
"""
from pathlib import Path
from .json_store import JSONIndexStore
from .index_builder import build_index
from .index_loader import load_index
from .stats import compute_stats
from cerberus.retrieval.utils import find_symbol, read_range
from cerberus.semantic.search import semantic_search
from cerberus.schemas import ScanResult


def save_index(scan_result: ScanResult, index_path: Path) -> Path:
    """
    Save a ScanResult to an index file.

    Args:
        scan_result: The scan result to save
        index_path: Path to save the index to

    Returns:
        Path to the saved index file
    """
    store = JSONIndexStore(index_path)
    return store.write(scan_result)


__all__ = [
    "JSONIndexStore",
    "build_index",
    "load_index",
    "save_index",
    "compute_stats",
    "find_symbol",
    "read_range",
    "semantic_search",
]
