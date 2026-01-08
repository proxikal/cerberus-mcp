"""
Public API for the watcher subsystem.

Facade for starting, stopping, and managing the background watcher daemon.
"""

from pathlib import Path
from typing import Optional
from loguru import logger

from ..schemas import WatcherStatus
from .daemon import (
    is_watcher_running,
    start_watcher_daemon,
    stop_watcher_daemon,
    get_watcher_status,
)
from .config import WATCHER_CONFIG


def start_watcher(
    project_path: Path,
    index_path: Path,
    force: bool = False,
) -> int:
    """
    Start the background watcher daemon for a project.

    Args:
        project_path: Path to project to watch
        index_path: Path to index file to keep updated
        force: Restart even if already running

    Returns:
        PID of watcher daemon

    Raises:
        RuntimeError: If watcher fails to start
    """
    project_path = project_path.resolve()
    index_path = index_path.resolve()

    # Check if already running
    if is_watcher_running(project_path):
        if not force:
            status = get_watcher_status(project_path)
            logger.info(f"Watcher already running (PID: {status.pid})")
            return status.pid
        else:
            # Stop existing watcher
            logger.info("Force flag set, stopping existing watcher")
            stop_watcher(project_path)

    # Start new watcher
    pid = start_watcher_daemon(project_path, index_path, background=True)
    logger.info(f"Watcher started for {project_path} (PID: {pid})")
    return pid


def stop_watcher(project_path: Path, timeout: int = 10) -> bool:
    """
    Stop the background watcher daemon for a project.

    Args:
        project_path: Path to project
        timeout: Seconds to wait for graceful shutdown

    Returns:
        True if stopped successfully
    """
    project_path = project_path.resolve()

    if not is_watcher_running(project_path):
        logger.debug(f"No watcher running for {project_path}")
        return True

    return stop_watcher_daemon(project_path, timeout=timeout)


def watcher_status(project_path: Path) -> WatcherStatus:
    """
    Get the status of the watcher daemon for a project.

    Args:
        project_path: Path to project

    Returns:
        WatcherStatus object
    """
    project_path = project_path.resolve()
    return get_watcher_status(project_path)


def ensure_watcher_running(
    project_path: Path,
    index_path: Path,
    auto_start: Optional[bool] = None,
) -> bool:
    """
    Ensure watcher is running, optionally auto-starting it.

    This is called by CLI commands to ensure the watcher is active.

    Args:
        project_path: Path to project
        index_path: Path to index file
        auto_start: Whether to auto-start if not running (default: from config)

    Returns:
        True if watcher is running (either was already or started successfully)
    """
    project_path = project_path.resolve()
    index_path = index_path.resolve()

    if auto_start is None:
        auto_start = WATCHER_CONFIG["auto_start"]

    # Check if already running
    if is_watcher_running(project_path):
        logger.debug("Watcher already running")
        return True

    # Auto-start if configured
    if auto_start:
        try:
            logger.info("Auto-starting watcher daemon...")
            start_watcher(project_path, index_path)
            return True
        except Exception as e:
            logger.warning(f"Failed to auto-start watcher: {e}")
            return False

    return False
