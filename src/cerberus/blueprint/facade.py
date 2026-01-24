"""Blueprint generation facade - orchestrates all components.

Phase 13.1: High-level API for generating enriched blueprints with caching.
Phase 13.2: Intelligence layer with churn, coverage, and stability.
Phase 13.3: Structural diffs, aggregation, and cycle detection.
"""

import time
from pathlib import Path
from typing import List, Optional, Union
import sqlite3

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol
from .schemas import (
    Blueprint,
    BlueprintNode,
    BlueprintRequest,
    SymbolOverlay,
    TreeRenderOptions,
    HydratedFile,
)
from .cache_manager import BlueprintCache
from .dependency_overlay import DependencyOverlay
from .complexity_analyzer import ComplexityAnalyzer
from .churn_analyzer import ChurnAnalyzer
from .coverage_analyzer import CoverageAnalyzer
from .stability_scorer import StabilityScorer
from .formatter import BlueprintFormatter
from .tree_builder import TreeBuilder
# Phase 13.3 analyzers
from .diff_analyzer import DiffAnalyzer
from .aggregator import BlueprintAggregator, AggregatedBlueprint
from .cycle_detector import CycleDetector
# Phase 13.5 analyzers
from .hydration_analyzer import HydrationAnalyzer


class BlueprintGenerator:
    """Orchestrates blueprint generation with overlays and caching."""

    def __init__(self, conn: sqlite3.Connection, repo_path: Optional[Path] = None):
        """
        Initialize blueprint generator.

        Args:
            conn: SQLite connection to database
            repo_path: Optional path to git repository root (for diff analysis)
        """
        self.conn = conn
        self.repo_path = repo_path or Path.cwd()
        self.cache = BlueprintCache(conn)
        # Phase 13.5: Pass repo_path for dependency classification
        self.dep_overlay = DependencyOverlay(conn, project_root=self.repo_path)
        self.complexity_analyzer = ComplexityAnalyzer()
        # Phase 13.2 analyzers
        self.churn_analyzer = ChurnAnalyzer()
        self.coverage_analyzer = CoverageAnalyzer()
        # Phase 13.3 analyzers
        self.diff_analyzer = DiffAnalyzer(conn, self.repo_path)
        self.aggregator = BlueprintAggregator(conn)
        self.cycle_detector = CycleDetector(conn)
        # Phase 13.5 analyzers
        self.hydration_analyzer = HydrationAnalyzer(conn, self.repo_path)

    def generate(self, request: BlueprintRequest) -> Union[Blueprint, AggregatedBlueprint]:
        """
        Generate blueprint for a file with requested overlays.

        Phase 13.3: Supports aggregation mode and structural diffs.

        Args:
            request: BlueprintRequest with file path and options

        Returns:
            Blueprint or AggregatedBlueprint object with requested overlays applied
        """
        # Phase 13.3: Handle aggregation mode
        if request.aggregate or Path(request.file_path).is_dir():
            request.aggregate = True
            return self._generate_aggregated(request)

        # Normalize file path
        file_path = str(Path(request.file_path).resolve())

        # Build flags dict for caching
        flags = {
            "deps": request.show_deps,
            "meta": request.show_meta,
            "fast": request.fast_mode,
            "churn": request.show_churn,
            "coverage": request.show_coverage,
            "stability": request.show_stability,
            "cycles": request.show_cycles,
            "diff": request.diff_ref is not None,
            "hydrate": request.show_hydrate,
        }

        # Try cache first (skip cache for diff mode as it's dynamic)
        if request.use_cache and not request.fast_mode and not request.diff_ref:
            cached = self.cache.get(file_path, flags)
            if cached:
                logger.debug(f"Returning cached blueprint for {file_path}")
                return cached

        # Generate fresh blueprint
        logger.debug(f"Generating fresh blueprint for {file_path}")
        blueprint = self._generate_fresh(request)

        # Phase 13.3: Apply diff annotations if diff mode enabled
        if request.diff_ref:
            self._annotate_diff(blueprint, request.diff_ref)

        # Phase 13.5: Apply auto-hydration if requested
        if request.show_hydrate and request.show_deps:
            # Hydration requires dependencies to be calculated
            self._apply_hydration(blueprint, request)

        # Cache if enabled
        if request.use_cache and not request.fast_mode and not request.diff_ref:
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
        if request.show_deps or request.show_meta or request.show_churn or request.show_coverage or request.show_stability or request.show_cycles:
            self._apply_overlays(
                nodes,
                symbols,
                file_path=file_path,
                show_deps=request.show_deps,
                show_meta=request.show_meta,
                show_churn=request.show_churn,
                show_coverage=request.show_coverage,
                show_stability=request.show_stability,
                show_cycles=request.show_cycles,
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
        import json as json_lib  # Avoid collision with outer json import

        # Prepare both absolute and relative paths for query
        # Database may have inconsistent path storage (absolute vs relative)
        abs_path = Path(file_path).resolve()
        paths_to_try = [str(abs_path)]

        # Also try the original unresolved path (for tests and symlinks)
        if str(abs_path) != file_path:
            paths_to_try.append(file_path)

        try:
            rel_path = abs_path.relative_to(self.repo_path)
            if str(rel_path) not in paths_to_try:
                paths_to_try.append(str(rel_path))
        except ValueError:
            pass  # Path outside repo, only try absolute

        try:
            # Try both absolute and relative paths
            placeholders = ",".join("?" * len(paths_to_try))
            cursor = self.conn.execute(
                f"""
                SELECT
                    name, type, file_path, start_line, end_line,
                    signature, return_type, parameters, parameter_types, parent_class
                FROM symbols
                WHERE file_path IN ({placeholders})
                ORDER BY start_line ASC, name ASC
                """,
                paths_to_try
            )

            symbols = []
            seen = set()
            for row in cursor.fetchall():
                (
                    name, sym_type, fp, start_line, end_line,
                    signature, return_type, parameters, parameter_types, parent_class
                ) = row

                key = (fp, name, start_line, end_line, sym_type)
                if key in seen:
                    continue
                seen.add(key)

                # Parse JSON fields (Phase 16.4 bugfix)
                parsed_params = json_lib.loads(parameters) if parameters else None
                parsed_param_types = json_lib.loads(parameter_types) if parameter_types else None

                symbols.append(
                    CodeSymbol(
                        name=name,
                        type=sym_type,
                        file_path=fp,
                        start_line=start_line,
                        end_line=end_line,
                        signature=signature,
                        return_type=return_type,
                        parameters=parsed_params,
                        parameter_types=parsed_param_types,
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
        file_path: str,
        show_deps: bool,
        show_meta: bool,
        show_churn: bool,
        show_coverage: bool,
        show_stability: bool,
        show_cycles: bool,
        fast_mode: bool
    ) -> None:
        """
        Apply overlays (dependencies, complexity, churn, coverage, stability, cycles) to nodes.

        Modifies nodes in place.

        Args:
            nodes: List of BlueprintNode objects
            symbols: Original CodeSymbol list (for queries)
            file_path: File path for cycle detection
            show_deps: Whether to add dependency overlay
            show_meta: Whether to add complexity overlay
            show_churn: Whether to add git churn overlay
            show_coverage: Whether to add test coverage overlay
            show_stability: Whether to add stability score overlay
            show_cycles: Whether to add cycle detection overlay
            fast_mode: Skip expensive analysis
        """
        # Build symbol lookup
        symbol_map = {sym.name: sym for sym in symbols}

        # Phase 13.3: Detect cycles if requested
        symbols_in_cycles = set()
        if show_cycles:
            cycles = self.cycle_detector.detect_cycles(file_path=file_path)
            symbols_in_cycles = self.cycle_detector.get_symbols_in_cycles(file_path, cycles)
            logger.debug(f"Detected {len(cycles)} cycles involving {len(symbols_in_cycles)} symbols")

        # Process each node recursively
        for node in nodes:
            self._apply_overlay_to_node(
                node,
                symbol_map,
                symbols_in_cycles=symbols_in_cycles,
                show_deps=show_deps,
                show_meta=show_meta,
                show_churn=show_churn,
                show_coverage=show_coverage,
                show_stability=show_stability,
                show_cycles=show_cycles,
                fast_mode=fast_mode
            )

    def _apply_overlay_to_node(
        self,
        node: BlueprintNode,
        symbol_map: dict,
        symbols_in_cycles: set,
        show_deps: bool,
        show_meta: bool,
        show_churn: bool,
        show_coverage: bool,
        show_stability: bool,
        show_cycles: bool,
        fast_mode: bool
    ) -> None:
        """
        Apply overlay to a single node recursively.

        Args:
            node: BlueprintNode to enrich
            symbol_map: Map of symbol names to CodeSymbol objects
            symbols_in_cycles: Set of symbol names involved in cycles
            show_deps: Add dependencies
            show_meta: Add complexity
            show_churn: Add git churn
            show_coverage: Add test coverage
            show_stability: Add stability score
            show_cycles: Add cycle detection
            fast_mode: Skip expensive operations
        """
        # Get original symbol
        symbol = symbol_map.get(node.name)
        if not symbol:
            return

        # Dependencies overlay (Phase 13.1)
        if show_deps and not fast_mode:
            deps = self.dep_overlay.get_dependencies(symbol)
            if deps:
                node.overlay.dependencies = deps

        # Complexity overlay (Phase 13.1)
        if show_meta and not fast_mode:
            complexity = self.complexity_analyzer.analyze(symbol)
            node.overlay.complexity = complexity

        # Churn overlay (Phase 13.2)
        if show_churn and not fast_mode:
            churn = self.churn_analyzer.analyze(symbol)
            if churn:
                node.overlay.churn = churn

        # Coverage overlay (Phase 13.2)
        if show_coverage and not fast_mode:
            coverage = self.coverage_analyzer.analyze(symbol)
            if coverage:
                node.overlay.coverage = coverage

        # Cycle detection overlay (Phase 13.3)
        if show_cycles:
            if node.name in symbols_in_cycles:
                node.overlay.in_cycle = True
                node.overlay.cycle_info = "⚠️ Part of circular dependency"

        # Stability score overlay (Phase 13.2)
        # Note: Stability requires complexity, churn, and coverage
        if show_stability and not fast_mode:
            # Ensure we have the prerequisite metrics
            if not node.overlay.complexity and show_meta:
                node.overlay.complexity = self.complexity_analyzer.analyze(symbol)
            if not node.overlay.churn and show_churn:
                node.overlay.churn = self.churn_analyzer.analyze(symbol)
            if not node.overlay.coverage and show_coverage:
                node.overlay.coverage = self.coverage_analyzer.analyze(symbol)

            # Calculate stability score
            stability = StabilityScorer.calculate(
                complexity=node.overlay.complexity,
                churn=node.overlay.churn,
                coverage=node.overlay.coverage,
                dependencies=node.overlay.dependencies
            )
            if stability:
                node.overlay.stability = stability

        # Recursively process children
        for child in node.children:
            self._apply_overlay_to_node(
                child,
                symbol_map,
                symbols_in_cycles=symbols_in_cycles,
                show_deps=show_deps,
                show_meta=show_meta,
                show_churn=show_churn,
                show_coverage=show_coverage,
                show_stability=show_stability,
                show_cycles=show_cycles,
                fast_mode=fast_mode
            )

    def _generate_aggregated(self, request: BlueprintRequest) -> AggregatedBlueprint:
        """
        Generate aggregated blueprint for a package (Phase 13.3).

        Args:
            request: BlueprintRequest with package path and options

        Returns:
            AggregatedBlueprint object
        """
        package_path = Path(request.file_path).resolve()

        if not package_path.is_dir():
            logger.warning(f"{package_path} is not a directory, treating as single file")
            # Fall back to single file blueprint
            request.aggregate = False
            return self.generate(request)

        return self.aggregator.aggregate_package(
            package_path=package_path,
            max_depth=request.aggregate_max_depth,
            include_deps=request.show_deps
        )

    def _annotate_diff(self, blueprint: Blueprint, git_ref: str) -> None:
        """
        Annotate blueprint with structural diff information (Phase 13.3).

        Modifies blueprint nodes in place to mark added/removed/modified symbols.

        Args:
            blueprint: Blueprint to annotate
            git_ref: Git reference to compare against
        """
        try:
            # Get structural changes
            changes = self.diff_analyzer.analyze_diff(
                file_path=blueprint.file_path,
                git_ref=git_ref
            )

            # Build change map
            change_map = {
                (change.symbol_name, change.symbol_type): change
                for change in changes
            }

            # Annotate nodes
            def annotate_node(node: BlueprintNode):
                key = (node.name, node.type)
                if key in change_map:
                    change = change_map[key]
                    # Add diff annotation to cycle_info field (reuse since rarely both used)
                    if change.change_type.value == "added":
                        node.overlay.cycle_info = f"+ NEW (added in {git_ref}..HEAD)"
                    elif change.change_type.value == "removed":
                        node.overlay.cycle_info = f"- REMOVED (deleted in {git_ref}..HEAD)"
                    elif change.change_type.value == "modified":
                        node.overlay.cycle_info = f"~ MODIFIED (signature changed)"

                # Recurse
                for child in node.children:
                    annotate_node(child)

            for node in blueprint.nodes:
                annotate_node(node)

            logger.debug(f"Annotated blueprint with {len(changes)} structural changes")

        except Exception as e:
            logger.error(f"Error annotating diff: {e}")

    def _apply_hydration(self, blueprint: Blueprint, request: BlueprintRequest) -> None:
        """
        Apply auto-hydration to blueprint (Phase 13.5).

        Analyzes dependencies and automatically includes mini-blueprints
        of heavily-referenced internal files.

        Args:
            blueprint: Main blueprint to hydrate
            request: Blueprint request with options
        """
        try:
            # Analyze which files should be hydrated
            files_to_hydrate = self.hydration_analyzer.analyze_for_hydration(blueprint)

            if not files_to_hydrate:
                logger.debug("No files selected for auto-hydration")
                return

            logger.debug(f"Auto-hydrating {len(files_to_hydrate)} files: {files_to_hydrate}")

            # Generate mini-blueprints for each hydrated file
            # (structure only, no overlays except deps for consistency)
            hydrated_files = []

            for file_path in files_to_hydrate:
                try:
                    # Count actual references for this file
                    ref_count = self.hydration_analyzer._count_file_references(blueprint).get(file_path, 0)

                    # Create minimal blueprint request (structure only)
                    hydrate_request = BlueprintRequest(
                        file_path=file_path,
                        show_deps=False,  # Don't recursively hydrate dependencies
                        show_meta=False,
                        show_churn=False,
                        show_coverage=False,
                        show_stability=False,
                        show_cycles=False,
                        show_hydrate=False,  # Prevent recursive hydration
                        use_cache=True,      # Use cache if available
                        fast_mode=True,      # Fast mode for hydrated files
                        output_format=request.output_format
                    )

                    # Generate mini-blueprint
                    mini_blueprint = self._generate_fresh(hydrate_request)

                    # Create HydratedFile entry
                    hydrated_file = HydratedFile(
                        file_path=file_path,
                        reference_count=ref_count,
                        blueprint=mini_blueprint
                    )

                    hydrated_files.append(hydrated_file)
                    logger.debug(f"Hydrated {file_path} ({ref_count} refs, {mini_blueprint.total_symbols} symbols)")

                except Exception as e:
                    logger.warning(f"Failed to hydrate {file_path}: {e}")
                    continue

            # Attach hydrated files to main blueprint
            blueprint.hydrated_files = hydrated_files
            logger.debug(f"Successfully hydrated {len(hydrated_files)} files")

        except Exception as e:
            logger.error(f"Error applying hydration: {e}")

    def format_output(
        self,
        blueprint: Union[Blueprint, AggregatedBlueprint],
        output_format: str,
        tree_options: Optional[TreeRenderOptions] = None
    ) -> str:
        """
        Format blueprint for output.

        Phase 13.3: Supports both Blueprint and AggregatedBlueprint.

        Args:
            blueprint: Blueprint or AggregatedBlueprint to format
            output_format: "tree" or "json"
            tree_options: Options for tree rendering

        Returns:
            Formatted output string
        """
        # Phase 13.3: Handle aggregated blueprints
        if isinstance(blueprint, AggregatedBlueprint):
            if output_format == "json":
                import json
                return json.dumps(blueprint.to_dict(), indent=None)
            elif output_format == "json-compact":
                return BlueprintFormatter.format_as_json_compact(blueprint)
            elif output_format == "flat":
                return BlueprintFormatter.format_as_flat(blueprint)
            else:
                # Tree format for aggregated packages
                builder = TreeBuilder(tree_options or TreeRenderOptions())
                return builder.build_aggregated_tree(blueprint.package_path, blueprint.nodes)

        # Regular blueprint formatting
        if output_format == "tree":
            return BlueprintFormatter.format_as_tree(blueprint, tree_options)
        elif output_format == "json":
            # Machine mode: minified
            return BlueprintFormatter.format_as_json(blueprint, pretty=False)
        elif output_format == "json-compact":
            return BlueprintFormatter.format_as_json_compact(blueprint)
        elif output_format == "flat":
            return BlueprintFormatter.format_as_flat(blueprint)
        else:
            raise ValueError(f"Unknown output format: {output_format}")
