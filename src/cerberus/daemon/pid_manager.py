"""
PID file management for the Cerberus Daemon.

Phase 9.2: Process tracking and lifecycle management.
"""

import os
from pathlib import Path
from typing import Optional
from loguru import logger


def is_daemon_running_pid(pid_file: Path) -> bool:
    """
    Check if a daemon is running based on PID file.

    Args:
        pid_file: Path to PID file

    Returns:
        True if daemon is running
    """
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


def get_daemon_pid_from_file(pid_file: Path) -> Optional[int]:
    """
    Get the PID of the running daemon.

    Args:
        pid_file: Path to PID file

    Returns:
        PID or None if not running
    """
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


def write_pid_file(pid_file: Path, pid: int) -> None:
    """
    Write PID to file.

    Args:
        pid_file: Path to PID file
        pid: Process ID to write
    """
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(pid))
    logger.debug(f"Wrote PID {pid} to {pid_file}")


def remove_pid_file(pid_file: Path) -> None:
    """
    Remove PID file.

    Args:
        pid_file: Path to PID file
    """
    pid_file.unlink(missing_ok=True)
    logger.debug(f"Removed PID file {pid_file}")


def send_signal_to_daemon(pid_file: Path, signal_num: int) -> bool:
    """
    Send a signal to the daemon process.

    Args:
        pid_file: Path to PID file
        signal_num: Signal number (e.g., signal.SIGTERM)

    Returns:
        True if signal sent successfully
    """
    pid = get_daemon_pid_from_file(pid_file)
    if pid is None:
        logger.debug("No daemon running to send signal to")
        return False

    try:
        os.kill(pid, signal_num)
        logger.debug(f"Sent signal {signal_num} to process {pid}")
        return True
    except OSError as e:
        logger.error(f"Failed to send signal to process {pid}: {e}")
        return False
