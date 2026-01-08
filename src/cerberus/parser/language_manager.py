from pathlib import Path
from typing import Dict, Optional

from tree_sitter import Language, Parser

from cerberus.logging_config import logger

# Path to the compiled language library
# This is created by running the setup_grammars.sh script
BUILD_DIR = Path(__file__).parent.parent.parent.parent / "build"
LANGUAGE_LIB_PATH = BUILD_DIR / "languages.so"

# Global cache for loaded languages to avoid repeated loading
_language_cache: Dict[str, Language] = {}

def get_language(language_name: str) -> Optional[Language]:
    """
    Loads a tree-sitter language from the compiled library.
    
    Caches the loaded language object for efficiency.
    """
    if not LANGUAGE_LIB_PATH.exists():
        logger.error(f"Language library not found at '{LANGUAGE_LIB_PATH}'. "
                     "Please run the setup_grammars.sh script.")
        return None

    if language_name in _language_cache:
        return _language_cache[language_name]

    try:
        lang = Language(LANGUAGE_LIB_PATH, language_name)
        _language_cache[language_name] = lang
        logger.debug(f"Successfully loaded language '{language_name}'")
        return lang
    except Exception as e:
        logger.error(f"Failed to load language '{language_name}' from '{LANGUAGE_LIB_PATH}'. Error: {e}")
        return None
