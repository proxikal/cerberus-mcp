"""Context assembly tool - ONE call replaces multi-tool workflows."""
from typing import Optional

from cerberus.resolution.context_assembler import ContextAssembler

from ..index_manager import get_index_manager


def register(mcp):
    @mcp.tool()
    def context(
        symbol_name: str,
        file_path: Optional[str] = None,
        include_bases: bool = True,
        include_deps: bool = True,
    ) -> dict:
        """
        Assemble complete context for understanding/modifying a symbol.

        Returns target code + skeletonized base classes + callers/callees + imports.
        Replaces: search → get_symbol → deps → skeletonize workflow.

        Token savings: 70-90% vs reading full inheritance chain.

        Args:
            symbol_name: Name of the symbol (function, class, method)
            file_path: Optional file path to disambiguate if multiple symbols share the name
            include_bases: Include skeletonized base classes for classes (default: True)
            include_deps: Include callers/callees information (default: True)

        Returns:
            dict with:
            - status: "ok" or "error"
            - target_symbol: The symbol name
            - target_file: Path where symbol was found
            - target_code: Full implementation of the symbol
            - base_classes: List of {name, file, depth, code, skeletonized} for inheritance chain
            - related_symbols: List of imports and type dependencies
            - callers: List of {name, file, line} for functions that call this symbol (if include_deps)
            - callees: List of {name, file, line} for functions this symbol calls (if include_deps)
            - total_lines: Total lines of context returned
            - compression_ratio: Ratio compared to reading full files
        """
        manager = get_index_manager()

        try:
            index = manager.get_index()
        except FileNotFoundError as e:
            return {"status": "error", "error_type": "no_index", "message": str(e)}

        # Check for SQLite store (required for context assembly)
        if not hasattr(index, "_store"):
            return {
                "status": "error",
                "error_type": "requires_sqlite",
                "message": "Context assembly requires SQLite index",
            }

        store = index._store

        # Assemble context using ContextAssembler
        assembler = ContextAssembler(store)
        assembled = assembler.assemble_context(
            symbol_name=symbol_name,
            file_path=file_path,
            include_bases=include_bases,
        )

        if assembled is None:
            return {
                "status": "error",
                "error_type": "symbol_not_found",
                "message": f"Symbol '{symbol_name}' not found",
            }

        # Build result
        result = {
            "status": "ok",
            "target_symbol": assembled.target_symbol,
            "target_file": assembled.target_file,
            "target_code": assembled.target_code,
            "base_classes": assembled.base_classes,
            "related_symbols": assembled.related_symbols,
            "total_lines": assembled.total_lines,
            "compression_ratio": round(assembled.compression_ratio, 3),
            "includes_inheritance": assembled.includes_inheritance,
        }

        # Add dependency info if requested
        if include_deps:
            callers, callees = _get_deps(store, symbol_name, assembled.target_file)
            result["callers"] = callers
            result["callees"] = callees

        return result


def _get_deps(store, symbol_name: str, file_path: str) -> tuple[list, list]:
    """Get callers and callees for a symbol using CallGraphBuilder."""
    try:
        from cerberus.resolution.call_graph_builder import CallGraphBuilder

        builder = CallGraphBuilder(store)

        location = builder._get_symbol_location(symbol_name, file_path)
        if not location:
            return [], []

        file_resolved, _, _ = location
        callers = builder._get_callers(symbol_name, file_resolved)
        callees = builder._get_callees(symbol_name, file_resolved)

        return (
            [{"name": name, "file": fpath, "line": line} for name, fpath, line in callers],
            [{"name": name, "file": fpath, "line": line} for name, fpath, line in callees],
        )
    except Exception:
        # Graceful degradation if call graph not available
        return [], []
