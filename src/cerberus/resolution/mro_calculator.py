"""
Phase 6: Method Resolution Order (MRO) Calculator.

Computes inheritance chains and method resolution order for classes.
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass

from cerberus.logging_config import logger
from cerberus.storage.sqlite_store import SQLiteIndexStore
from .config import INHERITANCE_CONFIG


@dataclass
class InheritanceNode:
    """Represents a node in the inheritance tree."""
    class_name: str
    file_path: Optional[str]
    base_classes: List[str]
    depth: int
    confidence: float


class MROCalculator:
    """
    Calculates Method Resolution Order (MRO) for classes.

    Implements C3 linearization algorithm (Python MRO) for computing
    the order in which base classes are searched for methods.
    """

    def __init__(self, store: SQLiteIndexStore):
        """
        Initialize the MRO calculator.

        Args:
            store: SQLite index store
        """
        self.store = store
        self.config = INHERITANCE_CONFIG
        self._inheritance_cache: Dict[str, List[str]] = {}

    def compute_mro(self, class_name: str, file_path: Optional[str] = None) -> List[InheritanceNode]:
        """
        Compute the MRO for a given class.

        Args:
            class_name: Name of the class
            file_path: Optional file path to disambiguate

        Returns:
            List of InheritanceNode objects in MRO order
        """
        logger.debug(f"Computing MRO for {class_name}")

        # Build inheritance tree
        mro = self._build_mro(class_name, file_path, depth=0, visited=set())

        logger.debug(f"MRO for {class_name}: {[node.class_name for node in mro]}")
        return mro

    def _build_mro(
        self,
        class_name: str,
        file_path: Optional[str],
        depth: int,
        visited: Set[str]
    ) -> List[InheritanceNode]:
        """
        Recursively build MRO using depth-first search.

        Args:
            class_name: Current class name
            file_path: File path of the class
            depth: Current depth in hierarchy
            visited: Set of visited classes to prevent cycles

        Returns:
            List of InheritanceNode objects
        """
        # Check max depth
        if depth > self.config["max_mro_depth"]:
            logger.warning(f"Max MRO depth reached for {class_name}")
            return []

        # Check for cycles
        cache_key = f"{class_name}:{file_path}" if file_path else class_name
        if cache_key in visited:
            logger.debug(f"Cycle detected: {class_name}")
            return []

        visited.add(cache_key)

        # Get base classes from database
        base_info = self._get_base_classes(class_name, file_path)

        if not base_info:
            # Leaf node (no base classes)
            return [InheritanceNode(
                class_name=class_name,
                file_path=file_path,
                base_classes=[],
                depth=depth,
                confidence=1.0
            )]

        # Build MRO: [self] + merge(base1_mro, base2_mro, ..., [base1, base2, ...])
        mro: List[InheritanceNode] = []

        # Add self first
        node = InheritanceNode(
            class_name=class_name,
            file_path=file_path,
            base_classes=[b[0] for b in base_info],
            depth=depth,
            confidence=1.0
        )
        mro.append(node)

        # For simplicity, use a linearized approach (not full C3)
        # This handles most common cases without complex merge logic
        for base_name, base_file, confidence in base_info:
            base_mro = self._build_mro(base_name, base_file, depth + 1, visited.copy())
            # Add base classes that aren't already in MRO
            for base_node in base_mro:
                if not any(n.class_name == base_node.class_name for n in mro):
                    base_node.confidence = min(base_node.confidence, confidence)
                    mro.append(base_node)

        return mro

    def _get_base_classes(
        self,
        class_name: str,
        file_path: Optional[str]
    ) -> List[Tuple[str, Optional[str], float]]:
        """
        Get base classes for a given class from symbol_references.

        Args:
            class_name: Name of the class
            file_path: Optional file path to disambiguate

        Returns:
            List of (base_class_name, base_file_path, confidence) tuples
        """
        conn = self.store._get_connection()
        try:
            if file_path:
                # Look for exact match
                cursor = conn.execute("""
                    SELECT target_symbol, target_file, confidence
                    FROM symbol_references
                    WHERE source_symbol = ?
                    AND source_file = ?
                    AND reference_type = 'inherits'
                    ORDER BY confidence DESC
                """, (class_name, file_path))
            else:
                # Look for any match
                cursor = conn.execute("""
                    SELECT target_symbol, target_file, confidence
                    FROM symbol_references
                    WHERE source_symbol = ?
                    AND reference_type = 'inherits'
                    ORDER BY confidence DESC
                """, (class_name,))

            results = cursor.fetchall()
            return [(row[0], row[1], row[2]) for row in results]

        finally:
            conn.close()

    def get_all_descendants(self, class_name: str, file_path: Optional[str] = None) -> List[str]:
        """
        Get all classes that inherit from the given class (directly or indirectly).

        Args:
            class_name: Base class name
            file_path: Optional file path to disambiguate

        Returns:
            List of descendant class names
        """
        logger.debug(f"Finding descendants of {class_name}")

        descendants: Set[str] = set()
        self._find_descendants(class_name, file_path, descendants, depth=0)

        logger.debug(f"Found {len(descendants)} descendants of {class_name}")
        return list(descendants)

    def _find_descendants(
        self,
        class_name: str,
        file_path: Optional[str],
        descendants: Set[str],
        depth: int
    ):
        """
        Recursively find all descendants of a class.

        Args:
            class_name: Base class name
            file_path: File path of the base class
            descendants: Set to accumulate descendants
            depth: Current recursion depth
        """
        if depth > self.config["max_mro_depth"]:
            return

        conn = self.store._get_connection()
        try:
            # Find all classes that inherit from this class
            if file_path:
                cursor = conn.execute("""
                    SELECT DISTINCT source_symbol, source_file
                    FROM symbol_references
                    WHERE target_symbol = ?
                    AND target_file = ?
                    AND reference_type = 'inherits'
                """, (class_name, file_path))
            else:
                cursor = conn.execute("""
                    SELECT DISTINCT source_symbol, source_file
                    FROM symbol_references
                    WHERE target_symbol = ?
                    AND reference_type = 'inherits'
                """, (class_name,))

            children = cursor.fetchall()

            for child_name, child_file in children:
                if child_name not in descendants:
                    descendants.add(child_name)
                    # Recursively find descendants of this child
                    self._find_descendants(child_name, child_file, descendants, depth + 1)

        finally:
            conn.close()

    def get_overridden_methods(
        self,
        class_name: str,
        file_path: Optional[str] = None
    ) -> Dict[str, List[Dict[str, any]]]:
        """
        Find methods that override base class methods.

        Args:
            class_name: Name of the class
            file_path: Optional file path

        Returns:
            Dict mapping method names to list of override info
        """
        logger.debug(f"Finding overridden methods in {class_name}")

        # Get MRO
        mro = self.compute_mro(class_name, file_path)

        if len(mro) <= 1:
            return {}  # No base classes

        # Get methods from the class
        conn = self.store._get_connection()
        try:
            cursor = conn.execute("""
                SELECT name, start_line, end_line
                FROM symbols
                WHERE parent_class = ?
                AND type = 'method'
            """ + (" AND file_path = ?" if file_path else ""),
                (class_name, file_path) if file_path else (class_name,)
            )
            class_methods = {row[0]: {"line": row[1], "end_line": row[2]} for row in cursor.fetchall()}

            # Check each base class for methods with same name
            overrides: Dict[str, List[Dict[str, any]]] = {}

            for base_node in mro[1:]:  # Skip self (index 0)
                cursor = conn.execute("""
                    SELECT name, file_path, start_line
                    FROM symbols
                    WHERE parent_class = ?
                    AND type = 'method'
                """ + (" AND file_path = ?" if base_node.file_path else ""),
                    (base_node.class_name, base_node.file_path) if base_node.file_path else (base_node.class_name,)
                )

                base_methods = cursor.fetchall()

                for method_name, method_file, method_line in base_methods:
                    if method_name in class_methods:
                        if method_name not in overrides:
                            overrides[method_name] = []

                        overrides[method_name].append({
                            "base_class": base_node.class_name,
                            "base_file": base_node.file_path,
                            "base_line": method_line,
                            "confidence": base_node.confidence
                        })

            logger.debug(f"Found {len(overrides)} overridden methods in {class_name}")
            return overrides

        finally:
            conn.close()
