"""
Tests for Phase 12: Memory Indexing

Test scenarios:
1. Schema initialization
2. JSON to SQLite migration
3. Memory retrieval
4. Split-table architecture (memory_store + memory_fts)
5. Integrity verification
6. Database statistics
7. WAL mode enabled
8. Pre-provisioned Delta columns
9. Sessions table structure
10. CLI helpers
"""

import json
import pytest
import sqlite3
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from cerberus.memory.indexing import (
    MemoryIndexManager,
    IndexedMemory,
    SessionRecord,
    migrate_memories,
    verify_database,
    show_stats,
    SCHEMA_SQL
)


@pytest.fixture
def temp_cerberus_dir():
    """Create temporary cerberus directory with JSON data."""
    with TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        # Create JSON memory structure
        memory_path = base_path / "memory"
        memory_path.mkdir()

        (memory_path / "languages").mkdir()
        (memory_path / "projects" / "test-project").mkdir(parents=True)

        yield base_path


def create_test_memory(content: str, category: str = "preference", scope: str = "universal") -> dict:
    """Helper to create test memory."""
    return {
        "id": f"mem-{hash(content) % 100000}",
        "content": content,
        "category": category,
        "scope": scope,
        "confidence": 0.9,
        "timestamp": datetime.now().isoformat(),
        "rationale": "Test rationale",
    }


# ===== SCHEMA INITIALIZATION TESTS =====

def test_schema_initialization(temp_cerberus_dir):
    """Test that schema is created correctly."""
    manager = MemoryIndexManager(temp_cerberus_dir)

    # Check database exists
    assert manager.db_path.exists()

    # Check tables exist
    conn = sqlite3.connect(str(manager.db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    assert "memory_store" in tables
    assert "memory_fts" in tables
    assert "sessions" in tables
    assert "session_activity" in tables

    conn.close()


def test_wal_mode_enabled(temp_cerberus_dir):
    """Test that WAL mode is enabled for concurrency."""
    manager = MemoryIndexManager(temp_cerberus_dir)

    conn = sqlite3.connect(str(manager.db_path))
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode")
    mode = cursor.fetchone()[0]

    assert mode == "wal"

    conn.close()


def test_memory_store_columns(temp_cerberus_dir):
    """Test that memory_store has all required columns including Delta fields."""
    manager = MemoryIndexManager(temp_cerberus_dir)

    conn = sqlite3.connect(str(manager.db_path))
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(memory_store)")
    columns = {row[1] for row in cursor.fetchall()}

    # Core columns
    assert "id" in columns
    assert "category" in columns
    assert "scope" in columns
    assert "confidence" in columns
    assert "created_at" in columns
    assert "last_accessed" in columns
    assert "access_count" in columns
    assert "metadata" in columns

    # Pre-provisioned Delta columns
    assert "anchor_file" in columns
    assert "anchor_symbol" in columns
    assert "anchor_score" in columns
    assert "anchor_metadata" in columns
    assert "valid_modes" in columns
    assert "mode_priority" in columns

    conn.close()


def test_indices_created(temp_cerberus_dir):
    """Test that indices are created on memory_store."""
    manager = MemoryIndexManager(temp_cerberus_dir)

    conn = sqlite3.connect(str(manager.db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indices = {row[0] for row in cursor.fetchall()}

    assert "idx_mem_scope" in indices
    assert "idx_mem_category" in indices
    assert "idx_mem_created" in indices
    assert "idx_sess_scope" in indices

    conn.close()


# ===== MIGRATION TESTS =====

def test_migrate_from_json_universal(temp_cerberus_dir):
    """Test migration of universal memories from JSON."""
    # Create JSON memories
    memory_path = temp_cerberus_dir / "memory"
    memories = [
        create_test_memory("Keep output concise", "preference", "universal"),
        create_test_memory("Always add tests", "rule", "universal"),
    ]

    with open(memory_path / "profile.json", "w") as f:
        json.dump(memories, f)

    # Migrate
    manager = MemoryIndexManager(temp_cerberus_dir)
    result = manager.migrate_from_json()

    assert result["status"] == "success"
    assert result["universal"] == 2
    assert result["total"] == 2


def test_migrate_from_json_languages(temp_cerberus_dir):
    """Test migration of language-specific memories."""
    memory_path = temp_cerberus_dir / "memory"
    memories = [
        create_test_memory("Use goroutines for concurrency", "preference", "language:go"),
    ]

    with open(memory_path / "languages" / "go.json", "w") as f:
        json.dump(memories, f)

    manager = MemoryIndexManager(temp_cerberus_dir)
    result = manager.migrate_from_json()

    assert result["status"] == "success"
    assert result["languages"] == 1
    assert result["total"] == 1


def test_migrate_from_json_projects(temp_cerberus_dir):
    """Test migration of project-specific memories."""
    memory_path = temp_cerberus_dir / "memory"
    memories = [
        create_test_memory("Use custom validation", "decision", "project:test-project"),
    ]

    proj_path = memory_path / "projects" / "test-project"
    with open(proj_path / "decisions.json", "w") as f:
        json.dump(memories, f)

    manager = MemoryIndexManager(temp_cerberus_dir)
    result = manager.migrate_from_json()

    assert result["status"] == "success"
    assert result["projects"] == 1
    assert result["total"] == 1


def test_migrate_already_migrated(temp_cerberus_dir):
    """Test that migration is idempotent."""
    memory_path = temp_cerberus_dir / "memory"
    memories = [create_test_memory("Test memory")]

    with open(memory_path / "profile.json", "w") as f:
        json.dump(memories, f)

    manager = MemoryIndexManager(temp_cerberus_dir)

    # First migration
    result1 = manager.migrate_from_json()
    assert result1["status"] == "success"

    # Second migration (should skip)
    result2 = manager.migrate_from_json()
    assert result2["status"] == "already_migrated"


def test_migrate_no_json_found(temp_cerberus_dir):
    """Test migration when no JSON files exist."""
    # Remove the memory directory to simulate no JSON found
    import shutil
    shutil.rmtree(temp_cerberus_dir / "memory")

    manager = MemoryIndexManager(temp_cerberus_dir)
    result = manager.migrate_from_json()

    assert result["status"] == "no_json_found"
    assert result["total"] == 0


def test_split_table_architecture(temp_cerberus_dir):
    """Test that memories are inserted into both memory_store and memory_fts."""
    memory_path = temp_cerberus_dir / "memory"
    memories = [create_test_memory("Test content")]

    with open(memory_path / "profile.json", "w") as f:
        json.dump(memories, f)

    manager = MemoryIndexManager(temp_cerberus_dir)
    manager.migrate_from_json()

    conn = sqlite3.connect(str(manager.db_path))
    cursor = conn.cursor()

    # Check memory_store
    cursor.execute("SELECT COUNT(*) FROM memory_store")
    store_count = cursor.fetchone()[0]
    assert store_count == 1

    # Check memory_fts
    cursor.execute("SELECT COUNT(*) FROM memory_fts")
    fts_count = cursor.fetchone()[0]
    assert fts_count == 1

    # Verify join works
    cursor.execute("""
        SELECT ms.id, mf.content FROM memory_store ms
        JOIN memory_fts mf ON ms.id = mf.id
    """)
    rows = cursor.fetchall()
    assert len(rows) == 1
    assert rows[0][1] == "Test content"

    conn.close()


# ===== RETRIEVAL TESTS =====

def test_get_memory_by_id(temp_cerberus_dir):
    """Test retrieving a memory by ID."""
    memory_path = temp_cerberus_dir / "memory"
    test_mem = create_test_memory("Test content", "preference", "universal")

    with open(memory_path / "profile.json", "w") as f:
        json.dump([test_mem], f)

    manager = MemoryIndexManager(temp_cerberus_dir)
    manager.migrate_from_json()

    # Retrieve
    mem = manager.get_memory(test_mem["id"])

    assert mem is not None
    assert mem.id == test_mem["id"]
    assert mem.content == "Test content"
    assert mem.category == "preference"
    assert mem.scope == "universal"
    assert mem.confidence == 0.9


def test_get_memory_not_found(temp_cerberus_dir):
    """Test retrieving non-existent memory."""
    manager = MemoryIndexManager(temp_cerberus_dir)

    mem = manager.get_memory("nonexistent-id")
    assert mem is None


def test_get_memory_with_metadata(temp_cerberus_dir):
    """Test that metadata is preserved during migration."""
    memory_path = temp_cerberus_dir / "memory"
    test_mem = create_test_memory("Test content")
    test_mem["rationale"] = "Test rationale"
    test_mem["evidence"] = ["source1", "source2"]

    with open(memory_path / "profile.json", "w") as f:
        json.dump([test_mem], f)

    manager = MemoryIndexManager(temp_cerberus_dir)
    manager.migrate_from_json()

    mem = manager.get_memory(test_mem["id"])

    assert mem.metadata["rationale"] == "Test rationale"
    assert mem.metadata["evidence"] == ["source1", "source2"]


# ===== INTEGRITY VERIFICATION TESTS =====

def test_verify_integrity_clean_database(temp_cerberus_dir):
    """Test integrity verification on clean database."""
    memory_path = temp_cerberus_dir / "memory"
    memories = [
        create_test_memory("Memory 1"),
        create_test_memory("Memory 2"),
    ]

    with open(memory_path / "profile.json", "w") as f:
        json.dump(memories, f)

    manager = MemoryIndexManager(temp_cerberus_dir)
    manager.migrate_from_json()

    result = manager.verify_integrity()

    assert result["status"] == "ok"
    assert len(result["issues"]) == 0
    assert result["memory_store_count"] == 2
    assert result["memory_fts_count"] == 2


def test_verify_integrity_orphaned_store(temp_cerberus_dir):
    """Test detection of orphaned memory_store entries."""
    manager = MemoryIndexManager(temp_cerberus_dir)

    # Insert into memory_store only (not memory_fts)
    conn = sqlite3.connect(str(manager.db_path))
    conn.execute("""
        INSERT INTO memory_store
        (id, category, scope, confidence, created_at)
        VALUES ('orphan-id', 'preference', 'universal', 0.9, ?)
    """, (datetime.now().isoformat(),))
    conn.commit()
    conn.close()

    result = manager.verify_integrity()

    assert result["status"] == "issues_found"
    assert any("memory_store entries missing from memory_fts" in issue for issue in result["issues"])


def test_verify_integrity_orphaned_fts(temp_cerberus_dir):
    """Test detection of orphaned memory_fts entries."""
    manager = MemoryIndexManager(temp_cerberus_dir)

    # Insert into memory_fts only (not memory_store)
    conn = sqlite3.connect(str(manager.db_path))
    conn.execute("""
        INSERT INTO memory_fts (id, content)
        VALUES ('orphan-fts-id', 'Orphaned content')
    """)
    conn.commit()
    conn.close()

    result = manager.verify_integrity()

    assert result["status"] == "issues_found"
    assert any("memory_fts entries missing from memory_store" in issue for issue in result["issues"])


# ===== STATISTICS TESTS =====

def test_get_stats(temp_cerberus_dir):
    """Test database statistics."""
    memory_path = temp_cerberus_dir / "memory"
    memories = [
        create_test_memory("Universal pref", "preference", "universal"),
        create_test_memory("Go rule", "rule", "language:go"),
        create_test_memory("Project decision", "decision", "project:test"),
    ]

    with open(memory_path / "profile.json", "w") as f:
        json.dump(memories, f)

    manager = MemoryIndexManager(temp_cerberus_dir)
    manager.migrate_from_json()

    stats = manager.get_stats()

    assert stats["total_memories"] == 3
    assert stats["by_scope"]["universal"] == 1
    assert stats["by_scope"]["language:go"] == 1
    assert stats["by_scope"]["project:test"] == 1
    assert stats["by_category"]["preference"] == 1
    assert stats["by_category"]["rule"] == 1
    assert stats["by_category"]["decision"] == 1


# ===== CLI HELPERS TESTS =====

def test_migrate_memories_cli(temp_cerberus_dir):
    """Test migrate_memories CLI helper."""
    memory_path = temp_cerberus_dir / "memory"
    memories = [create_test_memory("CLI test")]

    with open(memory_path / "profile.json", "w") as f:
        json.dump(memories, f)

    result = migrate_memories(base_path=temp_cerberus_dir)

    assert result["status"] == "success"
    assert result["total"] == 1


def test_verify_database_cli(temp_cerberus_dir):
    """Test verify_database CLI helper."""
    memory_path = temp_cerberus_dir / "memory"
    memories = [create_test_memory("Verify test")]

    with open(memory_path / "profile.json", "w") as f:
        json.dump(memories, f)

    migrate_memories(base_path=temp_cerberus_dir)
    result = verify_database(base_path=temp_cerberus_dir)

    assert result["status"] == "ok"


def test_show_stats_cli(temp_cerberus_dir):
    """Test show_stats CLI helper."""
    memory_path = temp_cerberus_dir / "memory"
    memories = [create_test_memory("Stats test")]

    with open(memory_path / "profile.json", "w") as f:
        json.dump(memories, f)

    migrate_memories(base_path=temp_cerberus_dir)
    stats = show_stats(base_path=temp_cerberus_dir)

    assert stats["total_memories"] == 1


# ===== SESSIONS TABLE TESTS =====

def test_sessions_table_structure(temp_cerberus_dir):
    """Test that sessions table has correct structure."""
    manager = MemoryIndexManager(temp_cerberus_dir)

    conn = sqlite3.connect(str(manager.db_path))
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(sessions)")
    columns = {row[1] for row in cursor.fetchall()}

    assert "id" in columns
    assert "scope" in columns
    assert "project_path" in columns
    assert "phase" in columns
    assert "context_data" in columns
    assert "created_at" in columns
    assert "last_accessed" in columns
    assert "last_activity" in columns
    assert "turn_count" in columns
    assert "status" in columns

    conn.close()


def test_session_activity_table_structure(temp_cerberus_dir):
    """Test that session_activity table has correct structure."""
    manager = MemoryIndexManager(temp_cerberus_dir)

    conn = sqlite3.connect(str(manager.db_path))
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(session_activity)")
    columns = {row[1] for row in cursor.fetchall()}

    assert "id" in columns
    assert "session_id" in columns
    assert "turn_number" in columns
    assert "activity_type" in columns
    assert "activity_data" in columns
    assert "timestamp" in columns

    conn.close()


# ===== EDGE CASES =====

def test_empty_database_stats(temp_cerberus_dir):
    """Test stats on empty database."""
    manager = MemoryIndexManager(temp_cerberus_dir)
    stats = manager.get_stats()

    assert stats["total_memories"] == 0
    assert stats["by_scope"] == {}
    assert stats["by_category"] == {}


def test_memory_without_id(temp_cerberus_dir):
    """Test that memories without ID get generated ID."""
    memory_path = temp_cerberus_dir / "memory"
    memory = {
        "content": "No ID memory",
        "category": "preference",
        "scope": "universal",
        "confidence": 0.9,
        "timestamp": datetime.now().isoformat(),
    }

    with open(memory_path / "profile.json", "w") as f:
        json.dump([memory], f)

    manager = MemoryIndexManager(temp_cerberus_dir)
    result = manager.migrate_from_json()

    assert result["total"] == 1

    # Verify it has an ID
    stats = manager.get_stats()
    assert stats["total_memories"] == 1


def test_indexed_memory_to_dict(temp_cerberus_dir):
    """Test IndexedMemory.to_dict() serialization."""
    mem = IndexedMemory(
        id="test-id",
        content="Test content",
        category="preference",
        scope="universal",
        confidence=0.9,
        created_at=datetime.now().isoformat(),
        metadata={"key": "value"},
        anchor_file="test.py",
        valid_modes=["production"],
    )

    d = mem.to_dict()

    assert d["id"] == "test-id"
    assert d["content"] == "Test content"
    assert d["metadata"]["key"] == "value"
    assert d["anchor_file"] == "test.py"
    assert d["valid_modes"] == ["production"]
