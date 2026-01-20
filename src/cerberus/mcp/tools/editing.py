"""
⚠️  DEPRECATED - DO NOT USE WITH MCP ⚠️

Code editing tools - surgical AST-based modifications.

DEPRECATION NOTICE:
==================
These editing tools are DEPRECATED and NOT registered in the MCP server.
They were experimental tools for testing purposes only.

AI agents should use their native Edit/Write tools instead, which are:
- More efficient
- Better integrated with the agent's workflow
- More reliable for code modifications

This module is kept in the codebase for reference but is NOT active.
DO NOT register these tools in src/cerberus/mcp/server.py

If you need code editing via MCP, AI agents already have superior
built-in tools (Edit, Write) that work better than these experimental
implementations.
"""
from pathlib import Path
from typing import List, Optional

from cerberus.mutation.editor import CodeEditor
from cerberus.mutation.facade import MutationFacade
from cerberus.mutation.undo import UndoStack
from cerberus.retrieval.utils import find_symbol_fts, read_range

from ..index_manager import get_index_manager
from ..validation import validate_syntax


def register(mcp):
    """
    ⚠️  DEPRECATED - DO NOT CALL THIS FUNCTION ⚠️

    These editing tools are DEPRECATED and should NOT be registered.
    They were experimental/testing tools only.

    AI agents should use their native Edit/Write tools instead.

    This function is NOT called in src/cerberus/mcp/server.py and
    should remain unregistered.
    """
    # Shared undo stack across tool calls (persists on disk)
    _undo = UndoStack()

    def _get_sqlite_store():
        """Fetch SQLite index store or return error dict."""
        manager = get_index_manager()
        index = manager.get_index()
        if not hasattr(index, "_store"):
            return None, {
                "status": "error",
                "error_type": "index_required",
                "message": "Editing tools require SQLite index. Run index_build to create .cerberus/cerberus.db.",
            }
        return index._store, manager

    def _record_undo(operation: str, file_path: str, original_content: str):
        """Record reverse patch for undo."""
        return _undo.record_transaction(
            operation_type=operation,
            files=[file_path],
            reverse_patches=[{"file_path": file_path, "original_content": original_content}],
        )

    @mcp.tool()
    def edit_symbol(
        name: str,
        new_code: str,
        file_path: Optional[str] = None,
        validate: bool = True,
        create_backup: bool = True,
    ) -> dict:
        """
        ⚠️  DEPRECATED - DO NOT USE ⚠️

        This tool is deprecated and NOT registered in the MCP server.
        Use native Edit/Write tools instead.

        Surgically edit a symbol's implementation.
        """
        if validate:
            is_valid, error = validate_syntax(new_code)
            if not is_valid:
                return {
                    "status": "error",
                    "error_type": "syntax_error",
                    "message": f"Invalid syntax in new code: {error}",
                }

        store, manager_or_error = _get_sqlite_store()
        if store is None:
            return manager_or_error
        manager = manager_or_error

        index = manager.get_index()
        matches = find_symbol_fts(name, index, exact=True)
        # Deduplicate identical entries (FTS can emit dupes)
        seen = set()
        unique_matches = []
        for m in matches:
            key = (m.file_path, m.start_line, m.end_line)
            if key not in seen:
                seen.add(key)
                unique_matches.append(m)
        matches = unique_matches

        if file_path:
            matches = [
                m for m in matches if m.file_path == file_path or m.file_path.endswith(file_path)
            ]

        if not matches:
            return {
                "status": "error",
                "error_type": "symbol_not_found",
                "message": f"Symbol '{name}' not found in index",
            }
        if len(matches) > 1:
            return {
                "status": "error",
                "error_type": "ambiguous_symbol",
                "message": f"Multiple symbols named '{name}' found. Specify file_path.",
                "candidates": [{"file": m.file_path, "line": m.start_line} for m in matches],
            }

        symbol = matches[0]
        target_path = symbol.file_path

        original_content = Path(target_path).read_text(encoding="utf-8", errors="ignore")

        facade = MutationFacade(store)
        result = facade.edit_symbol(
            file_path=target_path,
            symbol_name=name,
            new_code=new_code,
            force=True,  # allow edits from agent tools
        )

        if not result.success:
            return {
                "status": "error",
                "error_type": "edit_failed",
                "message": "; ".join(result.errors or ["Unknown error"]),
            }

        # Record undo and invalidate index
        _record_undo("edit", target_path, original_content)
        manager.invalidate()

        return {
            "status": "success",
            "file": target_path,
            "symbol": name,
            "diff": result.diff,
            "backup": result.backup_path if create_backup else None,
            "lines_changed": result.lines_changed,
        }

    @mcp.tool()
    def insert_code(
        file_path: str,
        line: int,
        code: str,
        position: str = "after",
        validate: bool = True,
    ) -> dict:
        """
        ⚠️  DEPRECATED - DO NOT USE ⚠️

        This tool is deprecated and NOT registered in the MCP server.
        Use native Write tools instead.

        Insert new code at a specific location.
        """
        path = Path(file_path)
        if not path.exists():
            return {
                "status": "error",
                "error_type": "file_not_found",
                "message": f"File not found: {file_path}",
            }

        original_content = path.read_text(encoding="utf-8", errors="ignore")

        lines = original_content.splitlines(keepends=True)
        insert_idx = max(0, min(len(lines), line - 1))
        if position == "after":
            insert_idx += 1

        code_block = code if code.endswith("\n") else code + "\n"
        new_content = "".join(lines[:insert_idx] + [code_block] + lines[insert_idx:])

        if validate:
            is_valid, error = validate_syntax(new_content, path.suffix)
            if not is_valid:
                return {
                    "status": "error",
                    "error_type": "syntax_error",
                    "message": f"Insertion created invalid syntax: {error}",
                }

        # Use CodeEditor for backup + atomic write
        editor = CodeEditor()
        byte_offset = sum(len(l.encode("utf-8")) for l in lines[:insert_idx])
        success, backup_path = editor.insert_symbol(str(path), byte_offset, code_block)

        if not success:
            return {
                "status": "error",
                "error_type": "insert_failed",
                "message": "Insert operation failed",
            }

        _record_undo("insert", str(path), original_content)
        get_index_manager().invalidate()

        return {
            "status": "success",
            "file": str(path),
            "inserted_at": line,
            "lines_added": len(code_block.splitlines()),
            "backup": backup_path,
        }

    @mcp.tool()
    def delete_symbol(
        name: str,
        file_path: Optional[str] = None,
        create_backup: bool = True,
    ) -> dict:
        """
        ⚠️  DEPRECATED - DO NOT USE ⚠️

        This tool is deprecated and NOT registered in the MCP server.
        Use native Edit tools instead.

        Delete a symbol from the codebase.
        """
        store, manager_or_error = _get_sqlite_store()
        if store is None:
            return manager_or_error
        manager = manager_or_error

        index = manager.get_index()
        matches = find_symbol_fts(name, index, exact=True)
        if file_path:
            matches = [
                m for m in matches if m.file_path == file_path or m.file_path.endswith(file_path)
            ]

        if not matches:
            return {
                "status": "error",
                "error_type": "symbol_not_found",
                "message": f"Symbol '{name}' not found",
            }
        if len(matches) > 1:
            return {
                "status": "error",
                "error_type": "ambiguous_symbol",
                "message": f"Multiple symbols named '{name}'. Specify file_path.",
                "candidates": [{"file": m.file_path, "line": m.start_line} for m in matches],
            }

        symbol = matches[0]
        target_path = symbol.file_path
        original_snippet = read_range(Path(target_path), symbol.start_line, symbol.end_line, padding=0)
        original_content = Path(target_path).read_text(encoding="utf-8", errors="ignore")

        facade = MutationFacade(store)
        result = facade.delete_symbol(
            file_path=target_path,
            symbol_name=name,
            keep_decorators=not create_backup,  # follow existing signature; backups handled by editor
            force=True,
        )

        if not result.success:
            return {
                "status": "error",
                "error_type": "delete_failed",
                "message": "; ".join(result.errors or ["Unknown error"]),
            }

        _record_undo("delete", target_path, original_content)
        manager.invalidate()

        return {
            "status": "success",
            "file": target_path,
            "symbol": name,
            "deleted_lines": f"{symbol.start_line}-{symbol.end_line}",
            "backup": result.backup_path if create_backup else None,
            "removed_code": original_snippet.content,
        }

    @mcp.tool()
    def undo() -> dict:
        """
        ⚠️  DEPRECATED - DO NOT USE ⚠️

        This tool is deprecated and NOT registered in the MCP server.

        Undo the last code modification.

        Reverts the most recent edit_symbol, insert_code, or delete_symbol
        operation by restoring the original file content.

        Returns:
            dict with:
            - status: "success" or "error"
            - undone_action: Type of action that was undone (edit, insert, delete)
            - files: List of files that were restored
            - error_type: (on error) Type of error
            - message: (on error) Error description
        """
        history = _undo.get_history(limit=1)
        if not history:
            return {
                "status": "error",
                "error_type": "nothing_to_undo",
                "message": "No actions to undo",
            }

        last = history[0]
        transaction_id = last.get("transaction_id")
        success, files, errors = _undo.apply_reverse_patches(transaction_id)

        if success:
            # Remove history entry after applying
            history_file = _undo.history_dir / f"{transaction_id}.json"
            if history_file.exists():
                history_file.unlink()
            get_index_manager().invalidate()
            return {
                "status": "success",
                "undone_action": last.get("operation_type"),
                "files": files,
            }

        return {
            "status": "error",
            "error_type": "undo_failed",
            "message": "; ".join(errors),
        }

    @mcp.tool()
    def undo_history(limit: int = 10) -> dict:
        """
        ⚠️  DEPRECATED - DO NOT USE ⚠️

        This tool is deprecated and NOT registered in the MCP server.

        Show recent undo history.

        Lists recent code modifications that can be undone, showing what
        actions were performed and which files were affected.

        Args:
            limit: Maximum number of history entries to return (default: 10)

        Returns:
            dict with:
            - count: Number of actions in history
            - actions: List of {action, files, timestamp} for each undoable operation
        """
        stack = _undo.get_history(limit=limit)
        return {
            "count": len(stack),
            "actions": [
                {
                    "action": action.get("operation_type"),
                    "files": action.get("files"),
                    "timestamp": action.get("timestamp"),
                }
                for action in stack
            ],
        }
