"""
Storage layer for Cerberus index.

This package provides SQLite-backed storage with FAISS vector search integration,
replacing the legacy JSON-based storage for improved memory efficiency and performance.
"""

from .sqlite_store import SQLiteIndexStore
from .faiss_store import FAISSVectorStore
from .adapter import ScanResultAdapter

__all__ = [
    "SQLiteIndexStore",
    "FAISSVectorStore",
    "ScanResultAdapter",
]
