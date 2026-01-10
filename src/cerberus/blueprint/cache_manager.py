"""Blueprint cache manager for performance optimization.

Phase 13.1: Mtime-based caching with TTL and invalidation.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
import sqlite3

from cerberus.logging_config import logger
from .schemas import Blueprint


class BlueprintCache:
    """Manages blueprint caching with TTL and invalidation."""

    DEFAULT_TTL = 3600  # 1 hour in seconds

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize cache manager.

        Args:
            conn: SQLite connection to database with blueprint_cache table
        """
        self.conn = conn
        # Phase 13.4: Track cache hit rate
        self._cache_hits = 0
        self._cache_misses = 0

    def get(self, file_path: str, flags: Dict[str, Any]) -> Optional[Blueprint]:
        """
        Retrieve cached blueprint if valid.

        Args:
            file_path: Absolute file path
            flags: Dictionary of flags (deps, meta, etc.)

        Returns:
            Blueprint object if cache hit and valid, None otherwise
        """
        try:
            # Get file mtime
            path = Path(file_path)
            if not path.exists():
                self._cache_misses += 1
                return None

            mtime = path.stat().st_mtime

            # Generate cache key
            cache_key = self._generate_cache_key(file_path, mtime, flags)

            # Query cache
            cursor = self.conn.execute(
                """
                SELECT blueprint_json, expires_at
                FROM blueprint_cache
                WHERE cache_key = ?
                """,
                (cache_key,)
            )
            row = cursor.fetchone()

            if not row:
                logger.debug(f"Blueprint cache miss: {file_path}")
                self._cache_misses += 1
                return None

            blueprint_json, expires_at = row

            # Check expiration
            current_time = time.time()
            if current_time > expires_at:
                logger.debug(f"Blueprint cache expired: {file_path}")
                # Clean up expired entry
                self.conn.execute(
                    "DELETE FROM blueprint_cache WHERE cache_key = ?",
                    (cache_key,)
                )
                self.conn.commit()
                self._cache_misses += 1
                return None

            # Deserialize and return
            data = json.loads(blueprint_json)
            blueprint = Blueprint(**data)
            blueprint.cached = True
            logger.debug(f"Blueprint cache hit: {file_path}")
            self._cache_hits += 1
            return blueprint

        except Exception as e:
            logger.warning(f"Error reading blueprint cache: {e}")
            self._cache_misses += 1
            return None

    def set(
        self,
        file_path: str,
        flags: Dict[str, Any],
        blueprint: Blueprint,
        ttl: int = None
    ) -> None:
        """
        Store blueprint in cache with TTL.

        Args:
            file_path: Absolute file path
            flags: Dictionary of flags used to generate blueprint
            blueprint: Blueprint object to cache
            ttl: Time-to-live in seconds (default: 1 hour)
        """
        try:
            ttl = ttl or self.DEFAULT_TTL

            # Get file mtime
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"Cannot cache blueprint for non-existent file: {file_path}")
                return

            mtime = path.stat().st_mtime

            # Generate cache key
            cache_key = self._generate_cache_key(file_path, mtime, flags)

            # Calculate expiration
            current_time = time.time()
            expires_at = current_time + ttl

            # Serialize blueprint
            blueprint.cached = False  # Reset cached flag before storing
            blueprint_json = blueprint.model_dump_json()

            # Store in database
            self.conn.execute(
                """
                INSERT OR REPLACE INTO blueprint_cache
                (cache_key, blueprint_json, expires_at, file_path)
                VALUES (?, ?, ?, ?)
                """,
                (cache_key, blueprint_json, expires_at, file_path)
            )
            self.conn.commit()
            logger.debug(f"Cached blueprint: {file_path} (expires in {ttl}s)")

        except Exception as e:
            logger.warning(f"Error caching blueprint: {e}")

    def invalidate(self, file_path: str) -> None:
        """
        Invalidate all cached blueprints for a file.

        Args:
            file_path: Absolute file path
        """
        try:
            # Delete all cache entries for this file (regardless of flags/mtime)
            cursor = self.conn.execute(
                "DELETE FROM blueprint_cache WHERE file_path = ?",
                (file_path,)
            )
            deleted = cursor.rowcount
            self.conn.commit()

            if deleted > 0:
                logger.debug(f"Invalidated {deleted} cached blueprint(s) for: {file_path}")

        except Exception as e:
            logger.warning(f"Error invalidating blueprint cache: {e}")

    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        try:
            current_time = time.time()
            cursor = self.conn.execute(
                "DELETE FROM blueprint_cache WHERE expires_at < ?",
                (current_time,)
            )
            deleted = cursor.rowcount
            self.conn.commit()

            if deleted > 0:
                logger.debug(f"Cleaned up {deleted} expired blueprint cache entries")

            return deleted

        except Exception as e:
            logger.warning(f"Error cleaning up blueprint cache: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache metrics
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN expires_at > ? THEN 1 ELSE 0 END) as valid,
                    SUM(CASE WHEN expires_at <= ? THEN 1 ELSE 0 END) as expired
                FROM blueprint_cache
                """,
                (time.time(), time.time())
            )
            row = cursor.fetchone()
            total, valid, expired = row

            # Phase 13.4: Calculate cache hit rate
            total_requests = self._cache_hits + self._cache_misses
            hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0

            return {
                "total_entries": total or 0,
                "valid_entries": valid or 0,
                "expired_entries": expired or 0,
                "cache_hits": self._cache_hits,
                "cache_misses": self._cache_misses,
                "hit_rate_percent": round(hit_rate, 1)
            }

        except Exception as e:
            logger.warning(f"Error getting blueprint cache stats: {e}")
            return {"total_entries": 0, "valid_entries": 0, "expired_entries": 0}

    @staticmethod
    def _generate_cache_key(file_path: str, mtime: float, flags: Dict[str, Any]) -> str:
        """
        Generate cache key from file path, mtime, and flags.

        Args:
            file_path: Absolute file path
            mtime: File modification time
            flags: Dictionary of flags

        Returns:
            Cache key string
        """
        # Sort flags for consistent hashing
        flags_str = json.dumps(sorted(flags.items()), sort_keys=True)

        # Hash flags for compact key
        flags_hash = hashlib.md5(flags_str.encode()).hexdigest()[:8]

        # Format: filepath:mtime:flagshash
        cache_key = f"{file_path}:{mtime:.6f}:{flags_hash}"

        return cache_key
