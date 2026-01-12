"""
Efficiency Metrics Tracking (Phase 19.3)

Tracks command usage patterns, workflow efficiency, and generates reports.
All data stored locally - no telemetry.

Privacy: Disable with CERBERUS_NO_METRICS=true
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

from cerberus.logging_config import logger


# Default storage location
METRICS_DIR = Path.home() / ".config" / "cerberus" / "metrics"
METRICS_FILE = "efficiency_metrics.json"


@dataclass
class CommandEvent:
    """A single command execution event."""

    command: str
    timestamp: float
    flags: List[str] = field(default_factory=list)
    lines_returned: int = 0
    hint_shown: Optional[str] = None
    hint_followed: bool = False
    session_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CommandEvent":
        return cls(**data)


@dataclass
class SessionSummary:
    """Summary of a single session."""

    session_id: str
    started_at: float
    ended_at: float
    command_count: int
    used_memory_context: bool
    blueprint_then_read_count: int
    large_responses: int
    tokens_saved: int


@dataclass
class EfficiencyReport:
    """Aggregated efficiency report."""

    period_days: int
    total_sessions: int
    total_commands: int

    # Command breakdown
    command_counts: Dict[str, int]
    flag_usage: Dict[str, Dict[str, int]]

    # Workflow patterns
    blueprint_then_read: int
    direct_get_symbol: int
    memory_context_sessions: int

    # Token efficiency
    total_tokens_saved: int
    avg_efficiency_percent: float

    # Hints
    hints_shown: int
    hints_followed: int

    # Suggestions
    suggestions: List[str]


class MetricsStore:
    """
    Persistent storage for efficiency metrics.

    Data stored in ~/.config/cerberus/metrics/efficiency_metrics.json
    """

    def __init__(self, metrics_dir: Optional[Path] = None):
        self.metrics_dir = metrics_dir or METRICS_DIR
        self.metrics_file = self.metrics_dir / METRICS_FILE
        self._ensure_dir()
        self._data = self._load()

    def _ensure_dir(self) -> None:
        """Ensure metrics directory exists."""
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        """Load metrics from disk."""
        if self.metrics_file.exists():
            try:
                with open(self.metrics_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.debug(f"Failed to load metrics: {e}")
                return self._create_empty()
        return self._create_empty()

    def _create_empty(self) -> Dict[str, Any]:
        """Create empty metrics structure."""
        return {
            "version": "1.0",
            "created_at": time.time(),
            "events": [],
            "sessions": [],
            "aggregates": {
                "command_counts": {},
                "flag_usage": {},
                "hints_shown": 0,
                "hints_followed": 0,
                "total_tokens_saved": 0,
            },
        }

    def _save(self) -> None:
        """Persist metrics to disk."""
        try:
            with open(self.metrics_file, "w") as f:
                json.dump(self._data, f, indent=2)
        except IOError as e:
            logger.debug(f"Failed to save metrics: {e}")

    def record_event(self, event: CommandEvent) -> None:
        """Record a command event."""
        self._data["events"].append(event.to_dict())

        # Update aggregates
        cmd = event.command
        agg = self._data["aggregates"]

        # Command counts
        agg["command_counts"][cmd] = agg["command_counts"].get(cmd, 0) + 1

        # Flag usage
        if cmd not in agg["flag_usage"]:
            agg["flag_usage"][cmd] = {}
        for flag in event.flags:
            agg["flag_usage"][cmd][flag] = agg["flag_usage"][cmd].get(flag, 0) + 1

        # Hints
        if event.hint_shown:
            agg["hints_shown"] += 1
            if event.hint_followed:
                agg["hints_followed"] += 1

        # Keep only last 10000 events
        if len(self._data["events"]) > 10000:
            self._data["events"] = self._data["events"][-10000:]

        self._save()

    def record_session(self, summary: SessionSummary) -> None:
        """Record a session summary."""
        self._data["sessions"].append(asdict(summary))

        # Keep only last 1000 sessions
        if len(self._data["sessions"]) > 1000:
            self._data["sessions"] = self._data["sessions"][-1000:]

        self._save()

    def add_tokens_saved(self, tokens: int) -> None:
        """Add to total tokens saved."""
        self._data["aggregates"]["total_tokens_saved"] += tokens
        self._save()

    def get_events_since(self, since_timestamp: float) -> List[CommandEvent]:
        """Get events since a timestamp."""
        events = []
        for e in self._data["events"]:
            if e.get("timestamp", 0) >= since_timestamp:
                events.append(CommandEvent.from_dict(e))
        return events

    def get_sessions_since(self, since_timestamp: float) -> List[Dict[str, Any]]:
        """Get sessions since a timestamp."""
        return [
            s for s in self._data["sessions"]
            if s.get("started_at", 0) >= since_timestamp
        ]

    def get_aggregates(self) -> Dict[str, Any]:
        """Get aggregate metrics."""
        return self._data["aggregates"]

    def clear(self) -> None:
        """Clear all metrics (for testing)."""
        self._data = self._create_empty()
        self._save()


class EfficiencyTracker:
    """
    Tracks efficiency metrics during command execution.

    Usage:
        tracker = get_efficiency_tracker()
        tracker.record_command("blueprint", ["--deps", "--meta"])
        tracker.record_hint_shown("memory")
    """

    _instance: Optional["EfficiencyTracker"] = None

    def __init__(self, store: Optional[MetricsStore] = None):
        self.store = store or MetricsStore()
        self._current_session_id = self._generate_session_id()
        self._session_started = time.time()
        self._last_command: Optional[str] = None
        self._session_commands = 0
        self._session_blueprint_then_read = 0
        self._session_used_memory = False
        self._session_large_responses = 0
        self._pending_hint: Optional[str] = None

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"session_{int(time.time() * 1000)}"

    @classmethod
    def get_instance(cls, store: Optional[MetricsStore] = None) -> "EfficiencyTracker":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls(store)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    def is_disabled(self) -> bool:
        """Check if metrics are disabled."""
        return os.getenv("CERBERUS_NO_METRICS", "").lower() in ("true", "1", "yes")

    def record_command(
        self,
        command: str,
        flags: Optional[List[str]] = None,
        lines_returned: int = 0,
    ) -> None:
        """Record a command execution."""
        if self.is_disabled():
            return

        flags = flags or []

        # Track workflow patterns
        if command == "blueprint":
            pass  # Next command might be a read
        elif command in ("get-symbol", "go") and self._last_command == "blueprint":
            self._session_blueprint_then_read += 1

        if command == "start" or "memory" in command:
            if "--with-memory" in flags or "context" in command:
                self._session_used_memory = True

        if lines_returned > 500:
            self._session_large_responses += 1

        # Create event
        event = CommandEvent(
            command=command,
            timestamp=time.time(),
            flags=flags,
            lines_returned=lines_returned,
            hint_shown=self._pending_hint,
            session_id=self._current_session_id,
        )

        self.store.record_event(event)
        self._last_command = command
        self._session_commands += 1
        self._pending_hint = None

    def record_hint_shown(self, hint_type: str) -> None:
        """Record that a hint was shown."""
        if self.is_disabled():
            return
        self._pending_hint = hint_type

    def record_hint_followed(self) -> None:
        """Record that the user followed a hint suggestion."""
        if self.is_disabled():
            return

        # Update the last event to mark hint as followed
        events = self.store._data["events"]
        if events:
            events[-1]["hint_followed"] = True
            self.store._save()

    def record_tokens_saved(self, tokens: int) -> None:
        """Record tokens saved."""
        if self.is_disabled():
            return
        self.store.add_tokens_saved(tokens)

    def end_session(self) -> None:
        """End the current session and record summary."""
        if self.is_disabled():
            return

        summary = SessionSummary(
            session_id=self._current_session_id,
            started_at=self._session_started,
            ended_at=time.time(),
            command_count=self._session_commands,
            used_memory_context=self._session_used_memory,
            blueprint_then_read_count=self._session_blueprint_then_read,
            large_responses=self._session_large_responses,
            tokens_saved=0,  # Could be enhanced later
        )
        self.store.record_session(summary)

        # Reset for next session
        self._current_session_id = self._generate_session_id()
        self._session_started = time.time()
        self._session_commands = 0
        self._session_blueprint_then_read = 0
        self._session_used_memory = False
        self._session_large_responses = 0


class ReportGenerator:
    """Generates efficiency reports from stored metrics."""

    def __init__(self, store: Optional[MetricsStore] = None):
        self.store = store or MetricsStore()

    def generate_report(self, days: int = 7) -> EfficiencyReport:
        """Generate an efficiency report for the given period."""
        since = time.time() - (days * 24 * 60 * 60)

        events = self.store.get_events_since(since)
        sessions = self.store.get_sessions_since(since)
        aggregates = self.store.get_aggregates()

        # Count commands in period
        command_counts: Dict[str, int] = {}
        flag_usage: Dict[str, Dict[str, int]] = {}
        hints_shown = 0
        hints_followed = 0

        for event in events:
            cmd = event.command
            command_counts[cmd] = command_counts.get(cmd, 0) + 1

            if cmd not in flag_usage:
                flag_usage[cmd] = {}
            for flag in event.flags:
                flag_usage[cmd][flag] = flag_usage[cmd].get(flag, 0) + 1

            if event.hint_shown:
                hints_shown += 1
                if event.hint_followed:
                    hints_followed += 1

        # Workflow patterns
        blueprint_then_read = sum(
            s.get("blueprint_then_read_count", 0) for s in sessions
        )
        direct_get_symbol = command_counts.get("get-symbol", 0)
        memory_sessions = sum(
            1 for s in sessions if s.get("used_memory_context", False)
        )

        # Token efficiency
        total_saved = aggregates.get("total_tokens_saved", 0)

        # Generate suggestions
        suggestions = self._generate_suggestions(
            command_counts, flag_usage, direct_get_symbol, memory_sessions, len(sessions)
        )

        return EfficiencyReport(
            period_days=days,
            total_sessions=len(sessions),
            total_commands=len(events),
            command_counts=command_counts,
            flag_usage=flag_usage,
            blueprint_then_read=blueprint_then_read,
            direct_get_symbol=direct_get_symbol,
            memory_context_sessions=memory_sessions,
            total_tokens_saved=total_saved,
            avg_efficiency_percent=0.0,  # Could calculate from session data
            hints_shown=hints_shown,
            hints_followed=hints_followed,
            suggestions=suggestions,
        )

    def _generate_suggestions(
        self,
        command_counts: Dict[str, int],
        flag_usage: Dict[str, Dict[str, int]],
        direct_get_symbol: int,
        memory_sessions: int,
        total_sessions: int,
    ) -> List[str]:
        """Generate actionable suggestions based on metrics."""
        suggestions = []

        # Check get-symbol usage without --snippet
        get_symbol_count = command_counts.get("get-symbol", 0)
        snippet_usage = flag_usage.get("get-symbol", {}).get("--snippet", 0)
        if get_symbol_count > 0 and snippet_usage < get_symbol_count * 0.5:
            no_snippet = get_symbol_count - snippet_usage
            suggestions.append(
                f"{no_snippet} get-symbol calls could use --snippet for efficiency"
            )

        # Check memory context usage
        if total_sessions > 0:
            memory_pct = (memory_sessions / total_sessions) * 100
            if memory_pct < 50:
                skipped = total_sessions - memory_sessions
                suggestions.append(
                    f"{skipped} sessions skipped memory context (use 'cerberus start')"
                )

        # Check blueprint usage
        blueprint_count = command_counts.get("blueprint", 0)
        if blueprint_count == 0 and get_symbol_count > 5:
            suggestions.append(
                "Consider using 'cerberus blueprint' before get-symbol for better context"
            )

        # Check 'go' command adoption
        go_count = command_counts.get("go", 0)
        if go_count == 0 and get_symbol_count > 0:
            suggestions.append(
                "Try 'cerberus go <file>' for streamlined file exploration"
            )

        return suggestions


def get_efficiency_tracker() -> EfficiencyTracker:
    """Get the global efficiency tracker instance."""
    return EfficiencyTracker.get_instance()


def generate_efficiency_report(days: int = 7) -> EfficiencyReport:
    """Generate an efficiency report for the given period."""
    generator = ReportGenerator()
    return generator.generate_report(days)
