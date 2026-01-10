"""
DiffLedger: Track write efficiency metrics.

Phase 11: Prove value of surgical edits with data.
"""

import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional

from cerberus.logging_config import logger
from cerberus.schemas import DiffMetric
from .config import MUTATION_CONFIG


class DiffLedger:
    """
    Track and store mutation efficiency metrics.

    Metrics:
    - Write efficiency ratio (lines_changed / lines_total)
    - Tokens saved vs full rewrite
    - Operations by type (edit/insert/delete)
    """

    def __init__(self, ledger_path: Optional[str] = None):
        """
        Initialize diff ledger.

        Args:
            ledger_path: Path to SQLite ledger database
        """
        self.ledger_path = ledger_path or MUTATION_CONFIG["ledger_path"]
        self._init_database()

    def _init_database(self):
        """Initialize ledger database with schema."""
        try:
            conn = sqlite3.connect(self.ledger_path)
            cursor = conn.cursor()

            # Create diff_metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS diff_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    operation TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    lines_changed INTEGER NOT NULL,
                    lines_total INTEGER NOT NULL,
                    write_efficiency REAL NOT NULL,
                    tokens_saved INTEGER NOT NULL
                )
            """)

            # Create index on timestamp for efficient queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON diff_metrics(timestamp)
            """)

            conn.commit()
            conn.close()

            logger.debug(f"Diff ledger initialized: {self.ledger_path}")

        except Exception as e:
            logger.error(f"Failed to initialize ledger database: {e}")

    def record_mutation(
        self,
        operation: str,
        file_path: str,
        lines_changed: int,
        lines_total: int
    ) -> Optional[DiffMetric]:
        """
        Record a mutation operation.

        Args:
            operation: Operation type ("edit", "insert", "delete")
            file_path: Path to modified file
            lines_changed: Number of lines changed
            lines_total: Total lines in file

        Returns:
            DiffMetric object or None if failed
        """
        if lines_total == 0:
            write_efficiency = 0.0
        else:
            write_efficiency = lines_changed / lines_total

        # Estimate tokens saved (4 tokens per line average)
        tokens_saved = (lines_total - lines_changed) * 4

        metric = DiffMetric(
            timestamp=time.time(),
            operation=operation,
            file_path=file_path,
            lines_changed=lines_changed,
            lines_total=lines_total,
            write_efficiency=write_efficiency,
            tokens_saved=tokens_saved
        )

        # Store in database
        try:
            conn = sqlite3.connect(self.ledger_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO diff_metrics
                (timestamp, operation, file_path, lines_changed, lines_total,
                 write_efficiency, tokens_saved)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                metric.timestamp,
                metric.operation,
                metric.file_path,
                metric.lines_changed,
                metric.lines_total,
                metric.write_efficiency,
                metric.tokens_saved
            ))

            conn.commit()
            conn.close()

            logger.debug(f"Recorded mutation: {operation} on {file_path}")
            return metric

        except Exception as e:
            logger.error(f"Failed to record mutation: {e}")
            return None

    def get_statistics(self) -> Dict[str, any]:
        """
        Get overall statistics from ledger.

        Returns:
            Dict with aggregated statistics
        """
        try:
            conn = sqlite3.connect(self.ledger_path)
            cursor = conn.cursor()

            # Total operations
            cursor.execute("SELECT COUNT(*) FROM diff_metrics")
            total_ops = cursor.fetchone()[0]

            # Average write efficiency
            cursor.execute("SELECT AVG(write_efficiency) FROM diff_metrics")
            avg_efficiency = cursor.fetchone()[0] or 0.0

            # Total tokens saved
            cursor.execute("SELECT SUM(tokens_saved) FROM diff_metrics")
            total_tokens_saved = cursor.fetchone()[0] or 0

            # Operations by type
            cursor.execute("""
                SELECT operation, COUNT(*) FROM diff_metrics
                GROUP BY operation
            """)
            ops_by_type = dict(cursor.fetchall())

            conn.close()

            return {
                "total_operations": total_ops,
                "average_write_efficiency": round(avg_efficiency, 4),
                "total_tokens_saved": total_tokens_saved,
                "operations_by_type": ops_by_type
            }

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "total_operations": 0,
                "average_write_efficiency": 0.0,
                "total_tokens_saved": 0,
                "operations_by_type": {}
            }

    def get_recent_metrics(self, limit: int = 10) -> List[DiffMetric]:
        """
        Get recent metrics from ledger.

        Args:
            limit: Number of recent metrics to retrieve

        Returns:
            List of DiffMetric objects
        """
        try:
            conn = sqlite3.connect(self.ledger_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT timestamp, operation, file_path, lines_changed,
                       lines_total, write_efficiency, tokens_saved
                FROM diff_metrics
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            conn.close()

            metrics = []
            for row in rows:
                metric = DiffMetric(
                    timestamp=row[0],
                    operation=row[1],
                    file_path=row[2],
                    lines_changed=row[3],
                    lines_total=row[4],
                    write_efficiency=row[5],
                    tokens_saved=row[6]
                )
                metrics.append(metric)

            return metrics

        except Exception as e:
            logger.error(f"Failed to get recent metrics: {e}")
            return []
