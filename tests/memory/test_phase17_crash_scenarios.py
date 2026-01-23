"""
Phase 17: Session Lifecycle & Recovery - Integration Tests

End-to-end tests for crash detection, recovery, and lifecycle scenarios.
"""

import json
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cerberus.memory.session_lifecycle import (
    start_session,
    end_session,
    update_session_activity,
    detect_crash,
    auto_recover_crash,
    check_idle_timeout,
    recover_crashed_session,
    SessionState,
    SESSION_FILE,
)

from cerberus.memory.session_analyzer import CorrectionCandidate


# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture
def project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ============================================================================
# Full Lifecycle Integration Tests
# ============================================================================

def test_full_session_lifecycle(project_dir, monkeypatch):
    """
    Test complete session lifecycle:
    1. Start session
    2. Activity tracking
    3. Clean end
    """
    monkeypatch.chdir(project_dir)

    # 1. Start session
    state = start_session(
        working_directory=str(project_dir),
        project_name="integration-test",
        language="python"
    )

    session_id = state.session_id
    assert session_id.startswith("session-")

    session_file = project_dir / SESSION_FILE
    assert session_file.exists()

    # 2. Simulate activity
    for i in range(5):
        update_session_activity("turn", working_directory=str(project_dir))

    update_session_activity(
        "tool_use",
        {"tool": "Read"},
        working_directory=str(project_dir)
    )

    update_session_activity(
        "file_modified",
        {"file_path": "main.py"},
        working_directory=str(project_dir)
    )

    candidate = CorrectionCandidate(
        content="Always use type hints",
        confidence=0.9,
        source_turn=3,
        pattern="direct_command"
    )

    update_session_activity(
        "correction",
        {"candidate": candidate},
        working_directory=str(project_dir)
    )

    # 3. End session
    final_state = end_session("explicit", working_directory=str(project_dir))

    assert final_state.session_id == session_id
    assert final_state.turn_count == 5
    assert len(final_state.corrections) == 1
    assert "Read" in final_state.tools_used
    assert "main.py" in final_state.modified_files
    assert final_state.status == "ended"

    # Session file should be deleted
    assert not session_file.exists()


def test_crash_detection_and_recovery(project_dir, monkeypatch):
    """
    Test crash detection and recovery:
    1. Start session
    2. Simulate crash (don't end cleanly)
    3. Start new session (detects crash)
    4. Verify recovery
    """
    monkeypatch.chdir(project_dir)

    # 1. Start initial session
    state1 = start_session(
        working_directory=str(project_dir),
        project_name="crash-test",
        language="go"
    )

    session_id1 = state1.session_id

    # Add some corrections
    for i in range(3):
        candidate = CorrectionCandidate(
            content=f"Correction {i}",
            confidence=0.8 + (i * 0.05),
            source_turn=i,
            pattern="direct_command"
        )
        update_session_activity(
            "correction",
            {"candidate": candidate},
            working_directory=str(project_dir)
        )

    # 2. Simulate crash (modify last_activity to be stale)
    session_file = project_dir / SESSION_FILE
    with open(session_file, "r") as f:
        data = json.load(f)

    # Make it stale (10 minutes ago)
    stale_time = datetime.now() - timedelta(minutes=10)
    data["last_activity"] = stale_time.isoformat()

    with open(session_file, "w") as f:
        json.dump(data, f, indent=2)

    # 3. Start new session (should detect crash)
    with patch("cerberus.memory.session_lifecycle.auto_recover_crash") as mock_recover:
        mock_recovery = MagicMock()
        mock_recovery.auto_recovered = True
        mock_recovery.recovery_actions = ["auto-approved 2 proposals"]
        mock_recover.return_value = mock_recovery

        state2 = start_session(working_directory=str(project_dir))

        # Recovery should have been called
        mock_recover.assert_called_once()
        crashed_state = mock_recover.call_args[0][0]
        assert crashed_state.session_id == session_id1
        assert len(crashed_state.corrections) == 3

    # New session created
    assert state2.session_id != session_id1
    assert state2.session_id.startswith("session-")


@patch("cerberus.memory.session_lifecycle.SemanticAnalyzer")
@patch("cerberus.memory.session_lifecycle.ProposalEngine")
@patch("cerberus.memory.session_lifecycle.MemoryStorage")
def test_auto_recovery_workflow(
    mock_storage,
    mock_engine,
    mock_semantic,
    project_dir,
    monkeypatch
):
    """
    Test auto-recovery workflow:
    1. Create crashed session with corrections
    2. Run auto-recovery
    3. Verify high-confidence proposals stored
    """
    monkeypatch.chdir(project_dir)

    # 1. Create crashed session
    crashed_state = SessionState(
        session_id="session-auto-recover",
        started_at=datetime.now() - timedelta(minutes=10),
        last_activity=datetime.now() - timedelta(minutes=10),
        working_directory=str(project_dir),
        project_name="auto-recover-test",
        language="typescript",
        turn_count=10,
        corrections=[
            CorrectionCandidate(
                content="Always use const",
                confidence=0.95,
                source_turn=3,
                pattern="direct_command"
            ),
            CorrectionCandidate(
                content="Prefer arrow functions",
                confidence=0.85,
                source_turn=7,
                pattern="direct_command"
            )
        ],
        status="active"
    )

    # 2. Mock clustering
    from cerberus.memory.semantic_analyzer import CorrectionCluster, AnalyzedCorrections

    cluster1 = CorrectionCluster(
        canonical="Always use const",
        variants=["Always use const"],
        avg_confidence=0.95,
        frequency=1
    )

    cluster2 = CorrectionCluster(
        canonical="Prefer arrow functions",
        variants=["Prefer arrow functions"],
        avg_confidence=0.85,
        frequency=1
    )

    analyzed = AnalyzedCorrections(
        clusters=[cluster1, cluster2],
        compression_ratio=1.0,
        total_candidates=2
    )

    mock_semantic_instance = MagicMock()
    mock_semantic_instance.cluster_corrections.return_value = analyzed
    mock_semantic.return_value = mock_semantic_instance

    # 3. Mock proposals
    from cerberus.memory.proposal_engine import MemoryProposal

    proposal_high = MemoryProposal(
        id="p1",
        content="Always use const",
        scope="language:typescript",
        category="rule",
        confidence=0.95,
        rationale="High confidence",
        source_corrections=["Always use const"],
        priority=0.95
    )

    proposal_low = MemoryProposal(
        id="p2",
        content="Prefer arrow functions",
        scope="language:typescript",
        category="preference",
        confidence=0.85,
        rationale="Medium confidence",
        source_corrections=["Prefer arrow functions"],
        priority=0.85
    )

    mock_engine_instance = MagicMock()
    mock_engine_instance.generate_proposals.return_value = [proposal_high, proposal_low]
    mock_engine.return_value = mock_engine_instance

    # 4. Mock storage
    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance

    # Run auto-recovery
    recovery = auto_recover_crash(crashed_state)

    # Verify results
    assert recovery.auto_recovered is True
    assert len(recovery.recovery_actions) == 2

    # High-confidence proposal should be stored
    mock_storage_instance.store_batch.assert_called_once()
    stored_proposals = mock_storage_instance.store_batch.call_args[0][0]
    assert len(stored_proposals) == 1
    assert stored_proposals[0].id == "p1"  # Only high-confidence


def test_manual_recovery_workflow(project_dir, monkeypatch):
    """
    Test manual recovery workflow:
    1. Detect crashed session
    2. List crashed sessions
    3. Manually recover specific session
    """
    monkeypatch.chdir(project_dir)

    # 1. Create crashed session
    crashed_state = SessionState(
        session_id="session-manual-recover",
        started_at=datetime.now() - timedelta(minutes=15),
        last_activity=datetime.now() - timedelta(minutes=10),
        working_directory=str(project_dir),
        project_name="manual-test",
        language="python",
        turn_count=5,
        corrections=[
            CorrectionCandidate(
                content="Test correction",
                confidence=0.9,
                source_turn=2,
                pattern="direct_command"
            )
        ],
        status="active"
    )

    session_file = project_dir / SESSION_FILE
    from cerberus.memory.session_lifecycle import _write_session_state
    _write_session_state(crashed_state, session_file)

    # 2. List crashed sessions
    from cerberus.memory.session_lifecycle import list_crashed_sessions

    sessions = list_crashed_sessions(working_directory=str(project_dir))

    assert len(sessions) == 1
    assert sessions[0]["session_id"] == "session-manual-recover"
    assert sessions[0]["correction_count"] == 1

    # 3. Recover (with mock)
    with patch("cerberus.memory.session_lifecycle.auto_recover_crash") as mock_recover:
        mock_recovery = MagicMock()
        mock_recovery.auto_recovered = True
        mock_recover.return_value = mock_recovery

        success = recover_crashed_session(
            "session-manual-recover",
            working_directory=str(project_dir)
        )

        assert success is True
        mock_recover.assert_called_once()

    # Session file should be cleaned up
    assert not session_file.exists()


def test_idle_timeout_scenario(project_dir, monkeypatch):
    """
    Test idle timeout scenario:
    1. Start session
    2. Simulate long idle period
    3. Check timeout triggers
    """
    monkeypatch.chdir(project_dir)

    # 1. Start session
    state = start_session(working_directory=str(project_dir))

    session_file = project_dir / SESSION_FILE

    # 2. Simulate long idle (35 minutes)
    with open(session_file, "r") as f:
        data = json.load(f)

    idle_time = datetime.now() - timedelta(minutes=35)
    data["last_activity"] = idle_time.isoformat()

    with open(session_file, "w") as f:
        json.dump(data, f, indent=2)

    # 3. Check timeout
    is_idle = check_idle_timeout(timeout_minutes=30, working_directory=str(project_dir))

    assert is_idle is True


def test_discard_crashed_session(project_dir, monkeypatch):
    """
    Test discarding crashed session without processing.
    """
    monkeypatch.chdir(project_dir)

    # Create crashed session
    crashed_state = SessionState(
        session_id="session-discard",
        started_at=datetime.now() - timedelta(minutes=10),
        last_activity=datetime.now() - timedelta(minutes=10),
        working_directory=str(project_dir),
        project_name="discard-test",
        language="python",
        turn_count=2,
        corrections=[
            CorrectionCandidate(
                content="Test",
                confidence=0.8,
                source_turn=1,
                pattern="direct_command"
            )
        ],
        status="active"
    )

    session_file = project_dir / SESSION_FILE
    from cerberus.memory.session_lifecycle import _write_session_state
    _write_session_state(crashed_state, session_file)

    # Discard session
    success = recover_crashed_session(
        "session-discard",
        discard=True,
        working_directory=str(project_dir)
    )

    assert success is True
    assert not session_file.exists()


def test_multiple_sessions_same_directory(project_dir, monkeypatch):
    """
    Test handling multiple sessions in same directory (sequential).
    """
    monkeypatch.chdir(project_dir)

    # Session 1
    state1 = start_session(working_directory=str(project_dir), project_name="session1")
    session_id1 = state1.session_id

    update_session_activity("turn", working_directory=str(project_dir))
    update_session_activity("turn", working_directory=str(project_dir))

    final_state1 = end_session("explicit", working_directory=str(project_dir))
    assert final_state1.session_id == session_id1
    assert final_state1.turn_count == 2

    # Session 2 (after Session 1 ended)
    state2 = start_session(working_directory=str(project_dir), project_name="session2")
    session_id2 = state2.session_id

    assert session_id2 != session_id1

    update_session_activity("turn", working_directory=str(project_dir))

    final_state2 = end_session("explicit", working_directory=str(project_dir))
    assert final_state2.session_id == session_id2
    assert final_state2.turn_count == 1


def test_session_with_corrupted_state_file(project_dir, monkeypatch):
    """
    Test handling corrupted session state file.
    """
    monkeypatch.chdir(project_dir)

    # Create corrupted session file
    session_file = project_dir / SESSION_FILE
    session_file.write_text("{invalid json content")

    # Start new session (should handle corruption)
    state = start_session(working_directory=str(project_dir))

    assert state.session_id.startswith("session-")
    assert session_file.exists()

    # Should be valid JSON now
    with open(session_file, "r") as f:
        data = json.load(f)
        assert data["session_id"] == state.session_id


def test_session_activity_timestamps_updated(project_dir, monkeypatch):
    """
    Test that session timestamps are updated correctly.
    """
    monkeypatch.chdir(project_dir)

    # Start session
    state = start_session(working_directory=str(project_dir))
    started_at = state.started_at
    initial_last_activity = state.last_activity

    # Wait a bit
    time.sleep(0.1)

    # Update activity
    update_session_activity("turn", working_directory=str(project_dir))

    # Load and check
    from cerberus.memory.session_lifecycle import _load_session_state
    updated_state = _load_session_state(project_dir / SESSION_FILE)

    assert updated_state.started_at == started_at  # Should not change
    assert updated_state.last_activity > initial_last_activity  # Should update


# ============================================================================
# Error Handling Integration Tests
# ============================================================================

def test_recovery_failure_handling(project_dir, monkeypatch):
    """
    Test handling of recovery failures.
    """
    monkeypatch.chdir(project_dir)

    # Create crashed session
    crashed_state = SessionState(
        session_id="session-fail-recover",
        started_at=datetime.now() - timedelta(minutes=10),
        last_activity=datetime.now() - timedelta(minutes=10),
        working_directory=str(project_dir),
        project_name="fail-test",
        language="python",
        turn_count=3,
        corrections=[
            CorrectionCandidate(
                content="Test",
                confidence=0.9,
                source_turn=1,
                pattern="direct_command"
            )
        ],
        status="active"
    )

    # Auto-recovery with exception
    with patch("cerberus.memory.session_lifecycle.SemanticAnalyzer") as mock_semantic:
        mock_semantic.side_effect = Exception("Recovery failed")

        recovery = auto_recover_crash(crashed_state)

        # Should not crash, should log failure
        assert recovery.auto_recovered is False
        assert len(recovery.recovery_actions) == 1
        assert "auto-recovery failed" in recovery.recovery_actions[0]


def test_concurrent_session_handling(project_dir, monkeypatch):
    """
    Test that file locking prevents concurrent session corruption.
    """
    monkeypatch.chdir(project_dir)

    # Start session
    state = start_session(working_directory=str(project_dir))

    # Simulate concurrent updates (file locking should prevent corruption)
    import threading

    def update_worker():
        for _ in range(10):
            update_session_activity("turn", working_directory=str(project_dir))
            time.sleep(0.01)

    threads = [threading.Thread(target=update_worker) for _ in range(3)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Load final state
    from cerberus.memory.session_lifecycle import _load_session_state
    final_state = _load_session_state(project_dir / SESSION_FILE)

    # Should have 30 turns (3 threads * 10 updates each)
    assert final_state.turn_count == 30
