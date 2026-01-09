import json
from pathlib import Path

from typer.testing import CliRunner

from cerberus.main import app

runner = CliRunner()
TEST_FILES_DIR = Path(__file__).parent / "test_files"


def test_bench_json(tmp_path):
    index_path = tmp_path / "bench_index.json"
    result = runner.invoke(
        app,
        ["bench", str(TEST_FILES_DIR), "--output", str(index_path), "--query", "greeting", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["files_indexed"] == 8  # Updated for Phase 5
    assert payload["symbols_indexed"] >= 13
    assert payload["total_duration"] >= payload["index_duration"]
