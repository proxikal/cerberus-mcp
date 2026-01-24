"""
Tests for Phase 8: Session Continuity

Covers all 15 test scenarios from PHASE-8-SESSION-CONTINUITY.md
"""

import json
import os
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cerberus.memory.session_continuity import (
    AutoCapture,
    InjectionPackage,
    SessionCleanupManager,
    SessionContext,
    SessionContextCapture,
    SessionContextInjector,
    detect_session_scope,
    on_session_start,
)


@pytest.fixture
def temp_db():
    """Create temporary test database with schema."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = Path(f.name)

    # Create schema using MemoryIndexManager (ensures complete schema)
    from cerberus.memory.indexing import MemoryIndexManager
    manager = MemoryIndexManager(db_path.parent)
    # Rename the created db to our temp path
    if (db_path.parent / "memory.db").exists():
        (db_path.parent / "memory.db").rename(db_path)

    yield db_path

    # Cleanup
    if db_path.exists():
        os.unlink(db_path)
    # Also cleanup WAL files if they exist
    for wal_file in [db_path.with_suffix('.db-wal'), db_path.with_suffix('.db-shm')]:
        if wal_file.exists():
            os.unlink(wal_file)


@pytest.fixture
def git_repo(tmp_path):
    """Create temporary git repo for testing."""
    repo_path = tmp_path / "test_project"
    repo_path.mkdir()
    (repo_path / ".git").mkdir()
    return repo_path


# ============================================================================
# Test Scenario 1: Basic capture (project scope)
# ============================================================================

def test_basic_capture_project_scope(temp_db, git_repo, monkeypatch):
    """Test basic session capture in project scope."""
    monkeypatch.chdir(git_repo)

    capture = SessionContextCapture(db_path=temp_db)

    # Verify scope detection
    assert capture.scope == f"project:{git_repo.name}"
    assert capture.project_path == str(git_repo)

    # Record some actions
    capture.record_file_modified("session_analyzer.py")
    capture.record_function("cluster_corrections")
    capture.record_decision("threshold", "0.75-precision")

    # Verify context
    context = capture.to_context(phase="PHASE-2-SEMANTIC")
    assert context.scope == f"project:{git_repo.name}"
    assert "impl:session_analyzer.py" in context.files_modified
    assert "impl:cluster_corrections" in context.key_functions
    assert "dec:threshold-0.75-precision" in context.decisions
    assert context.phase == "PHASE-2-SEMANTIC"


# ============================================================================
# Test Scenario 2: Global scope
# ============================================================================

def test_global_scope(temp_db, tmp_path, monkeypatch):
    """Test session capture in universal scope (no git repo)."""
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    monkeypatch.chdir(notes_dir)

    capture = SessionContextCapture(db_path=temp_db)

    # Verify universal scope
    assert capture.scope == "universal"
    assert capture.project_path is None

    # Record some actions
    capture.record_decision("approach", "brainstorming")
    capture.record_next("document-ideas")

    context = capture.to_context()
    assert context.scope == "universal"
    assert context.project_path is None


# ============================================================================
# Test Scenario 3: Save and load (same project)
# ============================================================================

def test_save_and_load_same_project(temp_db, git_repo, monkeypatch):
    """Test saving context and loading it in next session."""
    monkeypatch.chdir(git_repo)

    # First session: capture context
    capture1 = SessionContextCapture(db_path=temp_db)
    capture1.record_file_modified("proxy.go")
    capture1.record_decision("split", "3-files")
    capture1.record_next("add-mutex")
    session_id1 = capture1.session_id

    # Simulate session end (context auto-saved to DB via _sync_to_db)

    # Second session: load context
    capture2 = SessionContextCapture(db_path=temp_db)

    # Should get same session ID (active session for scope)
    assert capture2.session_id == session_id1

    # Should have loaded previous context
    assert "impl:proxy.go" in capture2.files_modified
    assert "dec:split-3-files" in capture2.decisions
    assert "next:add-mutex" in capture2.next_actions


# ============================================================================
# Test Scenario 4: Concurrent sessions
# ============================================================================

def test_concurrent_sessions(temp_db, tmp_path, monkeypatch):
    """Test multiple concurrent project sessions."""
    # Create two git repos
    repo_a = tmp_path / "cerberus"
    repo_a.mkdir()
    (repo_a / ".git").mkdir()

    repo_b = tmp_path / "hydra"
    repo_b.mkdir()
    (repo_b / ".git").mkdir()

    # Session A (cerberus)
    monkeypatch.chdir(repo_a)
    capture_a = SessionContextCapture(db_path=temp_db)
    capture_a.record_file_modified("semantic_analyzer.py")
    session_id_a = capture_a.session_id

    # Session B (hydra)
    monkeypatch.chdir(repo_b)
    capture_b = SessionContextCapture(db_path=temp_db)
    capture_b.record_file_modified("proxy.go")
    session_id_b = capture_b.session_id

    # Session IDs should be different
    assert session_id_a != session_id_b

    # Back to cerberus
    monkeypatch.chdir(repo_a)
    capture_a2 = SessionContextCapture(db_path=temp_db)

    # Should resume session A
    assert capture_a2.session_id == session_id_a
    assert "impl:semantic_analyzer.py" in capture_a2.files_modified
    assert "impl:proxy.go" not in capture_a2.files_modified  # Not from session B


# ============================================================================
# Test Scenario 5: Idle detection
# ============================================================================

def test_idle_detection(temp_db, git_repo, monkeypatch):
    """Test idle session detection and archival."""
    monkeypatch.chdir(git_repo)

    # Create session
    capture = SessionContextCapture(db_path=temp_db)
    session_id = capture.session_id

    # Manually set last_accessed to 8 days ago
    conn = sqlite3.connect(temp_db)
    old_timestamp = (datetime.now() - timedelta(days=8)).isoformat()
    conn.execute("""
        UPDATE sessions
        SET last_accessed = ?
        WHERE id = ?
    """, (old_timestamp, session_id))
    conn.commit()
    conn.close()

    # Try to inject (should delete idle session and return None)
    injector = SessionContextInjector(db_path=temp_db, idle_days=7)
    package = injector.inject(scope=capture.scope)

    assert package is None

    # Verify session was deleted (read-once, dispose pattern)
    conn = sqlite3.connect(temp_db)
    row = conn.execute("SELECT status FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()

    assert row is None  # Session should be deleted, not archived


# ============================================================================
# Test Scenario 6: Multiple scopes
# ============================================================================

def test_multiple_scopes(temp_db, tmp_path, monkeypatch):
    """Test isolation between universal and project sessions."""
    # Create universal session
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    monkeypatch.chdir(notes_dir)
    capture_universal = SessionContextCapture(db_path=temp_db)
    capture_universal.record_decision("brainstorm", "concepts")

    # Create project session
    repo = tmp_path / "cerberus"
    repo.mkdir()
    (repo / ".git").mkdir()
    monkeypatch.chdir(repo)
    capture_project = SessionContextCapture(db_path=temp_db)
    capture_project.record_file_modified("analyzer.py")

    # Inject project scope
    injector = SessionContextInjector(db_path=temp_db)
    package = injector.inject(scope="project:cerberus")

    assert package is not None
    assert "impl:analyzer.py" in package.codes
    assert "brainstorm" not in package.codes  # Universal session not included


# ============================================================================
# Test Scenario 7: Cleanup idle
# ============================================================================

def test_cleanup_idle_sessions(temp_db, git_repo, monkeypatch):
    """Test bulk cleanup of idle sessions."""
    monkeypatch.chdir(git_repo)

    # Create 3 sessions with different last_accessed times
    conn = sqlite3.connect(temp_db)

    # Session 1: 5 days ago (should remain active)
    session_id_1 = "session-aaa"
    last_accessed_1 = (datetime.now() - timedelta(days=5)).isoformat()
    conn.execute("""
        INSERT INTO sessions (id, scope, status, last_accessed, context_data)
        VALUES (?, 'project:test1', 'active', ?, '{}')
    """, (session_id_1, last_accessed_1))

    # Session 2: 8 days ago (should be archived)
    session_id_2 = "session-bbb"
    last_accessed_2 = (datetime.now() - timedelta(days=8)).isoformat()
    conn.execute("""
        INSERT INTO sessions (id, scope, status, last_accessed, context_data)
        VALUES (?, 'project:test2', 'active', ?, '{}')
    """, (session_id_2, last_accessed_2))

    # Session 3: 10 days ago (should be archived)
    session_id_3 = "session-ccc"
    last_accessed_3 = (datetime.now() - timedelta(days=10)).isoformat()
    conn.execute("""
        INSERT INTO sessions (id, scope, status, last_accessed, context_data)
        VALUES (?, 'project:test3', 'active', ?, '{}')
    """, (session_id_3, last_accessed_3))

    conn.commit()
    conn.close()

    # Run cleanup
    cleanup = SessionCleanupManager(db_path=temp_db)
    archived_count = cleanup.cleanup_idle(days=7)

    assert archived_count == 2

    # Verify statuses
    conn = sqlite3.connect(temp_db)
    status_1 = conn.execute("SELECT status FROM sessions WHERE id = ?", (session_id_1,)).fetchone()[0]
    status_2 = conn.execute("SELECT status FROM sessions WHERE id = ?", (session_id_2,)).fetchone()[0]
    status_3 = conn.execute("SELECT status FROM sessions WHERE id = ?", (session_id_3,)).fetchone()[0]
    conn.close()

    assert status_1 == "active"
    assert status_2 == "archived"
    assert status_3 == "archived"


# ============================================================================
# Test Scenario 8: Token budget
# ============================================================================

def test_token_budget(temp_db, git_repo, monkeypatch):
    """Test that session codes stay within token budget."""
    monkeypatch.chdir(git_repo)

    capture = SessionContextCapture(db_path=temp_db)

    # Record 15 files, 8 decisions, 3 blockers
    for i in range(15):
        capture.record_file_modified(f"file_{i}.py")

    for i in range(8):
        capture.record_decision(f"choice_{i}", f"reason_{i}")

    for i in range(3):
        capture.record_blocker("type", f"blocker_{i}")

    # Inject and check token count
    injector = SessionContextInjector(db_path=temp_db)
    package = injector.inject(scope=capture.scope)

    assert package is not None
    assert package.token_count < 1500  # Within budget


# ============================================================================
# Test Scenario 9: Scope detection
# ============================================================================

def test_scope_detection_nested(tmp_path, monkeypatch):
    """Test scope detection in nested directories."""
    # Create git repo
    repo = tmp_path / "cerberus"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "src").mkdir()

    # Test from src subdirectory
    monkeypatch.chdir(repo / "src")

    scope, project_path = detect_session_scope()

    assert scope == "project:cerberus"
    assert project_path == str(repo)


# ============================================================================
# Test Scenario 10: No active session
# ============================================================================

def test_no_active_session(temp_db, git_repo, monkeypatch):
    """Test injection when no active session exists."""
    monkeypatch.chdir(git_repo)

    injector = SessionContextInjector(db_path=temp_db)
    package = injector.inject(scope="project:nonexistent")

    assert package is None


# ============================================================================
# Test Scenario 11: AutoCapture tool integration
# ============================================================================

def test_autocapture_tool_use(temp_db, git_repo, monkeypatch):
    """Test AutoCapture integration with tool usage."""
    monkeypatch.chdir(git_repo)

    auto = AutoCapture(db_path=temp_db)

    # Simulate tool uses
    auto.on_tool_use("Edit", {"file_path": "analyzer.py"}, None)
    auto.on_tool_use("Write", {"file_path": "storage.py", "content": "def save_data():\n    pass"}, None)
    auto.on_tool_use("Bash", {"command": "pytest tests/"}, None)

    context = auto.get_context()

    assert "impl:analyzer.py" in context.files_modified
    assert "impl:storage.py" in context.files_modified
    assert "impl:save_data" in context.key_functions
    assert any("test:pytest" in item for item in context.completed)


# ============================================================================
# Test Scenario 12: AutoCapture user messages
# ============================================================================

def test_autocapture_user_message(temp_db, git_repo, monkeypatch):
    """Test AutoCapture detection from user messages."""
    monkeypatch.chdir(git_repo)

    auto = AutoCapture(db_path=temp_db)

    # Simulate user messages
    auto.on_user_message("Let's use TF-IDF for clustering")
    auto.on_user_message("I'm blocked because the database schema is unclear")

    context = auto.get_context()

    assert "dec:user_specified-explicit" in context.decisions
    assert any("block:user_reported" in item for item in context.blockers)


# ============================================================================
# Test Scenario 13: Session codes format
# ============================================================================

def test_session_codes_format(temp_db, git_repo, monkeypatch):
    """Test that injected codes follow AI-native format."""
    monkeypatch.chdir(git_repo)

    capture = SessionContextCapture(db_path=temp_db)
    capture.record_file_modified("proxy.go")
    capture.record_decision("split", "3-files")
    capture.record_blocker("race", "test-failure-line-712")
    capture.record_next("add-mutex-to-process-struct")
    capture.record_completion("impl:proxy-split")

    injector = SessionContextInjector(db_path=temp_db)
    package = injector.inject(scope=capture.scope)

    assert package is not None
    codes = package.codes

    # Verify format
    assert f"scope:project:{git_repo.name}" in codes
    assert "impl:proxy.go" in codes
    assert "dec:split-3-files" in codes
    assert "block:race:test-failure-line-712" in codes
    assert "next:add-mutex-to-process-struct" in codes
    assert "impl:proxy-split" in codes  # Completions don't get "done:" prefix


# ============================================================================
# Test Scenario 14: Mark complete
# ============================================================================

def test_mark_complete(temp_db, git_repo, monkeypatch):
    """Test marking session as complete."""
    monkeypatch.chdir(git_repo)

    # Create active session
    capture = SessionContextCapture(db_path=temp_db)
    session_id = capture.session_id

    # Mark complete
    injector = SessionContextInjector(db_path=temp_db)
    injector.mark_complete(scope=capture.scope)

    # Verify session was deleted
    conn = sqlite3.connect(temp_db)
    row = conn.execute("SELECT status FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()

    assert row is None  # Session should be deleted when marked complete


# ============================================================================
# Test Scenario 15: Integration with Phase 7
# ============================================================================

def test_integration_on_session_start(temp_db, git_repo, monkeypatch):
    """Test on_session_start integration function."""
    monkeypatch.chdir(git_repo)

    # Create session with some context
    capture = SessionContextCapture(db_path=temp_db)
    capture.record_file_modified("analyzer.py")
    capture.record_decision("threshold", "0.75")

    # Call integration function
    codes = on_session_start(scope=capture.scope, db_path=temp_db)

    assert codes is not None
    assert "impl:analyzer.py" in codes
    assert "dec:threshold-0.75" in codes


# ============================================================================
# Additional Edge Case Tests
# ============================================================================

def test_empty_context_data(temp_db, git_repo, monkeypatch):
    """Test handling of session with empty context_data."""
    monkeypatch.chdir(git_repo)

    # Create session without recording anything
    capture = SessionContextCapture(db_path=temp_db)

    # Inject should still work, just return minimal codes
    injector = SessionContextInjector(db_path=temp_db)
    package = injector.inject(scope=capture.scope)

    assert package is not None
    assert f"scope:project:{git_repo.name}" in package.codes


def test_unique_constraint_active_sessions(temp_db, git_repo, monkeypatch):
    """Test that only one active session per scope is allowed."""
    monkeypatch.chdir(git_repo)

    # Create first session
    capture1 = SessionContextCapture(db_path=temp_db)
    session_id_1 = capture1.session_id

    # Create second session (should reuse first)
    capture2 = SessionContextCapture(db_path=temp_db)
    session_id_2 = capture2.session_id

    # Should be same session
    assert session_id_1 == session_id_2


@pytest.mark.skip(reason="_touch_session() method removed - sessions use read-once dispose pattern")
def test_touch_session_updates_timestamp(temp_db, git_repo, monkeypatch):
    """Test that _touch_session updates last_accessed."""
    monkeypatch.chdir(git_repo)

    capture = SessionContextCapture(db_path=temp_db)
    session_id = capture.session_id

    # Set an old timestamp
    conn = sqlite3.connect(temp_db)
    old_timestamp = (datetime.now() - timedelta(hours=1)).isoformat()
    conn.execute(
        "UPDATE sessions SET last_accessed = ? WHERE id = ?",
        (old_timestamp, session_id)
    )
    conn.commit()

    initial_ts = conn.execute(
        "SELECT last_accessed FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()[0]
    conn.close()

    # Touch session
    injector = SessionContextInjector(db_path=temp_db)
    injector._touch_session(session_id)

    # Get updated timestamp
    conn = sqlite3.connect(temp_db)
    updated_ts = conn.execute(
        "SELECT last_accessed FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()[0]
    conn.close()

    # Timestamp should be updated
    assert updated_ts > initial_ts


def test_turn_count_increments(temp_db, git_repo, monkeypatch):
    """Test that turn_count increments on each sync."""
    monkeypatch.chdir(git_repo)

    capture = SessionContextCapture(db_path=temp_db)
    session_id = capture.session_id

    # Record some actions (each triggers _sync_to_db)
    capture.record_file_modified("file1.py")
    capture.record_file_modified("file2.py")
    capture.record_decision("choice", "reason")

    # Check turn count
    conn = sqlite3.connect(temp_db)
    turn_count = conn.execute(
        "SELECT turn_count FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()[0]
    conn.close()

    # Should have incremented 3 times
    assert turn_count == 3
