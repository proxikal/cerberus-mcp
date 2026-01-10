"""Test coverage analyzer for blueprint overlays.

Phase 13.2: Integrates with pytest/coverage.py to extract coverage metrics.
"""

import json
from pathlib import Path
from typing import Optional, Dict, List, Set
import glob

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol
from .schemas import CoverageMetrics


class CoverageAnalyzer:
    """Analyzes test coverage data from coverage.py JSON reports."""

    def __init__(self, coverage_file: Optional[Path] = None):
        """
        Initialize coverage analyzer.

        Args:
            coverage_file: Path to coverage.json file (auto-detected if None)
        """
        self.coverage_data: Optional[Dict] = None
        self.coverage_file = coverage_file or self._find_coverage_file()

        if self.coverage_file and self.coverage_file.exists():
            self._load_coverage_data()
        else:
            logger.info("No coverage data found - coverage analysis unavailable")

    def _find_coverage_file(self) -> Optional[Path]:
        """
        Find coverage.json file in common locations.

        Returns:
            Path to coverage.json or None if not found
        """
        # Common locations for coverage.json
        search_paths = [
            Path("coverage.json"),
            Path(".coverage.json"),
            Path("htmlcov/coverage.json"),
            Path("coverage/coverage.json"),
        ]

        for path in search_paths:
            if path.exists():
                logger.debug(f"Found coverage file: {path}")
                return path

        return None

    def _load_coverage_data(self) -> None:
        """Load coverage data from JSON file."""
        try:
            with open(self.coverage_file, 'r') as f:
                data = json.load(f)
                self.coverage_data = data.get('files', {})
                logger.debug(f"Loaded coverage data for {len(self.coverage_data)} files")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load coverage data from {self.coverage_file}: {e}")
            self.coverage_data = None

    def analyze(self, symbol: CodeSymbol) -> Optional[CoverageMetrics]:
        """
        Analyze coverage for a symbol.

        Args:
            symbol: CodeSymbol to analyze

        Returns:
            CoverageMetrics or None if coverage data unavailable
        """
        if not self.coverage_data:
            return None

        file_path = symbol.file_path

        # Try to find matching file in coverage data (handle relative vs absolute paths)
        file_coverage = self._find_file_coverage(file_path)
        if not file_coverage:
            return None

        # Extract line coverage for symbol's range
        executed_lines = set(file_coverage.get('executed_lines', []))
        missing_lines = set(file_coverage.get('missing_lines', []))

        # Calculate coverage for this symbol's line range
        symbol_lines = set(range(symbol.start_line, symbol.end_line + 1))

        # Filter to only executable lines (in coverage data)
        all_tracked_lines = executed_lines | missing_lines
        symbol_tracked_lines = symbol_lines & all_tracked_lines

        if not symbol_tracked_lines:
            # No executable lines in this symbol
            return CoverageMetrics(
                percent=100.0,  # Assume 100% if no executable lines
                covered_lines=0,
                total_lines=0,
                test_files=[],
                assertion_count=0
            )

        # Calculate coverage percentage
        symbol_covered = symbol_tracked_lines & executed_lines
        coverage_percent = (len(symbol_covered) / len(symbol_tracked_lines)) * 100.0

        # Find test files (heuristic: search for test_*.py files that might test this)
        test_files = self._find_test_files(symbol)

        return CoverageMetrics(
            percent=round(coverage_percent, 1),
            covered_lines=len(symbol_covered),
            total_lines=len(symbol_tracked_lines),
            test_files=test_files,
            assertion_count=0  # TODO: Parse test files to count assertions
        )

    def _find_file_coverage(self, file_path: str) -> Optional[Dict]:
        """
        Find coverage data for a file, handling path variations.

        Args:
            file_path: Absolute or relative file path

        Returns:
            Coverage data dict or None
        """
        if not self.coverage_data:
            return None

        # Try exact match first
        if file_path in self.coverage_data:
            return self.coverage_data[file_path]

        # Try converting to Path and matching on name/suffix
        target_path = Path(file_path)

        for cov_file, cov_data in self.coverage_data.items():
            cov_path = Path(cov_file)

            # Match on absolute path resolution
            try:
                if target_path.resolve() == cov_path.resolve():
                    return cov_data
            except (OSError, RuntimeError):
                pass

            # Match on relative path from project root
            if target_path.name == cov_path.name:
                # Same filename - check if paths end the same way
                target_parts = target_path.parts
                cov_parts = cov_path.parts

                # Compare last N parts
                match_len = min(len(target_parts), len(cov_parts), 3)
                if target_parts[-match_len:] == cov_parts[-match_len:]:
                    return cov_data

        return None

    def _find_test_files(self, symbol: CodeSymbol) -> List[str]:
        """
        Find test files that might test this symbol (heuristic).

        Args:
            symbol: CodeSymbol being analyzed

        Returns:
            List of test file paths
        """
        test_files = []

        # Get the source file name
        source_file = Path(symbol.file_path)
        module_name = source_file.stem

        # Common test file naming patterns
        patterns = [
            f"test_{module_name}.py",
            f"{module_name}_test.py",
            f"test_{module_name}_*.py",
            f"*_test_{module_name}.py",
        ]

        # Search in common test directories
        search_dirs = [
            Path("tests"),
            Path("test"),
            source_file.parent / "tests",
            source_file.parent / "test",
        ]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for pattern in patterns:
                matches = search_dir.glob(pattern)
                for match in matches:
                    if match.is_file():
                        test_files.append(str(match))

        return test_files

    def has_coverage_data(self) -> bool:
        """Check if coverage data is available."""
        return self.coverage_data is not None

    @staticmethod
    def generate_coverage_instructions() -> str:
        """
        Return instructions for generating coverage data.

        Returns:
            Help text for users
        """
        return """
To enable coverage analysis, run:

    pytest --cov=src --cov-report=json

This generates coverage.json which Cerberus will auto-detect.
"""
