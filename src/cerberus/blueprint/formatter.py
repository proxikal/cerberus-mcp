"""Output formatting for blueprints (ASCII tree vs JSON).

Phase 13.1: Support both human-readable tree and machine-readable JSON outputs.
"""

import json
from typing import Dict, Any
from .schemas import Blueprint, TreeRenderOptions
from .tree_builder import TreeBuilder


class BlueprintFormatter:
    """Formats blueprints for different output modes."""

    @staticmethod
    def format_as_tree(blueprint: Blueprint, options: TreeRenderOptions = None) -> str:
        """
        Format blueprint as ASCII tree.

        Args:
            blueprint: Blueprint to format
            options: Tree rendering options

        Returns:
            ASCII tree string
        """
        builder = TreeBuilder(options or TreeRenderOptions())
        return builder.build_tree(blueprint)

    @staticmethod
    def format_as_json(
        blueprint: Blueprint,
        pretty: bool = False,
        include_metadata: bool = True
    ) -> str:
        """
        Format blueprint as JSON.

        Args:
            blueprint: Blueprint to format
            pretty: Whether to pretty-print JSON
            include_metadata: Include generation metadata

        Returns:
            JSON string
        """
        # Convert to dict
        data = BlueprintFormatter._to_dict(blueprint, include_metadata)

        # Serialize
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            # Machine mode: minified JSON
            return json.dumps(data, separators=(',', ':'), ensure_ascii=False)

    @staticmethod
    def _to_dict(blueprint: Blueprint, include_metadata: bool) -> Dict[str, Any]:
        """
        Convert Blueprint to dictionary representation.

        Args:
            blueprint: Blueprint to convert
            include_metadata: Include generation metadata

        Returns:
            Dictionary representation
        """
        result = {
            "file": blueprint.file_path,
            "total_symbols": blueprint.total_symbols,
            "symbols": [BlueprintFormatter._node_to_dict(node) for node in blueprint.nodes]
        }

        if include_metadata:
            result["metadata"] = {
                "cached": blueprint.cached,
                "generated_at": blueprint.generated_at
            }

        return result

    @staticmethod
    def _node_to_dict(node) -> Dict[str, Any]:
        """
        Convert BlueprintNode to dictionary.

        Args:
            node: BlueprintNode to convert

        Returns:
            Dictionary representation
        """
        result = {
            "name": node.name,
            "type": node.type,
            "line": node.start_line,
            "signature": node.signature
        }

        # Add parent class if method
        if node.parent_class:
            result["parent_class"] = node.parent_class

        # Add overlays if present
        overlay = node.overlay

        if overlay.dependencies:
            result["dependencies"] = [
                {
                    "target": dep.target,
                    "confidence": dep.confidence,
                    "resolution_method": dep.resolution_method
                }
                for dep in overlay.dependencies
            ]

        if overlay.complexity:
            result["complexity"] = {
                "lines": overlay.complexity.lines,
                "score": overlay.complexity.complexity,
                "level": overlay.complexity.level,
                "branches": overlay.complexity.branches,
                "nesting": overlay.complexity.nesting
            }

        # Add children (methods for classes)
        if node.children:
            result["methods" if node.type == "class" else "children"] = [
                BlueprintFormatter._node_to_dict(child) for child in node.children
            ]

        return result
