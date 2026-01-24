"""
Index staleness detection with caching.

Checks if the index is stale compared to git status.
Caches results to avoid excessive git command execution.
"""

import time
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger


class StalenessCache:
    """Thread-safe cache for staleness check results."""

    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self._cache: Optional[Dict[str, Any]] = None
        self._timestamp: float = 0.0

    def get(self) -> Optional[Dict[str, Any]]:
        """Get cached result if still valid."""
        if self._cache is None:
            return None

        age = time.time() - self._timestamp
        if age > self.ttl_seconds:
            return None

        return self._cache

    def set(self, result: Dict[str, Any]) -> None:
        """Cache a staleness check result."""
        self._cache = result
        self._timestamp = time.time()

    def clear(self) -> None:
        """Clear the cache."""
        self._cache = None
        self._timestamp = 0.0


# Global cache instance (60-second TTL)
_staleness_cache = StalenessCache(ttl_seconds=60)


def check_staleness(
    project_root: Path,
    index_git_commit: Optional[str] = None,
    use_cache: bool = True,
) -> Dict[str, Any]:
    """
    Check if index is stale compared to git state.

    Args:
        project_root: Path to project root
        index_git_commit: Git commit hash from index metadata
        use_cache: Whether to use cached result (default: True)

    Returns:
        {
            "is_stale": bool,
            "reason": str or None,
            "can_update": bool,  # Can run smart_update
            "uncommitted_changes": bool,
            "commit_mismatch": bool,
            "checked_at": float,  # Timestamp
        }
    """
    # Check cache first
    if use_cache:
        cached = _staleness_cache.get()
        if cached is not None:
            logger.debug(f"Using cached staleness result (age: {time.time() - cached['checked_at']:.1f}s)")
            return cached

    checked_at = time.time()

    # Check if git repository
    if not _is_git_repo(project_root):
        result = {
            "is_stale": False,
            "reason": None,
            "can_update": False,
            "uncommitted_changes": False,
            "commit_mismatch": False,
            "checked_at": checked_at,
        }
        _staleness_cache.set(result)
        return result

    # Check for uncommitted changes
    has_uncommitted = _has_uncommitted_changes(project_root)

    # Check for commit mismatch
    current_commit = _get_current_commit(project_root)
    has_commit_mismatch = False

    if index_git_commit and current_commit:
        has_commit_mismatch = current_commit != index_git_commit

    # Determine staleness
    is_stale = has_uncommitted or has_commit_mismatch

    # Determine reason
    reason = None
    if has_uncommitted and has_commit_mismatch:
        reason = "uncommitted_changes_and_new_commits"
    elif has_uncommitted:
        reason = "uncommitted_changes"
    elif has_commit_mismatch:
        reason = "new_commits"

    result = {
        "is_stale": is_stale,
        "reason": reason,
        "can_update": True,  # Can always try smart_update
        "uncommitted_changes": has_uncommitted,
        "commit_mismatch": has_commit_mismatch,
        "checked_at": checked_at,
    }

    _staleness_cache.set(result)
    logger.debug(f"Staleness check: is_stale={is_stale}, reason={reason}")
    return result


def _is_git_repo(path: Path) -> bool:
    """Check if path is in a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception as e:
        logger.debug(f"Error checking git repo: {e}")
        return False


def _has_uncommitted_changes(path: Path) -> bool:
    """
    Check if there are uncommitted changes (staged, unstaged, or untracked).

    Returns:
        True if there are any changes, False otherwise
    """
    try:
        # Check for staged + unstaged + untracked files
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            logger.warning(f"git status failed: {result.stderr}")
            return False

        # If output is non-empty, there are changes
        has_changes = len(result.stdout.strip()) > 0

        if has_changes:
            logger.debug(f"Detected uncommitted changes in {path}")

        return has_changes

    except Exception as e:
        logger.error(f"Error checking uncommitted changes: {e}")
        return False


def _get_current_commit(path: Path) -> Optional[str]:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            return result.stdout.strip()

        return None

    except Exception as e:
        logger.debug(f"Error getting current commit: {e}")
        return None


def clear_cache() -> None:
    """Clear the staleness check cache (for testing)."""
    _staleness_cache.clear()
    logger.debug("Staleness cache cleared")
