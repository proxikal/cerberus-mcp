"""
Vector semantic search (refactored from semantic/search.py).

Optimized for Phase 4: Direct FAISS queries for streaming SQLite indices.
"""

from pathlib import Path
from typing import List, Dict
import numpy as np
from loguru import logger

from ..schemas import CodeSymbol, SearchResult, CodeSnippet, ScanResult
from ..semantic.embeddings import embed_texts
from ..semantic.vector_store import InMemoryVectorStore, VectorDocument, build_faiss_store
from ..storage import SQLiteIndexStore, FAISSVectorStore
from .utils import read_range
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


def vector_search_faiss(
    query: str,
    sqlite_store: SQLiteIndexStore,
    faiss_store: FAISSVectorStore,
    top_k: int = 10,
    model_name: str = None,
    padding: int = 3,
) -> List[SearchResult]:
    """
    Perform vector semantic search using FAISS directly (Phase 4 streaming).

    This function queries FAISS index directly and then fetches matching symbols
    from SQLite, achieving constant memory usage regardless of index size.

    Args:
        query: Search query
        sqlite_store: SQLite index store
        faiss_store: FAISS vector store
        top_k: Number of top results
        model_name: Embedding model name (default from config)
        padding: Snippet padding for file content

    Returns:
        List of SearchResult objects
    """
    if model_name is None:
        model_name = VECTOR_CONFIG["model"]

    try:
        # Embed query
        logger.debug(f"Embedding query: '{query}'")
        query_vec = embed_texts([query], model_name=model_name)[0]

        # Query FAISS directly
        logger.debug(f"Querying FAISS index ({len(faiss_store)} vectors)")
        scores, faiss_ids = faiss_store.search(query_vec, k=top_k)

        if len(faiss_ids) == 0:
            logger.info("No FAISS results found")
            return []

        logger.debug(f"FAISS returned {len(faiss_ids)} candidates")

        # Get symbol IDs from FAISS IDs
        symbol_ids = [faiss_store.get_symbol_id(fid) for fid in faiss_ids]

        # Fetch symbols from SQLite by querying for each symbol ID
        # (SQLite doesn't have a direct "get by ID" query, so we need to match by symbol metadata)
        results: List[SearchResult] = []

        # Query embedding metadata to get symbol names and file paths
        conn = sqlite_store._get_connection()
        try:
            for faiss_id, score, symbol_id in zip(faiss_ids, scores, symbol_ids):
                # Get symbol info from embeddings_metadata
                cursor = conn.execute("""
                    SELECT s.*, em.name, em.file_path
                    FROM embeddings_metadata em
                    JOIN symbols s ON s.id = em.symbol_id
                    WHERE em.symbol_id = ?
                """, (symbol_id,))

                row = cursor.fetchone()
                if not row:
                    logger.warning(f"Symbol {symbol_id} not found in SQLite (orphaned FAISS entry)")
                    continue

                # Build CodeSymbol
                symbol = CodeSymbol(
                    name=row['name'],
                    type=row['type'],
                    file_path=row['file_path'],
                    start_line=row['start_line'],
                    end_line=row['end_line'],
                    signature=row['signature'],
                    return_type=row['return_type'],
                    parameters=__import__('json').loads(row['parameters']) if row['parameters'] else None,
                    parent_class=row['parent_class'],
                )

                # Load snippet (lazy loading - only for results that passed FAISS filter)
                try:
                    snippet_obj = read_range(
                        Path(symbol.file_path),
                        symbol.start_line,
                        symbol.end_line,
                        padding=padding,
                    )
                except Exception as e:
                    logger.warning(f"Failed to load snippet for {symbol.name}: {e}")
                    continue

                # Create SearchResult
                result = SearchResult(
                    symbol=symbol,
                    score=float(score),  # FAISS cosine similarity (0-1)
                    snippet=snippet_obj,
                )
                results.append(result)

        finally:
            conn.close()

        # Filter by minimum similarity
        min_sim = VECTOR_CONFIG["min_similarity"]
        results = [r for r in results if r.score >= min_sim]

        logger.info(f"Vector search (FAISS) for '{query}' returned {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"FAISS vector search failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return []
