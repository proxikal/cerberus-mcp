"""
Phase 9.6: File Watcher Integration for Daemon.

Integrates the existing filesystem watcher into the daemon server
for automatic index updates.
"""

import threading
from pathlib import Path
from typing import Optional
from loguru import logger

from watchdog.observers import Observer
from ..watcher.filesystem_monitor import CerberusEventHandler
from ..watcher.config import WATCHER_CONFIG


class DaemonWatcher:
    """
    Manages file watching within the daemon process.

    Phase 9.6: Integrates filesystem monitoring into the daemon lifecycle.
    """

    def __init__(
        self,
        project_path: Path,
        index_path: Path,
        debounce_delay: float = 2.0,
    ):
        """
        Initialize daemon watcher.

        Args:
            project_path: Path to project to watch
            index_path: Path to index file
            debounce_delay: Seconds to wait after last event before updating
        """
        self.project_path = project_path.resolve()
        self.index_path = index_path.resolve()
        self.debounce_delay = debounce_delay

        self.observer: Optional[Observer] = None
        self.event_handler: Optional[CerberusEventHandler] = None
        self.running = False

        logger.debug(f"DaemonWatcher initialized for {self.project_path}")

    def start(self) -> bool:
        """
        Start watching filesystem.

        Returns:
            True if started successfully

        Phase 9.6: Start filesystem monitoring thread
        """
        if self.running:
            logger.debug("Watcher already running")
            return True

        try:
            # Create event handler
            self.event_handler = CerberusEventHandler(
                project_path=self.project_path,
                index_path=self.index_path,
                debounce_delay=self.debounce_delay,
            )

            # Create and start observer
            self.observer = Observer()
            self.observer.schedule(
                self.event_handler,
                str(self.project_path),
                recursive=True,
            )
            self.observer.start()

            self.running = True
            logger.info(f"Phase 9.6: Watcher started for {self.project_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to start watcher: {e}")
            return False

    def stop(self, timeout: float = 5.0) -> bool:
        """
        Stop watching filesystem.

        Args:
            timeout: Seconds to wait for graceful shutdown

        Returns:
            True if stopped successfully

        Phase 9.6: Stop filesystem monitoring thread
        """
        if not self.running:
            logger.debug("Watcher not running")
            return True

        try:
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=timeout)

            self.running = False
            logger.info("Phase 9.6: Watcher stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping watcher: {e}")
            return False

    def get_stats(self) -> dict:
        """
        Get watcher statistics.

        Returns:
            Dictionary of watcher stats

        Phase 9.6: Monitoring and debugging
        """
        if not self.event_handler:
            return {
                "running": False,
                "events_processed": 0,
                "updates_triggered": 0,
            }

        return {
            "running": self.running,
            "events_processed": self.event_handler.events_processed,
            "updates_triggered": self.event_handler.updates_triggered,
            "last_update_time": self.event_handler.last_update_time,
            "project_path": str(self.project_path),
        }


def create_daemon_watcher(
    project_path: Path,
    index_path: Path,
    auto_start: bool = True,
) -> Optional[DaemonWatcher]:
    """
    Create and optionally start a daemon watcher.

    Args:
        project_path: Path to project to watch
        index_path: Path to index file
        auto_start: Start watcher immediately (default: True)

    Returns:
        DaemonWatcher instance or None if creation fails

    Phase 9.6: Factory function for daemon integration
    """
    try:
        watcher = DaemonWatcher(
            project_path=project_path,
            index_path=index_path,
            debounce_delay=WATCHER_CONFIG.get("debounce_delay", 2.0),
        )

        if auto_start:
            if not watcher.start():
                logger.warning("Failed to auto-start watcher")
                return None

        return watcher

    except Exception as e:
        logger.error(f"Failed to create daemon watcher: {e}")
        return None
