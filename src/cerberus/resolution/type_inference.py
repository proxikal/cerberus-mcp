"""
Phase 6: Cross-File Type Inference.

Infers types across file boundaries using dataflow analysis,
import tracking, and return type propagation.
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass

from cerberus.logging_config import logger
from cerberus.storage.sqlite_store import SQLiteIndexStore


@dataclass
class InferredType:
    """Represents an inferred type for a symbol."""
    symbol_name: str
    file_path: str
    line: int
    inferred_type: str
    confidence: float
    inference_method: str  # 'return_type', 'assignment', 'parameter', 'import'


class TypeInference:
    """
    Performs cross-file type inference using dataflow analysis.

    Strategies:
    1. Return type propagation - Track function return types across calls
    2. Assignment tracking - Follow variable assignments across files
    3. Parameter type hints - Use explicit type annotations
    4. Import resolution - Track types through import chains
    """

    def __init__(self, store: SQLiteIndexStore):
        """
        Initialize type inference engine.

        Args:
            store: SQLite index store
        """
        self.store = store
        self._type_cache: Dict[str, InferredType] = {}

    def infer_variable_type(
        self,
        variable_name: str,
        file_path: str,
        line: int
    ) -> Optional[InferredType]:
        """
        Infer the type of a variable at a specific location.

        Args:
            variable_name: Name of the variable
            file_path: File containing the variable
            line: Line number where variable is used

        Returns:
            InferredType or None if type cannot be inferred
        """
        cache_key = f"{variable_name}:{file_path}:{line}"
        if cache_key in self._type_cache:
            return self._type_cache[cache_key]

        logger.debug(f"Inferring type for {variable_name} at {file_path}:{line}")

        # Strategy 1: Check for type annotations
        type_info = self._check_type_annotation(variable_name, file_path, line)
        if type_info:
            self._type_cache[cache_key] = type_info
            return type_info

        # Strategy 2: Check for class instantiation
        type_info = self._check_instantiation(variable_name, file_path, line)
        if type_info:
            self._type_cache[cache_key] = type_info
            return type_info

        # Strategy 3: Check for return type propagation
        type_info = self._check_return_type(variable_name, file_path, line)
        if type_info:
            self._type_cache[cache_key] = type_info
            return type_info

        # Strategy 4: Check imports
        type_info = self._check_import_type(variable_name, file_path)
        if type_info:
            self._type_cache[cache_key] = type_info
            return type_info

        logger.debug(f"Could not infer type for {variable_name}")
        return None

    def infer_function_return_type(
        self,
        function_name: str,
        file_path: Optional[str] = None
    ) -> Optional[InferredType]:
        """
        Infer the return type of a function.

        Args:
            function_name: Name of the function
            file_path: Optional file path to disambiguate

        Returns:
            InferredType or None
        """
        logger.debug(f"Inferring return type for {function_name}")

        conn = self.store._get_connection()
        try:
            # Check if function has explicit return type annotation
            if file_path:
                cursor = conn.execute("""
                    SELECT return_type, file_path, start_line
                    FROM symbols
                    WHERE name = ? AND file_path = ? AND type IN ('function', 'method')
                    LIMIT 1
                """, (function_name, file_path))
            else:
                cursor = conn.execute("""
                    SELECT return_type, file_path, start_line
                    FROM symbols
                    WHERE name = ? AND type IN ('function', 'method')
                    LIMIT 1
                """, (function_name,))

            result = cursor.fetchone()
            if result and result[0]:
                return InferredType(
                    symbol_name=function_name,
                    file_path=result[1],
                    line=result[2],
                    inferred_type=result[0],
                    confidence=1.0,
                    inference_method="return_type_annotation"
                )

            return None
        finally:
            conn.close()

    def propagate_types_across_calls(self) -> int:
        """
        Propagate types across function calls in the codebase.

        This creates new type_infos entries based on dataflow analysis.

        Returns:
            Number of new type inferences created
        """
        logger.info("Starting cross-file type propagation...")

        conn = self.store._get_connection()
        try:
            # Find all function calls with known return types
            cursor = conn.execute("""
                SELECT c.caller_file, c.line, c.callee, s.return_type
                FROM calls c
                JOIN symbols s ON c.callee = s.name
                WHERE s.return_type IS NOT NULL
                AND s.type IN ('function', 'method')
            """)

            calls_with_types = cursor.fetchall()

            new_inferences = []
            for caller_file, line, callee, return_type in calls_with_types:
                # This call returns a typed value
                # We could track assignments: result = some_function()
                # For now, just log the inference
                logger.debug(f"Call to {callee} at {caller_file}:{line} returns {return_type}")

            logger.info(f"Type propagation complete: {len(new_inferences)} new inferences")
            return len(new_inferences)

        finally:
            conn.close()

    def _check_type_annotation(
        self,
        variable_name: str,
        file_path: str,
        line: int
    ) -> Optional[InferredType]:
        """Check for explicit type annotation in type_infos table."""
        conn = self.store._get_connection()
        try:
            cursor = conn.execute("""
                SELECT type_annotation, line
                FROM type_infos
                WHERE name = ? AND file_path = ? AND line <= ?
                AND type_annotation IS NOT NULL
                ORDER BY line DESC
                LIMIT 1
            """, (variable_name, file_path, line))

            result = cursor.fetchone()
            if result and result[0]:
                return InferredType(
                    symbol_name=variable_name,
                    file_path=file_path,
                    line=result[1],
                    inferred_type=result[0],
                    confidence=0.9,
                    inference_method="type_annotation"
                )
            return None
        finally:
            conn.close()

    def _check_instantiation(
        self,
        variable_name: str,
        file_path: str,
        line: int
    ) -> Optional[InferredType]:
        """Check if variable is a class instantiation."""
        conn = self.store._get_connection()
        try:
            # Look for symbol_references with instance_of type
            cursor = conn.execute("""
                SELECT target_symbol, target_type, source_line
                FROM symbol_references
                WHERE source_symbol = ? AND source_file = ?
                AND reference_type = 'instance_of'
                AND source_line <= ?
                ORDER BY source_line DESC
                LIMIT 1
            """, (variable_name, file_path, line))

            result = cursor.fetchone()
            if result:
                return InferredType(
                    symbol_name=variable_name,
                    file_path=file_path,
                    line=result[2],
                    inferred_type=result[0],
                    confidence=0.85,
                    inference_method="class_instantiation"
                )
            return None
        finally:
            conn.close()

    def _check_return_type(
        self,
        variable_name: str,
        file_path: str,
        line: int
    ) -> Optional[InferredType]:
        """Check if variable gets its type from a function return."""
        # This would require assignment tracking
        # For now, return None (placeholder for future enhancement)
        return None

    def _check_import_type(
        self,
        variable_name: str,
        file_path: str
    ) -> Optional[InferredType]:
        """Check if variable is an imported symbol with known type."""
        conn = self.store._get_connection()
        try:
            # Check import_links for this symbol
            cursor = conn.execute("""
                SELECT definition_file, definition_symbol
                FROM import_links
                WHERE importer_file = ?
                AND definition_symbol = ?
                LIMIT 1
            """, (file_path, variable_name))

            result = cursor.fetchone()
            if result and result[0]:
                # Get the type of the imported symbol
                def_file, def_symbol = result[0], result[1]

                cursor = conn.execute("""
                    SELECT type, start_line
                    FROM symbols
                    WHERE file_path = ? AND name = ?
                    LIMIT 1
                """, (def_file, def_symbol))

                symbol_result = cursor.fetchone()
                if symbol_result:
                    return InferredType(
                        symbol_name=variable_name,
                        file_path=file_path,
                        line=0,
                        inferred_type=symbol_result[0],
                        confidence=0.95,
                        inference_method="import_resolution"
                    )

            return None
        finally:
            conn.close()
