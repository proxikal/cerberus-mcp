"""
Change analysis for mapping changed lines to affected symbols.
"""

from pathlib import Path
from typing import List, Set
from loguru import logger

from ..schemas import ModifiedFile, LineRange, CodeSymbol, ScanResult


def identify_affected_symbols(
    modified_file: ModifiedFile,
    scan_result: ScanResult,
) -> List[str]:
    """
    Identify which symbols in a file are affected by changed line ranges.

    Args:
        modified_file: File with changed line ranges
        scan_result: Previous scan result containing symbols

    Returns:
        List of affected symbol names
    """
    affected_symbols: Set[str] = set()

    # Normalize the modified file path for comparison
    # Project root is stored in scan_result, git diff returns relative paths
    if scan_result.project_root:
        modified_file_abs = str((Path(scan_result.project_root) / modified_file.path).resolve())
    else:
        # Fallback: just use the path as-is
        modified_file_abs = modified_file.path


    # Find symbols whose line ranges overlap with changed lines
    for symbol in scan_result.symbols:
        # Only check symbols from this file
        # Normalize both paths for comparison
        symbol_path_abs = str(Path(symbol.file_path).resolve())
        if symbol_path_abs != modified_file_abs:
            continue


        # Check if symbol's line range overlaps with any changed range
        for changed_range in modified_file.changed_lines:
            if _ranges_overlap(symbol.start_line, symbol.end_line, changed_range):
                affected_symbols.add(symbol.name)
                logger.debug(
                    f"Symbol '{symbol.name}' at lines {symbol.start_line}-{symbol.end_line} "
                    f"affected by change at lines {changed_range.start}-{changed_range.end}"
                )

    return list(affected_symbols)


def _ranges_overlap(symbol_start: int, symbol_end: int, changed_range: LineRange) -> bool:
    """
    Check if a symbol's line range overlaps with a changed line range.

    Args:
        symbol_start: Start line of symbol
        symbol_end: End line of symbol
        changed_range: Changed line range

    Returns:
        True if ranges overlap
    """
    # Check if ranges overlap
    # Overlap occurs if: symbol_start <= changed_end AND changed_start <= symbol_end
    return symbol_start <= changed_range.end and changed_range.start <= symbol_end


def find_callers_to_reparse(
    affected_symbols: List[str],
    scan_result: ScanResult,
    max_callers: int = 50,
) -> Set[str]:
    """
    Find symbols that call affected symbols and may need re-parsing.

    Only re-parses callers if the signature of affected symbols changed.

    Args:
        affected_symbols: Symbols that were modified
        scan_result: Previous scan result with call graph
        max_callers: Maximum number of callers to reparse

    Returns:
        Set of caller symbol names to re-parse
    """
    callers_to_reparse: Set[str] = set()

    # Build a map of file -> symbols for faster lookup
    file_to_symbols: dict[str, Set[str]] = {}
    for symbol in scan_result.symbols:
        if symbol.file_path not in file_to_symbols:
            file_to_symbols[symbol.file_path] = set()
        file_to_symbols[symbol.file_path].add(symbol.name)

    # For each affected symbol, find its callers from CallReference list
    for symbol_name in affected_symbols:
        # Find calls to this symbol
        for call_ref in scan_result.calls:
            if call_ref.callee == symbol_name:
                # Find the caller symbol(s) in the caller file
                caller_file_symbols = file_to_symbols.get(call_ref.caller_file, set())
                # Add all symbols from the caller file
                # (we don't know which specific symbol made the call)
                callers_to_reparse.update(caller_file_symbols)

                # Respect max_callers limit
                if len(callers_to_reparse) >= max_callers:
                    logger.warning(
                        f"Reached max callers limit ({max_callers}), "
                        f"some callers may not be re-parsed"
                    )
                    return callers_to_reparse

    if callers_to_reparse:
        logger.debug(
            f"Found {len(callers_to_reparse)} callers to re-parse: "
            f"{list(callers_to_reparse)[:5]}..."
        )

    return callers_to_reparse


def should_fallback_to_full_reparse(
    total_files: int,
    changed_files: int,
    threshold: float = 0.3,
) -> bool:
    """
    Determine if we should fall back to full re-parse instead of incremental.

    Args:
        total_files: Total number of files in project
        changed_files: Number of files that changed
        threshold: Threshold ratio (default 0.3 = 30%)

    Returns:
        True if should do full reparse
    """
    if total_files == 0:
        return True

    change_ratio = changed_files / total_files

    if change_ratio > threshold:
        logger.info(
            f"Change ratio {change_ratio:.1%} exceeds threshold {threshold:.1%}, "
            f"recommending full re-parse"
        )
        return True

    return False


def calculate_affected_files(
    added_files: List[str],
    modified_files: List[ModifiedFile],
    deleted_files: List[str],
) -> Set[str]:
    """
    Calculate the total set of affected file paths.

    Args:
        added_files: List of added file paths
        modified_files: List of modified files with changes
        deleted_files: List of deleted file paths

    Returns:
        Set of all affected file paths
    """
    affected = set(added_files)
    affected.update(m.path for m in modified_files)
    affected.update(deleted_files)
    return affected
