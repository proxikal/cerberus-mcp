# Phase 7: Testing + Documentation

## Overview

Final phase - comprehensive testing of all MCP tools and complete documentation for users and developers.

## Goals

- Integration tests for all 24 MCP tools
- End-to-end test scenarios
- Claude Code integration testing
- User documentation (setup, usage)
- Developer documentation (architecture, extending)
- Migration guide from CLI

## Tasks

### 7.1 Create MCP Test Infrastructure

**File: `tests/test_mcp/__init__.py`:**
```python
"""MCP integration tests."""
```

**File: `tests/test_mcp/conftest.py`:**
```python
"""Shared fixtures for MCP tests."""
import pytest
from pathlib import Path
import tempfile
import shutil

from cerberus.mcp import create_server
from cerberus.index import build_index


@pytest.fixture
def temp_project():
    """Create a temporary project with sample files."""
    temp_dir = tempfile.mkdtemp()
    project = Path(temp_dir)

    # Create sample Python files
    (project / "src").mkdir()
    (project / "src" / "main.py").write_text('''
"""Main module."""

def hello(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

class Calculator:
    """Simple calculator."""

    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b
''')

    (project / "src" / "utils.py").write_text('''
"""Utility functions."""
from .main import add

def sum_list(numbers: list) -> int:
    """Sum a list of numbers."""
    total = 0
    for n in numbers:
        total = add(total, n)
    return total
''')

    yield project

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def indexed_project(temp_project):
    """Create a temporary project with index built."""
    index_path = temp_project / ".cerberus" / "cerberus.db"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    build_index(
        root_dir=temp_project,
        extensions=[".py"],
        output_path=index_path
    )

    return temp_project, index_path


@pytest.fixture
def mcp_server():
    """Create an MCP server instance for testing."""
    return create_server()
```

### 7.2 Test Read Tools

**File: `tests/test_mcp/test_read_tools.py`:**
```python
"""Tests for read-only MCP tools."""
import pytest
import os


class TestSearchTool:
    """Tests for search tool."""

    def test_search_finds_function(self, indexed_project, mcp_server):
        """Search finds function by name."""
        project, index_path = indexed_project
        os.chdir(project)

        # Get the search tool
        search_tool = mcp_server.get_tool("search")
        results = search_tool(query="hello", limit=5)

        assert len(results) >= 1
        assert any(r["name"] == "hello" for r in results)

    def test_search_finds_class(self, indexed_project, mcp_server):
        """Search finds class by name."""
        project, index_path = indexed_project
        os.chdir(project)

        search_tool = mcp_server.get_tool("search")
        results = search_tool(query="Calculator", limit=5)

        assert len(results) >= 1
        assert any(r["name"] == "Calculator" for r in results)

    def test_search_empty_query(self, indexed_project, mcp_server):
        """Search with empty query returns error."""
        project, index_path = indexed_project
        os.chdir(project)

        search_tool = mcp_server.get_tool("search")
        results = search_tool(query="nonexistent_xyz_123", limit=5)

        assert len(results) == 0


class TestGetSymbolTool:
    """Tests for get_symbol tool."""

    def test_get_symbol_exact(self, indexed_project, mcp_server):
        """Get symbol by exact name."""
        project, index_path = indexed_project
        os.chdir(project)

        tool = mcp_server.get_tool("get_symbol")
        results = tool(name="hello", exact=True)

        assert len(results) == 1
        assert results[0]["name"] == "hello"
        assert "code" in results[0]
        assert "def hello" in results[0]["code"]

    def test_get_symbol_with_context(self, indexed_project, mcp_server):
        """Get symbol includes context lines."""
        project, index_path = indexed_project
        os.chdir(project)

        tool = mcp_server.get_tool("get_symbol")
        results = tool(name="hello", context_lines=10)

        assert len(results) == 1
        # Context should include docstring and more
        assert '"""Greet someone."""' in results[0]["code"]


class TestReadRangeTool:
    """Tests for read_range tool."""

    def test_read_range_basic(self, indexed_project, mcp_server):
        """Read specific line range."""
        project, index_path = indexed_project
        os.chdir(project)

        tool = mcp_server.get_tool("read_range")
        result = tool(
            file_path=str(project / "src" / "main.py"),
            start_line=1,
            end_line=5
        )

        assert "content" in result
        assert '"""Main module."""' in result["content"]

    def test_read_range_with_context(self, indexed_project, mcp_server):
        """Read range includes context lines."""
        project, index_path = indexed_project
        os.chdir(project)

        tool = mcp_server.get_tool("read_range")
        result = tool(
            file_path=str(project / "src" / "main.py"),
            start_line=5,
            end_line=7,
            context_lines=2
        )

        assert result["start_line"] == 3  # 5 - 2
        assert result["end_line"] == 9    # 7 + 2


class TestBlueprintTool:
    """Tests for blueprint tool."""

    def test_blueprint_file(self, indexed_project, mcp_server):
        """Generate blueprint for a file."""
        project, index_path = indexed_project
        os.chdir(project)

        tool = mcp_server.get_tool("blueprint")
        result = tool(path=str(project / "src" / "main.py"))

        assert "hello" in result or "Calculator" in result

    def test_blueprint_json_format(self, indexed_project, mcp_server):
        """Blueprint with JSON format."""
        project, index_path = indexed_project
        os.chdir(project)

        tool = mcp_server.get_tool("blueprint")
        result = tool(
            path=str(project / "src" / "main.py"),
            format="json"
        )

        # Should be parseable as JSON (string in this case)
        import json
        parsed = json.loads(result)
        assert "symbols" in parsed or "file" in parsed
```

### 7.3 Test Memory Tools

**File: `tests/test_mcp/test_memory_tools.py`:**
```python
"""Tests for memory MCP tools."""
import pytest
import tempfile
import os


@pytest.fixture
def clean_memory(tmp_path):
    """Use temporary memory directory."""
    memory_dir = tmp_path / ".cerberus" / "memory"
    memory_dir.mkdir(parents=True)

    old_home = os.environ.get("HOME")
    os.environ["HOME"] = str(tmp_path)

    yield memory_dir

    if old_home:
        os.environ["HOME"] = old_home


class TestMemoryLearn:
    """Tests for memory_learn tool."""

    def test_learn_preference(self, mcp_server, clean_memory):
        """Learn a preference."""
        tool = mcp_server.get_tool("memory_learn")
        result = tool(
            category="preference",
            content="Prefer early returns"
        )

        assert result["status"] == "learned"
        assert result["category"] == "preference"

    def test_learn_decision(self, mcp_server, clean_memory, tmp_path):
        """Learn a project decision."""
        os.chdir(tmp_path)

        tool = mcp_server.get_tool("memory_learn")
        result = tool(
            category="decision",
            content="Use SQLite for storage",
            project="test-project",
            metadata={"topic": "Database", "rationale": "Simple and fast"}
        )

        assert result["status"] == "learned"
        assert result["project"] == "test-project"

    def test_learn_correction(self, mcp_server, clean_memory):
        """Learn a correction."""
        tool = mcp_server.get_tool("memory_learn")
        result = tool(
            category="correction",
            content="Use loguru instead of print",
            metadata={"mistake": "Used print() for logging"}
        )

        assert result["status"] == "learned"
        assert result["category"] == "correction"


class TestMemoryShow:
    """Tests for memory_show tool."""

    def test_show_all(self, mcp_server, clean_memory):
        """Show all memory."""
        # First learn something
        learn_tool = mcp_server.get_tool("memory_learn")
        learn_tool(category="preference", content="Test preference")

        # Then show
        show_tool = mcp_server.get_tool("memory_show")
        result = show_tool()

        assert "preferences" in result
        assert "Test preference" in str(result["preferences"])

    def test_show_by_category(self, mcp_server, clean_memory):
        """Show specific category."""
        show_tool = mcp_server.get_tool("memory_show")
        result = show_tool(category="preferences")

        assert "preferences" in result
        assert "decisions" not in result


class TestMemoryContext:
    """Tests for memory_context tool."""

    def test_context_generation(self, mcp_server, clean_memory):
        """Generate context for prompt injection."""
        # Learn some things first
        learn = mcp_server.get_tool("memory_learn")
        learn(category="preference", content="Use type hints")
        learn(category="preference", content="Prefer composition over inheritance")

        # Generate context
        context_tool = mcp_server.get_tool("memory_context")
        result = context_tool(compact=True)

        assert isinstance(result, str)
        assert "type hints" in result.lower() or "preferences" in result.lower()
```

### 7.4 Test Editing Tools

**File: `tests/test_mcp/test_editing_tools.py`:**
```python
"""Tests for editing MCP tools."""
import pytest


class TestEditSymbol:
    """Tests for edit_symbol tool."""

    def test_edit_function(self, indexed_project, mcp_server):
        """Edit a function implementation."""
        project, index_path = indexed_project
        import os
        os.chdir(project)

        tool = mcp_server.get_tool("edit_symbol")
        result = tool(
            name="hello",
            new_code='''def hello(name: str) -> str:
    """Greet someone enthusiastically."""
    return f"Hello, {name}! Welcome!"
'''
        )

        assert result["status"] == "success"
        assert "diff" in result

        # Verify the change
        content = (project / "src" / "main.py").read_text()
        assert "Welcome!" in content

    def test_edit_validates_syntax(self, indexed_project, mcp_server):
        """Edit rejects invalid syntax."""
        project, index_path = indexed_project
        import os
        os.chdir(project)

        tool = mcp_server.get_tool("edit_symbol")
        result = tool(
            name="hello",
            new_code="def hello(name  # missing closing paren"
        )

        assert result["status"] == "error"
        assert result["error_type"] == "syntax_error"


class TestInsertCode:
    """Tests for insert_code tool."""

    def test_insert_after(self, indexed_project, mcp_server):
        """Insert code after a line."""
        project, index_path = indexed_project
        import os
        os.chdir(project)

        tool = mcp_server.get_tool("insert_code")
        result = tool(
            file_path=str(project / "src" / "main.py"),
            line=1,
            code="# Inserted comment\n",
            position="after"
        )

        assert result["status"] == "success"

        content = (project / "src" / "main.py").read_text()
        lines = content.splitlines()
        assert "# Inserted comment" in lines[1]


class TestDeleteSymbol:
    """Tests for delete_symbol tool."""

    def test_delete_function(self, indexed_project, mcp_server):
        """Delete a function."""
        project, index_path = indexed_project
        import os
        os.chdir(project)

        # Verify function exists
        content_before = (project / "src" / "main.py").read_text()
        assert "def add" in content_before

        tool = mcp_server.get_tool("delete_symbol")
        result = tool(name="add")

        assert result["status"] == "success"

        # Verify function is gone
        content_after = (project / "src" / "main.py").read_text()
        assert "def add" not in content_after


class TestUndo:
    """Tests for undo tool."""

    def test_undo_edit(self, indexed_project, mcp_server):
        """Undo an edit."""
        project, index_path = indexed_project
        import os
        os.chdir(project)

        # Make an edit
        edit_tool = mcp_server.get_tool("edit_symbol")
        edit_tool(
            name="hello",
            new_code='def hello(name: str) -> str:\n    return "Changed!"\n'
        )

        # Verify change
        content = (project / "src" / "main.py").read_text()
        assert "Changed!" in content

        # Undo
        undo_tool = mcp_server.get_tool("undo")
        result = undo_tool()

        assert result["status"] == "success"

        # Verify undone
        content = (project / "src" / "main.py").read_text()
        assert "Changed!" not in content
```

### 7.5 Create User Documentation

**File: `docs/MCP-USER-GUIDE.md`:**
```markdown
# Cerberus MCP User Guide

## Quick Start

### Installation

```bash
pip install cerberus
```

### Configure Claude Code

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "cerberus": {
      "command": "cerberus-mcp",
      "cwd": "/path/to/your/project"
    }
  }
}
```

### First Use

1. Open your project in Claude Code
2. Ask Claude to index your project:

   "Please index this codebase so we can search it"

3. Start using Cerberus tools:

   "Search for authentication related code"
   "Show me the structure of src/auth.py"
   "What functions call `validate_user`?"

## Available Tools

### Reading & Search

| Tool | Description | Example |
|------|-------------|---------|
| `search` | Find code by keyword or natural language | "Search for database connection code" |
| `get_symbol` | Get a specific function/class with code | "Get the `UserService` class" |
| `read_range` | Read specific lines from a file | "Read lines 50-100 from api.py" |
| `blueprint` | Show file structure | "Show blueprint of models.py" |

### Memory (Cross-Project Learning)

| Tool | Description | Example |
|------|-------------|---------|
| `memory_learn` | Teach preferences/decisions | "Remember that I prefer early returns" |
| `memory_show` | View stored memory | "Show my coding preferences" |
| `memory_context` | Get context for prompts | (Used internally) |

### Code Editing

| Tool | Description | Example |
|------|-------------|---------|
| `edit_symbol` | Modify a function/class | "Update the `process` function to..." |
| `insert_code` | Add new code | "Add a new method to UserService" |
| `delete_symbol` | Remove code | "Delete the deprecated `old_handler`" |
| `undo` | Revert last change | "Undo that change" |

### Analysis

| Tool | Description | Example |
|------|-------------|---------|
| `deps` | Show dependencies | "What calls `authenticate`?" |
| `call_graph` | Trace execution paths | "Show call graph from `main`" |
| `style_check` | Check code style | "Check style of src/" |

## Tips

1. **Index first**: Always index before searching
2. **Use memory**: Teach Cerberus your preferences for better suggestions
3. **Blueprint before edit**: Understand structure before modifying
4. **Undo is your friend**: Don't worry about mistakes

## Configuration

Create `cerberus.toml` in your project root:

```toml
[index]
watch_extensions = [".py", ".ts", ".js"]

[memory]
# Memory is stored globally by default
# Override with project-specific settings here

[quality]
style_rules = ["black", "isort"]
```
```

### 7.6 Create Developer Documentation

**File: `docs/MCP-DEVELOPER-GUIDE.md`:**
```markdown
# Cerberus MCP Developer Guide

## Architecture

```
cerberus/
├── mcp/                 # MCP server layer
│   ├── server.py        # FastMCP server
│   ├── index_manager.py # Index lifecycle
│   └── tools/           # Tool implementations
│
├── parser/              # AST parsing
├── storage/             # SQLite + FAISS
├── retrieval/           # Search engine
├── mutation/            # Code editing
├── memory/              # Session memory
└── ...
```

## Adding a New Tool

1. Create tool in `src/cerberus/mcp/tools/`:

```python
def register(mcp):
    @mcp.tool()
    def my_new_tool(arg1: str, arg2: int = 10) -> dict:
        """
        Tool description for Claude.

        Args:
            arg1: First argument
            arg2: Second argument with default

        Returns:
            Result dictionary
        """
        # Implementation
        return {"status": "success", "data": result}
```

2. Register in `server.py`:

```python
from .tools import my_module

def create_server():
    # ...
    my_module.register(mcp)
```

3. Add tests in `tests/test_mcp/`

## Core Modules

### IndexManager

Handles lazy loading and file watching:

```python
from cerberus.mcp.index_manager import get_index_manager

manager = get_index_manager()
index = manager.get_index()  # Lazy loads
manager.invalidate()          # Force reload on next access
```

### Memory System

Cross-project developer memory:

```python
from cerberus.memory.store import MemoryStore
from cerberus.memory.profile import ProfileManager

store = MemoryStore()
profile = ProfileManager(store)
```

## Testing

```bash
# Run all MCP tests
pytest tests/test_mcp/ -v

# Run specific test
pytest tests/test_mcp/test_read_tools.py::TestSearchTool -v

# With coverage
pytest tests/test_mcp/ --cov=cerberus.mcp
```

## Debugging

Enable debug logging:

```python
import os
os.environ["CERBERUS_DEBUG"] = "1"
```

Or in config:

```toml
[logging]
level = "DEBUG"
```
```

### 7.7 Create Migration Guide

**File: `docs/MIGRATION-FROM-CLI.md`:**
```markdown
# Migrating from Cerberus CLI to MCP

## Overview

Cerberus 2.0 replaces the CLI with MCP (Model Context Protocol). This guide helps you transition.

## Command Mapping

| Old CLI Command | New MCP Tool | Notes |
|-----------------|--------------|-------|
| `cerberus index .` | `index_build` | Same functionality |
| `cerberus search "query"` | `search` | Enhanced with better ranking |
| `cerberus get-symbol Name` | `get_symbol` | Now uses FTS5 |
| `cerberus blueprint file.py` | `blueprint` | Same output |
| `cerberus go file.py` | `blueprint` + `read_range` | Split into two tools |
| `cerberus memory learn` | `memory_learn` | Same functionality |
| `cerberus memory show` | `memory_show` | Same functionality |
| `cerberus mutations edit` | `edit_symbol` | Same functionality |
| `cerberus symbolic deps` | `deps` | Same functionality |
| `cerberus quality style-check` | `style_check` | Same functionality |
| `cerberus metrics report` | `metrics_report` | Same functionality |

## What's Removed

- CLI entry point (`cerberus` command)
- Daemon subsystem (replaced by MCP)
- JSON-RPC protocol (replaced by MCP)
- Direct terminal output (now structured data)

## What's New

- Native Claude Code integration
- Direct Python function calls (no subprocess)
- Structured error responses
- Better tool discoverability

## Data Migration

Your existing data is preserved:

- **Index**: `.cerberus/cerberus.db` - works as-is
- **Memory**: `~/.cerberus/memory/` - works as-is
- **Config**: `cerberus.toml` - works as-is

## Getting Help

If you encounter issues:

1. Check the [User Guide](./MCP-USER-GUIDE.md)
2. Check the [Developer Guide](./MCP-DEVELOPER-GUIDE.md)
3. File an issue on GitHub
```

## Files to Create

```
tests/test_mcp/
├── __init__.py
├── conftest.py
├── test_read_tools.py
├── test_memory_tools.py
├── test_editing_tools.py
├── test_quality_tools.py
└── test_analysis_tools.py

docs/
├── MCP-USER-GUIDE.md
├── MCP-DEVELOPER-GUIDE.md
└── MIGRATION-FROM-CLI.md
```

## Acceptance Criteria

- [ ] All 24 tools have integration tests
- [ ] Tests cover success and error cases
- [ ] Tests use temporary directories (no side effects)
- [ ] User guide covers all common use cases
- [ ] Developer guide explains architecture
- [ ] Migration guide maps all CLI commands
- [ ] Documentation includes examples
- [ ] All tests pass in CI

## Dependencies

- Phase 1-6 completed
- MCP server fully functional
- CLI removed

## Notes

- Keep tests isolated (use tmp directories)
- Document any breaking changes
- Include troubleshooting sections
- Consider video walkthrough for users
