"""
Real-time Bloat Enforcement.

Enforces limits during indexing with streaming support.

Phase: Bloat Protection System
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Iterator, Generator, Any

from loguru import logger

from .config import IndexLimitsConfig, get_limits_config


@dataclass
class EnforcementResult:
    """Result of enforcement decision."""

    allowed: bool
    status: str  # "ok", "warn", "skip", "stop"
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "status": self.status,
            "reason": self.reason,
        }


@dataclass
class EnforcementStats:
    """Statistics from enforcement during indexing."""

    files_processed: int = 0
    files_skipped_size: int = 0
    files_skipped_symbols: int = 0
    total_symbols: int = 0
    symbols_truncated_files: int = 0
    symbols_truncated_count: int = 0
    warnings: List[str] = field(default_factory=list)
    limit_reached: bool = False
    limit_reached_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "files_processed": self.files_processed,
            "files_skipped_size": self.files_skipped_size,
            "files_skipped_symbols": self.files_skipped_symbols,
            "total_symbols": self.total_symbols,
            "symbols_truncated_files": self.symbols_truncated_files,
            "symbols_truncated_count": self.symbols_truncated_count,
            "warning_count": len(self.warnings),
            "warnings": self.warnings[:10],  # Limit to first 10
            "limit_reached": self.limit_reached,
            "limit_reached_reason": self.limit_reached_reason,
        }


class BloatEnforcer:
    """
    Real-time bloat enforcement during indexing.

    Wraps the streaming scanner to enforce limits and track statistics.
    """

    def __init__(self, config: Optional[IndexLimitsConfig] = None):
        """
        Initialize enforcer.

        Args:
            config: Limits configuration (uses global if None)
        """
        self.config = config or get_limits_config()
        self.stats = EnforcementStats()
        self._total_limit_reached = False

    def enforce_file_size(
        self,
        file_path: Path,
        file_size: int,
    ) -> EnforcementResult:
        """
        Check if file should be processed based on size.

        Args:
            file_path: Path to file
            file_size: Size in bytes

        Returns:
            EnforcementResult
        """
        if file_size > self.config.max_file_bytes:
            self.stats.files_skipped_size += 1
            size_mb = file_size / (1024 * 1024)
            limit_mb = self.config.max_file_bytes / (1024 * 1024)
            logger.debug(
                f"Skipping {file_path}: {size_mb:.2f}MB > {limit_mb:.2f}MB limit"
            )
            return EnforcementResult(
                allowed=False,
                status="skip",
                reason=f"File too large: {size_mb:.2f}MB > {limit_mb:.2f}MB limit",
            )

        return EnforcementResult(allowed=True, status="ok")

    def enforce_symbols_per_file(
        self,
        file_path: str,
        symbols: List[Any],
    ) -> tuple[List[Any], EnforcementResult]:
        """
        Check symbol count for a single file, truncate if needed.

        Args:
            file_path: Path to file
            symbols: List of symbols from the file

        Returns:
            Tuple of (possibly truncated symbols, EnforcementResult)
        """
        symbol_count = len(symbols)

        if symbol_count > self.config.max_symbols_per_file:
            self.stats.files_skipped_symbols += 1
            self.stats.symbols_truncated_files += 1
            truncated_count = symbol_count - self.config.max_symbols_per_file
            self.stats.symbols_truncated_count += truncated_count

            warning = (
                f"Truncated {file_path}: {symbol_count} symbols "
                f"> {self.config.max_symbols_per_file} limit "
                f"(dropped {truncated_count})"
            )
            self.stats.warnings.append(warning)
            logger.warning(warning)

            # Truncate symbols
            truncated_symbols = symbols[: self.config.max_symbols_per_file]

            return truncated_symbols, EnforcementResult(
                allowed=True,  # Still process, but truncated
                status="warn",
                reason=f"Symbols truncated: {symbol_count} > {self.config.max_symbols_per_file} limit",
            )

        return symbols, EnforcementResult(allowed=True, status="ok")

    def enforce_total_symbols(
        self,
        new_symbols: int,
    ) -> EnforcementResult:
        """
        Check if adding symbols would exceed total limit.

        Args:
            new_symbols: Number of symbols to add

        Returns:
            EnforcementResult
        """
        if self._total_limit_reached:
            return EnforcementResult(
                allowed=False,
                status="stop",
                reason="Total symbol limit already reached",
            )

        projected = self.stats.total_symbols + new_symbols

        if projected > self.config.max_total_symbols:
            self._total_limit_reached = True
            self.stats.limit_reached = True
            reason = (
                f"Total symbol limit reached: {projected:,} "
                f"> {self.config.max_total_symbols:,}. "
                f"Override with: CERBERUS_MAX_TOTAL_SYMBOLS={self.config.max_total_symbols * 2}"
            )
            self.stats.limit_reached_reason = reason
            logger.warning(reason)
            return EnforcementResult(
                allowed=False,
                status="stop",
                reason=reason,
            )

        # Warning threshold
        threshold = int(self.config.max_total_symbols * self.config.warn_threshold)
        if projected > threshold and self.stats.total_symbols <= threshold:
            percent = int((projected / self.config.max_total_symbols) * 100)
            warning = (
                f"Approaching symbol limit: {projected:,}/{self.config.max_total_symbols:,} "
                f"({percent}%)"
            )
            self.stats.warnings.append(warning)
            logger.warning(warning)

        self.stats.total_symbols += new_symbols
        return EnforcementResult(allowed=True, status="ok")

    def wrap_file_stream(
        self,
        stream: Iterator[Any],
    ) -> Generator[Any, None, None]:
        """
        Wrap file stream with enforcement.

        Filters files based on limits and tracks statistics.
        Expects FileResult objects with file_obj.size and symbols attributes.

        Args:
            stream: Original FileResult stream

        Yields:
            FileResult objects that pass enforcement
        """
        for result in stream:
            # Check total limit before processing
            total_check = self.enforce_total_symbols(len(result.symbols))
            if not total_check.allowed:
                logger.warning(f"Stopping indexing: {total_check.reason}")
                break

            # Actually we already added the symbols in enforce_total_symbols
            # Need to subtract and re-check after truncation
            self.stats.total_symbols -= len(result.symbols)

            # Check per-file symbol limit and truncate if needed
            result.symbols, symbol_check = self.enforce_symbols_per_file(
                result.file_obj.path,
                result.symbols,
            )

            # Now add the (possibly truncated) count
            total_check = self.enforce_total_symbols(len(result.symbols))
            if not total_check.allowed:
                logger.warning(f"Stopping indexing: {total_check.reason}")
                break

            self.stats.files_processed += 1
            yield result

    def get_summary(self) -> dict:
        """Get enforcement summary for reporting."""
        return {
            "stats": self.stats.to_dict(),
            "config": self.config.to_dict(),
            "status": "limit_reached" if self._total_limit_reached else "ok",
        }

    def log_summary(self) -> None:
        """Log enforcement summary."""
        stats = self.stats

        if stats.files_skipped_size > 0:
            logger.info(
                f"Skipped {stats.files_skipped_size} file(s) exceeding "
                f"{self.config.max_file_bytes / (1024*1024):.1f}MB size limit"
            )

        if stats.symbols_truncated_files > 0:
            logger.info(
                f"Truncated symbols in {stats.symbols_truncated_files} file(s) "
                f"(dropped {stats.symbols_truncated_count:,} symbols total)"
            )

        if stats.limit_reached:
            logger.warning(
                f"Index stopped at {stats.total_symbols:,} symbols "
                f"(limit: {self.config.max_total_symbols:,})"
            )
        else:
            logger.info(
                f"Indexed {stats.total_symbols:,} symbols "
                f"({int(stats.total_symbols / self.config.max_total_symbols * 100)}% of limit)"
            )
