"""
Tests for Phase 19.5: Documentation Validator

Tests for:
  - DocsValidator validation logic
  - validate-docs CLI command
  - ValidationIssue and ValidationResult dataclasses
"""

import json
import pytest
import tempfile
from pathlib import Path
from typer.testing import CliRunner

from cerberus.cli.docs_validator import (
    DocsValidator,
    ValidationIssue,
    ValidationResult,
    validate_docs_cmd,
)
from cerberus.main import app

runner = CliRunner()


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_to_dict_basic(self):
        """Test basic conversion to dict."""
        issue = ValidationIssue(
            category="command",
            severity="error",
            message="Command not found",
        )
        result = issue.to_dict()
        assert result["category"] == "command"
        assert result["severity"] == "error"
        assert result["message"] == "Command not found"
        assert "line" not in result
        assert "suggestion" not in result

    def test_to_dict_with_line(self):
        """Test conversion with line number."""
        issue = ValidationIssue(
            category="version",
            severity="warning",
            message="Version mismatch",
            line_number=1,
        )
        result = issue.to_dict()
        assert result["line"] == 1

    def test_to_dict_with_suggestion(self):
        """Test conversion with suggestion."""
        issue = ValidationIssue(
            category="example",
            severity="warning",
            message="Invalid syntax",
            suggestion="Check your code",
        )
        result = issue.to_dict()
        assert result["suggestion"] == "Check your code"


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_empty_result(self):
        """Test empty result."""
        result = ValidationResult(valid=True)
        data = result.to_dict()
        assert data["valid"] is True
        assert data["issues"] == []
        assert data["error_count"] == 0
        assert data["warning_count"] == 0

    def test_result_with_issues(self):
        """Test result with issues."""
        issues = [
            ValidationIssue("cmd", "error", "Error 1"),
            ValidationIssue("cmd", "warning", "Warning 1"),
            ValidationIssue("version", "warning", "Warning 2"),
        ]
        result = ValidationResult(valid=False, issues=issues)
        data = result.to_dict()
        assert data["valid"] is False
        assert len(data["issues"]) == 3
        assert data["error_count"] == 1
        assert data["warning_count"] == 2

    def test_result_with_stats(self):
        """Test result with stats."""
        result = ValidationResult(
            valid=True,
            stats={"documented_commands": 10, "valid_commands": 10},
        )
        data = result.to_dict()
        assert data["stats"]["documented_commands"] == 10


class TestDocsValidator:
    """Tests for DocsValidator class."""

    def test_validate_missing_file(self):
        """Test validation when file doesn't exist."""
        validator = DocsValidator(Path("/nonexistent/CERBERUS.md"))
        result = validator.validate()
        assert result.valid is False
        assert len(result.issues) == 1
        assert result.issues[0].category == "file"
        assert result.issues[0].severity == "error"

    def test_validate_valid_file(self, tmp_path):
        """Test validation with valid CERBERUS.md."""
        # Create a minimal valid CERBERUS.md
        cerberus_md = tmp_path / "CERBERUS.md"
        cerberus_md.write_text("""# CERBERUS v0.19.4 | UACP/1.2 | Machine-First Protocol
# Test documentation

## Commands

```bash
cerberus start
cerberus go src/file.py
cerberus blueprint src/file.py
```
""")
        validator = DocsValidator(cerberus_md)
        result = validator.validate()
        assert result.valid is True
        assert result.stats["code_blocks"] == 1

    def test_validate_extracts_commands(self, tmp_path):
        """Test that validator extracts commands from docs."""
        cerberus_md = tmp_path / "CERBERUS.md"
        cerberus_md.write_text("""# CERBERUS v0.19.4

## Commands

```bash
cerberus start
cerberus go file.py
cerberus retrieval blueprint file.py
cerberus memory learn "something"
```
""")
        validator = DocsValidator(cerberus_md)
        result = validator.validate()
        assert result.stats["documented_commands"] >= 3

    def test_known_commands_coverage(self):
        """Test that KNOWN_COMMANDS has reasonable coverage."""
        # This test ensures we have a baseline of known commands
        assert "start" in DocsValidator.KNOWN_COMMANDS
        assert "go" in DocsValidator.KNOWN_COMMANDS
        assert "orient" in DocsValidator.KNOWN_COMMANDS
        assert "retrieval blueprint" in DocsValidator.KNOWN_COMMANDS
        assert "memory learn" in DocsValidator.KNOWN_COMMANDS
        assert "metrics report" in DocsValidator.KNOWN_COMMANDS
        assert "validate-docs" in DocsValidator.KNOWN_COMMANDS


class TestValidateDocsCLI:
    """Tests for validate-docs CLI command."""

    def test_json_output(self):
        """Test JSON output format."""
        result = runner.invoke(app, ["validate-docs", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "valid" in data
        assert "issues" in data
        assert "stats" in data

    def test_human_output(self):
        """Test human-readable output."""
        result = runner.invoke(app, ["--human", "validate-docs"])
        assert result.exit_code == 0
        assert "Stats:" in result.output or "passed" in result.output.lower()

    def test_strict_mode(self, tmp_path):
        """Test strict mode treats warnings as errors."""
        # Create a file that would generate a warning
        cerberus_md = tmp_path / "CERBERUS.md"
        cerberus_md.write_text("""# Test doc without version
Some content here.
""")
        result = runner.invoke(
            app,
            ["validate-docs", "--path", str(cerberus_md), "--strict", "--json"],
        )
        # In strict mode, the missing version warning becomes an error
        data = json.loads(result.output)
        assert data["valid"] is False or len(data["issues"]) > 0

    def test_custom_path(self, tmp_path):
        """Test validation with custom path."""
        cerberus_md = tmp_path / "CERBERUS.md"
        cerberus_md.write_text("""# CERBERUS v0.19.4
Test content.
""")
        result = runner.invoke(
            app,
            ["validate-docs", "--path", str(cerberus_md), "--json"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is True

    def test_nonexistent_path(self):
        """Test validation with nonexistent path."""
        result = runner.invoke(
            app,
            ["validate-docs", "--path", "/nonexistent/path/CERBERUS.md", "--json"],
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["valid"] is False
        assert any(i["category"] == "file" for i in data["issues"])


class TestVersionValidation:
    """Tests for version validation."""

    def test_missing_version(self, tmp_path):
        """Test detection of missing version."""
        cerberus_md = tmp_path / "CERBERUS.md"
        cerberus_md.write_text("""# Just a title
No version here.
""")
        validator = DocsValidator(cerberus_md)
        result = validator.validate()
        # Should have a warning about missing version
        version_issues = [i for i in result.issues if i.category == "version"]
        assert len(version_issues) >= 1

    def test_version_present(self, tmp_path):
        """Test that version is detected when present."""
        cerberus_md = tmp_path / "CERBERUS.md"
        cerberus_md.write_text("""# CERBERUS v0.19.4 | UACP/1.2
Content here.
""")
        validator = DocsValidator(cerberus_md)
        result = validator.validate()
        # Should not have version-related errors
        version_errors = [
            i for i in result.issues
            if i.category == "version" and i.severity == "error"
        ]
        assert len(version_errors) == 0


class TestExampleValidation:
    """Tests for code example validation."""

    def test_counts_code_blocks(self, tmp_path):
        """Test that code blocks are counted."""
        cerberus_md = tmp_path / "CERBERUS.md"
        cerberus_md.write_text("""# CERBERUS v0.19.4

```python
print("hello")
```

```bash
cerberus start
```

```json
{"key": "value"}
```
""")
        validator = DocsValidator(cerberus_md)
        result = validator.validate()
        assert result.stats["code_blocks"] == 3

    def test_no_code_blocks(self, tmp_path):
        """Test handling of no code blocks."""
        cerberus_md = tmp_path / "CERBERUS.md"
        cerberus_md.write_text("""# CERBERUS v0.19.4

Just text, no code.
""")
        validator = DocsValidator(cerberus_md)
        result = validator.validate()
        assert result.stats["code_blocks"] == 0
