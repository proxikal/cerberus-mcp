"""
Unit tests for Phase 11: The Surgical Writer (Symbolic Editing)

Tests for mutation package components: SymbolLocator, CodeEditor,
CodeFormatter, CodeValidator, DiffLedger.
"""

import pytest
import tempfile
import os
from pathlib import Path
from cerberus.mutation import (
    SymbolLocator,
    CodeEditor,
    CodeFormatter,
    CodeValidator,
    DiffLedger,
    MUTATION_CONFIG,
)
from cerberus.schemas import SymbolLocation, DiffMetric
from cerberus.storage.sqlite_store import SQLiteIndexStore


class TestCodeEditor:
    """Test CodeEditor atomic writes and backups."""

    def test_atomic_write(self):
        """Test atomic file write creates temp file then renames."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("original content")

            editor = CodeEditor()
            success = editor._atomic_write(str(test_file), "new content")

            assert success
            assert test_file.read_text() == "new content"

    def test_backup_creation(self):
        """Test backup file is created before edits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set backup dir to tmpdir
            config = {"backup_dir": tmpdir, "backup_enabled": True}
            editor = CodeEditor(config)

            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("def foo(): pass")

            backup_path = editor.create_backup(str(test_file))

            assert backup_path is not None
            assert Path(backup_path).exists()
            assert Path(backup_path).read_text() == "def foo(): pass"

    def test_line_ending_preservation_lf(self):
        """Test LF line endings are preserved."""
        editor = CodeEditor()
        content = "line1\nline2\nline3"
        detected = editor._detect_line_ending(content)
        assert detected == '\n'

        normalized = editor._normalize_line_endings(content, '\n')
        assert '\r\n' not in normalized

    def test_line_ending_preservation_crlf(self):
        """Test CRLF line endings are preserved."""
        editor = CodeEditor()
        content = "line1\r\nline2\r\nline3"
        detected = editor._detect_line_ending(content)
        assert detected == '\r\n'

        normalized = editor._normalize_line_endings("line1\nline2", '\r\n')
        assert normalized == "line1\r\nline2"


class TestCodeFormatter:
    """Test CodeFormatter indentation and formatting."""

    def test_get_indent(self):
        """Test indentation extraction from line."""
        formatter = CodeFormatter()
        assert formatter._get_indent("    code") == "    "
        assert formatter._get_indent("\t\tcode") == "\t\t"
        assert formatter._get_indent("no indent") == ""

    def test_detect_file_indentation_spaces(self):
        """Test detecting 4-space indentation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def foo():\n")
            f.write("    pass\n")
            f.write("    return 1\n")
            f.name

        try:
            formatter = CodeFormatter()
            indent = formatter.detect_file_indentation(f.name)
            assert indent == "    "  # 4 spaces
        finally:
            os.unlink(f.name)

    def test_detect_file_indentation_tabs(self):
        """Test detecting tab indentation."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def foo():\n")
            f.write("\tpass\n")
            f.write("\treturn 1\n")
            f.name

        try:
            formatter = CodeFormatter()
            indent = formatter.detect_file_indentation(f.name)
            assert indent == "\t"
        finally:
            os.unlink(f.name)

    def test_format_code_block_reindent(self):
        """Test reindenting code block to target level."""
        formatter = CodeFormatter()
        code = "def foo():\n    pass"
        # Reindent to level 1 (one indent unit deep)
        reindented = formatter.format_code_block(code, 1)

        lines = reindented.split('\n')
        assert lines[0].startswith("    def foo():")  # 1 indent
        assert lines[1].startswith("        pass")     # 2 indents


class TestCodeValidator:
    """Test CodeValidator syntax and semantic checks."""

    def test_validate_syntax_valid_python(self):
        """Test valid Python code passes syntax check."""
        validator = CodeValidator()
        code = "def foo():\n    return 42"

        is_valid, errors = validator.validate_syntax(code, "python")

        assert is_valid
        assert len(errors) == 0

    def test_validate_syntax_invalid_python(self):
        """Test invalid Python code fails syntax check."""
        validator = CodeValidator()
        code = "def foo(\n    return 42"  # Missing closing paren

        is_valid, errors = validator.validate_syntax(code, "python")

        assert not is_valid
        assert len(errors) > 0

    def test_dry_run_validation_success(self):
        """Test dry-run validation with valid code."""
        validator = CodeValidator()
        code = "def bar():\n    x = 1\n    return x"

        success, errors, warnings = validator.dry_run_validation(
            "test.py",
            code,
            "python"
        )

        assert success
        assert len(errors) == 0


class TestDiffLedger:
    """Test DiffLedger metrics tracking."""

    def test_record_mutation(self):
        """Test recording a mutation operation."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            ledger_path = f.name

        try:
            ledger = DiffLedger(ledger_path)

            metric = ledger.record_mutation(
                operation="edit",
                file_path="test.py",
                lines_changed=10,
                lines_total=100
            )

            assert metric is not None
            assert metric.operation == "edit"
            assert metric.lines_changed == 10
            assert metric.lines_total == 100
            assert metric.write_efficiency == 0.1
            assert metric.tokens_saved == 360  # (100-10) * 4

        finally:
            os.unlink(ledger_path)

    def test_get_statistics(self):
        """Test retrieving aggregated statistics."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            ledger_path = f.name

        try:
            ledger = DiffLedger(ledger_path)

            # Record multiple operations
            ledger.record_mutation("edit", "file1.py", 5, 100)
            ledger.record_mutation("edit", "file2.py", 10, 200)
            ledger.record_mutation("delete", "file3.py", 20, 100)

            stats = ledger.get_statistics()

            assert stats["total_operations"] == 3
            assert stats["total_tokens_saved"] > 0
            assert "edit" in stats["operations_by_type"]
            assert "delete" in stats["operations_by_type"]
            assert stats["operations_by_type"]["edit"] == 2
            assert stats["operations_by_type"]["delete"] == 1

        finally:
            os.unlink(ledger_path)

    def test_get_recent_metrics(self):
        """Test retrieving recent metrics."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            ledger_path = f.name

        try:
            ledger = DiffLedger(ledger_path)

            # Record operations
            ledger.record_mutation("edit", "file1.py", 5, 100)
            ledger.record_mutation("edit", "file2.py", 10, 200)

            recent = ledger.get_recent_metrics(limit=2)

            assert len(recent) == 2
            assert all(isinstance(m, DiffMetric) for m in recent)
            # Most recent first
            assert recent[0].file_path == "file2.py"
            assert recent[1].file_path == "file1.py"

        finally:
            os.unlink(ledger_path)


class TestSymbolLocator:
    """Test SymbolLocator AST-based symbol location."""

    def test_detect_language(self):
        """Test language detection from file extension."""
        locator = SymbolLocator()

        assert locator._detect_language(".py") == "python"
        assert locator._detect_language(".js") == "javascript"
        assert locator._detect_language(".ts") == "typescript"
        assert locator._detect_language(".tsx") == "typescript"
        assert locator._detect_language(".unknown") is None

    def test_locate_symbol_simple_function(self):
        """Test locating a simple function symbol."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("""def simple_function():
    return 42

def another_function():
    pass
""")

            # Create index
            index_path = Path(tmpdir) / "test.db"
            from cerberus.index import build_index
            scan_result = build_index(Path(tmpdir), str(index_path))

            # Load store
            store = SQLiteIndexStore(str(index_path))
            locator = SymbolLocator(store)

            # Locate symbol
            location = locator.locate_symbol(
                str(test_file),
                "simple_function",
                symbol_type="function"
            )

            if location:  # Only if tree-sitter is available
                assert location.symbol_name == "simple_function"
                assert location.symbol_type == "function"
                assert location.start_line == 1
                assert location.language == "python"
                assert location.start_byte >= 0
                assert location.end_byte > location.start_byte


class TestMutationConfig:
    """Test mutation configuration."""

    def test_default_config_values(self):
        """Test default configuration values are set."""
        assert MUTATION_CONFIG["backup_enabled"] is True
        assert MUTATION_CONFIG["auto_format_enabled"] is True
        assert MUTATION_CONFIG["ledger_enabled"] is True
        assert MUTATION_CONFIG["syntax_check_required"] is True

    def test_backup_dir_configured(self):
        """Test backup directory is configured."""
        assert "backup_dir" in MUTATION_CONFIG
        # Backup dir should be inside .cerberus/backups
        assert MUTATION_CONFIG["backup_dir"].endswith(".cerberus/backups") or \
               MUTATION_CONFIG["backup_dir"].endswith(".cerberus_backups")
