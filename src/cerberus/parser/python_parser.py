import re
from pathlib import Path
from typing import List

from cerberus.logging_config import logger
from cerberus.parser.config import LANGUAGE_QUERIES
from cerberus.schemas import CodeSymbol

def parse_python_file(file_path: Path, content: str) -> List[CodeSymbol]:
    """
    Parses a Python file using regex and extracts symbols.
    """
    logger.debug(f"Parsing content:\n---\n{content}\n---")
    symbols: List[CodeSymbol] = []
    queries = LANGUAGE_QUERIES.get("python", {})

    # Normalize file path to handle symlinks (e.g., /var vs /private/var on macOS)
    normalized_path = str(file_path.resolve())

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
                    end_line=line_number,  # Regex doesn't easily give us the end line
                )
            )
            logger.debug(f"Found symbol: {symbol_name} ({symbol_type}) on line {line_number}")

    return symbols
