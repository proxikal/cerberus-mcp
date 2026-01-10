"""
Background watcher module for real-time index synchronization.

Public API for starting, stopping, and querying watcher daemon status.
"""

from .facade import start_watcher, stop_watcher, watcher_status, ensure_watcher_running
from .daemon import is_watcher_running

__all__ = [
    "start_watcher",
    "stop_watcher",
    "watcher_status",
    "ensure_watcher_running",
    "is_watcher_running",
]
