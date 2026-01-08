from dataclasses import dataclass
from typing import List

import numpy as np

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol, SearchResult, CodeSnippet


@dataclass
class VectorDocument:
    embedding: np.ndarray
    symbol: CodeSymbol
    snippet: CodeSnippet


class InMemoryVectorStore:
    """
    Minimal in-memory vector store for embeddings.
    """

    def __init__(self, documents: List[VectorDocument]):
        self.documents = documents
        if documents:
            self.matrix = np.stack([doc.embedding for doc in documents])
        else:
            self.matrix = np.empty((0, 0))

    def search(self, query_embedding: np.ndarray, limit: int = 5) -> List[SearchResult]:
        if self.matrix.size == 0:
            logger.info("Vector store is empty.")
            return []

        # cosine similarity since embeddings are normalized
        scores = self.matrix @ query_embedding
        top_indices = scores.argsort()[-limit:][::-1]
        results: List[SearchResult] = []
        for idx in top_indices:
            score = float(scores[idx])
            doc = self.documents[int(idx)]
            results.append(
                SearchResult(symbol=doc.symbol, score=score, snippet=doc.snippet)
            )
        return results


def build_faiss_store(documents: List[VectorDocument], query_embedding: np.ndarray, limit: int) -> List[SearchResult]:
    """
    Optionally build a FAISS-backed search. Returns results or [] on failure to keep flow safe.
    """
    try:
        import faiss  # type: ignore
    except ImportError:
        logger.warning("FAISS not installed; falling back to in-memory search.")
        return []

    if not documents:
        return []

    dim = documents[0].embedding.shape[0]
    index = faiss.IndexFlatIP(dim)
    matrix = np.stack([doc.embedding.astype("float32") for doc in documents])
    index.add(matrix)

    q = query_embedding.astype("float32").reshape(1, -1)
    scores, idxs = index.search(q, limit)
    results: List[SearchResult] = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx == -1:
            continue
        doc = documents[int(idx)]
        results.append(
            SearchResult(symbol=doc.symbol, score=float(score), snippet=doc.snippet)
        )
    return results
