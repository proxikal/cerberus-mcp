"""Cycle detector for identifying circular dependencies in code.

Phase 13.3: Detects import cycles, call cycles, and inheritance cycles.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict, deque

from cerberus.logging_config import logger


class CycleType:
    """Types of cycles that can be detected."""
    IMPORT = "import_cycle"  # File-level import cycles
    CALL = "call_cycle"      # Function call cycles
    INHERITANCE = "inheritance_cycle"  # Class inheritance cycles


class Cycle:
    """Represents a detected circular dependency."""

    def __init__(
        self,
        cycle_type: str,
        path: List[str],
        files: Optional[List[str]] = None
    ):
        """
        Initialize cycle.

        Args:
            cycle_type: Type of cycle (import, call, inheritance)
            path: List of symbols in the cycle path
            files: Optional list of files involved
        """
        self.cycle_type = cycle_type
        self.path = path
        self.files = files or []

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON output."""
        return {
            "cycle_type": self.cycle_type,
            "path": self.path,
            "cycle_length": len(self.path),
            "files": self.files
        }

    def __str__(self) -> str:
        """String representation of cycle."""
        path_str = " → ".join(self.path) + " → " + self.path[0]
        return f"{self.cycle_type}: {path_str}"


class CycleDetector:
    """Detects circular dependencies in code."""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize cycle detector.

        Args:
            conn: SQLite connection to database
        """
        self.conn = conn

    def detect_cycles(
        self,
        file_path: Optional[str] = None,
        detect_imports: bool = True,
        detect_calls: bool = True,
        detect_inheritance: bool = True
    ) -> List[Cycle]:
        """
        Detect all types of cycles.

        Args:
            file_path: Optional file path to limit scope (None = whole codebase)
            detect_imports: Whether to detect import cycles
            detect_calls: Whether to detect call cycles
            detect_inheritance: Whether to detect inheritance cycles

        Returns:
            List of Cycle objects
        """
        cycles = []

        try:
            if detect_imports:
                import_cycles = self._detect_import_cycles(file_path)
                cycles.extend(import_cycles)

            if detect_calls:
                call_cycles = self._detect_call_cycles(file_path)
                cycles.extend(call_cycles)

            if detect_inheritance:
                inheritance_cycles = self._detect_inheritance_cycles(file_path)
                cycles.extend(inheritance_cycles)

        except Exception as e:
            logger.error(f"Error detecting cycles: {e}")

        return cycles

    def _detect_import_cycles(self, file_path: Optional[str]) -> List[Cycle]:
        """
        Detect import cycles at file level.

        Args:
            file_path: Optional file path to limit scope

        Returns:
            List of import Cycle objects
        """
        cycles = []

        try:
            # Build import graph
            import_graph = self._build_import_graph(file_path)

            # Find cycles using DFS
            visited = set()
            rec_stack = []

            def dfs(node: str, path: List[str]) -> None:
                visited.add(node)
                rec_stack.append(node)
                path.append(node)

                for neighbor in import_graph.get(node, []):
                    if neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = rec_stack.index(neighbor)
                        cycle_path = rec_stack[cycle_start:] + [neighbor]
                        cycles.append(Cycle(
                            cycle_type=CycleType.IMPORT,
                            path=cycle_path,
                            files=cycle_path
                        ))
                    elif neighbor not in visited:
                        dfs(neighbor, path[:])

                rec_stack.pop()

            for node in import_graph:
                if node not in visited:
                    dfs(node, [])

        except Exception as e:
            logger.error(f"Error detecting import cycles: {e}")

        return cycles

    def _detect_call_cycles(self, file_path: Optional[str]) -> List[Cycle]:
        """
        Detect call cycles at function level.

        Args:
            file_path: Optional file path to limit scope

        Returns:
            List of call Cycle objects
        """
        cycles = []

        try:
            # Build call graph
            call_graph = self._build_call_graph(file_path)

            # Find cycles
            visited = set()
            rec_stack = []

            def dfs(node: str) -> None:
                visited.add(node)
                rec_stack.append(node)

                for neighbor in call_graph.get(node, []):
                    if neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = rec_stack.index(neighbor)
                        cycle_path = rec_stack[cycle_start:]
                        cycles.append(Cycle(
                            cycle_type=CycleType.CALL,
                            path=cycle_path
                        ))
                    elif neighbor not in visited:
                        dfs(neighbor)

                rec_stack.pop()

            for node in call_graph:
                if node not in visited:
                    dfs(node)

        except Exception as e:
            logger.error(f"Error detecting call cycles: {e}")

        return cycles

    def _detect_inheritance_cycles(self, file_path: Optional[str]) -> List[Cycle]:
        """
        Detect inheritance cycles at class level.

        Args:
            file_path: Optional file path to limit scope

        Returns:
            List of inheritance Cycle objects
        """
        cycles = []

        try:
            # Build inheritance graph
            inheritance_graph = self._build_inheritance_graph(file_path)

            # Find cycles
            visited = set()
            rec_stack = []

            def dfs(node: str) -> None:
                visited.add(node)
                rec_stack.append(node)

                for neighbor in inheritance_graph.get(node, []):
                    if neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = rec_stack.index(neighbor)
                        cycle_path = rec_stack[cycle_start:]
                        cycles.append(Cycle(
                            cycle_type=CycleType.INHERITANCE,
                            path=cycle_path
                        ))
                    elif neighbor not in visited:
                        dfs(neighbor)

                rec_stack.pop()

            for node in inheritance_graph:
                if node not in visited:
                    dfs(node)

        except Exception as e:
            logger.error(f"Error detecting inheritance cycles: {e}")

        return cycles

    def _build_import_graph(self, file_path: Optional[str]) -> Dict[str, List[str]]:
        """
        Build file-level import graph from dependencies.

        Args:
            file_path: Optional file path to limit scope

        Returns:
            Dict mapping file to list of files it imports
        """
        graph = defaultdict(list)

        try:
            # Query dependencies
            query = """
                SELECT DISTINCT source_file, target_file
                FROM dependencies
                WHERE target_file IS NOT NULL
            """
            params = ()

            if file_path:
                query += " AND (source_file = ? OR target_file = ?)"
                params = (file_path, file_path)

            cursor = self.conn.execute(query, params)

            for source, target in cursor.fetchall():
                if source and target and source != target:
                    graph[source].append(target)

        except Exception as e:
            logger.error(f"Error building import graph: {e}")

        return dict(graph)

    def _build_call_graph(self, file_path: Optional[str]) -> Dict[str, List[str]]:
        """
        Build function-level call graph from dependencies.

        Args:
            file_path: Optional file path to limit scope

        Returns:
            Dict mapping function to list of functions it calls
        """
        graph = defaultdict(list)

        try:
            # Query function calls from dependencies
            query = """
                SELECT DISTINCT source_symbol, target_symbol
                FROM dependencies
                WHERE reference_type IN ('method_call', 'function_call')
            """
            params = ()

            if file_path:
                query += " AND source_file = ?"
                params = (file_path,)

            cursor = self.conn.execute(query, params)

            for source, target in cursor.fetchall():
                if source and target and source != target:
                    # Use fully qualified names
                    graph[source].append(target)

        except Exception as e:
            logger.error(f"Error building call graph: {e}")

        return dict(graph)

    def _build_inheritance_graph(self, file_path: Optional[str]) -> Dict[str, List[str]]:
        """
        Build class-level inheritance graph.

        Args:
            file_path: Optional file path to limit scope

        Returns:
            Dict mapping class to list of parent classes
        """
        graph = defaultdict(list)

        try:
            # Query inheritance relationships
            query = """
                SELECT DISTINCT source_symbol, target_symbol
                FROM dependencies
                WHERE reference_type = 'inherits_from'
            """
            params = ()

            if file_path:
                query += " AND source_file = ?"
                params = (file_path,)

            cursor = self.conn.execute(query, params)

            for child, parent in cursor.fetchall():
                if child and parent and child != parent:
                    graph[child].append(parent)

        except Exception as e:
            logger.error(f"Error building inheritance graph: {e}")

        return dict(graph)

    def get_symbols_in_cycles(
        self,
        file_path: str,
        cycles: List[Cycle]
    ) -> Set[str]:
        """
        Get set of symbol names that are involved in cycles.

        Args:
            file_path: File path to check
            cycles: List of detected cycles

        Returns:
            Set of symbol names involved in cycles
        """
        symbols_in_cycles = set()

        for cycle in cycles:
            # For call and inheritance cycles, check if symbols are in this file
            if cycle.cycle_type in [CycleType.CALL, CycleType.INHERITANCE]:
                # Check if any symbol in the cycle path belongs to this file
                try:
                    for symbol in cycle.path:
                        cursor = self.conn.execute(
                            "SELECT COUNT(*) FROM symbols WHERE name = ? AND file_path = ?",
                            (symbol, file_path)
                        )
                        count = cursor.fetchone()[0]
                        if count > 0:
                            symbols_in_cycles.add(symbol)
                except Exception as e:
                    logger.debug(f"Error checking symbol {symbol}: {e}")

            # For import cycles, add all symbols from files in the cycle
            elif cycle.cycle_type == CycleType.IMPORT and file_path in cycle.files:
                try:
                    cursor = self.conn.execute(
                        "SELECT name FROM symbols WHERE file_path = ?",
                        (file_path,)
                    )
                    for (symbol,) in cursor.fetchall():
                        symbols_in_cycles.add(symbol)
                except Exception as e:
                    logger.debug(f"Error fetching symbols: {e}")

        return symbols_in_cycles
