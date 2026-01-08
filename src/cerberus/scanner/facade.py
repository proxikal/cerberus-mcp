import os
import time
from pathlib import Path
from typing import List, Optional

import pathspec

from cerberus.logging_config import logger
from cerberus.tracing import trace
from cerberus.parser import parse_file
from cerberus.parser.dependencies import extract_imports, extract_calls, extract_import_links
from cerberus.parser.type_resolver import extract_types_from_file
from cerberus.schemas import CallReference, CodeSymbol, FileObject, ImportReference, ScanResult, TypeInfo, ImportLink
from .config import DEFAULT_IGNORE_PATTERNS

@trace
def scan(
    directory: Path,
    respect_gitignore: bool = True,
    extensions: Optional[List[str]] = None,
    previous_index: Optional[ScanResult] = None,
    incremental: bool = False,
    max_bytes: Optional[int] = None,
) -> ScanResult:
    """
    Scans a directory, finding all relevant files and gathering metadata.

    Args:
        directory: The root directory to start the scan from.
        respect_gitignore: If True, files listed in .gitignore will be excluded.
        extensions: A list of file extensions to include (e.g., ['.py', '.md']).
                    If None, all extensions are included.

    Returns:
        A ScanResult object containing the list of found files and metadata.
    """
    start_time = time.time()
    logger.info(f"Starting scan on directory: '{directory}'")
    
    previous_files = {}
    previous_symbols_by_file = {}
    if previous_index:
        previous_files = {f.path: f.last_modified for f in previous_index.files}
        for symbol in previous_index.symbols:
            previous_symbols_by_file.setdefault(symbol.file_path, []).append(symbol)
        if incremental:
            logger.info(f"Incremental mode enabled with {len(previous_files)} cached files.")

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
                logger.warning(f"Could not read or parse .gitignore file at '{gitignore_path}'. Error: {e}")

    spec = pathspec.PathSpec.from_lines("gitignore", all_patterns)
    if respect_gitignore:
        logger.debug(f"Initialized scanner with a total of {len(all_patterns)} ignore patterns.")
    else:
        logger.debug("Initialized scanner with no ignore patterns.")

    found_files: List[FileObject] = []
    parsed_symbols: List[CodeSymbol] = []
    imports: List[ImportReference] = []
    calls: List[CallReference] = []
    type_infos: List[TypeInfo] = []
    import_links: List[ImportLink] = []
    
    # Use a set for faster extension checking
    allowed_extensions = set(extensions) if extensions else None

    for root, dirs, files in os.walk(directory):
        root_path = Path(root)

        # Prune ignored directories. This is much more efficient than checking every file.
        # We modify 'dirs' in-place to prevent os.walk from descending into them.
        original_dirs = list(dirs)
        dirs[:] = []
        for d in original_dirs:
            dir_path_to_check = root_path.relative_to(directory) / d
            if spec.match_file(str(dir_path_to_check)):
                logger.debug(f"Ignoring directory '{dir_path_to_check}' due to ignore rules.")
            else:
                dirs.append(d)
        
        for file_name in files:
            file_path = root_path / file_name
            relative_path = file_path.relative_to(directory)

            # Check if the file should be ignored
            if spec.match_file(str(relative_path)):
                logger.debug(f"Ignoring '{relative_path}' due to ignore rules")
                continue

            # Check if the file extension is allowed
            if allowed_extensions and file_path.suffix not in allowed_extensions:
                logger.debug(f"Ignoring '{relative_path}' due to extension filter")
                continue

            try:
                # Gather file metadata
                stats = file_path.stat()
                if max_bytes is not None and stats.st_size > max_bytes:
                    logger.debug(f"Skipping '{relative_path}' due to size filter ({stats.st_size} > {max_bytes})")
                    continue

                file_obj = FileObject(
                    path=str(relative_path),
                    abs_path=str(file_path.resolve()),
                    size=stats.st_size,
                    last_modified=stats.st_mtime,
                )
                found_files.append(file_obj)

                # Parse the file to extract symbols, if supported
                # If incremental and unchanged, reuse cached symbols
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if incremental and previous_index:
                    prev_mtime = previous_files.get(str(relative_path))
                    if prev_mtime and abs(prev_mtime - stats.st_mtime) < 1e-6:
                        cached = previous_symbols_by_file.get(str(file_path), [])
                        parsed_symbols.extend(cached)
                        logger.debug(f"Reused {len(cached)} cached symbols for '{relative_path}'")
                    else:
                        file_symbols = parse_file(file_path)
                        parsed_symbols.extend(file_symbols)
                else:
                    file_symbols = parse_file(file_path)
                    parsed_symbols.extend(file_symbols)

                imports.extend(extract_imports(file_path, content))
                calls.extend(extract_calls(file_path, content))
                # Phase 1: Extract type information and import links
                type_infos.extend(extract_types_from_file(file_path, content))
                import_links.extend(extract_import_links(file_path, content))
            except (IOError, OSError, FileNotFoundError) as e:
                logger.warning(f"Could not access metadata for '{file_path}'. Skipping. Error: {e}")
                
    end_time = time.time()
    scan_duration = end_time - start_time
    
    scan_result = ScanResult(
        total_files=len(found_files),
        files=found_files,
        scan_duration=scan_duration,
        symbols=parsed_symbols,
        imports=imports,
        calls=calls,
        type_infos=type_infos,
        import_links=import_links,
    )
    
    logger.info(f"Scan complete. Found {scan_result.total_files} files in {scan_duration:.2f} seconds.")
    return scan_result
