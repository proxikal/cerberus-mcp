"""
Public API for Phase 5: Symbolic Intelligence resolution.

Provides high-level functions for resolving imports, types, and references.
"""

from pathlib import Path
from typing import List, Tuple

from cerberus.logging_config import logger
from cerberus.storage.sqlite_store import SQLiteIndexStore
from .resolver import ImportResolver
from .type_tracker import TypeTracker


def resolve_imports(store: SQLiteIndexStore, project_root: str) -> int:
    """
    Resolve all import links to their internal definitions.

    Phase 5.2: Import-Based Resolution.

    This is the main entry point for import resolution. It:
    1. Creates an ImportResolver
    2. Resolves all unresolved import links
    3. Updates the database with resolved definitions

    Args:
        store: SQLite index store
        project_root: Root directory of the project

    Returns:
        Number of import links resolved
    """
    logger.info("Phase 5.2: Starting import resolution...")

    # Create resolver
    resolver = ImportResolver(store, project_root)

    # Resolve imports
    resolved = resolver.resolve_import_links()

    # Update database
    resolver.update_resolved_links(resolved)

    logger.info(f"Phase 5.2: Resolved {len(resolved)} import links")
    return len(resolved)


def resolve_types(store: SQLiteIndexStore) -> int:
    """
    Resolve method calls and track types using type annotations and imports.

    Phase 5.3: Type-Based Resolution.

    This function:
    1. Creates a TypeTracker
    2. Resolves method calls to class definitions
    3. Tracks class instantiations
    4. Writes symbol references to database

    Args:
        store: SQLite index store

    Returns:
        Number of symbol references created
    """
    logger.info("Phase 5.3: Starting type tracking and method resolution...")

    # Create type tracker
    tracker = TypeTracker(store)

    # Resolve method calls
    method_references = tracker.resolve_method_calls()

    # Track class instantiations
    instantiation_references = tracker.track_class_instantiations()

    # Combine all references
    all_references = method_references + instantiation_references

    # Write to database
    if all_references:
        store.write_symbol_references_batch(all_references)
        logger.info(f"Phase 5.3: Created {len(all_references)} symbol references")
    else:
        logger.info("Phase 5.3: No symbol references created")

    return len(all_references)


def get_resolution_stats(store: SQLiteIndexStore) -> dict:
    """
    Get statistics about resolution coverage.

    Args:
        store: SQLite index store

    Returns:
        Dict with resolution statistics
    """
    conn = store._get_connection()
    try:
        # Count total import links
        cursor = conn.execute("SELECT COUNT(*) FROM import_links")
        total_imports = cursor.fetchone()[0]

        # Count resolved import links
        cursor = conn.execute("""
            SELECT COUNT(*) FROM import_links
            WHERE definition_file IS NOT NULL
        """)
        resolved_imports = cursor.fetchone()[0]

        # Count method calls
        cursor = conn.execute("SELECT COUNT(*) FROM method_calls")
        total_method_calls = cursor.fetchone()[0]

        # Count symbol references
        cursor = conn.execute("SELECT COUNT(*) FROM symbol_references")
        total_references = cursor.fetchone()[0]

        return {
            "total_import_links": total_imports,
            "resolved_import_links": resolved_imports,
            "unresolved_import_links": total_imports - resolved_imports,
            "resolution_rate": resolved_imports / total_imports if total_imports > 0 else 0.0,
            "total_method_calls": total_method_calls,
            "total_symbol_references": total_references,
        }
    finally:
        conn.close()
