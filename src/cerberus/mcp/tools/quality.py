"""Quality and style tools."""
from pathlib import Path
from typing import Any, Dict, List, Optional

from cerberus.quality.detector import StyleDetector
from cerberus.quality.fixer import StyleFixer
from cerberus.quality.style_guard import StyleIssue, StyleFix
from ..index_manager import get_index_manager
from ..config import get_config_value


def _serialize_issue(issue: StyleIssue, file_path: str) -> Dict[str, Any]:
    return {
        "file": file_path,
        "line": issue.line,
        "lines": list(issue.lines) if issue.lines else None,
        "type": issue.issue_type.value,
        "message": issue.description,
        "suggestion": issue.suggestion,
        "fixable": issue.auto_fixable,
    }


def _serialize_fix(fix: StyleFix, file_path: str) -> Dict[str, Any]:
    return {
        "file": file_path,
        "type": fix.issue_type.value,
        "line": fix.line,
        "lines": list(fix.lines) if fix.lines else None,
        "before": fix.before,
        "after": fix.after,
        "description": fix.description,
    }


def register(mcp):
    detector = StyleDetector()
    fixer = StyleFixer()

    @mcp.tool()
    def style_check(path: str, rules: Optional[List[str]] = None, fix_preview: bool = False) -> dict:
        """
        Check code for style violations.

        **AI WORKFLOW (Iterative):**
        1. Run style_check on file/directory
        2. Review the first 30 violations shown
        3. Call style_fix to fix them automatically (or fix manually)
        4. Re-run style_check to see remaining violations
        5. Repeat until clean

        This iterative approach is token-efficient and prevents overwhelming
        output on messy codebases.

        Args:
            path: File or directory to check
            rules: Optional list of specific rules to check (default: all rules)
            fix_preview: If True, include preview of auto-fixes for fixable issues

        Returns:
            dict with:
            - status: "checked" or "error"
            - path: Path that was checked
            - violation_count: Total number of violations found
            - violations_shown: Number of violations in response (limited)
            - violations: List of {file, line, type, message, suggestion, fixable}
            - truncated: True if more violations exist beyond the limit
            - fix_preview: (if requested) List of proposed fixes
        """
        target = Path(path)
        if not target.exists():
            return {
                "status": "error",
                "error_type": "path_not_found",
                "message": f"Path not found: {path}",
            }

        try:
            issues: List[Dict[str, Any]] = []

            if target.is_file():
                file_issues = detector.check_file(str(target))
                issues.extend(_serialize_issue(i, str(target)) for i in file_issues)
            else:
                results = detector.check_directory(str(target))
                for file_path, file_issues in results.items():
                    issues.extend(_serialize_issue(i, file_path) for i in file_issues)

            # Apply limit to prevent token explosion and encourage iterative fixing
            max_violations = get_config_value("limits.max_style_violations", 30)
            total_violations = len(issues)
            truncated = total_violations > max_violations
            limited_issues = issues[:max_violations]

            result: Dict[str, Any] = {
                "status": "checked",
                "path": str(target),
                "violation_count": total_violations,
                "violations_shown": len(limited_issues),
                "violations": limited_issues,
            }

            if truncated:
                result["truncated"] = True
                result["warning"] = f"Output limited to {max_violations} violations (out of {total_violations}). Fix these first and re-run."

            if fix_preview and issues:
                # Preview fixes for fixable issues on files we checked
                fixable = []
                files_seen = {vi["file"] for vi in issues if vi.get("fixable")}
                for fpath in files_seen:
                    success, fixes = fixer.fix_file(fpath, preview=True)
                    if success and fixes:
                        fixable.extend(_serialize_fix(fix, fpath) for fix in fixes)
                if fixable:
                    result["fix_preview"] = fixable

            return result
        except Exception as exc:
            return {
                "status": "error",
                "error_type": "check_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def style_fix(
        path: str,
        rules: Optional[List[str]] = None,
        dry_run: bool = False,
        create_backup: bool = True,
    ) -> dict:
        """
        Auto-fix style violations.

        Automatically applies fixes for fixable style violations.
        Use dry_run=True to preview changes without modifying files.

        Args:
            path: File or directory to fix
            rules: Optional list of specific rules to fix (default: all fixable rules)
            dry_run: If True, only preview fixes without applying them
            create_backup: If True, create backup before modifying files

        Returns:
            dict with:
            - status: "fixed", "dry_run", or "error"
            - files_modified: Number of files changed (0 if dry_run)
            - violations_fixed: Total fixes applied or would be applied
            - applied_fixes: List of {file, type, line, before, after, description}
        """
        target = Path(path)
        if not target.exists():
            return {
                "status": "error",
                "error_type": "path_not_found",
                "message": f"Path not found: {path}",
            }

        try:
            if target.is_file():
                success, fixes = fixer.fix_file(str(target), preview=dry_run)
                files_modified = 1 if (success and fixes and not dry_run) else 0
                violations_fixed = len(fixes)
                applied_fixes = [_serialize_fix(f, str(target)) for f in fixes]
            else:
                results = fixer.fix_directory(str(target), preview=dry_run)
                files_modified = sum(1 for ok, fx in results.values() if ok and fx and not dry_run)
                violations_fixed = sum(len(fx) for _, fx in results.values())
                applied_fixes = [
                    _serialize_fix(fix, fpath)
                    for fpath, (_, fixes) in results.items()
                    for fix in fixes
                ]

            if dry_run:
                return {
                    "status": "dry_run",
                    "would_fix": violations_fixed,
                    "violations": applied_fixes,
                }

            if files_modified > 0:
                from ..index_manager import get_index_manager

                get_index_manager().invalidate()

            return {
                "status": "fixed",
                "files_modified": files_modified,
                "violations_fixed": violations_fixed,
                "applied_fixes": applied_fixes,
            }
        except Exception as exc:
            return {
                "status": "error",
                "error_type": "fix_failed",
                "message": str(exc),
            }

    @mcp.tool()
    def related_changes(file_path: str, symbol_name: Optional[str] = None) -> dict:
        """
        Suggest related changes based on current modification.

        Uses code relationships and historical patterns to predict other
        files or symbols that might need updating when you change this code.

        Args:
            file_path: Path to the file being modified
            symbol_name: Optional specific symbol being modified (uses filename stem if not provided)

        Returns:
            dict with:
            - status: "analyzed" or "error"
            - file: The file being analyzed
            - symbol: The symbol being analyzed
            - stats: Analysis statistics
            - suggestions: List of {file, symbol, line, reason, confidence, score, relationship, command}
        """
        from cerberus.quality.predictor import PredictionEngine

        # Use IndexManager to get the current index path
        manager = get_index_manager()
        try:
            manager.get_index()  # Ensure index is loaded
            if not manager._index_path:
                return {
                    "status": "error",
                    "error_type": "index_required",
                    "message": "No index found. Run index_build first.",
                }
            index_path = manager._index_path
        except FileNotFoundError:
            return {
                "status": "error",
                "error_type": "index_required",
                "message": "No index found. Run index_build first.",
            }

        engine = PredictionEngine(str(index_path))
        edited_symbol = symbol_name or Path(file_path).stem

        try:
            suggestions, stats = engine.predict_related_changes(edited_symbol, file_path)
            return {
                "status": "analyzed",
                "file": file_path,
                "symbol": symbol_name,
                "stats": stats.__dict__,
                "suggestions": [
                    {
                        "file": s.file,
                        "symbol": s.symbol,
                        "line": s.line,
                        "reason": s.reason,
                        "confidence": s.confidence,
                        "score": s.confidence_score,
                        "relationship": s.relationship,
                        "command": s.command,
                    }
                    for s in suggestions
                ],
            }
        except Exception as exc:
            return {
                "status": "error",
                "error_type": "prediction_failed",
                "message": str(exc),
            }
