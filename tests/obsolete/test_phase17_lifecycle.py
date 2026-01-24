"""
Phase 17: Session Lifecycle & Recovery - Unit Tests

OBSOLETE: These tests were written for JSON-based session storage and session_lifecycle.py module.
The module was renamed to session_cli.py and session storage migrated to SQLite (memory.db).
See tests/memory/test_session_continuity.py for modern session tests.

Tests for session lifecycle management, crash detection, and recovery.
"""

import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Skip all tests in this file - they test obsolete JSON session storage
pytestmark = pytest.mark.skip(reason="Obsolete: session_lifecycle.py renamed to session_cli.py, JSON storage replaced by SQLite")

# Imports commented out - session_lifecycle module renamed to session_cli
# from cerberus.memory.session_lifecycle import (
#     SessionState,
#     SessionRecovery,
#     start_session,
#     end_session,
#     update_session_activity,
#     detect_crash,
#     auto_recover_crash,
#     check_idle_timeout,
#     idle_timeout_daemon,
#     get_session_state_info,
#     list_crashed_sessions,
#     recover_crashed_session,
#     _write_session_state,
#     _load_session_state,
#     SESSION_FILE,
#     SESSION_TIMEOUTS,
# )
#
# from cerberus.memory.session_analyzer import CorrectionCandidate


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_session_state():
    """Create a mock SessionState."""
    return SessionState(
        session_id="session-test123",
        started_at=datetime.now(),
        last_activity=datetime.now(),
        working_directory="/tmp/test-project",
        project_name="test-project",
        language="python",
        turn_count=5,
        corrections=[],
        tools_used=["Read", "Edit"],
        modified_files=["main.py", "utils.py"],
        status="active"
    )


@pytest.fixture
def mock_correction_candidate():
    """Create a mock CorrectionCandidate."""
    return CorrectionCandidate(
        turn_number=3,
        user_message="Don't use global variables",
        ai_response="Generated code with globals",
        correction_type="rule",
        confidence=0.9,
        context_before=[]
    )


# ============================================================================
# SessionState Tests
# ============================================================================

def test_session_state_to_dict(mock_session_state):
    """Test SessionState serialization."""
    data = mock_session_state.to_dict()

    assert data["session_id"] == "session-test123"
    assert data["project_name"] == "test-project"
    assert data["language"] == "python"
    assert data["turn_count"] == 5
    assert isinstance(data["started_at"], str)
    assert isinstance(data["last_activity"], str)
    assert data["tools_used"] == ["Read", "Edit"]
    assert data["modified_files"] == ["main.py", "utils.py"]


def test_session_state_from_dict():
    """Test SessionState deserialization."""
    data = {
        "session_id": "session-abc",
        "started_at": "2026-01-22T10:30:00",
        "last_activity": "2026-01-22T10:35:00",
        "working_directory": "/tmp/test",
        "project_name": "test",
        "language": "go",
        "turn_count": 3,
        "corrections": [],
        "tools_used": ["Bash"],
        "modified_files": [],
        "status": "active"
    }

    state = SessionState.from_dict(data)

    assert state.session_id == "session-abc"
    assert state.project_name == "test"
    assert isinstance(state.started_at, datetime)
    assert isinstance(state.last_activity, datetime)


# ============================================================================
# Session Start Tests
# ============================================================================

def test_start_session_clean(temp_dir, monkeypatch):
    """Test starting session with no existing session."""
    monkeypatch.chdir(temp_dir)

    state = start_session(
        working_directory=str(temp_dir),
        project_name="test-project",
        language="python"
    )

    assert state.session_id.startswith("session-")
    assert state.project_name == "test-project"
    assert state.language == "python"
    assert state.turn_count == 0
    assert state.status == "active"

    # Check session file created
    session_file = temp_dir / SESSION_FILE
    assert session_file.exists()


def test_start_session_with_stale_session(temp_dir, monkeypatch):
    """Test starting session when stale session exists (crash recovery)."""
    monkeypatch.chdir(temp_dir)

    # Create stale session file (last activity 10 minutes ago)
    old_state = SessionState(
        session_id="session-old",
        started_at=datetime.now() - timedelta(minutes=20),
        last_activity=datetime.now() - timedelta(minutes=10),
        working_directory=str(temp_dir),
        project_name="old-project",
        language="go",
        turn_count=5,
        corrections=[],
        tools_used=[],
        modified_files=[],
        status="active"
    )

    session_file = temp_dir / SESSION_FILE
    _write_session_state(old_state, session_file)

    # Start new session (should detect crash)
    with patch("cerberus.memory.session_lifecycle._handle_crashed_session") as mock_handle:
        state = start_session(working_directory=str(temp_dir))

        # Crash handler should have been called
        mock_handle.assert_called_once()
        old_session_id = mock_handle.call_args[0][0].session_id
        assert old_session_id == "session-old"

    # New session should be created
    assert state.session_id != "session-old"
    assert state.session_id.startswith("session-")


def test_start_session_with_recent_session(temp_dir, monkeypatch):
    """Test starting session when recent active session exists (no crash)."""
    monkeypatch.chdir(temp_dir)

    # Create recent session file (last activity 1 minute ago)
    recent_state = SessionState(
        session_id="session-recent",
        started_at=datetime.now() - timedelta(minutes=2),
        last_activity=datetime.now() - timedelta(minutes=1),
        working_directory=str(temp_dir),
        project_name="recent-project",
        language="typescript",
        turn_count=2,
        corrections=[],
        tools_used=[],
        modified_files=[],
        status="active"
    )

    session_file = temp_dir / SESSION_FILE
    _write_session_state(recent_state, session_file)

    # Start new session (should NOT detect crash since recent)
    with patch("cerberus.memory.session_lifecycle._handle_crashed_session") as mock_handle:
        state = start_session(working_directory=str(temp_dir))

        # Crash handler should NOT have been called
        mock_handle.assert_not_called()

    # New session should be created anyway
    assert state.session_id != "session-recent"


# ============================================================================
# Session End Tests
# ============================================================================

def test_end_session(temp_dir, monkeypatch):
    """Test ending active session."""
    monkeypatch.chdir(temp_dir)

    # Start session
    start_state = start_session(working_directory=str(temp_dir), project_name="test")

    # End session
    end_state = end_session("explicit", working_directory=str(temp_dir))

    assert end_state is not None
    assert end_state.session_id == start_state.session_id
    assert end_state.status == "ended"

    # Session file should be deleted
    session_file = temp_dir / SESSION_FILE
    assert not session_file.exists()


def test_end_session_no_active_session(temp_dir, monkeypatch):
    """Test ending when no active session exists."""
    monkeypatch.chdir(temp_dir)

    end_state = end_session("explicit", working_directory=str(temp_dir))

    assert end_state is None


# ============================================================================
# Activity Tracking Tests
# ============================================================================

def test_update_session_activity_turn(temp_dir, monkeypatch):
    """Test updating session with turn activity."""
    monkeypatch.chdir(temp_dir)

    # Start session
    state = start_session(working_directory=str(temp_dir))
    initial_turn_count = state.turn_count

    # Update activity
    update_session_activity("turn", working_directory=str(temp_dir))

    # Load and check
    updated_state = _load_session_state(Path(str(temp_dir)) / SESSION_FILE)
    assert updated_state.turn_count == initial_turn_count + 1


def test_update_session_activity_correction(temp_dir, mock_correction_candidate, monkeypatch):
    """Test updating session with correction."""
    monkeypatch.chdir(temp_dir)

    # Start session
    start_session(working_directory=str(temp_dir))

    # Update activity with correction
    update_session_activity(
        "correction",
        {"candidate": mock_correction_candidate},
        working_directory=str(temp_dir)
    )

    # Load and check
    state = _load_session_state(Path(str(temp_dir)) / SESSION_FILE)
    assert len(state.corrections) == 1
    assert state.corrections[0].user_message == "Don't use global variables"


def test_update_session_activity_tool_use(temp_dir, monkeypatch):
    """Test updating session with tool use."""
    monkeypatch.chdir(temp_dir)

    # Start session
    start_session(working_directory=str(temp_dir))

    # Update with tool uses
    update_session_activity("tool_use", {"tool": "Read"}, working_directory=str(temp_dir))
    update_session_activity("tool_use", {"tool": "Edit"}, working_directory=str(temp_dir))
    update_session_activity("tool_use", {"tool": "Read"}, working_directory=str(temp_dir))  # Duplicate

    # Load and check
    state = _load_session_state(Path(str(temp_dir)) / SESSION_FILE)
    assert "Read" in state.tools_used
    assert "Edit" in state.tools_used
    # Duplicates not added
    assert state.tools_used.count("Read") == 1


def test_update_session_activity_file_modified(temp_dir, monkeypatch):
    """Test updating session with modified files."""
    monkeypatch.chdir(temp_dir)

    # Start session
    start_session(working_directory=str(temp_dir))

    # Update with file modifications
    update_session_activity("file_modified", {"file_path": "main.py"}, working_directory=str(temp_dir))
    update_session_activity("file_modified", {"file_path": "utils.py"}, working_directory=str(temp_dir))

    # Load and check
    state = _load_session_state(Path(str(temp_dir)) / SESSION_FILE)
    assert "main.py" in state.modified_files
    assert "utils.py" in state.modified_files


# ============================================================================
# Crash Detection Tests
# ============================================================================

def test_detect_crash_stale_session(temp_dir, monkeypatch):
    """Test crash detection with stale session."""
    monkeypatch.chdir(temp_dir)

    # Create stale session (last activity 10 minutes ago)
    old_state = SessionState(
        session_id="session-stale",
        started_at=datetime.now() - timedelta(minutes=15),
        last_activity=datetime.now() - timedelta(minutes=10),
        working_directory=str(temp_dir),
        project_name="test",
        language="python",
        turn_count=5,
        status="active"
    )

    session_file = temp_dir / SESSION_FILE
    _write_session_state(old_state, session_file)

    # Detect crash
    crashed_state = detect_crash(working_directory=str(temp_dir))

    assert crashed_state is not None
    assert crashed_state.session_id == "session-stale"


def test_detect_crash_no_crash(temp_dir, monkeypatch):
    """Test crash detection with recent active session."""
    monkeypatch.chdir(temp_dir)

    # Create recent session (last activity 1 minute ago)
    recent_state = SessionState(
        session_id="session-active",
        started_at=datetime.now() - timedelta(minutes=2),
        last_activity=datetime.now() - timedelta(minutes=1),
        working_directory=str(temp_dir),
        project_name="test",
        language="python",
        turn_count=2,
        status="active"
    )

    session_file = temp_dir / SESSION_FILE
    _write_session_state(recent_state, session_file)

    # Detect crash (should be None)
    crashed_state = detect_crash(working_directory=str(temp_dir))

    assert crashed_state is None


def test_detect_crash_no_session_file(temp_dir):
    """Test crash detection when no session file exists."""
    crashed_state = detect_crash(working_directory=str(temp_dir))

    assert crashed_state is None


# ============================================================================
# Auto-Recovery Tests
# ============================================================================

@patch("cerberus.memory.storage.MemoryStorage")
@patch("cerberus.memory.proposal_engine.ProposalEngine")
@patch("cerberus.memory.semantic_analyzer.SemanticAnalyzer")
def test_auto_recover_crash_with_corrections(
    mock_semantic,
    mock_engine,
    mock_storage,
    mock_correction_candidate
):
    """Test auto-recovery with corrections."""
    # Create crashed state with corrections
    crashed_state = SessionState(
        session_id="session-crashed",
        started_at=datetime.now() - timedelta(minutes=10),
        last_activity=datetime.now() - timedelta(minutes=5),
        working_directory="/tmp/test",
        project_name="test",
        language="python",
        turn_count=5,
        corrections=[mock_correction_candidate],
        status="crashed"
    )

    # Mock clustering
    mock_cluster = MagicMock()
    mock_analyzed = MagicMock()
    mock_analyzed.clusters = [mock_cluster]
    mock_semantic_instance = MagicMock()
    mock_semantic_instance.cluster_corrections.return_value = mock_analyzed
    mock_semantic.return_value = mock_semantic_instance

    # Mock proposals
    mock_proposal_high = MagicMock()
    mock_proposal_high.confidence = 0.95
    mock_proposal_low = MagicMock()
    mock_proposal_low.confidence = 0.7

    mock_engine_instance = MagicMock()
    mock_engine_instance.generate_proposals.return_value = [
        mock_proposal_high,
        mock_proposal_low
    ]
    mock_engine.return_value = mock_engine_instance

    # Mock storage
    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance

    # Run recovery
    recovery = auto_recover_crash(crashed_state)

    assert recovery.auto_recovered is True
    assert len(recovery.recovery_actions) == 2  # High confidence + remaining
    assert "auto-approved 1 high-confidence" in recovery.recovery_actions[0]
    assert "1 proposal(s) require manual review" in recovery.recovery_actions[1]

    # Storage should be called with high-confidence only
    mock_storage_instance.store_batch.assert_called_once()


def test_auto_recover_crash_no_corrections():
    """Test auto-recovery with no corrections."""
    crashed_state = SessionState(
        session_id="session-no-corrections",
        started_at=datetime.now(),
        last_activity=datetime.now(),
        working_directory="/tmp/test",
        project_name="test",
        language="python",
        turn_count=0,
        corrections=[],
        status="crashed"
    )

    recovery = auto_recover_crash(crashed_state)

    assert recovery.auto_recovered is False
    assert len(recovery.recovery_actions) == 0


# ============================================================================
# Idle Timeout Tests
# ============================================================================

def test_check_idle_timeout_idle(temp_dir, monkeypatch):
    """Test idle timeout detection when session is idle."""
    monkeypatch.chdir(temp_dir)

    # Create session with old last_activity
    old_state = SessionState(
        session_id="session-idle",
        started_at=datetime.now() - timedelta(minutes=35),
        last_activity=datetime.now() - timedelta(minutes=35),
        working_directory=str(temp_dir),
        project_name="test",
        language="python",
        turn_count=1,
        status="active"
    )

    session_file = temp_dir / SESSION_FILE
    _write_session_state(old_state, session_file)

    # Check idle (30 minute timeout)
    is_idle = check_idle_timeout(timeout_minutes=30, working_directory=str(temp_dir))

    assert is_idle is True


def test_check_idle_timeout_active(temp_dir, monkeypatch):
    """Test idle timeout detection when session is active."""
    monkeypatch.chdir(temp_dir)

    # Create session with recent last_activity
    active_state = SessionState(
        session_id="session-active",
        started_at=datetime.now() - timedelta(minutes=10),
        last_activity=datetime.now() - timedelta(minutes=2),
        working_directory=str(temp_dir),
        project_name="test",
        language="python",
        turn_count=5,
        status="active"
    )

    session_file = temp_dir / SESSION_FILE
    _write_session_state(active_state, session_file)

    # Check idle (30 minute timeout)
    is_idle = check_idle_timeout(timeout_minutes=30, working_directory=str(temp_dir))

    assert is_idle is False


def test_check_idle_timeout_no_session(temp_dir):
    """Test idle timeout when no session exists."""
    is_idle = check_idle_timeout(timeout_minutes=30, working_directory=str(temp_dir))

    assert is_idle is False


# ============================================================================
# Session Info Tests
# ============================================================================

def test_get_session_state_info(temp_dir, monkeypatch):
    """Test getting session state info."""
    monkeypatch.chdir(temp_dir)

    # Start session
    state = start_session(
        working_directory=str(temp_dir),
        project_name="test-project",
        language="python"
    )

    # Get info
    info = get_session_state_info(working_directory=str(temp_dir))

    assert info is not None
    assert info["session_id"] == state.session_id
    assert info["project_name"] == "test-project"
    assert info["language"] == "python"
    assert info["turn_count"] == 0
    assert info["correction_count"] == 0
    assert "duration_minutes" in info
    assert "idle_minutes" in info


def test_get_session_state_info_no_session(temp_dir):
    """Test getting session info when no active session."""
    info = get_session_state_info(working_directory=str(temp_dir))

    assert info is None


# ============================================================================
# Manual Recovery Tests
# ============================================================================

def test_list_crashed_sessions(temp_dir, monkeypatch):
    """Test listing crashed sessions."""
    monkeypatch.chdir(temp_dir)

    # Create stale session
    from cerberus.memory.session_analyzer import CorrectionCandidate

    crashed_state = SessionState(
        session_id="session-crashed",
        started_at=datetime.now() - timedelta(minutes=20),
        last_activity=datetime.now() - timedelta(minutes=10),
        working_directory=str(temp_dir),
        project_name="test",
        language="python",
        turn_count=5,
        corrections=[CorrectionCandidate(
            turn_number=1,
            user_message="Test correction",
            ai_response="Generated code",
            correction_type="rule",
            confidence=0.9,
            context_before=[]
        )],
        status="active"
    )

    session_file = temp_dir / SESSION_FILE
    _write_session_state(crashed_state, session_file)

    # List crashed sessions
    sessions = list_crashed_sessions(working_directory=str(temp_dir))

    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "session-crashed"
    assert sessions[0]["correction_count"] == 1


def test_list_crashed_sessions_none(temp_dir):
    """Test listing crashed sessions when none exist."""
    sessions = list_crashed_sessions(working_directory=str(temp_dir))

    assert len(sessions) == 0


@patch("cerberus.memory.session_lifecycle.auto_recover_crash")
def test_recover_crashed_session_success(mock_auto_recover, temp_dir, monkeypatch):
    """Test successful session recovery."""
    monkeypatch.chdir(temp_dir)

    # Create crashed session
    crashed_state = SessionState(
        session_id="session-to-recover",
        started_at=datetime.now() - timedelta(minutes=10),
        last_activity=datetime.now() - timedelta(minutes=10),
        working_directory=str(temp_dir),
        project_name="test",
        language="python",
        turn_count=3,
        corrections=[MagicMock()],
        status="active"
    )

    session_file = temp_dir / SESSION_FILE
    _write_session_state(crashed_state, session_file)

    # Mock recovery
    mock_recovery = MagicMock()
    mock_recovery.auto_recovered = True
    mock_auto_recover.return_value = mock_recovery

    # Recover
    success = recover_crashed_session("session-to-recover", working_directory=str(temp_dir))

    assert success is True
    mock_auto_recover.assert_called_once()
    assert not session_file.exists()  # Cleaned up


def test_recover_crashed_session_discard(temp_dir, monkeypatch):
    """Test discarding crashed session."""
    monkeypatch.chdir(temp_dir)

    # Create crashed session
    crashed_state = SessionState(
        session_id="session-to-discard",
        started_at=datetime.now() - timedelta(minutes=10),
        last_activity=datetime.now() - timedelta(minutes=10),
        working_directory=str(temp_dir),
        project_name="test",
        language="python",
        turn_count=1,
        status="active"
    )

    session_file = temp_dir / SESSION_FILE
    _write_session_state(crashed_state, session_file)

    # Discard
    success = recover_crashed_session(
        "session-to-discard",
        discard=True,
        working_directory=str(temp_dir)
    )

    assert success is True
    assert not session_file.exists()  # Cleaned up


def test_recover_crashed_session_not_found(temp_dir):
    """Test recovering when session doesn't exist."""
    success = recover_crashed_session("nonexistent-session", working_directory=str(temp_dir))

    assert success is False


# ============================================================================
# File Locking Tests
# ============================================================================

def test_write_read_session_state(temp_dir, mock_session_state):
    """Test writing and reading session state with locking."""
    session_file = temp_dir / SESSION_FILE

    # Write
    _write_session_state(mock_session_state, session_file)

    assert session_file.exists()

    # Read
    loaded_state = _load_session_state(session_file)

    assert loaded_state.session_id == mock_session_state.session_id
    assert loaded_state.project_name == mock_session_state.project_name
    assert loaded_state.turn_count == mock_session_state.turn_count
