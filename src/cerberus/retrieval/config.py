"""
Configuration for hybrid retrieval.

Phase 3 Dogfooding Test: Modified for incremental update validation.
"""

HYBRID_SEARCH_CONFIG = {
    "default_mode": "auto",  # "keyword", "semantic", "balanced", "auto"
    "keyword_weight": 0.5,  # For balanced mode (0.0-1.0)
    "semantic_weight": 0.5,  # For balanced mode (0.0-1.0)
    "top_k_per_method": 20,  # Retrieve top K from each method before fusion
    "final_top_k": 10,  # Return top K after fusion
    "min_score_threshold": 0.1,  # Minimum score to include in results
}

BM25_CONFIG = {
    "k1": 1.5,  # Term frequency saturation parameter
    "b": 0.75,  # Length normalization parameter
    "min_doc_freq": 1,  # Minimum document frequency for a term
    "max_doc_freq_ratio": 0.9,  # Ignore terms appearing in >90% of documents (stop words)
}

VECTOR_CONFIG = {
    "model": "all-MiniLM-L6-v2",  # Default embedding model
    "batch_size": 32,
    "normalize_embeddings": True,
    "cache_embeddings": True,
    "min_similarity": 0.2,  # Minimum cosine similarity
}

# Query type detection heuristics
QUERY_DETECTION = {
    "exact_match_indicators": [
        r"^[A-Z][a-z]+[A-Z]",  # CamelCase (e.g., "MyClass")
        r"^[a-z]+_[a-z]+",  # snake_case (e.g., "my_function")
        r"^[A-Z_]+$",  # SCREAMING_SNAKE_CASE (e.g., "MY_CONSTANT")
    ],
    "semantic_indicators": [
        r"\b(how|what|where|when|why|find|search|get|code|logic|implementation)\b",
        r"\s{3,}",  # Multiple words (natural language)
    ],
    "short_query_threshold": 3,  # Queries with ≤3 words are likely keyword searches
}
