"""
SQLite Resolution Operations

Handles Phase 5/6 symbolic intelligence operations including method calls,
symbol references, type info, import links, and call references.
"""

import json
import sqlite3
from typing import Any, Dict, Iterator, List, Optional

from cerberus.logging_config import logger
from cerberus.schemas import (
    CallReference,
    ImportLink,
    ImportReference,
    MethodCall,
    SymbolReference,
    TypeInfo,
)
from cerberus.storage.sqlite.config import DEFAULT_BATCH_SIZE


class SQLiteResolutionOperations:
    """
    Phase 5/6 resolution operations.

    Handles writing and querying symbolic intelligence data including:
    - Import references and links
    - Function call references
    - Method calls with receiver tracking
    - Type information
    - Symbol references with confidence scores
    """

    def __init__(self, get_connection_func):
        """
        Initialize with a connection factory function.

        Args:
            get_connection_func: Callable that returns a new SQLite connection
        """
        self._get_connection = get_connection_func

    # ========== WRITE OPERATIONS ==========

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

    def write_method_calls_batch(self, method_calls: List[MethodCall], conn: Optional[sqlite3.Connection] = None):
        """
        Batch write method calls (Phase 5.1).

        Args:
            method_calls: List of MethodCall objects
            conn: Optional connection from transaction context
        """
        if not method_calls:
            return

        _conn = conn or self._get_connection()
        try:
            _conn.executemany("""
                INSERT INTO method_calls (caller_file, line, receiver, method, receiver_type)
                VALUES (?, ?, ?, ?, ?)
            """, [(mc.caller_file, mc.line, mc.receiver, mc.method, mc.receiver_type)
                  for mc in method_calls])

            if not conn:
                _conn.commit()
                logger.debug(f"Wrote {len(method_calls)} method_calls")
        finally:
            if not conn:
                _conn.close()

    def write_symbol_references_batch(self, refs: List[SymbolReference], conn: Optional[sqlite3.Connection] = None):
        """
        Batch write symbol references (Phase 5.2+).

        Args:
            refs: List of SymbolReference objects
            conn: Optional connection from transaction context
        """
        if not refs:
            return

        _conn = conn or self._get_connection()
        try:
            _conn.executemany("""
                INSERT INTO symbol_references (source_file, source_line, source_symbol,
                                              reference_type, target_file, target_symbol,
                                              target_type, confidence, resolution_method)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [(ref.source_file, ref.source_line, ref.source_symbol,
                   ref.reference_type, ref.target_file, ref.target_symbol,
                   ref.target_type, ref.confidence, ref.resolution_method)
                  for ref in refs])

            if not conn:
                _conn.commit()
                logger.debug(f"Wrote {len(refs)} symbol_references")
        finally:
            if not conn:
                _conn.close()

    # ========== QUERY OPERATIONS ==========

    def query_import_links(
        self,
        filter: Optional[Dict[str, Any]] = None,
        batch_size: int = DEFAULT_BATCH_SIZE
    ) -> Iterator[ImportLink]:
        """
        Stream import links with optional filtering.

        Phase 5.2: Updated to support streaming all import links for resolution.

        Args:
            filter: Optional dict with 'importer_file' key for filtering
            batch_size: Rows per iteration (for streaming)

        Yields:
            ImportLink objects
        """
        conn = self._get_connection()
        try:
            if filter and 'importer_file' in filter:
                query = "SELECT * FROM import_links WHERE importer_file = ?"
                params = (filter['importer_file'],)
            else:
                # Query all import links (for resolution)
                query = "SELECT * FROM import_links"
                params = ()

            cursor = conn.execute(query, params)

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    yield ImportLink(
                        importer_file=row['importer_file'],
                        imported_module=row['imported_module'],
                        imported_symbols=json.loads(row['imported_symbols']),
                        import_line=row['import_line'],
                        definition_file=row['definition_file'],
                        definition_symbol=row['definition_symbol'],
                    )
        finally:
            conn.close()

    def query_calls_by_callee(self, callee: str, batch_size: int = DEFAULT_BATCH_SIZE) -> Iterator[CallReference]:
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

    def query_method_calls(self, batch_size: int = DEFAULT_BATCH_SIZE) -> Iterator[MethodCall]:
        """
        Stream all method calls (Phase 5.3).

        Args:
            batch_size: Rows per iteration

        Yields:
            MethodCall objects
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM method_calls ORDER BY caller_file, line")

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    yield MethodCall(
                        caller_file=row['caller_file'],
                        line=row['line'],
                        receiver=row['receiver'],
                        method=row['method'],
                        receiver_type=row['receiver_type'],
                    )
        finally:
            conn.close()

    def query_type_infos(self, batch_size: int = DEFAULT_BATCH_SIZE) -> Iterator[TypeInfo]:
        """
        Stream all type infos (Phase 5.3).

        Args:
            batch_size: Rows per iteration

        Yields:
            TypeInfo objects
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT * FROM type_infos ORDER BY file_path, line")

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    yield TypeInfo(
                        name=row['name'],
                        type_annotation=row['type_annotation'],
                        inferred_type=row['inferred_type'],
                        file_path=row['file_path'],
                        line=row['line'],
                    )
        finally:
            conn.close()

    def query_symbol_references(self, batch_size: int = DEFAULT_BATCH_SIZE) -> Iterator[SymbolReference]:
        """
        Stream all symbol references (Phase 5.3).

        Args:
            batch_size: Rows per iteration

        Yields:
            SymbolReference objects
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("""
                SELECT * FROM symbol_references
                ORDER BY source_file, source_line
            """)

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    yield SymbolReference(
                        source_file=row['source_file'],
                        source_line=row['source_line'],
                        source_symbol=row['source_symbol'],
                        reference_type=row['reference_type'],
                        target_file=row['target_file'],
                        target_symbol=row['target_symbol'],
                        target_type=row['target_type'],
                        confidence=row['confidence'],
                        resolution_method=row['resolution_method'],
                    )
        finally:
            conn.close()

    def query_method_calls_filtered(
        self,
        method: Optional[str] = None,
        receiver: Optional[str] = None,
        receiver_type: Optional[str] = None,
        file_path: Optional[str] = None,
        batch_size: int = DEFAULT_BATCH_SIZE
    ) -> Iterator[MethodCall]:
        """
        Stream method calls with optional filtering (Phase 5 CLI support).

        Args:
            method: Filter by method name
            receiver: Filter by receiver variable name
            receiver_type: Filter by resolved receiver type
            file_path: Filter by caller file path
            batch_size: Rows per iteration

        Yields:
            MethodCall objects matching filters
        """
        conn = self._get_connection()
        try:
            # Build dynamic query
            conditions = []
            params = []

            if method:
                conditions.append("method = ?")
                params.append(method)
            if receiver:
                conditions.append("receiver = ?")
                params.append(receiver)
            if receiver_type:
                conditions.append("receiver_type = ?")
                params.append(receiver_type)
            if file_path:
                conditions.append("caller_file = ?")
                params.append(file_path)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"SELECT * FROM method_calls WHERE {where_clause} ORDER BY caller_file, line"

            cursor = conn.execute(query, tuple(params))

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    yield MethodCall(
                        caller_file=row['caller_file'],
                        line=row['line'],
                        receiver=row['receiver'],
                        method=row['method'],
                        receiver_type=row['receiver_type'],
                    )
        finally:
            conn.close()

    def query_symbol_references_filtered(
        self,
        source_symbol: Optional[str] = None,
        target_symbol: Optional[str] = None,
        reference_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        source_file: Optional[str] = None,
        target_file: Optional[str] = None,
        batch_size: int = DEFAULT_BATCH_SIZE
    ) -> Iterator[SymbolReference]:
        """
        Stream symbol references with optional filtering (Phase 5 CLI support).

        Args:
            source_symbol: Filter by source symbol name
            target_symbol: Filter by target symbol name
            reference_type: Filter by reference type (method_call, instance_of, etc.)
            min_confidence: Filter by minimum confidence score
            source_file: Filter by source file path
            target_file: Filter by target file path
            batch_size: Rows per iteration

        Yields:
            SymbolReference objects matching filters
        """
        conn = self._get_connection()
        try:
            # Build dynamic query
            conditions = []
            params = []

            if source_symbol:
                conditions.append("source_symbol = ?")
                params.append(source_symbol)
            if target_symbol:
                conditions.append("target_symbol = ?")
                params.append(target_symbol)
            if reference_type:
                conditions.append("reference_type = ?")
                params.append(reference_type)
            if min_confidence is not None:
                conditions.append("confidence >= ?")
                params.append(min_confidence)
            if source_file:
                conditions.append("source_file = ?")
                params.append(source_file)
            if target_file:
                conditions.append("target_file = ?")
                params.append(target_file)

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            query = f"SELECT * FROM symbol_references WHERE {where_clause} ORDER BY source_file, source_line"

            cursor = conn.execute(query, tuple(params))

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                for row in rows:
                    yield SymbolReference(
                        source_file=row['source_file'],
                        source_line=row['source_line'],
                        source_symbol=row['source_symbol'],
                        reference_type=row['reference_type'],
                        target_file=row['target_file'],
                        target_symbol=row['target_symbol'],
                        target_type=row['target_type'],
                        confidence=row['confidence'],
                        resolution_method=row['resolution_method'],
                    )
        finally:
            conn.close()
