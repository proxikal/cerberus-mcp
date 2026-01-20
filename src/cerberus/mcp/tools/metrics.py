"""Metrics and efficiency tracking tools."""
from dataclasses import asdict
from typing import Optional

from cerberus.metrics import generate_efficiency_report, get_efficiency_tracker
from cerberus.metrics.mcp_tracker import get_mcp_tracker, reset_mcp_tracker


def register(mcp):
    @mcp.tool()
    def metrics_report(period: str = "session", detailed: bool = False) -> dict:
        """
        Get efficiency metrics report.

        Provides insights into code retrieval patterns and tool usage
        to help optimize workflows.

        Args:
            period: Time period - "session" (current), "today", "week", or "all" (30 days)
            detailed: Include detailed breakdowns (flag usage, command counts)

        Returns:
            dict with:
            - status: "ok" or "error"
            - period_days: Number of days covered
            - report: Efficiency metrics including retrieval counts, patterns, and suggestions
        """
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
        """
        Clear metrics data.

        Resets all collected efficiency metrics. Requires explicit confirmation
        to prevent accidental data loss.

        Args:
            confirm: Must be True to actually clear data (safety check)

        Returns:
            dict with:
            - status: "cleared" if successful, "confirmation_required" if confirm=False
            - message: Description of result
        """
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
        """
        Get current metrics collection status.

        Shows whether metrics collection is enabled and provides session information.

        Returns:
            dict with:
            - enabled: Whether metrics collection is active
            - storage_path: Path to metrics storage file
            - session_start: When current session began
            - commands_this_session: Number of commands in current session
        """
        try:
            tracker = get_efficiency_tracker()
            store = tracker.store
            return {
                "enabled": not tracker.is_disabled(),
                "storage_path": str(store.metrics_file) if hasattr(store, "metrics_file") else None,
                "session_start": tracker._session_started,  # type: ignore[attr-defined]
                "commands_this_session": tracker._session_commands,  # type: ignore[attr-defined]
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    @mcp.tool()
    def mcp_metrics_session() -> dict:
        """
        Get MCP tool usage metrics for current session.

        Returns detailed statistics about MCP tool usage, token efficiency,
        and optimization opportunities.

        Returns:
            dict with:
            - session_summary: Overview of session metrics
            - tool_statistics: Per-tool usage statistics
            - recommendations: Efficiency recommendations
        """
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
        """
        Get metrics for a specific MCP tool.

        Args:
            tool_name: Name of the tool to get metrics for

        Returns:
            dict with tool-specific statistics
        """
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
        """
        Export current session metrics to JSON file.

        Args:
            output_path: Optional path for output file (auto-generated if not provided)

        Returns:
            dict with:
            - status: "ok" or "error"
            - output_path: Path where metrics were exported
        """
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
        """
        Reset MCP session metrics.

        Clears current session data and starts fresh tracking.

        Returns:
            dict with status message
        """
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
