"""Tests for metrics MCP tools (metrics_report, metrics_clear, metrics_status)."""
import os

import pytest

from .conftest import unwrap_result


class TestMetricsReportTool:
    """Tests for metrics_report tool."""

    @pytest.mark.asyncio
    async def test_metrics_report_session(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        result = unwrap_result(
            await mcp_client.call_tool("metrics_report", {"period": "session"})
        )

        assert result["status"] == "ok"
        assert result["period_days"] == 1
        assert "report" in result

    @pytest.mark.asyncio
    async def test_metrics_report_week(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        result = unwrap_result(
            await mcp_client.call_tool("metrics_report", {"period": "week"})
        )

        assert result["status"] == "ok"
        assert result["period_days"] == 7

    @pytest.mark.asyncio
    async def test_metrics_report_detailed(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        result = unwrap_result(
            await mcp_client.call_tool(
                "metrics_report", {"period": "session", "detailed": True}
            )
        )

        assert result["status"] == "ok"
        # Detailed reports may include additional fields like flag_usage, command_counts

    @pytest.mark.asyncio
    async def test_metrics_report_all_period(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        result = unwrap_result(
            await mcp_client.call_tool("metrics_report", {"period": "all"})
        )

        assert result["status"] == "ok"
        assert result["period_days"] == 30


class TestMetricsClearTool:
    """Tests for metrics_clear tool."""

    @pytest.mark.asyncio
    async def test_metrics_clear_requires_confirmation(
        self, mcp_client, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        result = unwrap_result(
            await mcp_client.call_tool("metrics_clear", {"confirm": False})
        )

        assert result["status"] == "confirmation_required"

    @pytest.mark.asyncio
    async def test_metrics_clear_with_confirmation(
        self, mcp_client, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        result = unwrap_result(
            await mcp_client.call_tool("metrics_clear", {"confirm": True})
        )

        assert result["status"] == "cleared"


class TestMetricsStatusTool:
    """Tests for metrics_status tool."""

    @pytest.mark.asyncio
    async def test_metrics_status(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        result = unwrap_result(await mcp_client.call_tool("metrics_status", {}))

        assert "enabled" in result
        # Other fields may vary based on tracker state
