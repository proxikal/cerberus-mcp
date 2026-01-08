"""
Surgical index updates for incremental re-parsing.
"""

import time
from pathlib import Path
from typing import List, Set
from loguru import logger

from ..schemas import (
    FileChange,
    ModifiedFile,
    IncrementalUpdateResult,
    ScanResult,
    CodeSymbol,
)
from ..scanner import scan
from ..index import load_index, save_index
from .config import INCREMENTAL_CONFIG
from .change_analyzer import (
    identify_affected_symbols,
    find_callers_to_reparse,
    calculate_affected_files,
)


def apply_surgical_update(
    index_path: Path,
    file_changes: FileChange,
    project_path: Path,
) -> IncrementalUpdateResult:
    """
    Apply surgical updates to an existing index based on detected changes.

    Args:
        index_path: Path to existing index file
        file_changes: Detected file changes
        project_path: Root path of the project

    Returns:
        IncrementalUpdateResult with update statistics
    """
    start_time = time.time()

    # Load existing index
    logger.info(f"Loading existing index from {index_path}")
    scan_result = load_index(index_path)

    updated_symbols: List[CodeSymbol] = []
    removed_symbols: List[str] = []
    affected_callers: Set[str] = set()
    files_reparsed = 0

    # Handle deleted files
    if file_changes.deleted:
        logger.info(f"Removing {len(file_changes.deleted)} deleted files from index")
        _remove_deleted_files(scan_result, file_changes.deleted, removed_symbols)

    # Handle new files (full parse)
    if file_changes.added:
        logger.info(f"Parsing {len(file_changes.added)} new files")
        new_symbols = _parse_new_files(file_changes.added, project_path)
        updated_symbols.extend(new_symbols)
        scan_result.symbols.extend(new_symbols)
        files_reparsed += len(file_changes.added)

    # Handle modified files (surgical update)
    if file_changes.modified:
        logger.info(f"Surgically updating {len(file_changes.modified)} modified files")

        for modified_file in file_changes.modified:
            # Identify affected symbols in this file
            affected = identify_affected_symbols(modified_file, scan_result)

            # Note: We re-parse the file even if no existing symbols are affected
            # because new symbols may have been added (e.g., new functions/classes)
            if affected:
                logger.info(f"Re-parsing {modified_file.path} (affected: {len(affected)} symbols)")
            else:
                logger.info(f"Re-parsing {modified_file.path} (no existing symbols affected, checking for new symbols)")

            # Re-parse the entire file
            file_path = project_path / modified_file.path
            if not file_path.exists():
                logger.warning(f"File {file_path} does not exist, skipping")
                continue

            # Scan the modified file
            new_scan = scan(
                directory=file_path.parent,
                respect_gitignore=False,
                extensions=None,
                previous_index=None,
                incremental=False,
                max_bytes=None,
            )

            # Remove old symbols from this file
            # Normalize paths for comparison (scanner returns absolute, git diff returns relative)
            modified_file_abs = str((project_path / modified_file.path).resolve())

            scan_result.symbols = [
                s for s in scan_result.symbols
                if Path(s.file_path).resolve() != Path(modified_file_abs)
            ]

            # Add newly scanned symbols (filter to only this file)
            new_file_symbols = [
                s for s in new_scan.symbols
                if Path(s.file_path).resolve() == Path(modified_file_abs)
            ]

            scan_result.symbols.extend(new_file_symbols)
            updated_symbols.extend(new_file_symbols)
            files_reparsed += 1

            # Track affected callers if configured
            if INCREMENTAL_CONFIG["reparse_callers_on_signature_change"]:
                callers = find_callers_to_reparse(
                    affected,
                    scan_result,
                    max_callers=INCREMENTAL_CONFIG["max_affected_callers_to_reparse"],
                )
                affected_callers.update(callers)

    # Re-parse affected callers if needed
    if affected_callers:
        logger.info(f"Re-parsing {len(affected_callers)} affected callers")
        # For now, we don't re-parse callers (would require complex dependency resolution)
        # This is a future enhancement
        pass

    # Save updated index
    logger.info(f"Saving updated index to {index_path}")
    save_index(scan_result, index_path)

    elapsed_time = time.time() - start_time

    result = IncrementalUpdateResult(
        updated_symbols=updated_symbols,
        removed_symbols=removed_symbols,
        affected_callers=list(affected_callers),
        files_reparsed=files_reparsed,
        elapsed_time=elapsed_time,
        strategy="incremental",
    )

    logger.info(
        f"Incremental update complete: "
        f"{len(updated_symbols)} symbols updated, "
        f"{len(removed_symbols)} removed, "
        f"{files_reparsed} files re-parsed in {elapsed_time:.2f}s"
    )

    return result


def _remove_deleted_files(
    scan_result: ScanResult,
    deleted_files: List[str],
    removed_symbols: List[str],
) -> None:
    """
    Remove symbols from deleted files.

    Args:
        scan_result: Scan result to modify (in-place)
        deleted_files: List of deleted file paths
        removed_symbols: List to append removed symbol names to
    """
    initial_count = len(scan_result.symbols)

    # Remove symbols from deleted files
    scan_result.symbols = [
        s for s in scan_result.symbols
        if s.file_path not in deleted_files
    ]

    removed_count = initial_count - len(scan_result.symbols)

    if removed_count > 0:
        logger.info(f"Removed {removed_count} symbols from {len(deleted_files)} deleted files")

    # Track which symbols were removed (for reporting)
    # Note: We don't have the old symbols anymore, so we can't list them by name
    removed_symbols.extend([f"<deleted from {f}>" for f in deleted_files])


def _parse_new_files(added_files: List[str], project_path: Path) -> List[CodeSymbol]:
    """
    Parse new files and extract symbols.

    Args:
        added_files: List of new file paths (relative to project root)
        project_path: Root path of project

    Returns:
        List of newly extracted symbols
    """
    # For now, we'll re-scan the entire project to get new symbols
    # This is inefficient but simple; can be optimized later
    # TODO: Add support for scanning specific files only

    all_symbols = []

    for added_file in added_files:
        file_path = project_path / added_file
        if not file_path.exists():
            logger.warning(f"Added file {file_path} does not exist, skipping")
            continue

        # Scan the directory containing this file
        # This is a workaround since scan() takes a directory, not individual files
        try:
            scan_result = scan(
                directory=file_path.parent,
                respect_gitignore=False,
                extensions=None,
                previous_index=None,
                incremental=False,
                max_bytes=None,
            )

            # Filter symbols to only those from the added file
            # Normalize paths for comparison (scanner returns absolute, git diff returns relative)
            added_file_abs = str((project_path / added_file).resolve())
            file_symbols = [
                s for s in scan_result.symbols
                if Path(s.file_path).resolve() == Path(added_file_abs)
            ]
            all_symbols.extend(file_symbols)
        except Exception as e:
            logger.error(f"Failed to scan {file_path}: {e}")
            continue

    logger.info(f"Extracted {len(all_symbols)} symbols from {len(added_files)} new files")

    return all_symbols
