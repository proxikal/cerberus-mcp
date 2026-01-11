"""
Tests for Phase 19.3: Efficiency Metrics & Observability

Tests for:
  - MetricsStore persistence
  - EfficiencyTracker event recording
  - ReportGenerator aggregation
  - CLI metrics commands
"""

import json
import os
import pytest
import tempfile
import time

pytestmark = pytest.mark.integration  # Uses CliRunner which spawns slow CLI
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner

from cerberus.metrics.efficiency import (
    CommandEvent,
    SessionSummary,
    EfficiencyReport,
    MetricsStore,
    EfficiencyTracker,
    ReportGenerator,
    get_efficiency_tracker,
    generate_efficiency_report,
)
from cerberus.main import app

runner = CliRunner()


class TestCommandEvent:
    """Tests for CommandEvent dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        event = CommandEvent(
            command="blueprint",
            timestamp=1234567890.0,
            flags=["--deps", "--meta"],
            lines_returned=100,
        )
        result = event.to_dict()
        assert result["command"] == "blueprint"
        assert result["flags"] == ["--deps", "--meta"]
        assert result["lines_returned"] == 100

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "command": "get-symbol",
            "timestamp": 1234567890.0,
            "flags": ["--snippet"],
            "lines_returned": 50,
            "hint_shown": "efficiency",
            "hint_followed": True,
            "session_id": "session_123",
        }
        event = CommandEvent.from_dict(data)
        assert event.command == "get-symbol"
        assert event.flags == ["--snippet"]
        assert event.hint_shown == "efficiency"


class TestMetricsStore:
    """Tests for MetricsStore persistence."""

    def test_create_empty(self, tmp_path):
        """Test creating new empty store."""
        store = MetricsStore(metrics_dir=tmp_path)
        assert store._data["version"] == "1.0"
        assert store._data["events"] == []

    def test_record_event(self, tmp_path):
        """Test recording an event."""
        store = MetricsStore(metrics_dir=tmp_path)
        event = CommandEvent(
            command="blueprint",
            timestamp=time.time(),
            flags=["--deps"],
        )
        store.record_event(event)

        assert len(store._data["events"]) == 1
        assert store._data["aggregates"]["command_counts"]["blueprint"] == 1

    def test_persistence(self, tmp_path):
        """Test that data persists across instances."""
        # Create and write
        store1 = MetricsStore(metrics_dir=tmp_path)
        event = CommandEvent(
            command="blueprint",
            timestamp=time.time(),
        )
        store1.record_event(event)

        # Load in new instance
        store2 = MetricsStore(metrics_dir=tmp_path)
        assert len(store2._data["events"]) == 1
        assert store2._data["aggregates"]["command_counts"]["blueprint"] == 1

    def test_flag_usage_tracking(self, tmp_path):
        """Test that flag usage is tracked per command."""
        store = MetricsStore(metrics_dir=tmp_path)

        # Record events with different flags
        store.record_event(CommandEvent("blueprint", time.time(), ["--deps"]))
        store.record_event(CommandEvent("blueprint", time.time(), ["--deps", "--meta"]))
        store.record_event(CommandEvent("blueprint", time.time(), ["--meta"]))

        agg = store._data["aggregates"]
        assert agg["flag_usage"]["blueprint"]["--deps"] == 2
        assert agg["flag_usage"]["blueprint"]["--meta"] == 2

    def test_events_limit(self, tmp_path):
        """Test that events are limited to 10000."""
        store = MetricsStore(metrics_dir=tmp_path)

        # Add 10001 events
        for i in range(10001):
            store.record_event(CommandEvent("test", time.time()))

        assert len(store._data["events"]) == 10000

    def test_record_session(self, tmp_path):
        """Test recording session summary."""
        store = MetricsStore(metrics_dir=tmp_path)
        summary = SessionSummary(
            session_id="test_session",
            started_at=time.time() - 3600,
            ended_at=time.time(),
            command_count=10,
            used_memory_context=True,
            blueprint_then_read_count=5,
            large_responses=1,
            tokens_saved=1000,
        )
        store.record_session(summary)

        assert len(store._data["sessions"]) == 1

    def test_clear(self, tmp_path):
        """Test clearing all data."""
        store = MetricsStore(metrics_dir=tmp_path)
        store.record_event(CommandEvent("test", time.time()))
        store.clear()

        assert store._data["events"] == []
        assert store._data["aggregates"]["command_counts"] == {}


class TestEfficiencyTracker:
    """Tests for EfficiencyTracker."""

    def setup_method(self):
        """Reset singleton before each test."""
        EfficiencyTracker.reset_instance()

    def test_singleton(self, tmp_path):
        """Test singleton pattern."""
        store = MetricsStore(metrics_dir=tmp_path)
        tracker1 = EfficiencyTracker.get_instance(store)
        tracker2 = EfficiencyTracker.get_instance()
        assert tracker1 is tracker2

    def test_disabled_via_env(self, tmp_path, monkeypatch):
        """Test that metrics are disabled via environment variable."""
        monkeypatch.setenv("CERBERUS_NO_METRICS", "true")
        store = MetricsStore(metrics_dir=tmp_path)
        tracker = EfficiencyTracker(store)

        tracker.record_command("test")
        assert len(store._data["events"]) == 0

    def test_record_command(self, tmp_path):
        """Test recording a command."""
        store = MetricsStore(metrics_dir=tmp_path)
        tracker = EfficiencyTracker(store)

        tracker.record_command("blueprint", ["--deps", "--meta"], lines_returned=100)

        assert len(store._data["events"]) == 1
        event = store._data["events"][0]
        assert event["command"] == "blueprint"
        assert event["flags"] == ["--deps", "--meta"]
        assert event["lines_returned"] == 100

    def test_workflow_pattern_detection(self, tmp_path):
        """Test detection of blueprint -> read pattern."""
        store = MetricsStore(metrics_dir=tmp_path)
        tracker = EfficiencyTracker(store)

        tracker.record_command("blueprint")
        tracker.record_command("go")

        assert tracker._session_blueprint_then_read == 1

    def test_hint_tracking(self, tmp_path):
        """Test hint shown/followed tracking."""
        store = MetricsStore(metrics_dir=tmp_path)
        tracker = EfficiencyTracker(store)

        tracker.record_hint_shown("efficiency")
        tracker.record_command("get-symbol")

        events = store._data["events"]
        assert events[0]["hint_shown"] == "efficiency"


class TestReportGenerator:
    """Tests for ReportGenerator."""

    def test_empty_report(self, tmp_path):
        """Test report with no data."""
        store = MetricsStore(metrics_dir=tmp_path)
        generator = ReportGenerator(store)
        report = generator.generate_report(days=7)

        assert report.total_sessions == 0
        assert report.total_commands == 0
        assert report.command_counts == {}

    def test_report_with_data(self, tmp_path):
        """Test report with events."""
        store = MetricsStore(metrics_dir=tmp_path)

        # Add some events
        store.record_event(CommandEvent("blueprint", time.time(), ["--deps"]))
        store.record_event(CommandEvent("blueprint", time.time(), ["--meta"]))
        store.record_event(CommandEvent("get-symbol", time.time(), ["--snippet"]))

        generator = ReportGenerator(store)
        report = generator.generate_report(days=7)

        assert report.total_commands == 3
        assert report.command_counts["blueprint"] == 2
        assert report.command_counts["get-symbol"] == 1

    def test_suggestions_for_no_snippet(self, tmp_path):
        """Test suggestion for get-symbol without --snippet."""
        store = MetricsStore(metrics_dir=tmp_path)

        # Add get-symbol calls without --snippet
        for _ in range(5):
            store.record_event(CommandEvent("get-symbol", time.time()))

        generator = ReportGenerator(store)
        report = generator.generate_report(days=7)

        assert any("--snippet" in s for s in report.suggestions)

    def test_suggestions_for_no_memory(self, tmp_path):
        """Test suggestion for sessions without memory context."""
        store = MetricsStore(metrics_dir=tmp_path)

        # Add sessions without memory
        for i in range(5):
            store.record_session(SessionSummary(
                session_id=f"session_{i}",
                started_at=time.time() - 100,
                ended_at=time.time(),
                command_count=10,
                used_memory_context=False,
                blueprint_then_read_count=0,
                large_responses=0,
                tokens_saved=0,
            ))

        generator = ReportGenerator(store)
        report = generator.generate_report(days=7)

        assert any("memory context" in s.lower() for s in report.suggestions)


class TestMetricsCLI:
    """Tests for metrics CLI commands."""

    def test_metrics_report_json(self, tmp_path, monkeypatch):
        """Test metrics report with JSON output."""
        # Set up temp metrics directory
        monkeypatch.setenv("HOME", str(tmp_path))

        result = runner.invoke(app, ["metrics", "report", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "period_days" in data
        assert "total_sessions" in data
        assert "command_counts" in data

    def test_metrics_report_human(self, tmp_path, monkeypatch):
        """Test metrics report with human output."""
        monkeypatch.setenv("HOME", str(tmp_path))

        result = runner.invoke(app, ["--human", "metrics", "report"])
        assert result.exit_code == 0
        assert "Efficiency Report" in result.output

    def test_metrics_status_json(self, tmp_path, monkeypatch):
        """Test metrics status with JSON output."""
        monkeypatch.setenv("HOME", str(tmp_path))

        result = runner.invoke(app, ["metrics", "status", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "enabled" in data
        assert "storage_path" in data

    def test_metrics_clear(self, tmp_path, monkeypatch):
        """Test metrics clear command."""
        monkeypatch.setenv("HOME", str(tmp_path))

        result = runner.invoke(app, ["metrics", "clear", "--yes"])
        assert result.exit_code == 0
        assert "cleared" in result.output.lower()


class TestGetEfficiencyTracker:
    """Tests for get_efficiency_tracker factory."""

    def setup_method(self):
        """Reset singleton before each test."""
        EfficiencyTracker.reset_instance()

    def test_returns_singleton(self):
        """Test that factory returns singleton."""
        tracker1 = get_efficiency_tracker()
        tracker2 = get_efficiency_tracker()
        assert tracker1 is tracker2


class TestGenerateEfficiencyReport:
    """Tests for generate_efficiency_report helper."""

    def test_returns_report(self, tmp_path, monkeypatch):
        """Test that helper returns EfficiencyReport."""
        monkeypatch.setenv("HOME", str(tmp_path))

        report = generate_efficiency_report(days=7)
        assert isinstance(report, EfficiencyReport)
        assert report.period_days == 7
