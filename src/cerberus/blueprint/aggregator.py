"""Package-level blueprint aggregator for cross-file architectural views.

Phase 13.3: Aggregates blueprints across multiple files in a package.
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Set
from collections import defaultdict

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol
from .schemas import Blueprint, BlueprintNode, SymbolOverlay


class AggregatedBlueprint:
    """Represents an aggregated blueprint across multiple files."""

    def __init__(
        self,
        package_path: str,
        files: List[str],
        nodes: List[BlueprintNode],
        total_symbols: int,
        total_files: int,
        cross_file_refs: Dict[str, List[str]],
    ):
        self.package_path = package_path
        self.files = files
        self.nodes = nodes
        self.total_symbols = total_symbols
        self.total_files = total_files
        self.cross_file_refs = cross_file_refs  # Maps symbol to files that reference it

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON output."""
        return {
            "package_path": self.package_path,
            "total_files": self.total_files,
            "total_symbols": self.total_symbols,
            "files": self.files,
            "nodes": [self._node_to_dict(node) for node in self.nodes],
            "cross_file_references": {
                symbol: {
                    "referenced_by_count": len(refs),
                    "referenced_by_files": refs
                }
                for symbol, refs in self.cross_file_refs.items()
                if len(refs) > 1  # Only include symbols referenced by multiple files
            }
        }

    def _node_to_dict(self, node: BlueprintNode) -> Dict:
        """Convert BlueprintNode to dict recursively."""
        result = {
            "name": node.name,
            "type": node.type,
            "file": node.file_path,
            "lines": f"{node.start_line}-{node.end_line}",
        }

        if node.overlay:
            result["overlay"] = {
                "dependencies": [
                    {"target": d.target, "confidence": d.confidence}
                    for d in node.overlay.dependencies or []
                ]
            }

        if node.children:
            result["children"] = [self._node_to_dict(child) for child in node.children]

        return result


class BlueprintAggregator:
    """Aggregates blueprints across multiple files in a package."""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize aggregator.

        Args:
            conn: SQLite connection to database
        """
        self.conn = conn

    def aggregate_package(
        self,
        package_path: Path,
        max_depth: Optional[int] = None,
        include_deps: bool = False
    ) -> AggregatedBlueprint:
        """
        Aggregate blueprints for all files in a package.

        Args:
            package_path: Path to package directory
            max_depth: Maximum directory depth to traverse (None = unlimited)
            include_deps: Whether to include dependency analysis

        Returns:
            AggregatedBlueprint object
        """
        try:
            # Get all Python files in the package
            files = self._get_package_files(package_path, max_depth)

            if not files:
                logger.warning(f"No files found in package {package_path}")
                return AggregatedBlueprint(
                    package_path=str(package_path),
                    files=[],
                    nodes=[],
                    total_symbols=0,
                    total_files=0,
                    cross_file_refs={}
                )

            # Aggregate symbols across all files
            all_nodes = []
            total_symbols = 0
            cross_file_refs = defaultdict(list)

            for file_path in files:
                # Get symbols for this file
                symbols = self._get_file_symbols(file_path)
                total_symbols += len(symbols)

                # Group symbols by file
                file_node = self._create_file_node(file_path, symbols)
                all_nodes.append(file_node)

                # Track cross-file references if dependencies enabled
                if include_deps:
                    self._track_cross_file_refs(file_path, symbols, cross_file_refs)

            # Sort nodes by file path
            all_nodes.sort(key=lambda n: n.file_path)

            return AggregatedBlueprint(
                package_path=str(package_path),
                files=[str(f) for f in files],
                nodes=all_nodes,
                total_symbols=total_symbols,
                total_files=len(files),
                cross_file_refs=dict(cross_file_refs)
            )

        except Exception as e:
            logger.error(f"Error aggregating package {package_path}: {e}")
            return AggregatedBlueprint(
                package_path=str(package_path),
                files=[],
                nodes=[],
                total_symbols=0,
                total_files=0,
                cross_file_refs={}
            )

    def _get_package_files(
        self,
        package_path: Path,
        max_depth: Optional[int]
    ) -> List[Path]:
        """
        Get all code files in a package directory.

        Args:
            package_path: Path to package
            max_depth: Maximum directory depth

        Returns:
            List of file paths
        """
        files = []
        package_path = package_path.resolve()

        # Get all files from database that are in this package
        try:
            cursor = self.conn.execute(
                """
                SELECT DISTINCT file_path
                FROM symbols
                WHERE file_path LIKE ?
                ORDER BY file_path
                """,
                (f"{package_path}%",)
            )

            for (file_path,) in cursor.fetchall():
                path = Path(file_path)

                # Check depth constraint
                if max_depth is not None:
                    try:
                        rel_path = path.relative_to(package_path)
                        depth = len(rel_path.parts) - 1  # -1 because file itself doesn't count
                        if depth > max_depth:
                            continue
                    except ValueError:
                        # Path is not relative to package_path
                        continue

                files.append(path)

        except Exception as e:
            logger.error(f"Error getting package files: {e}")

        return files

    def _get_file_symbols(self, file_path: Path) -> List[CodeSymbol]:
        """
        Get all symbols for a file from database.

        Args:
            file_path: File path

        Returns:
            List of CodeSymbol objects
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT
                    name, type, start_line, end_line,
                    signature, return_type, parameters, parameter_types, parent_class
                FROM symbols
                WHERE file_path = ?
                ORDER BY start_line ASC
                """,
                (str(file_path),)
            )

            symbols = []
            for row in cursor.fetchall():
                (
                    name, sym_type, start_line, end_line,
                    signature, return_type, parameters, parameter_types, parent_class
                ) = row

                # Normalize JSON-encoded fields from SQLite into Python types
                parsed_params = json.loads(parameters) if parameters else None
                parsed_param_types = json.loads(parameter_types) if parameter_types else None

                symbols.append(
                    CodeSymbol(
                        name=name,
                        type=sym_type,
                        file_path=str(file_path),
                        start_line=start_line,
                        end_line=end_line,
                        signature=signature,
                        return_type=return_type,
                        parameters=parsed_params,
                        parameter_types=parsed_param_types,
                        parent_class=parent_class
                    )
                )

            return symbols

        except Exception as e:
            logger.error(f"Error getting symbols for {file_path}: {e}")
            return []

    def _create_file_node(
        self,
        file_path: Path,
        symbols: List[CodeSymbol]
    ) -> BlueprintNode:
        """
        Create a blueprint node representing a file with its symbols.

        Args:
            file_path: File path
            symbols: Symbols in the file

        Returns:
            BlueprintNode representing the file
        """
        # Build hierarchy of symbols
        children = self._build_symbol_hierarchy(symbols)

        # Create file node
        file_node = BlueprintNode(
            name=file_path.name,
            type="file",
            file_path=str(file_path),
            start_line=1,
            end_line=max((s.end_line for s in symbols), default=0),
            children=children
        )

        return file_node

    def _build_symbol_hierarchy(self, symbols: List[CodeSymbol]) -> List[BlueprintNode]:
        """
        Build hierarchical structure from flat symbol list.

        Args:
            symbols: List of CodeSymbol objects

        Returns:
            List of top-level BlueprintNode objects
        """
        # Group by parent
        by_parent: Dict[Optional[str], List[CodeSymbol]] = defaultdict(list)
        for sym in symbols:
            by_parent[sym.parent_class].append(sym)

        # Build hierarchy recursively
        def build_children(parent_name: Optional[str]) -> List[BlueprintNode]:
            children = []
            for sym in by_parent.get(parent_name, []):
                node = BlueprintNode(
                    name=sym.name,
                    type=sym.type,
                    file_path=sym.file_path,
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    signature=sym.signature,
                    children=build_children(sym.name) if sym.type in ["class", "module"] else []
                )
                children.append(node)
            return children

        return build_children(None)

    def _track_cross_file_refs(
        self,
        file_path: Path,
        symbols: List[CodeSymbol],
        cross_file_refs: Dict[str, List[str]]
    ):
        """
        Track cross-file references for symbols.

        Args:
            file_path: Current file path
            symbols: Symbols in the file
            cross_file_refs: Dictionary to populate with references
        """
        # Query dependencies for symbols in this file
        for sym in symbols:
            # Check if this symbol is referenced from other files
            try:
                cursor = self.conn.execute(
                    """
                    SELECT DISTINCT d.source_file
                    FROM dependencies d
                    WHERE d.target_symbol = ? AND d.source_file != ?
                    """,
                    (sym.name, str(file_path))
                )

                for (source_file,) in cursor.fetchall():
                    cross_file_refs[sym.name].append(source_file)

            except Exception as e:
                logger.debug(f"Error tracking references for {sym.name}: {e}")
