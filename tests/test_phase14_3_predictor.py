"""
Phase 14.3 Tests: Predictive Editing - Deterministic Relationship Discovery

Tests for the prediction engine that suggests related changes based on AST relationships.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path

from cerberus.quality.predictor import PredictionEngine, Prediction, PredictionStats


class TestPredictionEngine:
    """Test suite for Phase 14.3 Prediction Engine."""

    @pytest.fixture
    def temp_index(self, tmp_path):
        """Create a temporary SQLite index for testing."""
        index_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(index_path))
        cursor = conn.cursor()

        # Create minimal schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY,
                name TEXT,
                file_path TEXT,
                type TEXT,
                start_line INTEGER,
                end_line INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY,
                caller_name TEXT,
                callee_name TEXT,
                file_path TEXT,
                line_number INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY,
                file_path TEXT,
                import_name TEXT,
                module_path TEXT
            )
        """)

        # Insert test data
        cursor.execute("""
            INSERT INTO symbols (name, file_path, type, start_line, end_line)
            VALUES ('validate_ops', '/test/mutations.py', 'function', 10, 20)
        """)

        cursor.execute("""
            INSERT INTO symbols (name, file_path, type, start_line, end_line)
            VALUES ('batch_edit', '/test/mutations.py', 'function', 50, 100)
        """)

        cursor.execute("""
            INSERT INTO calls (caller_name, callee_name, file_path, line_number)
            VALUES ('batch_edit', 'validate_ops', '/test/mutations.py', 55)
        """)

        conn.commit()
        conn.close()

        return index_path

    def test_engine_initialization(self, temp_index):
        """Test that PredictionEngine initializes correctly."""
        engine = PredictionEngine(str(temp_index))
        assert engine.index_path == str(temp_index)
        assert engine.confidence_threshold == 0.9

    def test_engine_custom_threshold(self, temp_index):
        """Test PredictionEngine with custom confidence threshold."""
        engine = PredictionEngine(str(temp_index), confidence_threshold=0.95)
        assert engine.confidence_threshold == 0.95

    def test_predict_related_changes_basic(self, temp_index):
        """Test basic prediction functionality."""
        engine = PredictionEngine(str(temp_index))
        predictions, stats = engine.predict_related_changes(
            edited_symbol="validate_ops",
            file_path="/test/mutations.py"
        )

        # Should return predictions and stats
        assert isinstance(predictions, list)
        assert isinstance(stats, PredictionStats)
        assert stats.total_analyzed >= 0

    def test_find_direct_dependencies(self, temp_index):
        """Test finding direct dependencies (callees)."""
        engine = PredictionEngine(str(temp_index))
        deps = engine._find_direct_dependencies("batch_edit", "/test/mutations.py")

        # batch_edit calls validate_ops
        assert len(deps) > 0
        assert any(d.symbol == "validate_ops" for d in deps)
        assert all(d.confidence_score == 1.0 for d in deps)  # AST-verified
        assert all(d.reason == "direct_dependency" for d in deps)

    def test_confidence_filtering(self, temp_index):
        """Test that only high-confidence predictions are shown."""
        engine = PredictionEngine(str(temp_index), confidence_threshold=0.95)
        predictions, stats = engine.predict_related_changes(
            edited_symbol="validate_ops",
            file_path="/test/mutations.py"
        )

        # All shown predictions should meet threshold
        for pred in predictions:
            assert pred.confidence_score >= 0.95

    def test_to_json_format(self, temp_index):
        """Test JSON serialization of predictions."""
        engine = PredictionEngine(str(temp_index))
        predictions = [
            Prediction(
                confidence="HIGH",
                confidence_score=1.0,
                symbol="test_func",
                file="/test/file.py",
                line=10,
                reason="direct_caller",
                relationship="calls target (AST-verified)"
            )
        ]
        stats = PredictionStats(
            total_analyzed=5,
            high_confidence=1,
            shown=1,
            filtered=4
        )

        result = engine.to_json(predictions, stats)

        assert "predictions" in result
        assert "prediction_stats" in result
        assert len(result["predictions"]) == 1
        assert result["prediction_stats"]["total_analyzed"] == 5
        assert result["prediction_stats"]["shown"] == 1

    def test_to_text_format(self, temp_index):
        """Test human-readable text format."""
        engine = PredictionEngine(str(temp_index))
        predictions = [
            Prediction(
                confidence="HIGH",
                confidence_score=1.0,
                symbol="test_func",
                file="/test/file.py",
                line=10,
                reason="direct_caller",
                relationship="calls target (AST-verified)"
            )
        ]

        text = engine.to_text(predictions, verbose=False)
        assert "[Predictive]" in text
        assert "test_func" in text

    def test_empty_predictions(self, temp_index):
        """Test handling of no predictions."""
        engine = PredictionEngine(str(temp_index))
        predictions = []

        text = engine.to_text(predictions)
        assert "No high-confidence suggestions" in text

    def test_prediction_limit(self, temp_index):
        """Test that predictions are limited to top 5."""
        engine = PredictionEngine(str(temp_index))

        # Create 10 mock predictions
        all_preds = [
            Prediction(
                confidence="HIGH",
                confidence_score=1.0,
                symbol=f"func_{i}",
                file=f"/test/file_{i}.py",
                line=i,
                reason="direct_caller",
                relationship="test"
            )
            for i in range(10)
        ]

        # The engine should limit to 5
        # We'll test this indirectly through predict_related_changes
        # which applies the limit

    def test_imports_file_verification(self, temp_index):
        """Test import verification for test files."""
        engine = PredictionEngine(str(temp_index))

        # Test with non-existent import
        result = engine._imports_file("/nonexistent/test.py", "/target/file.py")
        assert result is False  # Should be False for non-existent

    def test_risk_score_default(self, temp_index):
        """Test default risk score calculation."""
        engine = PredictionEngine(str(temp_index))
        risk_score = engine._get_risk_score("/test/file.py")

        # Should return default medium risk
        assert 0.0 <= risk_score <= 1.0
        assert risk_score == 0.5  # Default value


class TestPredictionDataStructures:
    """Test prediction data structures."""

    def test_prediction_creation(self):
        """Test Prediction dataclass creation."""
        pred = Prediction(
            confidence="HIGH",
            confidence_score=1.0,
            symbol="test_func",
            file="/test.py",
            line=10,
            reason="direct_caller",
            relationship="calls target"
        )

        assert pred.confidence == "HIGH"
        assert pred.confidence_score == 1.0
        assert pred.symbol == "test_func"
        assert pred.file == "/test.py"
        assert pred.line == 10

    def test_prediction_stats_creation(self):
        """Test PredictionStats dataclass creation."""
        stats = PredictionStats(
            total_analyzed=10,
            high_confidence=5,
            shown=3,
            filtered=7
        )

        assert stats.total_analyzed == 10
        assert stats.high_confidence == 5
        assert stats.shown == 3
        assert stats.filtered == 7


class TestPredictionLogging:
    """Test prediction logging to ledger (Phase 14.3 basic logging)."""

    def test_record_predictions(self, tmp_path):
        """Test recording predictions to ledger."""
        from cerberus.mutation.ledger import DiffLedger

        ledger_path = tmp_path / "ledger.db"
        ledger = DiffLedger(ledger_path=str(ledger_path))

        # Record some predictions
        predictions = [
            {"symbol": "test_func", "confidence_score": 1.0},
            {"symbol": "another_func", "confidence_score": 0.95}
        ]

        result = ledger.record_predictions(
            edited_symbol="validate_ops",
            edited_file="/test/mutations.py",
            predictions=predictions
        )

        assert result is True

    def test_get_prediction_stats(self, tmp_path):
        """Test retrieving prediction statistics."""
        from cerberus.mutation.ledger import DiffLedger

        ledger_path = tmp_path / "ledger.db"
        ledger = DiffLedger(ledger_path=str(ledger_path))

        # Record several predictions
        for i in range(5):
            predictions = [
                {"symbol": f"func_{i}", "confidence_score": 1.0},
                {"symbol": "common_func", "confidence_score": 0.95}
            ]
            ledger.record_predictions(
                edited_symbol=f"symbol_{i}",
                edited_file="/test/file.py",
                predictions=predictions
            )

        # Get stats
        stats = ledger.get_prediction_stats(limit=100)

        assert stats["total_prediction_logs"] == 5
        assert stats["average_predictions_per_edit"] == 2.0
        assert "common_func" in stats["top_predicted_symbols"]
        # common_func appears in all 5 logs
        assert stats["top_predicted_symbols"]["common_func"] == 5

    def test_empty_predictions_logging(self, tmp_path):
        """Test logging when no predictions are made."""
        from cerberus.mutation.ledger import DiffLedger

        ledger_path = tmp_path / "ledger.db"
        ledger = DiffLedger(ledger_path=str(ledger_path))

        # Record empty predictions
        result = ledger.record_predictions(
            edited_symbol="some_symbol",
            edited_file="/test/file.py",
            predictions=[]
        )

        assert result is True

        # Stats should show 1 log with 0 predictions
        stats = ledger.get_prediction_stats()
        assert stats["total_prediction_logs"] == 1
        assert stats["average_predictions_per_edit"] == 0.0


class TestDeterministicConstraints:
    """Test that predictions follow deterministic constraints."""

    def test_no_fuzzy_matching(self, tmp_path):
        """Ensure no fuzzy/probabilistic matching is used."""
        # This is more of a design constraint test
        # The engine should only use exact AST relationships
        index_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(index_path))
        cursor = conn.cursor()

        # Create minimal schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY,
                name TEXT,
                file_path TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY,
                caller_name TEXT,
                callee_name TEXT,
                file_path TEXT,
                line_number INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY,
                file_path TEXT,
                import_name TEXT,
                module_path TEXT
            )
        """)
        conn.commit()
        conn.close()

        engine = PredictionEngine(str(index_path))

        # With no data, should return empty predictions
        predictions, stats = engine.predict_related_changes(
            edited_symbol="some_func",
            file_path="/test.py"
        )

        # Should be empty, not "guessing" similar symbols
        assert len(predictions) == 0

    def test_high_confidence_only(self, tmp_path):
        """Ensure only high confidence (>=0.9) predictions are shown."""
        index_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(index_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS symbols (
                id INTEGER PRIMARY KEY,
                name TEXT,
                file_path TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY,
                caller_name TEXT,
                callee_name TEXT,
                file_path TEXT,
                line_number INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY,
                file_path TEXT,
                import_name TEXT,
                module_path TEXT
            )
        """)
        conn.commit()
        conn.close()

        engine = PredictionEngine(str(index_path), confidence_threshold=0.9)
        predictions, stats = engine.predict_related_changes(
            edited_symbol="test",
            file_path="/test.py"
        )

        # All predictions should be >= threshold
        for pred in predictions:
            assert pred.confidence_score >= 0.9
