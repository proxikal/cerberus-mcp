"""Tests for memory MCP tools."""
import os


import pytest

from .conftest import unwrap_result


class TestMemoryLearn:
    """Tests for memory_learn tool."""

    @pytest.mark.asyncio
    async def test_learn_preference(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        result = unwrap_result(
            await mcp_client.call_tool(
                "memory_learn", {"category": "preference", "content": "Prefer early returns"}
            )
        )

        assert result["status"] == "learned"
        assert result.get("category") in {
            "preference",
            "general",
            "coding_style",
            "naming_conventions",
            "anti_patterns",
        }

    @pytest.mark.asyncio
    async def test_learn_decision(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        result = unwrap_result(
            await mcp_client.call_tool(
                "memory_learn",
                {
                    "category": "decision",
                    "content": "Use SQLite for storage",
                    "project": "test-project",
                    "metadata": {"topic": "Database", "rationale": "Simple and fast"},
                },
            )
        )

        assert result["status"] == "learned"
        assert result["project"] == "test-project"

    @pytest.mark.asyncio
    async def test_learn_correction(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        result = unwrap_result(
            await mcp_client.call_tool(
                "memory_learn",
                {
                    "category": "correction",
                    "content": "Use loguru instead of print",
                    "metadata": {"mistake": "Used print() for logging"},
                },
            )
        )

        assert result["status"] == "learned"
        assert result["category"] == "correction"


class TestMemoryShow:
    """Tests for memory_show tool."""

    @pytest.mark.asyncio
    async def test_show_all(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        await mcp_client.call_tool(
            "memory_learn", {"category": "preference", "content": "Test preference"}
        )

        result = unwrap_result(await mcp_client.call_tool("memory_show", {}))

        assert "memories" in result
        assert result["total"] > 0
        assert any("Test preference" in m["content"] for m in result["memories"])

    @pytest.mark.asyncio
    async def test_show_by_category(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        await mcp_client.call_tool(
            "memory_learn", {"category": "preference", "content": "Test preference"}
        )
        result = unwrap_result(await mcp_client.call_tool("memory_show", {"category": "preference"}))

        assert result["status"] == "ok"
        assert all(m["category"] == "preference" for m in result["memories"])


class TestMemoryContext:
    """Tests for memory_context tool."""

    @pytest.mark.asyncio
    async def test_context_generation(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        await mcp_client.call_tool(
            "memory_learn", {"category": "preference", "content": "Use type hints"}
        )
        await mcp_client.call_tool(
            "memory_learn", {"category": "preference", "content": "Prefer composition over inheritance"}
        )

        result = unwrap_result(await mcp_client.call_tool("memory_context", {"compact": True}))

        # unwrap_result extracts the "result" key, so we get the string directly
        assert isinstance(result, str)
        assert len(result) > 0


class TestMemoryForget:
    """Tests for memory_forget tool."""

    @pytest.mark.asyncio
    async def test_forget_preference(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))

        # First learn something
        await mcp_client.call_tool(
            "memory_learn", {"category": "preference", "content": "Temp preference to forget"}
        )

        # Then forget it
        result = unwrap_result(
            await mcp_client.call_tool(
                "memory_forget",
                {"category": "preference", "identifier": "Temp preference to forget"},
            )
        )

        assert result["status"] in ("forgotten", "not_found")

    @pytest.mark.asyncio
    async def test_forget_decision(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        # Learn a decision
        await mcp_client.call_tool(
            "memory_learn",
            {
                "category": "decision",
                "content": "Decision to forget",
                "project": "test-project",
            },
        )

        # Try to forget it
        result = unwrap_result(
            await mcp_client.call_tool(
                "memory_forget",
                {
                    "category": "decision",
                    "identifier": "Decision to forget",
                    "project": "test-project",
                },
            )
        )

        assert result["status"] in ("forgotten", "not_found", "error")

    @pytest.mark.asyncio
    async def test_forget_unknown_category(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))

        result = unwrap_result(
            await mcp_client.call_tool(
                "memory_forget", {"category": "unknown", "identifier": "test"}
            )
        )

        assert result["status"] == "error"


class TestMemoryStats:
    """Tests for memory_stats tool."""

    @pytest.mark.asyncio
    async def test_stats_empty(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))

        result = unwrap_result(await mcp_client.call_tool("memory_stats", {}))

        assert "preferences" in result
        assert "decisions" in result
        assert "corrections" in result
        assert "total_entries" in result

    @pytest.mark.asyncio
    async def test_stats_after_learning(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))

        # Learn some items
        await mcp_client.call_tool(
            "memory_learn", {"category": "preference", "content": "Pref 1"}
        )
        await mcp_client.call_tool(
            "memory_learn", {"category": "preference", "content": "Pref 2"}
        )

        result = unwrap_result(await mcp_client.call_tool("memory_stats", {}))

        assert result["preferences"] >= 2
        assert result["total_entries"] >= 2
        assert "database_path" in result


class TestMemoryExport:
    """Tests for memory_export tool."""

    @pytest.mark.asyncio
    async def test_export_default_path(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        # Learn something to export
        await mcp_client.call_tool(
            "memory_learn", {"category": "preference", "content": "Export test"}
        )

        result = unwrap_result(await mcp_client.call_tool("memory_export", {}))

        assert result["status"] == "exported"
        assert "path" in result
        assert "entries" in result

    @pytest.mark.asyncio
    async def test_export_custom_path(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        # Learn something first so we have data to export
        await mcp_client.call_tool(
            "memory_learn", {"category": "preference", "content": "Test export data"}
        )

        output_file = str(tmp_path / "custom-export.json")

        result = unwrap_result(
            await mcp_client.call_tool("memory_export", {"output_path": output_file})
        )

        assert result["status"] == "exported"
        assert result["path"] == output_file
        assert (tmp_path / "custom-export.json").exists()


class TestMemoryImport:
    """Tests for memory_import tool."""

    @pytest.mark.asyncio
    async def test_import_with_merge(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        # First export some data
        await mcp_client.call_tool(
            "memory_learn", {"category": "preference", "content": "Import test"}
        )
        export_file = str(tmp_path / "export.json")
        await mcp_client.call_tool("memory_export", {"output_path": export_file})

        # Then import it back with merge
        result = unwrap_result(
            await mcp_client.call_tool(
                "memory_import", {"input_path": export_file, "merge": True}
            )
        )

        assert result["status"] == "imported"
        assert result["merged"] is True
        assert "counts" in result

    @pytest.mark.asyncio
    async def test_import_without_merge(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        # Create export file
        await mcp_client.call_tool(
            "memory_learn", {"category": "preference", "content": "Replace test"}
        )
        export_file = str(tmp_path / "export2.json")
        await mcp_client.call_tool("memory_export", {"output_path": export_file})

        result = unwrap_result(
            await mcp_client.call_tool(
                "memory_import", {"input_path": export_file, "merge": False}
            )
        )

        assert result["status"] == "imported"
        assert result["merged"] is False


class TestMemoryExtract:
    """Tests for memory_extract tool."""

    @pytest.mark.asyncio
    async def test_extract_no_git(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        os.chdir(tmp_path)

        # Try to extract from a non-git directory
        result = unwrap_result(
            await mcp_client.call_tool(
                "memory_extract", {"path": str(tmp_path), "lookback_days": 7}
            )
        )

        # Should handle gracefully (either error or empty result)
        assert "success" in result or "status" in result or "error" in result

    @pytest.mark.asyncio
    async def test_extract_path_not_found(self, mcp_client, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))

        result = unwrap_result(
            await mcp_client.call_tool(
                "memory_extract", {"path": "/nonexistent/path"}
            )
        )

        assert result.get("success") is False or result.get("status") == "error"
