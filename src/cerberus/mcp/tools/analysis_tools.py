"""
Advanced code analysis tools for AI agents.

Provides:
- Project onboarding summaries
- Change impact analysis
- Test coverage mapping
- Pattern consistency checking
"""

from pathlib import Path
from typing import Optional, List

from cerberus.analysis.project_summary import generate_project_summary
from cerberus.analysis.impact_analyzer import analyze_change_impact
from cerberus.analysis.test_mapper import map_test_coverage
from cerberus.analysis.pattern_checker import check_pattern_consistency, PatternChecker
from cerberus.analysis.architecture_validator import validate_architecture, ArchitectureValidator
from cerberus.analysis.semantic_search import search_by_behavior, SemanticSearchEngine
from cerberus.analysis.circular_dependency_detector import find_circular_dependencies
from cerberus.mcp.tools.token_utils import estimate_json_tokens, add_usage_hint
from ..index_manager import get_index_manager


def register(mcp):
    """Register analysis tools with MCP server."""

    @mcp.tool()
    def project_summary() -> dict:
        """
        Generate comprehensive project onboarding summary.

        **Use Case:**
        Perfect for AI agents starting a new session - provides 80/20 value
        in ~800 tokens instead of 5,000+ tokens of exploration.

        **What It Includes:**
        - Tech stack detection
        - Architecture overview
        - Key module purposes
        - Entry points
        - Coding patterns
        - Dependencies
        - Testing approach

        **Token Efficiency:**
        ~800 tokens vs ~5,000+ tokens for manual exploration (84% savings)

        Returns:
            dict with:
            - status: "ok" or "error"
            - summary: ProjectSummary object with all fields
            - _token_info: Token cost metadata
        """
        try:
            # Get project root (where .cerberus/ index is)
            manager = get_index_manager()
            project_root = manager._project_root or Path.cwd()

            # Generate summary
            summary = generate_project_summary(project_root)

            response = {
                "status": "ok",
                "summary": summary.to_dict(),
            }

            # Add token info
            tokens = estimate_json_tokens(summary.to_dict())
            response["_token_info"] = {
                "estimated_tokens": tokens,
                "alternative": "Manual codebase exploration",
                "alternative_tokens": 5000,
                "tokens_saved": 5000 - tokens,
                "savings_percent": round(((5000 - tokens) / 5000) * 100, 1)
            }

            add_usage_hint(
                response,
                "Use this at session start for quick project context",
                hint_type="suggestion"
            )

            return response

        except Exception as exc:
            return {
                "status": "error",
                "error_type": "summary_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def analyze_impact(symbol_name: str, file_path: Optional[str] = None) -> dict:
        """
        Analyze the impact of changing a symbol.

        **Use Case:**
        Before refactoring, understand what code and tests would be affected.
        Makes safe modification decisions with confidence.

        **What It Analyzes:**
        - Direct callers (immediate impact)
        - Transitive callers (ripple effects)
        - Affected tests (what needs updating)
        - Risk score (low, medium, high, critical)
        - Breaking change warnings
        - Safety assessment
        - Actionable recommendations

        **Risk Scoring:**
        - Low: < 5 callers, good test coverage
        - Medium: 5-15 callers, moderate coverage
        - High: 15+ callers or poor coverage
        - Critical: Heavy usage + poor coverage

        Args:
            symbol_name: Name of symbol to analyze (function, class, method)
            file_path: Optional file path to disambiguate if multiple symbols share name

        Returns:
            dict with:
            - status: "ok" or "error"
            - analysis: ImpactAnalysis object with complete assessment
            - _token_info: Token cost metadata
        """
        try:
            manager = get_index_manager()
            index = manager.get_index()

            if not hasattr(index, "_store"):
                return {
                    "status": "error",
                    "error_type": "index_required",
                    "message": "Impact analysis requires SQLite index"
                }

            store = index._store
            project_root = manager._project_root or Path.cwd()

            # Perform analysis
            analysis = analyze_change_impact(store, symbol_name, file_path, project_root)

            response = {
                "status": "ok",
                "analysis": analysis.to_dict(),
            }

            # Add token info
            tokens = estimate_json_tokens(analysis.to_dict())
            response["_token_info"] = {
                "estimated_tokens": tokens,
                "risk_level": analysis.risk_score,
            }

            # Add safety hint
            if not analysis.safe_to_modify:
                add_usage_hint(
                    response,
                    f"⚠️  {analysis.risk_score.upper()} RISK: Review recommendations before modifying",
                    hint_type="warning"
                )
            else:
                add_usage_hint(
                    response,
                    "✓ Safe to modify with normal precautions",
                    hint_type="suggestion"
                )

            return response

        except Exception as exc:
            return {
                "status": "error",
                "error_type": "analysis_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def test_coverage(symbol_name: str, file_path: Optional[str] = None) -> dict:
        """
        Map test coverage for a symbol.

        **Use Case:**
        Understand what tests exist for code you're about to modify.
        Identifies coverage gaps and suggests improvements.

        **What It Provides:**
        - Test functions that exercise this symbol
        - Coverage percentage estimate
        - Uncovered branches/paths
        - Coverage quality assessment
        - Safety for modification
        - Specific recommendations

        **Coverage Quality:**
        - excellent: 90%+ coverage, 3+ tests
        - good: 70%+ coverage, 2+ tests
        - fair: 50%+ coverage, 1+ test
        - poor: Some coverage but insufficient
        - none: No test coverage found

        Args:
            symbol_name: Name of symbol to analyze
            file_path: Optional file path to disambiguate

        Returns:
            dict with:
            - status: "ok" or "error"
            - coverage: TestCoverageReport with analysis
            - _token_info: Token cost metadata
        """
        try:
            manager = get_index_manager()
            index = manager.get_index()

            if not hasattr(index, "_store"):
                return {
                    "status": "error",
                    "error_type": "index_required",
                    "message": "Test coverage mapping requires SQLite index"
                }

            store = index._store
            project_root = manager._project_root or Path.cwd()

            # Perform coverage mapping
            coverage = map_test_coverage(store, symbol_name, file_path, project_root)

            response = {
                "status": "ok",
                "coverage": coverage.to_dict(),
            }

            # Add token info
            tokens = estimate_json_tokens(coverage.to_dict())
            response["_token_info"] = {
                "estimated_tokens": tokens,
                "coverage_quality": coverage.coverage_quality,
            }

            # Add coverage hint
            if coverage.coverage_quality == "none":
                add_usage_hint(
                    response,
                    "⚠️  No test coverage - add tests before modifying",
                    hint_type="warning"
                )
            elif coverage.coverage_quality in ("excellent", "good"):
                add_usage_hint(
                    response,
                    f"✓ {coverage.coverage_quality.capitalize()} coverage - safe to refactor",
                    hint_type="suggestion"
                )
            else:
                add_usage_hint(
                    response,
                    f"⚠️  {coverage.coverage_quality.capitalize()} coverage - consider adding tests",
                    hint_type="warning"
                )

            return response

        except Exception as exc:
            return {
                "status": "error",
                "error_type": "coverage_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def check_pattern(
        pattern: str,
        scope: Optional[str] = None,
        show_examples: bool = True,
        limit: int = 20
    ) -> dict:
        """
        Check if code follows established project patterns.

        **Use Case:**
        When writing new code, check how this project handles common patterns.
        Ensures consistency and helps maintain code quality.

        **Available Patterns:**
        - dataclass: Use dataclasses for data structures
        - type_hints: Type hints on function parameters and returns
        - async_await: Async/await for I/O operations
        - error_handling: Proper try/except with logging
        - import_style: Absolute vs relative imports
        - docstring_style: Google-style vs Sphinx-style docstrings

        **What It Provides:**
        - Conforming file count
        - Violations with file:line and snippets
        - Examples of correct usage (2-3 files)
        - Consistency score (0.0-1.0)
        - Actionable suggestions

        **Token Efficiency:**
        ~800-1500 tokens with bounded results (limit violations to 20)

        Args:
            pattern: Pattern to check (see Available Patterns above)
            scope: Optional path to scope check (file or directory). None = entire project
            show_examples: Include 2-3 examples of correct usage (default: True)
            limit: Max violations to return (default: 20, prevents token explosion)

        Returns:
            dict with:
            - status: "ok" or "error"
            - result: PatternCheckResult with analysis
            - _token_info: Token cost metadata
        """
        try:
            manager = get_index_manager()
            project_root = manager._project_root or Path.cwd()

            # Perform pattern check
            result = check_pattern_consistency(
                project_root=project_root,
                pattern_name=pattern,
                scope=scope,
                show_examples=show_examples,
                limit=limit
            )

            response = {
                "status": "ok",
                "result": result.to_dict(),
            }

            # Add token info
            tokens = estimate_json_tokens(result.to_dict())
            response["_token_info"] = {
                "estimated_tokens": tokens,
                "consistency_score": result.consistency_score,
                "violations_shown": len(result.violations),
                "examples_shown": len(result.examples),
            }

            # Add consistency hint
            if result.consistency_score >= 0.9:
                add_usage_hint(
                    response,
                    f"✓ Excellent pattern consistency ({result.consistency_score:.0%})",
                    hint_type="suggestion"
                )
            elif result.consistency_score >= 0.7:
                add_usage_hint(
                    response,
                    f"Good consistency ({result.consistency_score:.0%}) - {len(result.violations)} violations found",
                    hint_type="suggestion"
                )
            elif result.consistency_score > 0:
                add_usage_hint(
                    response,
                    f"⚠️  Low consistency ({result.consistency_score:.0%}) - pattern not widely adopted",
                    hint_type="warning"
                )
            else:
                add_usage_hint(
                    response,
                    f"Pattern '{pattern}' not found in project",
                    hint_type="info"
                )

            # Add available patterns hint if pattern not found
            if "Unknown pattern" in result.description:
                available = ", ".join(PatternChecker.PATTERNS.keys())
                add_usage_hint(
                    response,
                    f"Available patterns: {available}",
                    hint_type="info"
                )

            return response

        except Exception as exc:
            return {
                "status": "error",
                "error_type": "pattern_check_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def validate_architecture(
        rules: Optional[List[str]] = None,
        scope: Optional[str] = None,
        limit: int = 30
    ) -> dict:
        """
        Validate code against architectural rules.

        **Use Case:**
        Enforce structural boundaries and design constraints.
        Catches architectural violations before they become problems.

        **Available Rules:**
        - layer_separation: MCP tools must use index_manager (not direct store access)
        - type_coverage: All public functions must have type hints
        - docstring_coverage: All public classes/functions must have docstrings
        - async_boundaries: MCP tools must be async functions
        - import_restrictions: No circular imports between modules

        **What It Provides:**
        - Violations with file:line and severity
        - Code snippets showing the issue
        - Actionable suggestions for fixes
        - Conformance score (0.0-1.0)
        - Status: pass, warnings, or fail

        **Token Efficiency:**
        ~800-1500 tokens with bounded results (limit violations to 30)

        Args:
            rules: List of rule names to check. None = all rules
            scope: Optional path scope (file or directory). None = entire project
            limit: Max violations to return (default: 30)

        Returns:
            dict with:
            - status: "ok" or "error"
            - result: ArchitectureValidationResult with violations
            - _token_info: Token cost metadata
        """
        try:
            manager = get_index_manager()
            project_root = manager._project_root or Path.cwd()

            # Perform validation
            result = validate_architecture(
                project_root=project_root,
                rules=rules,
                scope=scope,
                limit=limit
            )

            response = {
                "status": "ok",
                "result": result.to_dict(),
            }

            # Add token info
            tokens = estimate_json_tokens(result.to_dict())
            response["_token_info"] = {
                "estimated_tokens": tokens,
                "conformance_score": result.conformance_score,
                "violations_shown": len(result.violations),
                "validation_status": result.status,
            }

            # Add status hint
            if result.status == "pass":
                add_usage_hint(
                    response,
                    f"✓ All architectural rules passed ({result.conformance_score:.0%} conformance)",
                    hint_type="suggestion"
                )
            elif result.status == "warnings":
                add_usage_hint(
                    response,
                    f"⚠️  {len(result.violations)} violations found - review recommendations",
                    hint_type="warning"
                )
            else:  # fail
                add_usage_hint(
                    response,
                    f"❌ Critical violations found - fix before proceeding",
                    hint_type="warning"
                )

            # Add available rules hint if needed
            if rules and not result.violations:
                available = ", ".join(ArchitectureValidator(project_root).rules.keys())
                add_usage_hint(
                    response,
                    f"Available rules: {available}",
                    hint_type="info"
                )

            return response

        except Exception as exc:
            return {
                "status": "error",
                "error_type": "validation_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def search_behavior(
        query: str,
        scope: Optional[str] = None,
        limit: int = 15
    ) -> dict:
        """
        Search code by behavior/purpose using natural language.

        **Use Case:**
        Find code by what it does, not just what it's named.
        Perfect for "show me how this project does X" questions.

        **Example Queries:**
        - "functions that make HTTP calls"
        - "error handlers"
        - "database queries"
        - "file I/O operations"
        - "async functions"
        - "logging operations"
        - "data validation"

        **How It Works:**
        Uses AST analysis to detect behavioral patterns:
        - HTTP calls: Detects httpx, requests, urllib usage
        - Error handlers: Finds try/except blocks with logging
        - Database queries: Detects SQL keywords and .execute() calls
        - File I/O: Finds open(), Path read/write operations
        - Async operations: Finds async def and await usage
        - Logging: Detects logger method calls
        - Data validation: Finds @dataclass, pydantic, validators

        **Token Efficiency:**
        ~800-1700 tokens with bounded results (limit matches to 15)

        Args:
            query: Natural language description of behavior to find
                   (e.g., "functions that handle errors")
            scope: Optional path scope (file or directory). None = entire project
            limit: Max matches to return (default: 15)

        Returns:
            dict with:
            - status: "ok" or "error"
            - result: SemanticSearchResult with matches
            - _token_info: Token cost metadata
        """
        try:
            manager = get_index_manager()
            project_root = manager._project_root or Path.cwd()

            # Perform semantic search
            result = search_by_behavior(
                project_root=project_root,
                query=query,
                scope=scope,
                limit=limit
            )

            response = {
                "status": "ok",
                "result": result.to_dict(),
            }

            # Add token info
            tokens = estimate_json_tokens(result.to_dict())
            response["_token_info"] = {
                "estimated_tokens": tokens,
                "matches_found": len(result.matches),
                "patterns_detected": result.detected_patterns,
                "files_scanned": result.total_files_scanned,
            }

            # Add result hint
            if result.matches:
                avg_confidence = sum(m["confidence"] for m in result.matches) / len(result.matches)
                add_usage_hint(
                    response,
                    f"✓ Found {len(result.matches)} matches (avg confidence: {avg_confidence:.0%})",
                    hint_type="suggestion"
                )
            else:
                add_usage_hint(
                    response,
                    "No matches found. Try different keywords or broader query.",
                    hint_type="info"
                )

            # Add detected patterns hint
            if result.detected_patterns:
                add_usage_hint(
                    response,
                    f"Searched for behaviors: {', '.join(result.detected_patterns)}",
                    hint_type="info"
                )

            return response

        except Exception as exc:
            return {
                "status": "error",
                "error_type": "semantic_search_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def find_circular_deps(
        scope: Optional[str] = None,
        min_severity: str = "low"
    ) -> dict:
        """
        Find circular dependency chains in the project.

        **Use Case:**
        Detect circular imports that can cause runtime errors and maintenance issues.
        Essential for maintaining clean architecture and preventing import deadlocks.

        **What It Detects:**
        - Direct cycles: A → B → A
        - Three-way cycles: A → B → C → A
        - Long chains: A → B → C → D → A
        - Any length circular dependency chains

        **Severity Levels:**
        - critical: Long chains (4+) involving core modules
        - high: 3+ modules or involving critical modules (main, server, core)
        - medium: Direct cycles (2 modules) or 3-way cycles
        - low: Simple cycles in utility modules

        **Token Efficiency:**
        ~500-1500 tokens with bounded results

        Args:
            scope: Optional path scope (directory). None = entire project
            min_severity: Minimum severity to report (default: "low")
                         Options: "low", "medium", "high", "critical"

        Returns:
            dict with:
            - status: "ok" or "error"
            - result: CircularDependencyResult with chains
            - _token_info: Token cost metadata
        """
        try:
            manager = get_index_manager()
            project_root = manager._project_root or Path.cwd()

            # Detect circular dependencies
            result = find_circular_dependencies(
                project_root=project_root,
                scope=scope,
                min_severity=min_severity
            )

            response = {
                "status": "ok",
                "result": result.to_dict(),
            }

            # Add token info
            tokens = estimate_json_tokens(result.to_dict())
            response["_token_info"] = {
                "estimated_tokens": tokens,
                "total_modules": result.total_modules,
                "circular_chains_found": len(result.circular_chains),
            }

            # Add result hint
            if result.circular_chains:
                # Count by severity
                by_severity = {}
                for chain in result.circular_chains:
                    sev = chain["severity"]
                    by_severity[sev] = by_severity.get(sev, 0) + 1

                critical = by_severity.get("critical", 0)
                high = by_severity.get("high", 0)

                if critical > 0:
                    add_usage_hint(
                        response,
                        f"❌ {critical} CRITICAL circular dependencies found - fix immediately",
                        hint_type="warning"
                    )
                elif high > 0:
                    add_usage_hint(
                        response,
                        f"⚠️  {high} HIGH severity circular dependencies - should fix",
                        hint_type="warning"
                    )
                else:
                    add_usage_hint(
                        response,
                        f"⚠️  {len(result.circular_chains)} circular dependencies found",
                        hint_type="warning"
                    )
            else:
                add_usage_hint(
                    response,
                    f"✓ No circular dependencies ({result.total_modules} modules analyzed)",
                    hint_type="suggestion"
                )

            return response

        except Exception as exc:
            return {
                "status": "error",
                "error_type": "circular_dependency_detection_failed",
                "message": str(exc),
            }
