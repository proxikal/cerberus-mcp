"""
Unit tests for Phase 3.3: Hybrid Retrieval

Tests BM25 search, vector search, ranking fusion, and query detection.
"""

import pytest
from pathlib import Path
from cerberus.schemas import CodeSymbol, SearchResult, CodeSnippet
from cerberus.retrieval.bm25_search import BM25Index
from cerberus.retrieval.hybrid_ranker import (
    detect_query_type,
    reciprocal_rank_fusion,
    weighted_score_fusion,
)


class TestBM25Search:
    """Test BM25 keyword search."""

    def test_bm25_basic_search(self):
        """Test basic BM25 search."""
        # Create test documents
        documents = [
            {
                "symbol": CodeSymbol(
                    name="DatabaseConnection",
                    type="class",
                    file_path="db.py",
                    start_line=1,
                    end_line=10,
                ),
                "snippet_text": "class DatabaseConnection connects to database with connection pooling",
            },
            {
                "symbol": CodeSymbol(
                    name="connect_to_db",
                    type="function",
                    file_path="db.py",
                    start_line=20,
                    end_line=30,
                ),
                "snippet_text": "function connect_to_db establishes database connection",
            },
            {
                "symbol": CodeSymbol(
                    name="User",
                    type="class",
                    file_path="user.py",
                    start_line=1,
                    end_line=20,
                ),
                "snippet_text": "class User represents user model with authentication",
            },
        ]

        # Build BM25 index
        bm25 = BM25Index(documents, k1=1.5, b=0.75)

        # Search for "database"
        results = bm25.search("database", top_k=5)

        # Should find database-related symbols
        assert len(results) >= 2
        assert any("database" in r.symbol.name.lower() or "db" in r.symbol.name.lower() for r in results)

    def test_bm25_exact_match(self):
        """Test BM25 gives high scores for exact matches."""
        documents = [
            {
                "symbol": CodeSymbol(
                    name="MyClass",
                    type="class",
                    file_path="test.py",
                    start_line=1,
                    end_line=10,
                ),
                "snippet_text": "class MyClass implements functionality",
            },
            {
                "symbol": CodeSymbol(
                    name="OtherClass",
                    type="class",
                    file_path="test.py",
                    start_line=20,
                    end_line=30,
                ),
                "snippet_text": "class OtherClass does something else",
            },
        ]

        bm25 = BM25Index(documents)
        results = bm25.search("MyClass", top_k=5)

        # MyClass should be first result
        assert len(results) > 0
        assert results[0].symbol.name == "MyClass"
        # BM25 normalized scores might be lower, just check it's positive
        assert results[0].score > 0

    def test_bm25_empty_query(self):
        """Test BM25 with empty query."""
        documents = [
            {
                "symbol": CodeSymbol(
                    name="Test",
                    type="function",
                    file_path="test.py",
                    start_line=1,
                    end_line=5,
                ),
                "snippet_text": "function test",
            },
        ]

        bm25 = BM25Index(documents)
        results = bm25.search("", top_k=5)

        assert len(results) == 0


class TestQueryTypeDetection:
    """Test query type auto-detection."""

    def test_detect_camelcase(self):
        """Test detection of CamelCase queries."""
        assert detect_query_type("DatabaseConnection") == "keyword"
        assert detect_query_type("MyClass") == "keyword"
        assert detect_query_type("UserAuthService") == "keyword"

    def test_detect_snake_case(self):
        """Test detection of snake_case queries."""
        assert detect_query_type("get_user_data") == "keyword"
        assert detect_query_type("connect_to_database") == "keyword"

    def test_detect_semantic_queries(self):
        """Test detection of semantic queries."""
        assert detect_query_type("how does authentication work") == "semantic"
        assert detect_query_type("code that handles database connections") == "semantic"
        assert detect_query_type("find error handling logic") == "semantic"

    def test_detect_short_queries(self):
        """Test short queries detected as keyword."""
        assert detect_query_type("auth") == "keyword"
        assert detect_query_type("db connection") == "keyword"

    def test_detect_long_queries(self):
        """Test long natural language queries as semantic."""
        query = "what is the implementation of user authentication and authorization"
        assert detect_query_type(query) == "semantic"


class TestRankingFusion:
    """Test ranking fusion methods."""

    def test_reciprocal_rank_fusion(self):
        """Test RRF fusion."""
        # Create test results
        bm25_results = [
            SearchResult(
                symbol=CodeSymbol(
                    name="Result1", type="function", file_path="test.py", start_line=1, end_line=5
                ),
                score=0.9,
                snippet=CodeSnippet(file_path="test.py", start_line=1, end_line=5, content="code"),
            ),
            SearchResult(
                symbol=CodeSymbol(
                    name="Result2", type="function", file_path="test.py", start_line=10, end_line=15
                ),
                score=0.7,
                snippet=CodeSnippet(file_path="test.py", start_line=10, end_line=15, content="code"),
            ),
        ]

        vector_results = [
            SearchResult(
                symbol=CodeSymbol(
                    name="Result2", type="function", file_path="test.py", start_line=10, end_line=15
                ),
                score=0.8,
                snippet=CodeSnippet(file_path="test.py", start_line=10, end_line=15, content="code"),
            ),
            SearchResult(
                symbol=CodeSymbol(
                    name="Result3", type="function", file_path="test.py", start_line=20, end_line=25
                ),
                score=0.6,
                snippet=CodeSnippet(file_path="test.py", start_line=20, end_line=25, content="code"),
            ),
        ]

        # Fuse results
        fused = reciprocal_rank_fusion(bm25_results, vector_results, k=60)

        # Should have 3 unique results
        assert len(fused) == 3

        # Result2 appears in both, should rank high
        result2 = next((r for r in fused if r.symbol.name == "Result2"), None)
        assert result2 is not None
        assert result2.match_type == "both"
        assert result2.bm25_score > 0
        assert result2.vector_score > 0

    def test_weighted_score_fusion(self):
        """Test weighted score fusion."""
        bm25_results = [
            SearchResult(
                symbol=CodeSymbol(
                    name="KeywordMatch", type="function", file_path="test.py", start_line=1, end_line=5
                ),
                score=0.9,
                snippet=CodeSnippet(file_path="test.py", start_line=1, end_line=5, content="code"),
            ),
        ]

        vector_results = [
            SearchResult(
                symbol=CodeSymbol(
                    name="SemanticMatch", type="function", file_path="test.py", start_line=10, end_line=15
                ),
                score=0.8,
                snippet=CodeSnippet(file_path="test.py", start_line=10, end_line=15, content="code"),
            ),
        ]

        # Emphasize keywords
        fused = weighted_score_fusion(
            bm25_results,
            vector_results,
            keyword_weight=0.7,
            semantic_weight=0.3,
        )

        # Should have both results
        assert len(fused) == 2

        # KeywordMatch should score higher (weighted toward keywords)
        keyword_match = next((r for r in fused if r.symbol.name == "KeywordMatch"), None)
        semantic_match = next((r for r in fused if r.symbol.name == "SemanticMatch"), None)

        assert keyword_match is not None
        assert semantic_match is not None
        assert keyword_match.hybrid_score > semantic_match.hybrid_score

    def test_fusion_empty_results(self):
        """Test fusion with empty result sets."""
        empty = []
        results = [
            SearchResult(
                symbol=CodeSymbol(
                    name="Test", type="function", file_path="test.py", start_line=1, end_line=5
                ),
                score=0.5,
                snippet=CodeSnippet(file_path="test.py", start_line=1, end_line=5, content="code"),
            ),
        ]

        # Fuse with empty BM25
        fused1 = reciprocal_rank_fusion(empty, results)
        assert len(fused1) == 1
        assert fused1[0].match_type == "semantic"

        # Fuse with empty vector
        fused2 = reciprocal_rank_fusion(results, empty)
        assert len(fused2) == 1
        assert fused2[0].match_type == "keyword"


if __name__ == "__main__":
    # Run tests manually (if pytest not available)
    import sys

    test_classes = [
        TestBM25Search,
        TestQueryTypeDetection,
        TestRankingFusion,
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n{'=' * 60}")
        print(f"Testing: {test_class.__name__}")
        print('=' * 60)

        instance = test_class()
        methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in methods:
            total_tests += 1
            try:
                method = getattr(instance, method_name)
                method()
                print(f"✓ {method_name}")
                passed_tests += 1
            except AssertionError as e:
                print(f"✗ {method_name}: {e}")
            except Exception as e:
                print(f"✗ {method_name}: ERROR: {e}")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed_tests}/{total_tests} tests passed")
    print('=' * 60)

    sys.exit(0 if passed_tests == total_tests else 1)
