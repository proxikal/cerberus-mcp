"""Index management tools."""
import time
from pathlib import Path
from typing import List, Optional

from ..index_manager import get_index_manager


def register(mcp):
    @mcp.tool()
    def index_build(path: str = ".", extensions: Optional[List[str]] = None, no_embeddings: bool = False) -> dict:
        """Build or rebuild codebase index from scratch.

        Args:
            path: Directory to index (default: current directory)
            extensions: File extensions to include (default: common code/doc files)
            no_embeddings: Skip embedding generation for semantic search (default: False, rare use)

        Semantic search is enabled by default with bundled all-MiniLM-L6-v2 model.
        Only use no_embeddings=True to disable embeddings in edge cases (e.g., testing, resource constraints).
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
            corrected_extensions: list = []
            for ext in extensions:
                if not ext.startswith("."):
                    # Auto-correct by adding dot prefix
                    corrected_extensions.append(f".{ext}")
                else:
                    corrected_extensions.append(ext)
            extensions = corrected_extensions

        manager = get_index_manager()
        return manager.rebuild(Path(path), extensions, store_embeddings=not no_embeddings)

    @mcp.tool()
    def index_status() -> dict:
        """Get index health statistics and metadata."""
        manager = get_index_manager()
        return manager.get_stats()

    @mcp.tool()
    def index_watcher() -> dict:
        """Check file watcher status for auto-updates."""
        manager = get_index_manager()
        return manager.get_watcher_status()

    @mcp.tool()
    def index_auto_update(enabled: Optional[bool] = None) -> dict:
        """Enable or disable automatic index updates."""
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
        """Incrementally update index using git-aware detection."""
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
