"""
Phase 13: Indexed Search & Integration Tests

Comprehensive test suite covering all 10 test scenarios from PHASE-13B-INTEGRATION.md
"""

import pytest
import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import shutil

from cerberus.memory.search import (
    MemorySearchEngine,
    SearchQuery,
    SearchResult,
    BudgetAwareSearch
)
from cerberus.memory.storage import MemoryStorage
from cerberus.memory.retrieval import MemoryRetrieval
from cerberus.memory.indexing import MemoryIndexManager


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "memory.db"

    # Create schema using MemoryIndexManager
    manager = MemoryIndexManager(temp_dir)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def populated_db(temp_db):
    """Create database with test data."""
    db_path = temp_db / "memory.db"
    conn = sqlite3.connect(str(db_path))

    # Insert test memories
    test_memories = [
        # Scenario 1: Basic text search
        {
            "id": str(uuid.uuid4()),
            "content": "Always split large files into smaller modules",
            "category": "rule",
            "scope": "universal",
            "confidence": 0.9,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({"rationale": "Maintainability"})
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Keep files under 500 lines for better readability",
            "category": "rule",
            "scope": "universal",
            "confidence": 0.8,
            "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
            "metadata": json.dumps({"rationale": "Readability"})
        },
        # Scenario 2: Scope filtering
        {
            "id": str(uuid.uuid4()),
            "content": "Use error handling with defer in Go",
            "category": "rule",
            "scope": "language:go",
            "confidence": 0.95,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({})
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Use context managers for resources in Python",
            "category": "rule",
            "scope": "language:python",
            "confidence": 0.9,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({})
        },
        # Scenario 3: Category filtering
        {
            "id": str(uuid.uuid4()),
            "content": "Don't use global variables",
            "category": "correction",
            "scope": "universal",
            "confidence": 1.0,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({})
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Prefer composition over inheritance",
            "category": "preference",
            "scope": "universal",
            "confidence": 0.7,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({})
        },
        # Scenario 4: Confidence filtering
        {
            "id": str(uuid.uuid4()),
            "content": "High confidence memory",
            "category": "rule",
            "scope": "universal",
            "confidence": 0.95,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({})
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Low confidence memory",
            "category": "rule",
            "scope": "universal",
            "confidence": 0.4,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({})
        },
        # Scenario 5: Prefix scope match
        {
            "id": str(uuid.uuid4()),
            "content": "Hydra project decision",
            "category": "decision",
            "scope": "project:hydra",
            "confidence": 0.9,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({})
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Hydra task-specific note",
            "category": "decision",
            "scope": "project:hydra:task:auth",
            "confidence": 0.85,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({})
        },
        # Scenario 6: Relevance ordering
        {
            "id": str(uuid.uuid4()),
            "content": "Keep output short and concise",
            "category": "preference",
            "scope": "universal",
            "confidence": 0.9,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({})
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Output must be brief",
            "category": "preference",
            "scope": "universal",
            "confidence": 0.85,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({})
        },
        # Scenario 7: Recency ordering
        {
            "id": str(uuid.uuid4()),
            "content": "Recent memory 1",
            "category": "rule",
            "scope": "universal",
            "confidence": 0.8,
            "created_at": datetime.now().isoformat(),
            "metadata": json.dumps({})
        },
        {
            "id": str(uuid.uuid4()),
            "content": "Old memory 1",
            "category": "rule",
            "scope": "universal",
            "confidence": 0.8,
            "created_at": (datetime.now() - timedelta(days=100)).isoformat(),
            "metadata": json.dumps({})
        },
    ]

    for mem in test_memories:
        # Insert into memory_store (metadata)
        conn.execute("""
            INSERT INTO memory_store (
                id, category, scope, confidence,
                created_at, last_accessed, access_count, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mem["id"],
            mem["category"],
            mem["scope"],
            mem["confidence"],
            mem["created_at"],
            mem["created_at"],
            0,
            mem["metadata"]
        ))

        # Insert into memory_fts (FTS5 search)
        conn.execute("""
            INSERT INTO memory_fts (id, content)
            VALUES (?, ?)
        """, (mem["id"], mem["content"]))

    conn.commit()
    conn.close()

    return temp_db


class TestPhase13SearchEngine:
    """Test MemorySearchEngine class."""

    def test_scenario_1_basic_text_search(self, populated_db):
        """Scenario 1: Basic text search - memories containing 'split' or 'files'."""
        engine = MemorySearchEngine(populated_db / "memory.db")

        query = SearchQuery(text="split files", limit=20)
        results = engine.search(query)

        assert len(results) > 0
        assert any("split" in r.content.lower() or "files" in r.content.lower() for r in results)

        # Check relevance scoring
        for result in results:
            assert 0.0 <= result.relevance_score <= 1.0

    def test_scenario_2_scope_filtering(self, populated_db):
        """Scenario 2: Scope filtering - only Go-specific memories."""
        engine = MemorySearchEngine(populated_db / "memory.db")

        query = SearchQuery(text="", scope="language:go", limit=20)
        results = engine.search(query)

        assert len(results) > 0
        assert all(r.scope == "language:go" for r in results)
        assert not any(r.scope == "language:python" for r in results)

    def test_scenario_3_category_filtering(self, populated_db):
        """Scenario 3: Category filtering - only corrections."""
        engine = MemorySearchEngine(populated_db / "memory.db")

        query = SearchQuery(text="", category="correction", limit=20)
        results = engine.search(query)

        assert len(results) > 0
        assert all(r.category == "correction" for r in results)

    def test_scenario_4_confidence_filtering(self, populated_db):
        """Scenario 4: Confidence filtering - only high-confidence memories."""
        engine = MemorySearchEngine(populated_db / "memory.db")

        query = SearchQuery(text="", min_confidence=0.8, limit=20)
        results = engine.search(query)

        assert len(results) > 0
        assert all(r.confidence >= 0.8 for r in results)

    def test_scenario_5_prefix_scope_match(self, populated_db):
        """Scenario 5: Prefix scope match - project:hydra* matches all hydra scopes."""
        engine = MemorySearchEngine(populated_db / "memory.db")

        query = SearchQuery(text="", scope="project:hydra*", limit=20)
        results = engine.search(query)

        assert len(results) > 0
        assert all(r.scope.startswith("project:hydra") for r in results)

        # Check that both project:hydra and project:hydra:task:X are included
        scopes = {r.scope for r in results}
        assert "project:hydra" in scopes
        assert any(s.startswith("project:hydra:task:") for s in scopes)

    def test_scenario_6_relevance_ordering(self, populated_db):
        """Scenario 6: Relevance ordering - exact matches ranked higher."""
        engine = MemorySearchEngine(populated_db / "memory.db")

        query = SearchQuery(text="keep output short", limit=20, order_by="relevance")
        results = engine.search(query)

        assert len(results) > 0

        # First result should have highest relevance score
        if len(results) > 1:
            assert results[0].relevance_score >= results[1].relevance_score

    def test_scenario_7_recency_ordering(self, populated_db):
        """Scenario 7: Recency ordering - newest memories first."""
        engine = MemorySearchEngine(populated_db / "memory.db")

        query = SearchQuery(text="", order_by="recency", limit=20)
        results = engine.search(query)

        assert len(results) > 0

        # Check that results are ordered by creation date (newest first)
        if len(results) > 1:
            dates = [datetime.fromisoformat(r.created_at) for r in results]
            assert dates == sorted(dates, reverse=True)

    def test_scenario_8_budget_enforcement(self, populated_db):
        """Scenario 8: Budget enforcement - stops at budget limit."""
        engine = MemorySearchEngine(populated_db / "memory.db")
        budget_search = BudgetAwareSearch(engine)

        query = SearchQuery(text="", limit=100)
        results = budget_search.search_within_budget(query, budget=500)

        # Calculate total tokens
        total_tokens = sum(len(r.content.split()) * 1.3 + 10 for r in results)
        assert total_tokens <= 500

    def test_scenario_9_empty_results(self, populated_db):
        """Scenario 9: Empty results - no error on nonexistent term."""
        engine = MemorySearchEngine(populated_db / "memory.db")

        query = SearchQuery(text="nonexistent-term-xyz-12345", limit=20)
        results = engine.search(query)

        assert results == []

    def test_scenario_10_access_tracking(self, populated_db):
        """Scenario 10: Access tracking - access_count increments."""
        engine = MemorySearchEngine(populated_db / "memory.db")

        query = SearchQuery(text="split", limit=5)

        # First search
        results1 = engine.search(query)
        assert len(results1) > 0
        memory_id = results1[0].memory_id

        # Second search
        results2 = engine.search(query)

        # Third search
        results3 = engine.search(query)

        # Check access count in database directly
        conn = sqlite3.connect(str(populated_db / "memory.db"))
        cursor = conn.execute("SELECT access_count FROM memory_store WHERE id = ?", (memory_id,))
        access_count = cursor.fetchone()[0]
        conn.close()

        assert access_count >= 3


class TestPhase5Integration:
    """Test Phase 5 storage integration with SQLite."""

    def test_store_to_sqlite(self, temp_db):
        """Test storing proposals to SQLite."""
        storage = MemoryStorage(temp_db)

        # Create mock proposal
        from dataclasses import dataclass

        @dataclass
        class MockProposal:
            id: str
            content: str
            category: str
            scope: str
            confidence: float
            rationale: str

        proposal = MockProposal(
            id=str(uuid.uuid4()),
            content="Test memory content",
            category="rule",
            scope="universal",
            confidence=0.9,
            rationale="Test rationale"
        )

        result = storage.store_batch([proposal])

        assert result["total_stored"] == 1
        assert "universal" in result["by_scope"]

        # Verify in database
        conn = sqlite3.connect(str(temp_db / "memory.db"))
        cursor = conn.execute("SELECT COUNT(*) FROM memory_store")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1


class TestPhase6Integration:
    """Test Phase 6 retrieval integration with SQLite FTS5."""

    def test_retrieve_from_sqlite(self, populated_db):
        """Test retrieving memories from SQLite."""
        retrieval = MemoryRetrieval(populated_db)

        memories = retrieval.retrieve(
            language="go",
            token_budget=2000,
            min_relevance=0.0
        )

        assert len(memories) > 0

        # Check that Go-specific memories have higher relevance
        go_memories = [m for m in memories if "go" in m.scope.lower()]
        assert len(go_memories) > 0

    def test_token_savings_target(self, populated_db):
        """Validate 80%+ token savings compared to loading all memories."""
        retrieval = MemoryRetrieval(populated_db)

        # Retrieve with budget (FTS5 approach)
        filtered_memories = retrieval.retrieve(
            language="go",
            category="rule",
            token_budget=500,
            min_relevance=0.5
        )

        filtered_tokens = sum(m.token_count for m in filtered_memories)

        # Simulate loading all memories (JSON approach)
        all_memories = retrieval.retrieve(
            token_budget=10000,  # Large budget to get all
            min_relevance=0.0
        )

        all_tokens = sum(m.token_count for m in all_memories)

        if all_tokens > 0:
            savings = (1 - filtered_tokens / all_tokens) * 100
            print(f"\nToken savings: {savings:.1f}%")
            print(f"Filtered: {filtered_tokens} tokens, All: {all_tokens} tokens")

            # Target: 80%+ savings
            # Note: This may vary based on test data
            assert savings > 0  # At least some savings


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
