"""Tests for Phase 13.5 Section 3: Width Management & Smart Truncation."""

import pytest

pytestmark = [pytest.mark.fast, pytest.mark.blueprint]

from cerberus.blueprint.tree_builder import TreeBuilder
from cerberus.blueprint.schemas import (
    BlueprintNode,
    DependencyInfo,
    TreeRenderOptions,
)


class TestWidthManagement:
    """Tests for width management and smart truncation."""

    @pytest.fixture
    def tree_builder(self):
        """Create TreeBuilder with default options."""
        return TreeBuilder(TreeRenderOptions())

    def test_is_private_symbol_single_underscore(self, tree_builder):
        """Test private symbol detection for single underscore."""
        assert tree_builder._is_private_symbol("_private_func") is True
        assert tree_builder._is_private_symbol("_helper") is True

    def test_is_private_symbol_dunder_not_private(self, tree_builder):
        """Test that dunder methods are not considered private."""
        assert tree_builder._is_private_symbol("__init__") is False
        assert tree_builder._is_private_symbol("__str__") is False

    def test_is_private_symbol_public(self, tree_builder):
        """Test public symbols are not private."""
        assert tree_builder._is_private_symbol("public_func") is False
        assert tree_builder._is_private_symbol("myFunction") is False

    def test_truncate_line_no_limit(self, tree_builder):
        """Test truncation with no max_width (no truncation)."""
        long_line = "x" * 200
        result = tree_builder._truncate_line(long_line)
        assert result == long_line
        assert len(result) == 200

    def test_truncate_line_under_limit(self):
        """Test truncation when line is under limit."""
        builder = TreeBuilder(TreeRenderOptions(max_width=100))
        short_line = "x" * 50
        result = builder._truncate_line(short_line)
        assert result == short_line

    def test_truncate_line_over_limit(self):
        """Test truncation when line exceeds limit."""
        builder = TreeBuilder(TreeRenderOptions(max_width=80))
        long_line = "x" * 200
        result = builder._truncate_line(long_line)
        assert len(result) == 80
        assert result.endswith("...")
        assert result == ("x" * 77) + "..."

    def test_format_dependencies_truncation(self):
        """Test dependency list truncation."""
        builder = TreeBuilder(TreeRenderOptions(truncate_threshold=3))

        deps = [
            DependencyInfo(target=f"func{i}", confidence=0.9, dependency_type="internal")
            for i in range(10)
        ]

        result = builder._format_dependencies(deps)
        assert "... and 7 more" in result
        assert result.count("func") == 3

    def test_format_dependencies_no_truncation(self):
        """Test dependency list without truncation."""
        builder = TreeBuilder(TreeRenderOptions(truncate_threshold=10))

        deps = [
            DependencyInfo(target=f"func{i}", confidence=0.9, dependency_type="internal")
            for i in range(5)
        ]

        result = builder._format_dependencies(deps)
        assert "... and" not in result
        assert result.count("func") == 5

    def test_collapse_private_filters_symbols(self):
        """Test collapse_private option filters private symbols."""
        builder = TreeBuilder(TreeRenderOptions(collapse_private=True))

        public_child = BlueprintNode(
            name="public_method",
            type="method",
            start_line=1,
            end_line=5
        )
        private_child = BlueprintNode(
            name="_private_method",
            type="method",
            start_line=6,
            end_line=10
        )

        parent = BlueprintNode(
            name="MyClass",
            type="class",
            start_line=1,
            end_line=20,
            children=[public_child, private_child]
        )

        lines = builder._render_node(parent, depth=0, is_last=True, parent_prefixes=[])

        content = "\n".join(lines)
        assert "public_method" in content
        assert "_private_method" not in content
        assert "Private: 1 symbols collapsed" in content
