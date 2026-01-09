import json
from pathlib import Path

from typer.testing import CliRunner

from cerberus.main import app

runner = CliRunner()
TEST_FILES_DIR = Path(__file__).parent / "test_files"


def test_scan_json_output():
    result = runner.invoke(app, ["scan", str(TEST_FILES_DIR), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["total_files"] == 8  # Updated for Phase 5
    assert payload["files"]
    assert payload["symbols"]


def test_index_and_stats_json(tmp_path):
    index_path = tmp_path / "cli_index.json"
    index_res = runner.invoke(
        app,
        ["index", str(TEST_FILES_DIR), "--output", str(index_path), "--json"],
    )
    assert index_res.exit_code == 0
    index_payload = json.loads(index_res.stdout)
    assert index_payload["index_path"] == str(index_path)
    assert index_path.exists()

    stats_res = runner.invoke(
        app,
        ["stats", "--index", str(index_path), "--json"],
    )
    assert stats_res.exit_code == 0
    stats_payload = json.loads(stats_res.stdout)
    assert stats_payload["total_files"] == 8  # Updated for Phase 5
    assert stats_payload["total_symbols"] >= 13  # At least 13 symbols
    assert "imports" in stats_payload
    assert "calls" in stats_payload


def test_get_symbol_json(tmp_path):
    index_path = tmp_path / "cli_index.json"
    runner.invoke(app, ["index", str(TEST_FILES_DIR), "--output", str(index_path), "--json"])

    result = runner.invoke(
        app,
        ["get-symbol", "MyClass", "--index", str(index_path), "--padding", "0", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert any(item["symbol"]["name"] == "MyClass" for item in payload)
    assert all("snippet" in item for item in payload)


def test_deps_cli(tmp_path):
    """
    deps should surface callers/imports.
    """
    index_path = tmp_path / "cli_index.json"
    runner.invoke(app, ["index", str(TEST_FILES_DIR), "--output", str(index_path), "--json"])

    result = runner.invoke(
        app,
        ["deps", "--symbol", "top_level_function", "--index", str(index_path), "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["callers"]

    result_imports = runner.invoke(
        app,
        ["deps", "--file", "sample.py", "--index", str(index_path), "--json"],
    )
    assert result_imports.exit_code == 0
    imports_payload = json.loads(result_imports.stdout)
    assert imports_payload["imports"]


def test_search_json(tmp_path):
    index_path = tmp_path / "cli_index.json"
    runner.invoke(app, ["index", str(TEST_FILES_DIR), "--output", str(index_path), "--json"])

    result = runner.invoke(
        app,
        ["search", "greeting", "--index", str(index_path), "--limit", "2", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) <= 2
    assert all("score" in item for item in payload)


def test_incremental_index(tmp_path, monkeypatch):
    """
    Incremental flag should reuse unchanged files and still include new symbols.
    """
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    # Copy test files to a writable location
    for path in TEST_FILES_DIR.iterdir():
        target = workdir / path.name
        target.write_text(path.read_text())

    index_path = tmp_path / "cli_index.json"
    first = runner.invoke(app, ["index", str(workdir), "--output", str(index_path), "--json"])
    assert first.exit_code == 0

    # Modify sample.py to add a new function
    sample_py = workdir / "sample.py"
    sample_py.write_text(sample_py.read_text() + "\n\ndef added_func():\n    return 42\n")

    second = runner.invoke(
        app,
        ["index", str(workdir), "--output", str(index_path), "--json", "--incremental"],
    )
    assert second.exit_code == 0
    payload = json.loads(second.stdout)
    assert payload["total_files"] == 8  # Updated for Phase 5

    stats_res = runner.invoke(app, ["stats", "--index", str(index_path), "--json"])
    stats_payload = json.loads(stats_res.stdout)
    assert stats_payload["total_symbols"] >= 14  # at least 14 symbols after addition
