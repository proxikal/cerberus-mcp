"""
DiffLedger: Track write efficiency metrics.

Phase 11: Prove value of surgical edits with data.
"""

import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional, Any

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

            # Create prediction_log table (Phase 14.3)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prediction_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    edited_symbol TEXT NOT NULL,
                    edited_file TEXT NOT NULL,
                    predictions_count INTEGER NOT NULL,
                    predicted_symbols TEXT NOT NULL,
                    confidence_scores TEXT NOT NULL
                )
            """)

            # Create index on timestamp for predictions
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prediction_timestamp
                ON prediction_log(timestamp)
            """)

            # Create action_log table (Phase 14.4)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    action_type TEXT NOT NULL,
                    target_symbol TEXT,
                    target_file TEXT NOT NULL,
                    command TEXT NOT NULL
                )
            """)

            # Create index on timestamp for actions
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_action_timestamp
                ON action_log(timestamp)
            """)

            # Create index on target_symbol for fast correlation
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_action_symbol
                ON action_log(target_symbol)
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

    def record_predictions(
        self,
        edited_symbol: str,
        edited_file: str,
        predictions: List[Dict[str, Any]]
    ) -> bool:
        """
        Record predictions made by the prediction engine (Phase 14.3).

        Args:
            edited_symbol: Name of the symbol that was edited
            edited_file: File path of the edited symbol
            predictions: List of prediction dictionaries

        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            import json
            import time

            conn = sqlite3.connect(self.ledger_path)
            cursor = conn.cursor()

            # Extract symbols and scores
            predicted_symbols = [p.get("symbol", "") for p in predictions]
            confidence_scores = [p.get("confidence_score", 0.0) for p in predictions]

            cursor.execute("""
                INSERT INTO prediction_log (
                    timestamp, edited_symbol, edited_file,
                    predictions_count, predicted_symbols, confidence_scores
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                time.time(),
                edited_symbol,
                edited_file,
                len(predictions),
                json.dumps(predicted_symbols),
                json.dumps(confidence_scores)
            ))

            conn.commit()
            conn.close()

            logger.debug(f"Recorded {len(predictions)} predictions for {edited_symbol}")
            return True

        except Exception as e:
            logger.error(f"Failed to record predictions: {e}")
            return False

    def get_prediction_stats(self, limit: int = 100) -> Dict[str, Any]:
        """
        Get statistics about predictions (Phase 14.3 basic logging).

        Args:
            limit: Number of recent predictions to analyze

        Returns:
            Dictionary with prediction statistics
        """
        try:
            import json

            conn = sqlite3.connect(self.ledger_path)
            cursor = conn.cursor()

            # Total predictions made
            cursor.execute("""
                SELECT COUNT(*) FROM prediction_log
            """)
            total_logs = cursor.fetchone()[0]

            # Average predictions per symbol edit
            cursor.execute("""
                SELECT AVG(predictions_count) FROM prediction_log
                LIMIT ?
            """, (limit,))
            avg_predictions = cursor.fetchone()[0] or 0.0

            # Most frequently predicted symbols
            cursor.execute("""
                SELECT predicted_symbols FROM prediction_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()

            all_predicted = []
            for row in rows:
                symbols = json.loads(row[0])
                all_predicted.extend(symbols)

            # Count frequency
            from collections import Counter
            symbol_counts = Counter(all_predicted)
            top_predicted = dict(symbol_counts.most_common(5))

            conn.close()

            return {
                "total_prediction_logs": total_logs,
                "average_predictions_per_edit": round(avg_predictions, 2),
                "top_predicted_symbols": top_predicted
            }

        except Exception as e:
            logger.error(f"Failed to get prediction stats: {e}")
            return {
                "total_prediction_logs": 0,
                "average_predictions_per_edit": 0.0,
                "top_predicted_symbols": {}
            }

    def record_action(
        self,
        action_type: str,
        target_symbol: Optional[str],
        target_file: str,
        command: str
    ) -> bool:
        """
        Record an agent action for correlation with predictions (Phase 14.4).

        Args:
            action_type: Type of action (edit, get-symbol, blueprint, etc.)
            target_symbol: Symbol being accessed/modified (if applicable)
            target_file: File path being accessed
            command: Full cerberus command executed

        Returns:
            True if recorded successfully, False otherwise
        """
        try:
            import time

            conn = sqlite3.connect(self.ledger_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO action_log (
                    timestamp, action_type, target_symbol, target_file, command
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                time.time(),
                action_type,
                target_symbol,
                target_file,
                command
            ))

            conn.commit()
            conn.close()

            logger.debug(f"Recorded action: {action_type} on {target_symbol or target_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to record action: {e}")
            return False

    def get_prediction_accuracy(
        self,
        time_window: float = 900.0,  # 15 minutes in seconds
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Calculate prediction accuracy by correlating predictions with actions (Phase 14.4).

        Args:
            time_window: Time window in seconds to consider actions as "following" predictions (default: 15 min)
            limit: Number of recent predictions to analyze

        Returns:
            Dictionary with accuracy metrics
        """
        try:
            import json

            conn = sqlite3.connect(self.ledger_path)
            cursor = conn.cursor()

            # Get recent predictions
            cursor.execute("""
                SELECT id, timestamp, edited_symbol, edited_file,
                       predicted_symbols, confidence_scores
                FROM prediction_log
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            predictions = cursor.fetchall()

            if not predictions:
                conn.close()
                return {
                    "total_predictions": 0,
                    "predictions_followed": 0,
                    "accuracy_rate": 0.0,
                    "avg_time_to_action": 0.0,
                    "actions_per_prediction": 0.0
                }

            total_prediction_count = 0
            followed_count = 0
            time_deltas = []

            for pred_row in predictions:
                pred_id, pred_timestamp, edited_symbol, edited_file, predicted_symbols_json, confidence_scores_json = pred_row
                predicted_symbols = json.loads(predicted_symbols_json)
                total_prediction_count += len(predicted_symbols)

                # For each predicted symbol, check if there was a follow-up action within time window
                for predicted_symbol in predicted_symbols:
                    cursor.execute("""
                        SELECT timestamp, action_type
                        FROM action_log
                        WHERE target_symbol = ?
                          AND timestamp > ?
                          AND timestamp <= ?
                        ORDER BY timestamp ASC
                        LIMIT 1
                    """, (
                        predicted_symbol,
                        pred_timestamp,
                        pred_timestamp + time_window
                    ))

                    action_row = cursor.fetchone()
                    if action_row:
                        followed_count += 1
                        action_timestamp = action_row[0]
                        time_delta = action_timestamp - pred_timestamp
                        time_deltas.append(time_delta)

            conn.close()

            # Calculate metrics
            accuracy_rate = (followed_count / total_prediction_count) if total_prediction_count > 0 else 0.0
            avg_time_to_action = (sum(time_deltas) / len(time_deltas)) if time_deltas else 0.0

            return {
                "total_predictions": total_prediction_count,
                "predictions_followed": followed_count,
                "predictions_ignored": total_prediction_count - followed_count,
                "accuracy_rate": round(accuracy_rate, 3),
                "avg_time_to_action_seconds": round(avg_time_to_action, 1),
                "time_window_seconds": time_window,
                "sample_size": len(predictions)
            }

        except Exception as e:
            logger.error(f"Failed to get prediction accuracy: {e}")
            return {
                "total_predictions": 0,
                "predictions_followed": 0,
                "accuracy_rate": 0.0,
                "error": str(e)
            }
