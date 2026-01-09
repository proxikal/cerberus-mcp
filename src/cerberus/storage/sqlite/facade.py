"""
SQLite Storage Facade

Public API for SQLite-backed storage. Delegates to specialized modules while
maintaining backward compatibility with the original SQLiteIndexStore interface.
"""

from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from cerberus.schemas import (
    CallReference,
    CodeSymbol,
    FileObject,
    ImportLink,
    ImportReference,
    MethodCall,
    SymbolReference,
    TypeInfo,
)
from cerberus.storage.sqlite.persistence import SQLitePersistence
from cerberus.storage.sqlite.symbols import SQLiteSymbolsOperations
from cerberus.storage.sqlite.resolution import SQLiteResolutionOperations


class SQLiteIndexStore:
    """
    SQLite-backed index store with streaming support.

    Replaces the monolithic implementation with a modular architecture:
    - persistence: Connection management, transactions, metadata
    - symbols: File and symbol CRUD operations
    - resolution: Phase 5/6 symbolic intelligence operations

    Features:
    - Streaming queries via generators (constant memory)
    - FAISS integration for vector search
    - Transactional writes with rollback support
    - Foreign key cascades for automatic cleanup

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
        # Initialize persistence layer
        self.persistence = SQLitePersistence(index_path)

        # Initialize specialized operation modules
        self.symbols = SQLiteSymbolsOperations(self.persistence._get_connection)
        self.resolution = SQLiteResolutionOperations(self.persistence._get_connection)

        # Expose persistence layer attributes for backward compatibility
        self.db_path = self.persistence.db_path
        self.index_dir = self.persistence.index_dir
        self._faiss_store = self.persistence._faiss_store

    # ========== CONNECTION & TRANSACTION MANAGEMENT ==========

    def _get_connection(self):
        """Get database connection with optimized settings."""
        return self.persistence._get_connection()

    def transaction(self):
        """Context manager for atomic transactions."""
        return self.persistence.transaction()

    # ========== FILE & SYMBOL OPERATIONS ==========

    def write_file(self, file_obj: FileObject, conn=None):
        """Write or update a single file record."""
        return self.symbols.write_file(file_obj, conn)

    def write_symbols_batch(self, symbols: List[CodeSymbol], conn=None, chunk_size: int = 1000):
        """Batch write symbols with optimized chunking."""
        return self.symbols.write_symbols_batch(symbols, conn, chunk_size)

    def write_embedding_metadata(self, symbol_id: int, faiss_id: int, name: str,
                                 file_path: str, model: str, conn=None):
        """Write embedding metadata."""
        return self.symbols.write_embedding_metadata(
            symbol_id, faiss_id, name, file_path, model, conn
        )

    def delete_file(self, file_path: str, conn=None):
        """Delete file and all associated data."""
        return self.symbols.delete_file(file_path, conn)

    def query_symbols(self, filter: Optional[Dict[str, Any]] = None, batch_size: int = 100):
        """Streaming query for symbols with optional filtering."""
        return self.symbols.query_symbols(filter, batch_size)

    def fts5_search(self, query: str, top_k: int = 20, batch_size: int = 100):
        """Phase 7: FTS5-based keyword search with zero RAM overhead."""
        return self.symbols.fts5_search(query, top_k, batch_size)

    def find_symbol_by_line(self, file_path: str, line: int):
        """Find symbol containing a specific line."""
        return self.symbols.find_symbol_by_line(file_path, line)

    # ========== RESOLUTION OPERATIONS (PHASE 5/6) ==========

    def write_imports_batch(self, imports: List[ImportReference], conn=None):
        """Batch write import references."""
        return self.resolution.write_imports_batch(imports, conn)

    def write_calls_batch(self, calls: List[CallReference], conn=None):
        """Batch write call references."""
        return self.resolution.write_calls_batch(calls, conn)

    def write_type_infos_batch(self, type_infos: List[TypeInfo], conn=None):
        """Batch write type information."""
        return self.resolution.write_type_infos_batch(type_infos, conn)

    def write_import_links_batch(self, import_links: List[ImportLink], conn=None):
        """Batch write import links."""
        return self.resolution.write_import_links_batch(import_links, conn)

    def write_method_calls_batch(self, method_calls: List[MethodCall], conn=None):
        """Batch write method calls (Phase 5.1)."""
        return self.resolution.write_method_calls_batch(method_calls, conn)

    def write_symbol_references_batch(self, refs: List[SymbolReference], conn=None):
        """Batch write symbol references (Phase 5.2+)."""
        return self.resolution.write_symbol_references_batch(refs, conn)

    def query_import_links(self, filter: Optional[Dict[str, Any]] = None, batch_size: int = 100):
        """Stream import links with optional filtering."""
        return self.resolution.query_import_links(filter, batch_size)

    def query_calls_by_callee(self, callee: str, batch_size: int = 100):
        """Stream call references by callee."""
        return self.resolution.query_calls_by_callee(callee, batch_size)

    def query_method_calls(self, batch_size: int = 100):
        """Stream all method calls (Phase 5.3)."""
        return self.resolution.query_method_calls(batch_size)

    def query_type_infos(self, batch_size: int = 100):
        """Stream all type infos (Phase 5.3)."""
        return self.resolution.query_type_infos(batch_size)

    def query_symbol_references(self, batch_size: int = 100):
        """Stream all symbol references (Phase 5.3)."""
        return self.resolution.query_symbol_references(batch_size)

    def query_method_calls_filtered(self, method=None, receiver=None,
                                   receiver_type=None, file_path=None, batch_size: int = 100):
        """Stream method calls with optional filtering."""
        return self.resolution.query_method_calls_filtered(
            method, receiver, receiver_type, file_path, batch_size
        )

    def query_symbol_references_filtered(self, source_symbol=None, target_symbol=None,
                                        reference_type=None, min_confidence=None,
                                        source_file=None, target_file=None, batch_size: int = 100):
        """Stream symbol references with optional filtering."""
        return self.resolution.query_symbol_references_filtered(
            source_symbol, target_symbol, reference_type, min_confidence,
            source_file, target_file, batch_size
        )

    # ========== METADATA & STATS ==========

    def get_metadata(self, key: str):
        """Get metadata value by key."""
        return self.persistence.get_metadata(key)

    def set_metadata(self, key: str, value: str, conn=None):
        """Set metadata key-value pair."""
        return self.persistence.set_metadata(key, value, conn)

    def get_stats(self):
        """Get index statistics."""
        return self.persistence.get_stats()

    def close(self):
        """Close store and persist any in-memory data."""
        return self.persistence.close()
