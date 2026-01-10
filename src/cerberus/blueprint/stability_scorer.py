"""Composite stability scorer for blueprint overlays.

Phase 13.2: Computes stability score from coverage, complexity, churn, and dependencies.
"""

from typing import Optional, Dict

from cerberus.logging_config import logger
from .schemas import (
    StabilityScore,
    ComplexityMetrics,
    ChurnMetrics,
    CoverageMetrics,
    DependencyInfo
)


class StabilityScorer:
    """Computes composite stability score from multiple metrics."""

    # Weights for composite score (must sum to 1.0)
    WEIGHT_COVERAGE = 0.4      # Well-tested = safer (40%)
    WEIGHT_COMPLEXITY = 0.3    # Simpler = safer (30%)
    WEIGHT_CHURN = 0.2         # Stable = safer (20%)
    WEIGHT_DEPENDENCIES = 0.1  # Fewer deps = safer (10%)

    @staticmethod
    def calculate(
        complexity: Optional[ComplexityMetrics],
        churn: Optional[ChurnMetrics],
        coverage: Optional[CoverageMetrics],
        dependencies: Optional[list] = None
    ) -> Optional[StabilityScore]:
        """
        Calculate composite stability score.

        Formula:
            stability = (coverage * 0.4) +
                       ((1 - complexity) * 0.3) +
                       ((1 - churn_rate) * 0.2) +
                       ((1 - dep_count/10) * 0.1)

        Args:
            complexity: ComplexityMetrics or None
            churn: ChurnMetrics or None
            coverage: CoverageMetrics or None
            dependencies: List of DependencyInfo or None

        Returns:
            StabilityScore or None if insufficient data
        """
        # Need at least 2 metrics to compute meaningful score
        available_metrics = sum([
            complexity is not None,
            churn is not None,
            coverage is not None,
        ])

        if available_metrics < 2:
            logger.debug("Insufficient metrics for stability score")
            return None

        # Normalize each factor to 0.0-1.0 scale
        factors = {}

        # Coverage factor (0-100% -> 0.0-1.0)
        if coverage:
            coverage_factor = coverage.percent / 100.0
            factors['coverage'] = coverage_factor
        else:
            coverage_factor = 0.5  # Neutral if unknown

        # Complexity factor (Low=0.2, Medium=0.5, High=0.9 -> inverted)
        if complexity:
            if complexity.level == "Low":
                complexity_normalized = 0.2
            elif complexity.level == "Medium":
                complexity_normalized = 0.5
            else:  # High
                complexity_normalized = 0.9

            # Invert: simpler code is safer
            complexity_factor = 1.0 - complexity_normalized
            factors['complexity'] = complexity_normalized  # Store original for display
        else:
            complexity_factor = 0.5  # Neutral if unknown

        # Churn factor (0 edits = 0, 10+ edits = 1.0 -> inverted)
        if churn:
            # Normalize edit frequency (cap at 10 edits/week)
            churn_normalized = min(churn.edit_frequency / 10.0, 1.0)
            # Invert: stable code is safer
            churn_factor = 1.0 - churn_normalized
            factors['churn'] = churn.edit_frequency
        else:
            churn_factor = 0.5  # Neutral if unknown

        # Dependency factor (0 deps = 0, 10+ deps = 1.0 -> inverted)
        if dependencies:
            dep_count = len(dependencies)
            dep_normalized = min(dep_count / 10.0, 1.0)
            # Invert: fewer deps is safer
            dep_factor = 1.0 - dep_normalized
            factors['dependencies'] = dep_count
        else:
            dep_factor = 0.7  # Slightly positive if unknown (assume few deps)
            factors['dependencies'] = 0

        # Compute weighted score
        score = (
            coverage_factor * StabilityScorer.WEIGHT_COVERAGE +
            complexity_factor * StabilityScorer.WEIGHT_COMPLEXITY +
            churn_factor * StabilityScorer.WEIGHT_CHURN +
            dep_factor * StabilityScorer.WEIGHT_DEPENDENCIES
        )

        # Clamp to [0.0, 1.0]
        score = max(0.0, min(1.0, score))

        # Determine risk level
        level = StabilityScore.calculate_level(score)

        return StabilityScore(
            score=round(score, 2),
            level=level,
            factors=factors
        )

    @staticmethod
    def explain_score(stability: StabilityScore) -> str:
        """
        Generate human-readable explanation of stability score.

        Args:
            stability: StabilityScore to explain

        Returns:
            Multi-line explanation string
        """
        lines = [
            f"Stability: {stability.level} ({stability.score:.2f})",
            "",
            "Contributing factors:"
        ]

        if 'coverage' in stability.factors:
            cov = stability.factors['coverage']
            lines.append(f"  • Coverage: {cov:.1f}% (weight: 40%)")

        if 'complexity' in stability.factors:
            comp = stability.factors['complexity']
            level_name = "Low" if comp < 0.5 else "Medium" if comp < 0.9 else "High"
            lines.append(f"  • Complexity: {level_name} (weight: 30%)")

        if 'churn' in stability.factors:
            churn = stability.factors['churn']
            lines.append(f"  • Churn: {int(churn)} edits/week (weight: 20%)")

        if 'dependencies' in stability.factors:
            deps = stability.factors['dependencies']
            lines.append(f"  • Dependencies: {int(deps)} calls (weight: 10%)")

        # Add recommendation based on risk level
        lines.append("")
        if stability.level == "🟢 SAFE":
            lines.append("✓ Safe to modify - well-tested and stable")
        elif stability.level == "🟡 MEDIUM":
            lines.append("⚠ Moderate risk - review carefully before changes")
        else:  # HIGH RISK
            lines.append("⛔ High risk - add tests and proceed with caution")

        return "\n".join(lines)
