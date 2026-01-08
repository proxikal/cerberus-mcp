"""
Recursive call graph operations for dependency analysis.

Part of Phase 1: Advanced Dependency Intelligence.
"""

from typing import Dict, List, Set, Optional
from pathlib import Path

from cerberus.logging_config import logger
from cerberus.tracing import trace
from cerberus.schemas import CallGraphNode, CallGraphResult, CallReference, ScanResult, CodeSymbol


def _build_call_map(scan_result: ScanResult) -> Dict[str, List[CallReference]]:
    """
    Build a map from symbol names to all call references that call them.

    Args:
        scan_result: The scan result containing all calls.

    Returns:
        Dictionary mapping symbol name -> list of CallReferences that call it.
    """
    call_map: Dict[str, List[CallReference]] = {}
    for call in scan_result.calls:
        if call.callee not in call_map:
            call_map[call.callee] = []
        call_map[call.callee].append(call)
    return call_map


def _build_symbol_map(scan_result: ScanResult) -> Dict[str, List[CodeSymbol]]:
    """
    Build a map from symbol names to their definitions.

    Args:
        scan_result: The scan result containing all symbols.

    Returns:
        Dictionary mapping symbol name -> list of CodeSymbols (can be multiple with same name).
    """
    symbol_map: Dict[str, List[CodeSymbol]] = {}
    for symbol in scan_result.symbols:
        if symbol.name not in symbol_map:
            symbol_map[symbol.name] = []
        symbol_map[symbol.name].append(symbol)
    return symbol_map


@trace
def build_recursive_call_graph(
    target_symbol: str,
    scan_result: ScanResult,
    max_depth: int = 3,
) -> CallGraphResult:
    """
    Build a recursive call graph starting from a target symbol.

    The graph shows all callers of the target symbol, their callers, and so on
    up to max_depth levels.

    Args:
        target_symbol: The symbol name to start from.
        scan_result: The scan result containing all calls and symbols.
        max_depth: Maximum depth to traverse (0 = target only, 1 = direct callers, etc.).

    Returns:
        CallGraphResult containing the complete call graph.
    """
    call_map = _build_call_map(scan_result)
    symbol_map = _build_symbol_map(scan_result)

    # Check if target symbol exists
    if target_symbol not in symbol_map:
        logger.warning(f"Target symbol '{target_symbol}' not found in index")
        return CallGraphResult(
            target_symbol=target_symbol,
            max_depth=max_depth,
            root_node=None,
            total_nodes=0,
        )

    # Build the graph recursively
    visited: Set[str] = set()  # Prevent infinite loops
    total_nodes = 0

    def _build_node(symbol_name: str, depth: int) -> Optional[CallGraphNode]:
        nonlocal total_nodes

        # Base cases
        if depth > max_depth:
            return None

        # Prevent cycles
        node_key = f"{symbol_name}:{depth}"
        if node_key in visited:
            return None
        visited.add(node_key)

        # Get symbol definitions
        symbols = symbol_map.get(symbol_name, [])
        if not symbols:
            return None

        # Use the first symbol definition (could be multiple)
        primary_symbol = symbols[0]

        # Get callers
        caller_refs = call_map.get(symbol_name, [])
        caller_nodes = []

        for call_ref in caller_refs:
            # Find the symbol that contains this call (the calling function)
            # We need to find which function in caller_file contains line call_ref.line
            caller_symbols = [
                sym for sym in scan_result.symbols
                if sym.file_path == call_ref.caller_file
                and sym.start_line <= call_ref.line <= sym.end_line
            ]

            for caller_symbol in caller_symbols:
                caller_node = _build_node(caller_symbol.name, depth + 1)
                if caller_node:
                    caller_nodes.append(caller_node)

        total_nodes += 1

        return CallGraphNode(
            symbol_name=symbol_name,
            file_path=primary_symbol.file_path,
            line=primary_symbol.start_line,
            depth=depth,
            callers=caller_nodes,
        )

    root_node = _build_node(target_symbol, 0)

    logger.info(f"Built call graph for '{target_symbol}' with {total_nodes} nodes up to depth {max_depth}")

    return CallGraphResult(
        target_symbol=target_symbol,
        max_depth=max_depth,
        root_node=root_node,
        total_nodes=total_nodes,
    )


def get_recursive_callers(
    symbol_name: str,
    scan_result: ScanResult,
    depth: int = 3,
) -> List[CallGraphNode]:
    """
    Get all callers of a symbol recursively up to a specified depth.

    This is a convenience function that builds a call graph and returns
    all caller nodes in a flat list.

    Args:
        symbol_name: The symbol to find callers for.
        scan_result: The scan result containing all calls and symbols.
        depth: Maximum depth to traverse.

    Returns:
        List of CallGraphNode objects representing all callers.
    """
    graph_result = build_recursive_call_graph(symbol_name, scan_result, max_depth=depth)

    if not graph_result.root_node:
        return []

    # Flatten the tree into a list
    all_nodes: List[CallGraphNode] = []

    def _collect_nodes(node: CallGraphNode):
        all_nodes.append(node)
        for caller in node.callers:
            _collect_nodes(caller)

    _collect_nodes(graph_result.root_node)

    return all_nodes


def format_call_graph(graph_result: CallGraphResult, indent: str = "  ") -> str:
    """
    Format a call graph as a human-readable tree string.

    Args:
        graph_result: The call graph to format.
        indent: Indentation string for each level.

    Returns:
        Formatted string representation of the call graph.
    """
    if not graph_result.root_node:
        return f"No callers found for '{graph_result.target_symbol}'"

    lines: List[str] = []
    lines.append(f"Call Graph for '{graph_result.target_symbol}' (max depth: {graph_result.max_depth})")
    lines.append(f"Total nodes: {graph_result.total_nodes}")
    lines.append("")

    def _format_node(node: CallGraphNode, level: int):
        prefix = indent * level
        arrow = "← " if level > 0 else "● "
        lines.append(f"{prefix}{arrow}{node.symbol_name} ({node.file_path}:{node.line})")
        for caller in node.callers:
            _format_node(caller, level + 1)

    _format_node(graph_result.root_node, 0)

    return "\n".join(lines)
