from pathlib import Path
from typing import List

from cerberus.logging_config import logger
from cerberus.parser.config import LANGUAGE_QUERIES
from cerberus.schemas import CodeSymbol


def parse_typescript_file(file_path: Path, content: str) -> List[CodeSymbol]:
    """
    Parses a TypeScript file using regex to extract classes and functions.
    """
    logger.debug(f"Parsing TypeScript file: {file_path}")
    symbols: List[CodeSymbol] = []
    queries = LANGUAGE_QUERIES.get("typescript", {})

    for symbol_type, regex_pattern in queries.items():
        for match in regex_pattern.finditer(content):
            symbol_name = match.group(1)
            name_start = match.start(1)
            line_number = content.count("\n", 0, name_start) + 1

            symbols.append(
                CodeSymbol(
                    name=symbol_name,
                    type=symbol_type,
                    file_path=str(file_path.resolve()),
                    start_line=line_number,
                    end_line=line_number,
                )
            )
            logger.debug(f"Found TS symbol: {symbol_name} ({symbol_type}) on line {line_number}")

    return symbols
