from typing import List
from pathlib import Path

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol
from .config import SUPPORTED_LANGUAGES
from .python_parser import parse_python_file
from .javascript_parser import parse_javascript_file
from .typescript_parser import parse_typescript_file
from .go_parser import parse_go_file
# Import other specialist parsers here as they are created

def parse_file(file_path: Path) -> List[CodeSymbol]:
    """
    Parses a single file to extract symbols (functions, classes, etc.).

    This function acts as a facade, delegating to the appropriate
    language-specific parser based on the file extension.
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

    if language == "python":
        return parse_python_file(file_path, content)
    elif language == "javascript":
        return parse_javascript_file(file_path, content)
    elif language == "typescript":
        return parse_typescript_file(file_path, content)
    elif language == "go":
        return parse_go_file(file_path, content)
    
    logger.warning(f"No specialist parser implemented for language: '{language}'")
    return []
