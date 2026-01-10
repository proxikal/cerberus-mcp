"""
Batch command handlers for in-process execution.

Extracted from utils.py as part of Phase 7 Track B CLI de-monolithization.
Each handler processes a specific command type from batch requests.
"""

from pathlib import Path
from typing import Dict, Any
from cerberus.index import find_symbol, compute_stats, ScanResult
from cerberus.retrieval import hybrid_search
from cerberus.storage.sqlite_store import SQLiteIndexStore
from cerberus.mutation import MutationFacade


def handle_get_symbol(args: dict, scan_result: ScanResult, index_path: Path) -> dict:
    """Handle get-symbol command."""
    name = args.get("name")
    if not name:
        return {"error": "Missing required argument: name"}

    matches = find_symbol(name, scan_result)
    return {
        "found": len(matches) > 0,
        "count": len(matches),
        "matches": [
            {
                "name": m.name,
                "type": m.type,
                "file": m.file_path,
                "line_start": m.start_line,
                "line_end": m.end_line,
                "signature": m.signature,
                "parent_class": m.parent_class,
            }
            for m in matches
        ]
    }


def handle_search(args: dict, scan_result: ScanResult, index_path: Path) -> dict:
    """Handle search command."""
    query = args.get("query")
    if not query:
        return {"error": "Missing required argument: query"}

    mode = args.get("mode", "auto")
    top_k = args.get("top-k", args.get("limit", 10))
    padding = args.get("padding", 3)

    results = hybrid_search(
        query=query,
        index_path=index_path,
        mode=mode,
        top_k=top_k,
        padding=padding,
    )

    return {
        "query": query,
        "mode": mode,
        "count": len(results),
        "results": [
            {
                "rank": r.rank,
                "score": r.hybrid_score,
                "match_type": r.match_type,
                "symbol": {
                    "name": r.symbol.name,
                    "type": r.symbol.type,
                    "file": r.symbol.file_path,
                    "line_start": r.symbol.start_line,
                }
            }
            for r in results
        ]
    }


def handle_stats(args: dict, scan_result: ScanResult, index_path: Path) -> dict:
    """Handle stats command."""
    stats = compute_stats(scan_result)
    return {
        "total_files": stats.total_files,
        "total_symbols": stats.total_symbols,
        "symbol_types": stats.symbol_types,
        "average_symbols_per_file": stats.average_symbols_per_file,
    }


def handle_deps(args: dict, scan_result: ScanResult, index_path: Path) -> dict:
    """Handle deps command."""
    from cerberus.resolution import get_symbol_dependencies
    symbol = args.get("symbol")
    if not symbol:
        return {"error": "Missing required argument: symbol"}

    deps = get_symbol_dependencies(symbol, scan_result)
    return {
        "symbol": symbol,
        "dependencies": deps
    }


def handle_calls(args: dict, scan_result: ScanResult, index_path: Path) -> dict:
    """Handle calls command - find what a symbol calls."""
    symbol = args.get("symbol")
    if not symbol:
        return {"error": "Missing required argument: symbol"}

    # Filter calls where this symbol is the caller
    calls = [c for c in scan_result.calls if symbol in c.caller_file]
    return {
        "symbol": symbol,
        "calls": [
            {"callee": c.callee, "file": c.caller_file, "line": c.line}
            for c in calls[:50]  # Limit results
        ]
    }


def handle_references(args: dict, scan_result: ScanResult, index_path: Path) -> dict:
    """Handle references command - find where a symbol is used."""
    symbol = args.get("symbol")
    if not symbol:
        return {"error": "Missing required argument: symbol"}

    # Search for references to this symbol
    refs = [r for r in getattr(scan_result, 'symbol_references', [])
            if r.name == symbol]
    return {
        "symbol": symbol,
        "reference_count": len(refs),
        "references": [
            {"file": r.file_path, "line": r.line}
            for r in refs[:50]  # Limit results
        ]
    }


def handle_edit(args: dict, scan_result: ScanResult, index_path: Path) -> dict:
    """Handle edit command - Phase 11 symbolic editing."""
    file_path = args.get("file")
    symbol = args.get("symbol")
    code = args.get("code")

    if not file_path:
        return {"error": "Missing required argument: file"}
    if not symbol:
        return {"error": "Missing required argument: symbol"}
    if not code:
        return {"error": "Missing required argument: code"}

    try:
        # Load store
        store = SQLiteIndexStore(str(index_path))

        # Create facade
        facade = MutationFacade(store)

        # Perform edit
        result = facade.edit_symbol(
            file_path=file_path,
            symbol_name=symbol,
            new_code=code,
            symbol_type=args.get("type"),
            parent_class=args.get("parent"),
            dry_run=args.get("dry_run", False),
            auto_format=not args.get("no_format", False),
            auto_imports=not args.get("no_imports", False)
        )

        return result.model_dump()

    except Exception as e:
        return {"error": f"Edit failed: {e}"}


def handle_delete(args: dict, scan_result: ScanResult, index_path: Path) -> dict:
    """Handle delete command - Phase 11 symbolic deletion."""
    file_path = args.get("file")
    symbol = args.get("symbol")

    if not file_path:
        return {"error": "Missing required argument: file"}
    if not symbol:
        return {"error": "Missing required argument: symbol"}

    try:
        # Load store
        store = SQLiteIndexStore(str(index_path))

        # Create facade
        facade = MutationFacade(store)

        # Perform delete
        result = facade.delete_symbol(
            file_path=file_path,
            symbol_name=symbol,
            symbol_type=args.get("type"),
            parent_class=args.get("parent"),
            dry_run=args.get("dry_run", False),
            keep_decorators=args.get("keep_decorators", False)
        )

        return result.model_dump()

    except Exception as e:
        return {"error": f"Delete failed: {e}"}


# Command handler registry
BATCH_HANDLERS: Dict[str, Any] = {
    "get-symbol": handle_get_symbol,
    "search": handle_search,
    "stats": handle_stats,
    "deps": handle_deps,
    "calls": handle_calls,
    "references": handle_references,
    "edit": handle_edit,  # Phase 11
    "delete": handle_delete,  # Phase 11
}
