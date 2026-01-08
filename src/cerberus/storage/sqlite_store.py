"""
SQLite-backed storage for Cerberus index.

Provides streaming queries and efficient storage for large codebases,
targeting <250 MB constant RAM usage regardless of project size.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import numpy as np

from cerberus.exceptions import IndexCorruptionError
from cerberus.logging_config import logger
from cerberus.schemas import (
    CallReference,
    CodeSymbol,
    FileObject,
    ImportLink,
    ImportReference,
    TypeInfo,
)


# SQLite schema for Cerberus index
SCHEMA_SQL = """
-- Files table
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    abs_path TEXT NOT NULL,
    size INTEGER NOT NULL,
    last_modified REAL NOT NULL,
    indexed_at REAL DEFAULT (julianday('now'))
);

CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_files_last_modified ON files(last_modified);

-- Symbols table
CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('function', 'class', 'method', 'variable', 'interface', 'enum', 'struct')),
    file_path TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    signature TEXT,
    return_type TEXT,
    parameters TEXT,  -- JSON array serialized as TEXT
    parent_class TEXT,

    FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_file_path ON symbols(file_path);
CREATE INDEX IF NOT EXISTS idx_symbols_type ON symbols(type);
CREATE INDEX IF NOT EXISTS idx_symbols_parent_class ON symbols(parent_class) WHERE parent_class IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_symbols_file_range ON symbols(file_path, start_line, end_line);

-- Embeddings metadata table (actual vectors stored in FAISS)
CREATE TABLE IF NOT EXISTS embeddings_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id INTEGER NOT NULL UNIQUE,
    faiss_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at REAL DEFAULT (julianday('now')),

    FOREIGN KEY (symbol_id) REFERENCES symbols(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_symbol_id ON embeddings_metadata(symbol_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_faiss_id ON embeddings_metadata(faiss_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_lookup ON embeddings_metadata(name, file_path);

-- Imports table
CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line INTEGER NOT NULL,

    FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_imports_file_path ON imports(file_path);
CREATE INDEX IF NOT EXISTS idx_imports_module ON imports(module);

-- Calls table
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_file TEXT NOT NULL,
    callee TEXT NOT NULL,
    line INTEGER NOT NULL,

    FOREIGN KEY (caller_file) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_calls_caller_file ON calls(caller_file);
CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee);
CREATE INDEX IF NOT EXISTS idx_calls_caller_line ON calls(caller_file, line);

-- Type infos table
CREATE TABLE IF NOT EXISTS type_infos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type_annotation TEXT,
    inferred_type TEXT,
    file_path TEXT NOT NULL,
    line INTEGER NOT NULL,

    FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_type_infos_file ON type_infos(file_path);
CREATE INDEX IF NOT EXISTS idx_type_infos_name ON type_infos(name);

-- Import links table
CREATE TABLE IF NOT EXISTS import_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    importer_file TEXT NOT NULL,
    imported_module TEXT NOT NULL,
    imported_symbols TEXT NOT NULL,  -- JSON array
    import_line INTEGER NOT NULL,
    definition_file TEXT,
    definition_symbol TEXT,

    FOREIGN KEY (importer_file) REFERENCES files(path) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_import_links_importer ON import_links(importer_file);
CREATE INDEX IF NOT EXISTS idx_import_links_module ON import_links(imported_module);
CREATE INDEX IF NOT EXISTS idx_import_links_definition ON import_links(definition_file, definition_symbol)
    WHERE definition_file IS NOT NULL;

-- Metadata table
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL DEFAULT (julianday('now'))
);

-- Initialize schema version
INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '1.0.0');
INSERT OR IGNORE INTO metadata (key, value) VALUES ('created_at', strftime('%s', 'now'));
"""


class SQLiteIndexStore:
    """
    SQLite-backed index store with streaming support.

    Replaces JSONIndexStore with a disk-first architecture that maintains
    constant memory usage regardless of project size.

    Features:
    - Streaming queries via generators (constant memory)
    - FAISS integration for vector search
    - Transactional writes with rollback support
    - Foreign key cascades for automatic cleanup
    - Backward compatibility via ScanResultAdapter

    Args:
        index_path: Path to index directory or .db file
    """

    def __init__(self, index_path: Path):
        """
        Initialize store with automatic schema creation.

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
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)  # 10 second timeout
        conn.row_factory = sqlite3.Row  # Access columns by name
        conn.execute("PRAGMA foreign_keys = ON")  # Enable cascade deletes
        conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
        conn.execute("PRAGMA busy_timeout = 10000")  # 10 second busy timeout
        return conn

    @contextmanager
    def transaction(self):
        """
        Context manager for atomic transactions.

        Usage:
            with store.transaction() as conn:
                store.write_file(file_obj, conn=conn)
                store.write_symbols_batch(symbols, conn=conn)
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
                conn.executescript(SCHEMA_SQL)
            logger.debug(f"Initialized SQLite schema at {self.db_path}")
        except Exception as e:
            raise IndexCorruptionError(f"Failed to initialize database schema: {e}")

    # ========== WRITE OPERATIONS ==========

    def write_file(self, file_obj: FileObject, conn: Optional[sqlite3.Connection] = None):
        """
        Write or update a single file record.

        Uses UPSERT (INSERT OR REPLACE) to handle both new files and updates.

        Args:
            file_obj: FileObject to write
            conn: Optional connection from transaction context
        """
        _conn = conn or self._get_connection()
        try:
            _conn.execute("""
                INSERT INTO files (path, abs_path, size, last_modified)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    abs_path=excluded.abs_path,
                    size=excluded.size,
                    last_modified=excluded.last_modified,
                    indexed_at=julianday('now')
            """, (file_obj.path, file_obj.abs_path, file_obj.size, file_obj.last_modified))

            if not conn:
                _conn.commit()
                logger.debug(f"Wrote file: {file_obj.path}")
        finally:
            if not conn:
                _conn.close()

    def write_symbols_batch(self, symbols: List[CodeSymbol], conn: Optional[sqlite3.Connection] = None, chunk_size: int = 1000):
        """
        Batch write symbols with optimized chunking for large datasets.

        Uses chunked inserts to avoid memory buildup with massive symbol counts.
        Each chunk is committed as a sub-batch for better performance.

        Args:
            symbols: List of CodeSymbol objects
            conn: Optional connection from transaction context
            chunk_size: Number of symbols per chunk (default 1000)

        Returns:
            List of symbol IDs for linking with embeddings
        """
        if not symbols:
            return []

        _conn = conn or self._get_connection()
        try:
            all_symbol_ids = []
            total_symbols = len(symbols)

            # Process in chunks to avoid memory buildup
            for chunk_start in range(0, total_symbols, chunk_size):
                chunk_end = min(chunk_start + chunk_size, total_symbols)
                chunk = symbols[chunk_start:chunk_end]

                # Insert chunk
                chunk_ids = []
                for s in chunk:
                    cursor = _conn.execute("""
                        INSERT INTO symbols (name, type, file_path, start_line, end_line,
                                           signature, return_type, parameters, parent_class)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (s.name, s.type, s.file_path, s.start_line, s.end_line,
                         s.signature, s.return_type,
                         json.dumps(s.parameters) if s.parameters else None,
                         s.parent_class))
                    chunk_ids.append(cursor.lastrowid)

                all_symbol_ids.extend(chunk_ids)

                # Log progress for large batches
                if total_symbols > chunk_size:
                    logger.debug(f"Wrote symbol chunk {chunk_start//chunk_size + 1}/{(total_symbols + chunk_size - 1)//chunk_size} ({chunk_end}/{total_symbols})")

            if not conn:
                _conn.commit()

            logger.debug(f"Wrote {total_symbols} symbols total")
            return all_symbol_ids
        finally:
            if not conn:
                _conn.close()

    def write_imports_batch(self, imports: List[ImportReference], conn: Optional[sqlite3.Connection] = None):
        """Batch write import references."""
        if not imports:
            return

        _conn = conn or self._get_connection()
        try:
            _conn.executemany("""
                INSERT INTO imports (module, file_path, line)
                VALUES (?, ?, ?)
            """, [(i.module, i.file_path, i.line) for i in imports])

            if not conn:
                _conn.commit()
                logger.debug(f"Wrote {len(imports)} imports")
        finally:
            if not conn:
                _conn.close()

    def write_calls_batch(self, calls: List[CallReference], conn: Optional[sqlite3.Connection] = None):
        """Batch write call references."""
        if not calls:
            return

        _conn = conn or self._get_connection()
        try:
            _conn.executemany("""
                INSERT INTO calls (caller_file, callee, line)
                VALUES (?, ?, ?)
            """, [(c.caller_file, c.callee, c.line) for c in calls])

            if not conn:
                _conn.commit()
                logger.debug(f"Wrote {len(calls)} calls")
        finally:
            if not conn:
                _conn.close()

    def write_type_infos_batch(self, type_infos: List[TypeInfo], conn: Optional[sqlite3.Connection] = None):
        """Batch write type information."""
        if not type_infos:
            return

        _conn = conn or self._get_connection()
        try:
            _conn.executemany("""
                INSERT INTO type_infos (name, type_annotation, inferred_type, file_path, line)
                VALUES (?, ?, ?, ?, ?)
            """, [(t.name, t.type_annotation, t.inferred_type, t.file_path, t.line)
                  for t in type_infos])

            if not conn:
                _conn.commit()
                logger.debug(f"Wrote {len(type_infos)} type_infos")
        finally:
            if not conn:
                _conn.close()

    def write_import_links_batch(self, import_links: List[ImportLink], conn: Optional[sqlite3.Connection] = None):
        """Batch write import links."""
        if not import_links:
            return

        _conn = conn or self._get_connection()
        try:
            _conn.executemany("""
                INSERT INTO import_links (importer_file, imported_module, imported_symbols,
                                        import_line, definition_file, definition_symbol)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [(il.importer_file, il.imported_module, json.dumps(il.imported_symbols),
                   il.import_line, il.definition_file, il.definition_symbol)
                  for il in import_links])

            if not conn:
                _conn.commit()
                logger.debug(f"Wrote {len(import_links)} import_links")
        finally:
            if not conn:
                _conn.close()

    def write_embedding_metadata(
        self,
        symbol_id: int,
        faiss_id: int,
        name: str,
        file_path: str,
        model: str,
        conn: Optional[sqlite3.Connection] = None
    ):
        """
        Write embedding metadata (actual vector stored in FAISS).

        Args:
            symbol_id: SQLite symbol ID
            faiss_id: FAISS vector index
            name: Symbol name
            file_path: File path
            model: Embedding model name
            conn: Optional connection from transaction context
        """
        _conn = conn or self._get_connection()
        try:
            _conn.execute("""
                INSERT INTO embeddings_metadata (symbol_id, faiss_id, name, file_path, embedding_model)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(symbol_id) DO UPDATE SET
                    faiss_id=excluded.faiss_id,
                    embedding_model=excluded.embedding_model,
                    created_at=julianday('now')
            """, (symbol_id, faiss_id, name, file_path, model))

            if not conn:
                _conn.commit()
                logger.debug(f"Wrote embedding metadata for symbol_id={symbol_id}, faiss_id={faiss_id}")
        finally:
            if not conn:
                _conn.close()

    def delete_file(self, file_path: str, conn: Optional[sqlite3.Connection] = None):
        """
        Delete file and all associated data.

        Foreign key CASCADE handles automatic cleanup of:
        - symbols
        - imports
        - calls
        - type_infos
        - import_links
        - embeddings_metadata

        Args:
            file_path: Relative file path to delete
            conn: Optional connection from transaction context

        Returns:
            List of FAISS IDs to remove from vector store
        """
        _conn = conn or self._get_connection()
        try:
            # Get FAISS IDs for cleanup before deletion
            cursor = _conn.execute("SELECT id FROM symbols WHERE file_path = ?", (file_path,))
            symbol_ids = [row[0] for row in cursor.fetchall()]

            faiss_ids = []
            if symbol_ids:
                placeholders = ','.join('?' * len(symbol_ids))
                cursor = _conn.execute(
                    f"SELECT faiss_id FROM embeddings_metadata WHERE symbol_id IN ({placeholders})",
                    symbol_ids
                )
                faiss_ids = [row[0] for row in cursor.fetchall()]

            # Delete file (CASCADE removes all related data)
            _conn.execute("DELETE FROM files WHERE path = ?", (file_path,))

            if not conn:
                _conn.commit()
                logger.info(f"Deleted file '{file_path}' and {len(symbol_ids)} associated symbols")

            return faiss_ids
        finally:
            if not conn:
                _conn.close()

    # ========== QUERY OPERATIONS (STREAMING) ==========

    def query_symbols(
        self,
        filter: Optional[Dict[str, Any]] = None,
        batch_size: int = 100
    ) -> Iterator[CodeSymbol]:
        """
        Streaming query for symbols with optional filtering.

        Yields symbols in batches to balance memory usage vs query overhead.

        Args:
            filter: Optional dict with keys: 'name', 'file_path', 'type'
            batch_size: Number of rows to fetch per iteration (default: 100)

        Yields:
            CodeSymbol objects one at a time
        """
        conn = self._get_connection()
        try:
            # Build query dynamically based on filter
            query = "SELECT * FROM symbols"
            params = []

            if filter:
                conditions = []
                if 'name' in filter:
                    conditions.append("name = ?")
                    params.append(filter['name'])
                if 'file_path' in filter:
                    conditions.append("file_path = ?")
                    params.append(filter['file_path'])
                if 'type' in filter:
                    conditions.append("type = ?")
                    params.append(filter['type'])
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

            cursor = conn.execute(query, params)

            # Yield in batches
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    yield CodeSymbol(
                        name=row['name'],
                        type=row['type'],
                        file_path=row['file_path'],
                        start_line=row['start_line'],
                        end_line=row['end_line'],
                        signature=row['signature'],
                        return_type=row['return_type'],
                        parameters=json.loads(row['parameters']) if row['parameters'] else None,
                        parent_class=row['parent_class'],
                    )
        finally:
            conn.close()

    def query_import_links(self, filter: Dict[str, Any]) -> List[ImportLink]:
        """
        Query import links (typically small result sets).

        Args:
            filter: Dict with 'importer_file' key

        Returns:
            List of ImportLink objects
        """
        conn = self._get_connection()
        try:
            query = "SELECT * FROM import_links WHERE importer_file = ?"
            cursor = conn.execute(query, (filter['importer_file'],))

            results = []
            for row in cursor:
                results.append(ImportLink(
                    importer_file=row['importer_file'],
                    imported_module=row['imported_module'],
                    imported_symbols=json.loads(row['imported_symbols']),
                    import_line=row['import_line'],
                    definition_file=row['definition_file'],
                    definition_symbol=row['definition_symbol'],
                ))

            return results
        finally:
            conn.close()

    def query_calls_by_callee(self, callee: str, batch_size: int = 100) -> Iterator[CallReference]:
        """
        Stream call references by callee (for graph traversal).

        Args:
            callee: Function/method name being called
            batch_size: Rows per iteration

        Yields:
            CallReference objects
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM calls WHERE callee = ? ORDER BY caller_file, line",
                (callee,)
            )

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    yield CallReference(
                        caller_file=row['caller_file'],
                        callee=row['callee'],
                        line=row['line']
                    )
        finally:
            conn.close()

    def find_symbol_by_line(self, file_path: str, line: int) -> Optional[CodeSymbol]:
        """
        Find symbol containing a specific line (for graph analysis).

        Returns the smallest symbol containing the line.

        Args:
            file_path: File path
            line: Line number

        Returns:
            CodeSymbol if found, None otherwise
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM symbols
                WHERE file_path = ? AND start_line <= ? AND end_line >= ?
                ORDER BY (end_line - start_line) ASC
                LIMIT 1
            """, (file_path, line, line))

            row = cursor.fetchone()
            if row:
                return CodeSymbol(
                    name=row['name'],
                    type=row['type'],
                    file_path=row['file_path'],
                    start_line=row['start_line'],
                    end_line=row['end_line'],
                    signature=row['signature'],
                    return_type=row['return_type'],
                    parameters=json.loads(row['parameters']) if row['parameters'] else None,
                    parent_class=row['parent_class'],
                )
            return None
        finally:
            conn.close()

    # ========== METADATA OPERATIONS ==========

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
