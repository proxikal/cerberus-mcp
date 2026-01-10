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


class SymbolOverlay(BaseModel):
    """Overlays (metadata) attached to a symbol in blueprint."""

    dependencies: Optional[List[DependencyInfo]] = Field(
        None, description="Dependencies (calls) with confidence scores"
    )
    complexity: Optional[ComplexityMetrics] = Field(
        None, description="Complexity metrics"
    )
    # Future Phase 13.2 fields (placeholders for schema evolution):
    # churn: Optional[ChurnMetrics] = None
    # coverage: Optional[CoverageMetrics] = None
    # stability: Optional[StabilityScore] = None


class BlueprintNode(BaseModel):
    """A node in the blueprint tree (represents a symbol)."""

    name: str = Field(description="Symbol name")
    type: Literal["function", "class", "method", "variable", "interface", "enum", "struct"] = Field(
        description="Symbol type"
    )
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


class BlueprintRequest(BaseModel):
    """Request parameters for blueprint generation."""

    file_path: str
    show_deps: bool = Field(False, description="Include dependency overlay")
    show_meta: bool = Field(False, description="Include complexity metrics")
    use_cache: bool = Field(True, description="Allow cache usage")
    fast_mode: bool = Field(False, description="Skip expensive analysis")
    output_format: Literal["tree", "json"] = Field("json", description="Output format")

    # Future flags (Phase 13.2+):
    # show_churn: bool = False
    # show_coverage: bool = False
    # show_stability: bool = False


# Enable forward references for recursive models
BlueprintNode.model_rebuild()
