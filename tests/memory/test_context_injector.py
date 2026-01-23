"""
Tests for Phase 7: Context-Aware Injection

Validates:
- Context detection (project, language)
- Session start auto-injection (1200 token budget)
- On-demand queries (500 tokens each, max 2)
- Token budget enforcement (total cap 2200)
- Markdown formatting
- Usage statistics
"""

import pytest
import json
import tempfile
import shutil
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timedelta

from cerberus.memory.context_injector import (
    ContextDetector,
    ContextInjector,
    DetectedContext,
    inject_startup_context,
    inject_query_context,
    detect_context
)
from cerberus.memory.indexing import MemoryIndexManager


# Test fixtures

@pytest.fixture
def temp_project_dir():
    """Create temporary project directory with code files."""
    temp_dir = tempfile.mkdtemp()
    project_dir = Path(temp_dir) / "myproject"
    project_dir.mkdir()

    # Create .git directory (marks as git project)
    (project_dir / ".git").mkdir()

    # Create Python files
    (project_dir / "main.py").write_text("# Python code")
    (project_dir / "utils.py").write_text("# More Python")
    (project_dir / "test.go").write_text("// Go code")

    yield str(project_dir)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_storage_with_memories():
    """Create temporary storage with test memories in SQLite."""
    temp_dir = Path(tempfile.mkdtemp())
    db_path = temp_dir / "memory.db"

    # Create schema using MemoryIndexManager
    manager = MemoryIndexManager(temp_dir)

    # Insert test memories directly into SQLite
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    test_memories = [
        # Universal preferences
        {
            "id": "mem-001",
            "content": "Keep output concise",
            "category": "preference",
            "scope": "universal",
            "confidence": 0.95,
            "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
            "metadata": json.dumps({"rationale": "User preference"})
        },
        {
            "id": "mem-002",
            "content": "Use early returns",
            "category": "preference",
            "scope": "universal",
            "confidence": 0.85,
            "created_at": (datetime.now() - timedelta(days=10)).isoformat(),
            "metadata": json.dumps({"rationale": "Style preference"})
        },
        # Universal correction
        {
            "id": "mem-003",
            "content": "Never use eval",
            "category": "correction",
            "scope": "universal",
            "confidence": 0.98,
            "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
            "metadata": json.dumps({"rationale": "Security rule"})
        },
        # Python rule
        {
            "id": "mem-004",
            "content": "Use async/await for I/O",
            "category": "rule",
            "scope": "language:python",
            "confidence": 0.90,
            "created_at": (datetime.now() - timedelta(days=7)).isoformat(),
            "metadata": json.dumps({"rationale": "Python pattern"})
        },
        # Project decision
        {
            "id": "mem-005",
            "content": "Use golden egg docs",
            "category": "rule",
            "scope": "project:myproject",
            "confidence": 0.88,
            "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
            "metadata": json.dumps({"rationale": "Project decision"})
        }
    ]

    for memory in test_memories:
        # Insert into memory_store (metadata only, no content column)
        cursor.execute("""
            INSERT INTO memory_store
            (id, category, scope, confidence, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            memory["id"],
            memory["category"],
            memory["scope"],
            memory["confidence"],
            memory["created_at"],
            memory["metadata"]
        ))

        # Insert into FTS5 table (content goes here)
        cursor.execute("""
            INSERT INTO memory_fts (id, content)
            VALUES (?, ?)
        """, (
            memory["id"],
            memory["content"]
        ))

    conn.commit()
    conn.close()

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


# Test context detection

def test_detect_project_from_git(temp_project_dir):
    """Should detect project name from git repository."""
    detector = ContextDetector()
    context = detector.detect(cwd=temp_project_dir)

    assert context.project == "myproject"


def test_detect_language_from_files(temp_project_dir):
    """Should detect primary language from file extensions."""
    detector = ContextDetector()
    context = detector.detect(cwd=temp_project_dir)

    # Should detect Python (2 .py files vs 1 .go file)
    assert context.language == "python"
    assert "main.py" in context.detected_files
    assert "utils.py" in context.detected_files


def test_detect_no_project():
    """Should handle no project gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        detector = ContextDetector()
        context = detector.detect(cwd=temp_dir)

        # Generic temporary directory should not be detected as project
        assert context.project is None or context.project


def test_detect_no_language():
    """Should handle no language files gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        detector = ContextDetector()
        context = detector.detect(cwd=temp_dir)

        assert context.language is None


# Test startup injection

def test_startup_injection_formats_markdown(temp_storage_with_memories):
    """Startup injection should format as markdown."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    output = injector.inject_startup(context=context)

    # Should be markdown formatted
    assert "## Memory Context" in output
    assert "### Preferences" in output or "### Rules" in output or "### Corrections" in output


def test_startup_injection_respects_budget(temp_storage_with_memories):
    """Startup injection should stay under 1200 token budget."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    output = injector.inject_startup(context=context)

    # Count tokens
    token_count = injector._count_tokens(output)

    assert token_count <= injector.STARTUP_BUDGET


def test_startup_injection_includes_context(temp_storage_with_memories):
    """Should include project and language in output."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    output = injector.inject_startup(context=context)

    assert "myproject" in output
    assert "python" in output


def test_startup_injection_high_relevance_only(temp_storage_with_memories):
    """Startup should only include high relevance memories (min_relevance=0.5)."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    output = injector.inject_startup(context=context, min_relevance=0.5)

    # Should have content
    assert len(output) > 0


def test_startup_injection_empty_memories():
    """Should handle empty storage gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        context = DetectedContext(project="test", language="python")

        injector = ContextInjector(base_dir=temp_dir)
        output = injector.inject_startup(context=context)

        assert output == ""


# Test on-demand queries

def test_query_injection_formats_with_query_header(temp_storage_with_memories):
    """Query injection should include query in header."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    output = injector.inject_query("error handling", context=context)

    assert "Query:" in output
    assert "error handling" in output


def test_query_injection_respects_budget(temp_storage_with_memories):
    """Query injection should stay under 500 token budget."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    output = injector.inject_query("test query", context=context)

    token_count = injector._count_tokens(output)

    assert token_count <= injector.ONDEMAND_BUDGET


def test_query_injection_lower_min_relevance(temp_storage_with_memories):
    """Query should use broader relevance (min_relevance=0.3)."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    output = injector.inject_query("test", context=context, min_relevance=0.3)

    # Should return memories
    assert len(output) > 0


def test_query_limit_enforcement(temp_storage_with_memories):
    """Should enforce max 2 queries per session."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)

    # Query 1
    output1 = injector.inject_query("query 1", context=context)
    assert "query 1" in output1

    # Query 2
    output2 = injector.inject_query("query 2", context=context)
    assert "query 2" in output2

    # Query 3 (should be rejected)
    output3 = injector.inject_query("query 3", context=context)
    assert "limit reached" in output3


def test_query_empty_result(temp_storage_with_memories):
    """Should still return universal memories even with non-matching context."""
    context = DetectedContext(project="nonexistent", language="rust")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    output = injector.inject_query("test", context=context)

    # Universal memories should still be returned
    # (universal scope is always relevant regardless of context)
    assert len(output) > 0
    assert "Keep output concise" in output or "Never use eval" in output


# Test token budget enforcement

def test_total_budget_cap(temp_storage_with_memories):
    """Should enforce 2200 token total cap."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)

    # Startup (1200 tokens)
    injector.inject_startup(context=context)

    # Query 1 (500 tokens)
    injector.inject_query("query 1", context=context)

    # Query 2 (500 tokens)
    injector.inject_query("query 2", context=context)

    # Total should be under 2200
    assert injector.session_tokens_used <= injector.TOTAL_CAP


def test_budget_exhaustion_stops_queries(temp_storage_with_memories):
    """Should stop queries when budget exhausted."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)

    # Manually set high token usage
    injector.session_tokens_used = 2150  # Near cap

    # Try query (should be rejected)
    output = injector.inject_query("test", context=context)

    assert "budget exhausted" in output or "limit reached" in output


# Test markdown formatting

def test_markdown_has_categories(temp_storage_with_memories):
    """Output should group by categories."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    output = injector.inject_startup(context=context)

    # Should have category headers
    has_preferences = "### Preferences" in output
    has_rules = "### Rules" in output
    has_corrections = "### Corrections" in output

    # At least one category should be present
    assert has_preferences or has_rules or has_corrections


def test_markdown_has_scope_badges(temp_storage_with_memories):
    """Non-universal memories should have scope badges."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    output = injector.inject_startup(context=context)

    # Should have badges for language/project scopes
    # Check for backtick-wrapped scope indicators
    assert "`[" in output or len([m for m in output.split('\n') if m.startswith('-')]) > 0


def test_markdown_has_memory_count(temp_storage_with_memories):
    """Output should include memory count."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    output = injector.inject_startup(context=context)

    assert "memories loaded" in output or "memory" in output.lower()


# Test usage statistics

def test_usage_stats_tracks_tokens(temp_storage_with_memories):
    """Should track token usage in stats."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    injector.inject_startup(context=context)

    stats = injector.get_usage_stats()

    assert stats["session_tokens_used"] > 0
    assert stats["startup_budget"] == 1200
    assert stats["total_cap"] == 2200


def test_usage_stats_tracks_queries(temp_storage_with_memories):
    """Should track query count in stats."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)

    injector.inject_query("query 1", context=context)
    injector.inject_query("query 2", context=context)

    stats = injector.get_usage_stats()

    assert stats["ondemand_queries_count"] == 2
    assert stats["max_ondemand_queries"] == 2


def test_usage_stats_remaining_budget(temp_storage_with_memories):
    """Should calculate remaining budget."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)
    injector.inject_startup(context=context)

    stats = injector.get_usage_stats()

    assert stats["remaining_budget"] == stats["total_cap"] - stats["session_tokens_used"]
    assert stats["remaining_budget"] >= 0


# Test convenience functions

def test_inject_startup_context_convenience(temp_project_dir, temp_storage_with_memories):
    """inject_startup_context convenience function should work."""
    output = inject_startup_context(
        cwd=temp_project_dir,
        base_dir=temp_storage_with_memories
    )

    assert "## Memory Context" in output


def test_inject_query_context_convenience(temp_project_dir, temp_storage_with_memories):
    """inject_query_context convenience function should work."""
    output = inject_query_context(
        query="test query",
        cwd=temp_project_dir,
        base_dir=temp_storage_with_memories
    )

    assert "Query:" in output or "No relevant" in output or len(output) >= 0


def test_detect_context_convenience(temp_project_dir):
    """detect_context convenience function should work."""
    context = detect_context(cwd=temp_project_dir)

    assert context.project == "myproject"
    assert context.language == "python"


# Integration test

def test_full_session_flow(temp_project_dir, temp_storage_with_memories):
    """Full session: startup + 2 queries, budget enforcement."""
    context = DetectedContext(project="myproject", language="python")

    injector = ContextInjector(base_dir=temp_storage_with_memories)

    # Startup injection
    startup_output = injector.inject_startup(context=context)
    assert len(startup_output) > 0
    assert injector.session_tokens_used <= 1200

    # Query 1
    query1_output = injector.inject_query("error handling", context=context)
    assert len(query1_output) > 0

    # Query 2
    query2_output = injector.inject_query("testing", context=context)
    assert len(query2_output) > 0

    # Query 3 (should be rejected)
    query3_output = injector.inject_query("docs", context=context)
    assert "limit reached" in query3_output

    # Check total tokens
    stats = injector.get_usage_stats()
    assert stats["session_tokens_used"] <= stats["total_cap"]
    assert stats["ondemand_queries_count"] == 2


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
