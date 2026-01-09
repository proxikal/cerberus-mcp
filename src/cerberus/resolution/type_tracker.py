"""
Type tracking system for Phase 5.3.

Tracks variable types across assignments and resolves method calls
to their class definitions.
"""

from typing import Dict, List, Optional, Tuple

from cerberus.logging_config import logger
from cerberus.schemas import (
    CodeSymbol,
    ImportLink,
    MethodCall,
    SymbolReference,
    TypeInfo,
)
from cerberus.storage.sqlite_store import SQLiteIndexStore
from .config import CONFIDENCE_THRESHOLDS


class TypeTracker:
    """
    Tracks variable types and resolves method calls to class definitions.

    Phase 5.3: Type-Annotation and Instantiation Resolution.

    Strategies:
    1. Explicit type annotations: optimizer: Optimizer (confidence: 0.9)
    2. Class instantiation: optimizer = Adam() (confidence: 0.85)
    3. Resolved imports: from torch.optim import Adam (confidence: 1.0)
    """

    def __init__(self, store: SQLiteIndexStore):
        """
        Initialize type tracker with storage.

        Args:
            store: SQLite storage containing index data
        """
        self.store = store
        self._type_map: Dict[Tuple[str, str], str] = {}  # (file, var_name) -> type_name
        self._symbol_by_name: Dict[str, List[CodeSymbol]] = {}
        self._build_type_map()

    def _build_type_map(self):
        """
        Build type map from type_infos and resolved import_links.

        Maps (file_path, variable_name) -> type_name for all known types.
        """
        logger.debug("Building type map for method call resolution...")

        # Strategy 1: Load explicit type annotations
        for type_info in self.store.query_type_infos():
            key = (type_info.file_path, type_info.name)

            # Prefer explicit annotation over inferred
            if type_info.type_annotation:
                # Clean up type annotation (remove List[], Optional[], etc.)
                type_name = self._extract_base_type(type_info.type_annotation)
                self._type_map[key] = type_name
            elif type_info.inferred_type:
                type_name = self._extract_base_type(type_info.inferred_type)
                self._type_map[key] = type_name

        # Strategy 2: Track imports - what symbols are available in each file
        for link in self.store.query_import_links():
            if link.definition_file and link.definition_symbol:
                # Map imported symbol to its actual type
                for imported_symbol in link.imported_symbols:
                    key = (link.importer_file, imported_symbol)
                    # The imported symbol IS the type (class/function definition)
                    self._type_map[key] = link.definition_symbol

        logger.debug(f"Type map built: {len(self._type_map)} type mappings")

        # Build symbol lookup cache
        for symbol in self.store.query_symbols():
            name = symbol.name
            if name not in self._symbol_by_name:
                self._symbol_by_name[name] = []
            self._symbol_by_name[name].append(symbol)

        logger.debug(f"Symbol cache built: {len(self._symbol_by_name)} unique symbol names")

    def _extract_base_type(self, type_str: str) -> str:
        """
        Extract base type from type annotation.

        Examples:
            "List[int]" -> "List"
            "Optional[MyClass]" -> "MyClass"
            "torch.optim.Adam" -> "Adam"
            "-> str" -> "str"

        Args:
            type_str: Type annotation string

        Returns:
            Base type name
        """
        # Remove "-> " prefix (return type annotations)
        type_str = type_str.strip()
        if type_str.startswith("->"):
            type_str = type_str[2:].strip()

        # Extract from generics like List[X], Optional[X]
        if "[" in type_str:
            # Get the inner type for Optional, List, etc.
            if type_str.startswith(("Optional[", "Union[")):
                inner = type_str[type_str.index("[") + 1 : type_str.rindex("]")]
                # Take first type in Union
                if "," in inner:
                    inner = inner.split(",")[0].strip()
                return self._extract_base_type(inner)
            else:
                # For List[X], Dict[X,Y], return the container type
                return type_str[:type_str.index("[")]

        # Extract class name from module path
        if "." in type_str:
            return type_str.split(".")[-1]

        return type_str

    def resolve_method_calls(self) -> List[SymbolReference]:
        """
        Resolve all method calls to their class definitions.

        Returns:
            List of SymbolReference objects for resolved method calls
        """
        references = []
        resolved_count = 0
        total_count = 0

        logger.info("Starting method call resolution...")

        for method_call in self.store.query_method_calls():
            total_count += 1

            # Try to resolve the method call
            result = self._resolve_method_call(method_call)

            if result:
                target_file, target_symbol, target_type, confidence, method = result
                references.append(SymbolReference(
                    source_file=method_call.caller_file,
                    source_line=method_call.line,
                    source_symbol=method_call.receiver,
                    reference_type="method_call",
                    target_file=target_file,
                    target_symbol=target_symbol,
                    target_type=target_type,
                    confidence=confidence,
                    resolution_method=method,
                ))
                resolved_count += 1

        logger.info(f"Resolved {resolved_count}/{total_count} method calls ({resolved_count/total_count*100:.1f}%)")
        return references

    def _resolve_method_call(self, call: MethodCall) -> Optional[Tuple[str, str, str, float, str]]:
        """
        Resolve a single method call to its class definition.

        Args:
            call: MethodCall object

        Returns:
            Tuple of (target_file, target_symbol, target_type, confidence, resolution_method)
            or None if cannot be resolved
        """
        # Step 1: Get receiver type from type map
        key = (call.caller_file, call.receiver)
        receiver_type = self._type_map.get(key)

        if not receiver_type:
            # Try to handle chained receivers like "self.optimizer"
            if "." in call.receiver:
                base_receiver = call.receiver.split(".")[0]
                key = (call.caller_file, base_receiver)
                receiver_type = self._type_map.get(key)

        if not receiver_type:
            return None

        # Step 2: Find class definition for the receiver type
        class_candidates = [
            s for s in self._symbol_by_name.get(receiver_type, [])
            if s.type == "class"
        ]

        if not class_candidates:
            return None

        # Use the first class definition (could be improved with better disambiguation)
        class_def = class_candidates[0]

        # Step 3: Find method within the class
        method_candidates = [
            s for s in self._symbol_by_name.get(call.method, [])
            if s.type == "method" and s.parent_class == class_def.name
        ]

        if method_candidates:
            method_def = method_candidates[0]
            return (
                method_def.file_path,
                method_def.name,
                class_def.name,
                CONFIDENCE_THRESHOLDS["type_annotation"],
                "type_annotation"
            )

        # Fallback: Return class definition even if method not found
        # (method might be inherited or dynamically added)
        return (
            class_def.file_path,
            call.method,
            class_def.name,
            CONFIDENCE_THRESHOLDS["heuristic"],
            "heuristic"
        )

    def track_class_instantiations(self) -> List[SymbolReference]:
        """
        Track class instantiations like: optimizer = Adam().

        Uses type_infos.inferred_type to find instantiations.

        Returns:
            List of SymbolReference objects for instantiations
        """
        references = []

        logger.info("Tracking class instantiations...")

        for type_info in self.store.query_type_infos():
            if type_info.inferred_type:
                # inferred_type contains the class name from instantiation
                class_name = self._extract_base_type(type_info.inferred_type)

                # Find the class definition
                class_candidates = [
                    s for s in self._symbol_by_name.get(class_name, [])
                    if s.type == "class"
                ]

                if class_candidates:
                    class_def = class_candidates[0]
                    references.append(SymbolReference(
                        source_file=type_info.file_path,
                        source_line=type_info.line,
                        source_symbol=type_info.name,
                        reference_type="instance_of",
                        target_file=class_def.file_path,
                        target_symbol=class_def.name,
                        target_type=class_def.name,
                        confidence=CONFIDENCE_THRESHOLDS["class_instantiation"],
                        resolution_method="class_instantiation",
                    ))

        logger.info(f"Tracked {len(references)} class instantiations")
        return references
