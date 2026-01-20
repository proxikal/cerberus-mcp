"""Output formatting for blueprints (ASCII tree vs JSON).

Phase 13.1: Support both human-readable tree and machine-readable JSON outputs.
"""

import json
from typing import Dict, Any, Union
from .schemas import Blueprint, TreeRenderOptions
from .aggregator import AggregatedBlueprint
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
    def format_as_json_compact(blueprint: Union[Blueprint, AggregatedBlueprint]) -> str:
        """
        Format blueprint as compact JSON (minimal tokens).

        Differences from full JSON:
        - No indentation/whitespace.
        - Omits null/empty fields where safe.
        - Uses short field names (sig, parent).
        """
        def _strip_node(node):
            data = {
                "name": node.name,
                "type": node.type,
                "line": node.start_line,
            }
            if node.signature:
                data["sig"] = node.signature
            if node.parent_class:
                data["parent"] = node.parent_class
            if node.children:
                # Only include methods for classes; flatten to minimal info
                data["methods"] = [
                    {"name": c.name, "line": c.start_line}
                    for c in node.children
                ]
            return data

        if isinstance(blueprint, AggregatedBlueprint):
            payload = {
                "package": blueprint.package_path,
                "files": [
                    {
                        "file": node.file_path,
                        "symbols": [_strip_node(child) for child in node.children],
                    }
                    for node in blueprint.nodes
                ],
            }
        else:
            payload = {
                "file": blueprint.file_path,
                "symbols": [_strip_node(n) for n in blueprint.nodes],
            }

        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def format_as_flat(blueprint: Union[Blueprint, AggregatedBlueprint]) -> str:
        """
        Format blueprint as flat symbol list (minimal tokens).

        Returns one symbol per line: "type:name (line X)"
        Ideal for quick overview with ~200 tokens.
        """
        lines = []

        if isinstance(blueprint, AggregatedBlueprint):
            for node in blueprint.nodes:
                lines.append(f"# {node.file_path}")
                for child in node.children:
                    lines.append(f"  {child.type}:{child.name} (L{child.start_line})")
                    for method in child.children:
                        lines.append(f"    {method.type}:{method.name} (L{method.start_line})")
        else:
            lines.append(f"# {blueprint.file_path}")
            for node in blueprint.nodes:
                lines.append(f"{node.type}:{node.name} (L{node.start_line})")
                for child in node.children:
                    lines.append(f"  {child.type}:{child.name} (L{child.start_line})")

        return "\n".join(lines)

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

        # Phase 13.5: Include hydrated files
        if blueprint.hydrated_files:
            result["hydrated_dependencies"] = [
                {
                    "file": hf.file_path,
                    "reference_count": hf.reference_count,
                    "total_symbols": hf.blueprint.total_symbols,
                    "symbols": [BlueprintFormatter._node_to_dict(node) for node in hf.blueprint.nodes]
                }
                for hf in blueprint.hydrated_files
            ]

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
                    "target_file": dep.target_file,  # Phase 16.4: Required for hydration
                    "confidence": dep.confidence,
                    "resolution_method": dep.resolution_method,
                    "dependency_type": dep.dependency_type  # Phase 13.5
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

        # Phase 13.2 overlays
        if overlay.churn:
            result["churn"] = {
                "last_modified": overlay.churn.last_modified,
                "last_modified_timestamp": overlay.churn.last_modified_timestamp,
                "edit_frequency": overlay.churn.edit_frequency,
                "unique_authors": overlay.churn.unique_authors,
                "last_author": overlay.churn.last_author
            }

        if overlay.coverage:
            result["coverage"] = {
                "percent": overlay.coverage.percent,
                "covered_lines": overlay.coverage.covered_lines,
                "total_lines": overlay.coverage.total_lines,
                "test_files": overlay.coverage.test_files,
                "assertion_count": overlay.coverage.assertion_count
            }

        if overlay.stability:
            result["stability"] = {
                "score": overlay.stability.score,
                "level": overlay.stability.level,
                "factors": overlay.stability.factors
            }

        # Phase 13.3: Cycle detection and diff annotations
        if overlay.in_cycle:
            result["in_cycle"] = overlay.in_cycle
        if overlay.cycle_info:
            result["annotation"] = overlay.cycle_info

        # Add children (methods for classes)
        if node.children:
            result["methods" if node.type == "class" else "children"] = [
                BlueprintFormatter._node_to_dict(child) for child in node.children
            ]

        return result
