from pathlib import Path

from cerberus.tracing import trace
from cerberus.index.json_store import JSONIndexStore
from cerberus.schemas import ScanResult


@trace
def load_index(index_path: Path) -> ScanResult:
    """
    Load an index from disk.
    """
    store = JSONIndexStore(index_path)
    return store.read()
