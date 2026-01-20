"""
Phase 6: Call Graph Builder.

Generates execution path graphs by following function and method calls
through the codebase.
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import deque

from cerberus.logging_config import logger
from cerberus.storage.sqlite_store import SQLiteIndexStore
from .config import CALL_GRAPH_CONFIG

# Built-in functions and common stdlib to filter out
BUILTIN_FILTER = {
    # Python builtins
    'print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
    'range', 'enumerate', 'zip', 'map', 'filter', 'sum', 'min', 'max', 'abs',
    'isinstance', 'issubclass', 'type', 'getattr', 'setattr', 'hasattr', 'delattr',
    'open', 'input', 'sorted', 'reversed', 'all', 'any', 'next', 'iter',
    # Common stdlib methods
    'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'index', 'count',
    'keys', 'values', 'items', 'get', 'update', 'join', 'split', 'strip',
    'upper', 'lower', 'replace', 'format', 'startswith', 'endswith',
    'read', 'write', 'close', 'seek', 'tell',
    # Date/time
    'now', 'strftime', 'strptime', 'time', 'sleep',
    # JSON/serialization
    'json', 'loads', 'dumps',
    # JavaScript/TypeScript builtins
    'console', 'log', 'error', 'warn', 'info', 'debug',
    'parseInt', 'parseFloat', 'isNaN', 'isFinite',
    'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
    'push', 'shift', 'unshift', 'slice', 'splice', 'forEach', 'includes',
    # Go builtins
    'make', 'new', 'len', 'cap', 'append', 'copy', 'delete',
    'panic', 'recover', 'close',
    'Println', 'Printf', 'Sprintf', 'Fprintf',
}


@dataclass
class CallNode:
    """Represents a node in the call graph."""
    symbol_name: str
    file_path: str
    line: int
    depth: int
    call_type: str  # 'function', 'method', 'constructor'


@dataclass
class CallGraph:
    """Represents a complete call graph."""
    root_symbol: str
    root_file: str
    nodes: List[CallNode]
    edges: List[Tuple[str, str]]  # (caller, callee) pairs
    max_depth_reached: int
    truncated: bool  # True if max depth was hit


class CallGraphBuilder:
    """
    Builds call graphs by traversing function and method calls.

    Supports both forward graphs (what does this function call?)
    and reverse graphs (what calls this function?).
    """

    def __init__(self, store: SQLiteIndexStore):
        """
        Initialize the call graph builder.

        Args:
            store: SQLite index store
        """
        self.store = store
        self.config = CALL_GRAPH_CONFIG

    def build_forward_graph(
        self,
        symbol_name: str,
        file_path: Optional[str] = None,
        max_depth: Optional[int] = None
    ) -> CallGraph:
        """
        Build a forward call graph (what does this symbol call?).

        Args:
            symbol_name: Name of the function/method to start from
            file_path: Optional file path to disambiguate
            max_depth: Maximum depth to traverse (default from config)

        Returns:
            CallGraph object
        """
        max_depth = max_depth or self.config["max_depth"]
        max_nodes = self.config.get("max_nodes", 100)
        max_edges = self.config.get("max_edges", 200)
        logger.debug(f"Building forward call graph for {symbol_name} (max depth: {max_depth}, max nodes: {max_nodes})")

        nodes: List[CallNode] = []
        edges: List[Tuple[str, str]] = []
        visited: Set[str] = set()
        truncated = False

        # BFS traversal
        queue = deque([(symbol_name, file_path, 0)])
        max_depth_reached = 0

        while queue:
            current_symbol, current_file, depth = queue.popleft()

            if depth > max_depth:
                truncated = True
                continue

            # Check node limit
            if len(nodes) >= max_nodes:
                truncated = True
                logger.debug(f"Call graph truncated at {max_nodes} nodes")
                break

            max_depth_reached = max(max_depth_reached, depth)

            # Create unique key for visited tracking
            visit_key = f"{current_symbol}:{current_file}:{depth}"
            if visit_key in visited:
                continue
            visited.add(visit_key)

            # Get symbol location
            symbol_info = self._get_symbol_location(current_symbol, current_file)
            if symbol_info:
                file, line, sym_type = symbol_info
                nodes.append(CallNode(
                    symbol_name=current_symbol,
                    file_path=file,
                    line=line,
                    depth=depth,
                    call_type=sym_type
                ))

                # Find what this symbol calls
                callees = self._get_callees(current_symbol, file)

                for callee_name, callee_file, callee_line in callees:
                    # Check edge limit
                    if len(edges) >= max_edges:
                        truncated = True
                        logger.debug(f"Call graph truncated at {max_edges} edges")
                        break

                    edges.append((current_symbol, callee_name))

                    # Add to queue for traversal
                    if depth + 1 <= max_depth:
                        queue.append((callee_name, callee_file, depth + 1))

                # If edge limit hit, stop processing
                if truncated:
                    break

        logger.debug(f"Forward graph: {len(nodes)} nodes, {len(edges)} edges, max depth: {max_depth_reached}")

        return CallGraph(
            root_symbol=symbol_name,
            root_file=file_path or "",
            nodes=nodes,
            edges=edges,
            max_depth_reached=max_depth_reached,
            truncated=truncated
        )

    def build_reverse_graph(
        self,
        symbol_name: str,
        file_path: Optional[str] = None,
        max_depth: Optional[int] = None
    ) -> CallGraph:
        """
        Build a reverse call graph (what calls this symbol?).

        Args:
            symbol_name: Name of the function/method
            file_path: Optional file path to disambiguate
            max_depth: Maximum depth to traverse (default from config)

        Returns:
            CallGraph object
        """
        max_depth = max_depth or self.config["max_depth"]
        max_nodes = self.config.get("max_nodes", 100)
        max_edges = self.config.get("max_edges", 200)
        logger.debug(f"Building reverse call graph for {symbol_name} (max depth: {max_depth}, max nodes: {max_nodes})")

        nodes: List[CallNode] = []
        edges: List[Tuple[str, str]] = []
        visited: Set[str] = set()
        truncated = False

        # BFS traversal (reverse direction)
        queue = deque([(symbol_name, file_path, 0)])
        max_depth_reached = 0

        while queue:
            current_symbol, current_file, depth = queue.popleft()

            if depth > max_depth:
                truncated = True
                continue

            # Check node limit
            if len(nodes) >= max_nodes:
                truncated = True
                logger.debug(f"Call graph truncated at {max_nodes} nodes")
                break

            max_depth_reached = max(max_depth_reached, depth)

            visit_key = f"{current_symbol}:{current_file}:{depth}"
            if visit_key in visited:
                continue
            visited.add(visit_key)

            # Get symbol location
            symbol_info = self._get_symbol_location(current_symbol, current_file)
            if symbol_info:
                file, line, sym_type = symbol_info
                nodes.append(CallNode(
                    symbol_name=current_symbol,
                    file_path=file,
                    line=line,
                    depth=depth,
                    call_type=sym_type
                ))

                # Find what calls this symbol
                callers = self._get_callers(current_symbol, file)

                for caller_name, caller_file, caller_line in callers:
                    # Check edge limit
                    if len(edges) >= max_edges:
                        truncated = True
                        logger.debug(f"Call graph truncated at {max_edges} edges")
                        break

                    edges.append((caller_name, current_symbol))

                    # Add to queue for traversal
                    if depth + 1 <= max_depth:
                        queue.append((caller_name, caller_file, depth + 1))

                # If edge limit hit, stop processing
                if truncated:
                    break

        logger.debug(f"Reverse graph: {len(nodes)} nodes, {len(edges)} edges, max depth: {max_depth_reached}")

        return CallGraph(
            root_symbol=symbol_name,
            root_file=file_path or "",
            nodes=nodes,
            edges=edges,
            max_depth_reached=max_depth_reached,
            truncated=truncated
        )

    def _get_symbol_location(
        self,
        symbol_name: str,
        file_path: Optional[str]
    ) -> Optional[Tuple[str, int, str]]:
        """
        Get the location of a symbol.

        Returns:
            Tuple of (file_path, line, type) or None
        """
        conn = self.store._get_connection()
        try:
            if file_path:
                cursor = conn.execute("""
                    SELECT file_path, start_line, type
                    FROM symbols
                    WHERE name = ? AND file_path = ?
                    LIMIT 1
                """, (symbol_name, file_path))
            else:
                cursor = conn.execute("""
                    SELECT file_path, start_line, type
                    FROM symbols
                    WHERE name = ?
                    LIMIT 1
                """, (symbol_name,))

            result = cursor.fetchone()
            if result:
                return (result[0], result[1], result[2])
            return None
        finally:
            conn.close()

    def _get_callees(
        self,
        symbol_name: str,
        file_path: str
    ) -> List[Tuple[str, str, int]]:
        """
        Get all symbols called by the given symbol.

        Returns:
            List of (callee_name, callee_file, line) tuples
        """
        conn = self.store._get_connection()
        try:
            # First, get the symbol's line range
            cursor = conn.execute("""
                SELECT start_line, end_line
                FROM symbols
                WHERE name = ? AND file_path = ?
                LIMIT 1
            """, (symbol_name, file_path))

            result = cursor.fetchone()
            if not result:
                return []

            start_line, end_line = result

            # Get regular function calls within this symbol's line range
            cursor = conn.execute("""
                SELECT DISTINCT callee, line
                FROM calls
                WHERE caller_file = ?
                AND line >= ?
                AND line <= ?
            """, (file_path, start_line, end_line))

            calls = cursor.fetchall()

            # Also check method calls within the line range
            cursor = conn.execute("""
                SELECT DISTINCT method, line
                FROM method_calls
                WHERE caller_file = ?
                AND line >= ?
                AND line <= ?
            """, (file_path, start_line, end_line))

            method_calls = cursor.fetchall()

            # Combine and filter built-ins
            unique_calls = {}
            for callee, line in calls + method_calls:
                # Filter out built-ins and stdlib noise
                if callee in BUILTIN_FILTER:
                    continue

                if callee not in unique_calls:
                    # Try to resolve callee to its file
                    callee_info = self._get_symbol_location(callee, None)
                    callee_file = callee_info[0] if callee_info else file_path
                    unique_calls[callee] = (callee, callee_file, line)

            return list(unique_calls.values())
        finally:
            conn.close()

    def _get_callers(
        self,
        symbol_name: str,
        file_path: str
    ) -> List[Tuple[str, str, int]]:
        """
        Get all symbols that call the given symbol.

        Returns:
            List of (caller_name, caller_file, line) tuples
        """
        conn = self.store._get_connection()
        try:
            # Find calls to this symbol
            cursor = conn.execute("""
                SELECT DISTINCT caller_file, line
                FROM calls
                WHERE callee = ?
            """, (symbol_name,))

            call_locations = cursor.fetchall()

            # Also check method calls
            cursor = conn.execute("""
                SELECT DISTINCT caller_file, line
                FROM method_calls
                WHERE method = ?
            """, (symbol_name,))

            method_call_locations = cursor.fetchall()

            all_locations = call_locations + method_call_locations

            # For each location, find the enclosing function/method
            unique_callers = {}
            for caller_file, line in all_locations:
                # Find symbol that contains this line
                cursor = conn.execute("""
                    SELECT name, file_path, start_line
                    FROM symbols
                    WHERE file_path = ?
                    AND start_line <= ?
                    AND end_line >= ?
                    AND type IN ('function', 'method')
                    ORDER BY start_line DESC
                    LIMIT 1
                """, (caller_file, line, line))

                result = cursor.fetchone()
                if result:
                    caller_name, caller_file_path, caller_line = result
                    # Deduplicate by caller name and file
                    key = f"{caller_name}:{caller_file_path}"
                    if key not in unique_callers:
                        unique_callers[key] = (caller_name, caller_file_path, caller_line)

            return list(unique_callers.values())
        finally:
            conn.close()
