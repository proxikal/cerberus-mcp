"""
Public API for hybrid retrieval.

Facade for BM25 keyword search, vector semantic search, and hybrid fusion.
"""

from pathlib import Path
from typing import List, Literal, Optional
from loguru import logger

from ..schemas import ScanResult, SearchResult, HybridSearchResult, CodeSymbol
from ..index.index_loader import load_index
from .bm25_search import BM25Index
from .vector_search import vector_search
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

    # Build document snippets
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

    if mode in ["semantic", "balanced"]:
        logger.info(f"Performing vector semantic search for '{query}'")
        vector_results = vector_search(
            query=query,
            scan_result=scan_result,
            snippets=snippets,
            top_k=top_k_per_method,
            model_name=VECTOR_CONFIG["model"],
        )

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
