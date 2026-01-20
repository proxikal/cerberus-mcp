# Phase 3: Full Memory System Tools

## Overview

Implement all memory tools - the core value proposition of Cerberus. Cross-project developer memory that persists preferences, architectural decisions, and learned corrections.

## Goals

- All 8 memory tools working
- Global memory (preferences, corrections) shared across projects
- Per-project memory (decisions) isolated by project
- Context generation for prompt injection
- Pattern extraction from git history

## Memory Architecture Recap

```
~/.cerberus/memory/           # Global (cross-project)
├── profile.json              # Developer coding style preferences
└── corrections.json          # Learned mistakes/patterns

.cerberus/                    # Per-project
└── decisions/
    └── {project-name}.json   # Architectural decisions
```

## Tasks

### 3.1 Create Memory Tools Module

**File: `src/cerberus/mcp/tools/memory.py`**
```python
"""Memory system tools - cross-project developer memory."""
from typing import Dict, List, Optional, Any

from cerberus.memory.store import MemoryStore
from cerberus.memory.profile import ProfileManager
from cerberus.memory.decisions import DecisionManager
from cerberus.memory.corrections import CorrectionManager
from cerberus.memory.context import ContextGenerator
from cerberus.memory.extract import PatternExtractor


def register(mcp):

    # Initialize managers (lazy, singleton pattern)
    _store = None
    _profile = None
    _decisions = None
    _corrections = None
    _context = None
    _extractor = None

    def get_store():
        nonlocal _store
        if _store is None:
            _store = MemoryStore()
        return _store

    def get_profile():
        nonlocal _profile
        if _profile is None:
            _profile = ProfileManager(get_store())
        return _profile

    def get_decisions():
        nonlocal _decisions
        if _decisions is None:
            _decisions = DecisionManager(get_store())
        return _decisions

    def get_corrections():
        nonlocal _corrections
        if _corrections is None:
            _corrections = CorrectionManager(get_store())
        return _corrections

    def get_context():
        nonlocal _context
        if _context is None:
            _context = ContextGenerator(get_store())
        return _context

    def get_extractor():
        nonlocal _extractor
        if _extractor is None:
            _extractor = PatternExtractor()
        return _extractor

    @mcp.tool()
    def memory_learn(
        category: str,
        content: str,
        project: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> dict:
        """
        Teach Session Memory something new.

        Args:
            category: Type of memory - "preference", "decision", "correction"
            content: What to remember
            project: Project name (required for decisions, auto-detected if not provided)
            metadata: Additional structured data (topic, rationale, etc.)

        Returns:
            Confirmation with memory ID

        Examples:
            memory_learn("preference", "Prefer early returns over nested conditionals")
            memory_learn("decision", "Use SQLite for local storage", project="cerberus",
                        metadata={"topic": "Database", "rationale": "Simple, no server"})
            memory_learn("correction", "Don't use print() for logging, use loguru")
        """
        metadata = metadata or {}

        if category == "preference":
            profile = get_profile().load_profile()
            # Add to general preferences
            if not profile.general:
                profile.general = []
            profile.general.append(content)
            get_profile().save_profile(profile)
            return {"status": "learned", "category": "preference", "content": content}

        elif category == "decision":
            dm = get_decisions()
            if project is None:
                project = dm.detect_project_name()
            if project is None:
                return {"status": "error", "message": "Could not detect project name. Provide 'project' parameter."}

            decision_id = dm.add_decision(
                project=project,
                topic=metadata.get("topic", "General"),
                decision=content,
                rationale=metadata.get("rationale", ""),
                confidence=metadata.get("confidence", "medium")
            )
            return {"status": "learned", "category": "decision", "project": project, "id": decision_id}

        elif category == "correction":
            cm = get_corrections()
            correction_id = cm.add_correction(
                mistake=metadata.get("mistake", ""),
                correction=content,
                context=metadata.get("context", "")
            )
            return {"status": "learned", "category": "correction", "id": correction_id}

        else:
            return {"status": "error", "message": f"Unknown category: {category}. Use: preference, decision, correction"}

    @mcp.tool()
    def memory_show(
        category: Optional[str] = None,
        project: Optional[str] = None
    ) -> dict:
        """
        Display stored memory.

        Args:
            category: Filter by type - "preferences", "decisions", "corrections", or None for all
            project: Project name for decisions (auto-detected if not provided)

        Returns:
            Stored memory contents
        """
        result = {}

        if category is None or category == "preferences":
            profile = get_profile().load_profile()
            result["preferences"] = {
                "coding_style": profile.coding_style or {},
                "naming_conventions": profile.naming_conventions or {},
                "anti_patterns": profile.anti_patterns or [],
                "general": profile.general or []
            }

        if category is None or category == "decisions":
            dm = get_decisions()
            if project is None:
                project = dm.detect_project_name()
            if project:
                decisions = dm.load_decisions(project)
                result["decisions"] = {
                    "project": project,
                    "items": [d.model_dump() for d in decisions.decisions]
                }
            else:
                # List all projects
                projects = dm.list_projects()
                result["decisions"] = {"projects": projects}

        if category is None or category == "corrections":
            cm = get_corrections()
            corrections = cm.load_corrections()
            result["corrections"] = [c.model_dump() for c in corrections.corrections]

        return result

    @mcp.tool()
    def memory_context(
        project: Optional[str] = None,
        compact: bool = True,
        include_decisions: bool = True,
        include_preferences: bool = True,
        include_corrections: bool = True
    ) -> str:
        """
        Generate context for prompt injection.

        This is the primary way to use Session Memory - inject this into prompts
        to give the AI context about developer preferences and project decisions.

        Args:
            project: Project name (auto-detected if not provided)
            compact: If True, minimal format. If False, verbose.
            include_decisions: Include project decisions
            include_preferences: Include developer preferences
            include_corrections: Include learned corrections

        Returns:
            Formatted context string ready for prompt injection
        """
        cg = get_context()
        dm = get_decisions()

        if project is None:
            project = dm.detect_project_name()

        return cg.generate_context(
            project=project,
            compact=compact,
            include_decisions=include_decisions,
            include_preferences=include_preferences,
            include_corrections=include_corrections
        )

    @mcp.tool()
    def memory_extract(
        path: str = ".",
        lookback_days: int = 30
    ) -> dict:
        """
        Extract patterns from git history.

        Analyzes recent commits to learn coding patterns, common changes,
        and project conventions.

        Args:
            path: Repository path
            lookback_days: How far back to analyze

        Returns:
            Extracted patterns with confidence scores
        """
        extractor = get_extractor()
        patterns = extractor.extract_from_git(path, lookback_days)

        return {
            "patterns_found": len(patterns),
            "patterns": [p.model_dump() for p in patterns]
        }

    @mcp.tool()
    def memory_forget(
        category: str,
        identifier: str,
        project: Optional[str] = None
    ) -> dict:
        """
        Remove a specific memory entry.

        Args:
            category: Type - "preference", "decision", "correction"
            identifier: ID or content to remove
            project: Project name (for decisions)

        Returns:
            Confirmation of removal
        """
        if category == "preference":
            profile = get_profile().load_profile()
            if profile.general and identifier in profile.general:
                profile.general.remove(identifier)
                get_profile().save_profile(profile)
                return {"status": "forgotten", "category": "preference"}
            return {"status": "not_found", "category": "preference"}

        elif category == "decision":
            dm = get_decisions()
            if project is None:
                project = dm.detect_project_name()
            if project:
                success = dm.forget_decision(project, identifier)
                return {"status": "forgotten" if success else "not_found", "category": "decision"}
            return {"status": "error", "message": "Project not specified"}

        elif category == "correction":
            cm = get_corrections()
            success = cm.forget_correction(identifier)
            return {"status": "forgotten" if success else "not_found", "category": "correction"}

        return {"status": "error", "message": f"Unknown category: {category}"}

    @mcp.tool()
    def memory_stats() -> dict:
        """
        Get memory storage statistics.

        Returns:
            Storage sizes, entry counts, and health info
        """
        store = get_store()
        profile = get_profile().load_profile()
        dm = get_decisions()
        cm = get_corrections()

        # Count preferences
        pref_count = 0
        if profile.coding_style:
            pref_count += len(profile.coding_style)
        if profile.naming_conventions:
            pref_count += len(profile.naming_conventions)
        if profile.anti_patterns:
            pref_count += len(profile.anti_patterns)
        if profile.general:
            pref_count += len(profile.general)

        # Count decisions across projects
        projects = dm.list_projects()
        decision_count = 0
        for proj in projects:
            decisions = dm.load_decisions(proj)
            decision_count += len(decisions.decisions)

        # Count corrections
        corrections = cm.load_corrections()
        correction_count = len(corrections.corrections)

        return {
            "preferences": pref_count,
            "decisions": decision_count,
            "decision_projects": len(projects),
            "corrections": correction_count,
            "total_entries": pref_count + decision_count + correction_count
        }

    @mcp.tool()
    def memory_export(
        output_path: Optional[str] = None
    ) -> dict:
        """
        Export all memory for backup or sharing.

        Args:
            output_path: Where to save export (default: cerberus-memory-export.json)

        Returns:
            Export path and entry counts
        """
        import json
        from pathlib import Path
        from datetime import datetime

        if output_path is None:
            output_path = f"cerberus-memory-export-{datetime.now().strftime('%Y%m%d')}.json"

        profile = get_profile().load_profile()
        dm = get_decisions()
        cm = get_corrections()

        export_data = {
            "exported_at": datetime.now().isoformat(),
            "profile": profile.model_dump(),
            "decisions": {},
            "corrections": cm.load_corrections().model_dump()
        }

        for proj in dm.list_projects():
            export_data["decisions"][proj] = dm.load_decisions(proj).model_dump()

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        return {
            "status": "exported",
            "path": output_path,
            "entries": {
                "profile": 1,
                "decisions": len(export_data["decisions"]),
                "corrections": len(export_data["corrections"].get("corrections", []))
            }
        }

    @mcp.tool()
    def memory_import(
        input_path: str,
        merge: bool = True
    ) -> dict:
        """
        Import memory from backup.

        Args:
            input_path: Path to export file
            merge: If True, merge with existing. If False, replace.

        Returns:
            Import statistics
        """
        import json
        from pathlib import Path

        with open(input_path, "r") as f:
            import_data = json.load(f)

        imported = {"profile": 0, "decisions": 0, "corrections": 0}

        # Import profile
        if "profile" in import_data:
            from cerberus.memory.profile import DeveloperProfile
            imported_profile = DeveloperProfile(**import_data["profile"])

            if merge:
                existing = get_profile().load_profile()
                # Merge general preferences
                if imported_profile.general:
                    existing.general = list(set((existing.general or []) + imported_profile.general))
                get_profile().save_profile(existing)
            else:
                get_profile().save_profile(imported_profile)
            imported["profile"] = 1

        # Import decisions
        if "decisions" in import_data:
            dm = get_decisions()
            for proj, proj_data in import_data["decisions"].items():
                for decision in proj_data.get("decisions", []):
                    dm.add_decision(
                        project=proj,
                        topic=decision.get("topic", "General"),
                        decision=decision.get("decision", ""),
                        rationale=decision.get("rationale", ""),
                        confidence=decision.get("confidence", "medium")
                    )
                    imported["decisions"] += 1

        # Import corrections
        if "corrections" in import_data:
            cm = get_corrections()
            for correction in import_data["corrections"].get("corrections", []):
                cm.add_correction(
                    mistake=correction.get("mistake", ""),
                    correction=correction.get("correction", ""),
                    context=correction.get("context", "")
                )
                imported["corrections"] += 1

        return {
            "status": "imported",
            "merged": merge,
            "counts": imported
        }
```

### 3.2 Update Server Registration

**Update `src/cerberus/mcp/server.py`:**
```python
"""FastMCP server setup and tool registration."""
from fastmcp import FastMCP

from .tools import search, symbols, reading, indexing, memory

mcp = FastMCP("cerberus")

def create_server():
    """Create and configure the MCP server."""
    # Read tools
    search.register(mcp)
    symbols.register(mcp)
    reading.register(mcp)

    # Index management
    indexing.register(mcp)

    # Memory system (core value)
    memory.register(mcp)

    return mcp

def run_server():
    """Run the MCP server."""
    server = create_server()
    server.run()
```

### 3.3 Add Blueprint Tool

**File: `src/cerberus/mcp/tools/structure.py`**
```python
"""Structure and blueprint tools."""
from typing import Optional
from pathlib import Path

from cerberus.blueprint import BlueprintGenerator, BlueprintRequest
from ..index_manager import get_index_manager


def register(mcp):
    @mcp.tool()
    def blueprint(
        path: str,
        show_deps: bool = False,
        show_meta: bool = False,
        format: str = "tree"
    ) -> str:
        """
        Generate structural blueprint of a file or directory.

        Shows symbol hierarchy, line ranges, and optional overlays
        for dependencies and complexity metrics.

        Args:
            path: File or directory path
            show_deps: Include dependency information
            show_meta: Include complexity metrics
            format: Output format - "tree" or "json"

        Returns:
            Formatted blueprint
        """
        manager = get_index_manager()
        index = manager.get_index()

        if not hasattr(index, '_store'):
            return {"error": "Blueprint requires SQLite index"}

        conn = index._store._get_connection()

        try:
            request = BlueprintRequest(
                file_path=str(Path(path).resolve()),
                show_deps=show_deps,
                show_meta=show_meta,
                output_format=format
            )

            generator = BlueprintGenerator(conn)
            blueprint = generator.generate(request)

            return generator.format_output(blueprint, format)
        finally:
            conn.close()
```

## Files to Create/Modify

```
src/cerberus/mcp/
├── server.py           # MODIFIED - add memory registration
└── tools/
    ├── memory.py       # NEW - all 8 memory tools
    └── structure.py    # NEW - blueprint tool
```

## Acceptance Criteria

- [ ] `memory_learn` stores preferences, decisions, and corrections
- [ ] `memory_show` retrieves stored memory by category
- [ ] `memory_context` generates injectable prompt context
- [ ] `memory_extract` analyzes git history for patterns
- [ ] `memory_forget` removes specific entries
- [ ] `memory_stats` returns accurate counts
- [ ] `memory_export` creates valid backup file
- [ ] `memory_import` restores from backup (merge and replace modes)
- [ ] Global memory persists in ~/.cerberus/memory/
- [ ] Project decisions isolated by project name
- [ ] Auto-detection of project name works

## Dependencies

- Phase 1 completed (MCP server skeleton)
- Phase 2 completed (IndexManager for blueprint tool)

## Notes

- Memory is the differentiating feature - test thoroughly
- Ensure backwards compatibility with existing memory files
- Context generation should be fast - agents call it frequently
- Consider adding memory validation (e.g., max size limits)
