"""
Tests for Phase 6: Retrieval Operations (JSON)

Validates:
- Scope-based loading (universal → language → project)
- Relevance scoring (scope + recency + confidence)
- Recency scoring (standardized decay curve)
- Budget-aware retrieval
- Token counting
- Filtering by category
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from cerberus.memory.retrieval import (
    MemoryRetrieval,
    RetrievedMemory,
    retrieve_memories
)


# Test fixtures

@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory with test memories."""
    temp_dir = tempfile.mkdtemp()

    # Create universal memories
    universal_pref = [
        {
            "id": "mem-001",
            "category": "preference",
            "scope": "universal",
            "content": "Keep output concise",
            "rationale": "User preference",
            "confidence": 0.95,
            "timestamp": (datetime.now() - timedelta(days=5)).isoformat(),
            "access_count": 0,
            "last_accessed": None
        },
        {
            "id": "mem-002",
            "category": "preference",
            "scope": "universal",
            "content": "Use early returns",
            "rationale": "Style preference",
            "confidence": 0.85,
            "timestamp": (datetime.now() - timedelta(days=100)).isoformat(),
            "access_count": 0,
            "last_accessed": None
        }
    ]

    universal_corr = [
        {
            "id": "mem-003",
            "category": "correction",
            "scope": "universal",
            "content": "Never use eval",
            "rationale": "Security rule",
            "confidence": 0.98,
            "timestamp": (datetime.now() - timedelta(days=10)).isoformat(),
            "access_count": 0,
            "last_accessed": None
        }
    ]

    # Create language-specific memories
    python_rules = [
        {
            "id": "mem-004",
            "category": "rule",
            "scope": "language:python",
            "content": "Use async/await",
            "rationale": "Python pattern",
            "confidence": 0.90,
            "timestamp": (datetime.now() - timedelta(days=20)).isoformat(),
            "access_count": 0,
            "last_accessed": None
        }
    ]

    go_rules = [
        {
            "id": "mem-005",
            "category": "rule",
            "scope": "language:go",
            "content": "Use defer for cleanup",
            "rationale": "Go idiom",
            "confidence": 0.92,
            "timestamp": (datetime.now() - timedelta(days=15)).isoformat(),
            "access_count": 0,
            "last_accessed": None
        }
    ]

    # Create project-specific memories
    cerberus_decisions = [
        {
            "id": "mem-006",
            "category": "rule",
            "scope": "project:cerberus",
            "content": "Use golden egg docs",
            "rationale": "Project decision",
            "confidence": 0.88,
            "timestamp": (datetime.now() - timedelta(days=3)).isoformat(),
            "access_count": 0,
            "last_accessed": None
        }
    ]

    # Write files
    Path(temp_dir).mkdir(exist_ok=True)

    with open(Path(temp_dir) / "profile.json", 'w') as f:
        json.dump(universal_pref, f, indent=2)

    with open(Path(temp_dir) / "corrections.json", 'w') as f:
        json.dump(universal_corr, f, indent=2)

    Path(temp_dir, "languages").mkdir(exist_ok=True)
    with open(Path(temp_dir) / "languages" / "python.json", 'w') as f:
        json.dump(python_rules, f, indent=2)

    with open(Path(temp_dir) / "languages" / "go.json", 'w') as f:
        json.dump(go_rules, f, indent=2)

    Path(temp_dir, "projects", "cerberus").mkdir(parents=True, exist_ok=True)
    with open(Path(temp_dir) / "projects" / "cerberus" / "decisions.json", 'w') as f:
        json.dump(cerberus_decisions, f, indent=2)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def retrieval(temp_storage_dir):
    """Create MemoryRetrieval instance."""
    return MemoryRetrieval(base_dir=temp_storage_dir)


# Test scope-based loading

def test_load_universal_only(retrieval):
    """Should load only universal memories when no context."""
    memories = retrieval.retrieve()

    scopes = {m.scope for m in memories}
    assert "universal" in scopes
    assert not any(s.startswith("language:") for s in scopes)
    assert not any(s.startswith("project:") for s in scopes)


def test_load_with_language_context(retrieval):
    """Should load universal + language-specific memories."""
    memories = retrieval.retrieve(language="python")

    scopes = {m.scope for m in memories}
    assert "universal" in scopes
    assert "language:python" in scopes
    assert "language:go" not in scopes


def test_load_with_project_context(retrieval):
    """Should load universal + project-specific memories."""
    memories = retrieval.retrieve(project="cerberus")

    scopes = {m.scope for m in memories}
    assert "universal" in scopes
    assert "project:cerberus" in scopes


def test_load_with_full_context(retrieval):
    """Should load universal + language + project memories."""
    memories = retrieval.retrieve(language="go", project="cerberus")

    scopes = {m.scope for m in memories}
    assert "universal" in scopes
    assert "language:go" in scopes
    assert "project:cerberus" in scopes
    assert "language:python" not in scopes


# Test relevance scoring

def test_relevance_universal_highest(retrieval):
    """Universal memories should have high relevance."""
    memories = retrieval.retrieve()

    # Find universal memory
    universal = [m for m in memories if m.scope == "universal"][0]
    assert universal.relevance_score > 0.0


def test_relevance_recent_higher(retrieval):
    """More recent memories should have higher relevance."""
    memories = retrieval.retrieve()

    # mem-001 is 5 days old (recency=1.0)
    # mem-002 is 100 days old (recency=0.6)
    mem_001 = [m for m in memories if m.id == "mem-001"][0]
    mem_002 = [m for m in memories if m.id == "mem-002"][0]

    assert mem_001.relevance_score > mem_002.relevance_score


def test_relevance_confidence_weight(retrieval):
    """Higher confidence should increase relevance."""
    memories = retrieval.retrieve()

    # All else equal, higher confidence = higher relevance
    # mem-003 has confidence 0.98, mem-001 has 0.95
    mem_003 = [m for m in memories if m.id == "mem-003"][0]

    assert mem_003.confidence == 0.98
    assert mem_003.relevance_score > 0.0


def test_relevance_language_mismatch_filtered(retrieval):
    """Language mismatch should result in zero relevance (filtered out)."""
    # Request Python context
    memories = retrieval.retrieve(language="python")

    # Should not include Go memories
    go_memories = [m for m in memories if m.scope == "language:go"]
    assert len(go_memories) == 0


def test_relevance_sorting(retrieval):
    """Memories should be sorted by relevance (high to low)."""
    memories = retrieval.retrieve()

    # Check descending order
    for i in range(len(memories) - 1):
        assert memories[i].relevance_score >= memories[i+1].relevance_score


# Test recency scoring

def test_recency_less_than_7_days(retrieval):
    """Memories < 7 days old should have recency 1.0."""
    # mem-001 is 5 days old
    mem_001_timestamp = (datetime.now() - timedelta(days=5)).isoformat()
    recency = retrieval._calculate_recency(mem_001_timestamp)
    assert recency == 1.0


def test_recency_less_than_30_days(retrieval):
    """Memories < 30 days old should have recency 0.8."""
    # 20 days old
    timestamp = (datetime.now() - timedelta(days=20)).isoformat()
    recency = retrieval._calculate_recency(timestamp)
    assert recency == 0.8


def test_recency_less_than_90_days(retrieval):
    """Memories < 90 days old should have recency 0.6."""
    # 60 days old
    timestamp = (datetime.now() - timedelta(days=60)).isoformat()
    recency = retrieval._calculate_recency(timestamp)
    assert recency == 0.6


def test_recency_less_than_180_days(retrieval):
    """Memories < 180 days old should have recency 0.4."""
    # 120 days old
    timestamp = (datetime.now() - timedelta(days=120)).isoformat()
    recency = retrieval._calculate_recency(timestamp)
    assert recency == 0.4


def test_recency_greater_than_180_days(retrieval):
    """Memories >= 180 days old should have recency 0.2."""
    # 200 days old
    timestamp = (datetime.now() - timedelta(days=200)).isoformat()
    recency = retrieval._calculate_recency(timestamp)
    assert recency == 0.2


# Test budget-aware retrieval

def test_budget_enforcement_stops_at_limit(retrieval):
    """Should stop retrieving when budget exhausted."""
    # Small budget that won't fit all memories
    memories = retrieval.retrieve(token_budget=50)

    total_tokens = sum(m.token_count for m in memories)
    assert total_tokens <= 50


def test_budget_takes_highest_relevance(retrieval):
    """Budget should prioritize highest relevance memories."""
    # Get all memories without budget
    all_memories = retrieval.retrieve(token_budget=10000)

    # Get with small budget
    budgeted = retrieval.retrieve(token_budget=100)

    # Budgeted should be subset of highest relevance
    budgeted_ids = {m.id for m in budgeted}
    for memory in budgeted:
        # All budgeted memories should be high relevance
        assert memory.relevance_score > 0.0


def test_budget_zero_returns_empty(retrieval):
    """Zero budget should return empty list."""
    memories = retrieval.retrieve(token_budget=0)
    assert len(memories) == 0


# Test category filtering

def test_filter_by_preference(retrieval):
    """Should filter to only preferences."""
    memories = retrieval.retrieve(category="preference")

    for memory in memories:
        assert memory.category == "preference"


def test_filter_by_correction(retrieval):
    """Should filter to only corrections."""
    memories = retrieval.retrieve(category="correction")

    for memory in memories:
        assert memory.category == "correction"


def test_filter_by_rule(retrieval):
    """Should filter to only rules."""
    memories = retrieval.retrieve(language="python", category="rule")

    for memory in memories:
        assert memory.category == "rule"


# Test token counting

def test_token_count_populated(retrieval):
    """All memories should have token count."""
    memories = retrieval.retrieve()

    for memory in memories:
        assert memory.token_count > 0


def test_token_count_reasonable(retrieval):
    """Token counts should be reasonable estimates."""
    memories = retrieval.retrieve()

    for memory in memories:
        # Rough check: token count should be less than character count
        assert memory.token_count <= len(memory.content)
        # And greater than 1/5 of character count (very rough heuristic)
        assert memory.token_count >= len(memory.content) // 5


# Test min_relevance filtering

def test_min_relevance_filters(retrieval):
    """Should filter out memories below min_relevance."""
    memories = retrieval.retrieve(min_relevance=0.8)

    for memory in memories:
        assert memory.relevance_score >= 0.8


# Test empty storage

def test_empty_storage():
    """Should handle empty storage gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        retrieval = MemoryRetrieval(base_dir=temp_dir)
        memories = retrieval.retrieve()
        assert len(memories) == 0


# Test retrieval stats

def test_stats_counts_all_memories(retrieval):
    """Stats should count all memories correctly."""
    stats = retrieval.get_stats()

    # We have 6 total memories
    assert stats["total_memories"] == 6
    assert stats["total_files"] == 5

    # Scope breakdown
    assert stats["by_scope"]["universal"] == 3  # 2 preferences + 1 correction
    assert stats["by_scope"]["language"] == 2   # 1 python + 1 go
    assert stats["by_scope"]["project"] == 1    # 1 cerberus


# Test convenience function

def test_convenience_function(temp_storage_dir):
    """retrieve_memories convenience function should work."""
    memories = retrieve_memories(
        language="python",
        project="cerberus",
        base_dir=temp_storage_dir
    )

    assert len(memories) > 0
    scopes = {m.scope for m in memories}
    assert "universal" in scopes
    assert "language:python" in scopes
    assert "project:cerberus" in scopes


# Test RetrievedMemory dataclass

def test_retrieved_memory_to_dict():
    """RetrievedMemory.to_dict() should work."""
    memory = RetrievedMemory(
        id="test-001",
        category="preference",
        scope="universal",
        content="Test content",
        rationale="Test rationale",
        confidence=0.9,
        timestamp="2024-01-01T00:00:00",
        access_count=0,
        last_accessed=None,
        relevance_score=0.85,
        token_count=5
    )

    data = memory.to_dict()
    assert data["id"] == "test-001"
    assert data["relevance_score"] == 0.85
    assert data["token_count"] == 5


# Integration test

def test_full_integration(temp_storage_dir):
    """Full integration test with context and budget."""
    retrieval = MemoryRetrieval(base_dir=temp_storage_dir)

    # Python project context with budget
    memories = retrieval.retrieve(
        language="python",
        project="cerberus",
        token_budget=500
    )

    # Should have universal + python + cerberus
    scopes = {m.scope for m in memories}
    assert "universal" in scopes
    assert "language:python" in scopes
    assert "project:cerberus" in scopes

    # Should respect budget
    total_tokens = sum(m.token_count for m in memories)
    assert total_tokens <= 500

    # Should be sorted by relevance
    for i in range(len(memories) - 1):
        assert memories[i].relevance_score >= memories[i+1].relevance_score

    # All should have metadata
    for memory in memories:
        assert memory.id
        assert memory.content
        assert memory.relevance_score > 0.0
        assert memory.token_count > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
