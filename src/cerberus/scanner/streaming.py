"""
Streaming scanner for constant memory usage.

Yields file results one at a time instead of accumulating in memory.
"""

import os
import time
from pathlib import Path
from typing import Generator, Dict, List, Optional
from dataclasses import dataclass

import pathspec

from cerberus.logging_config import logger
from cerberus.parser import parse_file
from cerberus.parser.dependencies import extract_imports, extract_calls, extract_import_links
from cerberus.parser.type_resolver import extract_types_from_file
from cerberus.schemas import CallReference, CodeSymbol, FileObject, ImportReference, TypeInfo, ImportLink
from .config import DEFAULT_IGNORE_PATTERNS


@dataclass
class FileResult:
    """Result from parsing a single file."""
    file_obj: FileObject
    symbols: List[CodeSymbol]
    imports: List[ImportReference]
    calls: List[CallReference]
    type_infos: List[TypeInfo]
    import_links: List[ImportLink]


def scan_files_streaming(
    directory: Path,
    respect_gitignore: bool = True,
    extensions: Optional[List[str]] = None,
    previous_files: Optional[Dict[str, float]] = None,
    incremental: bool = False,
    max_bytes: Optional[int] = None,
) -> Generator[FileResult, None, None]:
    """
    Stream file parsing results one at a time (constant memory).

    Instead of accumulating all files/symbols in memory, this yields
    each file's results immediately after parsing.

    Args:
        directory: Root directory to scan
        respect_gitignore: Honor .gitignore patterns
        extensions: File extensions to include (None = all)
        previous_files: Dict of {file_path: last_modified} for incremental
        incremental: Skip unchanged files
        max_bytes: Skip files larger than this

    Yields:
        FileResult for each parsed file
    """
    logger.info(f"Starting streaming scan on directory: '{directory}'")

    # Load ignore patterns
    all_patterns = []
    if respect_gitignore:
        all_patterns.extend(DEFAULT_IGNORE_PATTERNS)
        gitignore_path = directory / ".gitignore"
        if gitignore_path.is_file():
            try:
                with open(gitignore_path, "r") as f:
                    gitignore_patterns = f.read().splitlines()
                    all_patterns.extend(gitignore_patterns)
                    logger.debug(f"Loaded {len(gitignore_patterns)} patterns from '{gitignore_path}'")
            except Exception as e:
                logger.warning(f"Could not read .gitignore: {e}")

    spec = pathspec.PathSpec.from_lines("gitignore", all_patterns)

    # Use set for faster extension checking
    allowed_extensions = set(extensions) if extensions else None

    file_count = 0

    for root, dirs, files in os.walk(directory):
        root_path = Path(root)

        # Prune ignored directories
        original_dirs = list(dirs)
        dirs[:] = []
        for d in original_dirs:
            dir_path_to_check = root_path.relative_to(directory) / d
            if not spec.match_file(str(dir_path_to_check)):
                dirs.append(d)

        for file_name in files:
            file_path = root_path / file_name
            relative_path = file_path.relative_to(directory)

            # Check if file should be ignored
            if spec.match_file(str(relative_path)):
                continue

            # Check extension filter
            if allowed_extensions and file_path.suffix not in allowed_extensions:
                continue

            # Check file size
            try:
                file_size = file_path.stat().st_size
                if max_bytes and file_size > max_bytes:
                    logger.debug(f"Skipping '{relative_path}' (size {file_size} > {max_bytes} bytes)")
                    continue
            except OSError as e:
                logger.warning(f"Could not stat '{relative_path}': {e}")
                continue

            # Create FileObject
            last_modified = file_path.stat().st_mtime
            file_obj = FileObject(
                path=str(relative_path),
                abs_path=str(file_path.resolve()),
                size=file_size,
                last_modified=last_modified,
            )

            # Check if file changed (for incremental)
            if incremental and previous_files:
                prev_mtime = previous_files.get(str(relative_path))
                if prev_mtime and abs(prev_mtime - last_modified) < 0.01:
                    logger.debug(f"Skipping unchanged file: '{relative_path}'")
                    continue

            # Parse file
            try:
                # Read file content
                content = file_path.read_text(encoding="utf-8", errors="ignore")

                # Parse symbols
                symbols = parse_file(file_path)
                if not symbols:
                    # Not a code file or no symbols found - skip
                    continue

                # Normalize file paths to relative
                for symbol in symbols:
                    symbol.file_path = str(relative_path)

                # Extract additional info (all take file_path and content)
                imports = extract_imports(file_path, content)
                calls = extract_calls(file_path, content)
                type_infos = extract_types_from_file(file_path, content)
                import_links = extract_import_links(file_path, content)

                # Normalize file paths in related data
                for imp in imports:
                    imp.file_path = str(relative_path)
                for call in calls:
                    call.caller_file = str(relative_path)
                for ti in type_infos:
                    ti.file_path = str(relative_path)
                for link in import_links:
                    link.importer_file = str(relative_path)

                # Yield result immediately (no accumulation!)
                yield FileResult(
                    file_obj=file_obj,
                    symbols=symbols,
                    imports=imports,
                    calls=calls,
                    type_infos=type_infos,
                    import_links=import_links,
                )

                file_count += 1

                if file_count % 500 == 0:
                    logger.info(f"Streaming progress: {file_count} files parsed")

            except Exception as e:
                logger.warning(f"Error parsing '{relative_path}': {e}")
                continue

    logger.info(f"Streaming scan complete: {file_count} files processed")
