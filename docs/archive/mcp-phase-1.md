# Phase 1: MCP Skeleton + Core Read Tools

## Overview

Establish the MCP server foundation with FastMCP and implement 3 read-only tools to prove the architecture works.

## Goals

- FastMCP server that starts and accepts connections
- Direct integration with Cerberus core library (no subprocess/HTTP)
- 3 working tools: `search`, `get_symbol`, `read_range`
- Claude Code can connect and use the tools

## Tasks

### 1.1 Install FastMCP Dependency

```bash
# Add to pyproject.toml or requirements.txt
fastmcp>=0.1.0
```

### 1.2 Create MCP Server Skeleton

**File: `src/cerberus/mcp/__init__.py`**
```python
"""Cerberus MCP Server - Model Context Protocol interface."""
from .server import create_server, run_server

__all__ = ["create_server", "run_server"]
```

**File: `src/cerberus/mcp/server.py`**
```python
"""FastMCP server setup and tool registration."""
from fastmcp import FastMCP
from pathlib import Path

from .tools import search, symbols, reading

mcp = FastMCP("cerberus")

def create_server():
    """Create and configure the MCP server."""
    # Register tool modules
    search.register(mcp)
    symbols.register(mcp)
    reading.register(mcp)
    return mcp

def run_server():
    """Run the MCP server."""
    server = create_server()
    server.run()
```

### 1.3 Implement Search Tool

**File: `src/cerberus/mcp/tools/search.py`**
```python
"""Search tool - hybrid keyword + semantic search."""
from typing import List, Optional
from pathlib import Path

from cerberus.retrieval import hybrid_search
from cerberus.index import load_index

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
        # TODO: Use IndexManager instead of direct load
        index_path = Path(".cerberus/cerberus.db")
        if not index_path.exists():
            index_path = Path("cerberus.db")

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

### 1.4 Implement Get Symbol Tool

**File: `src/cerberus/mcp/tools/symbols.py`**
```python
"""Symbol retrieval tools."""
from typing import List, Optional
from pathlib import Path

from cerberus.index import load_index
from cerberus.retrieval.utils import find_symbol_fts, read_range

def register(mcp):
    @mcp.tool()
    def get_symbol(
        name: str,
        exact: bool = True,
        context_lines: int = 5
    ) -> List[dict]:
        """
        Retrieve symbol by name with surrounding code context.

        Args:
            name: Symbol name to find
            exact: If True, exact match only. If False, includes partial matches.
            context_lines: Lines of context before/after symbol

        Returns:
            List of matching symbols with code snippets
        """
        index_path = Path(".cerberus/cerberus.db")
        if not index_path.exists():
            index_path = Path("cerberus.db")

        scan_result = load_index(index_path)
        matches = find_symbol_fts(name, scan_result, exact=exact)

        results = []
        for symbol in matches:
            snippet = read_range(
                Path(symbol.file_path),
                symbol.start_line,
                symbol.end_line,
                padding=context_lines
            )
            results.append({
                "name": symbol.name,
                "type": symbol.type,
                "file": symbol.file_path,
                "start_line": symbol.start_line,
                "end_line": symbol.end_line,
                "signature": symbol.signature,
                "code": snippet.content
            })

        return results
```

### 1.5 Implement Read Range Tool

**File: `src/cerberus/mcp/tools/reading.py`**
```python
"""File reading tools."""
from pathlib import Path

from cerberus.retrieval.utils import read_range as core_read_range

def register(mcp):
    @mcp.tool()
    def read_range(
        file_path: str,
        start_line: int,
        end_line: int,
        context_lines: int = 0
    ) -> dict:
        """
        Read specific lines from a file.

        Args:
            file_path: Path to file
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed)
            context_lines: Additional context lines before/after

        Returns:
            File content with metadata
        """
        snippet = core_read_range(
            Path(file_path),
            start_line,
            end_line,
            padding=context_lines
        )

        return {
            "file": snippet.file_path,
            "start_line": snippet.start_line,
            "end_line": snippet.end_line,
            "content": snippet.content
        }
```

### 1.6 Create Entry Point

**File: `src/cerberus/mcp/__main__.py`**
```python
"""Entry point for running MCP server directly."""
from .server import run_server

if __name__ == "__main__":
    run_server()
```

### 1.7 Test with Claude Code

Create test configuration for Claude Code:
```json
{
  "mcpServers": {
    "cerberus": {
      "command": "python",
      "args": ["-m", "cerberus.mcp"],
      "cwd": "/path/to/project"
    }
  }
}
```

## Files to Create

```
src/cerberus/mcp/
├── __init__.py
├── __main__.py
├── server.py
└── tools/
    ├── __init__.py
    ├── search.py
    ├── symbols.py
    └── reading.py
```

## Acceptance Criteria

- [ ] `python -m cerberus.mcp` starts without errors
- [ ] Claude Code can connect to the MCP server
- [ ] `search` tool returns results for valid queries
- [ ] `get_symbol` tool retrieves symbols with code snippets
- [ ] `read_range` tool reads file content correctly
- [ ] All tools return structured data (not strings)
- [ ] Errors are returned as structured MCP errors

## Dependencies

- None (this is the first phase)

## Notes

- This phase uses direct `load_index()` calls - Phase 2 adds IndexManager
- No file watching yet - index must exist before server starts
- Hardcoded index path discovery - Phase 2 adds proper config
