"""
Public API for Phase 5: Symbolic Intelligence resolution.

Provides high-level functions for resolving imports, types, and references.
"""

from pathlib import Path
from typing import List, Tuple, Dict, Optional

from cerberus.logging_config import logger
from cerberus.storage.sqlite_store import SQLiteIndexStore
from .resolver import ImportResolver
from .type_tracker import TypeTracker
from .inheritance_resolver import InheritanceResolver
from .mro_calculator import MROCalculator, InheritanceNode
from .call_graph_builder import CallGraphBuilder, CallGraph
from .type_inference import TypeInference, InferredType
from .context_assembler import ContextAssembler, AssembledContext


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


def resolve_inheritance(store: SQLiteIndexStore, project_root: str) -> int:
    """
    Resolve inheritance relationships and track base classes.

    Phase 6.1: Inheritance Resolution.

    This function:
    1. Creates an InheritanceResolver
    2. Extracts base class relationships from source code
    3. Writes 'inherits' references to symbol_references table

    Args:
        store: SQLite index store
        project_root: Root directory of the project

    Returns:
        Number of inheritance references created
    """
    logger.info("Phase 6.1: Starting inheritance resolution...")

    # Create resolver
    resolver = InheritanceResolver(store, project_root)

    # Extract inheritance relationships
    relations = resolver.resolve_inheritance()

    # Update database
    count = resolver.update_inheritance_references(relations)

    logger.info(f"Phase 6.1: Created {count} inheritance references")
    return count


def compute_class_mro(
    store: SQLiteIndexStore,
    class_name: str,
    file_path: Optional[str] = None
) -> List[InheritanceNode]:
    """
    Compute Method Resolution Order for a class.

    Phase 6.2: MRO Calculation.

    Args:
        store: SQLite index store
        class_name: Name of the class
        file_path: Optional file path to disambiguate

    Returns:
        List of InheritanceNode objects in MRO order
    """
    calculator = MROCalculator(store)
    return calculator.compute_mro(class_name, file_path)


def get_class_descendants(
    store: SQLiteIndexStore,
    class_name: str,
    file_path: Optional[str] = None
) -> List[str]:
    """
    Get all classes that inherit from the given class.

    Phase 6.2: Descendant Discovery.

    Args:
        store: SQLite index store
        class_name: Base class name
        file_path: Optional file path to disambiguate

    Returns:
        List of descendant class names
    """
    calculator = MROCalculator(store)
    return calculator.get_all_descendants(class_name, file_path)


def get_overridden_methods(
    store: SQLiteIndexStore,
    class_name: str,
    file_path: Optional[str] = None
) -> Dict[str, List[Dict[str, any]]]:
    """
    Find methods that override base class methods.

    Phase 6.2: Override Detection.

    Args:
        store: SQLite index store
        class_name: Name of the class
        file_path: Optional file path

    Returns:
        Dict mapping method names to list of override info
    """
    calculator = MROCalculator(store)
    return calculator.get_overridden_methods(class_name, file_path)


def build_call_graph(
    store: SQLiteIndexStore,
    symbol_name: str,
    file_path: Optional[str] = None,
    direction: str = "forward",
    max_depth: Optional[int] = None
) -> CallGraph:
    """
    Build a call graph for a symbol.

    Phase 6.3: Call Graph Generation.

    Args:
        store: SQLite index store
        symbol_name: Name of the function/method
        file_path: Optional file path to disambiguate
        direction: 'forward' (what does it call?) or 'reverse' (what calls it?)
        max_depth: Maximum depth to traverse

    Returns:
        CallGraph object
    """
    builder = CallGraphBuilder(store)

    if direction == "forward":
        return builder.build_forward_graph(symbol_name, file_path, max_depth)
    else:
        return builder.build_reverse_graph(symbol_name, file_path, max_depth)


def infer_type(
    store: SQLiteIndexStore,
    symbol_name: str,
    file_path: str,
    line: int
) -> Optional[InferredType]:
    """
    Infer the type of a variable at a specific location.

    Phase 6.4: Cross-File Type Inference.

    Args:
        store: SQLite index store
        symbol_name: Name of the variable/symbol
        file_path: File containing the symbol
        line: Line number

    Returns:
        InferredType or None
    """
    inference = TypeInference(store)
    return inference.infer_variable_type(symbol_name, file_path, line)


def assemble_context(
    store: SQLiteIndexStore,
    symbol_name: str,
    file_path: Optional[str] = None,
    include_bases: Optional[bool] = None,
    format_output: bool = False
) -> Optional[AssembledContext]:
    """
    Assemble smart context for a symbol with inheritance awareness.

    Phase 6.5: Smart Context Assembly.

    Args:
        store: SQLite index store
        symbol_name: Name of the symbol
        file_path: Optional file path to disambiguate
        include_bases: Whether to include base classes
        format_output: Whether to return formatted string

    Returns:
        AssembledContext or formatted string if format_output=True
    """
    assembler = ContextAssembler(store)
    context = assembler.assemble_context(symbol_name, file_path, include_bases)

    if context and format_output:
        return assembler.format_context(context)

    return context


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

        # Count inheritance references (Phase 6)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM symbol_references
            WHERE reference_type = 'inherits'
        """)
        inheritance_references = cursor.fetchone()[0]

        return {
            "total_import_links": total_imports,
            "resolved_import_links": resolved_imports,
            "unresolved_import_links": total_imports - resolved_imports,
            "resolution_rate": resolved_imports / total_imports if total_imports > 0 else 0.0,
            "total_method_calls": total_method_calls,
            "total_symbol_references": total_references,
            "inheritance_references": inheritance_references,
        }
    finally:
        conn.close()
