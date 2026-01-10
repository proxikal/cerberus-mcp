"""Blueprint system for architectural intelligence.

Phase 13.1: Foundation - ASCII trees, dependencies, complexity metrics, caching.
Phase 13.2: Intelligence layer - git churn, test coverage, stability scoring.
"""

from .schemas import (
    Blueprint,
    BlueprintNode,
    BlueprintRequest,
    ComplexityMetrics,
    DependencyInfo,
    SymbolOverlay,
    TreeRenderOptions,
    ChurnMetrics,
    CoverageMetrics,
    StabilityScore,
)
from .tree_builder import TreeBuilder
from .formatter import BlueprintFormatter
from .facade import BlueprintGenerator
from .cache_manager import BlueprintCache
from .dependency_overlay import DependencyOverlay
from .complexity_analyzer import ComplexityAnalyzer
from .churn_analyzer import ChurnAnalyzer
from .coverage_analyzer import CoverageAnalyzer
from .stability_scorer import StabilityScorer

__all__ = [
    "Blueprint",
    "BlueprintNode",
    "BlueprintRequest",
    "ComplexityMetrics",
    "DependencyInfo",
    "SymbolOverlay",
    "TreeRenderOptions",
    "ChurnMetrics",
    "CoverageMetrics",
    "StabilityScore",
    "TreeBuilder",
    "BlueprintFormatter",
    "BlueprintGenerator",
    "BlueprintCache",
    "DependencyOverlay",
    "ComplexityAnalyzer",
    "ChurnAnalyzer",
    "CoverageAnalyzer",
    "StabilityScorer",
]
