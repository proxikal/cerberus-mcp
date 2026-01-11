"""
Pre-flight Checks.

Disk space and system resource checks before indexing starts.

Phase: Bloat Protection System
"""

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from loguru import logger

from .config import IndexLimitsConfig, get_limits_config


@dataclass
class PreflightResult:
    """Result of pre-flight checks."""

    status: str  # "ok", "warn", "fail"
    checks: List[dict] = field(default_factory=list)
    can_proceed: bool = True
    summary: str = ""

    def to_dict(self) -> dict:
        """Export as dictionary for JSON output."""
        return {
            "status": self.status,
            "checks": self.checks,
            "can_proceed": self.can_proceed,
            "summary": self.summary,
        }


def run_preflight_checks(
    output_path: Path,
    config: Optional[IndexLimitsConfig] = None,
) -> PreflightResult:
    """
    Run pre-flight checks before indexing.

    Checks:
    1. Disk space availability
    2. Output directory writability
    3. Existing index size (if incremental)

    Args:
        output_path: Path where index will be written
        config: Limits configuration (uses global if None)

    Returns:
        PreflightResult with status and details
    """
    config = config or get_limits_config()
    checks = []

    # Check 1: Disk space
    disk_check = _check_disk_space(output_path, config)
    checks.append(disk_check)

    # Check 2: Directory writability
    write_check = _check_write_permission(output_path)
    checks.append(write_check)

    # Check 3: Existing index size
    existing_check = _check_existing_index(output_path, config)
    checks.append(existing_check)

    # Determine overall status
    statuses = [c["status"] for c in checks]
    if "fail" in statuses:
        overall_status = "fail"
        can_proceed = False
    elif "warn" in statuses:
        overall_status = "warn"
        can_proceed = not config.strict_mode
    else:
        overall_status = "ok"
        can_proceed = True

    # Generate summary
    failed = [c for c in checks if c["status"] == "fail"]
    warned = [c for c in checks if c["status"] == "warn"]

    if failed:
        summary = f"Pre-flight failed: {failed[0]['detail']}"
    elif warned:
        summary = f"Pre-flight warnings: {len(warned)} issue(s)"
    else:
        summary = "All pre-flight checks passed"

    logger.debug(f"Pre-flight result: {overall_status} - {summary}")

    return PreflightResult(
        status=overall_status,
        checks=checks,
        can_proceed=can_proceed,
        summary=summary,
    )


def _check_disk_space(output_path: Path, config: IndexLimitsConfig) -> dict:
    """Check available disk space."""
    try:
        # Get disk stats for target directory
        target_dir = output_path.parent if output_path.suffix else output_path
        target_dir = target_dir.resolve()

        # Walk up to find existing directory
        while not target_dir.exists() and target_dir.parent != target_dir:
            target_dir = target_dir.parent

        disk_usage = shutil.disk_usage(str(target_dir))
        free_bytes = disk_usage.free
        free_mb = free_bytes / (1024 * 1024)

        if free_bytes < config.min_free_disk_bytes:
            return {
                "name": "disk_space",
                "status": "fail",
                "detail": f"Insufficient disk space: {free_mb:.1f}MB free, need {config.min_free_disk_mb}MB",
                "remediation": "Free up disk space or reduce index scope with --ext filter",
                "value": free_mb,
                "limit": config.min_free_disk_mb,
            }

        # Warning at 2x minimum
        if free_bytes < config.min_free_disk_bytes * 2:
            return {
                "name": "disk_space",
                "status": "warn",
                "detail": f"Low disk space: {free_mb:.1f}MB free (minimum: {config.min_free_disk_mb}MB)",
                "remediation": "Consider freeing disk space before large indexing operations",
                "value": free_mb,
                "limit": config.min_free_disk_mb,
            }

        return {
            "name": "disk_space",
            "status": "ok",
            "detail": f"Disk space OK: {free_mb:.1f}MB free",
            "remediation": "",
            "value": free_mb,
            "limit": config.min_free_disk_mb,
        }

    except Exception as e:
        logger.debug(f"Disk space check error: {e}")
        return {
            "name": "disk_space",
            "status": "warn",
            "detail": f"Could not check disk space: {e}",
            "remediation": "Verify disk is accessible",
        }


def _check_write_permission(output_path: Path) -> dict:
    """Check write permission on output directory."""
    try:
        target_dir = output_path.parent if output_path.suffix else output_path
        target_dir = target_dir.resolve()

        # Find existing parent
        while not target_dir.exists() and target_dir.parent != target_dir:
            target_dir = target_dir.parent

        if not os.access(target_dir, os.W_OK):
            return {
                "name": "write_permission",
                "status": "fail",
                "detail": f"No write permission on {target_dir}",
                "remediation": f"Run: chmod u+w {target_dir}",
            }

        return {
            "name": "write_permission",
            "status": "ok",
            "detail": f"Write permission OK on {target_dir}",
            "remediation": "",
        }

    except Exception as e:
        logger.debug(f"Permission check error: {e}")
        return {
            "name": "write_permission",
            "status": "warn",
            "detail": f"Could not check permissions: {e}",
            "remediation": "Verify directory access",
        }


def _check_existing_index(output_path: Path, config: IndexLimitsConfig) -> dict:
    """Check existing index size if present."""
    try:
        # Determine DB path
        if output_path.suffix == ".db":
            db_path = output_path
        else:
            db_path = output_path / "cerberus.db"

        if not db_path.exists():
            return {
                "name": "existing_index",
                "status": "ok",
                "detail": "No existing index (fresh build)",
                "remediation": "",
            }

        size_bytes = db_path.stat().st_size
        size_mb = size_bytes / (1024 * 1024)

        if size_bytes > config.max_index_size_bytes:
            return {
                "name": "existing_index",
                "status": "warn",
                "detail": f"Existing index ({size_mb:.1f}MB) exceeds limit ({config.max_index_size_mb}MB)",
                "remediation": "Consider: cerberus clean --all or increase CERBERUS_MAX_INDEX_SIZE_MB",
                "value": size_mb,
                "limit": config.max_index_size_mb,
            }

        warn_threshold = config.max_index_size_bytes * config.warn_threshold
        if size_bytes > warn_threshold:
            percent = int((size_bytes / config.max_index_size_bytes) * 100)
            return {
                "name": "existing_index",
                "status": "warn",
                "detail": f"Existing index at {percent}% of limit ({size_mb:.1f}MB)",
                "remediation": "Monitor index growth; consider scope reduction",
                "value": size_mb,
                "limit": config.max_index_size_mb,
            }

        return {
            "name": "existing_index",
            "status": "ok",
            "detail": f"Existing index size OK: {size_mb:.1f}MB",
            "remediation": "",
            "value": size_mb,
            "limit": config.max_index_size_mb,
        }

    except Exception as e:
        logger.debug(f"Existing index check error: {e}")
        return {
            "name": "existing_index",
            "status": "warn",
            "detail": f"Could not check existing index: {e}",
            "remediation": "",
        }
