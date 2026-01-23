"""Memory system tools - cross-project developer memory."""
from typing import Any, Dict, List, Optional
from pathlib import Path

from cerberus.memory.store import MemoryStore
from cerberus.memory.profile import ProfileManager, Profile
from cerberus.memory.decisions import DecisionManager
from cerberus.memory.corrections import CorrectionManager
from cerberus.memory.context import ContextGenerator
from cerberus.memory.extract import GitExtractor

# Phase 13: Adaptive Learning Memory System (SQLite FTS5)
from cerberus.memory.search import MemorySearchEngine, SearchQuery


def register(mcp):
    # Lazy singletons to avoid repeated disk I/O
    _store: Optional[MemoryStore] = None
    _profile: Optional[ProfileManager] = None
    _decisions: Optional[DecisionManager] = None
    _corrections: Optional[CorrectionManager] = None
    _context: Optional[ContextGenerator] = None
    _extractor: Optional[GitExtractor] = None

    def get_store() -> MemoryStore:
        nonlocal _store
        if _store is None:
            _store = MemoryStore()
        return _store

    def get_profile() -> ProfileManager:
        nonlocal _profile
        if _profile is None:
            _profile = ProfileManager(get_store())
        return _profile

    def get_decisions() -> DecisionManager:
        nonlocal _decisions
        if _decisions is None:
            _decisions = DecisionManager(get_store())
        return _decisions

    def get_corrections() -> CorrectionManager:
        nonlocal _corrections
        if _corrections is None:
            _corrections = CorrectionManager(get_store())
        return _corrections

    def get_context() -> ContextGenerator:
        nonlocal _context
        if _context is None:
            _context = ContextGenerator(get_store())
        return _context

    def get_extractor() -> GitExtractor:
        nonlocal _extractor
        if _extractor is None:
            _extractor = GitExtractor(get_store())
        return _extractor

    @mcp.tool()
    def memory_learn(
        category: str,
        content: str,
        project: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
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
        """
        metadata = metadata or {}

        if category == "preference":
            # Prefer the ProfileManager's parser to keep consistency
            result = get_profile().learn(content)
            if result.get("success"):
                return {"status": "learned", "category": "preference", **result}

            # Fallback: append to general list if parsing failed
            profile = get_profile().load_profile()
            if not profile.general:
                profile.general = []
            profile.general.append(content)
            get_profile().save_profile(profile)
            return {"status": "learned", "category": "preference", "content": content}

        if category == "decision":
            dm = get_decisions()
            if project is None:
                project = dm.detect_project_name()
            if project is None:
                return {
                    "status": "error",
                    "message": "Could not detect project name. Provide 'project' parameter.",
                }

            # If topic provided, prepend for clearer parsing
            decision_text = (
                f"{metadata.get('topic')}: {content}"
                if metadata.get("topic")
                else content
            )
            result = dm.learn_decision(
                decision_text,
                project=project,
                rationale=metadata.get("rationale", ""),
            )
            if result.get("success"):
                return {
                    "status": "learned",
                    "category": "decision",
                    "project": project,
                    "decision": result.get("decision"),
                }
            return {"status": "error", "message": result.get("message", "Unknown error")}

        if category == "correction":
            cm = get_corrections()
            text = metadata.get("context", content) if metadata else content
            note = metadata.get("note") if metadata else None
            result = cm.learn_correction(text, note=note)
            if result.get("success"):
                return {
                    "status": "learned",
                    "category": "correction",
                    "correction": result.get("correction"),
                }
            return {"status": "error", "message": result.get("message", "Unknown error")}

        return {
            "status": "error",
            "message": f"Unknown category: {category}. Use: preference, decision, correction",
        }

    @mcp.tool()
    def memory_show(
        category: Optional[str] = None,
        project: Optional[str] = None,
    ) -> dict:
        """
        Display stored memory.

        Args:
            category: Filter by type - "preferences", "decisions", "corrections", or None for all
            project: Project name for decisions (auto-detected if not provided)

        Returns:
            Stored memory contents
        """
        result: Dict[str, Any] = {}

        if category is None or category == "preferences":
            profile = get_profile().load_profile()
            result["preferences"] = profile.to_dict()

        if category is None or category == "decisions":
            dm = get_decisions()
            if project is None:
                project = dm.detect_project_name()
            if project:
                decisions = dm.load_decisions(project)
                result["decisions"] = {
                    "project": project,
                    "items": [d.to_dict() for d in decisions.decisions],
                }
            else:
                result["decisions"] = {"projects": dm.list_projects()}

        if category is None or category == "corrections":
            cm = get_corrections()
            corrections = cm.load_corrections()
            result["corrections"] = [c.to_dict() for c in corrections.corrections]

        return result

    @mcp.tool()
    def memory_context(
        project: Optional[str] = None,
        compact: bool = True,
        include_decisions: bool = True,
        include_preferences: bool = True,
        include_corrections: bool = True,
    ) -> str:
        """
        Generate context for prompt injection.
        """
        cg = get_context()
        dm = get_decisions()

        if project is None:
            project = dm.detect_project_name()

        # ContextGenerator does not currently support selective exclusion;
        # the include_* flags are accepted for forward compatibility.
        return cg.generate_context(project=project, compact=compact)

    @mcp.tool()
    def memory_extract(path: str = ".", lookback_days: int = 30) -> dict:
        """
        Extract patterns from git history.

        Analyzes git commits to automatically learn coding patterns,
        naming conventions, and project-specific decisions.

        Args:
            path: Path to git repository (default: current directory)
            lookback_days: How many days of history to analyze (default: 30)

        Returns:
            dict with extraction results including learned patterns and statistics
        """
        extractor = get_extractor()
        since = f"{lookback_days} days ago"
        target = Path(path).resolve()
        if not target.exists():
            return {"success": False, "message": f"Path not found: {path}"}

        prev_cwd = Path.cwd()
        try:
            import os

            os.chdir(target)
            return extractor.extract_from_git(since=since)
        finally:
            os.chdir(prev_cwd)

    @mcp.tool()
    def memory_forget(
        category: str,
        identifier: str,
        project: Optional[str] = None,
    ) -> dict:
        """
        Remove a specific memory entry.

        Deletes a previously learned preference, decision, or correction
        from memory.

        Args:
            category: Type of memory - "preference", "decision", or "correction"
            identifier: The content or ID of the entry to remove
            project: Project name (required for decisions, auto-detected if not provided)

        Returns:
            dict with:
            - status: "forgotten" if removed, "not_found" if entry doesn't exist, or "error"
            - category: The category that was searched
            - message: Description of result
        """
        if category == "preference":
            profile = get_profile().load_profile()
            if profile.general and identifier in profile.general:
                profile.general.remove(identifier)
                get_profile().save_profile(profile)
                return {"status": "forgotten", "category": "preference"}
            return {"status": "not_found", "category": "preference"}

        if category == "decision":
            dm = get_decisions()
            if project is None:
                project = dm.detect_project_name()
            if project:
                result = dm.forget_decision(identifier, project=project)
                return {
                    "status": "forgotten" if result.get("success") else "not_found",
                    "category": "decision",
                    "message": result.get("message"),
                }
            return {"status": "error", "message": "Project not specified"}

        if category == "correction":
            cm = get_corrections()
            result = cm.forget_correction(identifier)
            return {
                "status": "forgotten" if result.get("success") else "not_found",
                "category": "correction",
                "message": result.get("message"),
            }

        return {"status": "error", "message": f"Unknown category: {category}"}

    @mcp.tool()
    def memory_stats() -> dict:
        """
        Get memory storage statistics.

        Shows counts of stored preferences, decisions, and corrections,
        along with storage paths.

        Returns:
            dict with:
            - preferences: Count of stored preferences
            - decisions: Count of stored decisions
            - decision_projects: Number of projects with decisions
            - corrections: Count of stored corrections
            - total_entries: Total memory entries
            - paths: Storage file paths for each category
        """
        store = get_store()
        profile = get_profile().load_profile()
        dm = get_decisions()
        cm = get_corrections()

        pref_count = 0
        if profile.coding_style:
            pref_count += len(profile.coding_style)
        if profile.naming_conventions:
            pref_count += len(profile.naming_conventions)
        if profile.anti_patterns:
            pref_count += len(profile.anti_patterns)
        if profile.general:
            pref_count += len(profile.general)

        projects = dm.list_projects()
        decision_count = 0
        for proj in projects:
            decisions = dm.load_decisions(proj)
            decision_count += len(decisions.decisions)

        corrections = cm.load_corrections()
        correction_count = len(corrections.corrections)

        return {
            "preferences": pref_count,
            "decisions": decision_count,
            "decision_projects": len(projects),
            "corrections": correction_count,
            "total_entries": pref_count + decision_count + correction_count,
            "paths": {
                "profile": str(store.profile_path),
                "corrections": str(store.corrections_path),
                "projects": [str(store.project_path(p)) for p in projects],
            },
        }

    @mcp.tool()
    def memory_export(output_path: Optional[str] = None) -> dict:
        """
        Export all memory for backup or sharing.

        Creates a JSON file containing all preferences, decisions, and
        corrections. Useful for backup or sharing between machines.

        Args:
            output_path: Path for export file (default: cerberus-memory-export-YYYYMMDD.json)

        Returns:
            dict with:
            - status: "exported" on success
            - path: Path where export was saved
            - entries: Counts of exported {profile, decisions, corrections}
        """
        import json
        from datetime import datetime

        if output_path is None:
            output_path = f"cerberus-memory-export-{datetime.now().strftime('%Y%m%d')}.json"

        profile = get_profile().load_profile()
        dm = get_decisions()
        cm = get_corrections()

        export_data = {
            "exported_at": datetime.now().isoformat(),
            "profile": profile.to_dict(),
            "decisions": {},
            "corrections": cm.load_corrections().to_dict(),
        }

        for proj in dm.list_projects():
            export_data["decisions"][proj] = dm.load_decisions(proj).to_dict()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

        return {
            "status": "exported",
            "path": output_path,
            "entries": {
                "profile": 1,
                "decisions": len(export_data["decisions"]),
                "corrections": len(export_data["corrections"].get("corrections", [])),
            },
        }

    @mcp.tool()
    def memory_import(input_path: str, merge: bool = True) -> dict:
        """
        Import memory from backup.

        Restores previously exported memory. Can either merge with existing
        memory or replace it entirely.

        Args:
            input_path: Path to the export JSON file to import
            merge: If True, merge with existing memory. If False, replace existing.

        Returns:
            dict with:
            - status: "imported" on success
            - merged: Whether merge mode was used
            - counts: Number of imported {profile, decisions, corrections}
        """
        import json

        with open(input_path, "r", encoding="utf-8") as f:
            import_data = json.load(f)

        imported = {"profile": 0, "decisions": 0, "corrections": 0}

        # Import profile
        if "profile" in import_data:
            imported_profile = Profile.from_dict(import_data["profile"])
            if merge:
                existing = get_profile().load_profile()
                # Merge general preferences
                if imported_profile.general:
                    existing.general = list(
                        {*(existing.general or []), *imported_profile.general}
                    )
                # Merge coding style, naming, anti-patterns, languages shallowly
                existing.coding_style.update(imported_profile.coding_style)
                existing.naming_conventions.update(imported_profile.naming_conventions)
                existing.anti_patterns = list(
                    {*(existing.anti_patterns or []), *imported_profile.anti_patterns}
                )
                existing.languages.update(imported_profile.languages)
                get_profile().save_profile(existing)
            else:
                get_profile().save_profile(imported_profile)
            imported["profile"] = 1

        # Import decisions
        if "decisions" in import_data:
            dm = get_decisions()
            for proj, proj_data in import_data["decisions"].items():
                for decision in proj_data.get("decisions", []):
                    dm.learn_decision(
                        decision.get("decision", ""),
                        project=proj,
                        rationale=decision.get("rationale", ""),
                    )
                    imported["decisions"] += 1

        # Import corrections
        if "corrections" in import_data:
            cm = get_corrections()
            for correction in import_data["corrections"].get("corrections", []):
                cm.learn_correction(
                    correction.get("correction", "")
                    or correction.get("pattern", "")
                    or "",
                    note=correction.get("note", ""),
                )
                imported["corrections"] += 1

        return {
            "status": "imported",
            "merged": merge,
            "counts": imported,
        }

    @mcp.tool()
    def memory_search(
        query: str,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> dict:
        """
        Search memories by text query using FTS5 full-text search.

        Phase 13: Adaptive Learning Memory System
        Uses SQLite FTS5 for efficient text search across memories.

        Args:
            query: Text to search for
            scope: Filter by scope (universal, language:X, project:Y)
            category: Filter by category (preference, rule, correction, decision)
            limit: Max results (default 10)

        Returns:
            Search results with relevance scores
        """
        db_path = Path.home() / ".cerberus" / "memory.db"

        if not db_path.exists():
            return {
                "status": "error",
                "message": "Adaptive memory database not found. No memories have been stored yet."
            }

        search_engine = MemorySearchEngine(db_path)

        search_query = SearchQuery(
            text=query,
            scope=scope,
            category=category,
            limit=limit,
            order_by="relevance"
        )

        try:
            results = search_engine.search(search_query)

            return {
                "status": "ok",
                "query": query,
                "total_results": len(results),
                "results": [
                    {
                        "content": r.content,
                        "scope": r.scope,
                        "category": r.category,
                        "relevance": round(r.relevance_score, 2),
                        "snippet": r.match_context,
                        "confidence": r.confidence,
                        "created_at": r.created_at,
                        "access_count": r.access_count
                    }
                    for r in results
                ]
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Search failed: {str(e)}"
            }
