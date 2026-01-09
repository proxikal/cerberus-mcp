"""
SQLite Storage Package

Modular SQLite-backed storage following the self-similarity mandate.

Public API:
- SQLiteIndexStore: Main facade for storage operations

Internal Modules:
- schema: Database schema definitions and initialization
- persistence: Connection management, transactions, metadata
- symbols: File and symbol CRUD operations
- resolution: Phase 5/6 symbolic intelligence operations
- config: Configuration constants
"""

from cerberus.storage.sqlite.facade import SQLiteIndexStore

__all__ = ['SQLiteIndexStore']
