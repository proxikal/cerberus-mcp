"""
Phase 14.1 Tests: Style Guard Foundation

Tests for explicit style checking and fixing with Symbol Guard integration.
"""

import pytest
import tempfile
from pathlib import Path

pytestmark = pytest.mark.fast

from cerberus.quality import StyleGuardV2, StyleDetector, StyleFixer, IssueType


class TestStyleGuardV2:
    """Test StyleGuardV2 core functionality."""

    def test_detect_trailing_whitespace(self):
        """Test detection of trailing whitespace."""
        content = "def foo():  \n    pass\n"
        guard = StyleGuardV2()
        issues = guard.detect_issues(content, "test.py")

        assert len(issues) == 1
        assert issues[0].issue_type == IssueType.TRAILING_WHITESPACE
        assert issues[0].line == 1

    def test_detect_missing_final_newline(self):
        """Test detection of missing final newline."""
        content = "def foo():\n    pass"
        guard = StyleGuardV2()
        issues = guard.detect_issues(content, "test.py")

        assert any(issue.issue_type == IssueType.MISSING_FINAL_NEWLINE for issue in issues)

    def test_detect_excessive_blank_lines(self):
        """Test detection of excessive blank lines."""
        content = "def foo():\n    pass\n\n\n\n\ndef bar():\n    pass\n"
        guard = StyleGuardV2()
        issues = guard.detect_issues(content, "test.py")

        excessive_issues = [i for i in issues if i.issue_type == IssueType.EXCESSIVE_BLANK_LINES]
        assert len(excessive_issues) > 0

    def test_detect_unsorted_imports(self):
        """Test detection of unsorted imports."""
        content = "import sys\nimport os\nimport ast\n\ndef foo():\n    pass\n"
        guard = StyleGuardV2()
        issues = guard.detect_issues(content, "test.py")

        import_issues = [i for i in issues if i.issue_type == IssueType.UNSORTED_IMPORTS]
        assert len(import_issues) == 1

    def test_fix_trailing_whitespace(self):
        """Test fixing trailing whitespace."""
        content = "def foo():  \n    pass  \n"
        guard = StyleGuardV2()
        fixed, fixes = guard.apply_fixes(content, "test.py")

        assert "  \n" not in fixed
        assert len(fixes) > 0
        assert any(f.issue_type == IssueType.TRAILING_WHITESPACE for f in fixes)

    def test_fix_excessive_blank_lines(self):
        """Test fixing excessive blank lines."""
        content = "def foo():\n    pass\n\n\n\n\ndef bar():\n    pass\n"
        guard = StyleGuardV2()
        fixed, fixes = guard.apply_fixes(content, "test.py")

        # Should reduce to max 2 blank lines
        assert "\n\n\n\n" not in fixed
        assert len(fixes) > 0

    def test_fix_import_sorting(self):
        """Test fixing import sorting."""
        content = "import sys\nimport os\nimport ast\n\ndef foo():\n    pass\n"
        guard = StyleGuardV2()
        fixed, fixes = guard.apply_fixes(content, "test.py")

        # Imports should be sorted alphabetically
        lines = fixed.split('\n')
        assert lines[0] == "import ast"
        assert lines[1] == "import os"
        assert lines[2] == "import sys"

        import_fixes = [f for f in fixes if f.issue_type == IssueType.UNSORTED_IMPORTS]
        assert len(import_fixes) == 1


class TestStyleDetector:
    """Test StyleDetector functionality."""

    def test_check_file(self):
        """Test checking a single file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def foo():  \n    pass")
            f.flush()
            temp_path = f.name

        try:
            detector = StyleDetector()
            issues = detector.check_file(temp_path)

            assert len(issues) > 0
            assert any(i.issue_type == IssueType.TRAILING_WHITESPACE for i in issues)
        finally:
            Path(temp_path).unlink()

    def test_format_issues_text(self):
        """Test formatting issues as text."""
        from cerberus.quality.style_guard import StyleIssue

        issues = [
            StyleIssue(
                issue_type=IssueType.TRAILING_WHITESPACE,
                line=1,
                description="Line 1: Trailing whitespace",
                suggestion="Remove trailing whitespace"
            )
        ]

        detector = StyleDetector()
        output = detector.format_issues(issues, "test.py", mode="text")

        assert "1 style issue(s)" in output
        assert "Line 1" in output

    def test_format_issues_json(self):
        """Test formatting issues as JSON."""
        import json
        from cerberus.quality.style_guard import StyleIssue

        issues = [
            StyleIssue(
                issue_type=IssueType.TRAILING_WHITESPACE,
                line=1,
                description="Line 1: Trailing whitespace",
                suggestion="Remove trailing whitespace"
            )
        ]

        detector = StyleDetector()
        output = detector.format_issues(issues, "test.py", mode="json")

        parsed = json.loads(output)
        assert parsed["count"] == 1
        assert parsed["issues"][0]["type"] == "trailing_whitespace"


class TestStyleFixer:
    """Test StyleFixer functionality."""

    def test_fix_file(self):
        """Test fixing a single file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def foo():  \n    pass")
            f.flush()
            temp_path = f.name

        try:
            fixer = StyleFixer()
            success, fixes = fixer.fix_file(temp_path)

            assert success
            assert len(fixes) > 0

            # Verify file was actually fixed
            with open(temp_path, 'r') as f:
                content = f.read()
                assert "  \n" not in content
        finally:
            Path(temp_path).unlink()

    def test_fix_file_preview(self):
        """Test preview mode doesn't modify file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            original = "def foo():  \n    pass"
            f.write(original)
            f.flush()
            temp_path = f.name

        try:
            fixer = StyleFixer()
            success, fixes = fixer.fix_file(temp_path, preview=True)

            assert success
            assert len(fixes) > 0

            # Verify file was NOT modified
            with open(temp_path, 'r') as f:
                content = f.read()
                assert content == original
        finally:
            Path(temp_path).unlink()

    def test_format_fixes_text(self):
        """Test formatting fixes as text."""
        from cerberus.quality.style_guard import StyleFix

        fixes = [
            StyleFix(
                issue_type=IssueType.TRAILING_WHITESPACE,
                line=1,
                before="def foo():  ",
                after="def foo():",
                description="Line 1: Removed trailing whitespace"
            )
        ]

        fixer = StyleFixer()
        output = fixer.format_fixes(fixes, "test.py", mode="text")

        assert "1 fix(es)" in output
        assert "Line 1" in output

    def test_format_fixes_json(self):
        """Test formatting fixes as JSON."""
        import json
        from cerberus.quality.style_guard import StyleFix

        fixes = [
            StyleFix(
                issue_type=IssueType.TRAILING_WHITESPACE,
                line=1,
                before="def foo():  ",
                after="def foo():",
                description="Line 1: Removed trailing whitespace"
            )
        ]

        fixer = StyleFixer()
        output = fixer.format_fixes(fixes, "test.py", mode="json")

        parsed = json.loads(output)
        assert parsed["count"] == 1
        assert parsed["fixes"][0]["type"] == "trailing_whitespace"


class TestIntegration:
    """Integration tests for Phase 14.1."""

    def test_full_workflow(self):
        """Test complete check -> fix workflow."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("import sys\nimport os\nimport ast\n\ndef foo():  \n    pass\n\n\n\n")
            f.flush()
            temp_path = f.name

        try:
            # Step 1: Check
            detector = StyleDetector()
            issues = detector.check_file(temp_path)
            assert len(issues) > 0

            # Step 2: Fix
            fixer = StyleFixer()
            success, fixes = fixer.fix_file(temp_path)
            assert success
            assert len(fixes) > 0

            # Step 3: Verify fixed
            issues_after = detector.check_file(temp_path)
            assert len(issues_after) < len(issues)

            # Step 4: Check file content
            with open(temp_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
                assert lines[0] == "import ast"  # Sorted
                assert lines[1] == "import os"
                assert lines[2] == "import sys"
                assert "  \n" not in content  # No trailing whitespace

        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
