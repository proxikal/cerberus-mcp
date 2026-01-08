import time
from pathlib import Path
from typing import Dict, List, Optional

from cerberus.index import build_index, semantic_search
from cerberus.logging_config import logger


def run_benchmark(
    directory: Path,
    index_path: Path,
    query: str,
    respect_gitignore: bool = True,
    extensions: Optional[List[str]] = None,
    limit: int = 5,
    padding: int = 2,
) -> Dict[str, float]:
    """
    Lightweight benchmark for indexing and semantic search to keep an eye on perf.
    """
    # Index timing
    t0 = time.perf_counter()
    scan_result = build_index(
        directory,
        index_path,
        respect_gitignore=respect_gitignore,
        extensions=extensions,
        incremental=False,
    )
    t1 = time.perf_counter()

    # Search timing
    results = semantic_search(query, index_path, limit=limit, padding=padding)
    t2 = time.perf_counter()

    metrics = {
        "index_duration": t1 - t0,
        "search_duration": t2 - t1,
        "total_duration": t2 - t0,
        "files_indexed": scan_result.total_files,
        "symbols_indexed": len(scan_result.symbols),
        "results_returned": len(results),
    }

    logger.info(
        f"Benchmark: indexed {metrics['files_indexed']} files / {metrics['symbols_indexed']} symbols "
        f"in {metrics['index_duration']:.4f}s, search in {metrics['search_duration']:.4f}s"
    )
    return metrics
