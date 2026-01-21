import re
from pathlib import Path
from typing import List

from cerberus.logging_config import logger
from cerberus.parser.config import LANGUAGE_QUERIES
from cerberus.schemas import CodeSymbol


def parse_rust_file(file_path: Path, content: str) -> List[CodeSymbol]:
    """
    Parses a Rust file to extract functions, structs, enums, traits, and impls.
    """
    logger.debug(f"Parsing Rust file: {file_path}")
    symbols: List[CodeSymbol] = []

    # Get patterns from config
    patterns = LANGUAGE_QUERIES.get("rust", {})

    # 1. Functions: fn name(), pub fn name(), async fn name(), etc.
    if "function" in patterns:
        for match in patterns["function"].finditer(content):
            name = match.group(1)
            _add_symbol(symbols, name, "function", match, content, file_path)

    # 2. Structs: struct Name, pub struct Name
    if "struct" in patterns:
        for match in patterns["struct"].finditer(content):
            name = match.group(1)
            _add_symbol(symbols, name, "struct", match, content, file_path)

    # 3. Enums: enum Name, pub enum Name
    if "enum" in patterns:
        for match in patterns["enum"].finditer(content):
            name = match.group(1)
            _add_symbol(symbols, name, "enum", match, content, file_path)

    # 4. Traits: trait Name, pub trait Name
    if "trait" in patterns:
        for match in patterns["trait"].finditer(content):
            name = match.group(1)
            _add_symbol(symbols, name, "trait", match, content, file_path)

    # 5. Impls: impl Name, impl<T> Name<T>
    if "impl" in patterns:
        for match in patterns["impl"].finditer(content):
            name = match.group(1)
            _add_symbol(symbols, name, "impl", match, content, file_path)

    return symbols


def _get_line_number(content: str, start_index: int) -> int:
    return content.count("\n", 0, start_index) + 1


def _find_closing_brace(content: str, start_index: int, start_line: int) -> int:
    """
    Find the closing brace for a function/struct/trait/impl definition.

    Args:
        content: File content
        start_index: Starting position in content
        start_line: Line number where the definition starts

    Returns:
        Line number of the closing brace, or start_line if not found
    """
    # Find the opening brace for this definition
    brace_start = content.find("{", start_index)
    if brace_start == -1:
        # No opening brace found (e.g., trait method signature)
        return start_line

    # Count braces to find the matching closing brace
    brace_count = 1
    pos = brace_start + 1
    in_string = False
    in_char = False
    in_line_comment = False
    in_block_comment = False

    while pos < len(content) and brace_count > 0:
        ch = content[pos]
        prev_ch = content[pos - 1] if pos > 0 else ''

        # Handle string literals
        if ch == '"' and prev_ch != '\\' and not in_char and not in_line_comment and not in_block_comment:
            in_string = not in_string
        # Handle character literals
        elif ch == "'" and prev_ch != '\\' and not in_string and not in_line_comment and not in_block_comment:
            in_char = not in_char
        # Handle line comments
        elif ch == '/' and pos + 1 < len(content) and content[pos + 1] == '/' and not in_string and not in_char and not in_block_comment:
            in_line_comment = True
        elif ch == '\n' and in_line_comment:
            in_line_comment = False
        # Handle block comments
        elif ch == '/' and pos + 1 < len(content) and content[pos + 1] == '*' and not in_string and not in_char:
            in_block_comment = True
            pos += 1  # Skip the '*'
        elif ch == '*' and pos + 1 < len(content) and content[pos + 1] == '/' and in_block_comment:
            in_block_comment = False
            pos += 1  # Skip the '/'
        # Count braces only outside strings/comments
        elif not in_string and not in_char and not in_line_comment and not in_block_comment:
            if ch == '{':
                brace_count += 1
            elif ch == '}':
                brace_count -= 1

        pos += 1

    if brace_count == 0:
        # Found matching closing brace
        return _get_line_number(content, pos - 1)
    else:
        # Couldn't find matching brace (malformed code?)
        return start_line


def _add_symbol(symbols: List, name: str, symbol_type: str, match, content: str, file_path: Path, parent_class: str = None):
    line_number = _get_line_number(content, match.start())

    # Extract signature (the whole line)
    line_end = content.find("\n", match.start())
    signature = content[match.start():line_end].strip() if line_end != -1 else ""

    # Calculate end_line by finding the matching closing brace
    # This is crucial for dependency tracking to work correctly
    end_line = _find_closing_brace(content, match.start(), line_number)

    symbols.append(
        CodeSymbol(
            name=name,
            type=symbol_type,
            file_path=str(file_path.resolve()),
            start_line=line_number,
            end_line=end_line,
            signature=signature,
            parent_class=parent_class
        )
    )
