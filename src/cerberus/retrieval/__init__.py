"""
Retrieval module for hybrid search (BM25 + Vector).

Public API for searching code symbols with keyword and semantic search.
"""

from .facade import hybrid_search, find_symbol, read_range

__all__ = [
    "hybrid_search",
    "find_symbol",
    "read_range",
]
