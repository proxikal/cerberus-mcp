"""
Public API for the Cerberus Daemon (Cognitive Cortex).

Phase 9: Daemon lifecycle management and core operations.

This facade provides the entry point for:
- Starting/stopping the daemon server
- Health checks and status queries
- Session management
- Client communication
"""

from pathlib import Path
from typing import Optional, Dict, Any
import signal
import time
import requests
from loguru import logger

from .config import (
    DAEMON_CONFIG,
    SESSION_CONFIG,
    SECURITY_CONFIG,
    PERFORMANCE_TARGETS,
    get_pid_file_path,
)
from .pid_manager import (
    is_daemon_running_pid,
    get_daemon_pid_from_file,
    send_signal_to_daemon,
)
from .server import run_daemon_server


# === Daemon Lifecycle Management ===

def start_daemon(
    index_path: Path,
    port: Optional[int] = None,
    socket_path: Optional[Path] = None,
    allow_write: bool = False,
    detach: bool = True,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Start the Cerberus Daemon server.

    Args:
        index_path: Path to the SQLite index database
        port: HTTP port (overrides config, used if socket unavailable)
        socket_path: Unix socket path (overrides config)
        allow_write: Enable write operations (default: read-only)
        detach: Run as background daemon (default: True)
        project_path: Optional project path (for multi-project support)

    Returns:
        Dict with daemon status: {
            "status": "started" | "already_running" | "failed",
            "pid": int,
            "socket_path": str | None,
            "port": int,
            "mode": "http",
        }

    Phase: 9.2 (Implementation complete)
    """
    logger.info(f"start_daemon called with index_path={index_path}")

    # Check if already running
    pid_file = get_pid_file_path(project_path)
    if is_daemon_running_pid(pid_file):
        existing_pid = get_daemon_pid_from_file(pid_file)
        logger.info(f"Daemon already running (PID: {existing_pid})")
        return {
            "status": "already_running",
            "pid": existing_pid,
            "socket_path": None,  # TODO Phase 9.3: Unix socket support
            "port": port or DAEMON_CONFIG["port"],
            "mode": "http",
        }

    # Resolve index path
    index_path = index_path.resolve()
    if not index_path.exists():
        logger.error(f"Index not found: {index_path}")
        return {
            "status": "failed",
            "error": f"Index not found: {index_path}",
            "pid": None,
            "socket_path": None,
            "port": None,
            "mode": "http",
        }

    # Start daemon server
    try:
        pid = run_daemon_server(
            index_path=index_path,
            host=DAEMON_CONFIG["host"],
            port=port or DAEMON_CONFIG["port"],
            background=detach,
            project_path=project_path,
        )

        # Wait a moment for server to start
        time.sleep(0.5)

        logger.info(f"Daemon started successfully (PID: {pid})")
        return {
            "status": "started",
            "pid": pid,
            "socket_path": None,  # TODO Phase 9.3: Unix socket support
            "port": port or DAEMON_CONFIG["port"],
            "mode": "http",
        }

    except Exception as e:
        logger.error(f"Failed to start daemon: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "pid": None,
            "socket_path": None,
            "port": None,
            "mode": "http",
        }


def stop_daemon(timeout: float = None, project_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Stop the running Cerberus Daemon.

    Args:
        timeout: Graceful shutdown timeout in seconds (default: from config)
        project_path: Optional project path

    Returns:
        Dict with status: {
            "status": "stopped" | "not_running" | "timeout",
            "uptime_seconds": float | None,
        }

    Phase: 9.2 (Implementation complete)
    """
    logger.info("stop_daemon called")

    timeout = timeout or DAEMON_CONFIG["shutdown_timeout"]
    pid_file = get_pid_file_path(project_path)

    # Check if daemon is running
    if not is_daemon_running_pid(pid_file):
        logger.info("Daemon not running")
        return {
            "status": "not_running",
            "uptime_seconds": None,
        }

    # Get status before stopping (for uptime)
    status_before = daemon_status(project_path)
    uptime = status_before.get("uptime_seconds")

    # Send SIGTERM for graceful shutdown
    if send_signal_to_daemon(pid_file, signal.SIGTERM):
        # Wait for process to exit
        start_wait = time.time()
        while time.time() - start_wait < timeout:
            if not is_daemon_running_pid(pid_file):
                logger.info("Daemon stopped gracefully")
                return {
                    "status": "stopped",
                    "uptime_seconds": uptime,
                }
            time.sleep(0.1)

        # Timeout: force kill
        logger.warning(f"Daemon did not stop within {timeout}s, sending SIGKILL")
        send_signal_to_daemon(pid_file, signal.SIGKILL)
        return {
            "status": "timeout",
            "uptime_seconds": uptime,
        }

    return {
        "status": "not_running",
        "uptime_seconds": None,
    }


def daemon_status(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Check the status of the Cerberus Daemon.

    Args:
        project_path: Optional project path

    Returns:
        Dict with status: {
            "running": bool,
            "pid": int | None,
            "uptime_seconds": float | None,
            "active_sessions": int,
            "memory_mb": float,
            "index_loaded": bool,
            "socket_path": str | None,
            "port": int | None,
        }

    Phase: 9.2 (Implementation complete)
    """
    logger.debug("daemon_status called")

    pid_file = get_pid_file_path(project_path)
    pid = get_daemon_pid_from_file(pid_file)

    if pid is None:
        return {
            "running": False,
            "pid": None,
            "uptime_seconds": None,
            "active_sessions": 0,
            "memory_mb": 0,
            "index_loaded": False,
            "socket_path": None,
            "port": None,
        }

    # Query daemon /status endpoint
    try:
        port = DAEMON_CONFIG["port"]
        response = requests.get(
            f"http://127.0.0.1:{port}/status",
            timeout=2.0,
        )
        if response.status_code == 200:
            status_data = response.json()
            return {
                "running": True,
                "pid": status_data.get("pid", pid),
                "uptime_seconds": status_data.get("uptime_seconds"),
                "active_sessions": status_data.get("active_sessions", 0),
                "memory_mb": status_data.get("memory_mb", 0),
                "index_loaded": status_data.get("index_loaded", False),
                "socket_path": None,
                "port": port,
            }
    except Exception as e:
        logger.debug(f"Failed to query daemon status: {e}")

    # Fallback: daemon is running but not responding
    return {
        "running": True,
        "pid": pid,
        "uptime_seconds": None,
        "active_sessions": 0,
        "memory_mb": 0,
        "index_loaded": False,
        "socket_path": None,
        "port": DAEMON_CONFIG["port"],
    }


def health_check(project_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Perform a health check on the daemon.

    Args:
        project_path: Optional project path

    Returns:
        Dict with health status: {
            "healthy": bool,
            "index_accessible": bool,
            "memory_ok": bool,
            "latency_ms": float,
        }

    Phase: 9.2 (Implementation complete)
    """
    logger.debug("health_check called")

    pid_file = get_pid_file_path(project_path)
    if not is_daemon_running_pid(pid_file):
        return {
            "healthy": False,
            "index_accessible": False,
            "memory_ok": False,
            "latency_ms": 0,
        }

    # Query daemon /health endpoint
    try:
        port = DAEMON_CONFIG["port"]
        start_time = time.time()
        response = requests.get(
            f"http://127.0.0.1:{port}/health",
            timeout=5.0,
        )
        latency_ms = (time.time() - start_time) * 1000

        if response.status_code == 200:
            health_data = response.json()
            return {
                "healthy": health_data.get("healthy", False),
                "index_accessible": health_data.get("index_loaded", False),
                "memory_ok": True,  # TODO Phase 9.10: actual memory check
                "latency_ms": latency_ms,
            }

    except Exception as e:
        logger.debug(f"Health check failed: {e}")

    return {
        "healthy": False,
        "index_accessible": False,
        "memory_ok": False,
        "latency_ms": 0,
    }


# === Client Communication ===

def is_daemon_running(project_path: Optional[Path] = None) -> bool:
    """
    Quick check if daemon is running.

    Args:
        project_path: Optional project path

    Returns:
        True if daemon is accessible, False otherwise

    Phase: 9.2 (Implementation complete)
    """
    logger.debug("is_daemon_running called")

    pid_file = get_pid_file_path(project_path)
    return is_daemon_running_pid(pid_file)


def send_rpc_request(
    method: str,
    params: Dict[str, Any],
    request_id: Optional[Any] = None,
    project_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Send a JSON-RPC request to the daemon.

    Args:
        method: RPC method name (e.g., "get_symbol", "search")
        params: Method parameters
        request_id: Optional request ID
        project_path: Optional project path

    Returns:
        JSON-RPC response dict with "result" or "error"

    Phase: 9.3 (Implementation complete)
    """
    logger.debug(f"send_rpc_request called: method={method}")

    # Check if daemon is running
    if not is_daemon_running(project_path):
        return {
            "error": {
                "code": -32000,
                "message": "Daemon not running",
            }
        }

    # Build JSON-RPC 2.0 request
    request_data = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": request_id or 1,
    }

    # Send request to daemon
    try:
        port = DAEMON_CONFIG["port"]
        response = requests.post(
            f"http://127.0.0.1:{port}/rpc",
            json=request_data,
            timeout=10.0,
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": {
                    "code": -32000,
                    "message": f"HTTP {response.status_code}",
                }
            }

    except Exception as e:
        logger.error(f"RPC request failed: {e}")
        return {
            "error": {
                "code": -32000,
                "message": f"Request failed: {str(e)}",
            }
        }


# === Utility Functions ===

def get_socket_path() -> Path:
    """
    Get the daemon socket path.

    Returns:
        Path to Unix socket or None if using HTTP mode

    Phase: 9.1
    """
    return DAEMON_CONFIG.get("socket_path")


def get_daemon_pid(project_path: Optional[Path] = None) -> Optional[int]:
    """
    Get the daemon process PID.

    Args:
        project_path: Optional project path

    Returns:
        PID if daemon is running, None otherwise

    Phase: 9.2 (Implementation complete)
    """
    logger.debug("get_daemon_pid called")

    pid_file = get_pid_file_path(project_path)
    return get_daemon_pid_from_file(pid_file)


# === Exports ===

__all__ = [
    "start_daemon",
    "stop_daemon",
    "daemon_status",
    "health_check",
    "is_daemon_running",
    "send_rpc_request",
    "get_socket_path",
    "get_daemon_pid",
]
