"""
SQLite Symbols Operations

Handles CRUD operations for files, symbols, and embeddings metadata.
"""

import json
import sqlite3
from typing import Any, Dict, Iterator, List, Optional

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol, FileObject
from cerberus.storage.sqlite.config import DEFAULT_CHUNK_SIZE, DEFAULT_BATCH_SIZE


class SQLiteSymbolsOperations:
    """
    Symbol and file CRUD operations.

    Handles writing and querying files, symbols, and embedding metadata.
    All methods accept an optional connection for transaction support.
    """

    def __init__(self, get_connection_func):
        """
        Initialize with a connection factory function.

        Args:
            get_connection_func: Callable that returns a new SQLite connection
        """
        self._get_connection = get_connection_func

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

    def write_symbols_batch(
        self,
        symbols: List[CodeSymbol],
        conn: Optional[sqlite3.Connection] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE
    ) -> List[int]:
        """
        Batch write symbols with optimized chunking for large datasets.

        Uses chunked inserts to avoid memory buildup with massive symbol counts.
        Each chunk is committed as a sub-batch for better performance.

        Args:
            symbols: List of CodeSymbol objects
            conn: Optional connection from transaction context
            chunk_size: Number of symbols per chunk

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
                                           signature, return_type, parameters, parameter_types, parent_class)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (s.name, s.type, s.file_path, s.start_line, s.end_line,
                         s.signature, s.return_type,
                         json.dumps(s.parameters) if s.parameters else None,
                         json.dumps(s.parameter_types) if s.parameter_types else None,
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

    def delete_file(self, file_path: str, conn: Optional[sqlite3.Connection] = None) -> List[int]:
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

    def query_symbols(
        self,
        filter: Optional[Dict[str, Any]] = None,
        batch_size: int = DEFAULT_BATCH_SIZE
    ) -> Iterator[CodeSymbol]:
        """
        Streaming query for symbols with optional filtering.

        Yields symbols in batches to balance memory usage vs query overhead.

        Args:
            filter: Optional dict with keys: 'name', 'file_path', 'type'
            batch_size: Number of rows to fetch per iteration

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
                        parameter_types=json.loads(row['parameter_types']) if row['parameter_types'] else None,
                        parent_class=row['parent_class'],
                    )
        finally:
            conn.close()

    def fts5_search(
        self,
        query: str,
        top_k: int = 20,
        batch_size: int = DEFAULT_BATCH_SIZE
    ) -> Iterator[tuple[CodeSymbol, float]]:
        """
        Phase 7: FTS5-based keyword search with zero RAM overhead.

        Uses SQLite's native full-text search engine to rank results by BM25
        without loading all symbols into memory. Offloads scoring to SQLite's
        C-engine for maximum performance.

        Args:
            query: Search query (supports FTS5 syntax like "function AND parse")
            top_k: Maximum number of results to return
            batch_size: Rows per fetch iteration

        Yields:
            Tuples of (CodeSymbol, relevance_score) ordered by relevance
        """
        conn = self._get_connection()
        try:
            # FTS5 query with BM25 ranking
            # The bm25() function returns negative scores (more negative = better match)
            # We negate it to get positive scores (higher = better)
            fts_query = """
                SELECT
                    s.id, s.name, s.type, s.file_path, s.start_line, s.end_line,
                    s.signature, s.return_type, s.parameters, s.parameter_types, s.parent_class,
                    -fts.rank as score
                FROM symbols_fts fts
                JOIN symbols s ON s.id = fts.rowid
                WHERE symbols_fts MATCH ?
                ORDER BY fts.rank
                LIMIT ?
            """

            cursor = conn.execute(fts_query, (query, top_k))

            # Yield in batches
            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    symbol = CodeSymbol(
                        name=row['name'],
                        type=row['type'],
                        file_path=row['file_path'],
                        start_line=row['start_line'],
                        end_line=row['end_line'],
                        signature=row['signature'],
                        return_type=row['return_type'],
                        parameters=json.loads(row['parameters']) if row['parameters'] else None,
                        parameter_types=json.loads(row['parameter_types']) if row['parameter_types'] else None,
                        parent_class=row['parent_class'],
                    )
                    # Normalize score to 0-1 range (FTS5 scores are typically 0-10)
                    normalized_score = min(row['score'] / 10.0, 1.0)
                    yield (symbol, normalized_score)

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
                    parameter_types=json.loads(row['parameter_types']) if row['parameter_types'] else None,
                    parent_class=row['parent_class'],
                )
            return None
        finally:
            conn.close()
