import re
from pathlib import Path
from typing import List

from cerberus.logging_config import logger
from cerberus.parser.config import LANGUAGE_QUERIES
from cerberus.schemas import CodeSymbol


def parse_go_file(file_path: Path, content: str) -> List[CodeSymbol]:
    """
    Parses a Go file to extract functions, methods, structs, and interfaces.
    """
    logger.debug(f"Parsing Go file: {file_path}")
    symbols: List[CodeSymbol] = []
    
    # 1. Methods: func (receiver) Name(...)
    # Match: func (u *User) Login
    # Group 1: Receiver content "u *User", Group 2: Method Name
    method_pattern = re.compile(r"^func\s+\(([^)]+)\)\s+([A-Za-z0-9_]+)", re.MULTILINE)
    
    # 2. Functions: func Name(...)
    # Match: func NewUser
    # Group 1: Function Name
    func_pattern = re.compile(r"^func\s+([A-Za-z0-9_]+)\s*\(", re.MULTILINE)
    
    # 3. Types: type Name struct/interface
    type_pattern = re.compile(r"^type\s+([A-Za-z0-9_]+)\s+(struct|interface)", re.MULTILINE)

    # Scan for Methods
    for match in method_pattern.finditer(content):
        receiver_str = match.group(1).strip() # e.g. "u *User" or "*User"
        name = match.group(2)
        
        # Extract parent class from receiver string
        # Handle: "u *User", "*User", "User", "u User"
        parent_class = receiver_str.split(" ")[-1].replace("*", "")
        
        _add_symbol(symbols, name, "method", match, content, file_path, parent_class=parent_class)

    # Scan for Functions
    for match in func_pattern.finditer(content):
        name = match.group(1)
        # Avoid duplicates (if method regex accidentally matched a function, unlikely with current patterns)
        _add_symbol(symbols, name, "function", match, content, file_path)

    # Scan for Types
    for match in type_pattern.finditer(content):
        name = match.group(1)
        kind = match.group(2)
        _add_symbol(symbols, name, kind, match, content, file_path)

    return symbols

def _get_line_number(content: str, start_index: int) -> int:
    return content.count("\n", 0, start_index) + 1

def _find_closing_brace(content: str, start_index: int, start_line: int) -> int:
    """
    Find the closing brace for a function/method/type definition.

    Args:
        content: File content
        start_index: Starting position in content
        start_line: Line number where the definition starts

    Returns:
        Line number of the closing brace, or start_line if not found
    """
    # Find the opening brace for this function/struct/interface
    brace_start = content.find("{", start_index)
    if brace_start == -1:
        # No opening brace found (e.g., interface method signature)
        return start_line

    # Count braces to find the matching closing brace
    brace_count = 1
    pos = brace_start + 1
    in_string = False
    in_char = False
    in_comment = False
    in_block_comment = False

    while pos < len(content) and brace_count > 0:
        ch = content[pos]
        prev_ch = content[pos - 1] if pos > 0 else ''

        # Handle string literals
        if ch == '"' and prev_ch != '\\' and not in_char and not in_comment and not in_block_comment:
            in_string = not in_string
        # Handle character literals
        elif ch == "'" and prev_ch != '\\' and not in_string and not in_comment and not in_block_comment:
            in_char = not in_char
        # Handle line comments
        elif ch == '/' and pos + 1 < len(content) and content[pos + 1] == '/' and not in_string and not in_char and not in_block_comment:
            in_comment = True
        elif ch == '\n' and in_comment:
            in_comment = False
        # Handle block comments
        elif ch == '/' and pos + 1 < len(content) and content[pos + 1] == '*' and not in_string and not in_char:
            in_block_comment = True
            pos += 1  # Skip the '*'
        elif ch == '*' and pos + 1 < len(content) and content[pos + 1] == '/' and in_block_comment:
            in_block_comment = False
            pos += 1  # Skip the '/'
        # Count braces only outside strings/comments
        elif not in_string and not in_char and not in_comment and not in_block_comment:
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

def _add_symbol(symbols: List, name: str, symbol_type: str, match, content: str, file_path: Path, parent_class: str | None = None):
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
