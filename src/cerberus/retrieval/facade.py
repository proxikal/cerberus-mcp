"""
Public API for hybrid retrieval.

Facade for BM25 keyword search, vector semantic search, and hybrid fusion.

Optimized for Phase 4 Aegis-Scale with streaming support for SQLite indices.
"""

from pathlib import Path
from typing import List, Literal, Optional, Union
from loguru import logger

from ..schemas import ScanResult, SearchResult, HybridSearchResult, CodeSymbol, CodeSnippet
from ..index.index_loader import load_index
from ..storage import ScanResultAdapter, SQLiteIndexStore, FAISSVectorStore
from .bm25_search import BM25Index
from .vector_search import vector_search, vector_search_faiss
from .hybrid_ranker import (
    detect_query_type,
    reciprocal_rank_fusion,
    weighted_score_fusion,
)
from .utils import find_symbol, read_range
from .config import HYBRID_SEARCH_CONFIG, BM25_CONFIG, VECTOR_CONFIG


# Re-export utilities for backward compatibility
__all__ = ["hybrid_search", "find_symbol", "read_range"]


def hybrid_search(
    query: str,
    index_path: Path,
    mode: Literal["keyword", "semantic", "balanced", "auto"] = "auto",
    top_k: int = None,
    keyword_weight: float = None,
    semantic_weight: float = None,
    fusion_method: Literal["rrf", "weighted"] = "rrf",
    padding: int = 3,
) -> List[HybridSearchResult]:
    """
    Perform hybrid search combining BM25 keyword and vector semantic search.

    Optimized for Phase 4: Uses streaming queries for SQLite indices to maintain
    constant memory usage regardless of project size.

    Args:
        query: Search query
        index_path: Path to index file
        mode: Search mode ("keyword", "semantic", "balanced", "auto")
        top_k: Number of results to return (default from config)
        keyword_weight: Weight for keyword scores (for weighted fusion)
        semantic_weight: Weight for semantic scores (for weighted fusion)
        fusion_method: "rrf" (Reciprocal Rank Fusion) or "weighted"
        padding: Context padding for snippets

    Returns:
        List of HybridSearchResult sorted by relevance
    """
    # Load config defaults
    if top_k is None:
        top_k = HYBRID_SEARCH_CONFIG["final_top_k"]

    if keyword_weight is None:
        keyword_weight = HYBRID_SEARCH_CONFIG["keyword_weight"]

    if semantic_weight is None:
        semantic_weight = HYBRID_SEARCH_CONFIG["semantic_weight"]

    # Auto-detect mode if needed
    if mode == "auto":
        mode = "balanced"  # Default to balanced
        detected_type = detect_query_type(query)
        if detected_type == "keyword":
            logger.info(f"Auto-detected keyword query: '{query}'")
            keyword_weight = 0.7
            semantic_weight = 0.3
        else:
            logger.info(f"Auto-detected semantic query: '{query}'")
            keyword_weight = 0.3
            semantic_weight = 0.7

    # Load index
    scan_result = load_index(index_path)

    # Detect if SQLite index and use optimized streaming path
    is_sqlite = isinstance(scan_result, ScanResultAdapter)

    if is_sqlite:
        logger.info("Using streaming SQLite optimized search path")
        return _hybrid_search_streaming(
            query=query,
            scan_result=scan_result,
            mode=mode,
            top_k=top_k,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight,
            fusion_method=fusion_method,
            padding=padding,
        )
    else:
        logger.info("Using legacy in-memory search path (Legacy memory-load index)")
        return _hybrid_search_legacy(
            query=query,
            scan_result=scan_result,
            mode=mode,
            top_k=top_k,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight,
            fusion_method=fusion_method,
            padding=padding,
        )


def _hybrid_search_streaming(
    query: str,
    scan_result: ScanResultAdapter,
    mode: str,
    top_k: int,
    keyword_weight: float,
    semantic_weight: float,
    fusion_method: str,
    padding: int,
) -> List[HybridSearchResult]:
    """
    Streaming search for SQLite indices (constant memory).

    Key optimization: Defer snippet loading until after we identify top candidates.
    """
    store = scan_result._store
    top_k_per_method = HYBRID_SEARCH_CONFIG["top_k_per_method"]

    bm25_results: List[SearchResult] = []
    vector_results: List[SearchResult] = []

    # Phase 7: FTS5 keyword search (zero RAM overhead - SQLite C-engine handles BM25)
    if mode in ["keyword", "balanced"]:
        logger.info(f"Performing FTS5 keyword search for '{query}'")

        # Use SQLite FTS5 for zero-memory keyword search
        # No need to load symbols into memory - SQLite handles everything
        fts5_results = []
        for symbol, score in store.fts5_search(query, top_k=top_k_per_method):
            snippet = CodeSnippet(
                file_path=symbol.file_path,
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                content="",  # Loaded lazily later
            )
            fts5_results.append(SearchResult(
                symbol=symbol,
                score=score,
                snippet=snippet,
            ))

        bm25_results = fts5_results
        logger.debug(f"FTS5 search returned {len(bm25_results)} results")

    # Vector semantic search (query FAISS directly)
    has_embeddings = False
    if mode in ["semantic", "balanced"]:
        logger.info(f"Performing streaming vector search for '{query}'")

        # Check if FAISS store is available
        if store._faiss_store and len(store._faiss_store) > 0:
            logger.debug("Using FAISS direct query (streaming)")
            has_embeddings = True
            vector_results = vector_search_faiss(
                query=query,
                sqlite_store=store,
                faiss_store=store._faiss_store,
                top_k=top_k_per_method,
                model_name=VECTOR_CONFIG["model"],
                padding=padding,
            )
        else:
            logger.warning("No FAISS store available, falling back to keyword search")

    # Handle single-method modes
    if mode == "keyword":
        # Load snippets for top results only
        return _finalize_results(bm25_results[:top_k], "keyword", padding)

    if mode == "semantic":
        # FALLBACK: If no embeddings, use keyword search instead
        if not has_embeddings or not vector_results:
            logger.warning("Semantic search requested but no embeddings available - falling back to keyword search")
            if not bm25_results:
                # Need to run keyword search since it wasn't done
                logger.info(f"Performing FTS5 keyword search for fallback")
                fts5_results = []
                for symbol, score in store.fts5_search(query, top_k=top_k_per_method):
                    snippet = CodeSnippet(
                        file_path=symbol.file_path,
                        start_line=symbol.start_line,
                        end_line=symbol.end_line,
                        content="",  # Loaded lazily later
                    )
                    fts5_results.append(SearchResult(
                        symbol=symbol,
                        score=score,
                        snippet=snippet,
                    ))
                bm25_results = fts5_results
            return _finalize_results(bm25_results[:top_k], "keyword_fallback", padding)

        return _finalize_results(vector_results[:top_k], "semantic", padding)

    # Balanced mode - fuse results
    # FALLBACK: If no embeddings, use keyword search only
    if not has_embeddings or not vector_results:
        logger.warning("Balanced mode requested but no embeddings available - falling back to keyword search")
        return _finalize_results(bm25_results[:top_k], "keyword_fallback", padding)

    logger.info(f"Fusing results using {fusion_method} method")

    if fusion_method == "rrf":
        hybrid_results = reciprocal_rank_fusion(bm25_results, vector_results)
    else:
        hybrid_results = weighted_score_fusion(
            bm25_results,
            vector_results,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight,
        )

    # Load full snippets for final top-K results only (lazy loading optimization)
    final_results = hybrid_results[:top_k]
    for result in final_results:
        # Load actual file snippet if not already loaded
        if not hasattr(result, 'snippet') or not result.snippet:
            snippet_obj = read_range(
                Path(result.symbol.file_path),
                result.symbol.start_line,
                result.symbol.end_line,
                padding=padding,
            )
            # Note: HybridSearchResult doesn't have snippet field, but we ensure SearchResults do

    return final_results


def _hybrid_search_legacy(
    query: str,
    scan_result: ScanResult,
    mode: str,
    top_k: int,
    keyword_weight: float,
    semantic_weight: float,
    fusion_method: str,
    padding: int,
) -> List[HybridSearchResult]:
    """
    Legacy search for JSON indices (full memory load).

    Maintains backward compatibility with existing code.
    """
    # Build document snippets (legacy full-load approach)
    snippets = []
    for symbol in scan_result.symbols:
        snippet_obj = read_range(
            Path(symbol.file_path),
            symbol.start_line,
            symbol.end_line,
            padding=padding,
        )
        snippets.append({
            "symbol": symbol,
            "snippet_text": snippet_obj.content,
        })

    logger.info(f"Built {len(snippets)} document snippets for search")

    # Perform searches based on mode
    bm25_results: List[SearchResult] = []
    vector_results: List[SearchResult] = []

    top_k_per_method = HYBRID_SEARCH_CONFIG["top_k_per_method"]

    if mode in ["keyword", "balanced"]:
        logger.info(f"Performing BM25 keyword search for '{query}'")
        bm25_index = BM25Index(
            documents=snippets,
            k1=BM25_CONFIG["k1"],
            b=BM25_CONFIG["b"],
        )
        bm25_results = bm25_index.search(query, top_k=top_k_per_method)

    has_embeddings = False
    if mode in ["semantic", "balanced"]:
        logger.info(f"Performing vector semantic search for '{query}'")
        # Check if embeddings are available
        if scan_result.embeddings:
            has_embeddings = True
            vector_results = vector_search(
                query=query,
                scan_result=scan_result,
                snippets=snippets,
                top_k=top_k_per_method,
                model_name=VECTOR_CONFIG["model"],
            )
        else:
            logger.warning("No embeddings available in legacy index, skipping vector search")

    # Handle single-method modes
    if mode == "keyword":
        # Convert BM25 results to HybridSearchResult
        return [
            HybridSearchResult(
                symbol=r.symbol,
                bm25_score=r.score,
                vector_score=0.0,
                hybrid_score=r.score,
                rank=idx + 1,
                match_type="keyword",
            )
            for idx, r in enumerate(bm25_results[:top_k])
        ]

    if mode == "semantic":
        # FALLBACK: If no embeddings, use keyword search instead
        if not has_embeddings or not vector_results:
            logger.warning("Semantic search requested but no embeddings available - falling back to keyword search")
            if not bm25_results:
                # Need to run keyword search since it wasn't done
                logger.info(f"Performing BM25 keyword search for fallback")
                bm25_index = BM25Index(
                    documents=snippets,
                    k1=BM25_CONFIG["k1"],
                    b=BM25_CONFIG["b"],
                )
                bm25_results = bm25_index.search(query, top_k=top_k_per_method)

            return [
                HybridSearchResult(
                    symbol=r.symbol,
                    bm25_score=r.score,
                    vector_score=0.0,
                    hybrid_score=r.score,
                    rank=idx + 1,
                    match_type="keyword_fallback",
                )
                for idx, r in enumerate(bm25_results[:top_k])
            ]

        # Convert vector results to HybridSearchResult
        return [
            HybridSearchResult(
                symbol=r.symbol,
                bm25_score=0.0,
                vector_score=r.score,
                hybrid_score=r.score,
                rank=idx + 1,
                match_type="semantic",
            )
            for idx, r in enumerate(vector_results[:top_k])
        ]

    # Balanced mode - fuse results
    # FALLBACK: If no embeddings, use keyword search only
    if not has_embeddings or not vector_results:
        logger.warning("Balanced mode requested but no embeddings available - falling back to keyword search")
        return [
            HybridSearchResult(
                symbol=r.symbol,
                bm25_score=r.score,
                vector_score=0.0,
                hybrid_score=r.score,
                rank=idx + 1,
                match_type="keyword_fallback",
            )
            for idx, r in enumerate(bm25_results[:top_k])
        ]

    # Balanced mode - fuse results
    logger.info(f"Fusing results using {fusion_method} method")

    if fusion_method == "rrf":
        hybrid_results = reciprocal_rank_fusion(bm25_results, vector_results)
    else:
        hybrid_results = weighted_score_fusion(
            bm25_results,
            vector_results,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight,
        )

    # Return top K
    return hybrid_results[:top_k]


def _finalize_results(
    results: List[SearchResult],
    match_type: str,
    padding: int,
) -> List[HybridSearchResult]:
    """
    Convert SearchResults to HybridSearchResults with proper scoring.

    Args:
        results: List of SearchResult objects
        match_type: "keyword" or "semantic"
        padding: Snippet padding

    Returns:
        List of HybridSearchResult objects
    """
    hybrid_results = []
    seen = set()
    for idx, r in enumerate(results):
        key = (r.symbol.file_path, r.symbol.name, r.symbol.start_line, r.symbol.end_line, r.symbol.type)
        if key in seen:
            continue
        seen.add(key)
        # Ensure snippet is loaded
        if not r.snippet or not r.snippet.content:
            snippet_obj = read_range(
                Path(r.symbol.file_path),
                r.symbol.start_line,
                r.symbol.end_line,
                padding=padding,
            )
            r.snippet.content = snippet_obj.content

        # Handle keyword and keyword_fallback modes (both use BM25 scores)
        if match_type in ["keyword", "keyword_fallback"]:
            hybrid_result = HybridSearchResult(
                symbol=r.symbol,
                bm25_score=r.score,
                vector_score=0.0,
                hybrid_score=r.score,
                rank=idx + 1,
                match_type=match_type,  # Preserve the actual match_type
            )
        else:
            # Semantic mode (uses vector scores)
            hybrid_result = HybridSearchResult(
                symbol=r.symbol,
                bm25_score=0.0,
                vector_score=r.score,
                hybrid_score=r.score,
                rank=idx + 1,
                match_type="semantic",
            )
        hybrid_results.append(hybrid_result)

    return hybrid_results
