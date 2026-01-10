"""Dependency overlay for blueprint enrichment.

Phase 13.1: Integrates Phase 5 confidence scores to show symbol dependencies.
Phase 13.5: Adds dependency classification (internal/external/stdlib).
"""

from typing import List, Optional
from pathlib import Path
import sqlite3

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol
from .schemas import DependencyInfo
from .dependency_classifier import DependencyClassifier


class DependencyOverlay:
    """Enriches blueprint with dependency information from symbol_references."""

    def __init__(self, conn: sqlite3.Connection, project_root: Optional[Path] = None):
        """
        Initialize dependency overlay.

        Args:
            conn: SQLite connection to database with symbol_references table
            project_root: Optional project root for dependency classification (Phase 13.5)
        """
        self.conn = conn
        # Phase 13.5: Initialize dependency classifier
        self.classifier = DependencyClassifier(project_root or Path.cwd())

    def get_dependencies(self, symbol: CodeSymbol) -> List[DependencyInfo]:
        """
        Query dependencies for a symbol with confidence scores.

        Args:
            symbol: CodeSymbol to get dependencies for

        Returns:
            List of DependencyInfo objects with confidence scores
        """
        try:
            # Query symbol_references table
            cursor = self.conn.execute(
                """
                SELECT DISTINCT
                    target_symbol,
                    target_file,
                    confidence,
                    resolution_method,
                    reference_type
                FROM symbol_references
                WHERE source_file = ? AND source_symbol = ?
                ORDER BY confidence DESC, target_symbol ASC
                """,
                (symbol.file_path, symbol.name)
            )

            dependencies = []
            for row in cursor.fetchall():
                target_symbol, target_file, confidence, resolution_method, reference_type = row

                # Skip if target is None (unresolved)
                if not target_symbol:
                    continue

                # Phase 13.5: Classify dependency type
                dep_type = self.classifier.classify_dependency(
                    target_symbol=target_symbol,
                    target_file=target_file
                )

                dependencies.append(
                    DependencyInfo(
                        target=target_symbol,
                        target_file=target_file,
                        confidence=confidence or 1.0,
                        resolution_method=resolution_method,
                        reference_type=reference_type,
                        dependency_type=dep_type
                    )
                )

            if dependencies:
                logger.debug(
                    f"Found {len(dependencies)} dependencies for {symbol.name} "
                    f"in {symbol.file_path}"
                )

            return dependencies

        except Exception as e:
            logger.warning(f"Error querying dependencies for {symbol.name}: {e}")
            return []

    def get_bulk_dependencies(
        self,
        symbols: List[CodeSymbol]
    ) -> dict[str, List[DependencyInfo]]:
        """
        Get dependencies for multiple symbols efficiently.

        Args:
            symbols: List of CodeSymbol objects

        Returns:
            Dictionary mapping symbol names to dependency lists
        """
        if not symbols:
            return {}

        try:
            # Build query with multiple symbols
            # Group by file_path for efficiency
            file_symbols = {}
            for symbol in symbols:
                if symbol.file_path not in file_symbols:
                    file_symbols[symbol.file_path] = []
                file_symbols[symbol.file_path].append(symbol.name)

            result = {}

            # Query for each file
            for file_path, symbol_names in file_symbols.items():
                placeholders = ",".join("?" * len(symbol_names))
                cursor = self.conn.execute(
                    f"""
                    SELECT DISTINCT
                        source_symbol,
                        target_symbol,
                        target_file,
                        confidence,
                        resolution_method,
                        reference_type
                    FROM symbol_references
                    WHERE source_file = ?
                      AND source_symbol IN ({placeholders})
                      AND target_symbol IS NOT NULL
                    ORDER BY source_symbol, confidence DESC, target_symbol ASC
                    """,
                    (file_path, *symbol_names)
                )

                # Group by source_symbol
                for row in cursor.fetchall():
                    (
                        source_symbol,
                        target_symbol,
                        target_file,
                        confidence,
                        resolution_method,
                        reference_type
                    ) = row

                    if source_symbol not in result:
                        result[source_symbol] = []

                    # Phase 13.5: Classify dependency type
                    dep_type = self.classifier.classify_dependency(
                        target_symbol=target_symbol,
                        target_file=target_file
                    )

                    result[source_symbol].append(
                        DependencyInfo(
                            target=target_symbol,
                            target_file=target_file,
                            confidence=confidence or 1.0,
                            resolution_method=resolution_method,
                            reference_type=reference_type,
                            dependency_type=dep_type
                        )
                    )

            logger.debug(
                f"Retrieved dependencies for {len(result)} symbols across "
                f"{len(file_symbols)} files"
            )

            return result

        except Exception as e:
            logger.warning(f"Error in bulk dependency query: {e}")
            return {}

    def get_dependency_count(self, symbol: CodeSymbol) -> int:
        """
        Get count of dependencies for a symbol (lightweight).

        Args:
            symbol: CodeSymbol to count dependencies for

        Returns:
            Number of dependencies
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT COUNT(DISTINCT target_symbol)
                FROM symbol_references
                WHERE source_file = ?
                  AND source_symbol = ?
                  AND target_symbol IS NOT NULL
                """,
                (symbol.file_path, symbol.name)
            )
            count = cursor.fetchone()[0]
            return count or 0

        except Exception as e:
            logger.warning(f"Error counting dependencies: {e}")
            return 0
