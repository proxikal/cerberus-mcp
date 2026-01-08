from functools import lru_cache
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from cerberus.logging_config import logger


@lru_cache(maxsize=1)
def get_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    logger.info(f"Loading embedding model '{model_name}'")
    return SentenceTransformer(model_name)


def embed_texts(texts: List[str], model_name: str = "all-MiniLM-L6-v2") -> np.ndarray:
    model = get_model(model_name)
    return np.array(model.encode(texts, convert_to_numpy=True, normalize_embeddings=True))
