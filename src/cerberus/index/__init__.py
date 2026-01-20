"""
Public API for the indexing subsystem.
"""
from pathlib import Path
from typing import Union
from .json_store import JSONIndexStore
from .index_builder import build_index
from .index_loader import load_index, is_sqlite_index
from .stats import compute_stats
from cerberus.retrieval.utils import find_symbol, find_symbol_fts, read_range
from cerberus.semantic.search import semantic_search
from cerberus.schemas import ScanResult
from cerberus.storage import ScanResultAdapter


def save_index(scan_result: Union[ScanResult, ScanResultAdapter], index_path: Path) -> Path:
    """
    Save a ScanResult or ScanResultAdapter to an index file.

    Supports both legacy JSON format and new SQLite format.

    Args:
        scan_result: The scan result to save (ScanResult for JSON, ScanResultAdapter for SQLite)
        index_path: Path to save the index to

    Returns:
        Path to the saved index file

    Raises:
        ValueError: If SQLite adapter is used but index format is JSON
    """
    # Check if this is a SQLite adapter
    if isinstance(scan_result, ScanResultAdapter):
        # For SQLite, the data is already persisted to disk
        # We just need to update metadata if needed
        # The store is already saved, so we just return the path
        return scan_result._store.db_path

    # Legacy JSON format
    if isinstance(scan_result, ScanResult):
        store = JSONIndexStore(index_path)
        return store.write(scan_result)

    raise ValueError(f"Unsupported scan_result type: {type(scan_result)}")


__all__ = [
    "JSONIndexStore",
    "build_index",
    "load_index",
    "save_index",
    "compute_stats",
    "find_symbol",
    "find_symbol_fts",
    "read_range",
    "semantic_search",
]
