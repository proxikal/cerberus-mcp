"""
Git diff parsing for detecting changed files and line ranges.
"""

import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple
from loguru import logger

from ..schemas import FileChange, ModifiedFile, LineRange


def get_git_root(project_path: Path) -> Optional[Path]:
    """
    Get the git repository root for a project path.

    Args:
        project_path: Path to check

    Returns:
        Git root path or None if not a git repo
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
        return None
    except Exception as e:
        logger.debug(f"Error getting git root: {e}")
        return None


def get_current_commit(project_path: Path) -> Optional[str]:
    """
    Get the current git commit hash.

    Args:
        project_path: Path to git repository

    Returns:
        Commit hash or None if error
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        logger.debug(f"Error getting current commit: {e}")
        return None


def get_git_diff(project_path: Path, from_commit: Optional[str] = None) -> Optional[str]:
    """
    Get git diff output for the project.

    Args:
        project_path: Path to git repository
        from_commit: Commit to compare from (default: compare working tree to HEAD)

    Returns:
        Git diff output or None if error
    """
    try:
        if from_commit:
            # Compare from specific commit to working tree
            cmd = ["git", "diff", from_commit, "HEAD", "--unified=0"]
        else:
            # Compare working tree changes (staged + unstaged)
            cmd = ["git", "diff", "HEAD", "--unified=0"]

        result = subprocess.run(
            cmd,
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return result.stdout

        logger.warning(f"Git diff failed with code {result.returncode}: {result.stderr}")
        return None
    except subprocess.TimeoutExpired:
        logger.error("Git diff timed out after 30 seconds")
        return None
    except Exception as e:
        logger.error(f"Error running git diff: {e}")
        return None


def get_untracked_files(project_path: Path) -> List[str]:
    """
    Get list of untracked files in git repository.

    Args:
        project_path: Path to git repository

    Returns:
        List of untracked file paths (relative to project root)
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            files = result.stdout.strip().split("\n")
            return [f for f in files if f]

        return []
    except Exception as e:
        logger.debug(f"Error getting untracked files: {e}")
        return []


def parse_git_diff(diff_output: str, project_root: Path) -> Tuple[List[str], List[ModifiedFile], List[str]]:
    """
    Parse git diff output to extract changed files and line ranges.

    Args:
        diff_output: Output from git diff
        project_root: Root path of the git repository

    Returns:
        Tuple of (added_files, modified_files, deleted_files)
    """
    added_files: List[str] = []
    modified_files: List[ModifiedFile] = []
    deleted_files: List[str] = []

    # Split diff into file sections
    file_sections = re.split(r'^diff --git ', diff_output, flags=re.MULTILINE)

    for section in file_sections:
        if not section.strip():
            continue

        # Extract file paths from "diff --git a/file b/file" or already split section
        file_match = re.search(r'^a/(.*?) b/(.*?)$', section, re.MULTILINE)
        if not file_match:
            # Try to match if already split (section doesn't start with "diff --git")
            file_match = re.match(r'a/(.*?) b/(.*?)(?:\n|$)', section)

        if not file_match:
            continue

        old_path = file_match.group(1)
        new_path = file_match.group(2)

        # Check if file was deleted
        if re.search(r'^deleted file mode', section, re.MULTILINE):
            deleted_files.append(old_path)
            logger.debug(f"Detected deleted file: {old_path}")
            continue

        # Check if file was added
        if re.search(r'^new file mode', section, re.MULTILINE):
            added_files.append(new_path)
            logger.debug(f"Detected new file: {new_path}")
            continue

        # File was modified - extract changed line ranges
        changed_lines = parse_line_ranges(section)

        if changed_lines:
            modified_file = ModifiedFile(
                path=new_path,
                changed_lines=changed_lines,
                affected_symbols=[],  # Will be populated by change analyzer
            )
            modified_files.append(modified_file)
            logger.debug(f"Detected modified file: {new_path} with {len(changed_lines)} changed ranges")

    return added_files, modified_files, deleted_files


def parse_line_ranges(diff_section: str) -> List[LineRange]:
    """
    Parse line ranges from a diff section.

    Parses unified diff headers like:
    @@ -15,3 +15,5 @@ (removed 3 lines starting at 15, added 5 lines starting at 15)

    Args:
        diff_section: Section of diff output for a single file

    Returns:
        List of LineRange objects representing changes
    """
    line_ranges: List[LineRange] = []

    # Match unified diff headers: @@ -old_start,old_count +new_start,new_count @@
    hunk_pattern = r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@'

    for match in re.finditer(hunk_pattern, diff_section):
        old_start = int(match.group(1))
        old_count = int(match.group(2)) if match.group(2) else 1
        new_start = int(match.group(3))
        new_count = int(match.group(4)) if match.group(4) else 1

        # Determine change type based on counts
        if old_count == 0 and new_count > 0:
            # Lines were added
            line_ranges.append(
                LineRange(
                    start=new_start,
                    end=new_start + new_count - 1,
                    change_type="added",
                )
            )
        elif old_count > 0 and new_count == 0:
            # Lines were deleted
            line_ranges.append(
                LineRange(
                    start=old_start,
                    end=old_start + old_count - 1,
                    change_type="deleted",
                )
            )
        else:
            # Lines were modified
            line_ranges.append(
                LineRange(
                    start=new_start,
                    end=new_start + new_count - 1,
                    change_type="modified",
                )
            )

    return line_ranges
