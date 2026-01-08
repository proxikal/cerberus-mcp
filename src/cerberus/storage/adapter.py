"""
Backward compatibility adapter for SQLite storage.

Provides a ScanResult-like interface that lazily loads data from SQLite,
allowing existing consumers to work without modification while achieving
streaming memory efficiency.
"""

import json
from typing import Any, Dict, List, Optional

from cerberus.logging_config import logger
from cerberus.schemas import (
    CallReference,
    CodeSymbol,
    FileObject,
    ImportLink,
    ImportReference,
    SymbolEmbedding,
    TypeInfo,
)
from .sqlite_store import SQLiteIndexStore


class ScanResultAdapter:
    """
    Adapter to make SQLiteIndexStore compatible with ScanResult API.

    Provides lazy loading with caching for properties. The first access
    to each property loads the full dataset from SQLite and caches it.

    This maintains backward compatibility while allowing gradual migration
    to streaming queries where beneficial.

    Memory Behavior:
    - Before access: ~0 MB (only store reference)
    - After .symbols access: loads all symbols into memory (cached)
    - After .files access: loads all files into memory (cached)
    - etc.

    For memory-efficient operations, consumers should use the underlying
    store's streaming methods directly via adapter._store.

    Args:
        store: SQLiteIndexStore instance
    """

    def __init__(self, store: SQLiteIndexStore):
        self._store = store

        # Lazy-loaded caches
        self._cached_files: Optional[List[FileObject]] = None
        self._cached_symbols: Optional[List[CodeSymbol]] = None
        self._cached_embeddings: Optional[List[SymbolEmbedding]] = None
        self._cached_imports: Optional[List[ImportReference]] = None
        self._cached_calls: Optional[List[CallReference]] = None
        self._cached_type_infos: Optional[List[TypeInfo]] = None
        self._cached_import_links: Optional[List[ImportLink]] = None
        self._cached_metadata: Optional[Dict[str, Any]] = None

    @property
    def files(self) -> List[FileObject]:
        """
        Lazy load all files from SQLite.

        Returns:
            List of FileObject (cached after first access)
        """
        if self._cached_files is None:
            conn = self._store._get_connection()
            try:
                cursor = conn.execute("SELECT * FROM files ORDER BY path")
                self._cached_files = [
                    FileObject(
                        path=row['path'],
                        abs_path=row['abs_path'],
                        size=row['size'],
                        last_modified=row['last_modified']
                    )
                    for row in cursor.fetchall()
                ]
                logger.debug(f"Loaded {len(self._cached_files)} files from SQLite (cached)")
            finally:
                conn.close()

        return self._cached_files

    @property
    def symbols(self) -> List[CodeSymbol]:
        """
        Lazy load all symbols from SQLite.

        Returns:
            List of CodeSymbol (cached after first access)
        """
        if self._cached_symbols is None:
            self._cached_symbols = list(self._store.query_symbols())
            logger.debug(f"Loaded {len(self._cached_symbols)} symbols from SQLite (cached)")

        return self._cached_symbols

    @property
    def embeddings(self) -> List[SymbolEmbedding]:
        """
        Lazy load embeddings metadata from SQLite.

        Note: This loads metadata only, not the actual vectors.
        Use store._faiss_store for vector operations.

        Returns:
            List of SymbolEmbedding (cached after first access)
        """
        if self._cached_embeddings is None:
            conn = self._store._get_connection()
            try:
                cursor = conn.execute("""
                    SELECT em.name, em.file_path, em.faiss_id, em.symbol_id
                    FROM embeddings_metadata em
                    ORDER BY em.symbol_id
                """)

                # For backward compatibility, we need to reconstruct vectors from FAISS
                # This is expensive and should be avoided - consumers should use FAISS directly
                embeddings = []

                if self._store._faiss_store and hasattr(self._store, '_faiss_store'):
                    for row in cursor.fetchall():
                        try:
                            # Reconstruct vector from FAISS (expensive!)
                            vector = self._store._faiss_store.index.reconstruct(int(row['faiss_id']))
                            embeddings.append(SymbolEmbedding(
                                name=row['name'],
                                file_path=row['file_path'],
                                vector=vector.tolist()
                            ))
                        except Exception as e:
                            logger.warning(f"Failed to reconstruct vector for faiss_id={row['faiss_id']}: {e}")
                else:
                    # No FAISS store available, return empty embeddings
                    logger.debug("No FAISS store available for embedding reconstruction")

                self._cached_embeddings = embeddings
                logger.debug(f"Loaded {len(self._cached_embeddings)} embeddings from FAISS (cached)")
            finally:
                conn.close()

        return self._cached_embeddings

    @property
    def imports(self) -> List[ImportReference]:
        """
        Lazy load all imports from SQLite.

        Returns:
            List of ImportReference (cached after first access)
        """
        if self._cached_imports is None:
            conn = self._store._get_connection()
            try:
                cursor = conn.execute("SELECT * FROM imports ORDER BY file_path, line")
                self._cached_imports = [
                    ImportReference(
                        module=row['module'],
                        file_path=row['file_path'],
                        line=row['line']
                    )
                    for row in cursor.fetchall()
                ]
                logger.debug(f"Loaded {len(self._cached_imports)} imports from SQLite (cached)")
            finally:
                conn.close()

        return self._cached_imports

    @property
    def calls(self) -> List[CallReference]:
        """
        Lazy load all calls from SQLite.

        Returns:
            List of CallReference (cached after first access)
        """
        if self._cached_calls is None:
            conn = self._store._get_connection()
            try:
                cursor = conn.execute("SELECT * FROM calls ORDER BY caller_file, line")
                self._cached_calls = [
                    CallReference(
                        caller_file=row['caller_file'],
                        callee=row['callee'],
                        line=row['line']
                    )
                    for row in cursor.fetchall()
                ]
                logger.debug(f"Loaded {len(self._cached_calls)} calls from SQLite (cached)")
            finally:
                conn.close()

        return self._cached_calls

    @property
    def type_infos(self) -> List[TypeInfo]:
        """
        Lazy load all type_infos from SQLite.

        Returns:
            List of TypeInfo (cached after first access)
        """
        if self._cached_type_infos is None:
            conn = self._store._get_connection()
            try:
                cursor = conn.execute("SELECT * FROM type_infos ORDER BY file_path, line")
                self._cached_type_infos = [
                    TypeInfo(
                        name=row['name'],
                        type_annotation=row['type_annotation'],
                        inferred_type=row['inferred_type'],
                        file_path=row['file_path'],
                        line=row['line']
                    )
                    for row in cursor.fetchall()
                ]
                logger.debug(f"Loaded {len(self._cached_type_infos)} type_infos from SQLite (cached)")
            finally:
                conn.close()

        return self._cached_type_infos

    @property
    def import_links(self) -> List[ImportLink]:
        """
        Lazy load all import_links from SQLite.

        Returns:
            List of ImportLink (cached after first access)
        """
        if self._cached_import_links is None:
            conn = self._store._get_connection()
            try:
                cursor = conn.execute("SELECT * FROM import_links ORDER BY importer_file, import_line")
                self._cached_import_links = [
                    ImportLink(
                        importer_file=row['importer_file'],
                        imported_module=row['imported_module'],
                        imported_symbols=json.loads(row['imported_symbols']),
                        import_line=row['import_line'],
                        definition_file=row['definition_file'],
                        definition_symbol=row['definition_symbol']
                    )
                    for row in cursor.fetchall()
                ]
                logger.debug(f"Loaded {len(self._cached_import_links)} import_links from SQLite (cached)")
            finally:
                conn.close()

        return self._cached_import_links

    @property
    def metadata(self) -> Dict[str, Any]:
        """
        Lazy load metadata from SQLite.

        Returns:
            Dict of metadata key-value pairs (cached after first access)
        """
        if self._cached_metadata is None:
            conn = self._store._get_connection()
            try:
                cursor = conn.execute("SELECT key, value FROM metadata WHERE key NOT IN ('schema_version', 'created_at')")
                self._cached_metadata = {row['key']: row['value'] for row in cursor.fetchall()}
                logger.debug(f"Loaded {len(self._cached_metadata)} metadata entries from SQLite (cached)")
            finally:
                conn.close()

        return self._cached_metadata

    @property
    def project_root(self) -> str:
        """
        Get project root from metadata.

        Returns:
            Project root path as string
        """
        return self._store.get_metadata('project_root') or ""

    @property
    def total_files(self) -> int:
        """
        Get total file count.

        Returns:
            Number of files in index
        """
        return self._store.get_stats()['total_files']

    @property
    def scan_duration(self) -> float:
        """
        Get scan duration from metadata.

        Returns:
            Scan duration in seconds (0.0 if not recorded)
        """
        duration_str = self._store.get_metadata('scan_duration')
        return float(duration_str) if duration_str else 0.0

    def clear_cache(self):
        """
        Clear all cached data to free memory.

        Useful when the adapter is long-lived and you want to release memory
        after processing. The next property access will reload from SQLite.
        """
        self._cached_files = None
        self._cached_symbols = None
        self._cached_embeddings = None
        self._cached_imports = None
        self._cached_calls = None
        self._cached_type_infos = None
        self._cached_import_links = None
        self._cached_metadata = None
        logger.debug("Cleared ScanResultAdapter cache")

    def __repr__(self) -> str:
        stats = self._store.get_stats()
        return (
            f"ScanResultAdapter("
            f"files={stats['total_files']}, "
            f"symbols={stats['total_symbols']}, "
            f"embeddings={stats['total_embeddings']}, "
            f"store={self._store.db_path})"
        )
