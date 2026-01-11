import ast
import re
from pathlib import Path
from typing import List, Optional

from cerberus.logging_config import logger
from cerberus.parser.config import LANGUAGE_QUERIES
from cerberus.schemas import CodeSymbol


def parse_python_file(file_path: Path, content: str) -> List[CodeSymbol]:
    """
    Parse Python file using AST for accurate symbol extraction.

    Phase 16.3: Upgraded from regex to AST for proper parent_class tracking.
    This enables high-quality method call resolution.

    Args:
        file_path: Path to the Python file
        content: File content

    Returns:
        List of CodeSymbol objects with accurate type and parent_class
    """
    # Normalize file path to handle symlinks (e.g., /var vs /private/var on macOS)
    normalized_path = str(file_path.resolve())

    try:
        # Phase 16.3: Use AST parsing for accurate symbol extraction
        tree = ast.parse(content, filename=str(file_path))
        symbols = _extract_symbols_ast(tree, normalized_path, content)
        logger.debug(f"AST parser extracted {len(symbols)} symbols from {file_path.name}")
        return symbols
    except SyntaxError as e:
        # Fallback to regex for files with syntax errors
        logger.warning(f"AST parse failed for {file_path.name}: {e}. Falling back to regex.")
        return _parse_python_file_regex(file_path, content, normalized_path)
    except Exception as e:
        logger.error(f"Failed to parse {file_path.name}: {e}")
        return []


def _extract_symbols_ast(tree: ast.AST, file_path: str, content: str) -> List[CodeSymbol]:
    """
    Extract symbols from AST tree.

    Args:
        tree: AST tree
        file_path: Normalized file path
        content: File content (for calculating end lines)

    Returns:
        List of CodeSymbol objects
    """
    symbols = []

    class SymbolVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_class: Optional[str] = None
            self.class_stack: List[str] = []

        def visit_ClassDef(self, node: ast.ClassDef):
            # Extract class symbol
            symbols.append(CodeSymbol(
                name=node.name,
                type="class",
                file_path=file_path,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                signature=None,
                return_type=None,
                parameters=None,
                parent_class=None,
            ))

            # Track current class for method detection
            self.class_stack.append(node.name)
            self.current_class = node.name

            # Visit children (methods, nested classes)
            self.generic_visit(node)

            # Pop class from stack
            self.class_stack.pop()
            self.current_class = self.class_stack[-1] if self.class_stack else None

        def visit_FunctionDef(self, node: ast.FunctionDef):
            # Determine if this is a method or function
            is_method = self.current_class is not None
            symbol_type = "method" if is_method else "function"

            # Extract signature
            signature = _extract_signature(node)

            # Extract return type
            return_type = None
            if node.returns:
                return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else None

            # Extract parameters and their types
            parameters = [arg.arg for arg in node.args.args]
            parameter_types = {}
            if hasattr(ast, 'unparse'):
                for arg in node.args.args:
                    if arg.annotation:
                        try:
                            parameter_types[arg.arg] = ast.unparse(arg.annotation)
                        except Exception:
                            pass  # Skip malformed annotations

            symbols.append(CodeSymbol(
                name=node.name,
                type=symbol_type,
                file_path=file_path,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                signature=signature,
                return_type=return_type,
                parameters=parameters if parameters else None,
                parameter_types=parameter_types if parameter_types else None,
                parent_class=self.current_class,
            ))

            # Don't visit nested functions (they're rarely relevant for symbol indexing)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            # Treat async functions the same as regular functions
            self.visit_FunctionDef(node)

    visitor = SymbolVisitor()
    visitor.visit(tree)

    return symbols


def _extract_signature(node: ast.FunctionDef) -> Optional[str]:
    """
    Extract function signature from AST node.

    Args:
        node: FunctionDef AST node

    Returns:
        Function signature string or None
    """
    try:
        if hasattr(ast, 'unparse'):
            # Python 3.9+ has ast.unparse
            args_str = ast.unparse(node.args)
            if node.returns:
                return_str = ast.unparse(node.returns)
                return f"({args_str}) -> {return_str}"
            return f"({args_str})"
        else:
            # Fallback for older Python: basic signature
            args = [arg.arg for arg in node.args.args]
            return f"({', '.join(args)})"
    except Exception:
        return None


def _parse_python_file_regex(file_path: Path, content: str, normalized_path: str) -> List[CodeSymbol]:
    """
    Fallback regex-based parser for files with syntax errors.

    Args:
        file_path: Path object
        content: File content
        normalized_path: Normalized file path string

    Returns:
        List of CodeSymbol objects (without parent_class)
    """
    symbols: List[CodeSymbol] = []
    queries = LANGUAGE_QUERIES.get("python", {})

    for symbol_type, regex_pattern in queries.items():
        for match in regex_pattern.finditer(content):
            symbol_name = match.group(1)

            # Find the line number by counting newlines before the symbol name
            name_start = match.start(1)
            line_number = content.count('\n', 0, name_start) + 1

            symbols.append(
                CodeSymbol(
                    name=symbol_name,
                    type=symbol_type,
                    file_path=normalized_path,
                    start_line=line_number,
                    end_line=line_number,
                )
            )
            logger.debug(f"Found symbol (regex): {symbol_name} ({symbol_type}) on line {line_number}")

    return symbols
