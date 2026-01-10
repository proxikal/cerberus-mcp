"""
StyleDetector - Phase 14.1: Style Issue Detection

Detects style issues without making changes (style-check operation).
"""

from typing import List
from pathlib import Path

from cerberus.quality.style_guard import StyleGuardV2, StyleIssue
from cerberus.logging_config import logger


class StyleDetector:
    """
    Phase 14.1: Style issue detector for preview mode.

    This is the engine behind `cerberus quality style-check`.
    """

    def __init__(self):
        """Initialize detector."""
        self.style_guard = StyleGuardV2()
        logger.debug("StyleDetector initialized")

    def check_file(self, file_path: str) -> List[StyleIssue]:
        """
        Check a single file for style issues.

        Args:
            file_path: Path to file to check

        Returns:
            List of detected issues
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            issues = self.style_guard.detect_issues(content, file_path)
            logger.debug(f"Detected {len(issues)} issues in {file_path}")
            return issues

        except Exception as e:
            logger.error(f"Failed to check {file_path}: {e}")
            return []

    def check_directory(
        self,
        directory: str,
        recursive: bool = False,
        extensions: List[str] = None
    ) -> dict[str, List[StyleIssue]]:
        """
        Check all files in a directory.

        Args:
            directory: Directory path
            recursive: Recursively check subdirectories
            extensions: File extensions to check (default: .py, .js, .ts)

        Returns:
            Dict mapping file paths to their issues
        """
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.jsx', '.tsx']

        dir_path = Path(directory)
        results = {}

        if recursive:
            files = [
                f for f in dir_path.rglob('*')
                if f.is_file() and f.suffix in extensions
            ]
        else:
            files = [
                f for f in dir_path.glob('*')
                if f.is_file() and f.suffix in extensions
            ]

        for file_path in files:
            issues = self.check_file(str(file_path))
            if issues:
                results[str(file_path)] = issues

        logger.info(f"Checked {len(files)} files, found issues in {len(results)}")
        return results

    def format_issues(
        self,
        issues: List[StyleIssue],
        file_path: str = None,
        mode: str = "text"
    ) -> str:
        """
        Format issues for display.

        Args:
            issues: List of issues
            file_path: Optional file path for context
            mode: "text" or "json"

        Returns:
            Formatted string
        """
        if not issues:
            return "✅ No style issues detected"

        if mode == "json":
            import json
            return json.dumps(
                {
                    "file": file_path,
                    "issues": [issue.to_dict() for issue in issues],
                    "count": len(issues),
                },
                indent=2
            )

        # Text mode
        lines = []
        if file_path:
            lines.append(f"[File: {file_path}]")

        lines.append(f"⚠️  {len(issues)} style issue(s) detected:")
        lines.append("")

        for issue in issues:
            if issue.line:
                lines.append(f"  Line {issue.line}: {issue.description}")
            elif issue.lines:
                start, end = issue.lines
                lines.append(f"  Lines {start}-{end}: {issue.description}")
            else:
                lines.append(f"  {issue.description}")

            if issue.suggestion:
                lines.append(f"    → {issue.suggestion}")

        return '\n'.join(lines)
