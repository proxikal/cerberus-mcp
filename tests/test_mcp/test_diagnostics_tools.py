"""Tests for diagnostics MCP tools (health_check)."""
import os

import pytest

from .conftest import unwrap_result


class TestHealthCheckTool:
    """Tests for health_check tool."""

    @pytest.mark.asyncio
    async def test_health_check_basic(self, mcp_client, tmp_path):
        os.chdir(tmp_path)

        result = unwrap_result(await mcp_client.call_tool("health_check", {}))

        assert result["status"] == "healthy"
        assert "version" in result
        assert "python_version" in result
        assert "timestamp" in result
        assert "capabilities" in result
        assert isinstance(result["capabilities"], list)
        assert len(result["capabilities"]) > 0

    @pytest.mark.asyncio
    async def test_health_check_capabilities(self, mcp_client, tmp_path):
        os.chdir(tmp_path)

        result = unwrap_result(await mcp_client.call_tool("health_check", {}))

        # Should have all major capability categories
        expected_capabilities = [
            "search",
            "memory",
            "quality",
        ]
        for cap in expected_capabilities:
            assert cap in result["capabilities"]

    @pytest.mark.asyncio
    async def test_health_check_with_index(self, indexed_project, mcp_client):
        project, _ = indexed_project
        os.chdir(project)

        result = unwrap_result(await mcp_client.call_tool("health_check", {}))

        assert result["status"] == "healthy"
        # Index should be available after indexed_project fixture
        assert result.get("index_available", True) is True
        assert result.get("index_path") is not None
