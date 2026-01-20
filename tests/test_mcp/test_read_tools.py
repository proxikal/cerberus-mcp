"""Tests for read-only MCP tools."""
import json
import os

import pytest

from .conftest import unwrap_result


class TestSearchTool:
    """Tests for search tool."""

    @pytest.mark.asyncio
    async def test_search_finds_function(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        results = unwrap_result(await mcp_client.call_tool("search", {"query": "hello", "limit": 5}))

        assert len(results) >= 1
        assert any(r["name"] == "hello" for r in results)

    @pytest.mark.asyncio
    async def test_search_finds_class(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        results = unwrap_result(
            await mcp_client.call_tool("search", {"query": "Calculator", "limit": 5})
        )

        assert len(results) >= 1
        assert any(r["name"] == "Calculator" for r in results)

    @pytest.mark.asyncio
    async def test_search_empty_query(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        results = unwrap_result(
            await mcp_client.call_tool("search", {"query": "nonexistent_xyz_123", "limit": 5})
        )

        assert len(results) == 0


class TestGetSymbolTool:
    """Tests for get_symbol tool."""

    @pytest.mark.asyncio
    async def test_get_symbol_exact(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        results = unwrap_result(
            await mcp_client.call_tool("get_symbol", {"name": "hello", "exact": True})
        )

        assert len(results) == 1
        assert results[0]["name"] == "hello"
        assert "code" in results[0]
        assert "def hello" in results[0]["code"]

    @pytest.mark.asyncio
    async def test_get_symbol_with_context(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        results = unwrap_result(
            await mcp_client.call_tool("get_symbol", {"name": "hello", "context_lines": 10})
        )

        assert len(results) == 1
        assert '"""Greet someone."""' in results[0]["code"]


class TestReadRangeTool:
    """Tests for read_range tool."""

    @pytest.mark.asyncio
    async def test_read_range_basic(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(
            await mcp_client.call_tool(
                "read_range",
                {
                    "file_path": str(project / "src" / "main.py"),
                    "start_line": 1,
                    "end_line": 5,
                },
            )
        )

        assert "content" in result
        assert "Main module" in result["content"]

    @pytest.mark.asyncio
    async def test_read_range_with_context(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(
            await mcp_client.call_tool(
                "read_range",
                {
                    "file_path": str(project / "src" / "main.py"),
                    "start_line": 5,
                    "end_line": 7,
                    "context_lines": 2,
                },
            )
        )

        assert result["start_line"] == 3  # 5 - 2
        assert result["end_line"] == 9  # 7 + 2


class TestBlueprintTool:
    """Tests for blueprint tool."""

    @pytest.mark.asyncio
    async def test_blueprint_file(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(
            await mcp_client.call_tool("blueprint", {"path": str(project / "src" / "main.py")})
        )

        assert "hello" in result or "Calculator" in result

    @pytest.mark.asyncio
    async def test_blueprint_json_format(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(
            await mcp_client.call_tool(
                "blueprint",
                {"path": str(project / "src" / "main.py"), "format": "json"},
            )
        )

        parsed = json.loads(result) if isinstance(result, str) else result
        assert "symbols" in parsed or "file" in parsed
