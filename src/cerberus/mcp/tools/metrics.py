"""Metrics and efficiency tracking tools."""
from dataclasses import asdict
from typing import Optional

from cerberus.metrics import generate_efficiency_report, get_efficiency_tracker
from cerberus.metrics.mcp_tracker import get_mcp_tracker, reset_mcp_tracker


def register(mcp):
    @mcp.tool()
    def metrics_report(period: str = "session", detailed: bool = False) -> dict:
        """Get tool usage metrics and efficiency patterns."""
        try:
            days = {
                "session": 1,
                "today": 1,
                "week": 7,
                "all": 30,
            }.get(period, 7)

            report = generate_efficiency_report(days=days)
            data = asdict(report)

            # Trim detail if not requested
            if not detailed:
                data.pop("flag_usage", None)
                data.pop("command_counts", None)

            return {"status": "ok", "period_days": days, "report": data}
        except Exception as exc:
            return {
                "status": "error",
                "error_type": "metrics_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def metrics_clear(confirm: bool = False) -> dict:
        """Clear stored metrics data."""
        if not confirm:
            return {
                "status": "confirmation_required",
                "message": "Set confirm=True to clear all metrics data",
            }

        try:
            tracker = get_efficiency_tracker()
            tracker.store.clear()
            return {"status": "cleared", "message": "Efficiency metrics cleared"}
        except Exception as exc:
            return {
                "status": "error",
                "error_type": "clear_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def metrics_status() -> dict:
        """Check metrics collection status."""
        try:
            tracker = get_efficiency_tracker()
            store = tracker.store
            return {
                "enabled": not tracker.is_disabled(),
                "storage_path": str(store.metrics_file) if hasattr(store, "metrics_file") else None,
                "session_start": tracker._session_started,
                "commands_this_session": tracker._session_commands,
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    @mcp.tool()
    def mcp_metrics_session() -> dict:
        """Get MCP tool usage metrics for current session."""
        try:
            tracker = get_mcp_tracker()
            summary = tracker.get_session_summary()
            stats = tracker.get_tool_statistics()
            recommendations = tracker.get_efficiency_recommendations()

            return {
                "status": "ok",
                "session_summary": summary,
                "tool_statistics": stats,
                "recommendations": recommendations,
            }
        except Exception as exc:
            return {
                "status": "error",
                "error_type": "mcp_metrics_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def mcp_metrics_tool(tool_name: str) -> dict:
        """Get detailed metrics for specific MCP tool."""
        try:
            tracker = get_mcp_tracker()
            stats = tracker.get_tool_statistics(tool_name)

            return {
                "status": "ok",
                "tool_name": tool_name,
                "statistics": stats,
            }
        except Exception as exc:
            return {
                "status": "error",
                "error_type": "tool_metrics_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def mcp_metrics_export(output_path: Optional[str] = None) -> dict:
        """Export MCP metrics to JSON file."""
        try:
            tracker = get_mcp_tracker()
            from pathlib import Path
            path = tracker.export_session_data(
                Path(output_path) if output_path else None
            )

            return {
                "status": "ok",
                "output_path": str(path),
                "message": f"Session metrics exported to {path}",
            }
        except Exception as exc:
            return {
                "status": "error",
                "error_type": "export_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def mcp_metrics_reset() -> dict:
        """Reset MCP metrics collection."""
        try:
            reset_mcp_tracker()
            return {
                "status": "ok",
                "message": "MCP session metrics reset",
            }
        except Exception as exc:
            return {
                "status": "error",
                "error_type": "reset_failed",
                "message": str(exc),
            }
