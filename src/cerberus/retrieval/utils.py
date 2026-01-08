"""
Utility functions for retrieval (find_symbol, read_range).

These were originally in retrieval.py and are kept for backward compatibility.
"""

import re
from pathlib import Path
from typing import List
from loguru import logger

from ..schemas import CodeSnippet, CodeSymbol, ScanResult


def find_symbol(name: str, scan_result: ScanResult) -> List[CodeSymbol]:
    """
    Returns all symbols matching a given name from the scan result.

    Args:
        name: Symbol name to search for
        scan_result: Scan result containing symbols

    Returns:
        List of matching CodeSymbol objects
    """
    matches = [symbol for symbol in scan_result.symbols if symbol.name == name]
    if not matches:
        logger.info(f"No symbols found matching '{name}'")
    else:
        logger.info(f"Found {len(matches)} symbol(s) matching '{name}'")
    return matches


def _skeletonize(content: str) -> str:
    """
    Produce a skeleton view of code: keep signatures and docstrings/comments.

    Args:
        content: Source code content

    Returns:
        Skeletonized code (signatures and docs only)
    """
    signature_patterns = [
        r"^\s*def\s+",
        r"^\s*class\s+",
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+",
        r"^\s*(?:export\s+)?class\s+",
        r"^\s*(?:export\s+)?interface\s+",
        r"^\s*(?:export\s+)?enum\s+",
        r"^\s*func\s+",
        r"^\s*type\s+.*\s+struct",
    ]
    signature_re = re.compile("|".join(signature_patterns))
    doc_re = re.compile(r'^\s*(?:\"\"\"|\'\'\'|//|#)')

    skeleton_lines: List[str] = []
    for line in content.splitlines():
        if signature_re.match(line) or doc_re.match(line):
            skeleton_lines.append(line.rstrip())
    return "\n".join(skeleton_lines)


def read_range(
    file_path: Path,
    start_line: int,
    end_line: int,
    padding: int = 5,
    skeleton: bool = False,
) -> CodeSnippet:
    """
    Reads a code range with optional padding lines for context.

    Args:
        file_path: Path to source file
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed)
        padding: Number of context lines before/after
        skeleton: Return skeletonized version (signatures only)

    Returns:
        CodeSnippet object
    """
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"File '{file_path}' not found when reading range.")
        return CodeSnippet(
            file_path=str(file_path),
            start_line=start_line,
            end_line=end_line,
            content="",
        )

    raw_text = path.read_text(encoding="utf-8", errors="ignore")

    if skeleton:
        content = _skeletonize(raw_text)
        start_idx = 0
        end_idx = len(content.splitlines())
    else:
        lines = raw_text.splitlines()
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
