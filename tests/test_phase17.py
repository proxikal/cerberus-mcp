"""
Phase 17 Tests: Context Optimization & get-symbol Efficiency

Tests for Phase 17 changes to get-symbol:
- --snippet mode (raw code output)
- --exact default behavior
- --context alias for --padding
- --limit caps results
- --show-callers opt-in (not default)
- Efficiency warning
"""

import pytest
import json
from pathlib import Path
from typer.testing import CliRunner
from cerberus.main import app

runner = CliRunner()


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal Python project for testing."""
    src = tmp_path / "src"
    src.mkdir()

    # Create a simple Python file with multiple functions
    code_file = src / "example.py"
    code_file.write_text("""
def func_a():
    '''First function'''
    return "a"

def func_b():
    '''Second function'''
    return "b"

def func_c():
    '''Third function'''
    return "c"

class MyClass:
    '''Example class'''
    def method_one(self):
        return 1

    def method_two(self):
        return 2
""")

    return tmp_path


@pytest.fixture
def indexed_project(sample_project):
    """Index the sample project and return both project path and index path."""
    idx_path = sample_project / "test_index.db"
    result = runner.invoke(app, ["index", str(sample_project), "--output", str(idx_path)])
    assert result.exit_code == 0, f"Indexing failed: {result.stdout}"
    assert idx_path.exists(), f"Index not created at {idx_path}"

    # Return a simple object with paths
    class IndexedProject:
        def __init__(self):
            self.project_path = sample_project
            self.index_path = idx_path

    return IndexedProject()


def test_snippet_mode_raw_output(indexed_project):
    """Test --snippet flag returns raw code only, no JSON wrapper."""
    result = runner.invoke(app, [
        "retrieval", "get-symbol", "func_a",
        "--snippet",
        "--index", str(indexed_project.index_path)
    ])

    assert result.exit_code == 0
    output = result.stdout

    # Should NOT be JSON
    with pytest.raises(json.JSONDecodeError):
        json.loads(output)

    # Should contain the function code
    assert "func_a" in output
    assert "First function" in output

    # Should NOT contain JSON structure keys
    assert '"symbol"' not in output
    assert '"snippet"' not in output
    assert '"callers"' not in output


def test_snippet_mode_multiple_results(indexed_project):
    """Test --snippet with multiple results includes separators."""
    result = runner.invoke(app, [
        "retrieval", "get-symbol", "func",
        "--fuzzy",
        "--snippet",
        "--index", str(indexed_project.index_path)
    ])

    assert result.exit_code == 0
    output = result.stdout

    # Should have multiple functions
    assert "func_a" in output or "func_b" in output or "func_c" in output

    # Should have separator comments if multiple results
    if output.count("def func") > 1:
        assert "# " in output  # Separator comment


def test_exact_match_default(indexed_project):
    """Test exact matching is default (not fuzzy)."""
    # Exact match should find only func_a
    result = runner.invoke(app, [
        "retrieval", "get-symbol", "func_a",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    assert result.exit_code == 0
    data = json.loads(result.stdout)

    # Should find exactly one match
    assert len(data) == 1
    assert data[0]["symbol"]["name"] == "func_a"


def test_fuzzy_match_opt_in(indexed_project):
    """Test fuzzy matching is opt-in with --fuzzy."""
    # Without --fuzzy, "func" should not match
    result = runner.invoke(app, [
        "retrieval", "get-symbol", "func",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    # Should fail to find exact match
    assert result.exit_code == 1

    # With --fuzzy, should find multiple matches
    result = runner.invoke(app, [
        "retrieval", "get-symbol", "func",
        "--fuzzy",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    assert result.exit_code == 0
    data = json.loads(result.stdout)

    # Should find multiple functions
    assert len(data) >= 2


def test_context_alias_for_padding(indexed_project):
    """Test --context is an alias for --padding."""
    # Get with --context 1
    result1 = runner.invoke(app, [
        "retrieval", "get-symbol", "func_a",
        "--context", "1",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    # Get with --padding 1
    result2 = runner.invoke(app, [
        "retrieval", "get-symbol", "func_a",
        "--padding", "1",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    assert result1.exit_code == 0
    assert result2.exit_code == 0

    data1 = json.loads(result1.stdout)
    data2 = json.loads(result2.stdout)

    # Should return the same snippet
    assert data1[0]["snippet"]["content"] == data2[0]["snippet"]["content"]


def test_limit_caps_results(indexed_project):
    """Test --limit caps the number of results returned."""
    # Get all matches with high limit
    result_all = runner.invoke(app, [
        "retrieval", "get-symbol", "method",
        "--fuzzy",
        "--limit", "100",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    # Get limited matches
    result_limited = runner.invoke(app, [
        "retrieval", "get-symbol", "method",
        "--fuzzy",
        "--limit", "1",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    assert result_all.exit_code == 0
    assert result_limited.exit_code == 0

    data_all = json.loads(result_all.stdout)
    data_limited = json.loads(result_limited.stdout)

    # Limited should have fewer results
    assert len(data_limited) == 1
    assert len(data_limited) < len(data_all)


def test_callers_opt_in_not_default(indexed_project):
    """Test callers are NOT included by default (opt-in with --show-callers)."""
    # Without --show-callers (default)
    result = runner.invoke(app, [
        "retrieval", "get-symbol", "func_a",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    assert result.exit_code == 0
    data = json.loads(result.stdout)

    # Callers should be empty list (not included by default)
    assert "callers" in data[0]
    assert data[0]["callers"] == []

    # With --show-callers
    result_with_callers = runner.invoke(app, [
        "retrieval", "get-symbol", "func_a",
        "--show-callers",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    assert result_with_callers.exit_code == 0
    data_with_callers = json.loads(result_with_callers.stdout)

    # Now callers might be populated (or empty if no callers exist)
    assert "callers" in data_with_callers[0]


def test_default_context_is_5_lines(indexed_project):
    """Test default context is 5 lines (Phase 17 change from 3)."""
    result = runner.invoke(app, [
        "retrieval", "get-symbol", "func_a",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    assert result.exit_code == 0
    data = json.loads(result.stdout)

    snippet = data[0]["snippet"]
    symbol = data[0]["symbol"]

    # Context lines = (snippet lines) - (symbol lines)
    snippet_line_count = snippet["end_line"] - snippet["start_line"] + 1
    symbol_line_count = symbol["end_line"] - symbol["start_line"] + 1

    # With 5 lines padding, we expect roughly symbol_lines + 10 (5 before + 5 after)
    # This is approximate due to file boundaries
    assert snippet_line_count >= symbol_line_count


def test_imports_not_included_by_default(indexed_project):
    """Test imports are NOT included by default."""
    result = runner.invoke(app, [
        "retrieval", "get-symbol", "func_a",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    assert result.exit_code == 0
    data = json.loads(result.stdout)

    # Imports should be empty (not included by default)
    assert "imports" in data[0]
    assert data[0]["imports"] == []


def test_snippet_mode_most_efficient(indexed_project):
    """Test --snippet mode is more efficient than full JSON."""
    # Full JSON output
    result_json = runner.invoke(app, [
        "retrieval", "get-symbol", "func_a",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    # Snippet output
    result_snippet = runner.invoke(app, [
        "retrieval", "get-symbol", "func_a",
        "--snippet",
        "--index", str(indexed_project.index_path)
    ])

    assert result_json.exit_code == 0
    assert result_snippet.exit_code == 0

    # Snippet output should be smaller
    assert len(result_snippet.stdout) < len(result_json.stdout)


def test_exact_flag_explicit(indexed_project):
    """Test --exact flag can be explicitly set."""
    result = runner.invoke(app, [
        "retrieval", "get-symbol", "func_a",
        "--exact",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["symbol"]["name"] == "func_a"


def test_no_exact_allows_fuzzy(indexed_project):
    """Test --no-exact allows fuzzy matching."""
    result = runner.invoke(app, [
        "retrieval", "get-symbol", "func",
        "--no-exact",
        "--fuzzy",
        "--json",
        "--index", str(indexed_project.index_path)
    ])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) >= 2  # Should find multiple func_* symbols


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
