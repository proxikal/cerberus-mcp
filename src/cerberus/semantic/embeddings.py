from functools import lru_cache
from typing import List, TYPE_CHECKING

import numpy as np

from cerberus.logging_config import logger

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_model(model_name: str = "all-MiniLM-L6-v2") -> "SentenceTransformer":
    """
    Phase 7: Lazy load embedding model (400MB+) only when semantic search is used.

    The model is loaded on first call and cached. For keyword-only searches,
    this function is never called, keeping RAM usage < 50MB.

    Models are bundled locally in the models/ directory for faster loading.
    Falls back to HuggingFace download if local model is missing or corrupted.

    Args:
        model_name: HuggingFace model identifier

    Returns:
        Loaded SentenceTransformer model
    """
    # Lazy import to avoid loading torch for commands that don't need semantic search
    from sentence_transformers import SentenceTransformer
    from pathlib import Path

    # Check for bundled local model first
    # Go up from src/cerberus/semantic/embeddings.py to project root
    local_model_path = Path(__file__).parent.parent.parent.parent / "models" / model_name

    if local_model_path.exists() and (local_model_path / "config.json").exists():
        logger.info(
            f"Loading bundled embedding model '{model_name}' from {local_model_path}"
        )
        try:
            return SentenceTransformer(str(local_model_path))
        except Exception as e:
            logger.warning(
                f"Failed to load local model from {local_model_path}: {e}. "
                "Falling back to HuggingFace download."
            )

    # Fallback: Download from HuggingFace
    logger.warning(
        f"Loading 400MB+ embedding model '{model_name}' from HuggingFace into RAM. "
        "This only happens for semantic searches. Keyword searches remain < 50MB."
    )
    return SentenceTransformer(model_name)


def embed_texts(texts: List[str], model_name: str = "all-MiniLM-L6-v2") -> np.ndarray:
    """
    Generate embeddings for texts using cached model.

    Args:
        texts: List of text strings to embed
        model_name: Model identifier (default: all-MiniLM-L6-v2)

    Returns:
        Normalized embedding vectors as numpy array
    """
    model = get_model(model_name)
    return np.array(model.encode(texts, convert_to_numpy=True, normalize_embeddings=True))


def clear_model_cache():
    """
    Phase 7: Clear the embedding model from memory.

    Use this to free the 400MB+ model RAM after semantic searches are complete.
    The model will be reloaded on next semantic search.
    """
    get_model.cache_clear()
    logger.info("Cleared embedding model cache. Freed ~400MB RAM.")
