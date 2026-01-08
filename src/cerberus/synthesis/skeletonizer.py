"""
AST-aware code skeletonization using tree-sitter.
Removes function/method bodies while preserving structure.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

try:
    from tree_sitter import Parser, Node, Language
    import tree_sitter_python as tspython
    import tree_sitter_javascript as tsjavascript
    import tree_sitter_typescript as tstypescript
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logger.warning("tree-sitter not available, skeletonization will be limited")

from ..schemas import SkeletonizedCode
from .config import SKELETONIZATION_CONFIG, BODY_REPLACEMENTS


class Skeletonizer:
    """
    AST-aware code skeletonizer that removes implementation while preserving structure.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize skeletonizer with optional configuration.

        Args:
            config: Optional configuration overrides
        """
        self.config = {**SKELETONIZATION_CONFIG, **(config or {})}
        self.parsers: Dict[str, Parser] = {}

        if TREE_SITTER_AVAILABLE:
            self._init_parsers()
        else:
            logger.warning("Tree-sitter not available, skeletonization disabled")

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

            logger.debug(f"Initialized parsers: {list(self.parsers.keys())}")
        except Exception as e:
            logger.error(f"Failed to initialize parsers: {e}")
            self.parsers = {}

    def skeletonize_file(
        self,
        file_path: str,
        preserve_symbols: Optional[List[str]] = None
    ) -> SkeletonizedCode:
        """
        Skeletonize a source code file.

        Args:
            file_path: Path to the source file
            preserve_symbols: List of symbol names to preserve fully (not skeletonize)

        Returns:
            SkeletonizedCode object with skeletonized content
        """
        preserve_symbols = preserve_symbols or []
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Detect language from extension
        language = self._detect_language(path.suffix)

        if not language or language not in self.parsers:
            logger.warning(f"Unsupported language for {file_path}, returning original")
            return SkeletonizedCode(
                file_path=file_path,
                original_lines=len(source_code.splitlines()),
                skeleton_lines=len(source_code.splitlines()),
                content=source_code,
                preserved_symbols=preserve_symbols,
                pruned_symbols=[],
                compression_ratio=1.0
            )

        # Parse and skeletonize
        skeleton = self._skeletonize(source_code, language, preserve_symbols)

        skeleton_lines = len(skeleton.splitlines())
        original_lines = len(source_code.splitlines())

        return SkeletonizedCode(
            file_path=file_path,
            original_lines=original_lines,
            skeleton_lines=skeleton_lines,
            content=skeleton,
            preserved_symbols=preserve_symbols,
            pruned_symbols=self._extract_pruned_symbols(source_code, language),
            compression_ratio=skeleton_lines / original_lines if original_lines > 0 else 1.0
        )

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

    def _skeletonize(
        self,
        source_code: str,
        language: str,
        preserve_symbols: List[str]
    ) -> str:
        """
        Skeletonize source code using AST.

        Args:
            source_code: Source code to skeletonize
            language: Programming language
            preserve_symbols: Symbols to preserve fully

        Returns:
            Skeletonized source code
        """
        parser = self.parsers.get(language)
        if not parser:
            return source_code

        # Parse source code
        tree = parser.parse(bytes(source_code, "utf8"))

        # Process AST and build skeleton
        if language == "python":
            skeleton = self._skeletonize_python(source_code, tree, preserve_symbols)
        elif language in ["javascript", "typescript"]:
            skeleton = self._skeletonize_js_ts(source_code, tree, preserve_symbols, language)
        else:
            skeleton = source_code

        return skeleton

    def _skeletonize_python(
        self,
        source_code: str,
        tree,
        preserve_symbols: List[str]
    ) -> str:
        """
        Skeletonize Python code.

        Keeps:
        - Function/method signatures
        - Docstrings
        - Type annotations
        - Decorators
        - Class definitions
        - Module-level constants

        Removes:
        - Function/method bodies (replaced with ...)
        """
        lines = source_code.splitlines(keepends=True)
        result_lines = list(lines)  # Copy of original lines

        # Find all function/method definitions
        functions = self._find_nodes_by_type(tree.root_node, ["function_definition"])

        for func_node in functions:
            func_name = self._get_function_name(func_node)

            # Skip if this function should be preserved
            if func_name in preserve_symbols:
                continue

            # Find the function body
            body_node = None
            for child in func_node.children:
                if child.type == "block":
                    body_node = child
                    break

            if not body_node:
                continue

            # Get the body range
            body_start_line = body_node.start_point[0]
            body_end_line = body_node.end_point[0]

            # Check if body is small enough to skip skeletonization
            body_line_count = body_end_line - body_start_line + 1
            if body_line_count <= self.config["min_lines_to_skeletonize"]:
                continue

            # Extract docstring if present
            docstring_end_line = None
            first_stmt = None
            for child in body_node.children:
                if child.type == "expression_statement":
                    first_stmt = child
                    break

            if first_stmt and self._is_docstring(first_stmt):
                docstring_end_line = first_stmt.end_point[0]

            # Determine where to insert ellipsis
            if self.config["keep_docstrings"] and docstring_end_line is not None:
                # Replace everything after docstring
                replacement_line = docstring_end_line + 1
            else:
                # Replace entire body
                replacement_line = body_start_line

            # Create replacement
            indent = self._get_indent(lines[replacement_line] if replacement_line < len(lines) else "")
            replacement = f"{indent}{self.config['replace_body_with']}\n"

            # Replace body lines with ellipsis
            if replacement_line < body_end_line:
                # Keep lines up to replacement_line, add ellipsis, skip rest
                for i in range(replacement_line + 1, body_end_line + 1):
                    result_lines[i] = ""
                result_lines[replacement_line] = replacement

        # Filter out empty lines at the end of blocks
        result = "".join(result_lines)
        return result

    def _skeletonize_js_ts(
        self,
        source_code: str,
        tree,
        preserve_symbols: List[str],
        language: str
    ) -> str:
        """Skeletonize JavaScript/TypeScript code."""
        lines = source_code.splitlines(keepends=True)
        result_lines = list(lines)

        # Find all function declarations and method definitions
        function_types = [
            "function_declaration",
            "method_definition",
            "arrow_function",
            "function"
        ]
        functions = self._find_nodes_by_type(tree.root_node, function_types)

        replacement_marker = BODY_REPLACEMENTS[language]

        for func_node in functions:
            func_name = self._get_function_name(func_node)

            if func_name in preserve_symbols:
                continue

            # Find function body
            body_node = None
            for child in func_node.children:
                if child.type == "statement_block":
                    body_node = child
                    break

            if not body_node:
                continue

            body_start_line = body_node.start_point[0]
            body_end_line = body_node.end_point[0]

            # Skip small bodies
            if body_end_line - body_start_line <= self.config["min_lines_to_skeletonize"]:
                continue

            # Replace body
            indent = self._get_indent(lines[body_start_line + 1] if body_start_line + 1 < len(lines) else "")
            replacement = f"{indent}{replacement_marker}\n"

            # Replace body lines
            for i in range(body_start_line + 1, body_end_line):
                result_lines[i] = ""
            if body_start_line + 1 < len(result_lines):
                result_lines[body_start_line + 1] = replacement

        return "".join(result_lines)

    def _find_nodes_by_type(self, node: 'Node', types: List[str]) -> List['Node']:
        """Recursively find all nodes of given types."""
        result = []
        if node.type in types:
            result.append(node)
        for child in node.children:
            result.extend(self._find_nodes_by_type(child, types))
        return result

    def _get_function_name(self, node: 'Node') -> str:
        """Extract function name from function node."""
        for child in node.children:
            if child.type == "identifier":
                return child.text.decode('utf8')
        return ""

    def _is_docstring(self, node: 'Node') -> bool:
        """Check if node is a docstring."""
        if node.type == "expression_statement":
            for child in node.children:
                if child.type == "string":
                    return True
        return False

    def _get_indent(self, line: str) -> str:
        """Extract indentation from a line."""
        return line[:len(line) - len(line.lstrip())]

    def _extract_pruned_symbols(self, source_code: str, language: str) -> List[str]:
        """Extract list of symbols that would be pruned."""
        parser = self.parsers.get(language)
        if not parser:
            return []

        tree = parser.parse(bytes(source_code, "utf8"))

        if language == "python":
            function_types = ["function_definition"]
        else:
            function_types = ["function_declaration", "method_definition"]

        functions = self._find_nodes_by_type(tree.root_node, function_types)
        return [self._get_function_name(f) for f in functions]


def skeletonize_file(
    file_path: str,
    preserve_symbols: Optional[List[str]] = None,
    config: Optional[Dict[str, Any]] = None
) -> SkeletonizedCode:
    """
    Convenience function to skeletonize a file.

    Args:
        file_path: Path to source file
        preserve_symbols: Symbol names to preserve fully
        config: Optional configuration overrides

    Returns:
        SkeletonizedCode object
    """
    skeletonizer = Skeletonizer(config=config)
    return skeletonizer.skeletonize_file(file_path, preserve_symbols)
