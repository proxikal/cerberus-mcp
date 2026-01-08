from pathlib import Path
from typing import List, Optional

from cerberus.logging_config import logger
from cerberus.tracing import trace
from cerberus.scanner import scan
from cerberus.schemas import ScanResult, SymbolEmbedding
from .json_store import JSONIndexStore
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
) -> ScanResult:
    """
    Run a scan and persist the results to a JSON index.
    """
    logger.info(f"Building index for directory '{directory}' -> '{output_path}'")
    previous_index = None
    if incremental and output_path.exists():
        try:
            previous_index = JSONIndexStore(output_path).read()
            logger.info(f"Loaded previous index from '{output_path}' for incremental scan.")
        except Exception as exc:
            logger.warning(f"Could not load previous index at '{output_path}' for incremental scan: {exc}")

    scan_result = scan(
        directory,
        respect_gitignore=respect_gitignore,
        extensions=extensions,
        previous_index=previous_index,
        incremental=incremental,
        max_bytes=max_bytes,
    )

    # Phase 3: Store project root and git commit metadata
    scan_result.project_root = str(directory.resolve())

    # Try to get git commit if in a git repository
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
            git_commit = result.stdout.strip()
            scan_result.metadata["git_commit"] = git_commit
            logger.info(f"Stored git commit in index: {git_commit[:8]}")
    except Exception as e:
        logger.debug(f"Could not get git commit (not a git repo?): {e}")

    if store_embeddings:
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
            logger.info(f"Stored {len(scan_result.embeddings)} embeddings in index.")
        except Exception as exc:
            logger.warning(f"Failed to store embeddings; proceeding without. Error: {exc}")

    store = JSONIndexStore(output_path)
    store.write(scan_result)

    return scan_result
