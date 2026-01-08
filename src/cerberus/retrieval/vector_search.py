"""
Vector semantic search (refactored from semantic/search.py).
"""

from pathlib import Path
from typing import List
import numpy as np
from loguru import logger

from ..schemas import CodeSymbol, SearchResult, CodeSnippet, ScanResult
from ..semantic.embeddings import embed_texts
from ..semantic.vector_store import InMemoryVectorStore, VectorDocument, build_faiss_store
from .config import VECTOR_CONFIG


def vector_search(
    query: str,
    scan_result: ScanResult,
    snippets: List[Dict],  # List of {symbol, snippet_text}
    top_k: int = 10,
    model_name: str = None,
    backend: str = "memory",
) -> List[SearchResult]:
    """
    Perform vector semantic search.

    Args:
        query: Search query
        scan_result: Scan result with symbols
        snippets: List of document snippets
        top_k: Number of top results
        model_name: Embedding model name (default from config)
        backend: "memory" or "faiss"

    Returns:
        List of SearchResult objects
    """
    if model_name is None:
        model_name = VECTOR_CONFIG["model"]

    if not snippets:
        return []

    try:
        # Check if we have precomputed embeddings in the index
        if scan_result.embeddings:
            logger.debug(f"Using {len(scan_result.embeddings)} precomputed embeddings")

            # Build vector documents from precomputed embeddings
            vector_docs = []
            for embed_entry in scan_result.embeddings:
                # Find matching symbol
                symbol = next(
                    (s for s in scan_result.symbols
                     if s.name == embed_entry.name and s.file_path == embed_entry.file_path),
                    None
                )

                if not symbol:
                    continue

                # Find snippet text
                snippet_doc = next(
                    (d for d in snippets
                     if d["symbol"].name == symbol.name and d["symbol"].file_path == symbol.file_path),
                    None
                )

                if not snippet_doc:
                    continue

                # Create code snippet
                snippet = CodeSnippet(
                    file_path=symbol.file_path,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    content=snippet_doc["snippet_text"],
                )

                vector_docs.append(
                    VectorDocument(
                        embedding=np.array(embed_entry.vector, dtype=float),
                        symbol=symbol,
                        snippet=snippet,
                    )
                )

            # Embed query
            query_vec = embed_texts([query], model_name=model_name)[0]

            # Search
            if backend == "faiss":
                results = build_faiss_store(vector_docs, query_vec, limit=top_k)
            else:
                store = InMemoryVectorStore(vector_docs)
                results = store.search(query_vec, limit=top_k)

        else:
            # No precomputed embeddings - compute on the fly
            logger.debug("Computing embeddings on the fly")

            texts = [doc["snippet_text"] for doc in snippets]
            embeddings = embed_texts(texts, model_name=model_name)
            query_vec = embed_texts([query], model_name=model_name)[0]

            vector_docs = []
            for i, doc in enumerate(snippets):
                symbol = doc["symbol"]
                snippet = CodeSnippet(
                    file_path=symbol.file_path,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    content=doc["snippet_text"],
                )
                vector_docs.append(
                    VectorDocument(
                        embedding=embeddings[i],
                        symbol=symbol,
                        snippet=snippet,
                    )
                )

            # Search
            if backend == "faiss":
                results = build_faiss_store(vector_docs, query_vec, limit=top_k)
            else:
                store = InMemoryVectorStore(vector_docs)
                results = store.search(query_vec, limit=top_k)

        # Filter by minimum similarity
        min_sim = VECTOR_CONFIG["min_similarity"]
        results = [r for r in results if r.score >= min_sim]

        logger.info(f"Vector search for '{query}' returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return []
