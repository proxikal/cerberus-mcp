"""ASCII tree builder for blueprint visualization.

Phase 13.1: Token-efficient visual hierarchy using indentation and tree characters.
"""

from typing import List
from .schemas import Blueprint, BlueprintNode, TreeRenderOptions


class TreeBuilder:
    """Builds ASCII tree representations of code structure."""

    # Tree drawing characters
    BRANCH = "├── "
    LAST_BRANCH = "└── "
    VERTICAL = "│   "
    SPACE = "    "

    def __init__(self, options: TreeRenderOptions = None):
        """Initialize tree builder with render options."""
        self.options = options or TreeRenderOptions()

    def build_tree(self, blueprint: Blueprint) -> str:
        """
        Convert blueprint to ASCII tree representation.

        Args:
            blueprint: Blueprint object with hierarchical nodes

        Returns:
            ASCII tree string with proper indentation and tree characters
        """
        lines = []

        # File header
        lines.append(f"[File: {blueprint.file_path}]")

        # Render each top-level node
        for i, node in enumerate(blueprint.nodes):
            is_last = i == len(blueprint.nodes) - 1
            lines.extend(self._render_node(node, depth=0, is_last=is_last, parent_prefixes=[]))

        return "\n".join(lines)

    def _render_node(
        self,
        node: BlueprintNode,
        depth: int,
        is_last: bool,
        parent_prefixes: List[bool]
    ) -> List[str]:
        """
        Render a single node and its children recursively.

        Args:
            node: Node to render
            depth: Current tree depth
            is_last: Whether this is the last child of its parent
            parent_prefixes: List of booleans indicating parent nesting levels

        Returns:
            List of rendered lines
        """
        # Check max_depth limit
        if self.options.max_depth is not None and depth >= self.options.max_depth:
            return []

        lines = []

        # Calculate prefix (tree characters)
        prefix = self._calculate_prefix(depth, is_last, parent_prefixes)

        # Build node label
        label = self._format_node_label(node)

        # Add main node line
        lines.append(f"{prefix}{label}")

        # Add overlay information (dependencies, complexity)
        overlay_lines = self._format_overlays(node, depth, is_last, parent_prefixes)
        lines.extend(overlay_lines)

        # Render children
        if node.children:
            new_parent_prefixes = parent_prefixes + [is_last]
            for i, child in enumerate(node.children):
                is_last_child = i == len(node.children) - 1
                lines.extend(
                    self._render_node(
                        child,
                        depth=depth + 1,
                        is_last=is_last_child,
                        parent_prefixes=new_parent_prefixes
                    )
                )

        return lines

    def _calculate_prefix(
        self,
        depth: int,
        is_last: bool,
        parent_prefixes: List[bool]
    ) -> str:
        """
        Calculate tree character prefix based on depth and position.

        Args:
            depth: Current depth level
            is_last: Whether this is the last sibling
            parent_prefixes: History of parent is_last values

        Returns:
            Tree character prefix string
        """
        if depth == 0:
            # Top-level nodes
            return self.LAST_BRANCH if is_last else self.BRANCH

        # Build prefix from parent levels
        prefix_parts = []
        for i, parent_is_last in enumerate(parent_prefixes):
            if parent_is_last:
                prefix_parts.append(self.SPACE)
            else:
                prefix_parts.append(self.VERTICAL)

        # Add current level connector
        prefix_parts.append(self.LAST_BRANCH if is_last else self.BRANCH)

        return "".join(prefix_parts)

    def _format_node_label(self, node: BlueprintNode) -> str:
        """
        Format the label for a node.

        Args:
            node: BlueprintNode to format

        Returns:
            Formatted label string
        """
        # Symbol type tag
        if node.type == "class":
            type_tag = "Class"
        elif node.type == "function":
            type_tag = "Function"
        elif node.type == "method":
            type_tag = ""  # Methods don't need explicit tag in tree
        else:
            type_tag = node.type.capitalize()

        # Build label
        parts = []

        if type_tag:
            parts.append(f"[{type_tag}: {node.name}]")
        else:
            parts.append(node.name)

        # Add signature if enabled and available
        if self.options.show_signatures and node.signature:
            # For methods, show signature directly
            if node.type == "method" or node.type == "function":
                # Extract just the signature part (remove 'def ' prefix if present)
                sig = node.signature
                if sig.startswith("def "):
                    sig = sig[4:]
                if not parts[0].endswith(")"):  # If name doesn't include params
                    parts[0] = sig
            else:
                parts.append(node.signature)

        # Add line range if enabled
        if self.options.show_line_numbers:
            parts.append(f"({node.line_range})")

        return " ".join(parts)

    def _format_overlays(
        self,
        node: BlueprintNode,
        depth: int,
        is_last: bool,
        parent_prefixes: List[bool]
    ) -> List[str]:
        """
        Format overlay information (dependencies, complexity, churn, coverage, stability).

        Args:
            node: Node with overlay data
            depth: Current depth
            is_last: Whether this is last sibling
            parent_prefixes: Parent nesting levels

        Returns:
            List of formatted overlay lines
        """
        lines = []
        overlay = node.overlay

        # Calculate indent for overlay lines (align under node content)
        indent = self._calculate_overlay_indent(depth, is_last, parent_prefixes)

        # Dependencies overlay (Phase 13.1)
        if overlay.dependencies:
            deps_str = self._format_dependencies(overlay.dependencies)
            lines.append(f"{indent}[Calls: {deps_str}]")

        # Complexity overlay (Phase 13.1)
        if overlay.complexity:
            complexity_str = self._format_complexity(overlay.complexity)
            lines.append(f"{indent}{complexity_str}")

        # Churn overlay (Phase 13.2)
        if overlay.churn:
            churn_str = self._format_churn(overlay.churn)
            lines.append(f"{indent}{churn_str}")

        # Coverage overlay (Phase 13.2)
        if overlay.coverage:
            coverage_str = self._format_coverage(overlay.coverage)
            lines.append(f"{indent}{coverage_str}")

        # Stability overlay (Phase 13.2)
        if overlay.stability:
            stability_str = self._format_stability(overlay.stability)
            lines.append(f"{indent}{stability_str}")

        return lines

    def _calculate_overlay_indent(
        self,
        depth: int,
        is_last: bool,
        parent_prefixes: List[bool]
    ) -> str:
        """Calculate indentation for overlay lines."""
        if depth == 0:
            # Top-level: align with tree character width
            return self.SPACE

        # Build indent from parent levels
        indent_parts = []
        for parent_is_last in parent_prefixes:
            if parent_is_last:
                indent_parts.append(self.SPACE)
            else:
                indent_parts.append(self.VERTICAL)

        # Add spacing for current level
        if is_last:
            indent_parts.append(self.SPACE)
        else:
            indent_parts.append(self.VERTICAL)

        return "".join(indent_parts)

    def _format_dependencies(self, dependencies: List) -> str:
        """
        Format dependency list with confidence scores.

        Args:
            dependencies: List of DependencyInfo objects

        Returns:
            Formatted dependency string
        """
        dep_strs = []
        for dep in dependencies:
            # Format: "target ✓confidence"
            dep_str = f"{dep.target} ✓{dep.confidence:.1f}"
            dep_strs.append(dep_str)

        return ", ".join(dep_strs)

    def _format_complexity(self, complexity) -> str:
        """
        Format complexity metrics.

        Args:
            complexity: ComplexityMetrics object

        Returns:
            Formatted complexity string
        """
        parts = [
            f"[Lines: {complexity.lines}]",
            f"[Complexity: {complexity.level}]",
            f"[Branches: {complexity.branches}]",
            f"[Nesting: {complexity.nesting}]"
        ]
        return " ".join(parts)

    def _format_churn(self, churn) -> str:
        """
        Format git churn metrics.

        Args:
            churn: ChurnMetrics object

        Returns:
            Formatted churn string
        """
        parts = []

        if churn.last_modified:
            parts.append(f"[Modified: {churn.last_modified}]")

        if churn.edit_frequency > 0:
            parts.append(f"[Edits: {churn.edit_frequency}/week]")

        if churn.unique_authors > 0:
            parts.append(f"[Authors: {churn.unique_authors}]")

        if churn.last_author:
            parts.append(f"[Last: {churn.last_author}]")

        return " ".join(parts) if parts else "[Churn: no data]"

    def _format_coverage(self, coverage) -> str:
        """
        Format test coverage metrics.

        Args:
            coverage: CoverageMetrics object

        Returns:
            Formatted coverage string
        """
        parts = []

        # Coverage percentage with indicator
        if coverage.percent >= 80:
            indicator = "✓"
        elif coverage.percent >= 50:
            indicator = "⚠"
        else:
            indicator = "⚠️"

        parts.append(f"[Coverage: {coverage.percent:.1f}% {indicator}]")

        if coverage.test_files:
            test_count = len(coverage.test_files)
            parts.append(f"[Tests: {test_count}]")
        else:
            parts.append("[Tests: none]")

        return " ".join(parts)

    def _format_stability(self, stability) -> str:
        """
        Format stability score.

        Args:
            stability: StabilityScore object

        Returns:
            Formatted stability string
        """
        return f"[Stability: {stability.level} ({stability.score:.2f})]"
