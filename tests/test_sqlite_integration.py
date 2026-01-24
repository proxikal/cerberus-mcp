"""
Integration tests for SQLite + FAISS index building.

Tests the full pipeline: scan → SQLite write → load → query
"""

import pytest
from pathlib import Path

pytestmark = pytest.mark.integration

from cerberus.index import build_index, load_index
from cerberus.storage import ScanResultAdapter, SQLiteIndexStore

# Check if FAISS is actually available (not just if the module can be imported)
try:
    import faiss  # Try to import faiss directly
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

requires_faiss = pytest.mark.skipif(
    not FAISS_AVAILABLE,
    reason="FAISS not installed - optional dependency for Cerberus Enterprise (install: pip install faiss-cpu)"
)


def test_build_sqlite_index(tmp_path):
    """Test building a SQLite index from test files directory."""
    # Build SQLite index (not .json suffix triggers SQLite)
    demo_dir = Path(__file__).parent / "test_files"
    output_path = tmp_path / "test_index"

    result = build_index(
        directory=demo_dir,
        output_path=output_path,
        respect_gitignore=False,
        store_embeddings=False,
    )

    # Verify it's a SQLite index
    assert isinstance(result, ScanResultAdapter)
    assert (output_path / "cerberus.db").exists()

    # Verify data was written
    stats = result._store.get_stats()
    assert stats['total_files'] > 0
    assert stats['total_symbols'] > 0

    # Verify lazy loading works
    symbols = result.symbols
    assert len(symbols) > 0

    files = result.files
    assert len(files) > 0


def test_load_sqlite_index(tmp_path):
    """Test loading a SQLite index."""
    # Build first
    demo_dir = Path(__file__).parent / "test_files"
    output_path = tmp_path / "test_index"

    build_index(
        directory=demo_dir,
        output_path=output_path,
        respect_gitignore=False,
        store_embeddings=False,
    )

    # Load
    result = load_index(output_path)

    # Verify it's a SQLite adapter
    assert isinstance(result, ScanResultAdapter)

    # Verify data is accessible
    assert result.total_files > 0
    assert len(result.symbols) > 0


@requires_faiss
def test_sqlite_index_with_embeddings(tmp_path):
    """Test building SQLite index with FAISS embeddings."""
    demo_dir = Path(__file__).parent / "test_files"
    output_path = tmp_path / "test_index_with_embeddings"

    result = build_index(
        directory=demo_dir,
        output_path=output_path,
        respect_gitignore=False,
        store_embeddings=True,  # Enable FAISS
    )

    assert isinstance(result, ScanResultAdapter)

    # Verify FAISS files created
    assert (output_path / "vectors.faiss").exists()
    assert (output_path / "vector_id_map.pkl").exists()

    # Verify embeddings count
    stats = result._store.get_stats()
    assert stats['total_embeddings'] == stats['total_symbols']


def test_json_compatibility(tmp_path):
    """Test that JSON format still works (backward compatibility)."""
    demo_dir = Path(__file__).parent / "test_files"
    output_path = tmp_path / "test_index.json"  # .json triggers JSON format

    result = build_index(
        directory=demo_dir,
        output_path=output_path,
        respect_gitignore=False,
        store_embeddings=False,
    )

    # Verify it's NOT a SQLite adapter (it's a ScanResult)
    assert not isinstance(result, ScanResultAdapter)
    assert hasattr(result, 'symbols')

    # Verify JSON file created
    assert output_path.exists()
    assert output_path.suffix == '.json'


def test_sqlite_query_symbols_streaming(tmp_path):
    """Test streaming symbol queries."""
    demo_dir = Path(__file__).parent / "test_files"
    output_path = tmp_path / "test_index"

    result = build_index(
        directory=demo_dir,
        output_path=output_path,
        respect_gitignore=False,
        store_embeddings=False,
    )

    store = result._store

    # Stream all symbols
    symbol_count = 0
    for symbol in store.query_symbols(batch_size=2):
        symbol_count += 1
        assert symbol.name
        assert symbol.type in ['function', 'class', 'method', 'variable', 'interface', 'enum', 'struct']

    assert symbol_count > 0

    # Filter by name
    filtered = list(store.query_symbols(filter={'name': 'AuthManager'}))
    if filtered:  # May or may not exist in demo
        assert all(s.name == 'AuthManager' for s in filtered)


def test_sqlite_metadata(tmp_path):
    """Test metadata storage in SQLite."""
    demo_dir = Path(__file__).parent / "test_files"
    output_path = tmp_path / "test_index"

    result = build_index(
        directory=demo_dir,
        output_path=output_path,
        respect_gitignore=False,
        store_embeddings=False,
    )

    # Verify metadata
    assert result.project_root
    assert result.total_files > 0
    assert result.scan_duration >= 0

    # Check metadata dict
    store = result._store
    project_root = store.get_metadata('project_root')
    assert project_root


def test_sqlite_adapter_cache_clear(tmp_path):
    """Test cache clearing in adapter."""
    demo_dir = Path(__file__).parent / "test_files"
    output_path = tmp_path / "test_index"

    result = build_index(
        directory=demo_dir,
        output_path=output_path,
        respect_gitignore=False,
        store_embeddings=False,
    )

    # Access to populate cache
    symbols_1 = result.symbols
    assert len(symbols_1) > 0
    assert result._cached_symbols is not None

    # Clear cache
    result.clear_cache()
    assert result._cached_symbols is None

    # Access again (should reload from SQLite)
    symbols_2 = result.symbols
    assert len(symbols_2) == len(symbols_1)


def test_sqlite_transaction_integrity(tmp_path):
    """Test that SQLite transactions maintain integrity."""
    demo_dir = Path(__file__).parent / "test_files"
    output_path = tmp_path / "test_index"

    # Build index
    result = build_index(
        directory=demo_dir,
        output_path=output_path,
        respect_gitignore=False,
        store_embeddings=False,
    )

    store = result._store

    # Get initial counts
    initial_stats = store.get_stats()
    initial_files = initial_stats['total_files']
    initial_symbols = initial_stats['total_symbols']

    # Verify counts match
    assert len(result.files) == initial_files
    assert len(result.symbols) == initial_symbols


def test_format_detection(tmp_path):
    """Test automatic format detection."""
    demo_dir = Path(__file__).parent / "test_files"

    # Build JSON
    json_path = tmp_path / "index.json"
    build_index(demo_dir, json_path, respect_gitignore=False)

    # Build SQLite
    sqlite_path = tmp_path / "sqlite_index"
    build_index(demo_dir, sqlite_path, respect_gitignore=False)

    # Load JSON
    json_result = load_index(json_path)
    assert not isinstance(json_result, ScanResultAdapter)

    # Load SQLite
    sqlite_result = load_index(sqlite_path)
    assert isinstance(sqlite_result, ScanResultAdapter)

    # Verify both have same data (excluding file-level symbols which SQLite doesn't store)
    json_non_file_symbols = [s for s in json_result.symbols if s.type != 'file']
    assert len(json_non_file_symbols) == len(sqlite_result.symbols)
