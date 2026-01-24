"""
Phase 16: Integration Specification - End-to-End Integration Tests

OBSOLETE: These tests were written for JSON-based session storage.
Session storage has been migrated to SQLite (memory.db).
See tests/memory/test_session_continuity.py for modern session tests.

Full session flow tests demonstrating:
1. Session start → MCP auto-injection
2. Correction detection during session
3. Session end → Proposal hook → Storage
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip all tests in this file - they test obsolete JSON session storage
pytestmark = pytest.mark.skip(reason="Obsolete: JSON session storage replaced by SQLite. See test_session_continuity.py")

from cerberus.memory.approval_cli import ApprovalResult
from cerberus.memory.hooks import (
    propose_hook,
    detect_context,
    install_hooks,
    verify_hooks,
)


# ============================================================================
# End-to-End Integration Tests
# ============================================================================

@pytest.fixture
def project_dir():
    """Create a temporary project directory with git."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        # Initialize git repo
        git_dir = project_path / ".git"
        git_dir.mkdir()

        # Add Python files
        (project_path / "main.py").write_text("print('Hello')\n")
        (project_path / "utils.py").write_text("def helper(): pass\n")

        yield project_path


def test_full_session_flow(project_dir, monkeypatch):
    """
    Test full session lifecycle:
    1. Session start (creates state file)
    2. Work happens (corrections detected)
    3. Session end (cleanup)
    """
    monkeypatch.chdir(project_dir)

    # 1. Session Start
    context = start_session()

    assert Path(context.working_directory).resolve() == Path(project_dir).resolve()
    assert context.language == "python"

    session_file = project_dir / SESSION_FILE
    assert session_file.exists()

    state = json.loads(session_file.read_text())
    assert state["session_id"] == context.session_id
    assert state["language"] == "python"

    # 2. During Session (simulate work)
    # In real usage, SessionAnalyzer would collect corrections here

    # 3. Session End
    end_state = end_session()

    assert end_state["session_id"] == context.session_id
    assert not session_file.exists()  # Cleanup


@patch("cerberus.memory.storage.MemoryStorage")
@patch("cerberus.memory.approval_cli.ApprovalCLI")
@patch("cerberus.memory.proposal_engine.ProposalEngine")
@patch("cerberus.memory.semantic_analyzer.SemanticAnalyzer")
@patch("cerberus.memory.session_analyzer.SessionAnalyzer")
def test_propose_hook_integration(
    mock_analyzer,
    mock_semantic,
    mock_engine,
    mock_cli,
    mock_storage,
    project_dir,
    monkeypatch
):
    """
    Test proposal hook integration:
    1. Corrections detected
    2. Clustered
    3. Proposals generated
    4. User approves
    5. Stored
    """
    monkeypatch.chdir(project_dir)

    # Setup mocks for full pipeline
    from cerberus.memory.session_analyzer import CorrectionCandidate
    from cerberus.memory.semantic_analyzer import AnalyzedCorrections, CorrectionCluster
    from cerberus.memory.proposal_engine import MemoryProposal

    # Mock Phase 1: Detection
    candidates = [
        CorrectionCandidate(
        turn_number=5,
        user_message="Don't use global variables",
        ai_response="Generated code",
        correction_type="rule",
        confidence=0.9,
        context_before=[]
    ),
        CorrectionCandidate(
        turn_number=12,
        user_message="Never use global state",
        ai_response="Generated code",
        correction_type="rule",
        confidence=0.85,
        context_before=[]
    )
    ]

    mock_analyzer_instance = MagicMock()
    mock_analyzer_instance.get_candidates.return_value = candidates
    mock_analyzer.return_value = mock_analyzer_instance

    # Mock Phase 2: Clustering
    cluster = CorrectionCluster(
        canonical_text="Avoid global variables",
        variants=["Don't use global variables", "Never use global state"],
        correction_type="rule",
        frequency=2,
        confidence=0.875
    )

    analyzed = AnalyzedCorrections(
        clusters=[cluster],
        outliers=[],
        total_raw=2,
        total_clustered=2,
        compression_ratio=0.5
    )

    mock_semantic_instance = MagicMock()
    mock_semantic_instance.cluster_corrections.return_value = analyzed
    mock_semantic.return_value = mock_semantic_instance

    # Mock Phase 3: Proposals
    proposal = MemoryProposal(
        id="proposal-1",
        category="correction",
        scope="universal",
        content="Avoid global variables",
        rationale="Detected 2 similar corrections",
        source_variants=cluster.variants,
        confidence=0.875,
        priority=2
    )

    mock_engine_instance = MagicMock()
    mock_engine_instance.generate_proposals.return_value = [proposal]
    mock_engine.return_value = mock_engine_instance

    # Mock Phase 4: Approval
    mock_cli_instance = MagicMock()
    mock_cli_instance.run.return_value = ApprovalResult(
        approved_ids=["proposal-1"],
        rejected_ids=[],
        total=1,
        approved_count=1,
        rejected_count=0
    )
    mock_cli.return_value = mock_cli_instance

    # Mock Phase 5: Storage
    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance

    # Run full pipeline
    result = propose_hook(interactive=True)

    # Verify results
    assert result.stored_count == 1
    assert result.session_stats["candidates"] == 2
    assert result.session_stats["clusters"] == 1
    assert result.session_stats["proposals"] == 1
    assert "proposal-1" in result.approved_ids

    # Verify all phases called
    mock_analyzer_instance.get_candidates.assert_called_once()
    mock_semantic_instance.cluster_corrections.assert_called_once()
    mock_engine_instance.generate_proposals.assert_called_once()
    mock_cli_instance.run.assert_called_once()
    mock_storage_instance.store_batch.assert_called_once()


def test_hook_installation_workflow(tmp_path, monkeypatch):
    """
    Test hook installation workflow:
    1. Install hooks
    2. Test installation
    3. Verify hook file content
    """
    from cerberus.memory.hooks import HOOK_DIRS

    # Mock hook directory
    hook_dir = tmp_path / "hooks"
    monkeypatch.setitem(HOOK_DIRS, "claude-code", str(hook_dir))

    # 1. Install
    success = install_hooks("claude-code", verbose=False)
    assert success

    # 2. Test
    success = verify_hooks("claude-code")
    assert success

    # 3. Verify content
    end_hook = hook_dir / "session-end.sh"
    assert end_hook.exists()
    assert end_hook.stat().st_mode & 0o111  # Executable bits

    content = end_hook.read_text()
    assert "#!/bin/bash" in content
    assert "cerberus memory propose --interactive" in content


@patch("cerberus.memory.session_analyzer.SessionAnalyzer")
def test_propose_hook_batch_mode(mock_analyzer, project_dir, monkeypatch):
    """
    Test propose hook in batch mode (auto-approve high confidence).
    """
    monkeypatch.chdir(project_dir)

    # Mock no corrections
    mock_analyzer_instance = MagicMock()
    mock_analyzer_instance.get_candidates.return_value = []
    mock_analyzer.return_value = mock_analyzer_instance

    # Run in batch mode
    result = propose_hook(interactive=False, batch_threshold=0.85)

    assert result.stored_count == 0
    assert result.session_stats["candidates"] == 0


def test_context_detection_comprehensive(project_dir, monkeypatch):
    """
    Test comprehensive context detection in real project.
    """
    monkeypatch.chdir(project_dir)

    # Add more files to project
    (project_dir / "src").mkdir()
    (project_dir / "src" / "app.py").write_text("# Main app\n")
    (project_dir / "src" / "models.py").write_text("# Models\n")
    (project_dir / "tests").mkdir()
    (project_dir / "tests" / "test_app.py").write_text("# Tests\n")

    context = detect_context()

    assert Path(context.working_directory).resolve() == Path(project_dir).resolve()
    assert context.language == "python"
    assert Path(context.git_repo).resolve() == Path(project_dir).resolve()
    assert context.session_id.startswith("session-")


@patch("cerberus.memory.storage.MemoryStorage")
@patch("cerberus.memory.approval_cli.ApprovalCLI")
@patch("cerberus.memory.proposal_engine.ProposalEngine")
@patch("cerberus.memory.semantic_analyzer.SemanticAnalyzer")
@patch("cerberus.memory.session_analyzer.SessionAnalyzer")
def test_session_with_agent_proposals(
    mock_analyzer,
    mock_semantic,
    mock_engine,
    mock_cli,
    mock_storage,
    project_dir,
    monkeypatch
):
    """
    Test session that includes agent proposals (Phase 10 integration).

    This test verifies that the proposal hook can handle both:
    - User correction proposals (from Phase 1-3)
    - Agent learning proposals (from Phase 10)
    """
    monkeypatch.chdir(project_dir)

    from cerberus.memory.session_analyzer import CorrectionCandidate
    from cerberus.memory.semantic_analyzer import AnalyzedCorrections, CorrectionCluster
    from cerberus.memory.proposal_engine import MemoryProposal

    # Mock user corrections
    user_candidate = CorrectionCandidate(
        turn_number=3,
        user_message="Always use type hints",
        ai_response="Generated code",
        correction_type="rule",
        confidence=0.9,
        context_before=[]
    )

    mock_analyzer_instance = MagicMock()
    mock_analyzer_instance.get_candidates.return_value = [user_candidate]
    mock_analyzer.return_value = mock_analyzer_instance

    # Mock clustering
    cluster = CorrectionCluster(
        canonical_text="Always use type hints",
        variants=["Always use type hints"],
        correction_type="rule",
        frequency=1,
        confidence=0.9
    )

    analyzed = AnalyzedCorrections(
        clusters=[cluster],
        outliers=[],
        total_raw=1,
        total_clustered=1,
        compression_ratio=1.0
    )

    mock_semantic_instance = MagicMock()
    mock_semantic_instance.cluster_corrections.return_value = analyzed
    mock_semantic.return_value = mock_semantic_instance

    # Mock proposals (user + agent)
    user_proposal = MemoryProposal(
        id="user-1",
        category="rule",
        scope="language:python",
        content="Always use type hints",
        rationale="User directive",
        source_variants=["Always use type hints"],
        confidence=0.9,
        priority=1
    )

    # Note: In real usage, agent proposals would come from Phase 10
    # For this test, we're just verifying the hook can handle multiple proposals

    mock_engine_instance = MagicMock()
    mock_engine_instance.generate_proposals.return_value = [user_proposal]
    mock_engine.return_value = mock_engine_instance

    # Mock approval (approve user proposal)
    mock_cli_instance = MagicMock()
    mock_cli_instance.run.return_value = ApprovalResult(
        approved_ids=["user-1"],
        rejected_ids=[],
        total=1,
        approved_count=1,
        rejected_count=0
    )
    mock_cli.return_value = mock_cli_instance

    # Mock storage
    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance

    # Run pipeline
    result = propose_hook(interactive=True)

    assert result.stored_count == 1
    assert "user-1" in result.approved_ids


def test_error_recovery_during_proposal(project_dir, monkeypatch, capsys):
    """
    Test that proposal hook errors don't crash the session end.
    """
    monkeypatch.chdir(project_dir)

    from cerberus.memory.hooks import propose_hook_with_error_handling

    # Mock SessionAnalyzer to raise error
    with patch("cerberus.memory.session_analyzer.SessionAnalyzer") as mock_analyzer:
        mock_analyzer.side_effect = Exception("Simulated error")

        # Should not raise
        propose_hook_with_error_handling()

    captured = capsys.readouterr()
    assert "Memory proposal failed" in captured.out


# ============================================================================
# Multi-CLI Support Tests
# ============================================================================

@pytest.mark.parametrize("cli_name", ["claude-code", "codex-cli", "gemini-cli"])
def test_hook_installation_all_clis(cli_name, tmp_path, monkeypatch):
    """
    Test hook installation works for all supported CLIs.
    """
    from cerberus.memory.hooks import HOOK_DIRS

    # Mock hook directory
    hook_dir = tmp_path / cli_name / "hooks"
    monkeypatch.setitem(HOOK_DIRS, cli_name, str(hook_dir))

    # Install
    success = install_hooks(cli_name, verbose=False)
    assert success

    # Verify
    end_hook = hook_dir / "session-end.sh"
    assert end_hook.exists()

    content = end_hook.read_text()
    assert "cerberus memory propose" in content


# ============================================================================
# Session State Persistence Tests
# ============================================================================

def test_session_state_survives_restart(project_dir, monkeypatch):
    """
    Test that session state persists across process restart.
    """
    monkeypatch.chdir(project_dir)

    # Start session
    context1 = start_session()
    session_id = context1.session_id

    # Simulate process restart (new import)
    from cerberus.memory.hooks import get_session_state

    # Session state should still exist
    state = get_session_state()
    assert state is not None
    assert state["session_id"] == session_id

    # End session
    end_state = end_session()
    assert end_state["session_id"] == session_id

    # After end, state should be gone
    state = get_session_state()
    assert state is None
