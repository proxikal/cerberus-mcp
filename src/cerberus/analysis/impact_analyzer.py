"""
Change Impact Analysis.

Analyzes what would be affected if you modify a symbol.
Helps AI agents make safe refactoring decisions.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
import re

from cerberus.resolution.call_graph_builder import CallGraphBuilder


@dataclass
class ImpactAnalysis:
    """Results of change impact analysis."""

    symbol: str
    file: str
    direct_callers: int = 0
    transitive_callers: int = 0
    affected_tests: List[str] = field(default_factory=list)
    risk_score: str = "low"  # low, medium, high, critical
    breaking_changes: List[str] = field(default_factory=list)
    safe_to_modify: bool = True
    recommendations: List[str] = field(default_factory=list)
    caller_details: List[Dict[str, Any]] = field(default_factory=list)
    test_coverage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "file": self.file,
            "direct_callers": self.direct_callers,
            "transitive_callers": self.transitive_callers,
            "affected_tests": self.affected_tests,
            "risk_score": self.risk_score,
            "breaking_changes": self.breaking_changes,
            "safe_to_modify": self.safe_to_modify,
            "recommendations": self.recommendations,
            "caller_details": self.caller_details,
            "test_coverage": self.test_coverage,
        }


class ImpactAnalyzer:
    """
    Analyzes the impact of changing a symbol.

    Uses call graph analysis + test mapping to determine:
    - What code would be affected
    - What tests would need updating
    - How risky the change is
    - Recommendations for safe modification
    """

    def __init__(self, store: Any, project_root: Optional[Path] = None):
        """
        Initialize impact analyzer.

        Args:
            store: SQLite symbol store
            project_root: Optional project root for test discovery
        """
        self.store = store
        self.project_root = project_root or Path.cwd()
        self.call_graph_builder = CallGraphBuilder(store)

    def analyze_impact(self, symbol_name: str, file_path: Optional[str] = None) -> ImpactAnalysis:
        """
        Analyze impact of modifying a symbol.

        Args:
            symbol_name: Name of symbol to analyze
            file_path: Optional file path to disambiguate

        Returns:
            ImpactAnalysis with complete impact assessment
        """
        result = ImpactAnalysis(symbol=symbol_name, file="")

        # Find symbol location
        location = self.call_graph_builder._get_symbol_location(symbol_name, file_path)
        if not location:
            result.safe_to_modify = False
            result.risk_score = "unknown"
            result.breaking_changes.append("Symbol not found in index")
            return result

        file_resolved, _, _ = location
        result.file = file_resolved

        # Get direct callers
        direct_callers = self.call_graph_builder._get_callers(symbol_name, file_resolved)
        result.direct_callers = len(direct_callers)
        result.caller_details = [
            {"name": name, "file": fpath, "line": line}
            for name, fpath, line in direct_callers
        ]

        # Get transitive callers (up to 2 levels)
        transitive = self._get_transitive_callers(symbol_name, file_resolved, max_depth=2)
        result.transitive_callers = len(transitive)

        # Find affected tests
        result.affected_tests = self._find_affected_tests(symbol_name, file_resolved, direct_callers)
        result.test_coverage = self._calculate_test_coverage(result.direct_callers, result.affected_tests)

        # Calculate risk score
        result.risk_score = self._calculate_risk_score(
            result.direct_callers,
            result.transitive_callers,
            result.test_coverage
        )

        # Determine if safe to modify
        result.safe_to_modify = self._is_safe_to_modify(result)

        # Generate breaking change warnings
        result.breaking_changes = self._identify_breaking_changes(result)

        # Generate recommendations
        result.recommendations = self._generate_recommendations(result)

        return result

    def _get_transitive_callers(self, symbol_name: str, file_path: str, max_depth: int = 2) -> Set[str]:
        """Get all transitive callers up to max_depth."""
        visited = set()
        to_visit = [(symbol_name, file_path, 0)]
        transitive = set()

        while to_visit:
            current_symbol, current_file, depth = to_visit.pop(0)

            if depth >= max_depth:
                continue

            key = f"{current_file}::{current_symbol}"
            if key in visited:
                continue
            visited.add(key)

            # Get callers of current symbol
            callers = self.call_graph_builder._get_callers(current_symbol, current_file)

            for caller_name, caller_file, _ in callers:
                caller_key = f"{caller_file}::{caller_name}"
                if caller_key not in visited:
                    transitive.add(caller_key)
                    to_visit.append((caller_name, caller_file, depth + 1))

        return transitive

    def _find_affected_tests(
        self,
        symbol_name: str,
        file_path: str,
        direct_callers: List[tuple]
    ) -> List[str]:
        """Find test files that would be affected by changes."""
        affected_tests = []

        # Convert file path to potential test names
        path_obj = Path(file_path)
        module_name = path_obj.stem

        # Common test file patterns
        test_patterns = [
            f"test_{module_name}.py",
            f"{module_name}_test.py",
            f"test_{symbol_name.lower()}.py",
        ]

        # Search for test files
        test_dir = self.project_root / "tests"
        if test_dir.exists():
            for pattern in test_patterns:
                for test_file in test_dir.glob(f"**/{pattern}"):
                    # Check if test file mentions the symbol
                    try:
                        content = test_file.read_text()
                        if symbol_name in content:
                            rel_path = test_file.relative_to(self.project_root)
                            # Find test functions that use this symbol
                            test_funcs = re.findall(r'def (test_\w+)', content)
                            for func in test_funcs:
                                # Check if symbol is mentioned near this test
                                func_match = re.search(f'def {func}.*?(?=def |$)', content, re.DOTALL)
                                if func_match and symbol_name in func_match.group(0):
                                    affected_tests.append(f"{rel_path}::{func}")
                    except:
                        continue

        # Also check if any direct callers are test functions
        for caller_name, caller_file, _ in direct_callers:
            if "test" in caller_file.lower() and caller_name.startswith("test_"):
                affected_tests.append(f"{caller_file}::{caller_name}")

        return list(set(affected_tests))[:10]  # Limit to top 10

    def _calculate_test_coverage(self, direct_callers: int, affected_tests: List[str]) -> float:
        """Calculate rough test coverage score."""
        if direct_callers == 0:
            return 1.0  # No callers = no risk

        if not affected_tests:
            return 0.0  # No tests = 0 coverage

        # Rough heuristic: at least 1 test per 3 callers is good
        ideal_tests = max(1, direct_callers // 3)
        coverage = min(1.0, len(affected_tests) / ideal_tests)
        return round(coverage, 2)

    def _calculate_risk_score(
        self,
        direct_callers: int,
        transitive_callers: int,
        test_coverage: float
    ) -> str:
        """Calculate risk score based on usage and testing."""
        # Risk factors
        usage_risk = direct_callers + (transitive_callers * 0.3)

        # Risk score thresholds
        if usage_risk == 0:
            return "low"
        elif usage_risk < 5:
            if test_coverage >= 0.7:
                return "low"
            elif test_coverage >= 0.4:
                return "medium"
            else:
                return "high"
        elif usage_risk < 15:
            if test_coverage >= 0.8:
                return "medium"
            elif test_coverage >= 0.5:
                return "high"
            else:
                return "critical"
        else:
            # Heavy usage
            if test_coverage >= 0.8:
                return "high"
            else:
                return "critical"

    def _is_safe_to_modify(self, result: ImpactAnalysis) -> bool:
        """Determine if symbol is safe to modify."""
        # Safe if:
        # - Low risk OR
        # - Medium risk with good test coverage OR
        # - High risk with excellent test coverage
        if result.risk_score == "low":
            return True
        elif result.risk_score == "medium" and result.test_coverage >= 0.7:
            return True
        elif result.risk_score == "high" and result.test_coverage >= 0.9:
            return True
        else:
            return False

    def _identify_breaking_changes(self, result: ImpactAnalysis) -> List[str]:
        """Identify potential breaking changes."""
        breaking = []

        if result.direct_callers > 0:
            breaking.append(
                f"Signature change would break {result.direct_callers} direct caller(s)"
            )

        if result.transitive_callers > 10:
            breaking.append(
                f"Ripple effects would impact {result.transitive_callers} indirect callers"
            )

        if result.test_coverage < 0.5 and result.direct_callers > 0:
            breaking.append(
                f"Low test coverage ({result.test_coverage:.0%}) increases risk of undetected breaks"
            )

        if not result.affected_tests and result.direct_callers > 5:
            breaking.append(
                "No tests found despite heavy usage - changes are risky"
            )

        return breaking

    def _generate_recommendations(self, result: ImpactAnalysis) -> List[str]:
        """Generate recommendations for safe modification."""
        recommendations = []

        if result.risk_score in ("high", "critical"):
            recommendations.append(
                "⚠️  High-risk change. Consider deprecation path for signature changes"
            )

        if result.affected_tests:
            recommendations.append(
                f"✓ Update tests: {', '.join(result.affected_tests[:3])}"
                + (f" and {len(result.affected_tests) - 3} more" if len(result.affected_tests) > 3 else "")
            )
        elif result.direct_callers > 0:
            recommendations.append(
                "⚠️  Add tests before modifying - no test coverage detected"
            )

        if result.direct_callers > 10:
            recommendations.append(
                "Consider adding deprecation warning before breaking changes"
            )

        if result.test_coverage < 0.5 and result.direct_callers > 0:
            recommendations.append(
                f"Improve test coverage (currently {result.test_coverage:.0%}) before major changes"
            )

        if not recommendations:
            recommendations.append(
                "✓ Safe to modify - low usage and good test coverage"
            )

        return recommendations


def analyze_change_impact(
    store: Any,
    symbol_name: str,
    file_path: Optional[str] = None,
    project_root: Optional[Path] = None
) -> ImpactAnalysis:
    """
    Convenience function to analyze change impact.

    Args:
        store: SQLite symbol store
        symbol_name: Name of symbol to analyze
        file_path: Optional file path to disambiguate
        project_root: Optional project root for test discovery

    Returns:
        ImpactAnalysis object
    """
    analyzer = ImpactAnalyzer(store, project_root)
    return analyzer.analyze_impact(symbol_name, file_path)
