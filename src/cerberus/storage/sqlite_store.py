"""
SQLite-backed storage for Cerberus index.

This module now serves as a backward-compatibility shim.
The actual implementation has been modularized into the sqlite/ package:
- sqlite/schema.py: Database schema definitions
- sqlite/persistence.py: Connection management, transactions, metadata
- sqlite/symbols.py: File and symbol CRUD operations
- sqlite/resolution.py: Phase 5/6 symbolic intelligence operations
- sqlite/facade.py: Public API facade

For new code, prefer importing directly from:
    from cerberus.storage.sqlite import SQLiteIndexStore
"""

from cerberus.storage.sqlite import SQLiteIndexStore

__all__ = ['SQLiteIndexStore']
