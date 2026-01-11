"""Tests for Phase 13.5 Section 4: Background Blueprint Regeneration."""

import pytest
import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock

pytestmark = [pytest.mark.fast, pytest.mark.blueprint]

from cerberus.blueprint.cache_manager import BlueprintCache
from cerberus.blueprint.blueprint_watcher import BlueprintWatcher


class TestCacheAccessTracking:
    """Tests for cache access tracking."""

    @pytest.fixture
    def mock_conn(self):
        """Create mock SQLite connection."""
        conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (0, "cache_key", "TEXT", 0, None, 1),
            (1, "blueprint_json", "TEXT", 1, None, 0),
            (2, "access_count", "INTEGER", 0, "0", 0),
            (3, "last_accessed", "REAL", 0, "0", 0),
        ]
        conn.execute.return_value = mock_cursor
        return conn

    @pytest.fixture
    def cache(self, mock_conn):
        """Create BlueprintCache instance."""
        return BlueprintCache(mock_conn)

    def test_ensure_access_tracking_schema(self, cache, mock_conn):
        """Test access tracking schema initialization."""
        calls = [str(call) for call in mock_conn.execute.call_args_list]
        assert any("PRAGMA table_info" in str(call) for call in calls)

    def test_track_access(self, cache, mock_conn):
        """Test access tracking increments count."""
        cache._track_access("test_cache_key")

        calls = [str(call) for call in mock_conn.execute.call_args_list]
        update_calls = [c for c in calls if "UPDATE blueprint_cache" in str(c)]
        assert len(update_calls) > 0

    def test_get_hot_files(self, cache, mock_conn):
        """Test getting frequently accessed files."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("/test/hot_file1.py", 15),
            ("/test/hot_file2.py", 10),
            ("/test/hot_file3.py", 7),
        ]
        mock_conn.execute.return_value = mock_cursor

        hot_files = cache.get_hot_files(min_access_count=5, limit=10)

        assert len(hot_files) == 3
        assert hot_files[0] == ("/test/hot_file1.py", 15)
        assert hot_files[1] == ("/test/hot_file2.py", 10)

    def test_get_hot_files_respects_min_access(self, cache, mock_conn):
        """Test hot files query uses min_access_count."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.execute.return_value = mock_cursor

        cache.get_hot_files(min_access_count=10, limit=5)

        call_args = mock_conn.execute.call_args
        assert call_args is not None
        args = call_args[0]
        if len(args) > 1:
            assert 10 in args[1]


class TestBlueprintWatcher:
    """Tests for BlueprintWatcher class."""

    @pytest.fixture
    def watcher(self, tmp_path):
        """Create BlueprintWatcher instance."""
        index_path = tmp_path / "test.db"
        return BlueprintWatcher(
            index_path=index_path,
            project_root=tmp_path,
            regeneration_interval=60.0,
            min_access_count=3
        )

    def test_initialization(self, watcher, tmp_path):
        """Test BlueprintWatcher initializes correctly."""
        assert watcher.regeneration_interval == 60.0
        assert watcher.min_access_count == 3
        assert watcher.last_regeneration == 0.0
        assert len(watcher.modified_files) == 0

    def test_on_file_modified(self, watcher):
        """Test tracking file modifications."""
        watcher.on_file_modified("/test/file1.py")
        watcher.on_file_modified("/test/file2.py")
        watcher.on_file_modified("/test/file1.py")

        assert len(watcher.modified_files) == 2
        assert "/test/file1.py" in watcher.modified_files
        assert "/test/file2.py" in watcher.modified_files

    def test_should_regenerate_initial(self, watcher):
        """Test should_regenerate on first call."""
        assert watcher.should_regenerate() is True

    def test_should_regenerate_after_interval(self, watcher):
        """Test should_regenerate after interval elapsed."""
        watcher.last_regeneration = time.time() - 120
        watcher.regeneration_interval = 60

        assert watcher.should_regenerate() is True

    def test_should_regenerate_before_interval(self, watcher):
        """Test should_regenerate before interval elapsed."""
        watcher.last_regeneration = time.time() - 30
        watcher.regeneration_interval = 60

        assert watcher.should_regenerate() is False

    def test_get_stats(self, watcher):
        """Test getting watcher statistics."""
        watcher.on_file_modified("/test/file1.py")
        watcher.on_file_modified("/test/file2.py")
        watcher.last_regeneration = time.time() - 100

        stats = watcher.get_stats()

        assert stats["modified_files_count"] == 2
        assert stats["last_regeneration"] > 0
        assert stats["time_since_last_regen"] is not None
