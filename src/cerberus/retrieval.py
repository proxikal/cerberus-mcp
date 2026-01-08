from pathlib import Path
from typing import List, Iterable

from cerberus.logging_config import logger
from cerberus.schemas import CodeSnippet, CodeSymbol, ScanResult


def find_symbol(name: str, scan_result: ScanResult) -> List[CodeSymbol]:
    """
    Returns all symbols matching a given name from the scan result.
    """
    matches = [symbol for symbol in scan_result.symbols if symbol.name == name]
    if not matches:
        logger.info(f"No symbols found matching '{name}'")
    else:
        logger.info(f"Found {len(matches)} symbol(s) matching '{name}'")
    return matches


def read_range(file_path: Path, start_line: int, end_line: int, padding: int = 5) -> CodeSnippet:
    """
    Reads a code range with optional padding lines for context.
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"File '{file_path}' not found when reading range.")
        return CodeSnippet(file_path=str(file_path), start_line=start_line, end_line=end_line, content="")

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    # Convert to zero-based indices for slicing
    start_idx = max(0, start_line - 1 - padding)
    end_idx = min(len(lines) - 1, end_line - 1 + padding) if lines else -1

    snippet_lines = lines[start_idx : end_idx + 1] if end_idx >= start_idx else []
    content = "\n".join(snippet_lines)

    logger.debug(
        f"Read range {start_line}-{end_line} with padding {padding} from '{file_path}' "
        f"-> actual slice {start_idx + 1}-{end_idx + 1}"
    )

    return CodeSnippet(
        file_path=str(file_path),
        start_line=start_idx + 1,
        end_line=end_idx + 1 if end_idx >= 0 else 0,
        content=content,
    )
