"""
Phase 6: Inheritance Resolution.

Extracts base class relationships from source code and populates
the 'inherits' reference type in symbol_references.
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass

from cerberus.logging_config import logger
from cerberus.storage.sqlite_store import SQLiteIndexStore
from cerberus.schemas import SymbolReference
from .config import INHERITANCE_CONFIG

try:
    from tree_sitter import Parser, Node, Language
    import tree_sitter_python as tspython
    import tree_sitter_javascript as tsjavascript
    import tree_sitter_typescript as tstypescript
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logger.warning("tree-sitter not available, inheritance resolution will be limited")


@dataclass
class InheritanceRelation:
    """Represents an inheritance relationship."""
    child_class: str
    child_file: str
    child_line: int
    base_classes: List[str]  # Ordered list of base classes
    confidence: float
    resolution_method: str


class InheritanceResolver:
    """
    Resolves inheritance relationships across the codebase.

    Uses tree-sitter to extract base class declarations and creates
    'inherits' references in the symbol_references table.
    """

    def __init__(self, store: SQLiteIndexStore, project_root: str):
        """
        Initialize the inheritance resolver.

        Args:
            store: SQLite index store
            project_root: Root directory of the project
        """
        self.store = store
        self.project_root = Path(project_root)
        self.config = INHERITANCE_CONFIG
        self.parsers: Dict[str, Parser] = {}

        if TREE_SITTER_AVAILABLE:
            self._init_parsers()
        else:
            logger.warning("Tree-sitter not available, inheritance resolution disabled")

    def _init_parsers(self):
        """Initialize tree-sitter parsers for supported languages."""
        try:
            # Python parser
            python_parser = Parser()
            python_parser.language = Language(tspython.language())
            self.parsers["python"] = python_parser

            # JavaScript parser
            js_parser = Parser()
            js_parser.language = Language(tsjavascript.language())
            self.parsers["javascript"] = js_parser

            # TypeScript parser
            ts_parser = Parser()
            ts_parser.language = Language(tstypescript.language_typescript())
            self.parsers["typescript"] = ts_parser

            logger.debug(f"Initialized inheritance parsers: {list(self.parsers.keys())}")
        except Exception as e:
            logger.error(f"Failed to initialize parsers: {e}")
            self.parsers = {}

    def resolve_inheritance(self) -> List[InheritanceRelation]:
        """
        Extract inheritance relationships from all indexed files.

        Returns:
            List of InheritanceRelation objects
        """
        if not TREE_SITTER_AVAILABLE:
            logger.error("Cannot resolve inheritance without tree-sitter")
            return []

        logger.info("Phase 6.1: Extracting inheritance relationships...")

        relations: List[InheritanceRelation] = []

        # Get all class symbols from the database
        conn = self.store._get_connection()
        try:
            cursor = conn.execute("""
                SELECT name, file_path, start_line
                FROM symbols
                WHERE type = 'class'
                ORDER BY file_path, start_line
            """)
            classes = cursor.fetchall()

            logger.info(f"Found {len(classes)} classes to analyze")

            # Process each class to extract inheritance
            for class_name, file_path, start_line in classes:
                class_relations = self._extract_class_inheritance(
                    class_name, file_path, start_line
                )
                relations.extend(class_relations)

        finally:
            conn.close()

        logger.info(f"Phase 6.1: Extracted {len(relations)} inheritance relationships")
        return relations

    def _extract_class_inheritance(
        self,
        class_name: str,
        file_path: str,
        start_line: int
    ) -> List[InheritanceRelation]:
        """
        Extract base classes for a specific class.

        Args:
            class_name: Name of the class
            file_path: File containing the class
            start_line: Line number of the class declaration

        Returns:
            List of inheritance relations for this class
        """
        # Determine language
        path = Path(file_path)
        if not path.exists():
            # Use absolute path
            path = self.project_root / file_path

        if not path.exists():
            logger.warning(f"File not found: {file_path}")
            return []

        language = self._detect_language(path.suffix)
        if not language or language not in self.parsers:
            return []

        # Read file content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return []

        # Parse and extract base classes
        parser = self.parsers[language]
        tree = parser.parse(bytes(source_code, "utf8"))

        # Extract base classes using language-specific logic
        if language == "python":
            return self._extract_python_inheritance(
                class_name, file_path, start_line, tree.root_node, source_code
            )
        elif language in ("javascript", "typescript"):
            return self._extract_js_ts_inheritance(
                class_name, file_path, start_line, tree.root_node, source_code, language
            )

        return []

    def _extract_python_inheritance(
        self,
        class_name: str,
        file_path: str,
        start_line: int,
        root_node: 'Node',
        source_code: str
    ) -> List[InheritanceRelation]:
        """Extract base classes from Python class definition."""
        relations = []

        # Find the class definition node
        class_node = self._find_class_node(root_node, class_name, start_line, "python")
        if not class_node:
            return relations

        # Python: class Foo(Base1, Base2):
        # Look for argument_list in class_definition
        for child in class_node.children:
            if child.type == "argument_list":
                base_classes = []
                for arg in child.children:
                    if arg.type in ("identifier", "attribute"):
                        base_name = source_code[arg.start_byte:arg.end_byte]
                        base_classes.append(base_name)

                if base_classes:
                    relations.append(InheritanceRelation(
                        child_class=class_name,
                        child_file=file_path,
                        child_line=start_line,
                        base_classes=base_classes,
                        confidence=self.config["confidence_direct"],
                        resolution_method="ast_extraction"
                    ))
                    logger.debug(f"Found inheritance: {class_name} -> {base_classes}")

        return relations

    def _extract_js_ts_inheritance(
        self,
        class_name: str,
        file_path: str,
        start_line: int,
        root_node: 'Node',
        source_code: str,
        language: str
    ) -> List[InheritanceRelation]:
        """Extract base classes from JavaScript/TypeScript class definition."""
        relations = []

        # Find the class definition node
        class_node = self._find_class_node(root_node, class_name, start_line, language)
        if not class_node:
            return relations

        # JS/TS: class Foo extends Bar implements Baz
        base_classes = []

        # Look for class_heritage
        for child in class_node.children:
            if child.type == "class_heritage":
                for heritage_child in child.children:
                    if heritage_child.type == "extends_clause":
                        # Get the extended class
                        for token in heritage_child.children:
                            if token.type in ("identifier", "member_expression"):
                                base_name = source_code[token.start_byte:token.end_byte]
                                base_classes.append(base_name)

                    # TypeScript: implements clause
                    if heritage_child.type == "implements_clause" and language == "typescript":
                        for token in heritage_child.children:
                            if token.type == "type_identifier":
                                interface_name = source_code[token.start_byte:token.end_byte]
                                base_classes.append(interface_name)

        if base_classes:
            relations.append(InheritanceRelation(
                child_class=class_name,
                child_file=file_path,
                child_line=start_line,
                base_classes=base_classes,
                confidence=self.config["confidence_direct"],
                resolution_method="ast_extraction"
            ))
            logger.debug(f"Found inheritance: {class_name} -> {base_classes}")

        return relations

    def _find_class_node(
        self,
        root_node: 'Node',
        class_name: str,
        line: int,
        language: str
    ) -> Optional['Node']:
        """Find the AST node for a class definition."""
        node_type = "class_definition" if language == "python" else "class_declaration"

        def search(node: 'Node') -> Optional['Node']:
            # Check if this is the class we're looking for
            if node.type == node_type:
                # Check line number (tree-sitter lines are 0-indexed)
                if node.start_point[0] + 1 == line:
                    # Verify class name
                    for child in node.children:
                        if child.type in ("identifier", "type_identifier"):
                            # This should be the class name
                            return node

            # Recursively search children
            for child in node.children:
                result = search(child)
                if result:
                    return result

            return None

        return search(root_node)

    def _detect_language(self, extension: str) -> Optional[str]:
        """Detect language from file extension."""
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        return ext_map.get(extension.lower())

    def update_inheritance_references(self, relations: List[InheritanceRelation]) -> int:
        """
        Write inheritance relations to the symbol_references table.

        Args:
            relations: List of InheritanceRelation objects

        Returns:
            Number of references created
        """
        if not relations:
            return 0

        logger.info(f"Phase 6.1: Writing {len(relations)} inheritance relations...")

        # Convert to SymbolReference objects
        references: List[SymbolReference] = []

        for relation in relations:
            for base_class in relation.base_classes:
                # Try to resolve base class to a definition in the index
                target_file, target_symbol = self._resolve_base_class(
                    base_class, relation.child_file
                )

                # Determine confidence based on resolution
                confidence = relation.confidence
                if target_file:
                    # Successfully resolved to definition
                    confidence = self.config["confidence_imported"] if target_file != relation.child_file else confidence
                else:
                    # Unresolved (likely external)
                    confidence = self.config["confidence_external"]
                    target_symbol = base_class

                references.append(SymbolReference(
                    source_file=relation.child_file,
                    source_line=relation.child_line,
                    source_symbol=relation.child_class,
                    reference_type="inherits",
                    target_file=target_file,
                    target_symbol=target_symbol,
                    target_type="class",
                    confidence=confidence,
                    resolution_method=relation.resolution_method
                ))

        # Write to database in batch
        self.store.write_symbol_references_batch(references)

        logger.info(f"Phase 6.1: Created {len(references)} inheritance references")
        return len(references)

    def _resolve_base_class(
        self,
        base_class_name: str,
        source_file: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve a base class name to its definition in the index.

        Args:
            base_class_name: Name of the base class
            source_file: File where the inheritance is declared

        Returns:
            Tuple of (target_file, target_symbol) or (None, None) if not found
        """
        conn = self.store._get_connection()
        try:
            # Strategy 1: Same file
            cursor = conn.execute("""
                SELECT file_path, name
                FROM symbols
                WHERE name = ? AND file_path = ? AND type = 'class'
                LIMIT 1
            """, (base_class_name, source_file))
            result = cursor.fetchone()
            if result:
                return result[0], result[1]

            # Strategy 2: Check imports in source file
            cursor = conn.execute("""
                SELECT il.definition_file, il.definition_symbol
                FROM import_links il
                WHERE il.importer_file = ?
                AND il.definition_symbol = ?
                AND il.definition_file IS NOT NULL
                LIMIT 1
            """, (source_file, base_class_name))
            result = cursor.fetchone()
            if result:
                return result[0], result[1]

            # Strategy 3: Search in same package (heuristic)
            source_dir = str(Path(source_file).parent)
            cursor = conn.execute("""
                SELECT file_path, name
                FROM symbols
                WHERE name = ? AND type = 'class'
                AND file_path LIKE ?
                LIMIT 1
            """, (base_class_name, f"{source_dir}%"))
            result = cursor.fetchone()
            if result:
                return result[0], result[1]

            # Not found - likely external
            return None, None

        finally:
            conn.close()
