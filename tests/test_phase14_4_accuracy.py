"""
Phase 14.4 Tests: Prediction Accuracy Tracking

Tests for correlating predictions with agent actions to measure accuracy.
"""

import pytest
import sqlite3
import tempfile
import time
import json
from pathlib import Path

from cerberus.mutation.ledger import DiffLedger


class TestPredictionAccuracyTracking:
    """Test suite for Phase 14.4 Prediction Accuracy Tracking."""

    @pytest.fixture
    def temp_ledger(self, tmp_path):
        """Create a temporary ledger for testing."""
        ledger_path = tmp_path / "test_ledger.db"
        ledger = DiffLedger(ledger_path=str(ledger_path))
        return ledger

    def test_action_log_table_creation(self, temp_ledger):
        """Test that action_log table is created properly."""
        conn = sqlite3.connect(temp_ledger.ledger_path)
        cursor = conn.cursor()

        # Check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='action_log'
        """)
        result = cursor.fetchone()
        assert result is not None, "action_log table should exist"

        # Check schema
        cursor.execute("PRAGMA table_info(action_log)")
        columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {'id', 'timestamp', 'action_type', 'target_symbol', 'target_file', 'command'}
        assert columns == expected_columns, f"Expected columns {expected_columns}, got {columns}"

        conn.close()

    def test_record_action_basic(self, temp_ledger):
        """Test recording a single action."""
        result = temp_ledger.record_action(
            action_type="edit",
            target_symbol="test_function",
            target_file="/test/file.py",
            command="cerberus mutations edit /test/file.py --symbol test_function"
        )

        assert result is True, "Action should be recorded successfully"

        # Verify it was recorded
        conn = sqlite3.connect(temp_ledger.ledger_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM action_log")
        rows = cursor.fetchall()
        conn.close()

        assert len(rows) == 1, "Should have one action logged"
        assert rows[0][2] == "edit", "Action type should be 'edit'"
        assert rows[0][3] == "test_function", "Target symbol should match"

    def test_record_action_no_symbol(self, temp_ledger):
        """Test recording an action without a symbol (e.g., file-level operation)."""
        result = temp_ledger.record_action(
            action_type="blueprint",
            target_symbol=None,
            target_file="/test/file.py",
            command="cerberus retrieval blueprint /test/file.py"
        )

        assert result is True, "Action should be recorded successfully"

        conn = sqlite3.connect(temp_ledger.ledger_path)
        cursor = conn.cursor()
        cursor.execute("SELECT target_symbol FROM action_log")
        symbol = cursor.fetchone()[0]
        conn.close()

        assert symbol is None, "Target symbol should be None"

    def test_prediction_accuracy_no_data(self, temp_ledger):
        """Test accuracy calculation with no data."""
        accuracy = temp_ledger.get_prediction_accuracy()

        assert accuracy['total_predictions'] == 0
        assert accuracy['predictions_followed'] == 0
        assert accuracy['accuracy_rate'] == 0.0

    def test_prediction_accuracy_with_followed_predictions(self, temp_ledger):
        """Test accuracy when predictions are followed."""
        # Record a prediction
        predictions = [
            {"symbol": "batch_edit", "confidence_score": 1.0},
            {"symbol": "validate_ops", "confidence_score": 0.95}
        ]
        temp_ledger.record_predictions("edited_function", "/test/file.py", predictions)

        # Wait a moment
        time.sleep(0.1)

        # Record actions that follow the predictions
        temp_ledger.record_action(
            action_type="get-symbol",
            target_symbol="batch_edit",
            target_file="/test/mutations.py",
            command="cerberus retrieval get-symbol batch_edit"
        )

        temp_ledger.record_action(
            action_type="edit",
            target_symbol="validate_ops",
            target_file="/test/mutations.py",
            command="cerberus mutations edit /test/mutations.py --symbol validate_ops"
        )

        # Calculate accuracy
        accuracy = temp_ledger.get_prediction_accuracy(time_window=10.0)

        assert accuracy['total_predictions'] == 2, "Should have 2 predictions"
        assert accuracy['predictions_followed'] == 2, "Both predictions should be followed"
        assert accuracy['accuracy_rate'] == 1.0, "100% accuracy"
        assert accuracy['avg_time_to_action_seconds'] > 0, "Should have time delta"

    def test_prediction_accuracy_with_ignored_predictions(self, temp_ledger):
        """Test accuracy when some predictions are ignored."""
        # Record predictions
        predictions = [
            {"symbol": "batch_edit", "confidence_score": 1.0},
            {"symbol": "validate_ops", "confidence_score": 0.95},
            {"symbol": "ignored_function", "confidence_score": 0.9}
        ]
        temp_ledger.record_predictions("edited_function", "/test/file.py", predictions)

        time.sleep(0.1)

        # Only follow one prediction
        temp_ledger.record_action(
            action_type="get-symbol",
            target_symbol="batch_edit",
            target_file="/test/mutations.py",
            command="cerberus retrieval get-symbol batch_edit"
        )

        # Calculate accuracy
        accuracy = temp_ledger.get_prediction_accuracy(time_window=10.0)

        assert accuracy['total_predictions'] == 3
        assert accuracy['predictions_followed'] == 1
        assert accuracy['predictions_ignored'] == 2
        assert abs(accuracy['accuracy_rate'] - 0.333) < 0.01, "Should be ~33% accuracy"

    def test_prediction_accuracy_time_window(self, temp_ledger):
        """Test that time window correctly filters actions."""
        # Record a prediction
        predictions = [{"symbol": "test_function", "confidence_score": 1.0}]
        temp_ledger.record_predictions("edited_function", "/test/file.py", predictions)

        # Record action outside time window (simulate 20 seconds later)
        conn = sqlite3.connect(temp_ledger.ledger_path)
        cursor = conn.cursor()

        # Get prediction timestamp
        cursor.execute("SELECT timestamp FROM prediction_log ORDER BY timestamp DESC LIMIT 1")
        pred_time = cursor.fetchone()[0]

        # Insert action 20 seconds later
        cursor.execute("""
            INSERT INTO action_log (timestamp, action_type, target_symbol, target_file, command)
            VALUES (?, ?, ?, ?, ?)
        """, (
            pred_time + 20.0,  # 20 seconds later
            "get-symbol",
            "test_function",
            "/test/file.py",
            "cerberus retrieval get-symbol test_function"
        ))
        conn.commit()
        conn.close()

        # With 10 second window, action should NOT be counted
        accuracy_10s = temp_ledger.get_prediction_accuracy(time_window=10.0)
        assert accuracy_10s['predictions_followed'] == 0, "Should not count action outside 10s window"

        # With 30 second window, action SHOULD be counted
        accuracy_30s = temp_ledger.get_prediction_accuracy(time_window=30.0)
        assert accuracy_30s['predictions_followed'] == 1, "Should count action within 30s window"

    def test_prediction_accuracy_multiple_actions_same_symbol(self, temp_ledger):
        """Test that only the first action within window is counted."""
        # Record a prediction
        predictions = [{"symbol": "test_function", "confidence_score": 1.0}]
        temp_ledger.record_predictions("edited_function", "/test/file.py", predictions)

        time.sleep(0.1)

        # Record multiple actions for the same symbol
        for i in range(3):
            temp_ledger.record_action(
                action_type="get-symbol",
                target_symbol="test_function",
                target_file="/test/file.py",
                command=f"cerberus retrieval get-symbol test_function (action {i})"
            )
            time.sleep(0.05)

        # Calculate accuracy
        accuracy = temp_ledger.get_prediction_accuracy(time_window=10.0)

        # Should only count the prediction once (first matching action)
        assert accuracy['total_predictions'] == 1
        assert accuracy['predictions_followed'] == 1
        assert accuracy['accuracy_rate'] == 1.0

    def test_get_prediction_stats_integration(self, temp_ledger):
        """Test integration of basic stats with accuracy tracking."""
        # Record some predictions
        temp_ledger.record_predictions("func1", "/test/file1.py", [
            {"symbol": "symbol_a", "confidence_score": 1.0},
            {"symbol": "symbol_b", "confidence_score": 0.95}
        ])

        temp_ledger.record_predictions("func2", "/test/file2.py", [
            {"symbol": "symbol_a", "confidence_score": 1.0}
        ])

        # Get stats
        stats = temp_ledger.get_prediction_stats(limit=100)

        assert stats['total_prediction_logs'] == 2, "Should have 2 prediction logs"
        assert stats['average_predictions_per_edit'] == 1.5, "Should average 1.5 predictions per edit"
        assert 'symbol_a' in stats['top_predicted_symbols'], "symbol_a should be in top predicted"
        assert stats['top_predicted_symbols']['symbol_a'] == 2, "symbol_a predicted twice"

    def test_action_indexing_performance(self, temp_ledger):
        """Test that action queries use indexes efficiently."""
        # Insert many actions
        for i in range(100):
            temp_ledger.record_action(
                action_type="edit",
                target_symbol=f"symbol_{i}",
                target_file=f"/test/file_{i}.py",
                command=f"test command {i}"
            )

        # Query should be fast due to indexes
        start_time = time.time()
        conn = sqlite3.connect(temp_ledger.ledger_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM action_log
            WHERE target_symbol = 'symbol_50'
            AND timestamp > 0
        """)
        result = cursor.fetchall()
        conn.close()
        elapsed = time.time() - start_time

        assert len(result) == 1, "Should find one matching action"
        assert elapsed < 0.1, f"Query should be fast (<100ms), took {elapsed*1000:.1f}ms"


class TestPredictionAccuracyCLI:
    """Test CLI integration for prediction accuracy."""

    def test_prediction_stats_command_exists(self):
        """Test that the prediction-stats command is available."""
        import subprocess
        result = subprocess.run(
            ["cerberus", "quality", "prediction-stats", "--help"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "Command should exist"
        assert "Phase 14.4" in result.stdout, "Should mention Phase 14.4"
        assert "accuracy" in result.stdout.lower(), "Should mention accuracy"

    def test_prediction_stats_json_output(self):
        """Test JSON output format."""
        import subprocess
        result = subprocess.run(
            ["cerberus", "quality", "prediction-stats", "--json"],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, "Command should execute successfully"

        # Parse JSON output
        output = json.loads(result.stdout.strip())

        assert "accuracy" in output, "Should have accuracy field"
        assert "basic_stats" in output, "Should have basic_stats field"
        assert "accuracy_rate" in output["accuracy"], "Should have accuracy_rate"
        assert "total_predictions" in output["accuracy"], "Should have total_predictions"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
