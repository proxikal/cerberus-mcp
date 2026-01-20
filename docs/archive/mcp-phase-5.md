# Phase 5: Quality + Metrics Tools

## Overview

Implement quality checking (style validation, auto-fix) and metrics tracking (token efficiency, command usage) tools.

## Goals

- Style checking against configured rules
- Auto-fix for common style violations
- Token efficiency tracking
- Usage metrics for optimization insights

## Tasks

### 5.1 Create Quality Tools Module

**File: `src/cerberus/mcp/tools/quality.py`**
```python
"""Quality and style tools."""
from typing import List, Optional, Dict, Any
from pathlib import Path

from cerberus.quality.detector import StyleDetector
from cerberus.quality.fixer import StyleFixer
from ..config import get_config_value


def register(mcp):

    _detector = None
    _fixer = None

    def get_detector():
        nonlocal _detector
        if _detector is None:
            rules = get_config_value("quality.style_rules", ["black", "isort"])
            _detector = StyleDetector(rules=rules)
        return _detector

    def get_fixer():
        nonlocal _fixer
        if _fixer is None:
            _fixer = StyleFixer()
        return _fixer

    @mcp.tool()
    def style_check(
        path: str,
        rules: Optional[List[str]] = None,
        fix_preview: bool = False
    ) -> dict:
        """
        Check code for style violations.

        Analyzes code against configured style rules (black, isort, etc.)
        and reports any violations.

        Args:
            path: File or directory to check
            rules: Override default rules (e.g., ["black", "isort", "flake8"])
            fix_preview: If True, show what auto-fix would change

        Returns:
            Violations found with locations and suggested fixes
        """
        detector = get_detector()

        target = Path(path)
        if not target.exists():
            return {
                "status": "error",
                "error_type": "path_not_found",
                "message": f"Path not found: {path}"
            }

        try:
            if target.is_file():
                violations = detector.check_file(target, rules=rules)
            else:
                violations = detector.check_directory(target, rules=rules)

            result = {
                "status": "checked",
                "path": str(path),
                "violation_count": len(violations),
                "violations": [
                    {
                        "file": v.file_path,
                        "line": v.line,
                        "column": v.column,
                        "rule": v.rule,
                        "message": v.message,
                        "severity": v.severity,
                        "fixable": v.fixable
                    }
                    for v in violations
                ]
            }

            if fix_preview and violations:
                fixer = get_fixer()
                fixable = [v for v in violations if v.fixable]
                if fixable:
                    preview = fixer.preview_fixes(fixable)
                    result["fix_preview"] = preview

            return result

        except Exception as e:
            return {
                "status": "error",
                "error_type": "check_failed",
                "message": str(e)
            }

    @mcp.tool()
    def style_fix(
        path: str,
        rules: Optional[List[str]] = None,
        dry_run: bool = False,
        create_backup: bool = True
    ) -> dict:
        """
        Auto-fix style violations.

        Automatically fixes violations that have known fixes
        (formatting, import sorting, etc.).

        Args:
            path: File or directory to fix
            rules: Override default rules
            dry_run: If True, report what would change without applying
            create_backup: Create .bak files before modifying

        Returns:
            Summary of fixes applied
        """
        detector = get_detector()
        fixer = get_fixer()

        target = Path(path)
        if not target.exists():
            return {
                "status": "error",
                "error_type": "path_not_found",
                "message": f"Path not found: {path}"
            }

        try:
            # First detect violations
            if target.is_file():
                violations = detector.check_file(target, rules=rules)
            else:
                violations = detector.check_directory(target, rules=rules)

            fixable = [v for v in violations if v.fixable]

            if not fixable:
                return {
                    "status": "nothing_to_fix",
                    "violations_found": len(violations),
                    "fixable": 0
                }

            if dry_run:
                return {
                    "status": "dry_run",
                    "would_fix": len(fixable),
                    "violations": [
                        {
                            "file": v.file_path,
                            "line": v.line,
                            "rule": v.rule,
                            "message": v.message
                        }
                        for v in fixable
                    ]
                }

            # Apply fixes
            result = fixer.fix_violations(
                fixable,
                create_backup=create_backup
            )

            # Invalidate index if files changed
            if result.get("files_modified", 0) > 0:
                from ..index_manager import get_index_manager
                get_index_manager().invalidate()

            return {
                "status": "fixed",
                "files_modified": result.get("files_modified", 0),
                "violations_fixed": result.get("violations_fixed", 0),
                "backups_created": result.get("backups", []) if create_backup else []
            }

        except Exception as e:
            return {
                "status": "error",
                "error_type": "fix_failed",
                "message": str(e)
            }

    @mcp.tool()
    def related_changes(
        file_path: str,
        symbol_name: Optional[str] = None
    ) -> dict:
        """
        Suggest related changes based on current modification.

        When editing code, suggests other files/symbols that might
        need corresponding updates (callers, tests, docs).

        Args:
            file_path: File being modified
            symbol_name: Specific symbol being changed (optional)

        Returns:
            List of related files/symbols to consider
        """
        from cerberus.quality.predictor import ChangePredictor
        from ..index_manager import get_index_manager

        manager = get_index_manager()
        index = manager.get_index()

        try:
            predictor = ChangePredictor(index)
            suggestions = predictor.predict_related(
                file_path=file_path,
                symbol_name=symbol_name
            )

            return {
                "status": "analyzed",
                "file": file_path,
                "symbol": symbol_name,
                "suggestions": [
                    {
                        "file": s.file_path,
                        "symbol": s.symbol_name,
                        "reason": s.reason,
                        "confidence": s.confidence,
                        "priority": s.priority
                    }
                    for s in suggestions
                ]
            }

        except Exception as e:
            return {
                "status": "error",
                "error_type": "prediction_failed",
                "message": str(e)
            }
```

### 5.2 Create Metrics Tools Module

**File: `src/cerberus/mcp/tools/metrics.py`**
```python
"""Metrics and efficiency tracking tools."""
from typing import Optional
from datetime import datetime, timedelta

from cerberus.metrics import get_tracker
from cerberus.metrics.efficiency import get_efficiency_tracker


def register(mcp):

    @mcp.tool()
    def metrics_report(
        period: str = "session",
        detailed: bool = False
    ) -> dict:
        """
        Get efficiency metrics report.

        Shows token savings, command usage, and efficiency trends.

        Args:
            period: Time period - "session", "today", "week", "all"
            detailed: Include per-command breakdown

        Returns:
            Metrics summary with savings calculations
        """
        try:
            tracker = get_efficiency_tracker()
            token_tracker = get_tracker()

            # Get efficiency data
            efficiency_data = tracker.get_report(period=period)

            # Get token tracking data
            token_data = token_tracker.get_summary()

            result = {
                "period": period,
                "summary": {
                    "total_commands": efficiency_data.get("total_commands", 0),
                    "tokens_saved": token_data.get("tokens_saved", 0),
                    "tokens_baseline": token_data.get("baseline_tokens", 0),
                    "efficiency_percent": token_data.get("efficiency_percent", 0),
                    "estimated_cost_saved": _estimate_cost_savings(token_data.get("tokens_saved", 0))
                },
                "top_commands": efficiency_data.get("command_usage", [])[:5]
            }

            if detailed:
                result["by_command"] = efficiency_data.get("by_command", {})
                result["by_hour"] = efficiency_data.get("by_hour", {})
                result["hints_shown"] = efficiency_data.get("hints_shown", {})

            return result

        except Exception as e:
            return {
                "status": "error",
                "error_type": "metrics_failed",
                "message": str(e)
            }

    @mcp.tool()
    def metrics_clear(
        confirm: bool = False
    ) -> dict:
        """
        Clear metrics data.

        Args:
            confirm: Must be True to actually clear

        Returns:
            Confirmation of cleared data
        """
        if not confirm:
            return {
                "status": "confirmation_required",
                "message": "Set confirm=True to clear all metrics data"
            }

        try:
            tracker = get_efficiency_tracker()
            tracker.clear()

            token_tracker = get_tracker()
            token_tracker.reset()

            return {
                "status": "cleared",
                "message": "All metrics data has been cleared"
            }

        except Exception as e:
            return {
                "status": "error",
                "error_type": "clear_failed",
                "message": str(e)
            }

    @mcp.tool()
    def metrics_status() -> dict:
        """
        Get current metrics collection status.

        Returns:
            Whether metrics are enabled, storage location, etc.
        """
        try:
            tracker = get_efficiency_tracker()

            return {
                "enabled": tracker.is_enabled(),
                "storage_path": str(tracker.storage_path) if hasattr(tracker, 'storage_path') else None,
                "session_start": tracker.session_start.isoformat() if hasattr(tracker, 'session_start') else None,
                "commands_this_session": tracker.session_command_count if hasattr(tracker, 'session_command_count') else 0
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


def _estimate_cost_savings(tokens_saved: int) -> dict:
    """Estimate cost savings based on token counts."""
    # Rough estimates based on typical API pricing
    # Claude: ~$0.008 per 1K input tokens, $0.024 per 1K output tokens
    # Assume 50/50 input/output split

    input_tokens = tokens_saved // 2
    output_tokens = tokens_saved // 2

    input_cost = (input_tokens / 1000) * 0.008
    output_cost = (output_tokens / 1000) * 0.024
    total_cost = input_cost + output_cost

    return {
        "tokens": tokens_saved,
        "estimated_usd": round(total_cost, 4),
        "note": "Estimate based on typical Claude API pricing"
    }
```

### 5.3 Create Dependencies/Call Graph Tools

**File: `src/cerberus/mcp/tools/analysis.py`**
```python
"""Code analysis tools - dependencies, call graphs."""
from typing import Optional, List
from pathlib import Path

from cerberus.resolution import (
    get_dependencies,
    build_call_graph,
    get_callers,
    get_callees
)
from ..index_manager import get_index_manager


def register(mcp):

    @mcp.tool()
    def deps(
        symbol_name: str,
        include_callers: bool = True,
        include_callees: bool = True,
        include_imports: bool = True
    ) -> dict:
        """
        Get dependency information for a symbol.

        Shows what calls this symbol, what it calls, and its imports.

        Args:
            symbol_name: Symbol to analyze
            include_callers: Include functions that call this symbol
            include_callees: Include functions this symbol calls
            include_imports: Include import dependencies

        Returns:
            Dependency graph for the symbol
        """
        manager = get_index_manager()
        index = manager.get_index()

        try:
            result = {
                "symbol": symbol_name,
                "callers": [],
                "callees": [],
                "imports": []
            }

            if include_callers:
                callers = get_callers(symbol_name, index)
                result["callers"] = [
                    {
                        "name": c.name,
                        "file": c.file_path,
                        "line": c.line
                    }
                    for c in callers
                ]

            if include_callees:
                callees = get_callees(symbol_name, index)
                result["callees"] = [
                    {
                        "name": c.name,
                        "file": c.file_path,
                        "line": c.line
                    }
                    for c in callees
                ]

            if include_imports:
                deps = get_dependencies(symbol_name, index)
                result["imports"] = deps.imports

            return result

        except Exception as e:
            return {
                "status": "error",
                "error_type": "analysis_failed",
                "message": str(e)
            }

    @mcp.tool()
    def call_graph(
        symbol_name: str,
        depth: int = 2,
        direction: str = "both"
    ) -> dict:
        """
        Build recursive call graph from a symbol.

        Args:
            symbol_name: Starting symbol
            depth: How many levels deep to trace
            direction: "callers", "callees", or "both"

        Returns:
            Nested call graph structure
        """
        manager = get_index_manager()
        index = manager.get_index()

        try:
            graph = build_call_graph(
                symbol_name=symbol_name,
                index=index,
                max_depth=depth,
                direction=direction
            )

            return {
                "root": symbol_name,
                "depth": depth,
                "direction": direction,
                "graph": _serialize_graph(graph)
            }

        except Exception as e:
            return {
                "status": "error",
                "error_type": "graph_failed",
                "message": str(e)
            }


def _serialize_graph(node, seen=None) -> dict:
    """Convert call graph to serializable dict, handling cycles."""
    if seen is None:
        seen = set()

    if node.name in seen:
        return {"name": node.name, "cyclic_ref": True}

    seen.add(node.name)

    return {
        "name": node.name,
        "file": node.file_path,
        "line": node.line,
        "children": [
            _serialize_graph(child, seen.copy())
            for child in (node.children or [])
        ]
    }
```

### 5.4 Update Server Registration

**Update `src/cerberus/mcp/server.py`:**
```python
"""FastMCP server setup and tool registration."""
from fastmcp import FastMCP

from .tools import (
    search, symbols, reading, indexing,
    memory, structure, editing,
    quality, metrics, analysis
)

mcp = FastMCP("cerberus")

def create_server():
    """Create and configure the MCP server."""
    # Read tools
    search.register(mcp)
    symbols.register(mcp)
    reading.register(mcp)
    structure.register(mcp)

    # Analysis tools
    analysis.register(mcp)

    # Index management
    indexing.register(mcp)

    # Memory system
    memory.register(mcp)

    # Editing tools
    editing.register(mcp)

    # Quality & metrics
    quality.register(mcp)
    metrics.register(mcp)

    return mcp

def run_server():
    """Run the MCP server."""
    server = create_server()
    server.run()
```

## Files to Create/Modify

```
src/cerberus/mcp/
├── server.py           # MODIFIED
└── tools/
    ├── quality.py      # NEW - style_check, style_fix, related_changes
    ├── metrics.py      # NEW - metrics_report, metrics_clear, metrics_status
    └── analysis.py     # NEW - deps, call_graph
```

## Acceptance Criteria

- [ ] `style_check` detects violations correctly
- [ ] `style_check` with fix_preview shows potential fixes
- [ ] `style_fix` applies fixes and creates backups
- [ ] `style_fix` dry_run mode works
- [ ] `related_changes` suggests relevant files/symbols
- [ ] `metrics_report` shows token savings
- [ ] `metrics_report` with detailed=True shows breakdown
- [ ] `metrics_clear` requires confirmation
- [ ] `metrics_status` shows collection state
- [ ] `deps` returns callers, callees, imports
- [ ] `call_graph` builds recursive graph
- [ ] `call_graph` handles cyclic references

## Dependencies

- Phase 1-4 completed
- Existing quality/ module working
- Existing metrics/ module working

## Notes

- Style rules should be configurable per-project
- Metrics should persist across server restarts
- Consider adding style rule explanations for learning
