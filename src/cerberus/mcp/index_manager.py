"""Index lifecycle management - lazy load, cache, debounced auto-update."""
from pathlib import Path
from typing import Optional, Union, Set
import threading
import time

from loguru import logger

from cerberus.index import build_index, load_index
from cerberus.schemas import ScanResult
from cerberus.storage import ScanResultAdapter

from .config import load_config, get_config_value, DEFAULTS


class _WatcherHandle:
    """Lightweight holder for watcher thread controls."""

    def __init__(self, thread: threading.Thread, stop_event: threading.Event):
        self.thread = thread
        self.stop_event = stop_event

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=5)


class _Debouncer:
    """
    Collects file changes and triggers callback after quiet period.

    Thread-safe debouncer that batches rapid file changes.
    """

    def __init__(self, callback, debounce_seconds: float = 3.0):
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.pending_files: Set[str] = set()
        self.lock = threading.Lock()
        self.timer: Optional[threading.Timer] = None

    def add(self, file_path: str):
        """Add a changed file, resetting the debounce timer."""
        with self.lock:
            self.pending_files.add(file_path)

            # Cancel existing timer
            if self.timer:
                self.timer.cancel()

            # Start new timer
            self.timer = threading.Timer(self.debounce_seconds, self._fire)
            self.timer.daemon = True
            self.timer.start()

    def _fire(self):
        """Fire the callback with collected files."""
        with self.lock:
            if not self.pending_files:
                return

            files = list(self.pending_files)
            self.pending_files.clear()
            self.timer = None

        try:
            self.callback(files)
        except Exception as e:
            logger.error(f"Debouncer callback error: {e}")

    def cancel(self):
        """Cancel pending debounce."""
        with self.lock:
            if self.timer:
                self.timer.cancel()
                self.timer = None
            self.pending_files.clear()


def _start_watcher_thread(project_root: Path, callback, debounce_seconds: float):
    """
    Start a lightweight watchdog observer with debouncing.

    Falls back silently if watchdog is unavailable.
    """
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except Exception as exc:
        logger.warning(f"Watchdog not available, skipping file watch: {exc}")
        return None

    debouncer = _Debouncer(callback, debounce_seconds)

    class _Handler(FileSystemEventHandler):
        def on_any_event(self, event):
            if event.is_directory:
                return
            try:
                debouncer.add(event.src_path)
            except Exception as e:
                logger.warning(f"Watcher event error: {e}")

    observer = Observer()
    handler = _Handler()
    observer.schedule(handler, str(project_root), recursive=True)

    stop_event = threading.Event()

    def run():
        observer.start()
        try:
            while not stop_event.is_set():
                time.sleep(1)
        finally:
            debouncer.cancel()
            observer.stop()
            observer.join()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return _WatcherHandle(thread, stop_event)


class IndexManager:
    """
    Manages index lifecycle with lazy loading, file watching, and auto-update.

    Features:
    - Lazy index loading on first access
    - File watching with debounced change detection
    - Optional auto-incremental-update on file changes
    - Thread-safe singleton pattern
    """

    _instance: Optional["IndexManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self._index: Optional[Union[ScanResult, ScanResultAdapter]] = None
        self._index_path: Optional[Path] = None
        self._watcher: Optional[_WatcherHandle] = None
        self._auto_update_enabled: bool = get_config_value(
            "index.auto_update", DEFAULTS["index"]["auto_update"]
        )
        self._debounce_seconds: float = get_config_value(
            "index.debounce_seconds", DEFAULTS["index"]["debounce_seconds"]
        )
        self._watch_extensions: list = get_config_value(
            "index.watch_extensions", DEFAULTS["index"]["watch_extensions"]
        )
        self._initialized = True

    def get_index(self) -> Union[ScanResult, ScanResultAdapter]:
        """
        Get index, loading lazily on first access.

        Returns:
            Loaded ScanResult/ScanResultAdapter

        Raises:
            FileNotFoundError: If no index can be discovered
        """
        if self._index is None:
            self._load_index()
        return self._index

    def _load_index(self):
        """Load index from discovered or configured path."""
        self._index_path = self._discover_index_path()
        logger.info(f"Loading index from {self._index_path}")
        self._index = load_index(self._index_path)
        self._start_watcher()

    def _discover_index_path(self) -> Path:
        """
        Auto-discover index path.

        Priority:
        1. CERBERUS_INDEX environment variable
        2. .cerberus/cerberus.db in current directory
        3. cerberus.db in current directory
        4. Config file specification

        Raises:
            FileNotFoundError: If no index found
        """
        import os

        env_path = os.environ.get("CERBERUS_INDEX")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path

        candidates = [
            Path(".cerberus/cerberus.db"),
            Path("cerberus.db"),
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        config_path = self._get_config_index_path()
        if config_path and config_path.exists():
            return config_path

        raise FileNotFoundError(
            "No Cerberus index found. Checked:\n"
            "  - $CERBERUS_INDEX environment variable\n"
            "  - .cerberus/cerberus.db\n"
            "  - cerberus.db\n"
            "Run 'index_build' tool to create an index."
        )

    def _get_config_index_path(self) -> Optional[Path]:
        """Read index path from config file if present."""
        config = load_config()
        if config and "index" in config:
            return Path(config["index"].get("path", ""))
        return None

    def _start_watcher(self):
        """Start file watcher with debounced auto-update."""
        if self._watcher is not None:
            return

        project_root = Path(getattr(self._index, "project_root", None) or Path.cwd())
        index_path = self._index_path

        def on_changes(changed_files):
            """Handle debounced file changes."""
            # Filter out index files and non-watched extensions
            filtered = []
            for file_path in changed_files:
                p = Path(file_path)

                # Skip index files
                if index_path and (
                    p == index_path
                    or p.name == f"{index_path.name}-wal"
                    or p.name == f"{index_path.name}-shm"
                ):
                    continue

                # Skip non-watched extensions
                if p.suffix not in self._watch_extensions:
                    continue

                filtered.append(file_path)

            if not filtered:
                return

            logger.info(f"Files changed ({len(filtered)} files)")

            if self._auto_update_enabled and index_path and index_path.exists():
                # Perform incremental update
                self._incremental_update(filtered)
            else:
                # Just invalidate cache
                logger.debug("Auto-update disabled, invalidating cache only")
                self.invalidate()

        self._watcher = _start_watcher_thread(
            project_root, on_changes, self._debounce_seconds
        )
        if self._watcher:
            logger.info(
                f"Started file watcher for {project_root} "
                f"(debounce={self._debounce_seconds}s, auto_update={self._auto_update_enabled})"
            )

    def _incremental_update(self, changed_files: list):
        """Perform incremental index update for changed files."""
        try:
            from cerberus.incremental.facade import update_index_incrementally

            logger.info(f"Incremental update for {len(changed_files)} changed files")

            result = update_index_incrementally(
                index_path=self._index_path,
                force_full_reparse=False,
            )

            # Invalidate cache so next access reloads fresh index
            self._index = None

            logger.info(
                f"Incremental update complete: "
                f"{result.files_reparsed} files reparsed, "
                f"{len(result.updated_symbols)} symbols updated"
            )

        except Exception as e:
            logger.error(f"Incremental update failed: {e}, falling back to cache invalidation")
            self.invalidate()

    def _stop_watcher(self):
        if self._watcher:
            try:
                self._watcher.stop()
            except Exception as exc:
                logger.warning(f"Error stopping watcher: {exc}")
            finally:
                self._watcher = None

    def invalidate(self):
        """Invalidate cached index - next get_index() will reload."""
        self._index = None
        logger.debug("Index cache invalidated")

    def set_auto_update(self, enabled: bool):
        """Enable or disable auto-update on file changes."""
        self._auto_update_enabled = enabled
        logger.info(f"Auto-update {'enabled' if enabled else 'disabled'}")

    def get_watcher_status(self) -> dict:
        """Get current watcher configuration and status."""
        return {
            "watching": self._watcher is not None,
            "auto_update": self._auto_update_enabled,
            "debounce_seconds": self._debounce_seconds,
            "watch_extensions": self._watch_extensions,
        }

    def rebuild(self, path: Path, extensions: list[str]) -> dict:
        """
        Explicitly rebuild index.

        Args:
            path: Directory to index
            extensions: File extensions to include

        Returns:
            Index statistics
        """
        logger.info(f"Rebuilding index for {path}")

        output_path = path / ".cerberus" / "cerberus.db"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        scan_result = build_index(
            directory=path,
            output_path=output_path,
            extensions=extensions,
        )

        self._index_path = output_path
        self._index = load_index(output_path)

        # Restart watcher for new path
        self._stop_watcher()
        self._start_watcher()

        return {
            "path": str(output_path),
            "files": scan_result.total_files,
            "symbols": len(scan_result.symbols),
        }

    def get_stats(self) -> dict:
        """Get index statistics."""
        index = self.get_index()
        store = getattr(index, "_store", None)
        stats = store.get_stats() if store else None

        return {
            "index_path": str(self._index_path) if self._index_path else "",
            "total_files": (stats or {}).get("total_files", getattr(index, "total_files", 0)),
            "total_symbols": (stats or {}).get("total_symbols", len(getattr(index, "symbols", []))),
            "total_embeddings": (stats or {}).get("total_embeddings", 0),
            "db_size_bytes": (stats or {}).get("db_size_bytes", 0),
        }


_manager: Optional[IndexManager] = None


def get_index_manager() -> IndexManager:
    """Get the global IndexManager instance."""
    global _manager
    if _manager is None:
        _manager = IndexManager()
    return _manager
