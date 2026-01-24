"""
File-based locking for index updates.

Prevents multiple processes from updating the index simultaneously.
Uses a lock file with PID and timestamp for stale lock detection.
"""

import os
import time
import json
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
from loguru import logger


class FileLockError(Exception):
    """Raised when file lock cannot be acquired."""
    pass


class FileLock:
    """
    File-based lock with timeout and stale lock detection.

    Uses a .lock file containing:
    - pid: Process ID that acquired lock
    - timestamp: When lock was acquired
    - hostname: Machine name (for multi-machine detection)
    """

    def __init__(self, lock_path: Path, timeout: float = 10.0):
        """
        Initialize file lock.

        Args:
            lock_path: Path to lock file
            timeout: Seconds to wait before assuming lock is stale
        """
        self.lock_path = lock_path
        self.timeout = timeout
        self._acquired = False

    def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire the lock.

        Args:
            blocking: If True, wait until lock available or timeout
            timeout: Override default timeout (seconds)

        Returns:
            True if lock acquired, False otherwise

        Raises:
            FileLockError: If lock cannot be acquired after timeout
        """
        if self._acquired:
            return True

        max_wait = timeout if timeout is not None else self.timeout
        start_time = time.time()

        while True:
            # Try to acquire lock
            if self._try_acquire():
                self._acquired = True
                logger.debug(f"Acquired lock: {self.lock_path}")
                return True

            # Check if lock is stale and can be broken
            if self._is_stale_lock():
                logger.warning(f"Breaking stale lock: {self.lock_path}")
                self._break_lock()
                continue

            # Non-blocking mode
            if not blocking:
                return False

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= max_wait:
                lock_info = self._read_lock_info()
                raise FileLockError(
                    f"Lock timeout after {elapsed:.1f}s. "
                    f"Lock held by PID {lock_info.get('pid', 'unknown')} "
                    f"since {lock_info.get('timestamp', 'unknown')}"
                )

            # Wait a bit before retrying
            time.sleep(0.1)

    def release(self) -> None:
        """Release the lock."""
        if not self._acquired:
            return

        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
                logger.debug(f"Released lock: {self.lock_path}")
        except Exception as e:
            logger.warning(f"Error releasing lock: {e}")
        finally:
            self._acquired = False

    def _try_acquire(self) -> bool:
        """
        Try to create lock file atomically.

        Returns:
            True if lock created, False if already exists
        """
        try:
            # Create parent directory if needed
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)

            # Try atomic file creation (fails if exists)
            fd = os.open(
                str(self.lock_path),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o644
            )

            # Write lock info
            lock_info = {
                "pid": os.getpid(),
                "timestamp": time.time(),
                "hostname": os.uname().nodename if hasattr(os, 'uname') else "unknown",
            }

            os.write(fd, json.dumps(lock_info).encode())
            os.close(fd)

            return True

        except FileExistsError:
            return False
        except Exception as e:
            logger.error(f"Error acquiring lock: {e}")
            return False

    def _read_lock_info(self) -> dict:
        """Read lock file info."""
        try:
            if not self.lock_path.exists():
                return {}

            with open(self.lock_path) as f:
                return json.load(f)

        except Exception as e:
            logger.debug(f"Error reading lock info: {e}")
            return {}

    def _is_stale_lock(self) -> bool:
        """
        Check if lock is stale (held longer than timeout).

        A lock is stale if:
        1. Lock file exists
        2. Timestamp is older than timeout
        3. Process that created it is not running (optional check)

        Returns:
            True if lock is stale and can be broken
        """
        if not self.lock_path.exists():
            return False

        lock_info = self._read_lock_info()
        if not lock_info:
            # Can't read lock file, assume it's stale
            return True

        # Check age
        lock_age = time.time() - lock_info.get("timestamp", 0)
        if lock_age < self.timeout:
            return False

        # Lock is old enough to be stale
        # Optional: check if process still exists
        lock_pid = lock_info.get("pid")
        if lock_pid and self._is_process_running(lock_pid):
            # Process still running, not stale yet
            logger.warning(
                f"Lock held by running process {lock_pid} for {lock_age:.1f}s "
                f"(timeout: {self.timeout}s)"
            )
            return False

        return True

    def _is_process_running(self, pid: int) -> bool:
        """Check if process with given PID is running."""
        try:
            # Send signal 0 to check if process exists
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _break_lock(self) -> None:
        """Force remove stale lock file."""
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
                logger.info(f"Broke stale lock: {self.lock_path}")
        except Exception as e:
            logger.error(f"Error breaking lock: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False


@contextmanager
def index_update_lock(index_path: Path, timeout: float = 10.0):
    """
    Context manager for index update locking.

    Usage:
        try:
            with index_update_lock(index_path):
                # Perform index update
                ...
        except FileLockError as e:
            # Lock timeout or acquisition failed
            logger.error(f"Could not acquire lock: {e}")

    Args:
        index_path: Path to index file
        timeout: Lock timeout in seconds

    Yields:
        FileLock instance

    Raises:
        FileLockError: If lock cannot be acquired
    """
    lock_path = index_path.with_suffix(".lock")
    lock = FileLock(lock_path, timeout=timeout)

    try:
        lock.acquire()
        yield lock
    finally:
        lock.release()
