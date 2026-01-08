import time
from pathlib import Path
from typing import List, Optional, Union

import numpy as np

from cerberus.logging_config import logger
from cerberus.tracing import trace
from cerberus.scanner import scan
from cerberus.schemas import ScanResult, SymbolEmbedding
from .json_store import JSONIndexStore
from .index_loader import is_sqlite_index, load_index
from cerberus.storage import SQLiteIndexStore, FAISSVectorStore, ScanResultAdapter
from cerberus.semantic.embeddings import embed_texts
from cerberus.retrieval.utils import read_range


@trace
def build_index(
    directory: Path,
    output_path: Path,
    respect_gitignore: bool = True,
    extensions: Optional[List[str]] = None,
    incremental: bool = False,
    store_embeddings: bool = False,
    padding: int = 3,
    model_name: str = "all-MiniLM-L6-v2",
    max_bytes: Optional[int] = None,
) -> Union[ScanResult, ScanResultAdapter]:
    """
    Run a scan and persist the results to an index.

    Automatically detects output format:
    - .json extension -> Legacy JSON format (full memory load)
    - Directory or .db -> SQLite + FAISS format (streaming, constant memory)

    Args:
        directory: Project root to scan
        output_path: Path to output index (.json for JSON, directory/file for SQLite)
        respect_gitignore: Honor .gitignore patterns
        extensions: File extensions to scan (None = all)
        incremental: Use previous index for unchanged files
        store_embeddings: Generate and store vector embeddings
        padding: Context lines around symbols for embeddings
        model_name: Embedding model name
        max_bytes: Skip files larger than this

    Returns:
        ScanResult (JSON) or ScanResultAdapter (SQLite)
    """
    start_time = time.time()
    logger.info(f"Building index for directory '{directory}' -> '{output_path}'")

    # Detect output format
    use_sqlite = not (str(output_path).endswith('.json'))

    if use_sqlite:
        # SQLite streaming path - constant memory
        return _build_sqlite_index(
            directory=directory,
            output_path=output_path,
            respect_gitignore=respect_gitignore,
            extensions=extensions,
            incremental=incremental,
            store_embeddings=store_embeddings,
            padding=padding,
            model_name=model_name,
            max_bytes=max_bytes,
            start_time=start_time,
        )
    else:
        # JSON legacy path - full memory load
        return _build_json_index(
            directory=directory,
            output_path=output_path,
            respect_gitignore=respect_gitignore,
            extensions=extensions,
            incremental=incremental,
            store_embeddings=store_embeddings,
            padding=padding,
            model_name=model_name,
            max_bytes=max_bytes,
        )


def _build_json_index(
    directory: Path,
    output_path: Path,
    respect_gitignore: bool,
    extensions: Optional[List[str]],
    incremental: bool,
    store_embeddings: bool,
    padding: int,
    model_name: str,
    max_bytes: Optional[int],
) -> ScanResult:
    """
    Build index in legacy JSON format (backward compatibility).

    Full memory accumulation before write.
    """
    logger.info("Using JSON format (legacy, full memory load)")

    previous_index = None
    if incremental and output_path.exists():
        try:
            previous_index = JSONIndexStore(output_path).read()
            logger.info(f"Loaded previous JSON index for incremental scan")
        except Exception as exc:
            logger.warning(f"Could not load previous JSON index: {exc}")

    scan_result = scan(
        directory,
        respect_gitignore=respect_gitignore,
        extensions=extensions,
        previous_index=previous_index,
        incremental=incremental,
        max_bytes=max_bytes,
    )

    # Store metadata
    scan_result.project_root = str(directory.resolve())
    _store_git_commit(directory, scan_result)

    # Generate embeddings (full batch)
    if store_embeddings:
        _generate_embeddings_json(scan_result, padding, model_name)

    # Write to JSON
    store = JSONIndexStore(output_path)
    store.write(scan_result)

    return scan_result


def _build_sqlite_index(
    directory: Path,
    output_path: Path,
    respect_gitignore: bool,
    extensions: Optional[List[str]],
    incremental: bool,
    store_embeddings: bool,
    padding: int,
    model_name: str,
    max_bytes: Optional[int],
    start_time: float,
) -> ScanResultAdapter:
    """
    Build index in SQLite format with streaming writes.

    Achieves constant memory usage by writing per-file immediately.
    """
    logger.info("Using SQLite format (streaming, constant memory)")

    # Initialize stores
    sqlite_store = SQLiteIndexStore(output_path)
    faiss_store = None
    if store_embeddings:
        faiss_store = FAISSVectorStore(sqlite_store.index_dir, dimension=384)
        sqlite_store._faiss_store = faiss_store

    # Load previous index for incremental
    previous_index = None
    if incremental and output_path.exists():
        try:
            result = load_index(output_path)
            if isinstance(result, ScanResultAdapter):
                # Extract previous index data for scanner
                previous_index = ScanResult(
                    total_files=result.total_files,
                    files=result.files,
                    scan_duration=result.scan_duration,
                    symbols=result.symbols,
                    project_root=result.project_root,
                    metadata=result.metadata,
                )
                logger.info(f"Loaded previous SQLite index for incremental scan")
        except Exception as exc:
            logger.warning(f"Could not load previous SQLite index: {exc}")

    # Run scan (still accumulates in memory for now - streaming scanner in next step)
    scan_result = scan(
        directory,
        respect_gitignore=respect_gitignore,
        extensions=extensions,
        previous_index=previous_index,
        incremental=incremental,
        max_bytes=max_bytes,
    )

    # Write to SQLite with transaction
    logger.info(f"Writing {len(scan_result.symbols)} symbols to SQLite...")

    # Build path mapping for normalization (absolute -> relative)
    path_map = {file_obj.abs_path: file_obj.path for file_obj in scan_result.files}

    def normalize_path(path: str) -> str:
        """Convert absolute or relative path to relative path matching files.path."""
        # If it's in the map, convert it
        if path in path_map:
            return path_map[path]
        # Otherwise, it's already relative or needs matching
        # Try to find by suffix match
        for abs_path, rel_path in path_map.items():
            if abs_path == path or abs_path.endswith(f"/{path}") or abs_path.endswith(f"\\{path}"):
                return rel_path
        # Last resort: return as-is
        return path

    # Normalize all file_path references to relative paths
    for symbol in scan_result.symbols:
        symbol.file_path = normalize_path(symbol.file_path)

    for import_ref in scan_result.imports:
        import_ref.file_path = normalize_path(import_ref.file_path)

    for call_ref in scan_result.calls:
        call_ref.caller_file = normalize_path(call_ref.caller_file)

    for type_info in scan_result.type_infos:
        type_info.file_path = normalize_path(type_info.file_path)

    for import_link in scan_result.import_links:
        import_link.importer_file = normalize_path(import_link.importer_file)
        if import_link.definition_file:
            import_link.definition_file = normalize_path(import_link.definition_file)

    with sqlite_store.transaction() as conn:
        # Write files
        for file_obj in scan_result.files:
            sqlite_store.write_file(file_obj, conn=conn)

        # Write symbols and get IDs
        symbol_ids = sqlite_store.write_symbols_batch(scan_result.symbols, conn=conn)

        # Write imports, calls, type_infos, import_links
        sqlite_store.write_imports_batch(scan_result.imports, conn=conn)
        sqlite_store.write_calls_batch(scan_result.calls, conn=conn)
        sqlite_store.write_type_infos_batch(scan_result.type_infos, conn=conn)
        sqlite_store.write_import_links_batch(scan_result.import_links, conn=conn)

        # Generate and store embeddings
        if store_embeddings and faiss_store is not None:
            logger.info(f"Generating embeddings for {len(scan_result.symbols)} symbols...")
            _generate_embeddings_sqlite(
                scan_result.symbols,
                symbol_ids,
                faiss_store,
                sqlite_store,
                padding,
                model_name,
                conn
            )

        # Store metadata
        project_root = str(directory.resolve())
        sqlite_store.set_metadata('project_root', project_root, conn=conn)

        scan_duration = time.time() - start_time
        sqlite_store.set_metadata('scan_duration', str(scan_duration), conn=conn)
        sqlite_store.set_metadata('total_files', str(len(scan_result.files)), conn=conn)

        # Store git commit
        git_commit = _get_git_commit(directory)
        if git_commit:
            sqlite_store.set_metadata('git_commit', git_commit, conn=conn)

    # Save FAISS index
    if faiss_store is not None:
        faiss_store.save()
        logger.info(f"Saved FAISS index with {len(faiss_store)} vectors")

    logger.info(f"SQLite index build complete in {time.time() - start_time:.2f}s")

    # Return adapter
    return ScanResultAdapter(sqlite_store)


def _generate_embeddings_json(scan_result: ScanResult, padding: int, model_name: str):
    """Generate embeddings for JSON format (batch operation)."""
    try:
        snippets = [
            read_range(Path(sym.file_path), sym.start_line, sym.end_line, padding=padding).content
            for sym in scan_result.symbols
        ]
        vectors = embed_texts(snippets, model_name=model_name)
        scan_result.embeddings = [
            SymbolEmbedding(
                name=sym.name,
                file_path=sym.file_path,
                vector=vectors[i].tolist(),
            )
            for i, sym in enumerate(scan_result.symbols)
        ]
        logger.info(f"Generated {len(scan_result.embeddings)} embeddings")
    except Exception as exc:
        logger.warning(f"Failed to generate embeddings: {exc}")


def _generate_embeddings_sqlite(
    symbols: List,
    symbol_ids: List[int],
    faiss_store: FAISSVectorStore,
    sqlite_store: SQLiteIndexStore,
    padding: int,
    model_name: str,
    conn,
):
    """Generate embeddings for SQLite format (batch with streaming write)."""
    try:
        # Generate snippets
        snippets = [
            read_range(Path(sym.file_path), sym.start_line, sym.end_line, padding=padding).content
            for sym in symbols
        ]

        # Batch embed
        vectors = embed_texts(snippets, model_name=model_name)

        # Add to FAISS and link to SQLite
        faiss_ids = faiss_store.add_vectors_batch(
            symbol_ids=symbol_ids,
            vectors=vectors.astype(np.float32)
        )

        # Write embedding metadata
        for symbol_id, faiss_id, symbol in zip(symbol_ids, faiss_ids, symbols):
            sqlite_store.write_embedding_metadata(
                symbol_id=symbol_id,
                faiss_id=faiss_id,
                name=symbol.name,
                file_path=symbol.file_path,
                model=model_name,
                conn=conn
            )

        logger.info(f"Generated and stored {len(vectors)} embeddings")

    except Exception as exc:
        logger.warning(f"Failed to generate embeddings: {exc}")


def _store_git_commit(directory: Path, scan_result: ScanResult):
    """Store git commit in ScanResult metadata."""
    git_commit = _get_git_commit(directory)
    if git_commit:
        scan_result.metadata["git_commit"] = git_commit
        logger.info(f"Stored git commit: {git_commit[:8]}")


def _get_git_commit(directory: Path) -> Optional[str]:
    """Get current git commit hash."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(directory),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        logger.debug(f"Could not get git commit: {e}")
    return None
