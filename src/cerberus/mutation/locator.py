"""
SymbolLocator: Map symbol names to precise AST byte ranges.

Phase 11: Core component for surgical editing.
"""

from pathlib import Path
from typing import Optional, List, Dict

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
from cerberus.schemas import SymbolLocation, CodeSymbol


class SymbolLocator:
    """
    Locate symbols by name and return precise AST byte ranges.

    Reuses tree-sitter infrastructure from synthesis/skeletonizer.py.
    """

    def __init__(self, store: Optional[SQLiteIndexStore] = None):
        """
        Initialize symbol locator with optional store.

        Args:
            store: SQLite index store for symbol queries
        """
        self.store = store
        self.parsers: Dict[str, Parser] = {}
        if TREE_SITTER_AVAILABLE:
            self._init_parsers()
        else:
            logger.warning("tree-sitter not available, symbol location disabled")

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

            logger.debug(f"SymbolLocator initialized parsers: {list(self.parsers.keys())}")
        except Exception as e:
            logger.error(f"Failed to initialize parsers: {e}")
            self.parsers = {}

    def locate_symbol(
        self,
        file_path: str,
        symbol_name: str,
        symbol_type: Optional[str] = None,
        parent_class: Optional[str] = None,
        store: Optional[SQLiteIndexStore] = None
    ) -> Optional[SymbolLocation]:
        """
        Locate a symbol by name and return its precise byte range.

        Args:
            file_path: Path to source file
            symbol_name: Symbol name to locate
            symbol_type: Optional symbol type filter ("function", "class", etc.)
            parent_class: Optional parent class for methods
            store: Optional SQLite store (overrides self.store)

        Returns:
            SymbolLocation with byte ranges or None if not found
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        # Use provided store or fall back to self.store
        active_store = store or self.store

        # Query index for symbol metadata (start_line, type)
        symbol_info = self._query_symbol(
            active_store,
            file_path,
            symbol_name,
            symbol_type,
            parent_class
        )

        if not symbol_info:
            logger.warning(f"Symbol '{symbol_name}' not found in index for {file_path}")
            return None

        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None

        # Detect language
        language = self._detect_language(path.suffix)
        if not language or language not in self.parsers:
            logger.error(f"Unsupported language for {file_path}")
            return None

        # Parse file with tree-sitter
        parser = self.parsers[language]
        tree = parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node

        # Find the AST node for this symbol
        target_node = self._find_symbol_node(
            root_node,
            symbol_name,
            symbol_info.type,
            symbol_info.start_line,
            parent_class
        )

        if not target_node:
            logger.warning(f"Could not locate AST node for '{symbol_name}' at line {symbol_info.start_line}")
            return None

        # Extract byte ranges and indentation
        start_byte = target_node.start_byte
        end_byte = target_node.end_byte
        start_line = target_node.start_point[0] + 1  # tree-sitter is 0-indexed
        end_line = target_node.end_point[0] + 1

        # Calculate indentation level
        first_line = source_code.split('\n')[start_line - 1] if start_line > 0 else ""
        indent = self._get_indent(first_line)
        indent_level = len(indent) // 4  # Assume 4-space indent

        return SymbolLocation(
            file_path=file_path,
            symbol_name=symbol_name,
            symbol_type=symbol_info.type,
            start_byte=start_byte,
            end_byte=end_byte,
            start_line=start_line,
            end_line=end_line,
            indentation_level=indent_level,
            language=language,
            parent_class=parent_class
        )

    def _query_symbol(
        self,
        store: Optional[SQLiteIndexStore],
        file_path: str,
        symbol_name: str,
        symbol_type: Optional[str],
        parent_class: Optional[str]
    ) -> Optional[CodeSymbol]:
        """Query index for symbol metadata."""
        if not store:
            logger.warning("No store provided for symbol query")
            return None

        # Normalize file path to handle symlinks (e.g., /var vs /private/var on macOS)
        normalized_path = str(Path(file_path).resolve())

        # Build filter dict for query
        filter_dict = {
            "name": symbol_name,
            "file_path": normalized_path
        }
        if symbol_type:
            filter_dict["type"] = symbol_type

        # Query symbols from store
        symbols = list(store.query_symbols(filter=filter_dict))

        if not symbols:
            return None

        # Filter by parent class if specified
        if parent_class:
            symbols = [s for s in symbols if getattr(s, 'parent_class', None) == parent_class]

        if not symbols:
            return None

        # Return first match (it's already a CodeSymbol)
        return symbols[0]

    def _find_symbol_node(
        self,
        root: Node,
        symbol_name: str,
        symbol_type: str,
        expected_line: int,
        parent_class: Optional[str]
    ) -> Optional[Node]:
        """
        Find the AST node for a symbol.

        Args:
            root: Root AST node
            symbol_name: Symbol name to find
            symbol_type: Symbol type ("function", "class", "method")
            expected_line: Expected line number from index (1-indexed)
            parent_class: Optional parent class for methods

        Returns:
            AST node or None
        """
        # Map symbol type to AST node types
        node_type_map = {
            "function": ["function_definition", "function_declaration"],
            "class": ["class_definition", "class_declaration"],
            "method": ["function_definition", "method_definition"],
        }

        target_types = node_type_map.get(symbol_type, [])
        if not target_types:
            logger.warning(f"Unknown symbol type: {symbol_type}")
            return None

        # Find all nodes of target types
        candidates = self._find_nodes_by_type(root, target_types)

        # Filter by name and line number
        for node in candidates:
            node_name = self._get_node_name(node)
            node_line = node.start_point[0] + 1  # Convert to 1-indexed

            if node_name == symbol_name and abs(node_line - expected_line) <= 1:
                # Found matching node
                logger.debug(f"Located node '{symbol_name}' at byte {node.start_byte}-{node.end_byte}")
                return node

        return None

    def _find_nodes_by_type(self, node: Node, types: List[str]) -> List[Node]:
        """
        Recursively find all nodes of given types.

        Reused from synthesis/skeletonizer.py:311-318.
        """
        result = []
        if node.type in types:
            result.append(node)
        for child in node.children:
            result.extend(self._find_nodes_by_type(child, types))
        return result

    def _get_node_name(self, node: Node) -> str:
        """
        Extract name/identifier from an AST node.

        Reused pattern from synthesis/skeletonizer.py:320-325.
        """
        # For function_definition, class_definition, look for identifier child
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode('utf8')
        return ""

    def _get_indent(self, line: str) -> str:
        """
        Extract indentation from a line.

        Reused from synthesis/skeletonizer.py:335-337.
        """
        return line[:len(line) - len(line.lstrip())]

    def _detect_language(self, extension: str) -> Optional[str]:
        """
        Detect language from file extension.

        Reused from synthesis/skeletonizer.py:123-132.
        """
        ext_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
        }
        return ext_map.get(extension.lower())
