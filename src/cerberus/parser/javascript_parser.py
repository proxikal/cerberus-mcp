"""
JavaScript parser using tree-sitter for accurate symbol extraction.

Extracts:
- Classes and methods
- Functions (regular, arrow, async)
- Variables (const, let, var with function assignments)
- Exports
"""
from pathlib import Path
from typing import List, Optional
import re

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol

try:
    from tree_sitter import Language, Parser
    import tree_sitter_javascript as tsjavascript
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logger.warning("tree-sitter not available for JavaScript parsing, falling back to regex")


def parse_javascript_file(file_path: Path, content: str) -> List[CodeSymbol]:
    """
    Parse JavaScript file using tree-sitter for accurate symbol extraction.

    Args:
        file_path: Path to the JavaScript file
        content: File content

    Returns:
        List of CodeSymbol objects with accurate type and parent_class
    """
    normalized_path = str(file_path.resolve())

    if TREE_SITTER_AVAILABLE:
        try:
            parser = Parser()
            parser.language = Language(tsjavascript.language())
            tree = parser.parse(bytes(content, "utf8"))
            symbols = _extract_symbols_treesitter(tree, normalized_path, content)
            logger.debug(f"Tree-sitter extracted {len(symbols)} symbols from {file_path.name}")
            return symbols
        except Exception as e:
            logger.warning(f"Tree-sitter parse failed for {file_path.name}: {e}. Falling back to regex.")
            return _parse_javascript_file_regex(file_path, content, normalized_path)
    else:
        return _parse_javascript_file_regex(file_path, content, normalized_path)


def _extract_symbols_treesitter(tree, file_path: str, content: str) -> List[CodeSymbol]:
    """
    Extract symbols from tree-sitter AST.

    Args:
        tree: Tree-sitter tree
        file_path: Normalized file path
        content: File content

    Returns:
        List of CodeSymbol objects
    """
    symbols: List[CodeSymbol] = []
    current_class: Optional[str] = None
    lines = content.split('\n')

    def visit_node(node, parent_class=None):
        nonlocal current_class

        # Class declarations
        if node.type == "class_declaration":
            class_name_node = node.child_by_field_name("name")
            if class_name_node:
                class_name = class_name_node.text.decode('utf8')
                symbols.append(CodeSymbol(
                    name=class_name,
                    type="class",
                    file_path=file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    signature=None,
                    return_type=None,
                    parameters=None,
                    parent_class=None,
                ))

                # Visit class body with current class context
                body = node.child_by_field_name("body")
                if body:
                    for child in body.children:
                        visit_node(child, class_name)

        # Method definitions (inside classes)
        elif node.type == "method_definition" and parent_class:
            name_node = node.child_by_field_name("name")
            if name_node:
                method_name = name_node.text.decode('utf8')

                # Extract parameters
                parameters = _extract_parameters(node)
                signature = f"({', '.join(parameters)})" if parameters else "()"

                # Check if async
                is_async = any(child.type == "async" for child in node.children)
                if is_async:
                    signature = f"async {signature}"

                symbols.append(CodeSymbol(
                    name=method_name,
                    type="method",
                    file_path=file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    signature=signature,
                    return_type=None,
                    parameters=parameters if parameters else None,
                    parent_class=parent_class,
                ))

        # Function declarations
        elif node.type == "function_declaration":
            name_node = node.child_by_field_name("name")
            if name_node:
                func_name = name_node.text.decode('utf8')

                # Extract parameters
                parameters = _extract_parameters(node)
                signature = f"({', '.join(parameters)})" if parameters else "()"

                # Check if async
                is_async = any(child.type == "async" for child in node.children)
                if is_async:
                    signature = f"async {signature}"

                symbols.append(CodeSymbol(
                    name=func_name,
                    type="function",
                    file_path=file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    signature=signature,
                    return_type=None,
                    parameters=parameters if parameters else None,
                    parent_class=None,
                ))

        # Variable declarations with function expressions or arrow functions
        elif node.type == "lexical_declaration":  # const, let
            for declarator in node.children:
                if declarator.type == "variable_declarator":
                    name_node = declarator.child_by_field_name("name")
                    value_node = declarator.child_by_field_name("value")

                    if name_node and value_node:
                        var_name = name_node.text.decode('utf8')

                        # Check if value is a function
                        if value_node.type in ("arrow_function", "function_expression"):
                            parameters = _extract_parameters(value_node)
                            signature = f"({', '.join(parameters)})" if parameters else "()"

                            # Check if async
                            is_async = any(child.type == "async" for child in value_node.children)
                            if is_async:
                                signature = f"async {signature}"

                            symbols.append(CodeSymbol(
                                name=var_name,
                                type="function",
                                file_path=file_path,
                                start_line=node.start_point[0] + 1,
                                end_line=node.end_point[0] + 1,
                                signature=signature,
                                return_type=None,
                                parameters=parameters if parameters else None,
                                parent_class=None,
                            ))

        # Variable declarations (var)
        elif node.type == "variable_declaration":
            for declarator in node.children:
                if declarator.type == "variable_declarator":
                    name_node = declarator.child_by_field_name("name")
                    value_node = declarator.child_by_field_name("value")

                    if name_node and value_node:
                        var_name = name_node.text.decode('utf8')

                        # Check if value is a function
                        if value_node.type in ("arrow_function", "function_expression"):
                            parameters = _extract_parameters(value_node)
                            signature = f"({', '.join(parameters)})" if parameters else "()"

                            # Check if async
                            is_async = any(child.type == "async" for child in value_node.children)
                            if is_async:
                                signature = f"async {signature}"

                            symbols.append(CodeSymbol(
                                name=var_name,
                                type="function",
                                file_path=file_path,
                                start_line=node.start_point[0] + 1,
                                end_line=node.end_point[0] + 1,
                                signature=signature,
                                return_type=None,
                                parameters=parameters if parameters else None,
                                parent_class=None,
                            ))

        # Recursively visit children (unless we handled them specially above)
        if node.type not in ("class_declaration",):
            for child in node.children:
                visit_node(child, parent_class)

    visit_node(tree.root_node)
    return symbols


def _extract_parameters(node) -> List[str]:
    """
    Extract parameter names from a function/method node.

    Args:
        node: Tree-sitter node (function_declaration, arrow_function, etc.)

    Returns:
        List of parameter names
    """
    parameters: List[str] = []

    # Find formal_parameters node
    for child in node.children:
        if child.type == "formal_parameters":
            for param_child in child.children:
                if param_child.type == "identifier":
                    parameters.append(param_child.text.decode('utf8'))
                elif param_child.type == "required_parameter":
                    # Might have pattern or identifier
                    for sub in param_child.children:
                        if sub.type == "identifier":
                            parameters.append(sub.text.decode('utf8'))
                            break
            break

    return parameters


def _parse_javascript_file_regex(file_path: Path, content: str, normalized_path: str) -> List[CodeSymbol]:
    """
    Fallback regex-based parser for files with syntax errors or when tree-sitter unavailable.

    Args:
        file_path: Path object
        content: File content
        normalized_path: Normalized file path string

    Returns:
        List of CodeSymbol objects (minimal extraction)
    """
    from cerberus.parser.config import LANGUAGE_QUERIES

    symbols: List[CodeSymbol] = []
    queries = LANGUAGE_QUERIES.get("javascript", {})

    for symbol_type, regex_pattern in queries.items():
        for match in regex_pattern.finditer(content):
            symbol_name = match.group(1)
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
            logger.debug(f"Found JS symbol (regex): {symbol_name} ({symbol_type}) on line {line_number}")

    return symbols
