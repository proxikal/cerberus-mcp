from pathlib import Path
from typing import Union

from cerberus.tracing import trace
from cerberus.logging_config import logger
from cerberus.index.json_store import JSONIndexStore
from cerberus.schemas import ScanResult
from cerberus.storage import SQLiteIndexStore, ScanResultAdapter


def is_sqlite_index(index_path: Path) -> bool:
    """
    Detect if index is SQLite format.

    Returns:
        True if SQLite index, False if JSON
    """
    # Check if path is a .db file
    if index_path.suffix == '.db':
        return True

    # Check if directory contains cerberus.db
    if index_path.is_dir() and (index_path / "cerberus.db").exists():
        return True

    # Otherwise assume JSON
    return False


@trace
def load_index(index_path: Path) -> Union[ScanResult, ScanResultAdapter]:
    """
    Load an index from disk with automatic format detection.

    Supports both legacy JSON format and new SQLite format.

    Args:
        index_path: Path to index file (.json) or directory (with cerberus.db)

    Returns:
        ScanResult for JSON indices (full load, legacy)
        ScanResultAdapter for SQLite indices (lazy load, streaming)

    Raises:
        FileNotFoundError: If index doesn't exist
        IndexCorruptionError: If index is corrupted or invalid
    """
    if not index_path.exists():
        raise FileNotFoundError(f"Index not found at {index_path}")

    if is_sqlite_index(index_path):
        # New SQLite format - streaming/lazy loading
        logger.info(f"Loading SQLite index from {index_path}")
        store = SQLiteIndexStore(index_path)
        return ScanResultAdapter(store)
    else:
        # Legacy JSON format - full load
        logger.info(f"Loading legacy index from {index_path}")
        store = JSONIndexStore(index_path)
        return store.read()
