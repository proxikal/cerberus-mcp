import json
from pathlib import Path

import pytest

from cerberus.blueprint.schemas import Blueprint, BlueprintNode
from cerberus.blueprint.formatter import BlueprintFormatter
from cerberus.blueprint.tree_builder import TreeBuilder

pytestmark = pytest.mark.fast


def test_json_compact_smaller_than_full():
    """Compact JSON should be significantly smaller than full JSON."""
    nodes = [
        BlueprintNode(
            name="MyClass",
            type="class",
            file_path="/tmp/file.py",
            start_line=1,
            end_line=50,
            signature=None,
            children=[
                BlueprintNode(
                    name="method_a",
                    type="method",
                    file_path="/tmp/file.py",
                    start_line=5,
                    end_line=10,
                    signature="(self)",
                )
            ],
        )
    ]
    bp = Blueprint(file_path="/tmp/file.py", nodes=nodes, total_symbols=2)

    full_json = BlueprintFormatter.format_as_json(bp, pretty=True)
    compact_json = BlueprintFormatter.format_as_json_compact(bp)

    assert len(compact_json) < len(full_json) * 0.7
    assert len(compact_json) > 0
    # Ensure it parses
    parsed = json.loads(compact_json)
    assert parsed["file"] == "/tmp/file.py"
    assert parsed["symbols"][0]["name"] == "MyClass"


def test_aggregated_tree_does_not_crash():
    """Aggregated tree builder should render file nodes and children."""
    file_node = BlueprintNode(
        name="file.py",
        type="file",
        file_path="/tmp/file.py",
        start_line=1,
        end_line=100,
        children=[
            BlueprintNode(
                name="func",
                type="function",
                file_path="/tmp/file.py",
                start_line=10,
                end_line=20,
                signature="()",
            )
        ],
    )
    builder = TreeBuilder()
    tree = builder.build_aggregated_tree(package_path="/tmp", nodes=[file_node])
    assert "[Package: /tmp]" in tree
    assert "file.py" in tree
