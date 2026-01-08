import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np

from cerberus.logging_config import logger
from cerberus.index import load_index
from cerberus.retrieval import read_range
from cerberus.schemas import CodeSymbol, SearchResult
from cerberus.semantic.embeddings import embed_texts
from cerberus.semantic.vector_store import (
    InMemoryVectorStore,
    VectorDocument,
    build_faiss_store,
)

WORD_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass
class IndexedDocument:
    symbol: CodeSymbol
    snippet_text: str


def build_documents(index_path: Path, padding: int = 3) -> List[IndexedDocument]:
    scan_result = load_index(index_path)
    documents: List[IndexedDocument] = []
    for symbol in scan_result.symbols:
        snippet = read_range(Path(symbol.file_path), symbol.start_line, symbol.end_line, padding=padding)
        documents.append(IndexedDocument(symbol=symbol, snippet_text=snippet.content))
    logger.info(f"Built {len(documents)} documents from index '{index_path}'")
    return documents


def semantic_search(
    query: str,
    index_path: Path,
    limit: int = 5,
    padding: int = 3,
    use_embeddings: bool = True,
    model_name: str = "all-MiniLM-L6-v2",
    min_score: float = 0.2,
    backend: str = "memory",
) -> List[SearchResult]:
    """
    Perform semantic search. Defaults to transformer embeddings; falls back to regex token matching on errors.
    """
    documents = build_documents(index_path, padding=padding)
    if not documents:
        return []

    if use_embeddings:
        try:
            scan_result = load_index(index_path)
            if scan_result.embeddings:
                # Use precomputed embeddings
                vector_docs = []
                for embed_entry in scan_result.embeddings:
                    match = next((d for d in documents if d.symbol.name == embed_entry.name and d.symbol.file_path == embed_entry.file_path), None)
                    if not match:
                        continue
                    vector_docs.append(
                        VectorDocument(
                            embedding=np.array(embed_entry.vector, dtype=float),
                            symbol=match.symbol,
                            snippet=read_range(Path(match.symbol.file_path), match.symbol.start_line, match.symbol.end_line, padding=padding),
                        )
                    )
                query_vec = embed_texts([query], model_name=model_name)[0]
                if backend == "faiss":
                    results = build_faiss_store(vector_docs, query_vec, limit=limit)
                else:
                    store = InMemoryVectorStore(vector_docs)
                    results = store.search(query_vec, limit=limit)
            else:
                texts = [doc.snippet_text for doc in documents]
                embeddings = embed_texts(texts, model_name=model_name)
                query_vec = embed_texts([query], model_name=model_name)[0]
                vector_docs = [
                    VectorDocument(embedding=embeddings[i], symbol=doc.symbol, snippet=read_range(Path(doc.symbol.file_path), doc.symbol.start_line, doc.symbol.end_line, padding=padding))
                    for i, doc in enumerate(documents)
                ]
                if backend == "faiss":
                    results = build_faiss_store(vector_docs, query_vec, limit=limit)
                else:
                    store = InMemoryVectorStore(vector_docs)
                    results = store.search(query_vec, limit=limit)
            results = [r for r in results if r.score >= min_score]
            logger.info(f"Semantic search (embeddings) for '{query}' returned {len(results)} result(s)")
            return results
        except Exception as exc:
            logger.warning(f"Embedding search failed, falling back to regex similarity. Error: {exc}")

    # Fallback: simple token overlap scoring
    def tokenize(text: str) -> List[str]:
        return [m.group(0).lower() for m in WORD_RE.finditer(text)]

    query_tokens = set(tokenize(query))
    if not query_tokens:
        logger.info("Query is empty after tokenization; returning no results.")
        return []
    scored: List[Tuple[float, SearchResult]] = []
    for doc in documents:
        snippet = read_range(Path(doc.symbol.file_path), doc.symbol.start_line, doc.symbol.end_line, padding=padding)
        tokens = set(tokenize(snippet.content))
        if not tokens:
            continue
        score = len(query_tokens & tokens) / len(tokens)
        scored.append((score, SearchResult(symbol=doc.symbol, score=score, snippet=snippet)))

    ranked = sorted(scored, key=lambda r: r[0], reverse=True)
    top = [r[1] for r in ranked if r[0] >= min_score][:limit]
    logger.info(f"Semantic search (fallback) for '{query}' returned {len(top)} result(s)")
    return top
