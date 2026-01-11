"""
Tests for Protocol Refresh System (Phase 19.7)

Tests protocol tracking, content generation, and refresh hints.
"""

import os
import json
import tempfile
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from cerberus.protocol.tracker import (
    ProtocolTracker,
    ProtocolState,
    get_protocol_tracker,
    reset_protocol_tracker,
    COMMAND_THRESHOLD,
    TIME_THRESHOLD_SECONDS,
    STALE_THRESHOLD_SECONDS,
)
from cerberus.protocol.content import (
    get_protocol_light,
    get_protocol_rules,
    get_protocol_full,
    get_protocol_json,
    PROTOCOL_VERSION,
)
from cerberus.cli.hints import EfficiencyHints


class TestProtocolState:
    """Test ProtocolState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = ProtocolState()
        assert state.last_refresh is None
        assert state.commands_since_refresh == 0
        assert state.total_commands == 0
        assert state.refresh_count == 0

    def test_to_dict(self):
        """Test state serialization."""
        state = ProtocolState()
        state.commands_since_refresh = 5
        d = state.to_dict()
        assert "session_start" in d
        assert d["commands_since_refresh"] == 5

    def test_from_dict(self):
        """Test state deserialization."""
        data = {
            "session_start": time.time(),
            "last_refresh": None,
            "commands_since_refresh": 10,
            "total_commands": 15,
            "refresh_count": 1,
        }
        state = ProtocolState.from_dict(data)
        assert state.commands_since_refresh == 10
        assert state.total_commands == 15


class TestProtocolTracker:
    """Test ProtocolTracker class."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_protocol_tracker()

    def teardown_method(self):
        """Clean up after each test."""
        reset_protocol_tracker()

    def test_tracker_initializes(self):
        """Test tracker initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / ".cerberus_protocol.json"
            tracker = ProtocolTracker(session_file)
            assert tracker.state.commands_since_refresh == 0

    def test_record_command(self):
        """Test command recording."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / ".cerberus_protocol.json"
            tracker = ProtocolTracker(session_file)

            tracker.record_command("blueprint")
            assert tracker.state.commands_since_refresh == 1
            assert tracker.state.total_commands == 1

            tracker.record_command("search")
            assert tracker.state.commands_since_refresh == 2
            assert tracker.state.total_commands == 2

    def test_record_refresh(self):
        """Test refresh recording."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / ".cerberus_protocol.json"
            tracker = ProtocolTracker(session_file)

            # Record some commands
            for _ in range(5):
                tracker.record_command("go")

            assert tracker.state.commands_since_refresh == 5

            # Record refresh
            tracker.record_refresh()
            assert tracker.state.commands_since_refresh == 0
            assert tracker.state.last_refresh is not None
            assert tracker.state.refresh_count == 1

    def test_should_suggest_refresh_after_commands(self):
        """Test refresh suggestion after command threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / ".cerberus_protocol.json"
            tracker = ProtocolTracker(session_file)

            # Under threshold
            for _ in range(COMMAND_THRESHOLD - 1):
                tracker.record_command("go")

            assert not tracker.should_suggest_refresh()

            # At threshold
            tracker.record_command("go")
            assert tracker.should_suggest_refresh()

    def test_should_suggest_refresh_after_time(self):
        """Test refresh suggestion after time threshold."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / ".cerberus_protocol.json"
            tracker = ProtocolTracker(session_file)

            # Simulate old session start
            tracker.state.session_start = time.time() - TIME_THRESHOLD_SECONDS - 1
            tracker._save_state()

            assert tracker.should_suggest_refresh()

    def test_should_not_suggest_after_recent_refresh(self):
        """Test no suggestion after recent refresh."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / ".cerberus_protocol.json"
            tracker = ProtocolTracker(session_file)

            # Record refresh
            tracker.record_refresh()

            # Record some commands (under threshold)
            for _ in range(5):
                tracker.record_command("go")

            assert not tracker.should_suggest_refresh()

    def test_get_refresh_reason(self):
        """Test refresh reason generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / ".cerberus_protocol.json"
            tracker = ProtocolTracker(session_file)

            # Under threshold - no reason
            assert tracker.get_refresh_reason() is None

            # Over command threshold
            for _ in range(COMMAND_THRESHOLD + 1):
                tracker.record_command("go")

            reason = tracker.get_refresh_reason()
            assert reason is not None
            assert "commands" in reason.lower()

    def test_get_status(self):
        """Test status retrieval."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / ".cerberus_protocol.json"
            tracker = ProtocolTracker(session_file)

            tracker.record_command("blueprint")
            tracker.record_command("search")

            status = tracker.get_status()
            assert "session_age_minutes" in status
            assert status["commands_since_refresh"] == 2
            assert status["total_commands"] == 2
            assert "needs_refresh" in status

    def test_state_persists_to_file(self):
        """Test that state is persisted to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / ".cerberus_protocol.json"

            # Create tracker and record commands
            tracker1 = ProtocolTracker(session_file)
            tracker1.record_command("go")
            tracker1.record_command("orient")

            # Create new tracker from same file
            tracker2 = ProtocolTracker(session_file)
            assert tracker2.state.commands_since_refresh == 2
            assert tracker2.state.total_commands == 2

    def test_reset(self):
        """Test tracker reset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            session_file = Path(tmpdir) / ".cerberus_protocol.json"
            tracker = ProtocolTracker(session_file)

            tracker.record_command("go")
            tracker.record_command("go")
            tracker.reset()

            assert tracker.state.commands_since_refresh == 0
            assert tracker.state.total_commands == 0


class TestProtocolContent:
    """Test protocol content generation."""

    def test_get_protocol_light(self):
        """Test light protocol content."""
        content = get_protocol_light()
        assert "CERBERUS PROTOCOL" in content
        assert "TOOL SELECTION" in content
        assert "FORBIDDEN" in content
        assert len(content) < 1000  # Should be short

    def test_get_protocol_rules(self):
        """Test rules protocol content."""
        content = get_protocol_rules()
        assert "TOOL SELECTION TABLE" in content
        assert "CORE RULES" in content
        assert "VIOLATION PROTOCOL" in content
        assert len(content) > len(get_protocol_light())

    def test_get_protocol_full_without_file(self):
        """Test full protocol when CERBERUS.md not found."""
        content = get_protocol_full(Path("/nonexistent/CERBERUS.md"))
        # Should fall back to rules + additional context
        assert "TOOL SELECTION" in content
        assert "CERBERUS.md not found" in content

    def test_get_protocol_json(self):
        """Test JSON protocol content."""
        data = get_protocol_json()
        assert "version" in data
        assert "tool_selection" in data
        assert "forbidden" in data
        assert "core_rules" in data
        assert data["version"] == PROTOCOL_VERSION

    def test_protocol_version_matches(self):
        """Test version is consistent across content."""
        light = get_protocol_light()
        rules = get_protocol_rules()
        json_data = get_protocol_json()

        assert PROTOCOL_VERSION in light
        assert PROTOCOL_VERSION in rules
        assert json_data["version"] == PROTOCOL_VERSION


class TestProtocolRefreshHint:
    """Test protocol refresh hint in efficiency hints."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_protocol_tracker()

    def teardown_method(self):
        """Clean up after each test."""
        reset_protocol_tracker()

    def test_hint_not_shown_when_fresh(self):
        """Test no hint when protocol is fresh."""
        hint = EfficiencyHints.check_protocol_refresh()
        assert hint is None

    def test_hint_shown_after_threshold(self):
        """Test hint shown after command threshold."""
        tracker = get_protocol_tracker()

        # Record many commands
        for _ in range(COMMAND_THRESHOLD + 1):
            tracker.record_command("go")

        hint = EfficiencyHints.check_protocol_refresh()
        assert hint is not None
        assert "cerberus refresh" in hint.command

    def test_hint_type_is_efficiency(self):
        """Test hint type is efficiency."""
        tracker = get_protocol_tracker()

        for _ in range(COMMAND_THRESHOLD + 1):
            tracker.record_command("go")

        hint = EfficiencyHints.check_protocol_refresh()
        assert hint.type == "efficiency"

    def test_hint_cleared_after_refresh(self):
        """Test hint goes away after refresh."""
        tracker = get_protocol_tracker()

        # Trigger hint
        for _ in range(COMMAND_THRESHOLD + 1):
            tracker.record_command("go")

        assert EfficiencyHints.check_protocol_refresh() is not None

        # Refresh
        tracker.record_refresh()

        # Hint should be gone
        assert EfficiencyHints.check_protocol_refresh() is None


class TestSingletonTracker:
    """Test singleton tracker behavior."""

    def setup_method(self):
        """Reset tracker before each test."""
        reset_protocol_tracker()

    def teardown_method(self):
        """Clean up after each test."""
        reset_protocol_tracker()

    def test_get_same_instance(self):
        """Test singleton returns same instance."""
        tracker1 = get_protocol_tracker()
        tracker2 = get_protocol_tracker()
        assert tracker1 is tracker2

    def test_reset_clears_singleton(self):
        """Test reset creates new instance."""
        tracker1 = get_protocol_tracker()
        tracker1.record_command("go")

        reset_protocol_tracker()

        tracker2 = get_protocol_tracker()
        # New instance should have fresh state
        assert tracker2.state.commands_since_refresh == 0
