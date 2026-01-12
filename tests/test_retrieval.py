"""Unit tests for retrieval operations."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

pytestmark = pytest.mark.fast

from cerberus.index import build_index, load_index
from cerberus.main import app
from cerberus.retrieval import find_symbol, read_range
from cerberus.schemas import CodeSymbol


TEST_FILES_DIR = Path(__file__).parent / "test_files"
runner = CliRunner()


def test_find_symbol_returns_all_matches(tmp_path):
    """
    Ensures find_symbol returns every matching entry (supports disambiguation).
    """
    index_path = tmp_path / "index.json"
    scan_result = build_index(TEST_FILES_DIR, index_path, respect_gitignore=False)

    duplicate = scan_result.symbols[0].model_copy(deep=True)
    scan_result.symbols.append(duplicate)

    matches = find_symbol(duplicate.name, scan_result)
    assert len(matches) >= 2


def test_read_range_respects_padding_bounds():
    """
    Ensures read_range applies padding without exceeding file boundaries.
    """
    sample_py = TEST_FILES_DIR / "sample.py"
    snippet = read_range(sample_py, start_line=5, end_line=5, padding=1)

    assert snippet.start_line == 4
    assert snippet.end_line == 6
    assert "class MyClass" in snippet.content


def test_read_range_skeleton_mode():
    """
    Skeleton mode should return only signatures/docstrings.
    """
    sample_py = TEST_FILES_DIR / "sample.py"
    snippet = read_range(sample_py, start_line=1, end_line=50, skeleton=True)

    assert "def top_level_function" in snippet.content
    assert "return math.sqrt" not in snippet.content


def test_skeleton_file_cli(tmp_path):
    """
    skeleton-file command should emit skeleton content.
    """
    result = runner.invoke(app, ["retrieval", "skeleton-file", str(TEST_FILES_DIR / "sample.py"), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "Skeleton" not in payload["content"]  # sanity
    assert "def top_level_function" in payload["content"]


def test_get_symbol_cli(tmp_path):
    """
    CLI should return the symbol table and context for a known symbol.
    """
    index_path = tmp_path / "cli_index.json"
    build_index(TEST_FILES_DIR, index_path, respect_gitignore=False)

    result = runner.invoke(
        app,
        ["retrieval", "get-symbol", "MyClass", "--index", str(index_path), "--padding", "0"],
    )

    assert result.exit_code == 0
    assert "MyClass" in result.stdout
    assert "class MyClass" in result.stdout
