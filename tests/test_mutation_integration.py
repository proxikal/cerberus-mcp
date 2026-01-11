"""
Integration tests for Phase 11: MutationFacade end-to-end testing.

Tests the complete edit/delete pipeline with real files.
"""

import pytest
import tempfile
import os
from pathlib import Path

pytestmark = [pytest.mark.integration, pytest.mark.mutation]
from cerberus.mutation import MutationFacade
from cerberus.storage.sqlite_store import SQLiteIndexStore
from cerberus.index import build_index


class TestMutationFacadeIntegration:
    """Integration tests for MutationFacade."""

    def test_edit_symbol_complete_pipeline(self):
        """Test complete edit pipeline: locate → edit → validate → save."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "sample.py"
            original_code = """def old_implementation():
    return "old"

def keep_this():
    pass
"""
            test_file.write_text(original_code)

            # Build index
            index_path = Path(tmpdir) / "test.db"
            scan_result = build_index(Path(tmpdir), str(index_path))

            # Load store
            store = SQLiteIndexStore(str(index_path))

            # Create facade
            facade = MutationFacade(store, config={"backup_enabled": True, "backup_dir": tmpdir})

            # Edit the symbol
            new_code = """def old_implementation():
    return "new"
"""
            result = facade.edit_symbol(
                file_path=str(test_file),
                symbol_name="old_implementation",
                new_code=new_code,
                dry_run=False
            )

            # Verify result
            assert result.success, f"Edit failed: {result.errors}"
            assert result.operation == "edit"
            assert result.symbol_name == "old_implementation"
            assert result.validation_passed
            assert result.backup_path is not None

            # Verify file was modified
            modified_content = test_file.read_text()
            assert "new" in modified_content
            assert "keep_this" in modified_content  # Other function preserved

            # Verify backup exists
            assert Path(result.backup_path).exists()

    def test_delete_symbol_complete_pipeline(self):
        """Test complete delete pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "sample.py"
            original_code = """def to_delete():
    return "delete me"

def keep_this():
    return "keep"
"""
            test_file.write_text(original_code)

            # Build index
            index_path = Path(tmpdir) / "test.db"
            scan_result = build_index(Path(tmpdir), str(index_path))

            # Load store
            store = SQLiteIndexStore(str(index_path))

            # Create facade
            facade = MutationFacade(store, config={"backup_enabled": True, "backup_dir": tmpdir})

            # Delete the symbol
            result = facade.delete_symbol(
                file_path=str(test_file),
                symbol_name="to_delete",
                dry_run=False
            )

            # Verify result
            assert result.success, f"Delete failed: {result.errors}"
            assert result.operation == "delete"
            assert result.validation_passed

            # Verify file was modified
            modified_content = test_file.read_text()
            assert "to_delete" not in modified_content
            assert "keep_this" in modified_content  # Other function preserved

    def test_dry_run_mode(self):
        """Test dry-run mode doesn't modify files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "sample.py"
            original_code = """def foo():
    return 1
"""
            test_file.write_text(original_code)

            # Build index
            index_path = Path(tmpdir) / "test.db"
            scan_result = build_index(Path(tmpdir), str(index_path))

            # Load store
            store = SQLiteIndexStore(str(index_path))

            # Create facade
            facade = MutationFacade(store)

            # Edit with dry_run=True
            result = facade.edit_symbol(
                file_path=str(test_file),
                symbol_name="foo",
                new_code="def foo():\n    return 2\n",
                dry_run=True
            )

            # File should not be modified in dry run
            assert test_file.read_text() == original_code

    def test_edit_preserves_other_code(self):
        """Test that editing one symbol doesn't affect others."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file with multiple functions
            test_file = Path(tmpdir) / "multi.py"
            original_code = """def first():
    return 1

def second():
    return 2

def third():
    return 3
"""
            test_file.write_text(original_code)

            # Build index
            index_path = Path(tmpdir) / "test.db"
            scan_result = build_index(Path(tmpdir), str(index_path))

            # Load store
            store = SQLiteIndexStore(str(index_path))

            # Create facade
            facade = MutationFacade(store, config={"backup_enabled": False})

            # Edit only second function
            result = facade.edit_symbol(
                file_path=str(test_file),
                symbol_name="second",
                new_code="def second():\n    return 222\n",
                dry_run=False
            )

            assert result.success

            # Verify other functions unchanged
            modified_content = test_file.read_text()
            assert "def first():" in modified_content
            assert "return 1" in modified_content
            assert "def third():" in modified_content
            assert "return 3" in modified_content
            # And second was changed
            assert "return 222" in modified_content

    def test_write_efficiency_metrics(self):
        """Test that write efficiency metrics are calculated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "sample.py"
            # Create a file with 20 lines
            lines = [f"# Line {i}" for i in range(1, 16)]
            lines.insert(5, "def target():")
            lines.insert(6, "    return 1")
            original_code = "\n".join(lines)
            test_file.write_text(original_code)

            # Build index
            index_path = Path(tmpdir) / "test.db"
            scan_result = build_index(Path(tmpdir), str(index_path))

            # Load store
            store = SQLiteIndexStore(str(index_path))

            # Create facade
            facade = MutationFacade(store, config={"backup_enabled": False})

            # Edit small symbol in large file
            result = facade.edit_symbol(
                file_path=str(test_file),
                symbol_name="target",
                new_code="def target():\n    return 2\n",
                dry_run=False
            )

            assert result.success
            # Verify efficiency metrics
            assert result.lines_total > 0
            assert result.lines_changed > 0
            assert result.lines_changed < result.lines_total
            assert result.write_efficiency < 1.0
            assert result.tokens_saved > 0

    def test_symbol_not_found(self):
        """Test error handling when symbol doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test file
            test_file = Path(tmpdir) / "sample.py"
            test_file.write_text("def existing(): pass\n")

            # Build index
            index_path = Path(tmpdir) / "test.db"
            scan_result = build_index(Path(tmpdir), str(index_path))

            # Load store
            store = SQLiteIndexStore(str(index_path))

            # Create facade
            facade = MutationFacade(store)

            # Try to edit non-existent symbol
            result = facade.edit_symbol(
                file_path=str(test_file),
                symbol_name="nonexistent",
                new_code="def nonexistent(): pass\n"
            )

            assert not result.success
            assert len(result.errors) > 0
            assert "not found" in result.errors[0].lower()
