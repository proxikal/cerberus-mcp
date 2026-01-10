"""Data models for blueprint system.

Phase 13.1: Foundation - Data structures for tree generation, dependencies, and complexity.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class ComplexityMetrics(BaseModel):
    """Complexity analysis for a code symbol."""

    lines: int = Field(description="Total lines of code (end_line - start_line)")
    complexity: int = Field(description="Cyclomatic complexity score")
    branches: int = Field(description="Number of branching statements (if/for/while/try)")
    nesting: int = Field(description="Maximum nesting depth")
    level: Literal["Low", "Medium", "High"] = Field(
        description="Complexity classification"
    )

    @classmethod
    def calculate_level(cls, complexity: int, lines: int) -> Literal["Low", "Medium", "High"]:
        """
        Calculate complexity level based on metrics.

        Thresholds:
        - Low: complexity < 10 and lines < 50
        - Medium: 10 <= complexity < 20 or 50 <= lines < 150
        - High: complexity >= 20 or lines >= 150
        """
        if complexity >= 20 or lines >= 150:
            return "High"
        elif complexity >= 10 or lines >= 50:
            return "Medium"
        else:
            return "Low"


class DependencyInfo(BaseModel):
    """Dependency information for a symbol."""

    target: str = Field(description="Target symbol name (e.g., 'stripe.charge')")
    target_file: Optional[str] = Field(None, description="File containing target symbol")
    confidence: float = Field(
        description="Confidence score (0.0-1.0) from Phase 5 resolution"
    )
    resolution_method: Optional[str] = Field(
        None, description="How dependency was resolved (import_trace, type_annotation, etc.)"
    )
    reference_type: Optional[str] = Field(
        None, description="Type of reference (method_call, instance_of, etc.)"
    )
    # Phase 13.5: Dependency classification
    dependency_type: Optional[Literal["internal", "external", "stdlib"]] = Field(
        None, description="Classification: internal (project code), external (third-party), or stdlib"
    )


class ChurnMetrics(BaseModel):
    """Git churn analysis for a symbol (Phase 13.2)."""

    last_modified: Optional[str] = Field(None, description="Human-readable last modification time (e.g., '2h ago')")
    last_modified_timestamp: Optional[float] = Field(None, description="Unix timestamp of last modification")
    edit_frequency: int = Field(0, description="Number of edits in the last 7 days")
    unique_authors: int = Field(0, description="Number of unique contributors")
    last_author: Optional[str] = Field(None, description="Most recent author username")


class CoverageMetrics(BaseModel):
    """Test coverage information for a symbol (Phase 13.2)."""

    percent: float = Field(0.0, description="Coverage percentage (0-100)")
    covered_lines: int = Field(0, description="Number of covered lines")
    total_lines: int = Field(0, description="Total executable lines")
    test_files: List[str] = Field(default_factory=list, description="Test files covering this symbol")
    assertion_count: int = Field(0, description="Number of assertions in tests")


class StabilityScore(BaseModel):
    """Composite stability score for risk assessment (Phase 13.2)."""

    score: float = Field(description="Composite stability score (0.0-1.0, higher is safer)")
    level: Literal["🟢 SAFE", "🟡 MEDIUM", "🔴 HIGH RISK"] = Field(
        description="Risk level classification"
    )
    factors: Dict[str, float] = Field(
        default_factory=dict,
        description="Contributing factors (coverage, complexity, churn, deps)"
    )

    @classmethod
    def calculate_level(cls, score: float) -> Literal["🟢 SAFE", "🟡 MEDIUM", "🔴 HIGH RISK"]:
        """
        Determine risk level from score.

        Thresholds:
        - SAFE: > 0.75
        - MEDIUM: 0.50-0.75
        - HIGH RISK: < 0.50
        """
        if score > 0.75:
            return "🟢 SAFE"
        elif score >= 0.50:
            return "🟡 MEDIUM"
        else:
            return "🔴 HIGH RISK"


class SymbolOverlay(BaseModel):
    """Overlays (metadata) attached to a symbol in blueprint."""

    dependencies: Optional[List[DependencyInfo]] = Field(
        None, description="Dependencies (calls) with confidence scores"
    )
    complexity: Optional[ComplexityMetrics] = Field(
        None, description="Complexity metrics"
    )
    # Phase 13.2 fields:
    churn: Optional[ChurnMetrics] = Field(None, description="Git churn analysis")
    coverage: Optional[CoverageMetrics] = Field(None, description="Test coverage metrics")
    stability: Optional[StabilityScore] = Field(None, description="Composite stability score")
    # Phase 13.3 fields:
    in_cycle: Optional[bool] = Field(None, description="Whether symbol is part of a circular dependency")
    cycle_info: Optional[str] = Field(None, description="Description of cycle (if in_cycle is True)")


class HydratedFile(BaseModel):
    """Information about an auto-hydrated file (Phase 13.5)."""

    file_path: str = Field(description="Path to hydrated file")
    reference_count: int = Field(description="Number of references from main file")
    blueprint: "Blueprint" = Field(description="Mini-blueprint of hydrated file")


class BlueprintNode(BaseModel):
    """A node in the blueprint tree (represents a symbol)."""

    name: str = Field(description="Symbol name")
    type: Literal["function", "class", "method", "variable", "interface", "enum", "struct", "file"] = Field(
        description="Symbol type"
    )
    file_path: Optional[str] = Field(None, description="File path (for file nodes in aggregation)")
    signature: Optional[str] = Field(None, description="Full signature")
    start_line: int = Field(description="Starting line number")
    end_line: int = Field(description="Ending line number")
    parent_class: Optional[str] = Field(
        None, description="Parent class name (for methods)"
    )

    # Overlays
    overlay: SymbolOverlay = Field(
        default_factory=SymbolOverlay,
        description="Metadata overlays (deps, complexity, etc.)"
    )

    # Nested structure
    children: List["BlueprintNode"] = Field(
        default_factory=list,
        description="Child symbols (e.g., methods within a class)"
    )

    @property
    def line_range(self) -> str:
        """Format line range as string."""
        return f"Lines {self.start_line}-{self.end_line}"


class Blueprint(BaseModel):
    """Complete blueprint for a file."""

    file_path: str = Field(description="Absolute file path")
    nodes: List[BlueprintNode] = Field(
        default_factory=list,
        description="Top-level symbol nodes"
    )
    total_symbols: int = Field(description="Total symbol count (including nested)")

    # Metadata
    cached: bool = Field(False, description="Whether this blueprint was served from cache")
    generated_at: Optional[float] = Field(None, description="Timestamp of generation")

    # Phase 13.5: Auto-hydration
    hydrated_files: List[HydratedFile] = Field(
        default_factory=list,
        description="Auto-hydrated dependencies (Phase 13.5)"
    )

    def count_symbols(self) -> int:
        """Recursively count all symbols including nested ones."""
        count = len(self.nodes)
        for node in self.nodes:
            count += self._count_children(node)
        return count

    def _count_children(self, node: BlueprintNode) -> int:
        """Helper to count nested children."""
        count = len(node.children)
        for child in node.children:
            count += self._count_children(child)
        return count


class TreeRenderOptions(BaseModel):
    """Options for rendering ASCII tree."""

    max_depth: Optional[int] = Field(None, description="Maximum tree depth")
    show_line_numbers: bool = Field(True, description="Show line ranges")
    show_signatures: bool = Field(True, description="Show function signatures")
    indent_size: int = Field(4, description="Spaces per indentation level")
    collapse_private: bool = Field(False, description="Collapse private symbols (Phase 13.5)")
    max_width: Optional[int] = Field(None, description="Maximum line width before truncation (Phase 13.5)")
    truncate_threshold: int = Field(5, description="Show first N items before truncating (Phase 13.5)")


class BlueprintRequest(BaseModel):
    """Request parameters for blueprint generation."""

    file_path: str
    show_deps: bool = Field(False, description="Include dependency overlay")
    show_meta: bool = Field(False, description="Include complexity metrics")
    use_cache: bool = Field(True, description="Allow cache usage")
    fast_mode: bool = Field(False, description="Skip expensive analysis")
    output_format: Literal["tree", "json"] = Field("json", description="Output format")

    # Phase 13.2 flags:
    show_churn: bool = Field(False, description="Include git churn analysis")
    show_coverage: bool = Field(False, description="Include test coverage metrics")
    show_stability: bool = Field(False, description="Include composite stability score")

    # Phase 13.2 diff mode:
    diff_ref: Optional[str] = Field(None, description="Git ref to compare against (e.g., 'HEAD~1', 'main')")

    # Phase 13.3 flags:
    show_cycles: bool = Field(False, description="Include cycle detection (circular dependencies)")
    aggregate: bool = Field(False, description="Aggregate multiple files (package-level view)")
    aggregate_max_depth: Optional[int] = Field(None, description="Max directory depth for aggregation")

    # Phase 13.5 flags:
    show_hydrate: bool = Field(False, description="Auto-hydrate heavily-referenced internal dependencies")


# Enable forward references for recursive models
BlueprintNode.model_rebuild()
