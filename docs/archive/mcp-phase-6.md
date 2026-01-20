# Phase 6: CLI/Daemon Removal + Cleanup

## Overview

Remove the old CLI and daemon code now that MCP is fully functional. Clean up the codebase and establish the new project structure.

## Goals

- Remove all CLI modules (src/cerberus/cli/)
- Remove daemon subsystem (src/cerberus/daemon/)
- Update package structure
- Update entry points
- Clean up unused dependencies
- Update documentation

## Pre-Removal Checklist

Before removing old code, verify MCP provides equivalent functionality:

| Old Command | MCP Tool | Status |
|-------------|----------|--------|
| `cerberus index` | `index_build` | ✓ |
| `cerberus search` | `search` | ✓ |
| `cerberus get-symbol` | `get_symbol` | ✓ |
| `cerberus blueprint` | `blueprint` | ✓ |
| `cerberus go` | `blueprint` + `read_range` | ✓ |
| `cerberus memory learn` | `memory_learn` | ✓ |
| `cerberus memory show` | `memory_show` | ✓ |
| `cerberus memory context` | `memory_context` | ✓ |
| `cerberus mutations edit` | `edit_symbol` | ✓ |
| `cerberus symbolic deps` | `deps` | ✓ |
| `cerberus quality style-check` | `style_check` | ✓ |
| `cerberus metrics report` | `metrics_report` | ✓ |

## Tasks

### 6.1 Remove CLI Module

**Delete entire directory:**
```
rm -rf src/cerberus/cli/
```

**Files being removed:**
```
src/cerberus/cli/
├── __init__.py
├── main.py              # Typer app entry point
├── retrieval.py         # get-symbol, search, blueprint
├── retrieval_routing.py # Daemon routing
├── symbolic.py          # deps, calls, references
├── mutations.py         # edit, delete, insert
├── workflow.py          # start, go, orient
├── memory.py            # memory commands
├── quality.py           # style-check, style-fix
├── metrics_cmd.py       # metrics commands
├── dogfood.py           # dogfood commands
├── daemon.py            # daemon management
├── docs.py              # docs commands
├── utils.py             # utility commands
├── batch_handlers.py    # batch processing
├── common.py            # shared utilities
├── config.py            # CLI config
├── output.py            # Output formatting
├── suggestions.py       # Symbol suggestions
├── anchoring.py         # Context anchoring
├── guidance.py          # JIT guidance
└── hints.py             # Efficiency hints
```

### 6.2 Remove Daemon Module

**Delete entire directory:**
```
rm -rf src/cerberus/daemon/
```

**Files being removed:**
```
src/cerberus/daemon/
├── __init__.py
├── server.py            # HTTP server
├── rpc_protocol.py      # JSON-RPC implementation
├── rpc_methods.py       # Method registry
├── facade.py            # Start/stop/health
├── thin_client.py       # CLI routing to daemon
├── pid_manager.py       # Process lifecycle
├── config.py            # Daemon config
├── watcher_integration.py # Watcher sync
└── session_manager.py   # Session handling
```

### 6.3 Update Package __init__.py

**Update `src/cerberus/__init__.py`:**
```python
"""
Cerberus - Intelligent Code Context Engine

MCP-based interface for code indexing, retrieval, and memory.
"""

__version__ = "2.0.0"  # Major version bump for MCP transition

# Core exports
from cerberus.index import build_index, load_index
from cerberus.retrieval import hybrid_search
from cerberus.retrieval.utils import find_symbol_fts, read_range
from cerberus.storage import SQLiteIndexStore, ScanResultAdapter
from cerberus.schemas import CodeSymbol, ScanResult

# MCP server
from cerberus.mcp import create_server, run_server

__all__ = [
    # Version
    "__version__",
    # Core
    "build_index",
    "load_index",
    "hybrid_search",
    "find_symbol_fts",
    "read_range",
    "SQLiteIndexStore",
    "ScanResultAdapter",
    "CodeSymbol",
    "ScanResult",
    # MCP
    "create_server",
    "run_server",
]
```

### 6.4 Update Entry Points

**Update `pyproject.toml`:**
```toml
[project.scripts]
# Remove old CLI entry point
# cerberus = "cerberus.cli.main:app"  # REMOVED

# New MCP entry point
cerberus-mcp = "cerberus.mcp:run_server"
```

Or if using setup.py:
```python
entry_points={
    "console_scripts": [
        # "cerberus=cerberus.cli.main:app",  # REMOVED
        "cerberus-mcp=cerberus.mcp:run_server",
    ],
}
```

### 6.5 Clean Up Unused Imports

Search for and remove imports from deleted modules:

```bash
# Find files importing from cli or daemon
grep -r "from cerberus.cli" src/cerberus/ --include="*.py"
grep -r "from cerberus.daemon" src/cerberus/ --include="*.py"
```

**Common cleanup locations:**

- `src/cerberus/watcher/daemon.py` - May import from daemon config
- `src/cerberus/agent_session.py` - May import from CLI
- Any module using `CLIConfig` or daemon routing

### 6.6 Update Watcher Module

The watcher module may have daemon dependencies. Update to work standalone:

**Update `src/cerberus/watcher/daemon.py`:**
```python
"""File watcher daemon - now standalone, no CLI/daemon deps."""

# Remove imports from cerberus.daemon
# Remove imports from cerberus.cli

# Keep core watcher functionality
```

### 6.7 Remove Unused Dependencies

**Check and potentially remove from requirements:**
```
typer          # CLI framework - REMOVE
click          # typer dependency - REMOVE (if not used elsewhere)
rich           # May keep for internal use, or REMOVE
```

**Update pyproject.toml or requirements.txt:**
```toml
[project]
dependencies = [
    # Keep
    "loguru",
    "pydantic",
    "fastmcp",
    # ... other core deps

    # Remove
    # "typer",
    # "rich",  # evaluate if still needed
]
```

### 6.8 Update Directory Structure

**Final structure after cleanup:**
```
src/cerberus/
├── __init__.py
├── schemas.py
├── logging_config.py
├── paths.py
├── tracing.py
│
├── mcp/                 # MCP server (NEW primary interface)
│   ├── __init__.py
│   ├── server.py
│   ├── config.py
│   ├── index_manager.py
│   ├── validation.py
│   └── tools/
│       ├── search.py
│       ├── symbols.py
│       ├── reading.py
│       ├── indexing.py
│       ├── memory.py
│       ├── structure.py
│       ├── editing.py
│       ├── quality.py
│       ├── metrics.py
│       └── analysis.py
│
├── parser/              # Language parsing
├── storage/             # SQLite + FAISS
├── retrieval/           # Search + symbol lookup
├── mutation/            # Code editing
├── blueprint/           # Structure views
├── resolution/          # Dependencies
├── memory/              # Session memory
├── quality/             # Style checking
├── metrics/             # Token tracking
├── watcher/             # File monitoring
├── semantic/            # Embeddings
├── incremental/         # Git-aware updates
├── limits/              # Bloat protection
├── synthesis/           # AI features
├── scanner/             # File scanning
├── anchoring/           # Context anchors
├── protocol/            # Protocol tracking
└── summarization/       # Summarization
```

### 6.9 Run Full Test Suite

After removal, ensure nothing is broken:

```bash
# Run all tests
pytest tests/ -v --ignore=tests/test_benchmark.py

# Specifically test MCP tools
pytest tests/test_mcp/ -v

# Check for import errors
python -c "from cerberus.mcp import create_server; print('OK')"
```

### 6.10 Update .gitignore

Add any new patterns, remove CLI-specific ones:

```gitignore
# MCP
*.mcp.log

# Remove if present
# .cerberus-cli-history
```

## Files to Delete

```
REMOVE:
├── src/cerberus/cli/           # Entire directory (~20 files)
├── src/cerberus/daemon/        # Entire directory (~10 files)
└── tests/test_cli*.py          # CLI-specific tests
```

## Files to Modify

```
MODIFY:
├── src/cerberus/__init__.py    # Update exports
├── pyproject.toml              # Update entry points, dependencies
├── src/cerberus/watcher/       # Remove daemon dependencies
└── Various files               # Remove CLI/daemon imports
```

## Acceptance Criteria

- [ ] `src/cerberus/cli/` directory deleted
- [ ] `src/cerberus/daemon/` directory deleted
- [ ] No remaining imports from deleted modules
- [ ] `cerberus-mcp` entry point works
- [ ] Old `cerberus` CLI entry point removed
- [ ] All tests pass (except CLI-specific tests)
- [ ] `python -m cerberus.mcp` starts server
- [ ] Package installs cleanly
- [ ] No typer/click in dependencies (unless needed elsewhere)

## Dependencies

- Phase 1-5 completed and tested
- All MCP tools verified working
- Backup of code before deletion (git commit)

## Rollback Plan

If issues are found after removal:

1. Git revert to pre-removal commit
2. Keep CLI alongside MCP temporarily
3. Fix issues before re-attempting removal

## Notes

- Make a clean git commit before starting this phase
- Tag the commit as "pre-mcp-cleanup" for easy rollback
- Consider keeping CLI in a separate branch for reference
- Update CHANGELOG.md with breaking changes
