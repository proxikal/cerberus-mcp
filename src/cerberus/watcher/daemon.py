"""
Daemon lifecycle management for the background watcher.

Handles starting, stopping, and status checking of the watcher daemon process.
"""

import os
import sys
import signal
import time
import subprocess
from pathlib import Path
from typing import Optional
from loguru import logger

from ..schemas import WatcherStatus
from .config import get_pid_file_path, get_socket_file_path, get_log_file_path, WATCHER_CONFIG


def is_watcher_running(project_path: Path) -> bool:
    """
    Check if a watcher daemon is running for the given project.

    Args:
        project_path: Path to project

    Returns:
        True if watcher is running
    """
    pid_file = get_pid_file_path(project_path)

    if not pid_file.exists():
        return False

    try:
        pid = int(pid_file.read_text().strip())

        # Check if process exists and is running
        try:
            os.kill(pid, 0)  # Signal 0 just checks if process exists
            return True
        except OSError:
            # Process doesn't exist, clean up stale PID file
            logger.debug(f"Removing stale PID file for process {pid}")
            pid_file.unlink(missing_ok=True)
            return False

    except (ValueError, IOError) as e:
        logger.debug(f"Error reading PID file: {e}")
        return False


def get_watcher_pid(project_path: Path) -> Optional[int]:
    """
    Get the PID of the running watcher daemon.

    Args:
        project_path: Path to project

    Returns:
        PID or None if not running
    """
    pid_file = get_pid_file_path(project_path)

    if not pid_file.exists():
        return None

    try:
        pid = int(pid_file.read_text().strip())

        # Verify process is actually running
        try:
            os.kill(pid, 0)
            return pid
        except OSError:
            return None

    except (ValueError, IOError):
        return None


def start_watcher_daemon(
    project_path: Path,
    index_path: Path,
    background: bool = True,
    auto_blueprint: bool = False,
) -> int:
    """
    Start the watcher daemon process.

    Args:
        project_path: Path to project to watch
        index_path: Path to index file to update
        background: Run as background daemon (default: True)
        auto_blueprint: Enable background blueprint regeneration (Phase 13.5)

    Returns:
        PID of started daemon

    Raises:
        RuntimeError: If daemon fails to start
    """
    # Check if already running
    if is_watcher_running(project_path):
        existing_pid = get_watcher_pid(project_path)
        logger.info(f"Watcher already running for {project_path} (PID: {existing_pid})")
        return existing_pid

    # Get paths
    pid_file = get_pid_file_path(project_path)
    log_file = get_log_file_path(project_path)

    # Build command to run the watcher
    # We'll run the watcher module directly
    python_executable = sys.executable
    watcher_module = "cerberus.watcher.filesystem_monitor"

    cmd = [
        python_executable,
        "-m",
        watcher_module,
        "--project", str(project_path),
        "--index", str(index_path),
        "--pid-file", str(pid_file),
    ]

    # Phase 13.5: Add auto-blueprint flag if enabled
    if auto_blueprint:
        cmd.append("--auto-blueprint")

    if background:
        # Start as background daemon
        logger.info(f"Starting watcher daemon for {project_path}")

        # Open log file for output
        log_file.parent.mkdir(parents=True, exist_ok=True)

        if WATCHER_CONFIG["log_to_file"]:
            log_fd = open(log_file, "a")
            process = subprocess.Popen(
                cmd,
                stdout=log_fd,
                stderr=subprocess.STDOUT,
                start_new_session=True,  # Detach from parent
            )
        else:
            # Discard output
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )

        # Give it a moment to start and write PID file
        time.sleep(0.5)

        # Verify it started
        if not pid_file.exists():
            raise RuntimeError("Watcher daemon failed to start (no PID file created)")

        pid = int(pid_file.read_text().strip())
        logger.info(f"Watcher daemon started (PID: {pid})")
        return pid

    else:
        # Run in foreground (for debugging)
        logger.info(f"Starting watcher in foreground for {project_path}")
        process = subprocess.Popen(cmd)
        return process.pid


def stop_watcher_daemon(project_path: Path, timeout: int = 10) -> bool:
    """
    Stop the watcher daemon for a project.

    Args:
        project_path: Path to project
        timeout: Seconds to wait for graceful shutdown

    Returns:
        True if stopped successfully
    """
    pid = get_watcher_pid(project_path)

    if pid is None:
        logger.debug(f"No watcher running for {project_path}")
        return True

    logger.info(f"Stopping watcher daemon (PID: {pid})")

    try:
        # Send SIGTERM for graceful shutdown
        os.kill(pid, signal.SIGTERM)

        # Wait for process to exit
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                os.kill(pid, 0)  # Check if still running
                time.sleep(0.1)
            except OSError:
                # Process is dead
                logger.info(f"Watcher daemon stopped (PID: {pid})")
                break
        else:
            # Timeout - force kill
            logger.warning(f"Watcher daemon did not stop gracefully, force killing (PID: {pid})")
            os.kill(pid, signal.SIGKILL)

        # Clean up PID file
        pid_file = get_pid_file_path(project_path)
        pid_file.unlink(missing_ok=True)

        # Clean up socket file
        socket_file = get_socket_file_path(project_path)
        socket_file.unlink(missing_ok=True)

        return True

    except ProcessLookupError:
        # Process already dead
        logger.debug(f"Process {pid} already dead")
        return True
    except Exception as e:
        logger.error(f"Error stopping watcher daemon: {e}")
        return False


def get_watcher_status(project_path: Path) -> WatcherStatus:
    """
    Get status of the watcher daemon for a project.

    Args:
        project_path: Path to project

    Returns:
        WatcherStatus object
    """
    pid = get_watcher_pid(project_path)

    if pid is None:
        return WatcherStatus(
            running=False,
            pid=None,
            watching=None,
            index_path=None,
            uptime=None,
            last_update=None,
            events_processed=0,
            updates_triggered=0,
        )

    # Read status from PID file metadata or status file
    # For now, return basic status
    # TODO: Implement status file or IPC to get detailed stats

    return WatcherStatus(
        running=True,
        pid=pid,
        watching=str(project_path),
        index_path=None,  # TODO: Get from daemon
        uptime=None,  # TODO: Get from daemon
        last_update=None,  # TODO: Get from daemon
        events_processed=0,  # TODO: Get from daemon
        updates_triggered=0,  # TODO: Get from daemon
    )
