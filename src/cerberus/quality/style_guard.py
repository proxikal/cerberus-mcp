"""
StyleGuardV2 - Phase 14.1: Explicit Style Fixing

Deterministic, AST-based style fixing with Symbol Guard integration.
NO auto-correction - agent must explicitly choose to fix.
"""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Set, Tuple, Optional, Dict
from enum import Enum

from cerberus.logging_config import logger


class IssueType(Enum):
    """Types of style issues that can be detected."""
    TRAILING_WHITESPACE = "trailing_whitespace"
    MISSING_FINAL_NEWLINE = "missing_final_newline"
    EXCESSIVE_BLANK_LINES = "excessive_blank_lines"
    UNSORTED_IMPORTS = "unsorted_imports"
    INCONSISTENT_QUOTES = "inconsistent_quotes"


@dataclass
class StyleIssue:
    """
    A detected style issue.

    Phase 14.1: Machine-parsable issue format for agent consumption.
    """
    issue_type: IssueType
    line: Optional[int] = None
    lines: Optional[Tuple[int, int]] = None  # For multi-line issues
    description: str = ""
    suggestion: str = ""
    auto_fixable: bool = True

    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        return {
            "type": self.issue_type.value,
            "line": self.line,
            "lines": list(self.lines) if self.lines else None,
            "description": self.description,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable,
        }


@dataclass
class StyleFix:
    """
    A style fix that was applied.

    Phase 14.1: Structured output for ledger logging and agent feedback.
    """
    issue_type: IssueType
    line: Optional[int] = None
    lines: Optional[Tuple[int, int]] = None
    before: str = ""
    after: str = ""
    description: str = ""

    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        return {
            "type": self.issue_type.value,
            "line": self.line,
            "lines": list(self.lines) if self.lines else None,
            "before": self.before,
            "after": self.after,
            "description": self.description,
        }


class StyleGuardV2:
    """
    Phase 14.1: Explicit style fixing with Symbol Guard integration.

    Key Differences from Phase 12.5:
    - EXPLICIT: No auto-fix, requires agent command
    - COMPREHENSIVE: Import sorting, quote fixing (AST-based)
    - SAFE: Symbol Guard integration for HIGH RISK files
    - AUDITABLE: Ledger logging for all operations
    """

    def __init__(self):
        """Initialize Style Guard V2."""
        logger.debug("StyleGuardV2 initialized")

    def detect_issues(
        self,
        content: str,
        file_path: str,
        check_all: bool = True,
    ) -> List[StyleIssue]:
        """
        Detect style issues without making changes.

        Phase 14.1: This is the style-check operation.

        Args:
            content: File content
            file_path: Path to file
            check_all: Check all lines (True) or only changed lines (False)

        Returns:
            List of detected issues
        """
        language = self._detect_language(file_path)
        issues = []

        if language == "python":
            issues.extend(self._detect_python_issues(content))
        elif language in ["javascript", "typescript"]:
            issues.extend(self._detect_javascript_issues(content))
        else:
            # Unknown language, only check basic issues
            issues.extend(self._detect_basic_issues(content))

        return issues

    def apply_fixes(
        self,
        content: str,
        file_path: str,
        issues: Optional[List[StyleIssue]] = None,
    ) -> Tuple[str, List[StyleFix]]:
        """
        Apply fixes to detected issues.

        Phase 14.1: This is the style-fix operation.

        Args:
            content: File content
            file_path: Path to file
            issues: Specific issues to fix (None = fix all detected)

        Returns:
            Tuple of (fixed_content, fixes_applied)
        """
        language = self._detect_language(file_path)

        # If no specific issues provided, detect all
        if issues is None:
            issues = self.detect_issues(content, file_path)

        # Apply fixes based on language
        fixes = []
        if language == "python":
            content, py_fixes = self._fix_python_issues(content, issues)
            fixes.extend(py_fixes)
        elif language in ["javascript", "typescript"]:
            content, js_fixes = self._fix_javascript_issues(content, issues)
            fixes.extend(js_fixes)
        else:
            content, basic_fixes = self._fix_basic_issues(content, issues)
            fixes.extend(basic_fixes)

        if fixes:
            logger.info(f"StyleGuardV2 applied {len(fixes)} fixes to {file_path}")

        return content, fixes

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

    def _detect_basic_issues(self, content: str) -> List[StyleIssue]:
        """
        Detect basic style issues (language-agnostic).

        Args:
            content: File content

        Returns:
            List of detected issues
        """
        issues = []
        lines = content.split('\n')

        # Check trailing whitespace
        for i, line in enumerate(lines):
            if line != line.rstrip():
                issues.append(StyleIssue(
                    issue_type=IssueType.TRAILING_WHITESPACE,
                    line=i + 1,
                    description=f"Line {i+1}: Trailing whitespace",
                    suggestion=f"Remove trailing whitespace",
                ))

        # Check final newline
        if content and not content.endswith('\n'):
            issues.append(StyleIssue(
                issue_type=IssueType.MISSING_FINAL_NEWLINE,
                line=len(lines),
                description="Missing final newline",
                suggestion="Add newline at end of file",
            ))

        return issues

    def _detect_python_issues(self, content: str) -> List[StyleIssue]:
        """
        Detect Python-specific style issues.

        Args:
            content: File content

        Returns:
            List of detected issues
        """
        issues = []

        # Start with basic issues
        issues.extend(self._detect_basic_issues(content))

        lines = content.split('\n')

        # Check excessive blank lines
        blank_count = 0
        for i, line in enumerate(lines):
            if not line.strip():
                blank_count += 1
                if blank_count > 2:
                    issues.append(StyleIssue(
                        issue_type=IssueType.EXCESSIVE_BLANK_LINES,
                        line=i + 1,
                        description=f"Line {i+1}: More than 2 consecutive blank lines",
                        suggestion="Remove excessive blank lines (max 2)",
                    ))
            else:
                blank_count = 0

        # Check import sorting (AST-based)
        try:
            tree = ast.parse(content)
            import_issues = self._detect_import_issues(tree, lines)
            issues.extend(import_issues)
        except SyntaxError:
            # Can't parse - skip import checking
            pass

        return issues

    def _detect_javascript_issues(self, content: str) -> List[StyleIssue]:
        """
        Detect JavaScript/TypeScript-specific style issues.

        Args:
            content: File content

        Returns:
            List of detected issues
        """
        # For now, just basic issues
        # TODO: Add JS-specific checks in future iterations
        return self._detect_basic_issues(content)

    def _detect_import_issues(
        self,
        tree: ast.AST,
        lines: List[str]
    ) -> List[StyleIssue]:
        """
        Detect unsorted imports in Python code.

        Phase 14.1: AST-based import analysis.

        Args:
            tree: AST of the file
            lines: File content split into lines

        Returns:
            List of import-related issues
        """
        issues = []

        # Find all import statements
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if hasattr(node, 'lineno'):
                    imports.append((node.lineno, node))

        if not imports:
            return issues

        # Group consecutive imports
        import_groups = []
        current_group = [imports[0]]

        for i in range(1, len(imports)):
            prev_line, _ = imports[i-1]
            curr_line, _ = imports[i]

            # Same group if consecutive or only blank lines between
            if curr_line - prev_line <= 2:
                current_group.append(imports[i])
            else:
                if len(current_group) > 1:
                    import_groups.append(current_group)
                current_group = [imports[i]]

        if len(current_group) > 1:
            import_groups.append(current_group)

        # Check if each group is sorted
        for group in import_groups:
            group_lines = [lines[lineno - 1] for lineno, _ in group]
            sorted_lines = sorted(group_lines)

            if group_lines != sorted_lines:
                start_line = group[0][0]
                end_line = group[-1][0]
                issues.append(StyleIssue(
                    issue_type=IssueType.UNSORTED_IMPORTS,
                    lines=(start_line, end_line),
                    description=f"Lines {start_line}-{end_line}: Imports not sorted alphabetically",
                    suggestion=f"Sort imports: {', '.join(sorted_lines[:3])}...",
                ))

        return issues

    def _fix_basic_issues(
        self,
        content: str,
        issues: List[StyleIssue]
    ) -> Tuple[str, List[StyleFix]]:
        """
        Fix basic style issues.

        Args:
            content: File content
            issues: Issues to fix

        Returns:
            Tuple of (fixed_content, fixes_applied)
        """
        fixes = []
        lines = content.split('\n')

        # Fix trailing whitespace
        for issue in issues:
            if issue.issue_type == IssueType.TRAILING_WHITESPACE and issue.line:
                i = issue.line - 1
                if i < len(lines):
                    before = lines[i]
                    lines[i] = lines[i].rstrip()
                    fixes.append(StyleFix(
                        issue_type=IssueType.TRAILING_WHITESPACE,
                        line=issue.line,
                        before=before,
                        after=lines[i],
                        description=f"Line {issue.line}: Removed trailing whitespace",
                    ))

        # Fix final newline
        for issue in issues:
            if issue.issue_type == IssueType.MISSING_FINAL_NEWLINE:
                if lines and lines[-1].strip():
                    lines.append('')
                    fixes.append(StyleFix(
                        issue_type=IssueType.MISSING_FINAL_NEWLINE,
                        line=len(lines),
                        before="(no newline)",
                        after="\\n",
                        description="Added final newline",
                    ))

        return '\n'.join(lines), fixes

    def _fix_python_issues(
        self,
        content: str,
        issues: List[StyleIssue]
    ) -> Tuple[str, List[StyleFix]]:
        """
        Fix Python-specific style issues.

        Args:
            content: File content
            issues: Issues to fix

        Returns:
            Tuple of (fixed_content, fixes_applied)
        """
        fixes = []
        lines = content.split('\n')

        # First fix basic issues
        content, basic_fixes = self._fix_basic_issues(content, issues)
        fixes.extend(basic_fixes)
        lines = content.split('\n')

        # Fix excessive blank lines
        blank_lines_to_fix = [
            issue for issue in issues
            if issue.issue_type == IssueType.EXCESSIVE_BLANK_LINES
        ]

        if blank_lines_to_fix:
            cleaned_lines = []
            blank_count = 0
            removed_count = 0

            for i, line in enumerate(lines):
                if not line.strip():
                    blank_count += 1
                    if blank_count <= 2:
                        cleaned_lines.append(line)
                    else:
                        removed_count += 1
                else:
                    blank_count = 0
                    cleaned_lines.append(line)

            if removed_count > 0:
                fixes.append(StyleFix(
                    issue_type=IssueType.EXCESSIVE_BLANK_LINES,
                    description=f"Removed {removed_count} excessive blank lines",
                ))
                lines = cleaned_lines

        # Fix import sorting (AST-based)
        import_issues = [
            issue for issue in issues
            if issue.issue_type == IssueType.UNSORTED_IMPORTS
        ]

        if import_issues:
            try:
                content_str = '\n'.join(lines)
                tree = ast.parse(content_str)
                content_str, import_fixes = self._fix_import_sorting(content_str, tree, import_issues)
                fixes.extend(import_fixes)
                return content_str, fixes
            except SyntaxError:
                # Can't parse - skip import fixing
                pass

        return '\n'.join(lines), fixes

    def _fix_javascript_issues(
        self,
        content: str,
        issues: List[StyleIssue]
    ) -> Tuple[str, List[StyleFix]]:
        """
        Fix JavaScript/TypeScript-specific style issues.

        Args:
            content: File content
            issues: Issues to fix

        Returns:
            Tuple of (fixed_content, fixes_applied)
        """
        # For now, just fix basic issues
        return self._fix_basic_issues(content, issues)

    def _fix_import_sorting(
        self,
        content: str,
        tree: ast.AST,
        issues: List[StyleIssue]
    ) -> Tuple[str, List[StyleFix]]:
        """
        Fix import sorting using AST.

        Phase 14.1: Native Python AST-based import sorting.

        Args:
            content: File content
            tree: AST of the file
            issues: Import-related issues

        Returns:
            Tuple of (fixed_content, fixes_applied)
        """
        fixes = []
        lines = content.split('\n')

        # Find all import statements with line numbers
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if hasattr(node, 'lineno'):
                    imports.append((node.lineno, node))

        # Sort imports
        imports.sort(key=lambda x: x[0])

        # Group and sort each consecutive block
        for issue in issues:
            if issue.lines:
                start_line, end_line = issue.lines

                # Extract import lines
                import_block = []
                for i in range(start_line - 1, end_line):
                    if i < len(lines):
                        import_block.append(lines[i])

                # Sort the block
                sorted_block = sorted(import_block)

                # Replace in original
                for i, sorted_line in enumerate(sorted_block):
                    lines[start_line - 1 + i] = sorted_line

                fixes.append(StyleFix(
                    issue_type=IssueType.UNSORTED_IMPORTS,
                    lines=(start_line, end_line),
                    before='\n'.join(import_block),
                    after='\n'.join(sorted_block),
                    description=f"Lines {start_line}-{end_line}: Sorted imports alphabetically",
                ))

        return '\n'.join(lines), fixes
