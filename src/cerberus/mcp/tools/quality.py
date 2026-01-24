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
        """Detect code style violations and optionally preview fixes."""
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
                fixable: list = []
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
        path: Optional[str] = None,
        rules: Optional[List[str]] = None,
        dry_run: bool = False,
        create_backup: bool = True,
        paths: Optional[List[str]] = None,
    ) -> dict:
        """Apply style fixes to file(s) with optional dry-run."""
        # Validate inputs
        if not path and not paths:
            return {
                "status": "error",
                "error_type": "missing_path",
                "message": "Must provide either path for single fix or paths for bulk fix"
            }

        # Handle bulk mode
        if paths:
            all_fixes: list = []
            files_modified_count = 0
            total_violations = 0
            errors: list = []
            processed_files: list = []

            for idx, file_path in enumerate(paths):
                try:
                    target = Path(file_path)
                    if not target.exists():
                        errors.append(f"{file_path}: Path not found")
                        continue

                    if target.is_file():
                        success, fixes = fixer.fix_file(str(target), preview=dry_run)
                        if success and fixes:
                            if not dry_run:
                                files_modified_count += 1
                            total_violations += len(fixes)
                            all_fixes.extend([_serialize_fix(f, str(target)) for f in fixes])
                            processed_files.append(str(target))
                    else:
                        # Handle directory
                        results = fixer.fix_directory(str(target), preview=dry_run)
                        for fpath, (ok, fx) in results.items():
                            if ok and fx:
                                if not dry_run:
                                    files_modified_count += 1
                                total_violations += len(fx)
                                all_fixes.extend([_serialize_fix(fix, fpath) for fix in fx])
                                processed_files.append(fpath)

                except Exception as e:
                    errors.append(f"{file_path}: {str(e)}")

            # Invalidate index if files were modified
            if files_modified_count > 0 and not dry_run:
                from ..index_manager import get_index_manager
                get_index_manager().invalidate()

            # Build bulk response
            if dry_run:
                return {
                    "status": "bulk_dry_run",
                    "requested_count": len(paths),
                    "processed_count": len(processed_files),
                    "would_fix": total_violations,
                    "violations": all_fixes,
                    "errors": errors if errors else None
                }

            return {
                "status": "bulk_fixed",
                "requested_count": len(paths),
                "files_modified": files_modified_count,
                "violations_fixed": total_violations,
                "applied_fixes": all_fixes,
                "errors": errors if errors else None
            }

        # Single mode (original logic)
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
        """Predict related changes needed after modifying symbol."""
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
