"""
ImportManager: Auto-inject missing imports.

Phase 11: Pillar 4 - Import Guardian.
"""

from typing import List, Set, Optional, Tuple
from pathlib import Path

try:
    from tree_sitter import Parser, Language, Node
    import tree_sitter_python as tspython
    import tree_sitter_javascript as tsjavascript
    import tree_sitter_typescript as tstypescript
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

from cerberus.logging_config import logger
from cerberus.storage.sqlite_store import SQLiteIndexStore


class ImportManager:
    """
    Manage imports and auto-inject missing dependencies.

    Features:
    - Parse code to extract identifier references
    - Query index to resolve symbol definitions
    - Generate import statements
    - Insert imports at appropriate location
    """

    def __init__(self, store: Optional[SQLiteIndexStore] = None):
        """
        Initialize import manager.

        Args:
            store: SQLite index store for symbol resolution
        """
        self.store = store
        self.parsers = {}
        if TREE_SITTER_AVAILABLE:
            self._init_parsers()
        else:
            logger.warning("tree-sitter not available, import management limited")

    def _init_parsers(self):
        """Initialize tree-sitter parsers."""
        try:
            python_parser = Parser()
            python_parser.language = Language(tspython.language())
            self.parsers["python"] = python_parser

            js_parser = Parser()
            js_parser.language = Language(tsjavascript.language())
            self.parsers["javascript"] = js_parser

            ts_parser = Parser()
            ts_parser.language = Language(tstypescript.language_typescript())
            self.parsers["typescript"] = ts_parser

            logger.debug("ImportManager initialized parsers")
        except Exception as e:
            logger.error(f"Failed to initialize parsers: {e}")
            self.parsers = {}

    def analyze_dependencies(
        self,
        code: str,
        language: str,
        store: Optional[SQLiteIndexStore] = None
    ) -> List[str]:
        """
        Analyze code and return list of required imports.

        Args:
            code: Code to analyze
            language: Language name
            store: Optional store for symbol resolution

        Returns:
            List of import statements needed
        """
        # Placeholder implementation
        # Full version would:
        # 1. Parse code and extract all identifier nodes
        # 2. Query store to find where each symbol is defined
        # 3. Generate import statements based on definitions
        # 4. Return list of import lines

        # For Phase 11.1, return empty list
        # This can be extended in future iterations
        return []

    def inject_imports(
        self,
        file_path: str,
        content: str,
        imports: List[str],
        language: str
    ) -> str:
        """
        Inject import statements into file content.

        Args:
            file_path: Path to file
            content: File content
            imports: List of import statements to inject
            language: Language name

        Returns:
            Modified content with imports injected
        """
        if not imports:
            return content

        # Find insertion point (after existing imports)
        insertion_point = self._find_import_insertion_point(content, language)

        # Build import block
        import_block = '\n'.join(imports) + '\n'

        # Insert imports
        modified_content = (
            content[:insertion_point] +
            import_block +
            content[insertion_point:]
        )

        return modified_content

    def _find_import_insertion_point(self, content: str, language: str) -> int:
        """
        Find the byte offset where imports should be inserted.

        Args:
            content: File content
            language: Language name

        Returns:
            Byte offset for insertion
        """
        lines = content.split('\n')

        # Find last import/require line
        last_import_line = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if language == "python":
                if stripped.startswith('import ') or stripped.startswith('from '):
                    last_import_line = i
            elif language in ["javascript", "typescript"]:
                if stripped.startswith('import ') or stripped.startswith('require('):
                    last_import_line = i

        # If imports found, insert after last import
        if last_import_line >= 0:
            # Calculate byte offset
            offset = sum(len(line) + 1 for line in lines[:last_import_line + 1])
            return offset

        # Otherwise, insert at beginning (after shebang/docstring if present)
        # Simplified: insert at beginning
        return 0

    def _extract_identifiers(self, code: str, language: str) -> Set[str]:
        """
        Extract all identifier references from code.

        Args:
            code: Code to analyze
            language: Language name

        Returns:
            Set of identifier names
        """
        if language not in self.parsers:
            return set()

        parser = self.parsers[language]

        try:
            tree = parser.parse(bytes(code, "utf8"))
            identifiers = set()

            def visit(node: Node):
                if node.type == "identifier":
                    identifiers.add(node.text.decode('utf8'))
                for child in node.children:
                    visit(child)

            visit(tree.root_node)
            return identifiers

        except Exception as e:
            logger.error(f"Failed to extract identifiers: {e}")
            return set()
