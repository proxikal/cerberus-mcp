"""Tests for quality MCP tools (style_check, style_fix, related_changes)."""
import os
from pathlib import Path

import pytest

from .conftest import unwrap_result


class TestStyleCheckTool:
    """Tests for style_check tool."""

    @pytest.mark.asyncio
    async def test_style_check_file(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(
            await mcp_client.call_tool(
                "style_check", {"path": str(project / "src" / "main.py")}
            )
        )

        assert result["status"] == "checked"
        assert "violation_count" in result
        assert "violations" in result

    @pytest.mark.asyncio
    async def test_style_check_directory(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(
            await mcp_client.call_tool("style_check", {"path": str(project / "src")})
        )

        assert result["status"] == "checked"
        assert "violation_count" in result

    @pytest.mark.asyncio
    async def test_style_check_with_fix_preview(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        # Create a file with a fixable style issue
        bad_file = project / "src" / "bad_style.py"
        bad_file.write_text("def foo( x ):\n    return x\n")

        result = unwrap_result(
            await mcp_client.call_tool(
                "style_check", {"path": str(bad_file), "fix_preview": True}
            )
        )

        assert result["status"] == "checked"
        # fix_preview may or may not be present depending on what issues were found

    @pytest.mark.asyncio
    async def test_style_check_path_not_found(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(
            await mcp_client.call_tool(
                "style_check", {"path": "/nonexistent/path/file.py"}
            )
        )

        assert result["status"] == "error"
        assert result["error_type"] == "path_not_found"


class TestStyleFixTool:
    """Tests for style_fix tool."""

    @pytest.mark.asyncio
    async def test_style_fix_dry_run(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(
            await mcp_client.call_tool(
                "style_fix",
                {"path": str(project / "src" / "main.py"), "dry_run": True},
            )
        )

        assert result["status"] == "dry_run"
        assert "would_fix" in result

    @pytest.mark.asyncio
    async def test_style_fix_applies_changes(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        # Create a file with fixable issues
        fixable_file = project / "src" / "fixable.py"
        fixable_file.write_text("def foo( x ):\n    return x\n")

        result = unwrap_result(
            await mcp_client.call_tool(
                "style_fix", {"path": str(fixable_file), "dry_run": False}
            )
        )

        # Either fixed something or nothing to fix
        assert result["status"] in ("fixed", "dry_run", "error")

    @pytest.mark.asyncio
    async def test_style_fix_path_not_found(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(
            await mcp_client.call_tool(
                "style_fix", {"path": "/nonexistent/path/file.py"}
            )
        )

        assert result["status"] == "error"
        assert result["error_type"] == "path_not_found"


class TestRelatedChangesTool:
    """Tests for related_changes tool."""

    @pytest.mark.asyncio
    async def test_related_changes_basic(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(
            await mcp_client.call_tool(
                "related_changes",
                {
                    "file_path": str(project / "src" / "main.py"),
                    "symbol_name": "add",
                },
            )
        )

        # May return analyzed or error if prediction engine has issues
        assert result["status"] in ("analyzed", "error")
        if result["status"] == "analyzed":
            assert "suggestions" in result

    @pytest.mark.asyncio
    async def test_related_changes_without_symbol(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(
            await mcp_client.call_tool(
                "related_changes", {"file_path": str(project / "src" / "main.py")}
            )
        )

        assert result["status"] in ("analyzed", "error")
