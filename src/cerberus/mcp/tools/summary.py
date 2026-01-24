"""Activation summary tool for CerberusBeta skill."""
from typing import Dict, Any, Optional


def register(mcp):
    @mcp.tool()
    def display_activation_summary(
        template: Optional[str] = None
    ) -> Dict[str, Any]:
        """Display formatted activation summary combining health and memory data."""
        from ..index_manager import get_index_manager
        from ...memory.storage import MemoryStorage
        from ...summarization.facade import get_summarization_facade
        from ...summaries import format_activation_summary
        from ..config import get_config_value
        from cerberus import __version__
        from datetime import datetime
        from pathlib import Path
        import sys

        # Import health check logic
        from .diagnostics import _is_project_context

        # Get template from config if not provided
        if template is None:
            template = get_config_value("skill.summary_template", "modern")

        # Collect health data (same as health_check tool)
        is_project = _is_project_context()
        context = "project" if is_project else "general"

        # Check index (only relevant in project context)
        index_info: Dict[str, Any] = {"available": False, "path": None, "age_hours": None}
        try:
            manager = get_index_manager()
            if manager._index is not None:
                index_info["available"] = True
                index_info["path"] = str(manager._index_path) if manager._index_path else None
            else:
                try:
                    discovered = manager._discover_index_path()
                    if discovered.exists():
                        index_info["available"] = True
                        index_info["path"] = str(discovered)
                        # Check age
                        mtime = discovered.stat().st_mtime
                        age_hours = (datetime.now().timestamp() - mtime) / 3600
                        index_info["age_hours"] = round(age_hours, 1)
                except FileNotFoundError:
                    pass
        except Exception:
            pass

        # Check memory (SQLite-based)
        memory_info = {"available": False, "preferences": 0, "decisions": 0, "total": 0}
        memory_context_str = None
        try:
            storage = MemoryStorage(enable_anchoring=False)

            if storage.db_path.exists():
                memory_info["available"] = True
                stats = storage.get_stats()
                memory_info["total"] = stats.get("total", 0)

                # Count by category
                by_category = stats.get("by_category", {})
                memory_info["preferences"] = by_category.get("preference", 0)
                memory_info["decisions"] = by_category.get("decision", 0)
                memory_info["corrections"] = by_category.get("correction", 0)

                # Count unique projects
                by_scope = stats.get("by_scope", {})
                project_scopes = [s for s in by_scope.keys() if s.startswith("project:")]
                memory_info["decision_projects"] = len(project_scopes)

                # Get memory context for key items
                from cerberus.memory.retrieval import MemoryRetrieval
                retrieval = MemoryRetrieval(storage)
                # Get a compact context string
                context_result = retrieval.get_context(
                    project=None,  # Auto-detect
                    compact=True,
                    include_preferences=True,
                    include_decisions=True,
                    include_corrections=True,
                )
                if context_result:
                    memory_context_str = context_result
        except Exception:
            # Silently continue if memory system unavailable
            pass

        # Build health data structure
        health_data = {
            "status": "healthy",
            "context": context,
            "version": __version__,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "timestamp": datetime.now().isoformat(),
            "capabilities": [
                "search",
                "symbols",
                "reading",
                "structure",
                "synthesis",
                "summarization",
                "analysis",
                "indexing",
                "memory",
                "quality",
                "metrics",
            ],
            "index": index_info,
            "index_available": index_info.get("available", False),
            "index_path": index_info.get("path"),
            "memory": memory_info,
        }

        # Format summary
        summary = format_activation_summary(
            health_data=health_data,
            memory_context=memory_context_str,
            template=template,
        )

        return {
            "summary": summary,
            "template": template,
        }
