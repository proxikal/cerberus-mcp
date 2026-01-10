"""
Filesystem monitoring daemon using watchdog.

This module runs as a separate process and monitors filesystem changes.
"""

import os
import sys
import time
import signal
from pathlib import Path
from typing import Set, Optional
from collections import deque
from datetime import datetime

from loguru import logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from ..schemas import FileChange, ModifiedFile, LineRange
from ..incremental import update_index_incrementally
from .config import WATCHER_CONFIG, MONITORING_CONFIG, get_log_file_path


class CerberusEventHandler(FileSystemEventHandler):
    """
    Handles filesystem events and triggers index updates.
    """

    def __init__(
        self,
        project_path: Path,
        index_path: Path,
        debounce_delay: float = 2.0,
    ):
        """
        Initialize the event handler.

        Args:
            project_path: Path to project being watched
            index_path: Path to index file
            debounce_delay: Seconds to wait after last event before updating
        """
        self.project_path = project_path
        self.index_path = index_path
        self.debounce_delay = debounce_delay

        # Track events for debouncing
        self.pending_events: deque = deque(maxlen=WATCHER_CONFIG["max_events_per_update"])
        self.last_event_time: Optional[float] = None

        # Statistics
        self.events_processed = 0
        self.updates_triggered = 0
        self.last_update_time: Optional[float] = None

        logger.info(f"Watcher initialized for {project_path}, updating {index_path}")

    def should_ignore_path(self, path: str) -> bool:
        """
        Check if a path should be ignored based on patterns.

        Args:
            path: Path to check

        Returns:
            True if should be ignored
        """
        from fnmatch import fnmatch

        for pattern in MONITORING_CONFIG["ignore_patterns"]:
            if fnmatch(path, pattern):
                return True

        # Check if file matches watch patterns
        matches_watch_pattern = False
        for pattern in MONITORING_CONFIG["watch_patterns"]:
            if fnmatch(path, pattern):
                matches_watch_pattern = True
                break

        return not matches_watch_pattern

    def on_any_event(self, event: FileSystemEvent):
        """
        Handle any filesystem event.

        Args:
            event: Filesystem event
        """
        # Ignore directories
        if event.is_directory:
            return

        # Get relative path
        try:
            rel_path = Path(event.src_path).relative_to(self.project_path)
        except ValueError:
            # Not in project path
            return

        # Check if should ignore
        if self.should_ignore_path(str(rel_path)):
            logger.debug(f"Ignoring event for {rel_path}")
            return

        logger.debug(f"Event: {event.event_type} - {rel_path}")

        # Track event
        self.pending_events.append(event)
        self.last_event_time = time.time()
        self.events_processed += 1

    def check_and_update(self) -> bool:
        """
        Check if debounce period has passed and trigger update if needed.

        Returns:
            True if update was triggered
        """
        if not self.pending_events or self.last_event_time is None:
            return False

        # Check if debounce delay has passed
        time_since_last_event = time.time() - self.last_event_time

        if time_since_last_event < self.debounce_delay:
            # Still within debounce window
            return False

        # Debounce delay has passed - trigger update
        logger.info(f"Debounce delay passed, triggering index update ({len(self.pending_events)} events)")

        try:
            # Trigger incremental update
            # We rely on git diff to detect changes, not the filesystem events
            # The events just tell us "something changed, check git"

            from ..incremental import detect_changes

            changes = detect_changes(self.project_path, self.index_path)

            if changes and (changes.added or changes.modified or changes.deleted):
                logger.info(
                    f"Detected changes: {len(changes.added)} added, "
                    f"{len(changes.modified)} modified, {len(changes.deleted)} deleted"
                )

                # Phase 13.4: Invalidate blueprint cache for changed files
                try:
                    import sqlite3
                    from ..blueprint.cache_manager import BlueprintCache

                    # Open connection to index database
                    conn = sqlite3.connect(str(self.index_path))
                    cache = BlueprintCache(conn)

                    # Invalidate cache for all changed files
                    all_changed_files = set()
                    all_changed_files.update(changes.added)
                    all_changed_files.update(changes.modified)
                    all_changed_files.update(changes.deleted)

                    for file_path in all_changed_files:
                        # Convert to absolute path
                        abs_path = str((self.project_path / file_path).resolve())
                        cache.invalidate(abs_path)
                        logger.debug(f"Invalidated blueprint cache for: {abs_path}")

                    conn.close()
                    logger.info(f"Invalidated blueprint cache for {len(all_changed_files)} files")

                except Exception as e:
                    # Don't fail the index update if cache invalidation fails
                    logger.warning(f"Error invalidating blueprint cache: {e}")

                result = update_index_incrementally(
                    index_path=self.index_path,
                    project_path=self.project_path,
                    changes=changes,
                )

                logger.info(
                    f"Index updated: {len(result.updated_symbols)} symbols updated, "
                    f"{len(result.removed_symbols)} removed in {result.elapsed_time:.2f}s"
                )

                self.updates_triggered += 1
                self.last_update_time = time.time()
            else:
                logger.debug("No actual changes detected via git diff")

        except Exception as e:
            logger.error(f"Error updating index: {e}")
        finally:
            # Clear pending events
            self.pending_events.clear()

        return True


def run_watcher_daemon(
    project_path: Path,
    index_path: Path,
    pid_file: Path,
):
    """
    Main daemon loop for the watcher.

    Args:
        project_path: Path to project to watch
        index_path: Path to index file
        pid_file: Path to PID file
    """
    # Write PID file
    pid = os.getpid()
    pid_file.write_text(str(pid))
    logger.info(f"Watcher daemon started (PID: {pid})")

    # Set up signal handlers for graceful shutdown
    shutdown_requested = False

    def signal_handler(signum, frame):
        nonlocal shutdown_requested
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        shutdown_requested = True

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create event handler
    event_handler = CerberusEventHandler(
        project_path=project_path,
        index_path=index_path,
        debounce_delay=WATCHER_CONFIG["debounce_delay"],
    )

    # Create observer
    observer = Observer()
    observer.schedule(
        event_handler,
        str(project_path),
        recursive=MONITORING_CONFIG["recursive"],
    )

    # Start watching
    observer.start()
    logger.info(f"Watching {project_path} for changes...")

    try:
        # Main loop
        while not shutdown_requested:
            time.sleep(0.5)  # Check every 500ms

            # Check if update should be triggered
            event_handler.check_and_update()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        # Stop observer
        observer.stop()
        observer.join()

        # Clean up PID file
        pid_file.unlink(missing_ok=True)

        logger.info(
            f"Watcher daemon stopped. "
            f"Processed {event_handler.events_processed} events, "
            f"triggered {event_handler.updates_triggered} updates"
        )


if __name__ == "__main__":
    """
    Entry point when run as a module.

    Usage: python -m cerberus.watcher.filesystem_monitor --project PATH --index PATH --pid-file PATH
    """
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Cerberus filesystem watcher daemon")
    parser.add_argument("--project", type=Path, required=True, help="Project path to watch")
    parser.add_argument("--index", type=Path, required=True, help="Index file path")
    parser.add_argument("--pid-file", type=Path, required=True, help="PID file path")

    args = parser.parse_args()

    # Configure logging to file with rotation
    log_file = get_log_file_path(args.project)
    logger.remove()  # Remove default handler
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="INFO",
        rotation=WATCHER_CONFIG["log_rotation_max_bytes"],  # Rotate when file reaches max size
        retention=WATCHER_CONFIG["log_rotation_backup_count"],  # Keep N backup files
        compression="gz",  # Compress rotated logs to save space
    )

    # Run daemon
    run_watcher_daemon(
        project_path=args.project,
        index_path=args.index,
        pid_file=args.pid_file,
    )
