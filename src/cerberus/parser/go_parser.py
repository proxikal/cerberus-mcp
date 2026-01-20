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

def _add_symbol(symbols: List, name: str, symbol_type: str, match, content: str, file_path: Path, parent_class: str = None):
    line_number = _get_line_number(content, match.start())
    
    # Extract signature (the whole line)
    line_end = content.find("\n", match.start())
    signature = content[match.start():line_end].strip() if line_end != -1 else ""

    symbols.append(
        CodeSymbol(
            name=name,
            type=symbol_type,
            file_path=str(file_path.resolve()),
            start_line=line_number,
            end_line=line_number, 
            signature=signature,
            parent_class=parent_class
        )
    )
