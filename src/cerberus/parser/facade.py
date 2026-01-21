from typing import List
from pathlib import Path

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol
from .config import SUPPORTED_LANGUAGES
from .python_parser import parse_python_file
from .javascript_parser import parse_javascript_file
from .typescript_parser import parse_typescript_file
from .go_parser import parse_go_file
from .rust_parser import parse_rust_file
from .markdown_parser import parse_markdown_file
# Import other specialist parsers here as they are created

def parse_file(file_path: Path) -> List[CodeSymbol]:
    """
    Parses a single file to extract symbols (functions, classes, etc.).

    This function acts as a facade, delegating to the appropriate
    language-specific parser based on the file extension.

    Every parsed file also gets a "file" symbol with the filename stem,
    enabling search by filename (e.g., search("README") finds README.md).
    """
    language = SUPPORTED_LANGUAGES.get(file_path.suffix)

    if not language:
        logger.debug(f"Unsupported file type: {file_path.suffix}. Skipping.")
        return []

    logger.debug(f"Parsing file: {file_path} with language {language}")

    try:
        content = file_path.read_text(encoding="utf-8")
    except (IOError, UnicodeDecodeError) as e:
        logger.error(f"Could not read file {file_path}. Error: {e}")
        return []

    # Parse with language-specific parser
    symbols: List[CodeSymbol] = []
    if language == "python":
        symbols = parse_python_file(file_path, content)
    elif language == "javascript":
        symbols = parse_javascript_file(file_path, content)
    elif language == "typescript":
        symbols = parse_typescript_file(file_path, content)
    elif language == "go":
        symbols = parse_go_file(file_path, content)
    elif language == "rust":
        symbols = parse_rust_file(file_path, content)
    elif language == "markdown":
        symbols = parse_markdown_file(file_path, content)
    else:
        logger.warning(f"No specialist parser implemented for language: '{language}'")

    # Add file symbol for filename-based search
    line_count = len(content.splitlines()) if content else 1
    file_symbol = CodeSymbol(
        name=file_path.stem,  # filename without extension
        type="file",
        file_path=str(file_path),
        start_line=1,
        end_line=line_count,
        signature=file_path.name,  # full filename with extension
    )
    symbols.insert(0, file_symbol)

    return symbols
