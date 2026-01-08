import json
from pathlib import Path

from typer.testing import CliRunner

from cerberus.main import app

runner = CliRunner()


def test_doctor_json():
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert any(item["name"] == "embeddings" for item in payload)


def test_generate_tools(tmp_path):
    output = tmp_path / "tools.json"
    result = runner.invoke(app, ["generate-tools", "--output", str(output)])
    assert result.exit_code == 0
    assert output.exists()
    manifest = json.loads(output.read_text())
    assert "tools" in manifest
    assert any(tool["name"] == "FindSymbol" for tool in manifest["tools"])
