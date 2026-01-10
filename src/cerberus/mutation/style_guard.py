"""
StyleGuard: Mini-linter for preventing lint rot.

Phase 12.5: Auto-fixes uncontroversial issues in changed lines only,
never blocking valid logic.
"""

import re
from typing import Tuple, List, Set
from pathlib import Path

from cerberus.logging_config import logger


class StyleGuard:
    """
    Lightweight linter that auto-fixes simple style issues.

    Phase 12.5: Prevents "lint rot" and sloppy AI code by automatically
    fixing uncontroversial issues before atomic writes.
    """

    def __init__(self):
        """Initialize style guard."""
        logger.debug("StyleGuard initialized")

    def auto_fix(
        self,
        content: str,
        file_path: str,
        changed_line_numbers: Set[int]
    ) -> Tuple[str, List[str]]:
        """
        Auto-fix simple style issues in changed lines only.

        Args:
            content: File content
            file_path: Path to file
            changed_line_numbers: Set of line numbers that were changed

        Returns:
            Tuple of (fixed_content, fixes_applied)
        """
        language = self._detect_language(file_path)
        fixes_applied = []

        if language == "python":
            content, py_fixes = self._fix_python_issues(content, changed_line_numbers)
            fixes_applied.extend(py_fixes)
        elif language in ["javascript", "typescript"]:
            content, js_fixes = self._fix_javascript_issues(content, changed_line_numbers)
            fixes_applied.extend(js_fixes)

        if fixes_applied:
            logger.info(f"StyleGuard applied {len(fixes_applied)} auto-fixes")

        return content, fixes_applied

    def _detect_language(self, file_path: str) -> str:
        """
        Detect file language from extension.

        Args:
            file_path: Path to file

        Returns:
            Language identifier
        """
        ext = Path(file_path).suffix.lower()

        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".jsx": "javascript",
            ".tsx": "typescript",
            ".go": "go",
            ".java": "java",
            ".rs": "rust",
        }

        return language_map.get(ext, "unknown")

    def _fix_python_issues(
        self,
        content: str,
        changed_lines: Set[int]
    ) -> Tuple[str, List[str]]:
        """
        Fix Python-specific style issues.

        Args:
            content: File content
            changed_lines: Set of changed line numbers

        Returns:
            Tuple of (fixed_content, fixes_applied)
        """
        lines = content.split('\n')
        fixes = []

        # Auto-fix: Remove trailing whitespace on changed lines
        for i in changed_lines:
            if i < len(lines) and lines[i].rstrip() != lines[i]:
                lines[i] = lines[i].rstrip()
                fixes.append(f"Line {i+1}: Removed trailing whitespace")

        # Auto-fix: Ensure single newline at EOF
        if lines and lines[-1].strip() and not content.endswith('\n'):
            lines.append('')
            fixes.append("EOF: Added final newline")

        # Auto-fix: Remove multiple consecutive blank lines (max 2)
        cleaned_lines = []
        blank_count = 0

        for i, line in enumerate(lines):
            if not line.strip():
                blank_count += 1
                if blank_count <= 2:  # Allow max 2 consecutive blank lines
                    cleaned_lines.append(line)
                elif (i + 1) in changed_lines:
                    # Only fix if in changed region
                    fixes.append(f"Line {i+1}: Removed excessive blank line")
            else:
                blank_count = 0
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines), fixes

    def _fix_javascript_issues(
        self,
        content: str,
        changed_lines: Set[int]
    ) -> Tuple[str, List[str]]:
        """
        Fix JavaScript/TypeScript-specific style issues.

        Args:
            content: File content
            changed_lines: Set of changed line numbers

        Returns:
            Tuple of (fixed_content, fixes_applied)
        """
        lines = content.split('\n')
        fixes = []

        # Auto-fix: Remove trailing whitespace on changed lines
        for i in changed_lines:
            if i < len(lines) and lines[i].rstrip() != lines[i]:
                lines[i] = lines[i].rstrip()
                fixes.append(f"Line {i+1}: Removed trailing whitespace")

        # Auto-fix: Ensure single newline at EOF
        if lines and lines[-1].strip() and not content.endswith('\n'):
            lines.append('')
            fixes.append("EOF: Added final newline")

        return '\n'.join(lines), fixes

    def should_run(self, enabled: bool = True) -> bool:
        """
        Determine if style guard should run.

        Args:
            enabled: Whether style guard is enabled

        Returns:
            True if should run
        """
        return enabled
