"""
CodeFormatter: Auto-indentation and code formatting.

Phase 11: Pillar 1 - Auto-Indentation.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional, Tuple

from cerberus.logging_config import logger
from .config import FORMATTERS, INDENT_DETECTION


class CodeFormatter:
    """
    Handle code indentation and formatting.

    Features:
    - Detect file indentation style (spaces vs tabs)
    - Reindent code blocks to target level
    - Shell out to black/prettier for full file formatting
    """

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize formatter with optional config.

        Args:
            config: Optional config overrides
        """
        self.config = config or {}

    def format_code_block(
        self,
        code: str,
        target_indent_level: int,
        file_path: Optional[str] = None
    ) -> str:
        """
        Reindent a code block to match target indentation level.

        Args:
            code: Code block to reindent
            target_indent_level: Target indentation level (number of units)
            file_path: Optional file path to detect indent style from

        Returns:
            Reindented code
        """
        # Detect indent style from file if provided
        indent_unit = INDENT_DETECTION["default_indent"]
        if file_path:
            detected_indent = self.detect_file_indentation(file_path)
            if detected_indent:
                indent_unit = detected_indent

        # Calculate target indent prefix
        target_indent = indent_unit * target_indent_level

        # Split into lines
        lines = code.split('\n')

        # Find minimum indentation in code block (base level)
        min_indent = float('inf')
        for line in lines:
            if line.strip():  # Ignore blank lines
                indent = self._get_indent(line)
                min_indent = min(min_indent, len(indent))

        if min_indent == float('inf'):
            min_indent = 0

        # Reindent each line relative to base
        reindented_lines = []
        for line in lines:
            if not line.strip():
                # Keep blank lines blank
                reindented_lines.append("")
            else:
                indent = self._get_indent(line)
                relative_indent_level = (len(indent) - min_indent) // len(indent_unit)
                new_indent = indent_unit * (target_indent_level + relative_indent_level)
                reindented_lines.append(new_indent + line.lstrip())

        return '\n'.join(reindented_lines)

    def detect_file_indentation(self, file_path: str) -> Optional[str]:
        """
        Detect indentation style from a file.

        Args:
            file_path: Path to file

        Returns:
            Indent unit string (e.g., "    " or "\t") or None
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"File not found for indent detection: {file_path}")
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read file for indent detection: {e}")
            return None

        # Sample first N lines
        max_lines = INDENT_DETECTION["max_sample_lines"]
        sample_lines = lines[:max_lines]

        # Count tabs vs spaces
        tab_count = 0
        space_count = 0
        space_widths = {}

        for line in sample_lines:
            if not line.strip():
                continue

            indent = self._get_indent(line)
            if '\t' in indent:
                tab_count += 1
            elif len(indent) > 0:
                space_count += 1
                # Track space width frequency
                width = len(indent)
                space_widths[width] = space_widths.get(width, 0) + 1

        # Determine style
        if tab_count > space_count:
            return "\t"
        elif space_count > 0:
            # Find most common space width
            if space_widths:
                most_common_width = max(space_widths, key=space_widths.get)
                # Normalize to unit (likely 2 or 4)
                if most_common_width >= 4:
                    return "    "  # 4 spaces
                elif most_common_width >= 2:
                    return "  "  # 2 spaces
            return INDENT_DETECTION["default_indent"]
        else:
            return INDENT_DETECTION["default_indent"]

    def format_file(
        self,
        file_path: str,
        language: str,
        dry_run: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Format entire file using external formatter (black/prettier).

        Args:
            file_path: Path to file
            language: Language ("python", "javascript", "typescript")
            dry_run: If True, don't actually format

        Returns:
            (success, error_message)
        """
        if dry_run:
            logger.debug(f"Dry run: would format {file_path} with {language} formatter")
            return True, None

        # Get formatter config
        formatter_config = FORMATTERS.get(language)
        if not formatter_config:
            logger.warning(f"No formatter configured for {language}")
            return True, None  # Not an error, just unsupported

        command = formatter_config["command"]

        # Check if formatter is available
        if not shutil.which(command):
            logger.debug(f"Formatter '{command}' not found in PATH, skipping auto-format")
            return True, None  # Not an error, just unavailable

        # Build command
        args = formatter_config["args"]
        full_command = [command] + args + [file_path]

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"Formatter failed: {error_msg}")
                return False, error_msg

            logger.debug(f"Formatted {file_path} with {command}")
            return True, None

        except subprocess.TimeoutExpired:
            error_msg = f"Formatter timeout after 30s"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Formatter error: {e}"
            logger.error(error_msg)
            return False, error_msg

    def _get_indent(self, line: str) -> str:
        """
        Extract indentation from a line.

        Reused from synthesis/skeletonizer.py:335-337.
        """
        return line[:len(line) - len(line.lstrip())]
