"""
Unit tests for SQLite and FAISS storage layer.

Tests cover:
- SQLite CRUD operations
- Transaction management
- Streaming queries
- FAISS vector operations (optional - skipped if FAISS not installed)
- Integration between SQLite and FAISS
"""

import pytest
import numpy as np
from pathlib import Path

from cerberus.storage.sqlite_store import SQLiteIndexStore
from cerberus.schemas import (
    FileObject,
    CodeSymbol,
    ImportReference,
    CallReference,
    TypeInfo,
    ImportLink,
)

# Check if FAISS is actually available (not just if the module can be imported)
try:
    import faiss  # Try to import faiss directly
    from cerberus.storage.faiss_store import FAISSVectorStore
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    FAISSVectorStore = None  # Placeholder for type hints

# Skip marker for FAISS tests
requires_faiss = pytest.mark.skipif(
    not FAISS_AVAILABLE,
    reason="FAISS not installed - optional dependency for Cerberus Enterprise (install: pip install faiss-cpu)"
)


# ========== SQLite Store Tests ==========

def test_sqlite_store_initialization(tmp_path):
    """Test database initialization with schema."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    assert store.db_path.exists()
    assert store.get_metadata('schema_version') == '1.0.0'


def test_write_and_query_files(tmp_path):
    """Test writing and querying files."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(
        path="test.py",
        abs_path="/abs/test.py",
        size=100,
        last_modified=123.456
    )

    store.write_file(file_obj)

    # Verify via stats
    stats = store.get_stats()
    assert stats['total_files'] == 1


def test_write_and_query_symbols(tmp_path):
    """Test writing and streaming query of symbols."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    # Write file first (foreign key constraint)
    file_obj = FileObject(path="a.py", abs_path="/abs/a.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    # Write symbols
    symbols = [
        CodeSymbol(
            name="foo",
            type="function",
            file_path="a.py",
            start_line=1,
            end_line=10,
            signature="def foo():",
        ),
        CodeSymbol(
            name="Bar",
            type="class",
            file_path="a.py",
            start_line=15,
            end_line=30,
        ),
    ]

    store.write_symbols_batch(symbols)

    # Query all symbols
    result = list(store.query_symbols())
    assert len(result) == 2
    assert result[0].name == "foo"
    assert result[1].name == "Bar"

    # Query filtered by name
    result = list(store.query_symbols(filter={'name': 'foo'}))
    assert len(result) == 1
    assert result[0].type == "function"

    # Query filtered by file_path
    result = list(store.query_symbols(filter={'file_path': 'a.py'}))
    assert len(result) == 2


def test_write_symbols_with_parameters(tmp_path):
    """Test symbols with parameter lists (JSON serialization)."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    symbol = CodeSymbol(
        name="func",
        type="function",
        file_path="test.py",
        start_line=1,
        end_line=10,
        parameters=["arg1", "arg2", "arg3"],
    )

    store.write_symbols_batch([symbol])

    # Query and verify parameters are deserialized correctly
    result = list(store.query_symbols(filter={'name': 'func'}))
    assert len(result) == 1
    assert result[0].parameters == ["arg1", "arg2", "arg3"]


def test_write_and_query_imports(tmp_path):
    """Test writing and querying imports."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    imports = [
        ImportReference(module="os", file_path="test.py", line=1),
        ImportReference(module="sys", file_path="test.py", line=2),
    ]

    store.write_imports_batch(imports)

    stats = store.get_stats()
    assert stats['total_imports'] == 2


def test_write_and_query_calls(tmp_path):
    """Test writing and querying call references."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    calls = [
        CallReference(caller_file="test.py", callee="foo", line=10),
        CallReference(caller_file="test.py", callee="bar", line=20),
        CallReference(caller_file="test.py", callee="foo", line=30),
    ]

    store.write_calls_batch(calls)

    # Query by callee
    result = list(store.query_calls_by_callee("foo"))
    assert len(result) == 2
    assert all(c.callee == "foo" for c in result)

    stats = store.get_stats()
    assert stats['total_calls'] == 3


def test_write_and_query_type_infos(tmp_path):
    """Test writing and querying type information."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    type_infos = [
        TypeInfo(
            name="x",
            type_annotation="int",
            inferred_type=None,
            file_path="test.py",
            line=5
        ),
    ]

    store.write_type_infos_batch(type_infos)

    stats = store.get_stats()
    assert stats['total_type_infos'] == 1


def test_write_and_query_import_links(tmp_path):
    """Test writing and querying import links."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="main.py", abs_path="/main.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    import_links = [
        ImportLink(
            importer_file="main.py",
            imported_module="utils",
            imported_symbols=["helper", "process"],
            import_line=1,
            definition_file="utils.py",
            definition_symbol="helper",
        ),
    ]

    store.write_import_links_batch(import_links)

    # Query by importer_file (returns Iterator, convert to list)
    result = list(store.query_import_links(filter={'importer_file': 'main.py'}))
    assert len(result) == 1
    assert result[0].imported_symbols == ["helper", "process"]

    stats = store.get_stats()
    assert stats['total_import_links'] == 1


def test_delete_file_cascade(tmp_path):
    """Test file deletion with foreign key cascade."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    # Write file and related data
    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    symbol = CodeSymbol(
        name="func",
        type="function",
        file_path="test.py",
        start_line=1,
        end_line=10,
    )
    store.write_symbols_batch([symbol])

    call = CallReference(caller_file="test.py", callee="foo", line=5)
    store.write_calls_batch([call])

    # Verify data exists
    assert store.get_stats()['total_symbols'] == 1
    assert store.get_stats()['total_calls'] == 1

    # Delete file
    store.delete_file("test.py")

    # Verify cascade deletion
    assert store.get_stats()['total_files'] == 0
    assert store.get_stats()['total_symbols'] == 0
    assert store.get_stats()['total_calls'] == 0


def test_find_symbol_by_line(tmp_path):
    """Test finding symbol containing a specific line."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    symbols = [
        CodeSymbol(name="outer", type="class", file_path="test.py", start_line=1, end_line=50),
        CodeSymbol(name="inner", type="method", file_path="test.py", start_line=10, end_line=20),
    ]
    store.write_symbols_batch(symbols)

    # Line 15 is inside 'inner' method
    result = store.find_symbol_by_line("test.py", 15)
    assert result is not None
    assert result.name == "inner"  # Should return smallest containing symbol

    # Line 30 is inside 'outer' but outside 'inner'
    result = store.find_symbol_by_line("test.py", 30)
    assert result is not None
    assert result.name == "outer"

    # Line 100 is outside all symbols
    result = store.find_symbol_by_line("test.py", 100)
    assert result is None


def test_transaction_commit(tmp_path):
    """Test transaction commit on success."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    symbol = CodeSymbol(name="func", type="function", file_path="test.py", start_line=1, end_line=10)

    with store.transaction() as conn:
        store.write_file(file_obj, conn=conn)
        store.write_symbols_batch([symbol], conn=conn)

    # Verify data was committed
    assert store.get_stats()['total_files'] == 1
    assert store.get_stats()['total_symbols'] == 1


def test_transaction_rollback(tmp_path):
    """Test transaction rollback on exception."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)

    try:
        with store.transaction() as conn:
            store.write_file(file_obj, conn=conn)
            raise ValueError("Forced error")
    except ValueError:
        pass

    # Verify rollback - no data should exist
    assert store.get_stats()['total_files'] == 0


def test_metadata_operations(tmp_path):
    """Test metadata get/set operations."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    # Set metadata
    store.set_metadata('project_root', '/path/to/project')
    store.set_metadata('git_commit', 'abc123')

    # Get metadata
    assert store.get_metadata('project_root') == '/path/to/project'
    assert store.get_metadata('git_commit') == 'abc123'

    # Non-existent key
    assert store.get_metadata('nonexistent') is None

    # Update existing
    store.set_metadata('git_commit', 'def456')
    assert store.get_metadata('git_commit') == 'def456'


def test_get_stats(tmp_path):
    """Test comprehensive stats reporting."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    symbol = CodeSymbol(name="func", type="function", file_path="test.py", start_line=1, end_line=10)
    store.write_symbols_batch([symbol])

    stats = store.get_stats()

    assert stats['total_files'] == 1
    assert stats['total_symbols'] == 1
    assert stats['total_embeddings'] == 0
    assert stats['total_calls'] == 0
    assert stats['total_imports'] == 0
    assert stats['total_type_infos'] == 0
    assert stats['total_import_links'] == 0
    assert stats['db_size_bytes'] > 0


def test_streaming_batch_size(tmp_path):
    """Test streaming queries with different batch sizes."""
    store = SQLiteIndexStore(tmp_path / "test.db")

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    store.write_file(file_obj)

    # Write 50 symbols
    symbols = [
        CodeSymbol(name=f"func_{i}", type="function", file_path="test.py", start_line=i, end_line=i+1)
        for i in range(50)
    ]
    store.write_symbols_batch(symbols)

    # Query with small batch size
    result = list(store.query_symbols(batch_size=10))
    assert len(result) == 50

    # Query with large batch size
    result = list(store.query_symbols(batch_size=100))
    assert len(result) == 50


# ========== FAISS Store Tests ==========

@pytest.fixture
def faiss_store(tmp_path):
    """Fixture providing a FAISS store instance."""
    if not FAISS_AVAILABLE:
        pytest.skip("FAISS not installed - optional dependency for Cerberus Enterprise")
    return FAISSVectorStore(tmp_path / "faiss_index", dimension=384)


@requires_faiss
def test_faiss_initialization(faiss_store):
    """Test FAISS store initialization."""
    assert faiss_store.dimension == 384
    assert len(faiss_store) == 0
    assert faiss_store.faiss_path.parent.exists()


@requires_faiss
def test_faiss_add_vector(faiss_store):
    """Test adding a single vector."""
    vector = np.random.rand(384).astype(np.float32)
    symbol_id = 1

    faiss_id = faiss_store.add_vector(symbol_id, vector)

    assert faiss_id == 0  # First vector gets ID 0
    assert len(faiss_store) == 1
    assert symbol_id in faiss_store


@requires_faiss
def test_faiss_add_vectors_batch(faiss_store):
    """Test batch adding vectors."""
    vectors = np.random.rand(10, 384).astype(np.float32)
    symbol_ids = list(range(1, 11))

    faiss_ids = faiss_store.add_vectors_batch(symbol_ids, vectors)

    assert len(faiss_ids) == 10
    assert faiss_ids == list(range(10))
    assert len(faiss_store) == 10


@requires_faiss
def test_faiss_vector_normalization(faiss_store):
    """Test that vectors are L2-normalized for cosine similarity."""
    # Create a non-normalized vector
    vector = np.array([3.0, 4.0] + [0.0] * 382, dtype=np.float32)
    assert np.linalg.norm(vector) == 5.0  # Not normalized

    faiss_store.add_vector(symbol_id=1, vector=vector)

    # Query should work with normalized query
    query = np.array([3.0, 4.0] + [0.0] * 382, dtype=np.float32)
    scores, faiss_ids = faiss_store.search(query, k=1)

    # Cosine similarity should be 1.0 (perfect match after normalization)
    assert len(scores) == 1
    assert scores[0] == pytest.approx(1.0, abs=0.01)


@requires_faiss
def test_faiss_search(faiss_store):
    """Test vector similarity search."""
    # Add 5 vectors
    vectors = np.random.rand(5, 384).astype(np.float32)
    symbol_ids = list(range(1, 6))
    faiss_store.add_vectors_batch(symbol_ids, vectors)

    # Search with first vector (should match itself)
    query = vectors[0]
    scores, faiss_ids = faiss_store.search(query, k=3)

    assert len(scores) == 3
    assert faiss_ids[0] == 0  # Best match is the query vector itself
    assert scores[0] == pytest.approx(1.0, abs=0.01)  # Perfect cosine similarity


@requires_faiss
def test_faiss_search_empty_index(faiss_store):
    """Test search on empty index."""
    query = np.random.rand(384).astype(np.float32)
    scores, faiss_ids = faiss_store.search(query, k=10)

    assert len(scores) == 0
    assert len(faiss_ids) == 0


@requires_faiss
def test_faiss_remove_vectors(faiss_store):
    """Test removing vectors (requires index rebuild)."""
    # Add 5 vectors
    vectors = np.random.rand(5, 384).astype(np.float32)
    symbol_ids = list(range(1, 6))
    faiss_store.add_vectors_batch(symbol_ids, vectors)

    assert len(faiss_store) == 5

    # Remove vectors at FAISS IDs 1 and 3
    faiss_store.remove_vectors([1, 3])

    # Should have 3 vectors left
    assert len(faiss_store) == 3

    # Verify ID map updated (symbol IDs 2 and 4 were removed)
    assert 1 in faiss_store  # symbol_id 1 (faiss_id 0) still exists
    assert 2 not in faiss_store  # symbol_id 2 (faiss_id 1) removed
    assert 3 in faiss_store  # symbol_id 3 (faiss_id 2) still exists
    assert 4 not in faiss_store  # symbol_id 4 (faiss_id 3) removed
    assert 5 in faiss_store  # symbol_id 5 (faiss_id 4) still exists


@requires_faiss
def test_faiss_save_and_load(tmp_path):
    """Test persistence of FAISS index and ID map."""
    # Create and populate store
    store1 = FAISSVectorStore(tmp_path / "faiss_index", dimension=384)
    vectors = np.random.rand(3, 384).astype(np.float32)
    symbol_ids = [1, 2, 3]
    store1.add_vectors_batch(symbol_ids, vectors)

    # Save
    store1.save()

    # Load in new instance
    store2 = FAISSVectorStore(tmp_path / "faiss_index", dimension=384)

    # Verify loaded correctly
    assert len(store2) == 3
    assert 1 in store2
    assert 2 in store2
    assert 3 in store2


@requires_faiss
def test_faiss_get_symbol_id(faiss_store):
    """Test reverse lookup from faiss_id to symbol_id."""
    symbol_ids = [10, 20, 30]
    vectors = np.random.rand(3, 384).astype(np.float32)
    faiss_store.add_vectors_batch(symbol_ids, vectors)

    # Reverse lookup
    assert faiss_store.get_symbol_id(0) == 10
    assert faiss_store.get_symbol_id(1) == 20
    assert faiss_store.get_symbol_id(2) == 30

    # Non-existent faiss_id
    with pytest.raises(KeyError):
        faiss_store.get_symbol_id(999)


@requires_faiss
def test_faiss_get_stats(faiss_store):
    """Test stats reporting."""
    vectors = np.random.rand(10, 384).astype(np.float32)
    symbol_ids = list(range(1, 11))
    faiss_store.add_vectors_batch(symbol_ids, vectors)

    stats = faiss_store.get_stats()

    assert stats['total_vectors'] == 10
    assert stats['dimension'] == 384
    assert stats['index_type'] == 'IndexFlatIP'
    assert stats['faiss_size_bytes'] >= 0
    assert stats['id_map_size_bytes'] >= 0


@requires_faiss
def test_faiss_clear(faiss_store):
    """Test clearing all vectors."""
    vectors = np.random.rand(5, 384).astype(np.float32)
    symbol_ids = list(range(1, 6))
    faiss_store.add_vectors_batch(symbol_ids, vectors)

    assert len(faiss_store) == 5

    faiss_store.clear()

    assert len(faiss_store) == 0
    assert not (1 in faiss_store)


# ========== Integration Tests ==========

@requires_faiss
def test_sqlite_faiss_integration(tmp_path):
    """Test integration between SQLite and FAISS for embeddings."""
    # Create stores
    sqlite_store = SQLiteIndexStore(tmp_path / "test.db")
    faiss_store = FAISSVectorStore(tmp_path / "faiss_index", dimension=384)

    # Write file and symbols to SQLite
    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    sqlite_store.write_file(file_obj)

    symbols = [
        CodeSymbol(name=f"func_{i}", type="function", file_path="test.py", start_line=i, end_line=i+1)
        for i in range(3)
    ]

    with sqlite_store.transaction() as conn:
        symbol_ids = sqlite_store.write_symbols_batch(symbols, conn=conn)

        # Add embeddings to FAISS
        vectors = np.random.rand(3, 384).astype(np.float32)
        faiss_ids = faiss_store.add_vectors_batch(symbol_ids, vectors)

        # Write embedding metadata to SQLite
        for symbol_id, faiss_id, symbol in zip(symbol_ids, faiss_ids, symbols):
            sqlite_store.write_embedding_metadata(
                symbol_id=symbol_id,
                faiss_id=faiss_id,
                name=symbol.name,
                file_path=symbol.file_path,
                model="all-MiniLM-L6-v2",
                conn=conn
            )

    # Verify stats
    sqlite_stats = sqlite_store.get_stats()
    faiss_stats = faiss_store.get_stats()

    assert sqlite_stats['total_symbols'] == 3
    assert sqlite_stats['total_embeddings'] == 3
    assert faiss_stats['total_vectors'] == 3

    # Test vector search and symbol lookup
    query = vectors[0]
    scores, faiss_ids_result = faiss_store.search(query, k=1)

    # Get symbol_id from FAISS ID
    symbol_id = faiss_store.get_symbol_id(faiss_ids_result[0])

    # Query symbol from SQLite
    result_symbols = list(sqlite_store.query_symbols())
    matched_symbol = next((s for s in result_symbols if s.name == f"func_0"), None)

    assert matched_symbol is not None
    assert matched_symbol.name == "func_0"


@requires_faiss
def test_delete_file_with_embeddings(tmp_path):
    """Test that deleting a file also removes embedding metadata."""
    sqlite_store = SQLiteIndexStore(tmp_path / "test.db")
    faiss_store = FAISSVectorStore(tmp_path / "faiss_index", dimension=384)

    # Create file, symbol, and embedding
    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    symbol = CodeSymbol(name="func", type="function", file_path="test.py", start_line=1, end_line=10)

    with sqlite_store.transaction() as conn:
        sqlite_store.write_file(file_obj, conn=conn)
        symbol_ids = sqlite_store.write_symbols_batch([symbol], conn=conn)

        vector = np.random.rand(384).astype(np.float32)
        faiss_id = faiss_store.add_vector(symbol_ids[0], vector)

        sqlite_store.write_embedding_metadata(
            symbol_id=symbol_ids[0],
            faiss_id=faiss_id,
            name=symbol.name,
            file_path=symbol.file_path,
            model="test-model",
            conn=conn
        )

    # Verify exists
    assert sqlite_store.get_stats()['total_embeddings'] == 1

    # Delete file (should cascade to embeddings_metadata)
    faiss_ids_to_remove = sqlite_store.delete_file("test.py")

    # Verify cascade
    assert sqlite_store.get_stats()['total_symbols'] == 0
    assert sqlite_store.get_stats()['total_embeddings'] == 0
    assert len(faiss_ids_to_remove) == 1

    # Clean up FAISS
    faiss_store.remove_vectors(faiss_ids_to_remove)
    assert len(faiss_store) == 0
