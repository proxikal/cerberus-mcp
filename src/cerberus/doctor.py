import os
from pathlib import Path
from typing import List, Dict, Optional

from cerberus.logging_config import logger


def _check_index_health(index_path: Path) -> Dict:
    """
    Validate index integrity: structure, missing files, and symbol counts.
    """
    if not index_path.exists():
        return {
            "name": "index_health",
            "status": "fail",
            "detail": f"Index file not found at {index_path}",
            "remediation": f"Run: cerberus index <directory> -o {index_path}",
        }

    try:
        from cerberus.index import load_index
        from cerberus.exceptions import IndexCorruptionError

        scan_result = load_index(index_path)

        # Check for basic structure
        if scan_result.total_files != len(scan_result.files):
            return {
                "name": "index_health",
                "status": "fail",
                "detail": f"Inconsistent file count: total_files={scan_result.total_files} but files list has {len(scan_result.files)} entries",
                "remediation": f"Rebuild index: cerberus index <directory> -o {index_path}",
            }

        # Check if referenced files exist
        missing_files = []
        for file_obj in scan_result.files[:10]:  # Check first 10 for performance
            if not Path(file_obj.abs_path).exists():
                missing_files.append(file_obj.path)

        if missing_files:
            return {
                "name": "index_health",
                "status": "warn",
                "detail": f"{len(missing_files)} file(s) in index no longer exist (e.g., {missing_files[0]})",
                "remediation": f"Rebuild index: cerberus index <directory> -o {index_path} --incremental",
            }

        # Check symbol consistency
        symbol_files = {sym.file_path for sym in scan_result.symbols}
        index_files = {f.path for f in scan_result.files}
        orphan_symbols = symbol_files - index_files
        if orphan_symbols:
            return {
                "name": "index_health",
                "status": "warn",
                "detail": f"{len(orphan_symbols)} symbols reference files not in index",
                "remediation": f"Rebuild index: cerberus index <directory> -o {index_path}",
            }

        return {
            "name": "index_health",
            "status": "ok",
            "detail": f"Index valid: {scan_result.total_files} files, {len(scan_result.symbols)} symbols",
            "remediation": "",
        }

    except Exception as exc:
        return {
            "name": "index_health",
            "status": "fail",
            "detail": f"Failed to load or validate index: {exc}",
            "remediation": f"Rebuild index: cerberus index <directory> -o {index_path}",
        }


def _check_grammars() -> Dict:
    languages_so = Path("build/languages.so")
    if languages_so.exists():
        return {"name": "grammars", "status": "ok", "detail": "build/languages.so present", "remediation": ""}
    return {
        "name": "grammars",
        "status": "warn",
        "detail": "build/languages.so not found (tree-sitter grammars optional for regex parser).",
        "remediation": "If needed, run: build or download grammars into build/languages.so",
    }


def _check_embeddings() -> Dict:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        # Avoid heavy download by probing model name only
        model_name = "all-MiniLM-L6-v2"
        return {"name": "embeddings", "status": "ok", "detail": f"sentence-transformers available ({model_name})", "remediation": ""}
    except Exception as exc:
        return {
            "name": "embeddings",
            "status": "fail",
            "detail": f"sentence-transformers unavailable: {exc}",
            "remediation": "pip install sentence-transformers==2.6.0",
        }


def _check_faiss() -> Dict:
    try:
        import faiss  # type: ignore
        _ = faiss.IndexFlatIP(4)
        return {"name": "faiss", "status": "ok", "detail": "faiss available for vector search", "remediation": ""}
    except Exception as exc:
        return {
            "name": "faiss",
            "status": "warn",
            "detail": f"faiss not available: {exc}",
            "remediation": "Optional: pip install faiss-cpu",
        }


def _check_permissions() -> Dict:
    dirs = [Path("build"), Path("vendor")]
    non_writable = []
    for d in dirs:
        target = d if d.exists() else d.parent
        if not os.access(target, os.W_OK):
            non_writable.append(str(target))
    if non_writable:
        return {
            "name": "permissions",
            "status": "fail",
            "detail": f"Non-writable: {', '.join(non_writable)}",
            "remediation": "Run: chmod -R u+w " + " ".join(non_writable),
        }
    return {"name": "permissions", "status": "ok", "detail": "build/vendor writable", "remediation": ""}


def run_diagnostics(index_path: Optional[Path] = None) -> List[Dict]:
    """
    Run all diagnostic checks.

    Args:
        index_path: Optional path to an index file to validate its health.

    Returns:
        List of diagnostic results.
    """
    checks = [_check_grammars(), _check_embeddings(), _check_faiss(), _check_permissions()]

    if index_path:
        checks.append(_check_index_health(index_path))

    logger.info("Doctor diagnostics completed.")
    return checks
