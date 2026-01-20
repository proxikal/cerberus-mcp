# Phase 2: Index Manager + File Watching

## Overview

Implement the IndexManager for lazy loading, caching, and automatic refresh when files change. Add configuration auto-discovery.

## Goals

- Index loaded on first tool use (not at server start)
- Cached in memory for fast subsequent access
- File watcher detects changes and invalidates cache
- Auto-discovery of index path (zero-config)
- Optional config file support

## Tasks

### 2.1 Create IndexManager

**File: `src/cerberus/mcp/index_manager.py`**
```python
"""Index lifecycle management - lazy load, cache, watch."""
from pathlib import Path
from typing import Optional
import threading

from loguru import logger

from cerberus.index import load_index
from cerberus.storage import ScanResultAdapter


class IndexManager:
    """
    Manages index lifecycle with lazy loading and file watching.

    Thread-safe singleton pattern - one index per MCP server process.
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
        if self._initialized:
            return

        self._index: Optional[ScanResultAdapter] = None
        self._index_path: Optional[Path] = None
        self._watcher_thread: Optional[threading.Thread] = None
        self._watch_callback = None
        self._initialized = True

    def get_index(self) -> ScanResultAdapter:
        """
        Get index, loading lazily on first access.

        Returns:
            Loaded ScanResultAdapter

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

        # Check environment variable
        env_path = os.environ.get("CERBERUS_INDEX")
        if env_path:
            path = Path(env_path)
            if path.exists():
                return path

        # Check standard locations
        candidates = [
            Path(".cerberus/cerberus.db"),
            Path("cerberus.db"),
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        # Check config file
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
        from .config import load_config
        config = load_config()
        if config and "index" in config:
            return Path(config["index"].get("path", ""))
        return None

    def _start_watcher(self):
        """Start file watcher to detect changes."""
        if self._watcher_thread is not None:
            return  # Already watching

        from cerberus.watcher import start_watcher_thread

        # Get project root from index
        project_root = Path(self._index.project_root) if self._index.project_root else Path.cwd()

        def on_change(changed_files):
            logger.info(f"Files changed: {changed_files}, invalidating index cache")
            self.invalidate()

        self._watcher_thread = start_watcher_thread(
            project_root,
            callback=on_change
        )
        logger.info(f"Started file watcher for {project_root}")

    def invalidate(self):
        """Invalidate cached index - next get_index() will reload."""
        self._index = None
        logger.debug("Index cache invalidated")

    def rebuild(self, path: Path, extensions: list[str]) -> dict:
        """
        Explicitly rebuild index.

        Args:
            path: Directory to index
            extensions: File extensions to include

        Returns:
            Index statistics
        """
        from cerberus.index import build_index

        logger.info(f"Rebuilding index for {path}")

        # Determine output path
        output_path = path / ".cerberus" / "cerberus.db"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build index
        scan_result = build_index(
            root_dir=path,
            extensions=extensions,
            output_path=output_path
        )

        # Update our cached reference
        self._index_path = output_path
        self._index = load_index(output_path)

        # Restart watcher for new path
        if self._watcher_thread:
            # TODO: Stop old watcher
            pass
        self._start_watcher()

        return {
            "path": str(output_path),
            "files": scan_result.total_files,
            "symbols": len(scan_result.symbols)
        }

    def get_stats(self) -> dict:
        """Get index statistics."""
        index = self.get_index()
        store = index._store
        stats = store.get_stats()

        return {
            "index_path": str(self._index_path),
            "total_files": stats["total_files"],
            "total_symbols": stats["total_symbols"],
            "total_embeddings": stats["total_embeddings"],
            "db_size_bytes": stats["db_size_bytes"]
        }


# Global instance
_manager: Optional[IndexManager] = None

def get_index_manager() -> IndexManager:
    """Get the global IndexManager instance."""
    global _manager
    if _manager is None:
        _manager = IndexManager()
    return _manager
```

### 2.2 Create Configuration Module

**File: `src/cerberus/mcp/config.py`**
```python
"""Configuration loading and auto-discovery."""
from pathlib import Path
from typing import Any, Dict, Optional
import os

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def load_config() -> Optional[Dict[str, Any]]:
    """
    Load configuration from file.

    Priority:
    1. CERBERUS_CONFIG environment variable
    2. ./cerberus.toml (project config)
    3. ~/.config/cerberus/config.toml (user config)

    Returns:
        Configuration dict or None if no config found
    """
    config_paths = []

    # Environment variable
    env_config = os.environ.get("CERBERUS_CONFIG")
    if env_config:
        config_paths.append(Path(env_config))

    # Project config
    config_paths.append(Path("cerberus.toml"))

    # User config
    config_paths.append(Path.home() / ".config" / "cerberus" / "config.toml")

    for path in config_paths:
        if path.exists():
            with open(path, "rb") as f:
                return tomllib.load(f)

    return None


def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a configuration value by dot-notation key.

    Example:
        get_config_value("index.path", ".cerberus/cerberus.db")
        get_config_value("limits.max_search_results", 100)
    """
    config = load_config()
    if config is None:
        return default

    parts = key.split(".")
    value = config

    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return default

    return value


# Default configuration values
DEFAULTS = {
    "index": {
        "path": ".cerberus/cerberus.db",
        "auto_rebuild": True,
        "watch_extensions": [".py", ".ts", ".js", ".go", ".tsx", ".jsx"]
    },
    "memory": {
        "global_store": "~/.cerberus/memory",
        "profile_max_size": 4096
    },
    "limits": {
        "max_search_results": 100,
        "max_file_size": 1_000_000,
        "max_symbols_per_file": 500
    },
    "quality": {
        "style_rules": ["black", "isort"],
        "auto_fix_on_edit": False
    }
}
```

### 2.3 Update Tools to Use IndexManager

**Update `src/cerberus/mcp/tools/search.py`:**
```python
"""Search tool - hybrid keyword + semantic search."""
from typing import List

from cerberus.retrieval import hybrid_search
from ..index_manager import get_index_manager


def register(mcp):
    @mcp.tool()
    def search(
        query: str,
        limit: int = 10,
        mode: str = "auto"
    ) -> List[dict]:
        """
        Search codebase for symbols matching query.

        Args:
            query: Search query (keyword or natural language)
            limit: Maximum results to return
            mode: Search mode - "auto", "keyword", "semantic", "balanced"

        Returns:
            List of matching symbols with file paths and line numbers
        """
        manager = get_index_manager()
        index_path = manager._index_path or manager._discover_index_path()

        results = hybrid_search(
            query=query,
            index_path=index_path,
            mode=mode,
            top_k=limit
        )

        return [
            {
                "name": r.symbol.name,
                "type": r.symbol.type,
                "file": r.symbol.file_path,
                "start_line": r.symbol.start_line,
                "end_line": r.symbol.end_line,
                "score": r.hybrid_score,
                "match_type": r.match_type
            }
            for r in results
        ]
```

### 2.4 Add Index Tools

**File: `src/cerberus/mcp/tools/indexing.py`**
```python
"""Index management tools."""
from typing import List, Optional
from pathlib import Path

from ..index_manager import get_index_manager


def register(mcp):
    @mcp.tool()
    def index_build(
        path: str = ".",
        extensions: Optional[List[str]] = None
    ) -> dict:
        """
        Build or rebuild the code index.

        Args:
            path: Directory to index (default: current directory)
            extensions: File extensions to include (default: common code files)

        Returns:
            Index statistics (file count, symbol count, path)
        """
        if extensions is None:
            extensions = [".py", ".ts", ".js", ".go", ".tsx", ".jsx"]

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
```

### 2.5 Update Server to Register Index Tools

**Update `src/cerberus/mcp/server.py`:**
```python
"""FastMCP server setup and tool registration."""
from fastmcp import FastMCP

from .tools import search, symbols, reading, indexing

mcp = FastMCP("cerberus")

def create_server():
    """Create and configure the MCP server."""
    search.register(mcp)
    symbols.register(mcp)
    reading.register(mcp)
    indexing.register(mcp)
    return mcp

def run_server():
    """Run the MCP server."""
    server = create_server()
    server.run()
```

## Files to Create/Modify

```
src/cerberus/mcp/
├── index_manager.py    # NEW
├── config.py           # NEW
├── server.py           # MODIFIED
└── tools/
    ├── indexing.py     # NEW
    ├── search.py       # MODIFIED
    └── symbols.py      # MODIFIED
```

## Acceptance Criteria

- [ ] Server starts without pre-existing index (lazy load)
- [ ] First tool call triggers index load
- [ ] Subsequent calls use cached index (fast)
- [ ] File changes trigger cache invalidation
- [ ] Next tool call after change reloads index
- [ ] `index_build` tool creates new index
- [ ] `index_status` tool returns accurate stats
- [ ] Auto-discovery finds index in standard locations
- [ ] Config file overrides work when present
- [ ] Clear error message when no index found

## Dependencies

- Phase 1 completed (basic MCP server working)

## Notes

- File watcher integration may need adjustment based on existing watcher code
- Consider debouncing file change events to avoid excessive reloads
- Thread safety is important - IndexManager uses locks
