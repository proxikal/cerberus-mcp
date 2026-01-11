"""Integration tests for SQLite and FAISS storage layers.

Tests cover the integration between SQLite and FAISS for embeddings.
"""

import pytest
import numpy as np
from pathlib import Path

pytestmark = pytest.mark.integration

from cerberus.storage.sqlite_store import SQLiteIndexStore
from cerberus.schemas import FileObject, CodeSymbol

# Check if FAISS is available
try:
    import faiss
    from cerberus.storage.faiss_store import FAISSVectorStore
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    FAISSVectorStore = None

requires_faiss = pytest.mark.skipif(
    not FAISS_AVAILABLE,
    reason="FAISS not installed - optional dependency for Cerberus Enterprise (install: pip install faiss-cpu)"
)


@requires_faiss
def test_sqlite_faiss_integration(tmp_path):
    """Test integration between SQLite and FAISS for embeddings."""
    sqlite_store = SQLiteIndexStore(tmp_path / "test.db")
    faiss_store = FAISSVectorStore(tmp_path / "faiss_index", dimension=384)

    file_obj = FileObject(path="test.py", abs_path="/test.py", size=100, last_modified=1.0)
    sqlite_store.write_file(file_obj)

    symbols = [
        CodeSymbol(name=f"func_{i}", type="function", file_path="test.py", start_line=i, end_line=i+1)
        for i in range(3)
    ]

    with sqlite_store.transaction() as conn:
        symbol_ids = sqlite_store.write_symbols_batch(symbols, conn=conn)

        vectors = np.random.rand(3, 384).astype(np.float32)
        faiss_ids = faiss_store.add_vectors_batch(symbol_ids, vectors)

        for symbol_id, faiss_id, symbol in zip(symbol_ids, faiss_ids, symbols):
            sqlite_store.write_embedding_metadata(
                symbol_id=symbol_id,
                faiss_id=faiss_id,
                name=symbol.name,
                file_path=symbol.file_path,
                model="all-MiniLM-L6-v2",
                conn=conn
            )

    sqlite_stats = sqlite_store.get_stats()
    faiss_stats = faiss_store.get_stats()

    assert sqlite_stats['total_symbols'] == 3
    assert sqlite_stats['total_embeddings'] == 3
    assert faiss_stats['total_vectors'] == 3

    query = vectors[0]
    scores, faiss_ids_result = faiss_store.search(query, k=1)

    symbol_id = faiss_store.get_symbol_id(faiss_ids_result[0])

    result_symbols = list(sqlite_store.query_symbols())
    matched_symbol = next((s for s in result_symbols if s.name == f"func_0"), None)

    assert matched_symbol is not None
    assert matched_symbol.name == "func_0"


@requires_faiss
def test_delete_file_with_embeddings(tmp_path):
    """Test that deleting a file also removes embedding metadata."""
    sqlite_store = SQLiteIndexStore(tmp_path / "test.db")
    faiss_store = FAISSVectorStore(tmp_path / "faiss_index", dimension=384)

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

    assert sqlite_store.get_stats()['total_embeddings'] == 1

    faiss_ids_to_remove = sqlite_store.delete_file("test.py")

    assert sqlite_store.get_stats()['total_symbols'] == 0
    assert sqlite_store.get_stats()['total_embeddings'] == 0
    assert len(faiss_ids_to_remove) == 1

    faiss_store.remove_vectors(faiss_ids_to_remove)
    assert len(faiss_store) == 0
