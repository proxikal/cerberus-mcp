"""
Phase 9.6: File Watcher Integration for Daemon.
Phase 13.5: Added background blueprint regeneration.

Integrates the existing filesystem watcher into the daemon server
for automatic index updates and blueprint regeneration.
"""

import threading
import time
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
    Phase 13.5: Added background blueprint regeneration.
    """

    def __init__(
        self,
        project_path: Path,
        index_path: Path,
        debounce_delay: float = 2.0,
        auto_blueprint: bool = False,
    ):
        """
        Initialize daemon watcher.

        Args:
            project_path: Path to project to watch
            index_path: Path to index file
            debounce_delay: Seconds to wait after last event before updating
            auto_blueprint: Enable background blueprint regeneration (Phase 13.5)
        """
        self.project_path = project_path.resolve()
        self.index_path = index_path.resolve()
        self.debounce_delay = debounce_delay
        self.auto_blueprint = auto_blueprint

        self.observer: Optional[Observer] = None
        self.event_handler: Optional[CerberusEventHandler] = None
        self.running = False

        # Phase 13.5: Blueprint regeneration
        self.blueprint_watcher = None
        self.blueprint_regen_thread = None

        logger.debug(
            f"DaemonWatcher initialized for {self.project_path} "
            f"(auto_blueprint={auto_blueprint})"
        )

    def start(self) -> bool:
        """
        Start watching filesystem.

        Returns:
            True if started successfully

        Phase 9.6: Start filesystem monitoring thread
        Phase 13.5: Start blueprint regeneration thread
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

            # Phase 13.5: Start blueprint regeneration if enabled
            if self.auto_blueprint:
                self._start_blueprint_regeneration()

            self.running = True
            logger.info(
                f"Watcher started for {self.project_path} "
                f"(auto_blueprint={self.auto_blueprint})"
            )
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

        stats = {
            "running": self.running,
            "events_processed": self.event_handler.events_processed,
            "updates_triggered": self.event_handler.updates_triggered,
            "last_update_time": self.event_handler.last_update_time,
            "project_path": str(self.project_path),
        }

        # Phase 13.5: Add blueprint regeneration stats
        if self.blueprint_watcher:
            stats["blueprint_regeneration"] = self.blueprint_watcher.get_stats()

        return stats

    def _start_blueprint_regeneration(self):
        """
        Start background blueprint regeneration thread.

        Phase 13.5: Background blueprint regeneration
        """
        try:
            from ..blueprint.blueprint_watcher import BlueprintWatcher

            # Create blueprint watcher
            self.blueprint_watcher = BlueprintWatcher(
                index_path=self.index_path,
                project_root=self.project_path,
                regeneration_interval=300.0,  # 5 minutes
                min_access_count=5
            )

            # Hook into filesystem events to track modifications
            original_on_any_event = self.event_handler.on_any_event

            def wrapped_on_any_event(event):
                # Call original handler
                original_on_any_event(event)

                # Notify blueprint watcher of file changes
                if not event.is_directory and hasattr(event, 'src_path'):
                    self.blueprint_watcher.on_file_modified(event.src_path)

            self.event_handler.on_any_event = wrapped_on_any_event

            # Start regeneration thread
            def regeneration_loop():
                """Background loop for blueprint regeneration."""
                logger.info("Blueprint regeneration thread started")
                while self.running:
                    try:
                        if self.blueprint_watcher:
                            self.blueprint_watcher.regenerate_hot_blueprints()
                    except Exception as e:
                        logger.error(f"Error in blueprint regeneration loop: {e}")

                    # Sleep for interval (check every 30 seconds if it's time to regenerate)
                    time.sleep(30)

                logger.info("Blueprint regeneration thread stopped")

            self.blueprint_regen_thread = threading.Thread(
                target=regeneration_loop,
                daemon=True,
                name="BlueprintRegenerationThread"
            )
            self.blueprint_regen_thread.start()

            logger.info("Background blueprint regeneration enabled")

        except Exception as e:
            logger.error(f"Failed to start blueprint regeneration: {e}")


def create_daemon_watcher(
    project_path: Path,
    index_path: Path,
    auto_start: bool = True,
    auto_blueprint: bool = False,
) -> Optional[DaemonWatcher]:
    """
    Create and optionally start a daemon watcher.

    Args:
        project_path: Path to project to watch
        index_path: Path to index file
        auto_start: Start watcher immediately (default: True)
        auto_blueprint: Enable background blueprint regeneration (Phase 13.5)

    Returns:
        DaemonWatcher instance or None if creation fails

    Phase 9.6: Factory function for daemon integration
    Phase 13.5: Added auto_blueprint parameter
    """
    try:
        watcher = DaemonWatcher(
            project_path=project_path,
            index_path=index_path,
            debounce_delay=WATCHER_CONFIG.get("debounce_delay", 2.0),
            auto_blueprint=auto_blueprint,
        )

        if auto_start:
            if not watcher.start():
                logger.warning("Failed to auto-start watcher")
                return None

        return watcher

    except Exception as e:
        logger.error(f"Failed to create daemon watcher: {e}")
        return None
