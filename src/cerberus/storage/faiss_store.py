"""
FAISS-backed vector storage for semantic search.

Provides efficient similarity search over symbol embeddings with
L2-normalized vectors for cosine similarity.
"""

import pickle
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

from cerberus.logging_config import logger


class FAISSVectorStore:
    """
    FAISS vector storage for symbol embeddings.

    Uses IndexFlatIP (inner product) with L2-normalized vectors
    for exact cosine similarity search.

    Features:
    - Exact search (no approximation) for accuracy
    - L2 normalization for cosine similarity
    - Persistent storage via faiss.write_index
    - Symbol ID mapping via pickle

    Args:
        index_path: Path to directory containing vector files
        dimension: Vector dimension (default: 384 for all-MiniLM-L6-v2)

    Files created:
        - vectors.faiss: FAISS index file
        - vector_id_map.pkl: {symbol_id -> faiss_id} mapping
    """

    def __init__(self, index_path: Path, dimension: int = 384):
        """
        Initialize FAISS store with lazy loading.

        Args:
            index_path: Directory path for vector storage
            dimension: Embedding dimension (default: 384)

        Raises:
            ImportError: If faiss-cpu or faiss-gpu not installed
        """
        if faiss is None:
            raise ImportError(
                "FAISS is not installed. Install with: pip install faiss-cpu (or faiss-gpu)"
            )

        self.index_path = Path(index_path)
        self.dimension = dimension
        self.faiss_path = self.index_path / "vectors.faiss"
        self.map_path = self.index_path / "vector_id_map.pkl"

        # Ensure directory exists
        self.index_path.mkdir(parents=True, exist_ok=True)

        # Load or create FAISS index
        if self.faiss_path.exists():
            try:
                self.index = faiss.read_index(str(self.faiss_path))
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors from {self.faiss_path}")
            except Exception as e:
                logger.warning(f"Failed to load FAISS index, creating new one: {e}")
                self.index = faiss.IndexFlatIP(dimension)
        else:
            # IndexFlatIP for cosine similarity (requires L2 normalized vectors)
            self.index = faiss.IndexFlatIP(dimension)
            logger.debug(f"Created new FAISS IndexFlatIP with dimension={dimension}")

        # Load or initialize ID mapping
        if self.map_path.exists():
            try:
                with open(self.map_path, 'rb') as f:
                    self.id_map: Dict[int, int] = pickle.load(f)
                logger.debug(f"Loaded ID map with {len(self.id_map)} entries")
            except Exception as e:
                logger.warning(f"Failed to load ID map, creating new one: {e}")
                self.id_map = {}
        else:
            self.id_map = {}

    def add_vector(self, symbol_id: int, vector: np.ndarray) -> int:
        """
        Add embedding vector to FAISS index.

        Normalizes vector for cosine similarity before adding.

        Args:
            symbol_id: SQLite symbol ID
            vector: Embedding vector (will be normalized)

        Returns:
            faiss_id: Index position in FAISS (sequential)
        """
        # Ensure vector is float32
        if vector.dtype != np.float32:
            vector = vector.astype(np.float32)

        # Normalize for cosine similarity (IndexFlatIP uses dot product)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        else:
            logger.warning(f"Zero-norm vector for symbol_id={symbol_id}, skipping normalization")

        # Reshape to (1, dimension) for FAISS
        vector = vector.reshape(1, -1)

        # Add to index
        faiss_id = self.index.ntotal  # Next available ID
        self.index.add(vector)

        # Update mapping
        self.id_map[symbol_id] = faiss_id

        logger.debug(f"Added vector for symbol_id={symbol_id} at faiss_id={faiss_id}")
        return faiss_id

    def add_vectors_batch(self, symbol_ids: List[int], vectors: np.ndarray) -> List[int]:
        """
        Batch add multiple vectors for efficiency.

        Args:
            symbol_ids: List of SQLite symbol IDs
            vectors: 2D array of shape (n, dimension)

        Returns:
            List of faiss_ids corresponding to each symbol_id
        """
        if len(symbol_ids) != len(vectors):
            raise ValueError(f"Mismatch: {len(symbol_ids)} symbol_ids vs {len(vectors)} vectors")

        # Ensure float32
        if vectors.dtype != np.float32:
            vectors = vectors.astype(np.float32)

        # Normalize all vectors
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        vectors = vectors / norms

        # Get starting FAISS ID
        start_faiss_id = self.index.ntotal

        # Batch add
        self.index.add(vectors)

        # Update mappings
        faiss_ids = list(range(start_faiss_id, start_faiss_id + len(symbol_ids)))
        for symbol_id, faiss_id in zip(symbol_ids, faiss_ids):
            self.id_map[symbol_id] = faiss_id

        logger.debug(f"Batch added {len(symbol_ids)} vectors (faiss_ids: {start_faiss_id} to {faiss_ids[-1]})")
        return faiss_ids

    def search(self, query_vector: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.

        Args:
            query_vector: Query embedding (will be normalized)
            k: Number of results to return

        Returns:
            Tuple of (scores, faiss_ids):
                - scores: Similarity scores (cosine similarity via dot product)
                - faiss_ids: FAISS index positions
        """
        if self.index.ntotal == 0:
            logger.warning("FAISS index is empty, returning empty results")
            return np.array([]), np.array([])

        # Ensure float32 and normalize
        if query_vector.dtype != np.float32:
            query_vector = query_vector.astype(np.float32)

        norm = np.linalg.norm(query_vector)
        if norm > 0:
            query_vector = query_vector / norm

        # Reshape to (1, dimension)
        query_vector = query_vector.reshape(1, -1)

        # Search (returns [batch_size, k] arrays)
        scores, faiss_ids = self.index.search(query_vector, min(k, self.index.ntotal))

        # Flatten from (1, k) to (k,)
        return scores[0], faiss_ids[0]

    def remove_vectors(self, faiss_ids: List[int]):
        """
        Remove vectors by FAISS IDs.

        IMPORTANT: FAISS doesn't support efficient deletion, so this
        requires rebuilding the entire index. Use sparingly.

        Args:
            faiss_ids: List of FAISS IDs to remove
        """
        if not faiss_ids:
            return

        faiss_ids_set = set(faiss_ids)

        # Extract remaining vectors
        remaining_vectors = []
        remaining_symbol_ids = []

        for symbol_id, fid in self.id_map.items():
            if fid not in faiss_ids_set:
                try:
                    # Reconstruct vector from FAISS index
                    vec = self.index.reconstruct(int(fid))
                    remaining_vectors.append(vec)
                    remaining_symbol_ids.append(symbol_id)
                except Exception as e:
                    logger.warning(f"Failed to reconstruct vector for faiss_id={fid}: {e}")

        # Rebuild index
        logger.info(f"Rebuilding FAISS index: removing {len(faiss_ids)} vectors, keeping {len(remaining_vectors)}")
        self.index.reset()

        if remaining_vectors:
            vectors_array = np.vstack(remaining_vectors)
            self.index.add(vectors_array)

        # Rebuild ID map with new sequential FAISS IDs
        self.id_map = {sid: i for i, sid in enumerate(remaining_symbol_ids)}

    def get_symbol_id(self, faiss_id: int) -> int:
        """
        Get symbol ID from FAISS ID.

        Args:
            faiss_id: FAISS index position

        Returns:
            symbol_id (SQLite primary key)

        Raises:
            KeyError: If faiss_id not found
        """
        # Reverse lookup (inefficient, but needed for search results)
        for symbol_id, fid in self.id_map.items():
            if fid == faiss_id:
                return symbol_id
        raise KeyError(f"FAISS ID {faiss_id} not found in ID map")

    def save(self):
        """
        Persist FAISS index and ID map to disk.
        """
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.faiss_path))
            logger.debug(f"Saved FAISS index ({self.index.ntotal} vectors) to {self.faiss_path}")

            # Save ID map
            with open(self.map_path, 'wb') as f:
                pickle.dump(self.id_map, f)
            logger.debug(f"Saved ID map ({len(self.id_map)} entries) to {self.map_path}")

        except Exception as e:
            logger.error(f"Failed to save FAISS store: {e}")
            raise

    def get_stats(self) -> Dict[str, any]:
        """
        Get vector store statistics.

        Returns:
            Dict with counts and sizes
        """
        stats = {
            'total_vectors': self.index.ntotal,
            'dimension': self.dimension,
            'index_type': 'IndexFlatIP',
            'faiss_size_bytes': self.faiss_path.stat().st_size if self.faiss_path.exists() else 0,
            'id_map_size_bytes': self.map_path.stat().st_size if self.map_path.exists() else 0,
        }
        return stats

    def clear(self):
        """
        Clear all vectors from index (for testing).
        """
        self.index.reset()
        self.id_map = {}
        logger.info("Cleared FAISS index and ID map")

    def __len__(self) -> int:
        """Return number of vectors in index."""
        return self.index.ntotal

    def __contains__(self, symbol_id: int) -> bool:
        """Check if symbol_id has an embedding."""
        return symbol_id in self.id_map
