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
    - .json extension -> Legacy format (full memory load)
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
            logger.info(f"Loaded previous legacy index for incremental scan")
        except Exception as exc:
            logger.warning(f"Could not load previous legacy index: {exc}")

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
    Build index in SQLite format with true streaming.

    Achieves constant memory usage by parsing and writing files one batch at a time.
    Never accumulates all symbols in memory.
    """
    logger.info("Using SQLite format (TRUE streaming, constant memory)")

    # Initialize stores
    sqlite_store = SQLiteIndexStore(output_path)
    faiss_store = None
    if store_embeddings:
        faiss_store = FAISSVectorStore(sqlite_store.index_dir, dimension=384)
        sqlite_store._faiss_store = faiss_store

    # Load previous index for incremental
    previous_files = {}
    if incremental and output_path.exists():
        try:
            result = load_index(output_path)
            if isinstance(result, ScanResultAdapter):
                # Load only file modification times for incremental comparison
                for file_obj in result.files:
                    previous_files[file_obj.path] = file_obj.last_modified
                logger.info(f"Loaded {len(previous_files)} cached files for incremental scan")
        except Exception as exc:
            logger.warning(f"Could not load previous SQLite index: {exc}")

    # Stream files from scanner and write immediately in batches
    from ..scanner.streaming import scan_files_streaming

    total_files = 0
    total_symbols = 0
    file_batch = []
    symbol_batch = []
    import_batch = []
    call_batch = []
    type_info_batch = []
    import_link_batch = []
    method_call_batch = []  # Phase 5.1

    BATCH_SIZE = 100  # Process 100 files at a time for optimal performance

    logger.info(f"Streaming files from {directory}...")

    for file_result in scan_files_streaming(
        directory=directory,
        respect_gitignore=respect_gitignore,
        extensions=extensions,
        previous_files=previous_files,
        incremental=incremental,
        max_bytes=max_bytes,
    ):
        # Accumulate into batches
        file_batch.append(file_result.file_obj)
        symbol_batch.extend(file_result.symbols)
        import_batch.extend(file_result.imports)
        call_batch.extend(file_result.calls)
        type_info_batch.extend(file_result.type_infos)
        import_link_batch.extend(file_result.import_links)
        method_call_batch.extend(file_result.method_calls)  # Phase 5.1

        total_files += 1

        # Write batch when it reaches BATCH_SIZE
        if len(file_batch) >= BATCH_SIZE:
            _write_batch_to_sqlite(
                sqlite_store=sqlite_store,
                faiss_store=faiss_store,
                file_batch=file_batch,
                symbol_batch=symbol_batch,
                import_batch=import_batch,
                call_batch=call_batch,
                type_info_batch=type_info_batch,
                import_link_batch=import_link_batch,
                method_call_batch=method_call_batch,  # Phase 5.1
                store_embeddings=store_embeddings,
                padding=padding,
                model_name=model_name,
            )

            total_symbols += len(symbol_batch)

            # Clear batches to release memory
            file_batch.clear()
            symbol_batch.clear()
            import_batch.clear()
            call_batch.clear()
            type_info_batch.clear()
            import_link_batch.clear()
            method_call_batch.clear()  # Phase 5.1

            if total_files % 500 == 0:
                logger.info(f"Progress: {total_files} files, {total_symbols} symbols written")

    # Write final partial batch
    if file_batch:
        _write_batch_to_sqlite(
            sqlite_store=sqlite_store,
            faiss_store=faiss_store,
            file_batch=file_batch,
            symbol_batch=symbol_batch,
            import_batch=import_batch,
            call_batch=call_batch,
            type_info_batch=type_info_batch,
            import_link_batch=import_link_batch,
            method_call_batch=method_call_batch,  # Phase 5.1
            store_embeddings=store_embeddings,
            padding=padding,
            model_name=model_name,
        )

        total_symbols += len(symbol_batch)

    # Store metadata
    project_root = str(directory.resolve())
    sqlite_store.set_metadata('project_root', project_root)

    scan_duration = time.time() - start_time
    sqlite_store.set_metadata('scan_duration', str(scan_duration))
    sqlite_store.set_metadata('total_files', str(total_files))

    # Store git commit
    git_commit = _get_git_commit(directory)
    if git_commit:
        sqlite_store.set_metadata('git_commit', git_commit)

    # Save FAISS index
    if faiss_store is not None:
        faiss_store.save()
        logger.info(f"Saved FAISS index with {len(faiss_store)} vectors")

    logger.info(f"SQLite streaming index complete: {total_files} files, {total_symbols} symbols in {scan_duration:.2f}s")

    # Phase 5.2: Post-processing - Import resolution
    try:
        from ..resolution import resolve_imports
        resolved_count = resolve_imports(sqlite_store, project_root)
        logger.info(f"Phase 5.2: Resolved {resolved_count} import links")
    except Exception as e:
        logger.warning(f"Phase 5.2: Import resolution failed: {e}")
        # Continue anyway - resolution is optional enhancement

    # Phase 5.3: Post-processing - Type tracking and method resolution
    try:
        from ..resolution import resolve_types
        reference_count = resolve_types(sqlite_store)
        logger.info(f"Phase 5.3: Created {reference_count} symbol references")
    except Exception as e:
        logger.warning(f"Phase 5.3: Type tracking failed: {e}")
        # Continue anyway - resolution is optional enhancement

    # Phase 6.1: Post-processing - Inheritance resolution
    try:
        from ..resolution import resolve_inheritance
        inheritance_count = resolve_inheritance(sqlite_store, project_root)
        logger.info(f"Phase 6.1: Created {inheritance_count} inheritance references")
    except Exception as e:
        logger.warning(f"Phase 6.1: Inheritance resolution failed: {e}")
        # Continue anyway - resolution is optional enhancement

    # Return adapter
    return ScanResultAdapter(sqlite_store)


def _write_batch_to_sqlite(
    sqlite_store: SQLiteIndexStore,
    faiss_store: Optional[FAISSVectorStore],
    file_batch: List,
    symbol_batch: List,
    import_batch: List,
    call_batch: List,
    type_info_batch: List,
    import_link_batch: List,
    method_call_batch: List,  # Phase 5.1
    store_embeddings: bool,
    padding: int,
    model_name: str,
):
    """
    Write a batch of files and related data to SQLite in a single transaction.

    This keeps transactions small and predictable (~100 files at a time).
    """
    with sqlite_store.transaction() as conn:
        # Write files
        for file_obj in file_batch:
            sqlite_store.write_file(file_obj, conn=conn)

        # Write symbols with chunked batching (handles large symbol counts)
        symbol_ids = sqlite_store.write_symbols_batch(symbol_batch, conn=conn)

        # Write related data
        if import_batch:
            sqlite_store.write_imports_batch(import_batch, conn=conn)
        if call_batch:
            sqlite_store.write_calls_batch(call_batch, conn=conn)
        if type_info_batch:
            sqlite_store.write_type_infos_batch(type_info_batch, conn=conn)
        if import_link_batch:
            sqlite_store.write_import_links_batch(import_link_batch, conn=conn)
        if method_call_batch:  # Phase 5.1
            sqlite_store.write_method_calls_batch(method_call_batch, conn=conn)

        # Generate and store embeddings
        if store_embeddings and faiss_store is not None and symbol_batch:
            _generate_embeddings_sqlite(
                symbol_batch,
                symbol_ids,
                faiss_store,
                sqlite_store,
                padding,
                model_name,
                conn
            )


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
