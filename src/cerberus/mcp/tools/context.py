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
        """Assemble complete context for symbol with bases, deps, and imports."""
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
