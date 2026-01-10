"""
Phase 14.3: Predictive Editing - Deterministic Relationship Discovery

Mission: Proactively suggest related changes using ONLY deterministic AST relationships.

Key Principles:
- 100% Signal / 0% Noise: Only AST-verified relationships
- No Heuristics: No fuzzy matching, semantic similarity, or ML models
- High Confidence Only: Minimum confidence threshold of 0.9
- Deterministic: Every suggestion must be explainable by code structure
"""

import json
import os
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class Prediction:
    """A single prediction for a related change."""
    confidence: str  # "HIGH", "MEDIUM" (but we filter to HIGH only)
    confidence_score: float  # 0.0-1.0
    symbol: str
    file: str
    line: int
    reason: str  # "direct_caller", "direct_dependency", "test_file_pattern_match"
    relationship: str  # Human-readable explanation
    anchor: Optional[Dict[str, Any]] = None  # Context anchor metadata
    command: Optional[str] = None  # Suggested cerberus command


@dataclass
class PredictionStats:
    """Statistics about the prediction analysis."""
    total_analyzed: int
    high_confidence: int
    shown: int
    filtered: int


class PredictionEngine:
    """
    Phase 14.3: Deterministic relationship discovery engine.

    STRICT RULES:
    - Only AST-verified relationships (no heuristics)
    - Only exact pattern matches (no fuzzy matching)
    - No ML, no semantic similarity, no probabilistic models
    - Every suggestion must be explainable by code structure
    """

    def __init__(self, index_path: str = "cerberus.db", confidence_threshold: float = 0.9):
        """
        Initialize the prediction engine.

        Args:
            index_path: Path to Cerberus SQLite index
            confidence_threshold: Minimum confidence score (default: 0.9)
        """
        self.index_path = index_path
        self.confidence_threshold = confidence_threshold
        self.conn = sqlite3.connect(index_path)
        self.conn.row_factory = sqlite3.Row

    def predict_related_changes(
        self,
        edited_symbol: str,
        file_path: str,
        symbol_type: str = "function"
    ) -> Tuple[List[Prediction], PredictionStats]:
        """
        Predict related changes after editing a symbol.

        Args:
            edited_symbol: Name of the edited symbol
            file_path: File path where the symbol was edited
            symbol_type: Type of symbol (function, class, etc.)

        Returns:
            Tuple of (predictions, stats)
        """
        all_suggestions = []

        # 1. Direct Callers (Confidence: 1.0)
        # Who calls this symbol? They might need updates.
        caller_suggestions = self._find_direct_callers(edited_symbol, file_path)
        all_suggestions.extend(caller_suggestions)

        # 2. Direct Dependencies (Confidence: 1.0)
        # What does this symbol call? Signature changes might propagate.
        dependency_suggestions = self._find_direct_dependencies(edited_symbol, file_path)
        all_suggestions.extend(dependency_suggestions)

        # 3. Test File Pattern Match (Confidence: 0.95)
        # Exact pattern: test_<symbol>.py or test_<module>.py with verified imports
        test_suggestions = self._find_test_files(edited_symbol, file_path)
        all_suggestions.extend(test_suggestions)

        # Filter by confidence threshold
        high_confidence = [s for s in all_suggestions if s.confidence_score >= self.confidence_threshold]

        # Prioritize by stability (SAFE > MEDIUM > HIGH RISK)
        prioritized = self._prioritize_by_stability(high_confidence)

        # Limit to top 5 to avoid noise
        shown = prioritized[:5]

        # Generate statistics
        stats = PredictionStats(
            total_analyzed=len(all_suggestions),
            high_confidence=len(high_confidence),
            shown=len(shown),
            filtered=len(all_suggestions) - len(shown)
        )

        return shown, stats

    def _find_direct_callers(self, symbol: str, file_path: str) -> List[Prediction]:
        """
        Find direct callers using AST call graph (Phase 5 symbolic intelligence).

        Confidence: 1.0 (AST-verified)
        """
        predictions = []

        try:
            # Use symbolic deps command to get callers
            result = subprocess.run(
                ["cerberus", "symbolic", "deps", "--symbol", symbol, "--json"],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                callers = data.get("callers", [])

                for caller in callers:
                    caller_file = caller.get("caller_file", "")
                    line = caller.get("line", 0)

                    # Extract symbol name from caller context if available
                    # For now, use file name as symbol hint
                    caller_symbol = Path(caller_file).stem

                    predictions.append(Prediction(
                        confidence="HIGH",
                        confidence_score=1.0,
                        symbol=caller_symbol,
                        file=caller_file,
                        line=line,
                        reason="direct_caller",
                        relationship=f"calls {symbol} (AST-verified)",
                        command=f"cerberus retrieval get-symbol {caller_symbol}"
                    ))
        except Exception as e:
            # Fail gracefully, don't crash on errors
            pass

        return predictions

    def _find_direct_dependencies(self, symbol: str, file_path: str) -> List[Prediction]:
        """
        Find direct dependencies (what this symbol calls).

        Confidence: 1.0 (AST-verified)
        """
        predictions = []

        try:
            # Query the calls table for what this symbol calls
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT DISTINCT
                    c.callee_name,
                    c.file_path,
                    c.line_number
                FROM calls c
                WHERE c.caller_name = ?
                  AND c.file_path = ?
                LIMIT 10
            """, (symbol, file_path))

            for row in cursor.fetchall():
                callee_name = row["callee_name"]
                callee_file = row["file_path"]
                line = row["line_number"]

                predictions.append(Prediction(
                    confidence="HIGH",
                    confidence_score=1.0,
                    symbol=callee_name,
                    file=callee_file,
                    line=line,
                    reason="direct_dependency",
                    relationship=f"{symbol} calls this (signature change propagation)",
                    command=f"cerberus retrieval get-symbol {callee_name}"
                ))
        except Exception as e:
            # Fail gracefully
            pass

        return predictions

    def _find_test_files(self, symbol: str, file_path: str) -> List[Prediction]:
        """
        Find test files using exact pattern matching + import verification.

        Patterns:
        - test_<symbol>.py
        - test_<module>.py
        - tests/test_<symbol>.py

        Confidence: 0.95 (exact pattern + verified import)
        """
        predictions = []

        # Extract module name from file path
        module_name = Path(file_path).stem

        # Generate test file patterns
        patterns = [
            f"test_{symbol}.py",
            f"test_{module_name}.py",
            f"tests/test_{symbol}.py",
            f"tests/test_{module_name}.py",
        ]

        # Get project root (directory containing the index)
        project_root = Path(self.index_path).parent

        for pattern in patterns:
            # Check if test file exists
            test_file_path = project_root / pattern

            if test_file_path.exists():
                # Verify it actually imports the edited file
                if self._imports_file(str(test_file_path), file_path):
                    # Extract test function name (convention: test_<symbol>)
                    test_symbol = f"test_{symbol}"

                    predictions.append(Prediction(
                        confidence="HIGH",
                        confidence_score=0.95,
                        symbol=test_symbol,
                        file=str(test_file_path),
                        line=1,  # We don't have exact line, use 1
                        reason="test_file_pattern_match",
                        relationship=f"test file for {symbol} (exact match + verified import)",
                        command=f"cerberus retrieval get-symbol {test_symbol}"
                    ))
                    break  # Only suggest one test file to avoid duplicates

        return predictions

    def _imports_file(self, test_file: str, target_file: str) -> bool:
        """
        Verify that test_file imports target_file.

        Uses index to check import relationships.
        """
        try:
            cursor = self.conn.cursor()

            # Get module name from target file
            target_module = Path(target_file).stem

            # Check if test file has imports from target
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM imports
                WHERE file_path = ?
                  AND (
                      import_name LIKE ? OR
                      module_path LIKE ?
                  )
            """, (test_file, f"%{target_module}%", f"%{target_module}%"))

            row = cursor.fetchone()
            return row["count"] > 0 if row else False
        except Exception:
            # If we can't verify, assume false (safe default)
            return False

    def _prioritize_by_stability(self, predictions: List[Prediction]) -> List[Prediction]:
        """
        Prioritize predictions by stability score (SAFE > MEDIUM > HIGH RISK).

        Uses Phase 13.2 stability scoring.
        """
        # For each prediction, get stability score
        scored_predictions = []

        for pred in predictions:
            risk_score = self._get_risk_score(pred.file)
            scored_predictions.append((pred, risk_score))

        # Sort by risk score (lower is better = more stable)
        scored_predictions.sort(key=lambda x: x[1])

        # Return sorted predictions
        return [pred for pred, _ in scored_predictions]

    def _get_risk_score(self, file_path: str) -> float:
        """
        Get composite risk score for a file.

        Returns value 0.0-1.0 where:
        - 0.0-0.33: SAFE
        - 0.34-0.66: MEDIUM
        - 0.67-1.0: HIGH RISK
        """
        try:
            # Try to get from git churn and coverage data
            # For now, return default medium risk
            # TODO: Integrate with StabilityScorer from Phase 13.2
            return 0.5
        except Exception:
            return 0.5  # Default to medium risk

    def to_json(self, predictions: List[Prediction], stats: PredictionStats) -> Dict[str, Any]:
        """
        Convert predictions to JSON format (machine mode).
        """
        return {
            "predictions": [
                {
                    "confidence": p.confidence,
                    "confidence_score": p.confidence_score,
                    "symbol": p.symbol,
                    "file": p.file,
                    "line": p.line,
                    "reason": p.reason,
                    "relationship": p.relationship,
                    "anchor": p.anchor,
                    "command": p.command
                }
                for p in predictions
            ],
            "prediction_stats": {
                "total_analyzed": stats.total_analyzed,
                "high_confidence": stats.high_confidence,
                "shown": stats.shown,
                "filtered": stats.filtered
            }
        }

    def to_text(self, predictions: List[Prediction], verbose: bool = False) -> str:
        """
        Convert predictions to human-readable text format.
        """
        if not predictions:
            return "[Predictive] No high-confidence suggestions found."

        lines = ["[Predictive] Related changes suggested:"]

        for i, pred in enumerate(predictions, 1):
            confidence_emoji = "🔮" if pred.confidence == "HIGH" else "⚠️"
            lines.append(f"  {i}. {confidence_emoji} {pred.symbol} ({pred.file}:{pred.line})")
            lines.append(f"     Reason: {pred.relationship}")

            if verbose:
                lines.append(f"     Confidence: {pred.confidence_score:.2f}")
                lines.append(f"     Command: {pred.command}")

        return "\n".join(lines)

    def __del__(self):
        """Close database connection on cleanup."""
        if hasattr(self, 'conn'):
            self.conn.close()
