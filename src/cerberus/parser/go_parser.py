from pathlib import Path
from typing import List

from cerberus.logging_config import logger
from cerberus.parser.config import LANGUAGE_QUERIES
from cerberus.schemas import CodeSymbol


def parse_go_file(file_path: Path, content: str) -> List[CodeSymbol]:
    """
    Parses a Go file to extract functions and structs.
    """
    logger.debug(f"Parsing Go file: {file_path}")
    symbols: List[CodeSymbol] = []
    queries = LANGUAGE_QUERIES.get("go", {})

    for symbol_type, regex_pattern in queries.items():
        for match in regex_pattern.finditer(content):
            symbol_name = match.group(1)
            name_start = match.start(1)
            line_number = content.count("\n", 0, name_start) + 1

            symbols.append(
                CodeSymbol(
                    name=symbol_name,
                    type=symbol_type,
                    file_path=str(file_path),
                    start_line=line_number,
                    end_line=line_number,
                )
            )
            logger.debug(f"Found Go symbol: {symbol_name} ({symbol_type}) on line {line_number}")

    return symbols
