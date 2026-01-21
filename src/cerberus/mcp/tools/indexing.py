"""Index management tools."""
import time
from pathlib import Path
from typing import List, Optional

from ..index_manager import get_index_manager


def register(mcp):
    @mcp.tool()
    def index_build(path: str = ".", extensions: Optional[List[str]] = None) -> dict:
        """
        Build or rebuild the code index.

        Args:
            path: Directory to index (default: current directory)
            extensions: File extensions to include (default: common code files)
                       IMPORTANT: Extensions must include the dot prefix (e.g., ".py", ".go", ".ts")

        Returns:
            Index statistics (file count, symbol count, path)
        """
        if extensions is None:
            # Code files
            extensions = [".py", ".ts", ".js", ".go", ".tsx", ".jsx"]
            # Documentation
            extensions.extend([".md", ".txt", ".rst"])
            # Configs
            extensions.extend([".json", ".yaml", ".yml", ".toml", ".ini"])
            # Scripts
            extensions.extend([".sh", ".bash"])
        else:
            # Validate and auto-correct extension format
            corrected_extensions = []
            for ext in extensions:
                if not ext.startswith("."):
                    # Auto-correct by adding dot prefix
                    corrected_extensions.append(f".{ext}")
                else:
                    corrected_extensions.append(ext)
            extensions = corrected_extensions

        manager = get_index_manager()
        return manager.rebuild(Path(path), extensions)

    @mcp.tool()
    def index_status() -> dict:
        """
        Get index health and statistics.

        Returns:
            Index path, file count, symbol count, size
        """
        manager = get_index_manager()
        return manager.get_stats()

    @mcp.tool()
    def index_watcher() -> dict:
        """
        Get file watcher status and configuration.

        Shows whether auto-update is enabled, debounce settings,
        and watched file extensions.

        Returns:
            Watcher configuration and status
        """
        manager = get_index_manager()
        return manager.get_watcher_status()

    @mcp.tool()
    def index_auto_update(enabled: Optional[bool] = None) -> dict:
        """
        Get or set auto-update on file changes.

        When enabled, the index automatically updates when source files
        change (with debouncing to batch rapid changes).

        Args:
            enabled: True to enable, False to disable, None to just query

        Returns:
            Current auto-update status
        """
        manager = get_index_manager()

        if enabled is not None:
            manager.set_auto_update(enabled)

        status = manager.get_watcher_status()
        return {
            "auto_update": status["auto_update"],
            "debounce_seconds": status["debounce_seconds"],
            "message": (
                "Index will auto-update on file changes"
                if status["auto_update"]
                else "Auto-update disabled, use index_build() to update manually"
            ),
        }

    @mcp.tool()
    def smart_update(force_full: bool = False) -> dict:
        """
        Update index incrementally based on git changes.

        Detects changes since last index and surgically updates only affected symbols.
        Falls back to full reparse if >30% files changed.

        10x faster than index_build for typical development.

        Args:
            force_full: Force full re-parse instead of surgical update (default: False)

        Returns:
            dict with:
            - status: "ok" or "error"
            - strategy: "surgical", "incremental", "full_reparse", or "failed"
            - files_reparsed: Number of files that were reparsed
            - updated_symbols: Count of symbols that were updated
            - elapsed_time: Time taken in seconds
        """
        manager = get_index_manager()

        # Check if index exists
        try:
            index = manager.get_index()
        except FileNotFoundError as e:
            return {"status": "error", "error_type": "no_index", "message": str(e)}

        # Get index path
        index_path = manager._index_path
        if not index_path or not index_path.exists():
            return {
                "status": "error",
                "error_type": "no_index_path",
                "message": "No index path available. Run index_build first.",
            }

        start_time = time.time()

        try:
            from cerberus.incremental.facade import update_index_incrementally

            result = update_index_incrementally(
                index_path=index_path,
                force_full_reparse=force_full,
            )

            # Invalidate manager cache so next access reloads fresh index
            manager.invalidate()

            elapsed = time.time() - start_time

            return {
                "status": "ok",
                "strategy": result.strategy,
                "files_reparsed": result.files_reparsed,
                "updated_symbols": len(result.updated_symbols),
                "removed_symbols": len(result.removed_symbols),
                "affected_callers": len(result.affected_callers),
                "elapsed_time": round(elapsed, 3),
            }

        except Exception as e:
            elapsed = time.time() - start_time
            return {
                "status": "error",
                "error_type": "update_failed",
                "message": str(e),
                "elapsed_time": round(elapsed, 3),
            }
