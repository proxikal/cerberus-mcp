"""Diagnostics and health check tools."""
import os
import sys
from datetime import datetime
from pathlib import Path

from cerberus import __version__

# Project indicators - files/dirs that suggest we're in a CODE project
PROJECT_INDICATORS = [
    # Version control
    ".git", ".svn", ".hg",
    # Language-specific project files
    "go.mod", "package.json", "Cargo.toml", "pyproject.toml",
    "setup.py", "requirements.txt", "Makefile", "pom.xml",
    "build.gradle", "composer.json", "Gemfile", "mix.exs",
]


def _is_project_context() -> bool:
    """Check if current directory appears to be a CODE project."""
    cwd = Path.cwd()

    # Check standard project indicators
    for indicator in PROJECT_INDICATORS:
        if (cwd / indicator).exists():
            return True

    # Check if Cerberus has indexed this directory (not just stored data)
    cerberus_index = cwd / ".cerberus" / "index.db"
    if cerberus_index.exists():
        return True

    return False


def register(mcp):
    @mcp.tool()
    def health_check() -> dict:
        """
        Check MCP server health and comprehensive status.

        Context-aware: detects if in project vs general directory.
        Only recommends index operations when in project context.

        Returns:
            dict with:
            - status: "healthy" if server is functioning
            - context: "project" or "general"
            - version: Cerberus version
            - index: Index availability (project context only)
            - memory: Memory system stats
            - summarization: LLM availability
            - recommendations: Suggested actions (context-appropriate)
        """
        from ..index_manager import get_index_manager

        recommendations = []
        is_project = _is_project_context()
        context = "project" if is_project else "general"

        # Check index (only relevant in project context)
        index_info = {"available": False, "path": None, "age_hours": None}
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
                        if age_hours > 24:
                            recommendations.append("Index is >24h old. Consider: index_build()")
                except FileNotFoundError:
                    recommendations.append("No index found. Run: index_build()")
        except Exception:
            recommendations.append("Index check failed. Run: index_build()")

        # Check memory
        memory_info = {"available": False, "preferences": 0, "decisions": 0}
        try:
            from cerberus.memory import MemoryStore
            store = MemoryStore()
            if store.profile_path.exists():
                memory_info["available"] = True
                from cerberus.memory import ProfileManager, DecisionManager
                profile = ProfileManager(store).load_profile()
                memory_info["preferences"] = len(profile.general) + len(profile.patterns)
                dm = DecisionManager(store)
                projects = dm.list_projects()
                memory_info["decision_projects"] = len(projects)
                total_decisions = sum(len(dm.load_decisions(p).decisions) for p in projects)
                memory_info["decisions"] = total_decisions
        except Exception:
            pass

        # Check summarization (Ollama)
        summarization_info = {"available": False}
        try:
            from cerberus.summarization.facade import get_summarization_facade
            facade = get_summarization_facade()
            summarization_info["available"] = facade.llm_client.is_available()
            if not summarization_info["available"]:
                summarization_info["hint"] = "Start Ollama: ollama serve"
        except Exception:
            pass

        return {
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
            "summarization": summarization_info,
            "recommendations": recommendations if recommendations else None,
        }
