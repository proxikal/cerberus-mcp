import json
import os
from pathlib import Path

import pytest

from .conftest import unwrap_result

pytestmark = pytest.mark.fast


@pytest.mark.asyncio
async def test_blueprint_compact_format(indexed_project, mcp_client, tmp_path):
    project_root, _ = indexed_project
    os.chdir(project_root)
    sample = project_root / "sample.py"
    sample.write_text(
        "class A:\n    def foo(self):\n        return 1\n\ndef bar():\n    return 2\n"
    )
    # Rebuild index with new file
    await mcp_client.call_tool("index_build", {"path": str(project_root)})

    result = unwrap_result(
        await mcp_client.call_tool(
            "blueprint",
            {
                "path": str(sample),
                "format": "json-compact",
            },
        )
    )

    parsed = result if isinstance(result, dict) else json.loads(result)
    assert parsed["file"].endswith("sample.py")
    assert any(sym["name"] == "A" for sym in parsed["symbols"])
    assert any(sym["name"] == "bar" for sym in parsed["symbols"])


@pytest.mark.asyncio
async def test_blueprint_directory_tree(indexed_project, mcp_client):
    project_root, _ = indexed_project
    os.chdir(project_root)
    pkg = project_root / "pkg"
    pkg.mkdir(exist_ok=True)
    (pkg / "one.py").write_text("def f():\n    return 1\n")
    (pkg / "two.py").write_text("def g():\n    return 2\n")
    await mcp_client.call_tool("index_build", {"path": str(project_root)})

    result = unwrap_result(
        await mcp_client.call_tool(
            "blueprint",
            {
                "path": str(pkg),
                "format": "tree",
            },
        )
    )

    # Should mention package and files
    assert "Package" in result or "pkg" in result
    assert "one.py" in result
    assert "two.py" in result
