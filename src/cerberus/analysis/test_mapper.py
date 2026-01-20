"""
Test Coverage Mapping.

Maps implementation code to test coverage, helping AI agents understand
what tests exist for a given symbol and where coverage gaps are.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
import re

from cerberus.resolution.call_graph_builder import CallGraphBuilder


@dataclass
class TestCoverageReport:
    """Test coverage report for a symbol."""

    symbol: str
    file: str
    covered_by: List[str] = field(default_factory=list)
    coverage_percent: float = 0.0
    uncovered_branches: List[str] = field(default_factory=list)
    coverage_quality: str = "unknown"  # excellent, good, fair, poor, none
    safe_to_modify: bool = False
    recommendations: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "file": self.file,
            "covered_by": self.covered_by,
            "coverage_percent": self.coverage_percent,
            "uncovered_branches": self.uncovered_branches,
            "coverage_quality": self.coverage_quality,
            "safe_to_modify": self.safe_to_modify,
            "recommendations": self.recommendations,
            "test_files": self.test_files,
        }


class TestCoverageMapper:
    """
    Maps implementation code to test coverage.

    Analyzes:
    - Which tests exercise a given symbol
    - What branches/paths are covered
    - Coverage quality and gaps
    - Recommendations for improvement
    """

    def __init__(self, store: Any, project_root: Optional[Path] = None):
        """
        Initialize test coverage mapper.

        Args:
            store: SQLite symbol store
            project_root: Optional project root for test discovery
        """
        self.store = store
        self.project_root = project_root or Path.cwd()
        self.call_graph_builder = CallGraphBuilder(store)

    def map_coverage(self, symbol_name: str, file_path: Optional[str] = None) -> TestCoverageReport:
        """
        Map test coverage for a symbol.

        Args:
            symbol_name: Name of symbol to analyze
            file_path: Optional file path to disambiguate

        Returns:
            TestCoverageReport with coverage analysis
        """
        report = TestCoverageReport(symbol=symbol_name, file="")

        # Find symbol location
        location = self.call_graph_builder._get_symbol_location(symbol_name, file_path)
        if not location:
            report.coverage_quality = "unknown"
            report.recommendations.append("Symbol not found in index")
            return report

        file_resolved, start_line, end_line = location
        report.file = file_resolved

        # Find test files that import or reference this symbol
        report.test_files = self._find_test_files(symbol_name, file_resolved)

        # Find specific tests that exercise this symbol
        report.covered_by = self._find_covering_tests(
            symbol_name, file_resolved, report.test_files
        )

        # Check for uncovered branches
        report.uncovered_branches = self._find_uncovered_branches(
            symbol_name, file_resolved, start_line, end_line, report.covered_by
        )

        # Calculate coverage percentage
        report.coverage_percent = self._calculate_coverage_percent(
            len(report.covered_by),
            len(report.uncovered_branches)
        )

        # Determine coverage quality
        report.coverage_quality = self._assess_coverage_quality(
            report.coverage_percent,
            len(report.covered_by)
        )

        # Determine if safe to modify
        report.safe_to_modify = report.coverage_percent >= 70

        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)

        return report

    def _find_test_files(self, symbol_name: str, file_path: str) -> List[str]:
        """Find test files that might test this symbol."""
        test_files = []

        # Convert file path to potential test names
        path_obj = Path(file_path)
        module_name = path_obj.stem

        # Common test file patterns
        test_patterns = [
            f"test_{module_name}.py",
            f"{module_name}_test.py",
            f"test_*{module_name}*.py",
            "test_*.py",  # All test files as fallback
        ]

        # Search for test files
        test_dir = self.project_root / "tests"
        if test_dir.exists():
            for pattern in test_patterns:
                for test_file in test_dir.glob(f"**/{pattern}"):
                    try:
                        content = test_file.read_text()
                        # Check if test file mentions the symbol or imports from the module
                        if symbol_name in content or module_name in content:
                            rel_path = str(test_file.relative_to(self.project_root))
                            if rel_path not in test_files:
                                test_files.append(rel_path)
                    except:
                        continue

        return test_files

    def _find_covering_tests(
        self,
        symbol_name: str,
        file_path: str,
        test_files: List[str]
    ) -> List[str]:
        """Find specific test functions that exercise this symbol."""
        covering_tests = []

        for test_file_rel in test_files:
            test_file = self.project_root / test_file_rel
            if not test_file.exists():
                continue

            try:
                content = test_file.read_text()

                # Find all test functions
                test_funcs = re.findall(r'def (test_\w+)', content)

                for func in test_funcs:
                    # Check if symbol is mentioned in this test function
                    # Look for the function definition and its body
                    func_pattern = f'def {func}.*?(?=\ndef |$)'
                    func_match = re.search(func_pattern, content, re.DOTALL)

                    if func_match:
                        func_body = func_match.group(0)
                        # Check if symbol is called or referenced
                        if symbol_name in func_body:
                            covering_tests.append(f"{test_file_rel}::{func}")
            except:
                continue

        # Also check call graph - are any test functions calling this symbol?
        callers = self.call_graph_builder._get_callers(symbol_name, file_path)
        for caller_name, caller_file, _ in callers:
            if "test" in caller_file.lower() and caller_name.startswith("test_"):
                test_ref = f"{caller_file}::{caller_name}"
                if test_ref not in covering_tests:
                    covering_tests.append(test_ref)

        return covering_tests[:20]  # Limit to top 20

    def _find_uncovered_branches(
        self,
        symbol_name: str,
        file_path: str,
        start_line: int,
        end_line: int,
        covered_by: List[str]
    ) -> List[str]:
        """Find potentially uncovered branches."""
        uncovered = []

        try:
            with open(file_path) as f:
                lines = f.readlines()

            # Extract function body
            if start_line <= len(lines) and end_line <= len(lines):
                body_lines = lines[start_line - 1:end_line]
                body = ''.join(body_lines)

                # Look for conditional branches
                if_count = len(re.findall(r'\bif\b', body))
                elif_count = len(re.findall(r'\belif\b', body))
                else_count = len(re.findall(r'\belse\b', body))
                except_count = len(re.findall(r'\bexcept\b', body))

                total_branches = if_count + elif_count + else_count + except_count

                # If we have branches but few/no tests, flag potential gaps
                if total_branches > 0:
                    tests_per_branch = len(covered_by) / total_branches if total_branches > 0 else 0

                    if tests_per_branch < 0.5:
                        # Find specific uncovered patterns
                        for i, line in enumerate(body_lines, start=start_line):
                            line_stripped = line.strip()
                            if line_stripped.startswith('if ') and 'TODO' not in line:
                                condition = line_stripped[3:].split(':')[0]
                                if 'is None' in condition or 'is not None' in condition:
                                    uncovered.append(f"line {i}: None check - {condition[:50]}")
                            elif line_stripped.startswith('except '):
                                exception = line_stripped[7:].split(':')[0]
                                if covered_by:
                                    # Check if any test name suggests exception testing
                                    if not any('error' in test.lower() or 'exception' in test.lower() for test in covered_by):
                                        uncovered.append(f"line {i}: Exception handler - {exception[:50]}")
                            elif 'raise ' in line_stripped:
                                if not any('error' in test.lower() or 'exception' in test.lower() for test in covered_by):
                                    uncovered.append(f"line {i}: Error path")

        except:
            pass

        return uncovered[:5]  # Limit to top 5

    def _calculate_coverage_percent(self, test_count: int, uncovered_count: int) -> float:
        """Calculate rough coverage percentage."""
        if test_count == 0:
            return 0.0

        # Heuristic: each test covers ~20% of code
        # Uncovered branches reduce coverage
        base_coverage = min(100, test_count * 20)
        penalty = uncovered_count * 10

        coverage = max(0, base_coverage - penalty)
        return round(coverage, 1)

    def _assess_coverage_quality(self, coverage_percent: float, test_count: int) -> str:
        """Assess overall coverage quality."""
        if coverage_percent >= 90 and test_count >= 3:
            return "excellent"
        elif coverage_percent >= 70 and test_count >= 2:
            return "good"
        elif coverage_percent >= 50 and test_count >= 1:
            return "fair"
        elif test_count > 0:
            return "poor"
        else:
            return "none"

    def _generate_recommendations(self, report: TestCoverageReport) -> List[str]:
        """Generate recommendations for improving coverage."""
        recommendations = []

        if report.coverage_quality == "none":
            recommendations.append(
                "⚠️  No test coverage found. Add tests before making changes."
            )
            recommendations.append(
                f"Create test file: tests/test_{Path(report.file).stem}.py"
            )
        elif report.coverage_quality == "poor":
            recommendations.append(
                "⚠️  Insufficient test coverage. Add more comprehensive tests."
            )
        elif report.coverage_quality == "fair":
            recommendations.append(
                "Consider adding edge case tests to improve coverage"
            )

        if report.uncovered_branches:
            recommendations.append(
                f"Add tests for {len(report.uncovered_branches)} uncovered branch(es):"
            )
            for branch in report.uncovered_branches[:3]:
                recommendations.append(f"  - {branch}")

        if report.coverage_quality in ("good", "excellent"):
            recommendations.append(
                "✓ Good test coverage - safe to refactor"
            )

        if not report.covered_by and report.test_files:
            recommendations.append(
                f"Test files found ({len(report.test_files)}) but no direct tests. "
                "Consider adding explicit tests for this symbol."
            )

        return recommendations


def map_test_coverage(
    store: Any,
    symbol_name: str,
    file_path: Optional[str] = None,
    project_root: Optional[Path] = None
) -> TestCoverageReport:
    """
    Convenience function to map test coverage.

    Args:
        store: SQLite symbol store
        symbol_name: Name of symbol to analyze
        file_path: Optional file path to disambiguate
        project_root: Optional project root for test discovery

    Returns:
        TestCoverageReport object
    """
    mapper = TestCoverageMapper(store, project_root)
    return mapper.map_coverage(symbol_name, file_path)
