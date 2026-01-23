"""
Phase 16: Integration Specification - IPC Utilities

Inter-process communication utilities for memory system integration.

This module provides helpers for communication between:
- MCP server (Python) ↔ Agent (Claude/Gemini)
- CLI commands ↔ Memory system
- Bash hooks ↔ Python subprocess

Key features:
- JSON-based message passing
- Error handling and fallback
- Process synchronization
- Session state management
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# Message Protocol
# ============================================================================

def send_message(message: Dict[str, Any], file_path: Optional[str] = None) -> None:
    """
    Send JSON message to file or stdout.

    Used for IPC between processes (e.g., hook → subprocess).

    Args:
        message: Dictionary to send as JSON
        file_path: Optional file path to write to (uses stdout if None)
    """
    json_str = json.dumps(message, indent=2)

    if file_path:
        Path(file_path).write_text(json_str)
    else:
        print(json_str)


def receive_message(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Receive JSON message from file or stdin.

    Used for IPC between processes.

    Args:
        file_path: Optional file path to read from (uses stdin if None)

    Returns:
        Parsed JSON dictionary

    Raises:
        json.JSONDecodeError: If message is not valid JSON
        FileNotFoundError: If file_path does not exist
    """
    if file_path:
        json_str = Path(file_path).read_text()
    else:
        json_str = sys.stdin.read()

    return json.loads(json_str)


# ============================================================================
# Process Execution
# ============================================================================

def run_cli_command(
    command: List[str],
    capture_output: bool = True,
    check: bool = True,
    timeout: Optional[int] = None
) -> subprocess.CompletedProcess:
    """
    Run CLI command as subprocess.

    Args:
        command: Command and arguments as list (e.g., ["cerberus", "memory", "propose"])
        capture_output: Whether to capture stdout/stderr (default: True)
        check: Whether to raise on non-zero exit (default: True)
        timeout: Optional timeout in seconds

    Returns:
        CompletedProcess with result

    Raises:
        subprocess.CalledProcessError: If command fails and check=True
        subprocess.TimeoutExpired: If timeout exceeded
    """
    return subprocess.run(
        command,
        capture_output=capture_output,
        text=True,
        check=check,
        timeout=timeout
    )


def run_cli_command_safe(
    command: List[str],
    default_output: str = "",
    timeout: Optional[int] = None
) -> str:
    """
    Run CLI command with error handling.

    Returns output on success, default_output on failure.

    Args:
        command: Command and arguments as list
        default_output: Output to return on failure (default: "")
        timeout: Optional timeout in seconds

    Returns:
        Command stdout on success, default_output on failure
    """
    try:
        result = run_cli_command(command, timeout=timeout)
        return result.stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return default_output


# ============================================================================
# File Locking (for session state)
# ============================================================================

import fcntl
import time
from contextlib import contextmanager
from typing import IO


@contextmanager
def file_lock(file_path: str, timeout: float = 5.0):
    """
    Context manager for file locking.

    Prevents race conditions when multiple processes access session state.

    Usage:
        with file_lock("/path/to/file.json"):
            # Read/write file safely
            pass

    Args:
        file_path: Path to file to lock
        timeout: Maximum time to wait for lock (seconds)

    Raises:
        TimeoutError: If lock cannot be acquired within timeout
    """
    lock_file = Path(f"{file_path}.lock")
    lock_file.touch(exist_ok=True)

    f = open(lock_file, "w")
    start_time = time.time()

    while True:
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except IOError:
            if time.time() - start_time > timeout:
                f.close()
                raise TimeoutError(f"Could not acquire lock on {file_path}")
            time.sleep(0.1)

    try:
        yield f
    finally:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        f.close()
        try:
            lock_file.unlink()
        except OSError:
            pass


# ============================================================================
# Session State Synchronization
# ============================================================================

def read_session_state_safe(file_path: str, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Read session state file with locking.

    Args:
        file_path: Path to session state JSON file
        timeout: Lock timeout in seconds

    Returns:
        Session state dictionary, or None if file doesn't exist or lock fails
    """
    if not Path(file_path).exists():
        return None

    try:
        with file_lock(file_path, timeout=timeout):
            return json.loads(Path(file_path).read_text())
    except (TimeoutError, json.JSONDecodeError, OSError):
        return None


def write_session_state_safe(
    file_path: str,
    state: Dict[str, Any],
    timeout: float = 2.0
) -> bool:
    """
    Write session state file with locking.

    Args:
        file_path: Path to session state JSON file
        state: Session state dictionary
        timeout: Lock timeout in seconds

    Returns:
        True if write successful, False otherwise
    """
    try:
        with file_lock(file_path, timeout=timeout):
            Path(file_path).write_text(json.dumps(state, indent=2))
        return True
    except (TimeoutError, OSError):
        return False


# ============================================================================
# Environment Detection
# ============================================================================

def is_mcp_running() -> bool:
    """
    Check if MCP server is running.

    Returns:
        True if MCP server is likely running, False otherwise
    """
    # Check for MCP-related environment variables
    mcp_env_vars = [
        "MCP_SERVER_RUNNING",
        "CLAUDE_CODE_MCP",
        "CERBERUS_MCP_SERVER"
    ]

    for var in mcp_env_vars:
        if os.environ.get(var):
            return True

    # Check for running process (heuristic)
    # This is a simplified check - in production you might query the MCP server directly
    return False


def is_cli_mode() -> bool:
    """
    Check if running in CLI mode (not via MCP).

    Returns:
        True if running in CLI mode, False if running via MCP
    """
    return not is_mcp_running()


# ============================================================================
# Error Response Helpers
# ============================================================================

def error_response(error_message: str, error_type: str = "error") -> Dict[str, Any]:
    """
    Create standardized error response.

    Args:
        error_message: Human-readable error message
        error_type: Error type identifier (default: "error")

    Returns:
        Error response dictionary
    """
    return {
        "status": "error",
        "error_type": error_type,
        "error_message": error_message
    }


def success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Create standardized success response.

    Args:
        data: Response data
        message: Optional success message

    Returns:
        Success response dictionary
    """
    response = {
        "status": "success",
        "data": data
    }

    if message:
        response["message"] = message

    return response


# ============================================================================
# Import guard for platform-specific modules
# ============================================================================

import os

# Note: fcntl is only available on Unix-like systems
# For Windows support, you would need to use msvcrt or win32file
if os.name != 'posix':
    # Provide fallback for non-Unix systems
    @contextmanager
    def file_lock(file_path: str, timeout: float = 5.0):
        """Fallback file lock for non-Unix systems (no-op)."""
        yield None
