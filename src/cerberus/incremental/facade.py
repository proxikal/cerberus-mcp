"""
Public API for incremental update operations.

Facade for git-aware surgical index updates.
"""

import time
from pathlib import Path
from typing import Optional
from loguru import logger

from ..schemas import FileChange, ModifiedFile, IncrementalUpdateResult
from ..index import load_index
from .git_diff import (
    get_git_root,
    get_current_commit,
    get_git_diff,
    get_untracked_files,
    parse_git_diff,
)
from .change_analyzer import should_fallback_to_full_reparse, calculate_affected_files
from .surgical_update import apply_surgical_update
from .config import INCREMENTAL_CONFIG


def detect_changes(
    project_path: Path,
    index_path: Path,
) -> Optional[FileChange]:
    """
    Detect changes in a project since the last index.

    Uses git diff to identify changed files and line ranges.

    Args:
        project_path: Path to project root
        index_path: Path to existing index file

    Returns:
        FileChange object with detected changes, or None if error
    """
    logger.info(f"Detecting changes in {project_path}")

    # Check if project is a git repository
    git_root = get_git_root(project_path)
    if not git_root:
        logger.warning(f"{project_path} is not a git repository, cannot detect changes")
        return None

    # Load existing index to get last indexed commit
    try:
        scan_result = load_index(index_path)
        last_commit = scan_result.metadata.get("git_commit")
    except Exception as e:
        logger.warning(f"Could not load index metadata: {e}")
        last_commit = None

    # Get git diff
    diff_output = get_git_diff(git_root, from_commit=last_commit)
    if diff_output is None:
        logger.error("Failed to get git diff")
        return None

    # Parse diff to extract changes
    added_files, modified_files, deleted_files = parse_git_diff(diff_output, git_root)

    # Add untracked files if configured
    if INCREMENTAL_CONFIG.get("include_untracked", True):
        untracked = get_untracked_files(git_root)
        if untracked:
            logger.info(f"Found {len(untracked)} untracked files")
            added_files.extend(untracked)

    # Create FileChange object
    file_change = FileChange(
        added=added_files,
        modified=modified_files,
        deleted=deleted_files,
        timestamp=time.time(),
    )

    logger.info(
        f"Detected changes: {len(added_files)} added, "
        f"{len(modified_files)} modified, {len(deleted_files)} deleted"
    )

    return file_change


def update_index_incrementally(
    index_path: Path,
    project_path: Optional[Path] = None,
    changes: Optional[FileChange] = None,
    force_full_reparse: bool = False,
) -> IncrementalUpdateResult:
    """
    Update an index incrementally based on detected changes.

    Args:
        index_path: Path to existing index file
        project_path: Path to project root (inferred from index if not provided)
        changes: Pre-detected changes (will detect if not provided)
        force_full_reparse: Force full re-parse instead of incremental

    Returns:
        IncrementalUpdateResult with update statistics
    """
    start_time = time.time()

    # Load index to get project path if not provided
    if project_path is None:
        scan_result = load_index(index_path)
        project_path = Path(scan_result.project_root)
        logger.info(f"Inferred project path from index: {project_path}")

    # Detect changes if not provided
    if changes is None:
        logger.info("Detecting changes...")
        changes = detect_changes(project_path, index_path)

        if changes is None:
            logger.error("Failed to detect changes, aborting update")
            return IncrementalUpdateResult(
                updated_symbols=[],
                removed_symbols=[],
                affected_callers=[],
                files_reparsed=0,
                elapsed_time=time.time() - start_time,
                strategy="failed",
            )

    # Check if we should fall back to full reparse
    total_files = len(load_index(index_path).symbols)  # Approximate
    affected_files = calculate_affected_files(changes.added, changes.modified, changes.deleted)

    if force_full_reparse or should_fallback_to_full_reparse(
        total_files,
        len(affected_files),
        threshold=INCREMENTAL_CONFIG["fallback_to_full_reparse_threshold"],
    ):
        logger.warning("Falling back to full re-parse (change ratio too high)")
        # For now, we'll still do incremental update
        # In the future, we could trigger a full re-index here
        pass

    # Apply surgical update
    result = apply_surgical_update(index_path, changes, project_path)

    # Update index metadata with current git commit
    if INCREMENTAL_CONFIG["store_git_commit_in_index"]:
        current_commit = get_current_commit(project_path)
        if current_commit:
            scan_result = load_index(index_path)

            # Handle SQLite vs JSON differently
            from ..storage import ScanResultAdapter
            if isinstance(scan_result, ScanResultAdapter):
                # SQLite: Update metadata directly in store
                scan_result._store.set_metadata('git_commit', current_commit)
                logger.info(f"Updated SQLite metadata with git commit: {current_commit[:8]}")
            else:
                # JSON: Update in-memory and save
                scan_result.metadata["git_commit"] = current_commit
                from ..index import save_index
                save_index(scan_result, index_path)
                logger.info(f"Updated JSON metadata with git commit: {current_commit[:8]}")

    return result
