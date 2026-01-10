"""Background blueprint regeneration.

Phase 13.5: Automatically regenerates hot blueprints when files change.
"""

import sqlite3
import time
from pathlib import Path
from typing import Set, Optional, Dict, Any

from cerberus.logging_config import logger
from ..index import load_index
from .facade import BlueprintGenerator
from .cache_manager import BlueprintCache
from .schemas import BlueprintRequest


class BlueprintWatcher:
    """Handles background regeneration of frequently-accessed blueprints."""

    def __init__(
        self,
        index_path: Path,
        project_root: Path,
        regeneration_interval: float = 300.0,  # 5 minutes
        min_access_count: int = 5
    ):
        """
        Initialize blueprint watcher.

        Args:
            index_path: Path to index database
            project_root: Project root directory
            regeneration_interval: Seconds between regeneration checks
            min_access_count: Minimum accesses to be considered "hot"
        """
        self.index_path = index_path
        self.project_root = project_root
        self.regeneration_interval = regeneration_interval
        self.min_access_count = min_access_count

        # Track last regeneration time
        self.last_regeneration = 0.0

        # Track files that have been modified (from filesystem watcher)
        self.modified_files: Set[str] = set()

        logger.info(
            f"Blueprint watcher initialized (interval: {regeneration_interval}s, "
            f"min_accesses: {min_access_count})"
        )

    def on_file_modified(self, file_path: str):
        """
        Callback when a file is modified by the filesystem watcher.

        Args:
            file_path: Absolute path to modified file
        """
        self.modified_files.add(file_path)
        logger.debug(f"File marked for potential blueprint regeneration: {file_path}")

    def should_regenerate(self) -> bool:
        """
        Check if it's time to run regeneration.

        Returns:
            True if enough time has elapsed since last regeneration
        """
        current_time = time.time()
        return (current_time - self.last_regeneration) >= self.regeneration_interval

    def regenerate_hot_blueprints(self):
        """
        Regenerate blueprints for frequently-accessed modified files.

        This is called periodically by the watcher daemon.
        """
        if not self.should_regenerate():
            return

        try:
            # Load index to get connection
            scan_result = load_index(self.index_path)
            if not hasattr(scan_result, '_store') or not hasattr(scan_result._store, '_get_connection'):
                logger.warning("Cannot regenerate blueprints: index format not supported")
                return

            conn = scan_result._store._get_connection()

            # Get cache and hot files
            cache = BlueprintCache(conn)
            hot_files = cache.get_hot_files(
                min_access_count=self.min_access_count,
                limit=20
            )

            if not hot_files:
                logger.debug("No hot files to regenerate")
                self.last_regeneration = time.time()
                return

            # Filter to only modified hot files
            hot_modified_files = [
                (file_path, access_count)
                for file_path, access_count in hot_files
                if file_path in self.modified_files
            ]

            if not hot_modified_files:
                logger.debug(f"No hot files have been modified ({len(self.modified_files)} total mods)")
                self.last_regeneration = time.time()
                return

            logger.info(
                f"Regenerating blueprints for {len(hot_modified_files)} hot files "
                f"({len(hot_files)} total hot, {len(self.modified_files)} modified)"
            )

            # Regenerate blueprints
            generator = BlueprintGenerator(conn, repo_path=self.project_root)
            regenerated_count = 0

            for file_path, access_count in hot_modified_files:
                try:
                    # Create blueprint request with common flags
                    # (using cached settings from most accessed blueprint)
                    request = BlueprintRequest(
                        file_path=file_path,
                        show_deps=True,  # Common flag
                        show_meta=True,   # Common flag
                        use_cache=False,  # Force regeneration
                        fast_mode=False,
                        output_format="json"
                    )

                    # Generate fresh blueprint
                    blueprint = generator.generate(request)

                    logger.debug(
                        f"Regenerated blueprint for {file_path} "
                        f"({access_count} accesses, {blueprint.total_symbols} symbols)"
                    )

                    regenerated_count += 1

                    # Remove from modified files since we've regenerated it
                    self.modified_files.discard(file_path)

                except Exception as e:
                    logger.warning(f"Failed to regenerate blueprint for {file_path}: {e}")
                    continue

            logger.info(f"Successfully regenerated {regenerated_count}/{len(hot_modified_files)} blueprints")

            # Update last regeneration time
            self.last_regeneration = time.time()

        except Exception as e:
            logger.error(f"Error in blueprint regeneration: {e}")
            self.last_regeneration = time.time()  # Prevent rapid retries

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about blueprint regeneration.

        Returns:
            Dictionary with stats
        """
        return {
            "modified_files_count": len(self.modified_files),
            "last_regeneration": self.last_regeneration,
            "time_since_last_regen": time.time() - self.last_regeneration if self.last_regeneration > 0 else None
        }
