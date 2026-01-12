"""Unit tests for FAISS vector storage layer.

Tests cover FAISS vector operations - skipped if FAISS not installed.
"""

import pytest
import numpy as np
from pathlib import Path

pytestmark = pytest.mark.fast

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

    assert faiss_id == 0
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
    vector = np.array([3.0, 4.0] + [0.0] * 382, dtype=np.float32)
    assert np.linalg.norm(vector) == 5.0

    faiss_store.add_vector(symbol_id=1, vector=vector)

    query = np.array([3.0, 4.0] + [0.0] * 382, dtype=np.float32)
    scores, faiss_ids = faiss_store.search(query, k=1)

    assert len(scores) == 1
    assert scores[0] == pytest.approx(1.0, abs=0.01)


@requires_faiss
def test_faiss_search(faiss_store):
    """Test vector similarity search."""
    vectors = np.random.rand(5, 384).astype(np.float32)
    symbol_ids = list(range(1, 6))
    faiss_store.add_vectors_batch(symbol_ids, vectors)

    query = vectors[0]
    scores, faiss_ids = faiss_store.search(query, k=3)

    assert len(scores) == 3
    assert faiss_ids[0] == 0
    assert scores[0] == pytest.approx(1.0, abs=0.01)


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
    vectors = np.random.rand(5, 384).astype(np.float32)
    symbol_ids = list(range(1, 6))
    faiss_store.add_vectors_batch(symbol_ids, vectors)

    assert len(faiss_store) == 5

    faiss_store.remove_vectors([1, 3])

    assert len(faiss_store) == 3
    assert 1 in faiss_store
    assert 2 not in faiss_store
    assert 3 in faiss_store
    assert 4 not in faiss_store
    assert 5 in faiss_store


@requires_faiss
def test_faiss_save_and_load(tmp_path):
    """Test persistence of FAISS index and ID map."""
    store1 = FAISSVectorStore(tmp_path / "faiss_index", dimension=384)
    vectors = np.random.rand(3, 384).astype(np.float32)
    symbol_ids = [1, 2, 3]
    store1.add_vectors_batch(symbol_ids, vectors)

    store1.save()

    store2 = FAISSVectorStore(tmp_path / "faiss_index", dimension=384)

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

    assert faiss_store.get_symbol_id(0) == 10
    assert faiss_store.get_symbol_id(1) == 20
    assert faiss_store.get_symbol_id(2) == 30

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
