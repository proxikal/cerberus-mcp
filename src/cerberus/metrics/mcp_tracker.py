"""
MCP-specific metrics tracking.

Extends the existing metrics system to track MCP tool usage,
token costs, and efficiency patterns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import time

from cerberus.metrics.efficiency import MetricsStore, CommandEvent


@dataclass
class MCPToolEvent:
    """Represents a single MCP tool invocation."""
    tool_name: str
    timestamp: float
    parameters: Dict[str, Any] = field(default_factory=dict)
    tokens_used: Optional[int] = None
    tokens_saved: Optional[int] = None
    alternative_approach: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
            "parameters": self.parameters,
            "tokens_used": self.tokens_used,
            "tokens_saved": self.tokens_saved,
            "alternative_approach": self.alternative_approach,
            "warnings": self.warnings,
            "hints": self.hints,
            "success": self.success,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPToolEvent':
        return cls(**data)


class MCPMetricsTracker:
    """
    Tracks MCP tool usage and efficiency metrics.

    Integrates with the existing MetricsStore but adds MCP-specific tracking.
    """

    def __init__(self, metrics_dir: Optional[Path] = None):
        """
        Initialize MCP metrics tracker.

        Args:
            metrics_dir: Directory for metrics storage (uses default if not provided)
        """
        self.store = MetricsStore(metrics_dir)
        self.session_start = time.time()
        self.session_events: List[MCPToolEvent] = []

    def track_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        tokens_used: Optional[int] = None,
        tokens_saved: Optional[int] = None,
        alternative_approach: Optional[str] = None,
        warnings: Optional[List[str]] = None,
        hints: Optional[List[str]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Track an MCP tool invocation.

        Args:
            tool_name: Name of the MCP tool
            parameters: Tool parameters used
            tokens_used: Estimated tokens used
            tokens_saved: Estimated tokens saved vs alternative
            alternative_approach: Description of alternative approach
            warnings: List of warnings issued
            hints: List of hints issued
            success: Whether the call succeeded
            error_message: Error message if failed
        """
        event = MCPToolEvent(
            tool_name=tool_name,
            timestamp=time.time(),
            parameters=parameters,
            tokens_used=tokens_used,
            tokens_saved=tokens_saved,
            alternative_approach=alternative_approach,
            warnings=warnings or [],
            hints=hints or [],
            success=success,
            error_message=error_message,
        )

        self.session_events.append(event)

        # Also track as a command event for compatibility with existing metrics
        self.store.record_command(
            CommandEvent(
                timestamp=event.timestamp,
                command=f"mcp:{tool_name}",
                flags=[],
                lines_returned=0,
            )
        )

        # Track token savings
        if tokens_saved and tokens_saved > 0:
            self.store.record_token_savings(tokens_saved)

    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of current session.

        Returns:
            Dict with session statistics
        """
        total_calls = len(self.session_events)
        successful_calls = sum(1 for e in self.session_events if e.success)
        failed_calls = total_calls - successful_calls

        total_tokens_used = sum(
            e.tokens_used for e in self.session_events if e.tokens_used
        )
        total_tokens_saved = sum(
            e.tokens_saved for e in self.session_events if e.tokens_saved
        )

        tool_usage = {}
        for event in self.session_events:
            tool_usage[event.tool_name] = tool_usage.get(event.tool_name, 0) + 1

        warnings_issued = sum(len(e.warnings) for e in self.session_events)
        hints_issued = sum(len(e.hints) for e in self.session_events)

        return {
            "session_start": self.session_start,
            "session_duration_seconds": time.time() - self.session_start,
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "total_tokens_used": total_tokens_used,
            "total_tokens_saved": total_tokens_saved,
            "efficiency_ratio": (
                total_tokens_saved / total_tokens_used
                if total_tokens_used > 0
                else 0
            ),
            "tool_usage": tool_usage,
            "warnings_issued": warnings_issued,
            "hints_issued": hints_issued,
        }

    def get_tool_statistics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get statistics for a specific tool or all tools.

        Args:
            tool_name: Optional tool name to filter by

        Returns:
            Dict with tool statistics
        """
        events = self.session_events
        if tool_name:
            events = [e for e in events if e.tool_name == tool_name]

        if not events:
            return {"message": "No events found"}

        total_calls = len(events)
        successful_calls = sum(1 for e in events if e.success)

        tokens_data = [e for e in events if e.tokens_used]
        avg_tokens = (
            sum(e.tokens_used for e in tokens_data) / len(tokens_data)
            if tokens_data
            else 0
        )

        savings_data = [e for e in events if e.tokens_saved and e.tokens_saved > 0]
        avg_savings = (
            sum(e.tokens_saved for e in savings_data) / len(savings_data)
            if savings_data
            else 0
        )

        return {
            "tool_name": tool_name or "all",
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "avg_tokens_used": round(avg_tokens, 2),
            "avg_tokens_saved": round(avg_savings, 2),
            "calls_with_warnings": sum(1 for e in events if e.warnings),
            "calls_with_hints": sum(1 for e in events if e.hints),
        }

    def export_session_data(self, output_path: Optional[Path] = None) -> Path:
        """
        Export session data to JSON file.

        Args:
            output_path: Optional path for output file

        Returns:
            Path to exported file
        """
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_path = Path(f"mcp-session-{timestamp}.json")

        data = {
            "session_summary": self.get_session_summary(),
            "events": [e.to_dict() for e in self.session_events],
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        return output_path

    def get_efficiency_recommendations(self) -> List[str]:
        """
        Generate efficiency recommendations based on usage patterns.

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Check for expensive blueprint usage
        blueprint_events = [e for e in self.session_events if e.tool_name == "blueprint"]
        expensive_blueprints = [
            e for e in blueprint_events
            if e.parameters.get("show_deps") and e.parameters.get("show_meta")
        ]

        if expensive_blueprints:
            recommendations.append(
                f"Found {len(expensive_blueprints)} blueprint calls with both show_deps=true "
                "and show_meta=true. Consider using only one flag unless both are needed."
            )

        # Check for deep call graphs
        call_graph_events = [e for e in self.session_events if e.tool_name == "call_graph"]
        deep_graphs = [e for e in call_graph_events if e.parameters.get("depth", 0) > 2]

        if deep_graphs:
            recommendations.append(
                f"Found {len(deep_graphs)} call_graph calls with depth > 2. "
                "Consider depth=1 or depth=2 for better token efficiency."
            )

        # Check for high search limits
        search_events = [e for e in self.session_events if e.tool_name == "search"]
        high_limit_searches = [e for e in search_events if e.parameters.get("limit", 0) > 20]

        if high_limit_searches:
            recommendations.append(
                f"Found {len(high_limit_searches)} search calls with limit > 20. "
                "Consider limit=5-10 for most use cases."
            )

        # Check for tools that could have used alternatives
        read_range_savings = [
            e for e in self.session_events
            if e.tool_name == "read_range" and e.tokens_saved and e.tokens_saved > 0
        ]

        if read_range_savings:
            total_saved = sum(e.tokens_saved for e in read_range_savings)
            recommendations.append(
                f"read_range saved {total_saved} tokens vs reading full files. "
                "Continue using read_range for targeted reads."
            )

        if not recommendations:
            recommendations.append("No efficiency concerns found. Usage patterns look good!")

        return recommendations


# Global instance for easy access
_tracker_instance: Optional[MCPMetricsTracker] = None


def get_mcp_tracker() -> MCPMetricsTracker:
    """Get or create global MCP metrics tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = MCPMetricsTracker()
    return _tracker_instance


def reset_mcp_tracker() -> None:
    """Reset global MCP metrics tracker instance."""
    global _tracker_instance
    _tracker_instance = None
