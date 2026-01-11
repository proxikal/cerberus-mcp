"""
Unit and integration tests for Phase 13.4: Watcher Integration & Cache Metrics

Tests:
- Blueprint cache invalidation on file changes
- Cache hit rate tracking (hits, misses, hit rate percentage)
- Watcher health --blueprints command
"""

import pytest
import sqlite3
import tempfile
import time
import sys
from pathlib import Path

pytestmark = [pytest.mark.fast, pytest.mark.blueprint]
from unittest.mock import Mock, patch, MagicMock

from cerberus.blueprint.cache_manager import BlueprintCache
from cerberus.blueprint.schemas import Blueprint
from cerberus.schemas import FileChange, ModifiedFile

# Mock watchdog module to avoid import errors
sys.modules['watchdog'] = MagicMock()
sys.modules['watchdog.observers'] = MagicMock()
sys.modules['watchdog.events'] = MagicMock()


class TestBlueprintCacheHitRateTracking:
    """Test cache hit rate tracking functionality."""

    @pytest.fixture
    def cache(self):
        """Create an in-memory cache for testing."""
        conn = sqlite3.connect(":memory:")
        # Create blueprint_cache table
        conn.execute("""
            CREATE TABLE blueprint_cache (
                cache_key TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                blueprint_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
        """)
        conn.commit()
        return BlueprintCache(conn)

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def test_func():\n    pass\n")
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def insert_cached_blueprint(self, cache, temp_file, flags=None, ttl=3600):
        """Helper to insert a blueprint into cache with correct mtime."""
        import json
        import hashlib

        if flags is None:
            flags = {}

        # Get file mtime
        mtime = temp_file.stat().st_mtime

        # Generate cache key matching what the cache manager would generate
        flags_str = json.dumps(sorted(flags.items()), sort_keys=True)
        flags_hash = hashlib.md5(flags_str.encode()).hexdigest()[:8]
        cache_key = f"{temp_file}:{mtime:.6f}:{flags_hash}"

        # Create a blueprint
        blueprint = Blueprint(
            file_path=str(temp_file),
            nodes=[],
            total_symbols=0,
            cached=False
        )

        # Insert directly into cache with correct mtime
        cache.conn.execute("""
            INSERT INTO blueprint_cache
            (cache_key, file_path, blueprint_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (cache_key, str(temp_file), blueprint.model_dump_json(), time.time(), time.time() + ttl))
        cache.conn.commit()

    def test_initial_counters_are_zero(self, cache):
        """Test that hit/miss counters start at zero."""
        assert cache._cache_hits == 0
        assert cache._cache_misses == 0

    def test_cache_miss_increments_counter(self, cache, temp_file):
        """Test that cache miss increments the miss counter."""
        # Get from empty cache (miss)
        result = cache.get(str(temp_file), {})

        assert result is None
        assert cache._cache_misses == 1
        assert cache._cache_hits == 0

    def test_cache_hit_increments_counter(self, cache, temp_file):
        """Test that cache hit increments the hit counter."""
        # Insert cached blueprint
        self.insert_cached_blueprint(cache, temp_file)

        # Get it (should be a hit)
        result = cache.get(str(temp_file), {})

        assert result is not None
        assert cache._cache_hits == 1
        assert cache._cache_misses == 0

    def test_cache_expired_increments_miss_counter(self, cache, temp_file):
        """Test that expired cache entry counts as a miss."""
        # Insert with expired TTL
        self.insert_cached_blueprint(cache, temp_file, ttl=-1)

        # Get it (should be expired/miss)
        result = cache.get(str(temp_file), {})

        assert result is None
        assert cache._cache_misses == 1
        assert cache._cache_hits == 0

    def test_multiple_hits_and_misses(self, cache, temp_file):
        """Test tracking multiple hits and misses."""
        # Miss
        cache.get(str(temp_file), {})
        assert cache._cache_misses == 1

        # Cache it
        self.insert_cached_blueprint(cache, temp_file)

        # Hit
        cache.get(str(temp_file), {})
        assert cache._cache_hits == 1

        # Hit again
        cache.get(str(temp_file), {})
        assert cache._cache_hits == 2

        # Miss with different flags
        cache.get(str(temp_file), {"deps": True})
        assert cache._cache_misses == 2

        # Final counts
        assert cache._cache_hits == 2
        assert cache._cache_misses == 2

    def test_get_stats_includes_hit_rate(self, cache, temp_file):
        """Test that get_stats includes hit rate metrics."""
        # Generate some hits and misses
        cache.get(str(temp_file), {})  # Miss
        self.insert_cached_blueprint(cache, temp_file)
        cache.get(str(temp_file), {})  # Hit
        cache.get(str(temp_file), {})  # Hit
        cache.get(str(temp_file), {"deps": True})  # Miss

        stats = cache.get_stats()

        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "hit_rate_percent" in stats
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 2
        assert stats["hit_rate_percent"] == 50.0

    def test_hit_rate_calculation_zero_requests(self, cache):
        """Test hit rate is 0.0 when no requests made."""
        stats = cache.get_stats()

        assert stats["hit_rate_percent"] == 0.0

    def test_hit_rate_calculation_100_percent(self, cache, temp_file):
        """Test hit rate is 100% with all hits."""
        self.insert_cached_blueprint(cache, temp_file)

        # 3 hits, 0 misses
        cache.get(str(temp_file), {})
        cache.get(str(temp_file), {})
        cache.get(str(temp_file), {})

        stats = cache.get_stats()
        assert stats["hit_rate_percent"] == 100.0

    def test_hit_rate_calculation_rounding(self, cache, temp_file):
        """Test hit rate is rounded to 1 decimal place."""
        self.insert_cached_blueprint(cache, temp_file)

        # 2 hits, 1 miss = 66.666...%
        cache.get(str(temp_file), {})  # Hit
        cache.get(str(temp_file), {})  # Hit
        cache.get(str(temp_file), {"deps": True})  # Miss

        stats = cache.get_stats()
        assert stats["hit_rate_percent"] == 66.7

    def test_error_during_get_increments_miss(self, cache):
        """Test that errors during get increment miss counter."""
        # Try to get from non-existent file
        result = cache.get("/nonexistent/file.py", {})

        assert result is None
        assert cache._cache_misses == 1


class TestCacheInvalidationIntegration:
    """Test cache invalidation when files change."""

    @pytest.fixture
    def mock_index_path(self):
        """Create a mock index database."""
        conn = sqlite3.connect(":memory:")
        # Create blueprint_cache table
        conn.execute("""
            CREATE TABLE blueprint_cache (
                cache_key TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                blueprint_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
        """)
        conn.commit()

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = Path(f.name)

        # Save to temp file
        backup_conn = sqlite3.connect(str(db_path))
        conn.backup(backup_conn)
        backup_conn.close()
        conn.close()

        yield db_path

        # Cleanup
        if db_path.exists():
            db_path.unlink()

    def test_invalidate_removes_all_cache_entries_for_file(self, mock_index_path):
        """Test that invalidate removes all cached blueprints for a file."""
        conn = sqlite3.connect(str(mock_index_path))
        cache = BlueprintCache(conn)

        # Insert multiple cache entries for same file with different flags
        file_path = "/test/file.py"

        conn.execute("""
            INSERT INTO blueprint_cache
            (cache_key, file_path, blueprint_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("key1", file_path, "{}", time.time(), time.time() + 3600))

        conn.execute("""
            INSERT INTO blueprint_cache
            (cache_key, file_path, blueprint_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("key2", file_path, "{}", time.time(), time.time() + 3600))

        conn.commit()

        # Verify entries exist
        cursor = conn.execute("SELECT COUNT(*) FROM blueprint_cache WHERE file_path = ?", (file_path,))
        assert cursor.fetchone()[0] == 2

        # Invalidate
        cache.invalidate(file_path)

        # Verify entries removed
        cursor = conn.execute("SELECT COUNT(*) FROM blueprint_cache WHERE file_path = ?", (file_path,))
        assert cursor.fetchone()[0] == 0

        conn.close()

    def test_cache_invalidation_logic(self):
        """Test the cache invalidation logic when file changes are detected."""
        # This is a simpler unit test that directly tests the invalidation logic
        # without needing the full CerberusEventHandler

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            index_path = project_path / "test.db"

            # Create index database with cache table
            conn = sqlite3.connect(str(index_path))
            conn.execute("""
                CREATE TABLE blueprint_cache (
                    cache_key TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    blueprint_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)

            # Add cache entries for multiple files
            test_file = project_path / "test.py"
            test_file.write_text("def test(): pass")

            conn.execute("""
                INSERT INTO blueprint_cache
                (cache_key, file_path, blueprint_json, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, ("testkey", str(test_file), "{}", time.time(), time.time() + 3600))
            conn.commit()

            # Verify cache entry exists
            cursor = conn.execute("SELECT COUNT(*) FROM blueprint_cache WHERE file_path = ?", (str(test_file),))
            assert cursor.fetchone()[0] == 1

            # Simulate cache invalidation (what check_and_update does)
            from cerberus.blueprint.cache_manager import BlueprintCache
            cache = BlueprintCache(conn)
            cache.invalidate(str(test_file))

            # Verify cache was invalidated
            cursor = conn.execute("SELECT COUNT(*) FROM blueprint_cache WHERE file_path = ?", (str(test_file),))
            assert cursor.fetchone()[0] == 0

            conn.close()


class TestWatcherHealthBlueprints:
    """Test watcher health --blueprints command integration."""

    def test_blueprint_stats_structure(self):
        """Test that blueprint stats have the correct structure."""
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE blueprint_cache (
                cache_key TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                blueprint_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
        """)
        conn.commit()

        cache = BlueprintCache(conn)
        stats = cache.get_stats()

        # Verify all required keys exist
        assert "total_entries" in stats
        assert "valid_entries" in stats
        assert "expired_entries" in stats
        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "hit_rate_percent" in stats

        # Verify types
        assert isinstance(stats["total_entries"], int)
        assert isinstance(stats["valid_entries"], int)
        assert isinstance(stats["expired_entries"], int)
        assert isinstance(stats["cache_hits"], int)
        assert isinstance(stats["cache_misses"], int)
        assert isinstance(stats["hit_rate_percent"], (int, float))

        conn.close()

    def test_expired_entries_counted_correctly(self):
        """Test that expired entries are counted separately."""
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE blueprint_cache (
                cache_key TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                blueprint_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
        """)

        current_time = time.time()

        # Insert valid entry
        conn.execute("""
            INSERT INTO blueprint_cache
            (cache_key, file_path, blueprint_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("valid", "/test/valid.py", "{}", current_time, current_time + 3600))

        # Insert expired entry
        conn.execute("""
            INSERT INTO blueprint_cache
            (cache_key, file_path, blueprint_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, ("expired", "/test/expired.py", "{}", current_time - 7200, current_time - 3600))

        conn.commit()

        cache = BlueprintCache(conn)
        stats = cache.get_stats()

        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 1
        assert stats["expired_entries"] == 1

        conn.close()

    def test_stats_with_no_entries(self):
        """Test stats when cache is empty."""
        conn = sqlite3.connect(":memory:")
        conn.execute("""
            CREATE TABLE blueprint_cache (
                cache_key TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                blueprint_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL
            )
        """)
        conn.commit()

        cache = BlueprintCache(conn)
        stats = cache.get_stats()

        assert stats["total_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["expired_entries"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["hit_rate_percent"] == 0.0

        conn.close()


class TestCacheInvalidationErrorHandling:
    """Test error handling in cache invalidation."""

    def test_cache_invalidation_handles_missing_table_gracefully(self):
        """Test that cache invalidation handles missing table gracefully."""
        # Create database without blueprint_cache table
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE dummy (id INTEGER)")

        from cerberus.blueprint.cache_manager import BlueprintCache
        cache = BlueprintCache(conn)

        # Should not crash when trying to invalidate on missing table
        # The invalidate method logs a warning and continues
        try:
            cache.invalidate("/some/file.py")
            # Should not raise exception
        except Exception as e:
            pytest.fail(f"Cache invalidation raised exception: {e}")

        conn.close()

    def test_get_stats_handles_database_errors(self):
        """Test that get_stats handles database errors gracefully."""
        conn = sqlite3.connect(":memory:")
        # Don't create the blueprint_cache table

        cache = BlueprintCache(conn)
        stats = cache.get_stats()

        # Should return default values on error
        assert stats["total_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["expired_entries"] == 0

        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
