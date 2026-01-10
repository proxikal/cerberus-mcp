"""Blueprint generation facade - orchestrates all components.

Phase 13.1: High-level API for generating enriched blueprints with caching.
"""

import time
from pathlib import Path
from typing import List, Optional
import sqlite3

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol
from .schemas import (
    Blueprint,
    BlueprintNode,
    BlueprintRequest,
    SymbolOverlay,
    TreeRenderOptions,
)
from .cache_manager import BlueprintCache
from .dependency_overlay import DependencyOverlay
from .complexity_analyzer import ComplexityAnalyzer
from .formatter import BlueprintFormatter


class BlueprintGenerator:
    """Orchestrates blueprint generation with overlays and caching."""

    def __init__(self, conn: sqlite3.Connection):
        """
        Initialize blueprint generator.

        Args:
            conn: SQLite connection to database
        """
        self.conn = conn
        self.cache = BlueprintCache(conn)
        self.dep_overlay = DependencyOverlay(conn)
        self.complexity_analyzer = ComplexityAnalyzer()

    def generate(self, request: BlueprintRequest) -> Blueprint:
        """
        Generate blueprint for a file with requested overlays.

        Args:
            request: BlueprintRequest with file path and options

        Returns:
            Blueprint object with requested overlays applied
        """
        # Normalize file path
        file_path = str(Path(request.file_path).resolve())

        # Build flags dict for caching
        flags = {
            "deps": request.show_deps,
            "meta": request.show_meta,
            "fast": request.fast_mode,
        }

        # Try cache first
        if request.use_cache and not request.fast_mode:
            cached = self.cache.get(file_path, flags)
            if cached:
                logger.debug(f"Returning cached blueprint for {file_path}")
                return cached

        # Generate fresh blueprint
        logger.debug(f"Generating fresh blueprint for {file_path}")
        blueprint = self._generate_fresh(request)

        # Cache if enabled
        if request.use_cache and not request.fast_mode:
            self.cache.set(file_path, flags, blueprint)

        return blueprint

    def _generate_fresh(self, request: BlueprintRequest) -> Blueprint:
        """
        Generate fresh blueprint (no cache).

        Args:
            request: BlueprintRequest with options

        Returns:
            Newly generated Blueprint
        """
        file_path = str(Path(request.file_path).resolve())

        # Query symbols from database
        symbols = self._query_symbols(file_path)

        if not symbols:
            logger.warning(f"No symbols found for {file_path}")
            return Blueprint(
                file_path=file_path,
                nodes=[],
                total_symbols=0,
                cached=False,
                generated_at=time.time()
            )

        # Build hierarchical structure
        nodes = self._build_hierarchy(symbols)

        # Apply overlays
        if request.show_deps or request.show_meta:
            self._apply_overlays(
                nodes,
                symbols,
                show_deps=request.show_deps,
                show_meta=request.show_meta,
                fast_mode=request.fast_mode
            )

        # Create blueprint
        blueprint = Blueprint(
            file_path=file_path,
            nodes=nodes,
            total_symbols=0,  # Will be calculated
            cached=False,
            generated_at=time.time()
        )

        # Calculate total symbols
        blueprint.total_symbols = blueprint.count_symbols()

        return blueprint

    def _query_symbols(self, file_path: str) -> List[CodeSymbol]:
        """
        Query all symbols for a file from database.

        Args:
            file_path: Absolute file path

        Returns:
            List of CodeSymbol objects (deduplicated)
        """
        try:
            cursor = self.conn.execute(
                """
                SELECT
                    name, type, file_path, start_line, end_line,
                    signature, return_type, parameters, parent_class
                FROM symbols
                WHERE file_path = ?
                ORDER BY start_line ASC, name ASC
                """,
                (file_path,)
            )

            symbols = []
            for row in cursor.fetchall():
                (
                    name, sym_type, fp, start_line, end_line,
                    signature, return_type, parameters, parent_class
                ) = row

                symbols.append(
                    CodeSymbol(
                        name=name,
                        type=sym_type,
                        file_path=fp,
                        start_line=start_line,
                        end_line=end_line,
                        signature=signature,
                        return_type=return_type,
                        parameters=parameters,
                        parent_class=parent_class
                    )
                )

            # Deduplicate symbols (SQLite may have duplicates from indexing)
            seen = set()
            unique_symbols = []
            for sym in symbols:
                key = (sym.name, sym.type, sym.start_line, sym.parent_class or '')
                if key not in seen:
                    seen.add(key)
                    unique_symbols.append(sym)

            logger.debug(f"Queried {len(symbols)} symbols, {len(unique_symbols)} unique for {file_path}")
            return unique_symbols

        except Exception as e:
            logger.error(f"Error querying symbols for {file_path}: {e}")
            return []

    def _build_hierarchy(self, symbols: List[CodeSymbol]) -> List[BlueprintNode]:
        """
        Build hierarchical tree structure from flat symbol list.

        Args:
            symbols: Flat list of CodeSymbol objects

        Returns:
            List of top-level BlueprintNode objects with children
        """
        # Separate top-level symbols from methods
        top_level = []
        methods_by_class = {}

        for symbol in symbols:
            if symbol.parent_class:
                # This is a method - group by class
                if symbol.parent_class not in methods_by_class:
                    methods_by_class[symbol.parent_class] = []
                methods_by_class[symbol.parent_class].append(symbol)
            else:
                # Top-level symbol
                top_level.append(symbol)

        # Build nodes
        nodes = []
        for symbol in top_level:
            node = self._symbol_to_node(symbol)

            # Add methods if this is a class
            if symbol.type == "class" and symbol.name in methods_by_class:
                for method in methods_by_class[symbol.name]:
                    child_node = self._symbol_to_node(method)
                    node.children.append(child_node)

            nodes.append(node)

        return nodes

    def _symbol_to_node(self, symbol: CodeSymbol) -> BlueprintNode:
        """
        Convert CodeSymbol to BlueprintNode.

        Args:
            symbol: CodeSymbol to convert

        Returns:
            BlueprintNode with empty overlay
        """
        return BlueprintNode(
            name=symbol.name,
            type=symbol.type,
            signature=symbol.signature,
            start_line=symbol.start_line,
            end_line=symbol.end_line,
            parent_class=symbol.parent_class,
            overlay=SymbolOverlay(),
            children=[]
        )

    def _apply_overlays(
        self,
        nodes: List[BlueprintNode],
        symbols: List[CodeSymbol],
        show_deps: bool,
        show_meta: bool,
        fast_mode: bool
    ) -> None:
        """
        Apply overlays (dependencies, complexity) to nodes.

        Modifies nodes in place.

        Args:
            nodes: List of BlueprintNode objects
            symbols: Original CodeSymbol list (for queries)
            show_deps: Whether to add dependency overlay
            show_meta: Whether to add complexity overlay
            fast_mode: Skip expensive analysis
        """
        # Build symbol lookup
        symbol_map = {sym.name: sym for sym in symbols}

        # Process each node recursively
        for node in nodes:
            self._apply_overlay_to_node(
                node,
                symbol_map,
                show_deps=show_deps,
                show_meta=show_meta,
                fast_mode=fast_mode
            )

    def _apply_overlay_to_node(
        self,
        node: BlueprintNode,
        symbol_map: dict,
        show_deps: bool,
        show_meta: bool,
        fast_mode: bool
    ) -> None:
        """
        Apply overlay to a single node recursively.

        Args:
            node: BlueprintNode to enrich
            symbol_map: Map of symbol names to CodeSymbol objects
            show_deps: Add dependencies
            show_meta: Add complexity
            fast_mode: Skip expensive operations
        """
        # Get original symbol
        symbol = symbol_map.get(node.name)
        if not symbol:
            return

        # Dependencies overlay
        if show_deps and not fast_mode:
            deps = self.dep_overlay.get_dependencies(symbol)
            if deps:
                node.overlay.dependencies = deps

        # Complexity overlay
        if show_meta and not fast_mode:
            complexity = self.complexity_analyzer.analyze(symbol)
            node.overlay.complexity = complexity

        # Recursively process children
        for child in node.children:
            self._apply_overlay_to_node(
                child,
                symbol_map,
                show_deps=show_deps,
                show_meta=show_meta,
                fast_mode=fast_mode
            )

    def format_output(
        self,
        blueprint: Blueprint,
        output_format: str,
        tree_options: Optional[TreeRenderOptions] = None
    ) -> str:
        """
        Format blueprint for output.

        Args:
            blueprint: Blueprint to format
            output_format: "tree" or "json"
            tree_options: Options for tree rendering

        Returns:
            Formatted output string
        """
        if output_format == "tree":
            return BlueprintFormatter.format_as_tree(blueprint, tree_options)
        elif output_format == "json":
            # Machine mode: minified
            return BlueprintFormatter.format_as_json(blueprint, pretty=False)
        else:
            raise ValueError(f"Unknown output format: {output_format}")
