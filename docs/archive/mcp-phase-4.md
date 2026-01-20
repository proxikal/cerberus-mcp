# Phase 4: Editing Tools + Undo

## Overview

Implement code editing tools with full undo support. These are "dangerous" tools that modify files, so they need careful implementation with safety checks.

## Goals

- Surgical AST-based code editing (not string replacement)
- Full undo stack for reverting changes
- Validation before applying edits
- Backup creation for safety
- Clear diff output showing what changed

## Tasks

### 4.1 Create Editing Tools Module

**File: `src/cerberus/mcp/tools/editing.py`**
```python
"""Code editing tools - surgical AST-based modifications."""
from typing import Optional, List
from pathlib import Path

from cerberus.mutation import (
    edit_symbol,
    delete_symbol,
    insert_code,
    undo_last,
    get_undo_stack,
    validate_syntax
)
from cerberus.mutation.ledger import DiffLedger
from ..index_manager import get_index_manager


def register(mcp):

    # Shared ledger for undo tracking
    _ledger = None

    def get_ledger():
        nonlocal _ledger
        if _ledger is None:
            _ledger = DiffLedger()
        return _ledger

    @mcp.tool()
    def edit_symbol(
        name: str,
        new_code: str,
        file_path: Optional[str] = None,
        validate: bool = True,
        create_backup: bool = True
    ) -> dict:
        """
        Surgically edit a symbol's implementation.

        Uses AST-based editing to replace a function, class, or method
        while preserving surrounding code and formatting.

        Args:
            name: Symbol name to edit (e.g., "my_function", "MyClass.method")
            new_code: New implementation code
            file_path: Optional file path if symbol name is ambiguous
            validate: Validate syntax before applying (default: True)
            create_backup: Create .bak file before editing (default: True)

        Returns:
            Success status with diff of changes

        Example:
            edit_symbol("calculate_total", '''
            def calculate_total(items: List[Item]) -> float:
                \"\"\"Calculate total with tax.\"\"\"
                subtotal = sum(item.price for item in items)
                return subtotal * 1.08  # 8% tax
            ''')
        """
        # Validate syntax first
        if validate:
            is_valid, error = validate_syntax(new_code)
            if not is_valid:
                return {
                    "status": "error",
                    "error_type": "syntax_error",
                    "message": f"Invalid syntax in new code: {error}"
                }

        # Find the symbol
        manager = get_index_manager()
        index = manager.get_index()

        from cerberus.retrieval.utils import find_symbol_fts
        matches = find_symbol_fts(name, index, exact=True)

        if not matches:
            return {
                "status": "error",
                "error_type": "symbol_not_found",
                "message": f"Symbol '{name}' not found in index"
            }

        # Filter by file path if specified
        if file_path:
            matches = [m for m in matches if m.file_path == file_path or m.file_path.endswith(file_path)]

        if len(matches) > 1:
            return {
                "status": "error",
                "error_type": "ambiguous_symbol",
                "message": f"Multiple symbols named '{name}' found. Specify file_path.",
                "candidates": [{"file": m.file_path, "line": m.start_line} for m in matches]
            }

        symbol = matches[0]

        # Perform the edit
        try:
            from cerberus.mutation.facade import MutationFacade
            facade = MutationFacade()

            result = facade.edit_symbol(
                file_path=symbol.file_path,
                symbol_name=name,
                new_code=new_code,
                create_backup=create_backup
            )

            # Record in ledger for undo
            ledger = get_ledger()
            ledger.record_edit(
                file_path=symbol.file_path,
                symbol_name=name,
                old_code=result.get("old_code", ""),
                new_code=new_code
            )

            # Invalidate index cache
            manager.invalidate()

            return {
                "status": "success",
                "file": symbol.file_path,
                "symbol": name,
                "diff": result.get("diff", ""),
                "backup": result.get("backup_path") if create_backup else None
            }

        except Exception as e:
            return {
                "status": "error",
                "error_type": "edit_failed",
                "message": str(e)
            }

    @mcp.tool()
    def insert_code(
        file_path: str,
        line: int,
        code: str,
        position: str = "after",
        validate: bool = True
    ) -> dict:
        """
        Insert new code at a specific location.

        Args:
            file_path: Path to file
            line: Line number for insertion point
            code: Code to insert
            position: "before" or "after" the specified line
            validate: Validate syntax after insertion

        Returns:
            Success status with updated line numbers
        """
        path = Path(file_path)
        if not path.exists():
            return {
                "status": "error",
                "error_type": "file_not_found",
                "message": f"File not found: {file_path}"
            }

        try:
            from cerberus.mutation.facade import MutationFacade
            facade = MutationFacade()

            result = facade.insert_code(
                file_path=str(path),
                line=line,
                code=code,
                position=position
            )

            # Validate result if requested
            if validate:
                content = path.read_text()
                is_valid, error = validate_syntax(content, path.suffix)
                if not is_valid:
                    # Rollback
                    facade.undo_last()
                    return {
                        "status": "error",
                        "error_type": "syntax_error",
                        "message": f"Insertion created invalid syntax: {error}",
                        "rolled_back": True
                    }

            # Record for undo
            ledger = get_ledger()
            ledger.record_insert(
                file_path=str(path),
                line=line,
                code=code
            )

            # Invalidate index
            get_index_manager().invalidate()

            return {
                "status": "success",
                "file": str(path),
                "inserted_at": line,
                "lines_added": len(code.splitlines())
            }

        except Exception as e:
            return {
                "status": "error",
                "error_type": "insert_failed",
                "message": str(e)
            }

    @mcp.tool()
    def delete_symbol(
        name: str,
        file_path: Optional[str] = None,
        create_backup: bool = True
    ) -> dict:
        """
        Delete a symbol from the codebase.

        Removes the entire function, class, or method definition.

        Args:
            name: Symbol name to delete
            file_path: Optional file path if ambiguous
            create_backup: Create .bak file before deletion

        Returns:
            Success status with deleted line range
        """
        manager = get_index_manager()
        index = manager.get_index()

        from cerberus.retrieval.utils import find_symbol_fts
        matches = find_symbol_fts(name, index, exact=True)

        if not matches:
            return {
                "status": "error",
                "error_type": "symbol_not_found",
                "message": f"Symbol '{name}' not found"
            }

        if file_path:
            matches = [m for m in matches if m.file_path == file_path or m.file_path.endswith(file_path)]

        if len(matches) > 1:
            return {
                "status": "error",
                "error_type": "ambiguous_symbol",
                "message": f"Multiple symbols named '{name}'. Specify file_path.",
                "candidates": [{"file": m.file_path, "line": m.start_line} for m in matches]
            }

        symbol = matches[0]

        try:
            from cerberus.mutation.facade import MutationFacade
            facade = MutationFacade()

            # Get old code for undo
            from cerberus.retrieval.utils import read_range
            old_snippet = read_range(
                Path(symbol.file_path),
                symbol.start_line,
                symbol.end_line,
                padding=0
            )

            result = facade.delete_symbol(
                file_path=symbol.file_path,
                symbol_name=name,
                create_backup=create_backup
            )

            # Record for undo
            ledger = get_ledger()
            ledger.record_delete(
                file_path=symbol.file_path,
                symbol_name=name,
                old_code=old_snippet.content,
                start_line=symbol.start_line
            )

            manager.invalidate()

            return {
                "status": "success",
                "file": symbol.file_path,
                "symbol": name,
                "deleted_lines": f"{symbol.start_line}-{symbol.end_line}",
                "backup": result.get("backup_path") if create_backup else None
            }

        except Exception as e:
            return {
                "status": "error",
                "error_type": "delete_failed",
                "message": str(e)
            }

    @mcp.tool()
    def undo() -> dict:
        """
        Undo the last code modification.

        Reverts the most recent edit_symbol, insert_code, or delete_symbol operation.

        Returns:
            Details of what was undone
        """
        ledger = get_ledger()
        last_action = ledger.get_last_action()

        if not last_action:
            return {
                "status": "error",
                "error_type": "nothing_to_undo",
                "message": "No actions to undo"
            }

        try:
            from cerberus.mutation.facade import MutationFacade
            facade = MutationFacade()

            result = facade.undo_last()

            # Pop from ledger
            ledger.pop_last_action()

            # Invalidate index
            get_index_manager().invalidate()

            return {
                "status": "success",
                "undone_action": last_action.get("action_type"),
                "file": last_action.get("file_path"),
                "symbol": last_action.get("symbol_name")
            }

        except Exception as e:
            return {
                "status": "error",
                "error_type": "undo_failed",
                "message": str(e)
            }

    @mcp.tool()
    def undo_history(limit: int = 10) -> dict:
        """
        Show recent undo history.

        Args:
            limit: Maximum entries to show

        Returns:
            List of recent actions that can be undone
        """
        ledger = get_ledger()
        stack = ledger.get_undo_stack(limit=limit)

        return {
            "count": len(stack),
            "actions": [
                {
                    "action": action.get("action_type"),
                    "file": action.get("file_path"),
                    "symbol": action.get("symbol_name"),
                    "timestamp": action.get("timestamp")
                }
                for action in stack
            ]
        }
```

### 4.2 Create Syntax Validation Helper

**File: `src/cerberus/mcp/validation.py`**
```python
"""Syntax validation utilities."""
import ast
from typing import Tuple, Optional


def validate_syntax(code: str, file_extension: str = ".py") -> Tuple[bool, Optional[str]]:
    """
    Validate code syntax.

    Args:
        code: Code to validate
        file_extension: File type for language detection

    Returns:
        Tuple of (is_valid, error_message)
    """
    if file_extension in [".py", ""]:
        return _validate_python(code)
    elif file_extension in [".js", ".jsx"]:
        return _validate_javascript(code)
    elif file_extension in [".ts", ".tsx"]:
        return _validate_typescript(code)
    else:
        # Unknown language - assume valid
        return True, None


def _validate_python(code: str) -> Tuple[bool, Optional[str]]:
    """Validate Python syntax using AST."""
    try:
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, f"Line {e.lineno}: {e.msg}"


def _validate_javascript(code: str) -> Tuple[bool, Optional[str]]:
    """Validate JavaScript syntax (basic check)."""
    # TODO: Use a proper JS parser
    # For now, check balanced braces
    try:
        braces = 0
        parens = 0
        brackets = 0
        in_string = False
        string_char = None

        for char in code:
            if in_string:
                if char == string_char:
                    in_string = False
            else:
                if char in '"\'`':
                    in_string = True
                    string_char = char
                elif char == '{':
                    braces += 1
                elif char == '}':
                    braces -= 1
                elif char == '(':
                    parens += 1
                elif char == ')':
                    parens -= 1
                elif char == '[':
                    brackets += 1
                elif char == ']':
                    brackets -= 1

        if braces != 0 or parens != 0 or brackets != 0:
            return False, "Unbalanced brackets/braces/parentheses"

        return True, None
    except Exception as e:
        return False, str(e)


def _validate_typescript(code: str) -> Tuple[bool, Optional[str]]:
    """Validate TypeScript syntax (same as JS for basic check)."""
    return _validate_javascript(code)
```

### 4.3 Update Server Registration

**Update `src/cerberus/mcp/server.py`:**
```python
"""FastMCP server setup and tool registration."""
from fastmcp import FastMCP

from .tools import search, symbols, reading, indexing, memory, structure, editing

mcp = FastMCP("cerberus")

def create_server():
    """Create and configure the MCP server."""
    # Read tools
    search.register(mcp)
    symbols.register(mcp)
    reading.register(mcp)
    structure.register(mcp)

    # Index management
    indexing.register(mcp)

    # Memory system
    memory.register(mcp)

    # Editing tools (dangerous - modify files)
    editing.register(mcp)

    return mcp

def run_server():
    """Run the MCP server."""
    server = create_server()
    server.run()
```

## Files to Create/Modify

```
src/cerberus/mcp/
├── server.py           # MODIFIED - add editing registration
├── validation.py       # NEW - syntax validation
└── tools/
    └── editing.py      # NEW - edit/insert/delete/undo tools
```

## Acceptance Criteria

- [ ] `edit_symbol` replaces symbol implementation correctly
- [ ] `edit_symbol` validates syntax before applying
- [ ] `edit_symbol` creates backup files
- [ ] `insert_code` adds code at correct location
- [ ] `insert_code` handles "before" and "after" positions
- [ ] `delete_symbol` removes entire symbol definition
- [ ] `delete_symbol` handles method deletion (Class.method)
- [ ] `undo` reverts the last change
- [ ] `undo_history` shows recent actions
- [ ] Multiple undos work in sequence (stack behavior)
- [ ] Index is invalidated after each edit
- [ ] Ambiguous symbol names return helpful error
- [ ] Syntax errors are caught before applying changes

## Dependencies

- Phase 1 completed (MCP server)
- Phase 2 completed (IndexManager)
- Phase 3 completed (memory for context)

## Safety Notes

- Always validate syntax before applying edits
- Create backups by default
- Undo stack should persist across tool calls (in-memory is OK for session)
- Consider adding confirmation for destructive operations
- Log all edits for audit trail
