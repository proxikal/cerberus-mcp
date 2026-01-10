"""
CodeValidator: Four Pillars of Integrity validation.

Phase 11: Pillars 2-4 - Syntax, Semantic, Import validation.
"""

from typing import Tuple, List, Optional

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


class CodeValidator:
    """
    Validate code mutations for safety and correctness.

    Four Pillars of Integrity:
    1. Auto-Indentation - Handled by CodeFormatter
    2. Syntax Verification - Parse and check for ERROR nodes
    3. Semantic Integrity - Query index for undefined symbols
    4. Import Guardian - Check for missing imports
    """

    def __init__(self, store: Optional[SQLiteIndexStore] = None):
        """
        Initialize validator with optional store.

        Args:
            store: SQLite index store for semantic checks
        """
        self.store = store
        self.parsers = {}
        if TREE_SITTER_AVAILABLE:
            self._init_parsers()
        else:
            logger.warning("tree-sitter not available, validation limited")

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

            logger.debug(f"CodeValidator initialized parsers")
        except Exception as e:
            logger.error(f"Failed to initialize parsers: {e}")
            self.parsers = {}

    def dry_run_validation(
        self,
        file_path: str,
        modified_code: str,
        language: str,
        store: Optional[SQLiteIndexStore] = None
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Perform dry-run validation without saving.

        Args:
            file_path: Path to file being modified
            modified_code: Modified code content
            language: Language ("python", "javascript", "typescript")
            store: Optional store for semantic checks

        Returns:
            (success, errors, warnings)
        """
        errors = []
        warnings = []

        # Pillar 2: Syntax Verification
        syntax_valid, syntax_errors = self.validate_syntax(modified_code, language)
        if not syntax_valid:
            errors.extend(syntax_errors)
            # Stop here if syntax is invalid
            return False, errors, warnings

        # Pillar 3: Semantic Integrity (warning-only by default)
        active_store = store or self.store
        if active_store:
            undefined_symbols = self.check_undefined_symbols(
                modified_code,
                language,
                active_store
            )
            if undefined_symbols:
                warnings.extend([
                    f"Undefined symbol: {sym}" for sym in undefined_symbols
                ])

        # Pillar 4: Import Guardian (checked in ImportManager)
        # This is a placeholder - actual import injection is handled separately

        success = len(errors) == 0
        return success, errors, warnings

    def validate_syntax(
        self,
        code: str,
        language: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate syntax by parsing and checking for ERROR nodes.

        Args:
            code: Code to validate
            language: Language name

        Returns:
            (is_valid, error_messages)
        """
        if language not in self.parsers:
            logger.warning(f"No parser for {language}, skipping syntax check")
            return True, []

        parser = self.parsers[language]

        try:
            tree = parser.parse(bytes(code, "utf8"))
            root_node = tree.root_node

            # Find all ERROR nodes
            error_nodes = self._find_error_nodes(root_node)

            if error_nodes:
                errors = []
                for error_node in error_nodes:
                    line = error_node.start_point[0] + 1
                    col = error_node.start_point[1] + 1
                    errors.append(f"Syntax error at line {line}, column {col}")
                return False, errors

            return True, []

        except Exception as e:
            logger.error(f"Failed to parse code: {e}")
            return False, [f"Parse error: {e}"]

    def check_undefined_symbols(
        self,
        code: str,
        language: str,
        store: SQLiteIndexStore
    ) -> List[str]:
        """
        Check for undefined symbol references.

        Args:
            code: Code to check
            language: Language name
            store: Index store for symbol lookups

        Returns:
            List of undefined symbol names
        """
        # For now, return empty list
        # Full implementation would:
        # 1. Parse code and extract all identifier references
        # 2. Query store to check if each symbol is defined
        # 3. Filter out built-ins and stdlib symbols
        # 4. Return list of undefined symbols

        # This is a simplified placeholder
        return []

    def _find_error_nodes(self, node: Node) -> List[Node]:
        """
        Recursively find all ERROR nodes in AST.

        Args:
            node: Root node to search from

        Returns:
            List of ERROR nodes
        """
        errors = []
        if node.type == "ERROR" or node.is_missing:
            errors.append(node)

        for child in node.children:
            errors.extend(self._find_error_nodes(child))

        return errors

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
