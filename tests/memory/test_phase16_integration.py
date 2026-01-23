"""
Phase 16: Integration Specification - Unit Tests

Tests for hook implementation and IPC utilities.
"""

import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

from cerberus.memory.approval_cli import ApprovalResult
from cerberus.memory.hooks import (
    HookContext,
    ProposalResult,
    detect_context,
    _find_git_repo,
    _detect_language,
    _generate_session_id,
    start_session,
    end_session,
    get_session_state,
    propose_hook,
    propose_hook_with_error_handling,
    install_hooks,
    uninstall_hooks,
    verify_hooks,
    SESSION_FILE,
    LANGUAGE_EXTENSIONS,
    HOOK_DIRS,
)

from cerberus.memory.ipc import (
    send_message,
    receive_message,
    run_cli_command,
    run_cli_command_safe,
    read_session_state_safe,
    write_session_state_safe,
    error_response,
    success_response,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_git_repo(temp_dir):
    """Create a mock git repository."""
    git_dir = temp_dir / ".git"
    git_dir.mkdir()

    # Mock git config
    config_dir = git_dir / "config"
    config_dir.write_text("[remote \"origin\"]\n\turl = git@github.com:user/test-repo.git\n")

    return temp_dir


@pytest.fixture
def mock_session_context():
    """Create a mock HookContext."""
    return HookContext(
        session_id="session-test123",
        working_directory="/tmp/test-project",
        git_repo="/tmp/test-project",
        project_name="test-project",
        language="python",
        timestamp=datetime(2026, 1, 22, 10, 30, 0)
    )


# ============================================================================
# Context Detection Tests
# ============================================================================

def test_generate_session_id():
    """Test session ID generation."""
    sid = _generate_session_id()
    assert sid.startswith("session-")
    assert len(sid) == len("session-") + 12  # 12 hex chars


def test_find_git_repo_found(mock_git_repo):
    """Test finding git repo when .git exists."""
    # Test from repo root
    result = _find_git_repo(str(mock_git_repo))
    # macOS: /var is symlink to /private/var, so resolve both paths
    assert Path(result).resolve() == Path(mock_git_repo).resolve()

    # Test from subdirectory
    subdir = mock_git_repo / "src" / "nested"
    subdir.mkdir(parents=True)
    result = _find_git_repo(str(subdir))
    # macOS: /var is symlink to /private/var, so resolve both paths
    assert Path(result).resolve() == Path(mock_git_repo).resolve()


def test_find_git_repo_not_found(temp_dir):
    """Test finding git repo when .git doesn't exist."""
    result = _find_git_repo(str(temp_dir))
    assert result is None


def test_detect_language_python(temp_dir):
    """Test language detection with Python files."""
    (temp_dir / "main.py").touch()
    (temp_dir / "utils.py").touch()
    (temp_dir / "test.js").touch()

    result = _detect_language(str(temp_dir))
    assert result == "python"


def test_detect_language_mixed(temp_dir):
    """Test language detection with mixed files (most common wins)."""
    (temp_dir / "a.js").touch()
    (temp_dir / "b.js").touch()
    (temp_dir / "c.js").touch()
    (temp_dir / "main.py").touch()

    result = _detect_language(str(temp_dir))
    assert result == "javascript"


def test_detect_language_none(temp_dir):
    """Test language detection with no code files."""
    (temp_dir / "README.md").touch()
    (temp_dir / "data.json").touch()

    result = _detect_language(str(temp_dir))
    assert result is None


@patch("cerberus.memory.hooks.subprocess.check_output")
def test_detect_context_with_git(mock_subprocess, mock_git_repo, monkeypatch):
    """Test context detection with git repo."""
    monkeypatch.chdir(mock_git_repo)

    # Mock git remote
    mock_subprocess.return_value = "git@github.com:user/awesome-project.git\n"

    # Create Python files
    (mock_git_repo / "main.py").touch()

    context = detect_context()

    assert context.session_id.startswith("session-")
    # macOS: resolve symlinks for path comparison
    assert Path(context.working_directory).resolve() == Path(mock_git_repo).resolve()
    assert Path(context.git_repo).resolve() == Path(mock_git_repo).resolve()
    assert context.project_name == "awesome-project"
    assert context.language == "python"
    assert isinstance(context.timestamp, datetime)


def test_detect_context_without_git(temp_dir, monkeypatch):
    """Test context detection without git repo."""
    monkeypatch.chdir(temp_dir)

    # Create TypeScript files
    (temp_dir / "index.ts").touch()

    context = detect_context()

    assert context.session_id.startswith("session-")
    # macOS: resolve symlinks for path comparison
    assert Path(context.working_directory).resolve() == Path(temp_dir).resolve()
    assert context.git_repo is None
    assert context.project_name == temp_dir.name
    assert context.language == "typescript"


# ============================================================================
# Session Tracking Tests
# ============================================================================

def test_start_session(temp_dir, mock_session_context, monkeypatch):
    """Test session start creates state file."""
    monkeypatch.chdir(temp_dir)
    # Update mock to use temp_dir
    mock_session_context.working_directory = str(temp_dir)
    mock_session_context.git_repo = str(temp_dir)

    context = start_session(mock_session_context)

    assert context == mock_session_context

    # Check session file created
    session_file = temp_dir / SESSION_FILE
    assert session_file.exists()

    # Check content
    state = json.loads(session_file.read_text())
    assert state["session_id"] == "session-test123"
    assert state["project_name"] == "test-project"
    assert state["language"] == "python"
    assert state["turn_count"] == 0
    assert state["corrections"] == []


def test_start_session_auto_detect(temp_dir, monkeypatch):
    """Test session start with auto-detection."""
    monkeypatch.chdir(temp_dir)
    (temp_dir / "main.py").touch()

    context = start_session()

    assert context.session_id.startswith("session-")
    # macOS: resolve symlinks for path comparison
    assert Path(context.working_directory).resolve() == Path(temp_dir).resolve()
    assert context.language == "python"

    # Check session file created
    session_file = temp_dir / SESSION_FILE
    assert session_file.exists()


def test_end_session(temp_dir, monkeypatch):
    """Test session end loads and deletes state file."""
    monkeypatch.chdir(temp_dir)

    # Create session file
    session_file = temp_dir / SESSION_FILE
    state_data = {
        "session_id": "session-abc123",
        "started_at": "2026-01-22T10:30:00",
        "project_name": "test-project",
        "corrections": [{"id": "c1", "content": "test"}]
    }
    session_file.write_text(json.dumps(state_data, indent=2))

    # End session
    state = end_session()

    assert state == state_data
    assert not session_file.exists()  # File deleted


def test_end_session_no_file(temp_dir, monkeypatch):
    """Test session end when no state file exists."""
    monkeypatch.chdir(temp_dir)

    state = end_session()

    assert state == {}


def test_get_session_state(temp_dir, monkeypatch):
    """Test getting session state without ending."""
    monkeypatch.chdir(temp_dir)

    # Create session file
    session_file = temp_dir / SESSION_FILE
    state_data = {"session_id": "session-xyz"}
    session_file.write_text(json.dumps(state_data))

    # Get state
    state = get_session_state()

    assert state == state_data
    assert session_file.exists()  # File still exists


def test_get_session_state_no_file(temp_dir, monkeypatch):
    """Test getting session state when no file exists."""
    monkeypatch.chdir(temp_dir)

    state = get_session_state()

    assert state is None


# ============================================================================
# Proposal Hook Tests
# ============================================================================

@patch("cerberus.memory.session_analyzer.SessionAnalyzer")
@patch("cerberus.memory.semantic_analyzer.SemanticAnalyzer")
@patch("cerberus.memory.proposal_engine.ProposalEngine")
@patch("cerberus.memory.approval_cli.ApprovalCLI")
@patch("cerberus.memory.storage.MemoryStorage")
def test_propose_hook_no_corrections(
    mock_storage, mock_cli, mock_engine, mock_semantic, mock_analyzer
):
    """Test propose hook when no corrections detected."""
    # Mock no corrections
    mock_analyzer_instance = MagicMock()
    mock_analyzer_instance.get_candidates.return_value = []
    mock_analyzer.return_value = mock_analyzer_instance

    result = propose_hook()

    assert result.stored_count == 0
    assert result.session_stats["candidates"] == 0
    assert result.session_stats["clusters"] == 0
    assert result.session_stats["proposals"] == 0


@patch("cerberus.memory.session_analyzer.SessionAnalyzer")
@patch("cerberus.memory.semantic_analyzer.SemanticAnalyzer")
@patch("cerberus.memory.proposal_engine.ProposalEngine")
@patch("cerberus.memory.approval_cli.ApprovalCLI")
@patch("cerberus.memory.storage.MemoryStorage")
def test_propose_hook_with_proposals(
    mock_storage, mock_cli, mock_engine, mock_semantic, mock_analyzer
):
    """Test propose hook with corrections and proposals."""
    # Mock corrections
    mock_candidate = MagicMock()
    mock_analyzer_instance = MagicMock()
    mock_analyzer_instance.get_candidates.return_value = [mock_candidate] * 5
    mock_analyzer.return_value = mock_analyzer_instance

    # Mock clusters
    mock_cluster = MagicMock()
    mock_analyzed = MagicMock()
    mock_analyzed.clusters = [mock_cluster] * 2
    mock_semantic_instance = MagicMock()
    mock_semantic_instance.cluster_corrections.return_value = mock_analyzed
    mock_semantic.return_value = mock_semantic_instance

    # Mock proposals
    mock_proposal_1 = MagicMock()
    mock_proposal_1.id = "p1"
    mock_proposal_2 = MagicMock()
    mock_proposal_2.id = "p2"
    mock_engine_instance = MagicMock()
    mock_engine_instance.generate_proposals.return_value = [mock_proposal_1, mock_proposal_2]
    mock_engine.return_value = mock_engine_instance

    # Mock CLI approval
    mock_cli_instance = MagicMock()
    mock_cli_instance.run.return_value = ApprovalResult(
        approved_ids=["p1", "p2"],
        rejected_ids=[],
        total=2,
        approved_count=2,
        rejected_count=0
    )
    mock_cli.return_value = mock_cli_instance

    # Mock storage
    mock_storage_instance = MagicMock()
    mock_storage.return_value = mock_storage_instance

    result = propose_hook(interactive=True)

    assert result.stored_count == 2
    assert result.session_stats["candidates"] == 5
    assert result.session_stats["clusters"] == 2
    assert result.session_stats["proposals"] == 2
    assert len(result.approved_ids) == 2

    # Verify storage was called
    mock_storage_instance.store_batch.assert_called_once()


@patch("cerberus.memory.hooks.propose_hook")
def test_propose_hook_with_error_handling_success(mock_propose):
    """Test error handling wrapper with successful execution."""
    mock_propose.return_value = ProposalResult(
        proposals=[],
        approved_ids=[],
        stored_count=0,
        session_stats={}
    )

    # Should not raise
    propose_hook_with_error_handling()

    mock_propose.assert_called_once()


@patch("cerberus.memory.hooks.propose_hook")
def test_propose_hook_with_error_handling_exception(mock_propose, capsys):
    """Test error handling wrapper catches exceptions."""
    mock_propose.side_effect = Exception("Test error")

    # Should not raise
    propose_hook_with_error_handling()

    captured = capsys.readouterr()
    assert "Memory proposal failed" in captured.out
    assert "Test error" in captured.out


# ============================================================================
# Hook Installation Tests
# ============================================================================

def test_install_hooks_claude_code(temp_dir, monkeypatch):
    """Test installing hooks for Claude Code."""
    # Mock hook directory
    hook_dir = temp_dir / "hooks"
    monkeypatch.setitem(HOOK_DIRS, "claude-code", str(hook_dir))

    success = install_hooks("claude-code", verbose=False)

    assert success
    assert hook_dir.exists()

    # Check session-end hook
    end_hook = hook_dir / "session-end.sh"
    assert end_hook.exists()
    assert os.access(end_hook, os.X_OK)  # Executable

    content = end_hook.read_text()
    assert "cerberus memory propose --interactive" in content


def test_install_hooks_invalid_cli():
    """Test installing hooks for invalid CLI."""
    with pytest.raises(ValueError, match="Unknown CLI"):
        install_hooks("invalid-cli")


def test_uninstall_hooks(temp_dir, monkeypatch):
    """Test uninstalling hooks."""
    # Mock hook directory with existing hook
    hook_dir = temp_dir / "hooks"
    hook_dir.mkdir()
    end_hook = hook_dir / "session-end.sh"
    end_hook.write_text("#!/bin/bash\necho test\n")

    monkeypatch.setitem(HOOK_DIRS, "claude-code", str(hook_dir))

    success = uninstall_hooks("claude-code", verbose=False)

    assert success
    assert not end_hook.exists()


def test_uninstall_hooks_no_hook(temp_dir, monkeypatch):
    """Test uninstalling when no hook exists."""
    hook_dir = temp_dir / "hooks"
    monkeypatch.setitem(HOOK_DIRS, "claude-code", str(hook_dir))

    success = uninstall_hooks("claude-code", verbose=False)

    assert success  # No error


def test_verify_hooks_success(temp_dir, monkeypatch):
    """Test hook testing when properly installed."""
    # Mock hook directory with valid hook
    hook_dir = temp_dir / "hooks"
    hook_dir.mkdir()
    end_hook = hook_dir / "session-end.sh"
    end_hook.write_text("#!/bin/bash\ncerberus memory propose --interactive\n")
    end_hook.chmod(0o755)

    monkeypatch.setitem(HOOK_DIRS, "claude-code", str(hook_dir))

    success = verify_hooks("claude-code")

    assert success


def test_verify_hooks_no_hook(temp_dir, monkeypatch):
    """Test hook testing when hook not installed."""
    hook_dir = temp_dir / "hooks"
    hook_dir.mkdir()
    monkeypatch.setitem(HOOK_DIRS, "claude-code", str(hook_dir))

    success = verify_hooks("claude-code")

    assert not success


# ============================================================================
# IPC Tests
# ============================================================================

def test_error_response():
    """Test error response creation."""
    response = error_response("Something went wrong", "validation_error")

    assert response["status"] == "error"
    assert response["error_type"] == "validation_error"
    assert response["error_message"] == "Something went wrong"


def test_success_response():
    """Test success response creation."""
    response = success_response({"key": "value"}, "Operation completed")

    assert response["status"] == "success"
    assert response["data"] == {"key": "value"}
    assert response["message"] == "Operation completed"


def test_send_message_stdout(capsys):
    """Test sending message to stdout."""
    message = {"test": "data"}

    send_message(message)

    captured = capsys.readouterr()
    assert json.loads(captured.out) == message


def test_send_message_file(temp_dir):
    """Test sending message to file."""
    message = {"test": "data"}
    file_path = temp_dir / "message.json"

    send_message(message, str(file_path))

    assert file_path.exists()
    assert json.loads(file_path.read_text()) == message


def test_receive_message_file(temp_dir):
    """Test receiving message from file."""
    message = {"test": "data"}
    file_path = temp_dir / "message.json"
    file_path.write_text(json.dumps(message))

    received = receive_message(str(file_path))

    assert received == message


def test_run_cli_command_success():
    """Test running CLI command successfully."""
    result = run_cli_command(["echo", "test"], capture_output=True)

    assert result.returncode == 0
    assert "test" in result.stdout


def test_run_cli_command_failure():
    """Test running CLI command that fails."""
    with pytest.raises(subprocess.CalledProcessError):
        run_cli_command(["false"], capture_output=True)


def test_run_cli_command_safe_success():
    """Test safe CLI command execution with success."""
    output = run_cli_command_safe(["echo", "hello"])

    assert "hello" in output


def test_run_cli_command_safe_failure():
    """Test safe CLI command execution with failure."""
    output = run_cli_command_safe(["false"], default_output="fallback")

    assert output == "fallback"


def test_write_read_session_state_safe(temp_dir):
    """Test safe session state write and read."""
    file_path = temp_dir / "session.json"
    state = {"session_id": "test", "data": [1, 2, 3]}

    # Write
    success = write_session_state_safe(str(file_path), state, timeout=1.0)
    assert success

    # Read
    read_state = read_session_state_safe(str(file_path), timeout=1.0)
    assert read_state == state


def test_read_session_state_safe_not_found(temp_dir):
    """Test safe session state read when file doesn't exist."""
    file_path = temp_dir / "nonexistent.json"

    state = read_session_state_safe(str(file_path))

    assert state is None


# ============================================================================
# Data Structure Tests
# ============================================================================

def test_hook_context_to_dict(mock_session_context):
    """Test HookContext serialization to dict."""
    data = mock_session_context.to_dict()

    assert data["session_id"] == "session-test123"
    assert data["working_directory"] == "/tmp/test-project"
    assert data["project_name"] == "test-project"
    assert data["language"] == "python"
    assert data["timestamp"] == "2026-01-22T10:30:00"


def test_proposal_result_creation():
    """Test ProposalResult creation."""
    result = ProposalResult(
        proposals=[],
        approved_ids=["p1", "p2"],
        stored_count=2,
        session_stats={"candidates": 10, "clusters": 3, "proposals": 5}
    )

    assert result.stored_count == 2
    assert len(result.approved_ids) == 2
    assert result.session_stats["candidates"] == 10
