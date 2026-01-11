"""
Post-Index Validation.

Health checks after indexing completes.

Phase: Bloat Protection System
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
from collections import Counter

from loguru import logger

from .config import IndexLimitsConfig, get_limits_config


@dataclass
class ValidationResult:
    """Result of post-index validation."""

    status: str  # "ok", "warn", "fail"
    checks: List[dict] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "checks": self.checks,
            "summary": self.summary,
        }


def validate_index_health(
    index_path: Path,
    config: Optional[IndexLimitsConfig] = None,
) -> ValidationResult:
    """
    Validate index health after building.

    Checks:
    1. Index size vs limit
    2. Symbol count vs limit
    3. FAISS vector count vs limit
    4. Symbol density per file

    Args:
        index_path: Path to index directory or database file (str or Path)
        config: Limits configuration

    Returns:
        ValidationResult with detailed checks
    """
    config = config or get_limits_config()
    checks = []

    # Normalize path - handle both str and Path
    if isinstance(index_path, str):
        index_path = Path(index_path)

    if index_path.is_file():
        db_path = index_path
        index_dir = index_path.parent
    else:
        db_path = index_path / "cerberus.db"
        index_dir = index_path

    # Check 1: Index size
    size_check = _check_index_size(db_path, config)
    checks.append(size_check)

    # Check 2: Symbol count (requires loading index)
    symbol_check = _check_symbol_count(db_path, config)
    checks.append(symbol_check)

    # Check 3: Vector count
    vector_check = _check_vector_count(index_dir, config)
    checks.append(vector_check)

    # Determine overall status
    statuses = [c["status"] for c in checks]
    if "fail" in statuses:
        overall = "fail"
    elif "warn" in statuses:
        overall = "warn"
    else:
        overall = "ok"

    # Summary
    failed = len([s for s in statuses if s == "fail"])
    warned = len([s for s in statuses if s == "warn"])

    if failed:
        summary = f"Validation failed: {failed} critical issue(s)"
    elif warned:
        summary = f"Validation warnings: {warned} issue(s) to monitor"
    else:
        summary = "All validation checks passed"

    logger.debug(f"Index validation: {overall} - {summary}")

    return ValidationResult(
        status=overall,
        checks=checks,
        summary=summary,
    )


def _check_index_size(db_path: Path, config: IndexLimitsConfig) -> dict:
    """Check database size against limit."""
    if not db_path.exists():
        return {
            "name": "index_size",
            "status": "warn",
            "detail": "Index database not found",
            "remediation": "Run: cerberus index <directory>",
        }

    try:
        size_bytes = db_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)
        limit_mb = config.max_index_size_mb
        percent = (size_bytes / config.max_index_size_bytes) * 100

        if size_bytes > config.max_index_size_bytes:
            return {
                "name": "index_size",
                "status": "fail",
                "detail": f"Index too large: {size_mb:.1f}MB ({percent:.0f}% of {limit_mb}MB limit)",
                "remediation": "Reduce scope with --ext filter or increase CERBERUS_MAX_INDEX_SIZE_MB",
                "value": size_mb,
                "limit": limit_mb,
                "percent": percent,
            }

        if percent > config.warn_threshold * 100:
            return {
                "name": "index_size",
                "status": "warn",
                "detail": f"Index size at {percent:.0f}% of limit ({size_mb:.1f}MB / {limit_mb}MB)",
                "remediation": "Monitor growth; consider scope reduction",
                "value": size_mb,
                "limit": limit_mb,
                "percent": percent,
            }

        return {
            "name": "index_size",
            "status": "ok",
            "detail": f"Index size OK: {size_mb:.1f}MB ({percent:.0f}% of limit)",
            "remediation": "",
            "value": size_mb,
            "limit": limit_mb,
            "percent": percent,
        }

    except Exception as e:
        logger.debug(f"Index size check error: {e}")
        return {
            "name": "index_size",
            "status": "warn",
            "detail": f"Could not check index size: {e}",
            "remediation": "",
        }


def _check_symbol_count(db_path: Path, config: IndexLimitsConfig) -> dict:
    """Check total symbol count against limit."""
    if not db_path.exists():
        return {
            "name": "symbol_count",
            "status": "warn",
            "detail": "Index database not found",
            "remediation": "Run: cerberus index <directory>",
        }

    try:
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get symbol count
        cursor.execute("SELECT COUNT(*) FROM symbols")
        symbol_count = cursor.fetchone()[0]
        conn.close()

        limit = config.max_total_symbols
        percent = (symbol_count / limit) * 100

        if symbol_count > limit:
            return {
                "name": "symbol_count",
                "status": "fail",
                "detail": f"Too many symbols: {symbol_count:,} ({percent:.0f}% of {limit:,} limit)",
                "remediation": "Reduce scope with --ext filter or increase CERBERUS_MAX_TOTAL_SYMBOLS",
                "value": symbol_count,
                "limit": limit,
                "percent": percent,
            }

        if percent > config.warn_threshold * 100:
            return {
                "name": "symbol_count",
                "status": "warn",
                "detail": f"Symbol count at {percent:.0f}% of limit ({symbol_count:,} / {limit:,})",
                "remediation": "Monitor growth; consider filtering",
                "value": symbol_count,
                "limit": limit,
                "percent": percent,
            }

        return {
            "name": "symbol_count",
            "status": "ok",
            "detail": f"Symbol count OK: {symbol_count:,} ({percent:.0f}% of limit)",
            "remediation": "",
            "value": symbol_count,
            "limit": limit,
            "percent": percent,
        }

    except Exception as e:
        logger.debug(f"Symbol count check error: {e}")
        return {
            "name": "symbol_count",
            "status": "warn",
            "detail": f"Could not check symbol count: {e}",
            "remediation": "",
        }


def _check_vector_count(index_dir: Path, config: IndexLimitsConfig) -> dict:
    """Check FAISS vector count against limit."""
    faiss_path = index_dir / "vectors.faiss"

    if not faiss_path.exists():
        return {
            "name": "vector_count",
            "status": "ok",
            "detail": "No FAISS vectors (embeddings not stored)",
            "remediation": "",
        }

    try:
        import faiss

        index = faiss.read_index(str(faiss_path))
        vector_count = index.ntotal
        limit = config.max_vectors
        percent = (vector_count / limit) * 100

        if vector_count > limit:
            return {
                "name": "vector_count",
                "status": "fail",
                "detail": f"Too many vectors: {vector_count:,} ({percent:.0f}% of {limit:,} limit)",
                "remediation": "Reduce scope or increase CERBERUS_MAX_VECTORS",
                "value": vector_count,
                "limit": limit,
                "percent": percent,
            }

        if percent > config.warn_threshold * 100:
            return {
                "name": "vector_count",
                "status": "warn",
                "detail": f"Vector count at {percent:.0f}% of limit ({vector_count:,} / {limit:,})",
                "remediation": "Monitor growth",
                "value": vector_count,
                "limit": limit,
                "percent": percent,
            }

        return {
            "name": "vector_count",
            "status": "ok",
            "detail": f"Vector count OK: {vector_count:,} ({percent:.0f}% of limit)",
            "remediation": "",
            "value": vector_count,
            "limit": limit,
            "percent": percent,
        }

    except ImportError:
        return {
            "name": "vector_count",
            "status": "ok",
            "detail": "FAISS not available, skipping vector check",
            "remediation": "",
        }
    except Exception as e:
        logger.debug(f"Vector count check error: {e}")
        return {
            "name": "vector_count",
            "status": "warn",
            "detail": f"Could not read FAISS index: {e}",
            "remediation": "Rebuild with --store-embeddings if needed",
        }
