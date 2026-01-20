"""
Hybrid ranking fusion (BM25 + Vector).

Uses Reciprocal Rank Fusion (RRF) to combine rankings from multiple methods.
"""

import re
from typing import List, Dict, Literal
from loguru import logger

from ..schemas import SearchResult, HybridSearchResult, CodeSymbol
from .config import HYBRID_SEARCH_CONFIG, QUERY_DETECTION


def detect_query_type(query: str) -> Literal["keyword", "semantic"]:
    """
    Detect whether a query is keyword-based or semantic.

    Args:
        query: Search query

    Returns:
        "keyword" or "semantic"
    """
    # Check for exact match indicators (CamelCase, snake_case, etc.)
    for pattern in QUERY_DETECTION["exact_match_indicators"]:
        if re.search(pattern, query):
            logger.debug(f"Query '{query}' detected as keyword (exact match pattern)")
            return "keyword"

    # Check for semantic indicators (natural language words)
    for pattern in QUERY_DETECTION["semantic_indicators"]:
        if re.search(pattern, query, re.IGNORECASE):
            logger.debug(f"Query '{query}' detected as semantic (natural language)")
            return "semantic"

    # Check query length
    word_count = len(query.split())
    if word_count <= QUERY_DETECTION["short_query_threshold"]:
        logger.debug(f"Query '{query}' detected as keyword (short query: {word_count} words)")
        return "keyword"

    # Default to semantic for longer queries
    logger.debug(f"Query '{query}' detected as semantic (default for {word_count} words)")
    return "semantic"


def reciprocal_rank_fusion(
    bm25_results: List[SearchResult],
    vector_results: List[SearchResult],
    k: int = 60,
) -> List[HybridSearchResult]:
    """
    Combine rankings using Reciprocal Rank Fusion (RRF).

    RRF score for a document = sum over all rankings of: 1 / (k + rank)

    Args:
        bm25_results: Results from BM25 search
        vector_results: Results from vector search
        k: Constant for RRF (default 60, standard value)

    Returns:
        List of HybridSearchResult sorted by fused score
    """
    # Build RRF scores with deduplication across both sources
    rrf_scores: Dict[str, Dict] = {}  # symbol_id -> {symbol, bm25_score, vector_score, rrf_score, ranks}

    # Helper to create unique symbol ID (file+name+line is stable across sources)
    def symbol_id(symbol: CodeSymbol) -> str:
        return f"{symbol.file_path}:{symbol.name}:{symbol.start_line}"

    # Process BM25 results
    for rank, result in enumerate(bm25_results, start=1):
        sid = symbol_id(result.symbol)
        if sid not in rrf_scores:
            rrf_scores[sid] = {
                "symbol": result.symbol,
                "snippet": result.snippet,
                "bm25_score": result.score,
                "vector_score": 0.0,
                "bm25_rank": rank,
                "vector_rank": None,
            }
        else:
            rrf_scores[sid]["bm25_score"] = result.score
            rrf_scores[sid]["bm25_rank"] = rank

    # Process vector results
    for rank, result in enumerate(vector_results, start=1):
        sid = symbol_id(result.symbol)
        if sid not in rrf_scores:
            rrf_scores[sid] = {
                "symbol": result.symbol,
                "snippet": result.snippet,
                "bm25_score": 0.0,
                "vector_score": result.score,
                "bm25_rank": None,
                "vector_rank": rank,
            }
        else:
            rrf_scores[sid]["vector_score"] = result.score
            rrf_scores[sid]["vector_rank"] = rank

    # Compute RRF scores
    for sid, data in rrf_scores.items():
        rrf_score = 0.0

        if data["bm25_rank"] is not None:
            rrf_score += 1.0 / (k + data["bm25_rank"])

        if data["vector_rank"] is not None:
            rrf_score += 1.0 / (k + data["vector_rank"])

        data["rrf_score"] = rrf_score

    # Sort by RRF score
    sorted_results = sorted(
        rrf_scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True
    )

    # Create HybridSearchResult objects
    hybrid_results: List[HybridSearchResult] = []
    for rank, data in enumerate(sorted_results, start=1):
        # Determine match type
        if data["bm25_rank"] and data["vector_rank"]:
            match_type = "both"
        elif data["bm25_rank"]:
            match_type = "keyword"
        else:
            match_type = "semantic"

        result = HybridSearchResult(
            symbol=data["symbol"],
            bm25_score=data["bm25_score"],
            vector_score=data["vector_score"],
            hybrid_score=data["rrf_score"],
            rank=rank,
            match_type=match_type,
        )
        hybrid_results.append(result)

    logger.info(f"RRF fusion combined {len(bm25_results)} BM25 + {len(vector_results)} vector = {len(hybrid_results)} results")

    return hybrid_results


def weighted_score_fusion(
    bm25_results: List[SearchResult],
    vector_results: List[SearchResult],
    keyword_weight: float = 0.5,
    semantic_weight: float = 0.5,
) -> List[HybridSearchResult]:
    """
    Combine rankings using weighted score fusion.

    Hybrid score = keyword_weight * bm25_score + semantic_weight * vector_score

    Args:
        bm25_results: Results from BM25 search
        vector_results: Results from vector search
        keyword_weight: Weight for BM25 score (0-1)
        semantic_weight: Weight for vector score (0-1)

    Returns:
        List of HybridSearchResult sorted by hybrid score
    """
    # Build score map
    scores: Dict[str, Dict] = {}

    # Helper to create unique symbol ID
    def symbol_id(symbol: CodeSymbol) -> str:
        return f"{symbol.file_path}:{symbol.name}:{symbol.start_line}"

    # Process BM25 results
    for result in bm25_results:
        sid = symbol_id(result.symbol)
        scores[sid] = {
            "symbol": result.symbol,
            "snippet": result.snippet,
            "bm25_score": result.score,
            "vector_score": 0.0,
        }

    # Process vector results
    for result in vector_results:
        sid = symbol_id(result.symbol)
        if sid in scores:
            scores[sid]["vector_score"] = result.score
        else:
            scores[sid] = {
                "symbol": result.symbol,
                "snippet": result.snippet,
                "bm25_score": 0.0,
                "vector_score": result.score,
            }

    # Compute weighted scores
    for sid, data in scores.items():
        hybrid_score = (
            keyword_weight * data["bm25_score"] +
            semantic_weight * data["vector_score"]
        )
        data["hybrid_score"] = hybrid_score

    # Sort by hybrid score
    sorted_results = sorted(
        scores.values(),
        key=lambda x: x["hybrid_score"],
        reverse=True
    )

    # Create HybridSearchResult objects
    hybrid_results: List[HybridSearchResult] = []
    for rank, data in enumerate(sorted_results, start=1):
        # Determine match type
        if data["bm25_score"] > 0 and data["vector_score"] > 0:
            match_type = "both"
        elif data["bm25_score"] > 0:
            match_type = "keyword"
        else:
            match_type = "semantic"

        result = HybridSearchResult(
            symbol=data["symbol"],
            bm25_score=data["bm25_score"],
            vector_score=data["vector_score"],
            hybrid_score=data["hybrid_score"],
            rank=rank,
            match_type=match_type,
        )
        hybrid_results.append(result)

    logger.info(f"Weighted fusion: {len(hybrid_results)} results (weights: {keyword_weight}/{semantic_weight})")

    return hybrid_results
