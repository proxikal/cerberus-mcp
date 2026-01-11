"""Structural diff analyzer for comparing blueprints across git revisions.

Phase 13.3: Compares code structure (symbols, signatures) between git refs.
"""

import subprocess
import tempfile
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Literal
from enum import Enum

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol


class ChangeType(str, Enum):
    """Types of structural changes."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class StructuralChange:
    """Represents a structural change to a symbol."""

    def __init__(
        self,
        change_type: ChangeType,
        symbol_name: str,
        symbol_type: str,
        old_signature: Optional[str] = None,
        new_signature: Optional[str] = None,
        old_line: Optional[int] = None,
        new_line: Optional[int] = None,
    ):
        self.change_type = change_type
        self.symbol_name = symbol_name
        self.symbol_type = symbol_type
        self.old_signature = old_signature
        self.new_signature = new_signature
        self.old_line = old_line
        self.new_line = new_line

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON output."""
        return {
            "change_type": self.change_type.value,
            "symbol_name": self.symbol_name,
            "symbol_type": self.symbol_type,
            "old_signature": self.old_signature,
            "new_signature": self.new_signature,
            "old_line": self.old_line,
            "new_line": self.new_line,
        }


class DiffAnalyzer:
    """Analyzes structural differences between git revisions."""

    def __init__(self, conn: sqlite3.Connection, repo_path: Path):
        """
        Initialize diff analyzer.

        Args:
            conn: SQLite connection to current index
            repo_path: Path to git repository root
        """
        self.conn = conn
        self.repo_path = repo_path

    def analyze_diff(
        self,
        file_path: str,
        git_ref: str
    ) -> List[StructuralChange]:
        """
        Analyze structural differences between current version and git ref.

        Args:
            file_path: Absolute path to file
            git_ref: Git reference (e.g., 'HEAD~1', 'main', 'v1.0.0')

        Returns:
            List of StructuralChange objects
        """
        try:
            # Get current symbols from database
            current_symbols = self._get_current_symbols(file_path)

            # Get symbols from git ref
            old_symbols = self._get_symbols_from_git_ref(file_path, git_ref)

            # Compare and identify changes
            changes = self._compare_symbols(old_symbols, current_symbols)

            return changes

        except Exception as e:
            logger.error(f"Error analyzing diff for {file_path} at {git_ref}: {e}")
            return []

    def _get_current_symbols(self, file_path: str) -> Dict[str, CodeSymbol]:
        """
        Get current symbols from database.

        Args:
            file_path: Absolute file path

        Returns:
            Dict mapping (name, type, parent) to CodeSymbol
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT
                    name, type, start_line, end_line,
                    signature, return_type, parameters, parent_class
                FROM symbols
                WHERE file_path = ?
                ORDER BY start_line ASC
                """,
                (file_path,)
            )

            symbols = {}
            for row in cursor.fetchall():
                (
                    name, sym_type, start_line, end_line,
                    signature, return_type, parameters, parent_class
                ) = row

                # Create unique key
                key = (name, sym_type, parent_class or "")

                # Parse parameters from JSON string if needed
                import json as json_lib
                params_list = None
                if parameters:
                    try:
                        params_list = json_lib.loads(parameters) if isinstance(parameters, str) else parameters
                    except (json_lib.JSONDecodeError, TypeError):
                        params_list = None

                symbols[key] = CodeSymbol(
                    name=name,
                    type=sym_type,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    signature=signature,
                    return_type=return_type,
                    parameters=params_list,
                    parent_class=parent_class
                )

            return symbols

        except Exception as e:
            logger.error(f"Error getting current symbols for {file_path}: {e}")
            return {}

    def _get_symbols_from_git_ref(
        self,
        file_path: str,
        git_ref: str
    ) -> Dict[str, CodeSymbol]:
        """
        Get symbols from a specific git ref by parsing the file at that revision.

        Args:
            file_path: Absolute file path
            git_ref: Git reference

        Returns:
            Dict mapping (name, type, parent) to CodeSymbol
        """
        try:
            # Convert absolute path to relative path from repo root
            abs_file_path = Path(file_path).resolve()
            repo_root = Path(self.repo_path).resolve()
            rel_path = abs_file_path.relative_to(repo_root)

            # Get file content from git
            result = subprocess.run(
                ["git", "show", f"{git_ref}:{rel_path}"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=True
            )

            file_content = result.stdout

            # Parse the content to extract symbols
            # Use Cerberus parsers directly
            from cerberus.parser.python_parser import parse_python_file
            from cerberus.parser.javascript_parser import parse_javascript_file
            from cerberus.parser.typescript_parser import parse_typescript_file
            from cerberus.parser.go_parser import parse_go_file

            # Determine language from file extension
            extension = abs_file_path.suffix
            parser_map = {
                ".py": parse_python_file,
                ".js": parse_javascript_file,
                ".ts": parse_typescript_file,
                ".go": parse_go_file
            }
            parser_func = parser_map.get(extension)

            if not parser_func:
                logger.warning(f"Unsupported file extension: {extension}")
                return {}

            # Parse the old version
            parsed_symbols = parser_func(abs_file_path, file_content)

            # Convert to dict with same key format
            symbols = {}
            for sym in parsed_symbols:
                key = (sym.name, sym.type, sym.parent_class or "")
                symbols[key] = sym

            return symbols

        except subprocess.CalledProcessError:
            # File might not exist in that ref
            logger.info(f"File {file_path} not found at {git_ref}")
            return {}
        except Exception as e:
            logger.error(f"Error getting symbols from git ref {git_ref}: {e}")
            return {}

    def _compare_symbols(
        self,
        old_symbols: Dict[str, CodeSymbol],
        new_symbols: Dict[str, CodeSymbol]
    ) -> List[StructuralChange]:
        """
        Compare symbol dictionaries and identify changes.

        Args:
            old_symbols: Symbols from old revision
            new_symbols: Symbols from current revision

        Returns:
            List of StructuralChange objects
        """
        changes = []

        old_keys = set(old_symbols.keys())
        new_keys = set(new_symbols.keys())

        # Added symbols
        for key in new_keys - old_keys:
            sym = new_symbols[key]
            changes.append(StructuralChange(
                change_type=ChangeType.ADDED,
                symbol_name=sym.name,
                symbol_type=sym.type,
                new_signature=sym.signature,
                new_line=sym.start_line
            ))

        # Removed symbols
        for key in old_keys - new_keys:
            sym = old_symbols[key]
            changes.append(StructuralChange(
                change_type=ChangeType.REMOVED,
                symbol_name=sym.name,
                symbol_type=sym.type,
                old_signature=sym.signature,
                old_line=sym.start_line
            ))

        # Modified symbols (same key, different signature)
        for key in old_keys & new_keys:
            old_sym = old_symbols[key]
            new_sym = new_symbols[key]

            # Check if signature changed
            if old_sym.signature != new_sym.signature:
                changes.append(StructuralChange(
                    change_type=ChangeType.MODIFIED,
                    symbol_name=new_sym.name,
                    symbol_type=new_sym.type,
                    old_signature=old_sym.signature,
                    new_signature=new_sym.signature,
                    old_line=old_sym.start_line,
                    new_line=new_sym.start_line
                ))

        # Sort by line number (new line for added/modified, old line for removed)
        changes.sort(key=lambda c: c.new_line if c.new_line else c.old_line or 0)

        return changes
