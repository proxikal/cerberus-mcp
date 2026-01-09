"""
SQLite Persistence Layer

Handles connection management, transactions, metadata, and database lifecycle.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from cerberus.logging_config import logger
from cerberus.exceptions import IndexCorruptionError
from cerberus.storage.sqlite.schema import init_schema
from cerberus.storage.sqlite.config import DEFAULT_TIMEOUT, ENABLE_WAL_MODE


class SQLitePersistence:
    """
    Manages SQLite database lifecycle, connections, and metadata.

    Responsibilities:
    - Connection creation and configuration
    - Transaction management
    - Metadata storage
    - Database statistics
    """

    def __init__(self, index_path: Path):
        """
        Initialize persistence layer with automatic schema creation.

        Args:
            index_path: Path to index directory (will create cerberus.db inside)
                       or path to .db file directly
        """
        if isinstance(index_path, str):
            index_path = Path(index_path)

        if index_path.suffix == '.db':
            self.db_path = index_path
            self.index_dir = index_path.parent
        else:
            self.index_dir = index_path
            self.db_path = index_path / "cerberus.db"

        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._init_schema()

        # FAISS store will be initialized by consumer (lazy initialization)
        self._faiss_store = None

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get database connection with optimized settings.

        Returns:
            Connection with row factory and foreign keys enabled
        """
        conn = sqlite3.connect(str(self.db_path), timeout=DEFAULT_TIMEOUT)
        conn.row_factory = sqlite3.Row  # Access columns by name
        conn.execute("PRAGMA foreign_keys = ON")  # Enable cascade deletes

        if ENABLE_WAL_MODE:
            conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency

        conn.execute(f"PRAGMA busy_timeout = {int(DEFAULT_TIMEOUT * 1000)}")
        return conn

    @contextmanager
    def transaction(self):
        """
        Context manager for atomic transactions.

        Usage:
            with persistence.transaction() as conn:
                # Perform database operations
                # Commits on success, rolls back on exception

        Yields:
            Connection object for passing to write methods
        """
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            conn.close()

    def _init_schema(self):
        """Initialize database schema if not exists."""
        try:
            with self.transaction() as conn:
                init_schema(conn, str(self.db_path))
        except Exception as e:
            raise IndexCorruptionError(f"Failed to initialize database schema: {e}")

    def get_metadata(self, key: str) -> Optional[str]:
        """Get metadata value by key."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else None
        finally:
            conn.close()

    def set_metadata(self, key: str, value: str, conn: Optional[sqlite3.Connection] = None):
        """Set metadata key-value pair."""
        _conn = conn or self._get_connection()
        try:
            _conn.execute("""
                INSERT INTO metadata (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=julianday('now')
            """, (key, value))

            if not conn:
                _conn.commit()
        finally:
            if not conn:
                _conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Dict with counts and sizes
        """
        conn = self._get_connection()
        try:
            stats = {}
            stats['total_files'] = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            stats['total_symbols'] = conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0]
            stats['total_embeddings'] = conn.execute("SELECT COUNT(*) FROM embeddings_metadata").fetchone()[0]
            stats['total_calls'] = conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
            stats['total_imports'] = conn.execute("SELECT COUNT(*) FROM imports").fetchone()[0]
            stats['total_type_infos'] = conn.execute("SELECT COUNT(*) FROM type_infos").fetchone()[0]
            stats['total_import_links'] = conn.execute("SELECT COUNT(*) FROM import_links").fetchone()[0]

            stats['db_size_bytes'] = self.db_path.stat().st_size if self.db_path.exists() else 0

            return stats
        finally:
            conn.close()

    def close(self):
        """
        Close store and persist any in-memory data.

        Currently a no-op for SQLite (writes are immediate),
        but reserved for future FAISS integration.
        """
        if self._faiss_store:
            self._faiss_store.save()
