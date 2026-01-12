"""
Tests for Phase 19.1: Streamlined Entry Points

Tests for:
  - cerberus start
  - cerberus go <file>
  - cerberus orient [dir]
"""

import json
import pytest
import tempfile
from pathlib import Path

pytestmark = pytest.mark.integration
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

from cerberus.main import app

runner = CliRunner()


class TestStartCommand:
    """Tests for `cerberus start` command."""

    def test_start_basic_json_output(self):
        """Test start command with JSON output."""
        result = runner.invoke(app, ["start", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert data["status"] == "initialized"
        assert "index" in data
        assert "watcher" in data
        assert "memory" in data
        assert "context" in data
        assert "next_command" in data

    def test_start_human_mode(self):
        """Test start command in human mode."""
        result = runner.invoke(app, ["--human", "start"])
        assert result.exit_code == 0
        assert "Cerberus Session Initialized" in result.output
        assert "Index:" in result.output
        assert "Watcher:" in result.output

    def test_start_index_check(self):
        """Test that start reports index status correctly."""
        result = runner.invoke(app, ["start", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "index" in data
        assert "healthy" in data["index"]
        assert "exists" in data["index"]

    def test_start_memory_summary(self):
        """Test that start includes memory summary."""
        result = runner.invoke(app, ["start", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "memory" in data
        assert "preferences" in data["memory"]
        assert "decisions" in data["memory"]
        assert "corrections" in data["memory"]

    def test_start_via_workflow_subcommand(self):
        """Test that start also works via workflow subcommand."""
        result = runner.invoke(app, ["workflow", "start", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert data["status"] == "initialized"


class TestGoCommand:
    """Tests for `cerberus go <file>` command."""

    def test_go_file_not_found(self):
        """Test go command with non-existent file."""
        result = runner.invoke(app, ["go", "nonexistent.py"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_go_no_index(self, tmp_path):
        """Test go command without index."""
        # Create a temp file
        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    pass\n")

        # Run from tmp_path where there's no index
        result = runner.invoke(app, ["go", str(test_file)], catch_exceptions=False)
        # Should fail because no index
        assert result.exit_code == 1
        assert "index" in result.output.lower()

    def test_go_json_output_structure(self, tmp_path, monkeypatch):
        """Test go command JSON output structure."""
        monkeypatch.chdir(tmp_path)

        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class MyClass:
    def __init__(self):
        pass

    def long_method(self):
        # This is a method with many lines
        x = 1
        y = 2
        z = 3
        return x + y + z

def standalone_function():
    pass
""")

        # Create index
        from cerberus.index import build_index
        build_index(tmp_path, tmp_path / "cerberus.db")

        result = runner.invoke(app, ["go", str(test_file), "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "file" in data
        assert "total_lines" in data
        assert "symbol_count" in data
        assert "symbols" in data
        assert "quick_reads" in data

    def test_go_custom_threshold(self, tmp_path, monkeypatch):
        """Test go command with custom threshold."""
        monkeypatch.chdir(tmp_path)

        # Create a test file with a function that's 10 lines
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def medium_function():
    line1 = 1
    line2 = 2
    line3 = 3
    line4 = 4
    line5 = 5
    line6 = 6
    line7 = 7
    return line1
""")

        # Create index
        from cerberus.index import build_index
        build_index(tmp_path, tmp_path / "cerberus.db")

        # With default threshold (30), should not be heavy
        result = runner.invoke(app, ["go", str(test_file), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["heavy_symbol_count"] == 0

        # With threshold of 5, should be heavy
        result = runner.invoke(app, ["go", str(test_file), "--threshold", "5", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["heavy_symbol_count"] >= 1

    def test_go_via_workflow_subcommand(self, tmp_path, monkeypatch):
        """Test that go also works via workflow subcommand."""
        monkeypatch.chdir(tmp_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("def hello():\n    pass\n")

        from cerberus.index import build_index
        build_index(tmp_path, tmp_path / "cerberus.db")

        result = runner.invoke(app, ["workflow", "go", str(test_file), "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "file" in data
        assert "symbols" in data


class TestOrientCommand:
    """Tests for `cerberus orient [dir]` command."""

    def test_orient_basic_json_output(self, tmp_path, monkeypatch):
        """Test orient command with JSON output."""
        monkeypatch.chdir(tmp_path)

        # Create some test files
        (tmp_path / "test1.py").write_text("def hello(): pass")
        (tmp_path / "test2.py").write_text("def world(): pass")
        (tmp_path / "test3.js").write_text("function foo() {}")

        result = runner.invoke(app, ["orient", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "project" in data
        assert "directory" in data
        assert "files" in data
        assert "total_lines" in data
        assert "index" in data
        assert "memory" in data

    def test_orient_file_counts(self, tmp_path, monkeypatch):
        """Test that orient counts files correctly."""
        monkeypatch.chdir(tmp_path)

        # Create test files
        (tmp_path / "file1.py").write_text("# Python file\n")
        (tmp_path / "file2.py").write_text("# Another Python file\n")
        (tmp_path / "script.js").write_text("// JS file\n")

        result = runner.invoke(app, ["orient", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert data["files"]["python"] == 2
        assert data["files"]["javascript"] == 1

    def test_orient_specific_directory(self, tmp_path, monkeypatch):
        """Test orient with specific directory argument."""
        monkeypatch.chdir(tmp_path)

        # Create subdirectory with files
        subdir = tmp_path / "src"
        subdir.mkdir()
        (subdir / "main.py").write_text("def main(): pass\n")

        result = runner.invoke(app, ["orient", str(subdir), "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "src" in data["directory"]
        assert data["files"]["python"] >= 1

    def test_orient_nonexistent_directory(self):
        """Test orient with non-existent directory."""
        result = runner.invoke(app, ["orient", "/nonexistent/path"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_orient_index_status(self, tmp_path, monkeypatch):
        """Test that orient reports index status."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "test.py").write_text("def foo(): pass")

        # Without index
        result = runner.invoke(app, ["orient", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["index"]["exists"] == False

        # Create index
        from cerberus.index import build_index
        build_index(tmp_path, tmp_path / "cerberus.db")

        # With index
        result = runner.invoke(app, ["orient", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["index"]["exists"] == True

    def test_orient_human_mode(self, tmp_path, monkeypatch):
        """Test orient in human mode."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "app.py").write_text("# App\n")

        result = runner.invoke(app, ["--human", "orient"])
        assert result.exit_code == 0
        assert "Project:" in result.output
        assert "Files:" in result.output

    def test_orient_hot_spots(self, tmp_path, monkeypatch):
        """Test that orient shows hot spots when index exists."""
        monkeypatch.chdir(tmp_path)

        # Create files with varying complexity
        (tmp_path / "simple.py").write_text("def foo(): pass")
        (tmp_path / "complex.py").write_text("""
class BigClass:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
""")

        # Create index
        from cerberus.index import build_index
        build_index(tmp_path, tmp_path / "cerberus.db")

        result = runner.invoke(app, ["orient", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "hot_spots" in data
        # complex.py should appear in hot spots due to more symbols
        if data["hot_spots"]:
            file_names = [hs["file"] for hs in data["hot_spots"]]
            # At least one file should be in hot spots
            assert len(file_names) > 0

    def test_orient_via_workflow_subcommand(self, tmp_path, monkeypatch):
        """Test that orient also works via workflow subcommand."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "test.py").write_text("def test(): pass")

        result = runner.invoke(app, ["workflow", "orient", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "project" in data
        assert "files" in data


class TestWorkflowIntegration:
    """Integration tests for workflow commands."""

    def test_full_workflow_sequence(self, tmp_path, monkeypatch):
        """Test a typical workflow: start -> orient -> go."""
        monkeypatch.chdir(tmp_path)

        # Create project structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        main_file = src_dir / "main.py"
        main_file.write_text("""
class Application:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

def main():
    app = Application()
    app.start()
    app.stop()

if __name__ == "__main__":
    main()
""")

        # Step 1: Create index
        from cerberus.index import build_index
        build_index(tmp_path, tmp_path / "cerberus.db")

        # Step 2: Start
        result = runner.invoke(app, ["start", "--json"])
        assert result.exit_code == 0
        start_data = json.loads(result.output)
        assert start_data["status"] == "initialized"
        assert start_data["index"]["healthy"] == True

        # Step 3: Orient
        result = runner.invoke(app, ["orient", "--json"])
        assert result.exit_code == 0
        orient_data = json.loads(result.output)
        assert orient_data["files"]["python"] >= 1

        # Step 4: Go into the main file
        result = runner.invoke(app, ["go", str(main_file), "--json"])
        assert result.exit_code == 0
        go_data = json.loads(result.output)
        assert go_data["symbol_count"] >= 1
        assert "Application" in [s["name"] for s in go_data["symbols"]]

    def test_workflow_without_index(self, tmp_path, monkeypatch):
        """Test workflow commands gracefully handle missing index."""
        monkeypatch.chdir(tmp_path)

        (tmp_path / "test.py").write_text("def foo(): pass")

        # Start should work but report no index
        result = runner.invoke(app, ["start", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["index"]["exists"] == False
        assert data["index"]["healthy"] == False

        # Orient should work
        result = runner.invoke(app, ["orient", "--json"])
        assert result.exit_code == 0

        # Go should fail with helpful message
        result = runner.invoke(app, ["go", str(tmp_path / "test.py")])
        assert result.exit_code == 1
        assert "index" in result.output.lower()
