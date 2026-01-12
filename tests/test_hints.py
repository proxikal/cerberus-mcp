"""
Tests for Phase 19.2: Efficiency Hints System

Tests for:
  - EfficiencyHints static methods
  - Hint formatting
  - HintCollector
"""

import pytest
import tempfile
from pathlib import Path

pytestmark = pytest.mark.fast
from unittest.mock import patch, MagicMock

from cerberus.cli.hints import (
    Hint,
    EfficiencyHints,
    HintCollector,
    get_hint_collector,
)


class TestHint:
    """Tests for Hint dataclass."""

    def test_hint_to_dict_basic(self):
        """Test basic hint to dict conversion."""
        hint = Hint(type="efficiency", message="Test message")
        result = hint.to_dict()
        assert result == {"type": "efficiency", "message": "Test message"}

    def test_hint_to_dict_with_alternative(self):
        """Test hint with alternative included."""
        hint = Hint(
            type="efficiency",
            message="Test message",
            alternative="Use --flag instead",
        )
        result = hint.to_dict()
        assert result["alternative"] == "Use --flag instead"

    def test_hint_to_dict_with_command(self):
        """Test hint with command included."""
        hint = Hint(
            type="memory",
            message="Test message",
            command="cerberus memory context",
        )
        result = hint.to_dict()
        assert result["command"] == "cerberus memory context"

    def test_hint_to_human_basic(self):
        """Test human-readable output."""
        hint = Hint(type="efficiency", message="Large response")
        result = hint.to_human()
        assert "Tip:" in result
        assert "Large response" in result

    def test_hint_to_human_with_command(self):
        """Test human-readable output with command suggestion."""
        hint = Hint(
            type="efficiency",
            message="Large response",
            command="read file.py lines 1-50",
        )
        result = hint.to_human()
        assert "Tip:" in result
        assert "Try:" in result
        assert "read file.py lines 1-50" in result


class TestEfficiencyHintsLargeResponse:
    """Tests for check_large_response."""

    def test_no_hint_below_threshold(self):
        """No hint when response is small."""
        hint = EfficiencyHints.check_large_response(lines=100)
        assert hint is None

    def test_no_hint_at_threshold(self):
        """No hint at exactly threshold."""
        hint = EfficiencyHints.check_large_response(lines=500)
        assert hint is None

    def test_hint_above_threshold(self):
        """Hint appears above threshold."""
        hint = EfficiencyHints.check_large_response(lines=501)
        assert hint is not None
        assert hint.type == "efficiency"
        assert "501 lines" in hint.message

    def test_no_hint_when_snippet_used(self):
        """No hint when --snippet was used."""
        hint = EfficiencyHints.check_large_response(lines=1000, used_snippet=True)
        assert hint is None

    def test_hint_includes_file_info(self):
        """Hint includes file and line information when provided."""
        hint = EfficiencyHints.check_large_response(
            lines=800,
            file_path="src/main.py",
            start_line=10,
            end_line=90,
        )
        assert hint is not None
        assert "src/main.py" in hint.message or "src/main.py" in (hint.command or "")
        assert "cerberus go" in hint.alternative


class TestEfficiencyHintsMemory:
    """Tests for check_memory_available."""

    def test_no_hint_when_with_memory_used(self):
        """No hint when --with-memory was already used."""
        hint = EfficiencyHints.check_memory_available(used_with_memory=True)
        assert hint is None

    def test_memory_check_handles_empty_gracefully(self):
        """Memory check handles empty memory gracefully."""
        # This tests the real implementation with empty memory
        # The hint should be None if no memory exists
        hint = EfficiencyHints.check_memory_available()
        # Can be None or a hint depending on actual memory state
        # Either is valid - we're testing it doesn't crash
        assert hint is None or hint.type == "memory"

    def test_memory_check_with_project(self):
        """Memory check accepts project parameter."""
        # Test that project parameter is accepted
        hint = EfficiencyHints.check_memory_available(project="test-project")
        # Can be None or a hint depending on actual memory state
        assert hint is None or hint.type == "memory"


class TestEfficiencyHintsCorrections:
    """Tests for check_corrections_available."""

    def test_no_hint_when_check_corrections_used(self):
        """No hint when --check-corrections was used."""
        hint = EfficiencyHints.check_corrections_available(used_check_corrections=True)
        assert hint is None

    def test_corrections_check_handles_empty_gracefully(self):
        """Corrections check handles empty corrections gracefully."""
        # Test with real implementation - it should handle empty state
        hint = EfficiencyHints.check_corrections_available()
        # Can be None or a hint depending on actual corrections state
        assert hint is None or hint.type == "correction"

    def test_corrections_check_with_file_path(self):
        """Corrections check accepts file_path parameter."""
        hint = EfficiencyHints.check_corrections_available(
            file_path="src/auth.py",
        )
        # Can be None or a hint depending on actual corrections state
        assert hint is None or hint.type == "correction"

    def test_corrections_check_with_symbol_name(self):
        """Corrections check accepts symbol_name parameter."""
        hint = EfficiencyHints.check_corrections_available(
            symbol_name="validate_token",
        )
        # Can be None or a hint depending on actual corrections state
        assert hint is None or hint.type == "correction"


class TestEfficiencyHintsIndexStale:
    """Tests for check_index_stale."""

    def test_hint_when_no_index(self, tmp_path, monkeypatch):
        """Hint appears when no index exists."""
        monkeypatch.chdir(tmp_path)
        hint = EfficiencyHints.check_index_stale()
        assert hint is not None
        assert "No index found" in hint.message

    def test_no_hint_when_index_fresh(self, tmp_path, monkeypatch):
        """No hint when index is fresh."""
        monkeypatch.chdir(tmp_path)

        # Create a fresh index file
        index_file = tmp_path / "cerberus.db"
        index_file.write_text("test")

        hint = EfficiencyHints.check_index_stale(
            index_path=index_file,
            threshold_minutes=60,
        )
        assert hint is None

    def test_hint_when_index_stale(self, tmp_path, monkeypatch):
        """Hint appears when index is stale."""
        import os
        import time

        monkeypatch.chdir(tmp_path)

        # Create an index file
        index_file = tmp_path / "cerberus.db"
        index_file.write_text("test")

        # Set mtime to 2 hours ago
        old_time = time.time() - (2 * 60 * 60)
        os.utime(index_file, (old_time, old_time))

        hint = EfficiencyHints.check_index_stale(
            index_path=index_file,
            threshold_minutes=60,
        )
        assert hint is not None
        assert "minutes old" in hint.message


class TestHintCollector:
    """Tests for HintCollector."""

    def test_empty_collector(self):
        """Empty collector has no hints."""
        collector = HintCollector()
        assert not collector.has_hints()
        assert collector.to_dict() == []
        assert collector.format_human() == ""

    def test_add_none(self):
        """Adding None does not add a hint."""
        collector = HintCollector()
        collector.add(None)
        assert not collector.has_hints()

    def test_add_hint(self):
        """Adding a hint works correctly."""
        collector = HintCollector()
        collector.add(Hint(type="test", message="Test message"))
        assert collector.has_hints()
        assert len(collector.to_dict()) == 1

    def test_multiple_hints(self):
        """Multiple hints are collected."""
        collector = HintCollector()
        collector.add(Hint(type="test1", message="Message 1"))
        collector.add(Hint(type="test2", message="Message 2"))
        assert len(collector.to_dict()) == 2

    def test_inject_into_json(self):
        """Hints are injected into JSON output."""
        collector = HintCollector()
        collector.add(Hint(type="test", message="Test"))

        output = {"data": "value"}
        result = collector.inject_into_json(output)

        assert "hints" in result
        assert len(result["hints"]) == 1
        assert result["data"] == "value"

    def test_inject_into_json_no_hints(self):
        """No hints key when empty."""
        collector = HintCollector()

        output = {"data": "value"}
        result = collector.inject_into_json(output)

        assert "hints" not in result
        assert result["data"] == "value"

    def test_format_human_output(self):
        """Human format works correctly."""
        collector = HintCollector()
        collector.add(Hint(type="test", message="Test message"))
        result = collector.format_human()

        assert "Tip:" in result
        assert "Test message" in result


class TestGetHintCollector:
    """Tests for get_hint_collector factory."""

    def test_returns_new_instance(self):
        """Factory returns new instance each time."""
        c1 = get_hint_collector()
        c2 = get_hint_collector()
        assert c1 is not c2

    def test_returns_hint_collector(self):
        """Factory returns HintCollector instance."""
        collector = get_hint_collector()
        assert isinstance(collector, HintCollector)
