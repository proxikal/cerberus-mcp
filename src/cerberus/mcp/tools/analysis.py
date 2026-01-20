"""Code analysis tools - dependencies, call graphs."""
from typing import Optional

from cerberus.resolution.call_graph_builder import CallGraphBuilder, CallGraph

from ..index_manager import get_index_manager
from cerberus.mcp.tools.token_utils import (
    add_warning,
    estimate_json_tokens,
)


def register(mcp):
    @mcp.tool()
    def deps(symbol_name: str, file_path: Optional[str] = None) -> dict:
        """
        Get callers and callees for a symbol.

        Analyzes the call graph to find what functions call this symbol
        (callers) and what functions this symbol calls (callees).

        Args:
            symbol_name: Name of the function/method to analyze
            file_path: Optional file path to disambiguate if multiple symbols share the name

        Returns:
            dict with:
            - status: "ok" or "error"
            - symbol: The symbol name
            - file: Path where symbol was found
            - callers: List of {name, file, line} for functions that call this symbol
            - callees: List of {name, file, line} for functions this symbol calls
            - imports: List of imports used by this symbol
        """
        manager = get_index_manager()
        index = manager.get_index()
        if not hasattr(index, "_store"):
            return {"status": "error", "message": "Call graph requires SQLite index"}
        store = index._store
        builder = CallGraphBuilder(store)

        location = builder._get_symbol_location(symbol_name, file_path)
        if not location:
            return {
                "status": "error",
                "error_type": "symbol_not_found",
                "message": f"Symbol '{symbol_name}' not found",
            }
        file_resolved, _, _ = location

        callers = builder._get_callers(symbol_name, file_resolved)
        callees = builder._get_callees(symbol_name, file_resolved)

        return {
            "status": "ok",
            "symbol": symbol_name,
            "file": file_resolved,
            "callers": [
                {"name": name, "file": fpath, "line": line} for name, fpath, line in callers
            ],
            "callees": [
                {"name": name, "file": fpath, "line": line} for name, fpath, line in callees
            ],
            "imports": [],
        }

    @mcp.tool()
    def call_graph(symbol_name: str, depth: int = 2, direction: str = "both") -> dict:
        """
        Build recursive call graph from a symbol.

        **TOKEN EFFICIENCY NOTE:**
        - Filters out built-in functions (print, len, str, etc.)
        - Limited to 100 nodes and 200 edges to prevent token explosion
        - Use depth=1 for immediate relationships only (~100-500 tokens)
        - Use depth=2 for broader context (~500-2000 tokens)
        - Depth >2 rarely needed for most analysis tasks

        **AI WORKFLOW:**
        Start with deps() for quick callers/callees. Only use call_graph
        when you need to understand multi-level call chains.

        Args:
            symbol_name: Starting symbol for the graph
            depth: How many levels deep to traverse (default: 2, max recommended: 3)
            direction: "callers" (who calls this), "callees" (what this calls), or "both"

        Returns:
            dict with:
            - status: "ok" or "error"
            - root: The starting symbol name
            - direction: The traversal direction used
            - graphs: List of graph objects, each containing:
              - root_symbol: Starting point
              - root_file: File containing root
              - nodes: List of {name, file, line, depth, type}
              - edges: List of {from, to} relationships
              - max_depth_reached: Whether depth limit was hit
              - truncated: Whether graph was truncated (hit node/edge limits)
        """
        manager = get_index_manager()
        index = manager.get_index()
        if not hasattr(index, "_store"):
            return {"status": "error", "message": "Call graph requires SQLite index"}
        store = index._store
        builder = CallGraphBuilder(store)

        graphs = []
        try:
            if direction in ("callees", "both"):
                graphs.append(builder.build_forward_graph(symbol_name, max_depth=depth))
            if direction in ("callers", "both"):
                graphs.append(builder.build_reverse_graph(symbol_name, max_depth=depth))
        except Exception as exc:
            return {"status": "error", "error_type": "graph_failed", "message": str(exc)}

        serialized = []
        for g in graphs:
            serialized.append(_serialize_graph(g))

        response = {
            "status": "ok",
            "root": symbol_name,
            "direction": direction,
            "graphs": serialized,
        }

        # Add warning for deep graphs
        if depth > 2:
            add_warning(
                response,
                f"Using depth={depth} can cause exponential graph growth. "
                "Consider depth=1 or depth=2 for most use cases."
            )

        # Add token estimation
        tokens = estimate_json_tokens(serialized)
        response["_token_info"] = {
            "estimated_tokens": tokens,
            "depth": depth,
            "direction": direction,
            "graph_count": len(serialized)
        }

        return response


def _serialize_graph(graph: CallGraph) -> dict:
    return {
        "root_symbol": graph.root_symbol,
        "root_file": graph.root_file,
        "max_depth_reached": graph.max_depth_reached,
        "truncated": graph.truncated,
        "nodes": [
            {
                "name": n.symbol_name,
                "file": n.file_path,
                "line": n.line,
                "depth": n.depth,
                "type": n.call_type,
            }
            for n in graph.nodes
        ],
        "edges": [{"from": a, "to": b} for a, b in graph.edges],
    }
