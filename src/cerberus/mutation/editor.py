"""
CodeEditor: Safe byte-range replacements with atomic writes.

Phase 11: Core editing operations with backup and rollback.
"""

import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

from cerberus.logging_config import logger
from cerberus.schemas import SymbolLocation
from .config import MUTATION_CONFIG


class CodeEditor:
    """
    Perform safe code mutations with backup and atomic writes.

    Features:
    - Mandatory backups before edits
    - Atomic writes (temp file + rename)
    - UTF-8 encoding handling
    - Line ending preservation (LF/CRLF)
    """

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize code editor with optional config.

        Args:
            config: Optional config overrides (merges with MUTATION_CONFIG)
        """
        self.config = {**MUTATION_CONFIG, **(config or {})}
        self._ensure_backup_dir()

    def _ensure_backup_dir(self):
        """Ensure backup directory exists."""
        if self.config["backup_enabled"]:
            backup_dir = Path(self.config["backup_dir"])
            backup_dir.mkdir(exist_ok=True)

    def replace_symbol(
        self,
        location: SymbolLocation,
        new_code: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Replace a symbol's byte range with new code.

        Args:
            location: Symbol location with byte ranges
            new_code: New code to replace the symbol

        Returns:
            (success, backup_path)
        """
        file_path = Path(location.file_path)

        # Read original content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return False, None

        # Phase 12: Capture file state for optimistic locking
        file_state = self._get_file_state(str(file_path))

        # Create backup
        backup_path = None
        if self.config["backup_enabled"]:
            backup_path = self.create_backup(str(file_path))
            if not backup_path:
                logger.error("Backup creation failed, aborting edit")
                return False, None

        # Detect line ending style
        line_ending = self._detect_line_ending(original_content)

        # Replace byte range
        modified_content = (
            original_content[:location.start_byte] +
            new_code +
            original_content[location.end_byte:]
        )

        # Normalize line endings
        modified_content = self._normalize_line_endings(modified_content, line_ending)

        # Phase 12: Check file unchanged before write (optimistic locking)
        try:
            self._check_file_unchanged(str(file_path), file_state)
        except RuntimeError as e:
            logger.error(str(e))
            return False, backup_path

        # Write atomically
        success = self._atomic_write(str(file_path), modified_content)

        if success:
            logger.info(f"Successfully replaced '{location.symbol_name}' in {file_path}")
        else:
            logger.error(f"Failed to write changes to {file_path}")
            # Restore from backup if write failed
            if backup_path:
                self._restore_backup(backup_path, str(file_path))

        return success, backup_path

    def insert_symbol(
        self,
        file_path: str,
        byte_offset: int,
        new_code: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Insert code at a specific byte offset.

        Args:
            file_path: Path to file
            byte_offset: Byte offset for insertion
            new_code: Code to insert

        Returns:
            (success, backup_path)
        """
        path = Path(file_path)

        # Read original content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return False, None

        # Phase 12: Capture file state for optimistic locking
        file_state = self._get_file_state(file_path)

        # Create backup
        backup_path = None
        if self.config["backup_enabled"]:
            backup_path = self.create_backup(file_path)
            if not backup_path:
                logger.error("Backup creation failed, aborting insert")
                return False, None

        # Detect line ending
        line_ending = self._detect_line_ending(original_content)

        # Insert at byte offset
        modified_content = (
            original_content[:byte_offset] +
            new_code +
            original_content[byte_offset:]
        )

        # Normalize line endings
        modified_content = self._normalize_line_endings(modified_content, line_ending)

        # Phase 12: Check file unchanged before write (optimistic locking)
        try:
            self._check_file_unchanged(file_path, file_state)
        except RuntimeError as e:
            logger.error(str(e))
            return False, backup_path

        # Write atomically
        success = self._atomic_write(file_path, modified_content)

        if success:
            logger.info(f"Successfully inserted code at byte {byte_offset} in {file_path}")
        else:
            logger.error(f"Failed to insert code in {file_path}")
            if backup_path:
                self._restore_backup(backup_path, file_path)

        return success, backup_path

    def delete_symbol(
        self,
        location: SymbolLocation,
        keep_decorators: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Delete a symbol from the file.

        Args:
            location: Symbol location
            keep_decorators: If True, only delete body, keep decorators

        Returns:
            (success, backup_path)
        """
        file_path = Path(location.file_path)

        # Read original content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return False, None

        # Phase 12: Capture file state for optimistic locking
        file_state = self._get_file_state(str(file_path))

        # Create backup
        backup_path = None
        if self.config["backup_enabled"]:
            backup_path = self.create_backup(str(file_path))
            if not backup_path:
                logger.error("Backup creation failed, aborting delete")
                return False, None

        # Detect line ending
        line_ending = self._detect_line_ending(original_content)

        # Delete byte range
        modified_content = (
            original_content[:location.start_byte] +
            original_content[location.end_byte:]
        )

        # Clean up extra whitespace (remove double blank lines)
        lines = modified_content.split('\n')
        cleaned_lines = []
        prev_blank = False
        for line in lines:
            is_blank = line.strip() == ""
            if not (is_blank and prev_blank):
                cleaned_lines.append(line)
            prev_blank = is_blank

        modified_content = '\n'.join(cleaned_lines)

        # Normalize line endings
        modified_content = self._normalize_line_endings(modified_content, line_ending)

        # Phase 12: Check file unchanged before write (optimistic locking)
        try:
            self._check_file_unchanged(str(file_path), file_state)
        except RuntimeError as e:
            logger.error(str(e))
            return False, backup_path

        # Write atomically
        success = self._atomic_write(str(file_path), modified_content)

        if success:
            logger.info(f"Successfully deleted '{location.symbol_name}' from {file_path}")
        else:
            logger.error(f"Failed to delete symbol from {file_path}")
            if backup_path:
                self._restore_backup(backup_path, str(file_path))

        return success, backup_path

    def create_backup(self, file_path: str) -> Optional[str]:
        """
        Create a timestamped backup of a file.

        Args:
            file_path: Path to file to backup

        Returns:
            Path to backup file or None if failed
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"Cannot backup non-existent file: {file_path}")
            return None

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{path.name}.{timestamp}.backup"
        backup_path = Path(self.config["backup_dir"]) / backup_filename

        try:
            shutil.copy2(str(path), str(backup_path))
            logger.debug(f"Created backup: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def _atomic_write(self, file_path: str, content: str) -> bool:
        """
        Write file atomically using temp file + rename.

        Args:
            file_path: Target file path
            content: Content to write

        Returns:
            True if successful
        """
        path = Path(file_path)

        try:
            # Create temp file in same directory as target
            # This ensures same filesystem for atomic rename
            fd, temp_path = tempfile.mkstemp(
                dir=str(path.parent),
                prefix=f".{path.name}.",
                suffix=".tmp"
            )

            try:
                # Write to temp file
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Atomic rename
                os.replace(temp_path, str(path))
                logger.debug(f"Atomic write completed: {file_path}")
                return True

            except Exception as e:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                logger.error(f"Failed during atomic write: {e}")
                return False

        except Exception as e:
            logger.error(f"Failed to create temp file: {e}")
            return False

    def _restore_backup(self, backup_path: str, target_path: str) -> bool:
        """
        Restore file from backup.

        Args:
            backup_path: Path to backup file
            target_path: Path to restore to

        Returns:
            True if successful
        """
        try:
            shutil.copy2(backup_path, target_path)
            logger.info(f"Restored {target_path} from backup")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

    def _detect_line_ending(self, content: str) -> str:
        """
        Detect line ending style (LF vs CRLF).

        Args:
            content: File content

        Returns:
            '\r\n' for CRLF, '\n' for LF
        """
        if '\r\n' in content:
            return '\r\n'
        return '\n'

    def _normalize_line_endings(self, content: str, line_ending: str) -> str:
        """
        Normalize line endings to match detected style.

        Args:
            content: Content to normalize
            line_ending: Target line ending ('\n' or '\r\n')

        Returns:
            Normalized content
        """
        # First convert all to LF
        content = content.replace('\r\n', '\n')
        # Then convert to target if CRLF
        if line_ending == '\r\n':
            content = content.replace('\n', '\r\n')
        return content

    def _get_file_state(self, file_path: str) -> Tuple[float, str]:
        """
        Get file state for optimistic locking.
        Phase 12: Capture mtime and content hash for race condition detection.

        Args:
            file_path: Path to file

        Returns:
            (mtime, content_hash) tuple
        """
        import hashlib

        path = Path(file_path)
        if not path.exists():
            return (0.0, "")

        # Get modification time
        mtime = path.stat().st_mtime

        # Compute content hash
        try:
            with open(path, 'rb') as f:
                content_hash = hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash {file_path}: {e}")
            content_hash = ""

        return (mtime, content_hash)

    def _check_file_unchanged(
        self,
        file_path: str,
        expected_state: Tuple[float, str]
    ) -> None:
        """
        Verify file hasn't changed since expected_state.
        Phase 12: Optimistic locking for concurrent edit detection.

        Args:
            file_path: Path to file
            expected_state: (mtime, hash) captured at read time

        Raises:
            RuntimeError: If file was modified externally
        """
        current_state = self._get_file_state(file_path)
        expected_mtime, expected_hash = expected_state
        current_mtime, current_hash = current_state

        # Check if file was modified
        if current_hash != expected_hash or current_mtime != expected_mtime:
            raise RuntimeError(
                f"[ERROR] File modified externally: {file_path}. "
                f"Expected mtime={expected_mtime}, hash={expected_hash[:8]}... "
                f"but found mtime={current_mtime}, hash={current_hash[:8]}..."
            )

    def generate_unified_diff(
        self,
        file_path: str,
        original_content: str,
        modified_content: str,
        max_diff_lines: int = 100
    ) -> str:
        """
        Generate unified diff between original and modified content.
        Phase 12: Diff-first feedback for AI agents.
        Phase 12.5: Token-aware diffing with intelligent truncation.

        Args:
            file_path: Path to file (for diff header)
            original_content: Original file content
            modified_content: Modified file content
            max_diff_lines: Maximum diff lines before truncation (default: 100)

        Returns:
            Unified diff string (possibly truncated)
        """
        import difflib
        from datetime import datetime

        original_lines = original_content.splitlines(keepends=True)
        modified_lines = modified_content.splitlines(keepends=True)

        diff_lines = list(difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=''
        ))

        # Phase 12.5: Token-aware diffing - truncate if too large
        if len(diff_lines) > max_diff_lines:
            return self._truncate_large_diff(diff_lines, max_diff_lines)

        return ''.join(diff_lines)

    def _truncate_large_diff(
        self,
        diff_lines: List[str],
        max_lines: int
    ) -> str:
        """
        Intelligently truncate large diffs.

        Phase 12.5: Preserve all deleted lines (high risk), truncate added lines.

        Args:
            diff_lines: Full diff lines
            max_lines: Maximum lines to keep

        Returns:
            Truncated diff with metadata
        """
        truncated = []
        header_lines = []
        deleted_lines = []
        context_lines = []
        added_lines = []
        current_lines = 0

        # Collect all lines by type
        for line in diff_lines:
            if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
                header_lines.append(line)
            elif line.startswith('-'):
                deleted_lines.append(line)
            elif line.startswith('+'):
                added_lines.append(line)
            else:
                context_lines.append(line)

        # Always include headers
        truncated.extend(header_lines)
        current_lines += len(header_lines)

        # Always include ALL deleted lines (critical - shows what was removed)
        truncated.extend(deleted_lines)
        current_lines += len(deleted_lines)

        # Add context lines if space permits
        remaining_lines = max_lines - current_lines
        if remaining_lines > 0:
            context_to_add = context_lines[:remaining_lines]
            truncated.extend(context_to_add)
            current_lines += len(context_to_add)
            remaining_lines = max_lines - current_lines

        # Truncate added lines if necessary
        if remaining_lines > 0:
            added_to_show = min(len(added_lines), remaining_lines - 1)  # -1 for truncation notice
            truncated.extend(added_lines[:added_to_show])

            if len(added_lines) > added_to_show:
                truncation_notice = f"\n[... {len(added_lines) - added_to_show} added lines truncated for brevity ...]\n"
                truncated.append(truncation_notice)
        else:
            truncation_notice = f"\n[... {len(added_lines)} added lines truncated for brevity ...]\n"
            truncated.append(truncation_notice)

        return ''.join(truncated)
