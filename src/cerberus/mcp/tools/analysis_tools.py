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
        """Generate high-level project overview with 80/20 analysis."""
        try:
            # Get project root (where .cerberus/ index is)
            manager = get_index_manager()
            index = manager.get_index()
            project_root = Path(getattr(index, "project_root", None) or Path.cwd())

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
        """Analyze impact of changing a symbol."""
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
            project_root = Path(getattr(index, "project_root", None) or Path.cwd())

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
        """Find tests covering specific code."""
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
            project_root = Path(getattr(index, "project_root", None) or Path.cwd())

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
        """Verify code follows project patterns."""
        try:
            manager = get_index_manager()
            index = manager.get_index()
            project_root = Path(getattr(index, "project_root", None) or Path.cwd())

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
        """Enforce architectural rules."""
        try:
            manager = get_index_manager()
            index = manager.get_index()
            project_root = Path(getattr(index, "project_root", None) or Path.cwd())

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
        """Find code with specific runtime behavior."""
        try:
            manager = get_index_manager()
            index = manager.get_index()
            project_root = Path(getattr(index, "project_root", None) or Path.cwd())

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
        """Detect circular import dependencies."""
        try:
            manager = get_index_manager()
            index = manager.get_index()
            project_root = Path(getattr(index, "project_root", None) or Path.cwd())

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
                by_severity: dict = {}
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
