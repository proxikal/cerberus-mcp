"""Memory system tools - cross-project developer memory."""
from typing import Any, Dict, List, Optional
from pathlib import Path

from cerberus.memory.store import MemoryStore
from cerberus.memory.profile import ProfileManager, Profile
from cerberus.memory.decisions import DecisionManager
from cerberus.memory.corrections import CorrectionManager
from cerberus.memory.context import ContextGenerator  # OLD system (kept for backwards compat)
from cerberus.memory.extract import GitExtractor

# Phase 7: NEW Adaptive Memory System (Context Injection)
from cerberus.memory.context_injector import inject_startup_context, inject_query_context

# Phase 13: Adaptive Learning Memory System (SQLite FTS5)
from cerberus.memory.search import MemorySearchEngine, SearchQuery

# Phase 5 (Version 2): SQLite Storage
from cerberus.memory.storage import MemoryStorage
from cerberus.memory.proposal_engine import MemoryProposal

# Phase 6 (Version 2): SQLite Retrieval
from cerberus.memory.retrieval import MemoryRetrieval


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
        import uuid
        from datetime import datetime

        metadata = metadata or {}

        # Determine scope based on category and project
        if category == "preference":
            scope = "universal"
        elif category == "decision":
            if project is None:
                # Auto-detect project from cwd
                from pathlib import Path
                project = Path.cwd().name
            scope = f"project:{project}"
        elif category == "correction":
            scope = "universal"
        else:
            return {
                "status": "error",
                "message": f"Unknown category: {category}. Use: preference, decision, correction",
            }

        # Create memory proposal
        memory_id = str(uuid.uuid4())
        proposal = MemoryProposal(
            id=memory_id,
            category=category,
            scope=scope,
            content=content,
            rationale=metadata.get("rationale", "User-provided memory via memory_learn"),
            source_variants=[],
            confidence=1.0,  # User-provided = maximum confidence
            priority=1
        )

        # Store to SQLite
        try:
            storage = MemoryStorage()
            storage.store(proposal)
            return {
                "status": "learned",
                "category": category,
                "scope": scope,
                "memory_id": memory_id,
                "content": content
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to store memory: {str(e)}"
            }

    @mcp.tool()
    def memory_show(
        category: Optional[str] = None,
        project: Optional[str] = None,
    ) -> dict:
        """
        Display stored memory.

        Args:
            category: Filter by type - "preference", "decision", "correction", or None for all
            project: Project name for decisions (auto-detected if not provided)

        Returns:
            Stored memory contents from SQLite
        """
        import sqlite3
        from pathlib import Path

        db_path = Path.home() / ".cerberus" / "memory.db"

        if not db_path.exists():
            return {"status": "empty", "message": "No memories stored yet"}

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        try:
            # Build query with filters
            query = "SELECT id, category, scope, metadata, created_at, last_accessed, access_count FROM memory_store WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                params.append(category)

            if project:
                query += " AND scope LIKE ?"
                params.append(f"project:{project}%")

            query += " ORDER BY created_at DESC"

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            # Also get content from FTS table
            memories = []
            for row in rows:
                content_cursor = conn.execute(
                    "SELECT content FROM memory_fts WHERE id = ?",
                    (row["id"],)
                )
                content_row = content_cursor.fetchone()

                memories.append({
                    "id": row["id"],
                    "category": row["category"],
                    "scope": row["scope"],
                    "content": content_row["content"] if content_row else "",
                    "created_at": row["created_at"],
                    "last_accessed": row["last_accessed"],
                    "access_count": row["access_count"]
                })

            return {
                "status": "ok",
                "total": len(memories),
                "memories": memories
            }

        finally:
            conn.close()

    @mcp.tool()
    def memory_context(
        query: Optional[str] = None,
        project: Optional[str] = None,
        compact: bool = True,
        include_decisions: bool = True,
        include_preferences: bool = True,
        include_corrections: bool = True,
    ) -> dict:
        """
        Generate context for prompt injection.

        Phase 7: NEW Adaptive Memory System
        - Auto-injects at session start (1200 tokens)
        - On-demand queries during work (500 tokens per query)

        Args:
            query: Optional query string for on-demand retrieval
            project: Optional project name (auto-detected if None)
            compact: Compact format (accepted for backwards compat)
            include_*: Filter flags (accepted for backwards compat)

        Returns:
            dict with memory context string
        """
        from pathlib import Path

        # Determine base directory
        base_dir = Path.home() / ".cerberus"

        # If query provided, use on-demand injection
        if query:
            result = inject_query_context(
                query=query,
                base_dir=str(base_dir),
                min_relevance=0.3
            )
        else:
            # Session start injection
            result = inject_startup_context(
                base_dir=str(base_dir),
                min_relevance=0.5
            )

        return {"result": result}

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
        # TODO: GitExtractor needs refactoring to use SQLite instead of JSON
        # Currently disabled until GitExtractor is updated to work with MemoryStorage
        return {
            "success": False,
            "message": "memory_extract is temporarily disabled - GitExtractor needs SQLite migration"
        }

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
            identifier: The content or ID of the entry to remove (can be memory ID or content text)
            project: Project name (required for decisions, auto-detected if not provided)

        Returns:
            dict with:
            - status: "forgotten" if removed, "not_found" if entry doesn't exist, or "error"
            - category: The category that was searched
            - message: Description of result
        """
        try:
            storage = MemoryStorage()

            # Try to delete by ID first
            if storage.delete_memory(identifier):
                return {
                    "status": "forgotten",
                    "category": category,
                    "memory_id": identifier,
                    "message": "Memory deleted successfully"
                }

            # If not found by ID, search by content
            import sqlite3
            from pathlib import Path

            db_path = Path.home() / ".cerberus" / "memory.db"
            conn = sqlite3.connect(str(db_path))

            # Search for memory by content
            cursor = conn.execute(
                """SELECT m.id FROM memory_store m
                   JOIN memory_fts f ON m.id = f.id
                   WHERE m.category = ? AND f.content LIKE ?""",
                (category, f"%{identifier}%")
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                memory_id = row[0]
                if storage.delete_memory(memory_id):
                    return {
                        "status": "forgotten",
                        "category": category,
                        "memory_id": memory_id,
                        "message": "Memory deleted successfully"
                    }

            return {
                "status": "not_found",
                "category": category,
                "message": f"No {category} memory found matching '{identifier}'"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete memory: {str(e)}"
            }

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
            - database_path: Path to SQLite database
            - database_size_kb: Size of database file
        """
        import sqlite3
        from pathlib import Path

        db_path = Path.home() / ".cerberus" / "memory.db"

        if not db_path.exists():
            return {
                "preferences": 0,
                "decisions": 0,
                "decision_projects": 0,
                "corrections": 0,
                "total_entries": 0,
                "database_path": str(db_path),
                "database_size_kb": 0
            }

        conn = sqlite3.connect(str(db_path))

        # Count by category
        cursor = conn.execute("SELECT category, COUNT(*) FROM memory_store GROUP BY category")
        counts = dict(cursor.fetchall())

        # Count unique projects
        cursor = conn.execute("SELECT COUNT(DISTINCT scope) FROM memory_store WHERE scope LIKE 'project:%'")
        project_count = cursor.fetchone()[0]

        # Total count
        cursor = conn.execute("SELECT COUNT(*) FROM memory_store")
        total = cursor.fetchone()[0]

        conn.close()

        # Get database file size
        db_size_kb = db_path.stat().st_size / 1024

        return {
            "preferences": counts.get("preference", 0),
            "decisions": counts.get("decision", 0),
            "decision_projects": project_count,
            "corrections": counts.get("correction", 0),
            "total_entries": total,
            "database_path": str(db_path),
            "database_size_kb": round(db_size_kb, 2)
        }

    @mcp.tool()
    def memory_export(output_path: Optional[str] = None) -> dict:
        """
        Export all memory for backup or sharing.

        Creates a JSON file containing all memories from SQLite database.
        Useful for backup or sharing between machines.

        Args:
            output_path: Path for export file (default: cerberus-memory-export-YYYYMMDD.json)

        Returns:
            dict with:
            - status: "exported" on success
            - path: Path where export was saved
            - entries: Count of exported memories by category
        """
        import json
        import sqlite3
        from datetime import datetime
        from pathlib import Path

        if output_path is None:
            output_path = f"cerberus-memory-export-{datetime.now().strftime('%Y%m%d')}.json"

        db_path = Path.home() / ".cerberus" / "memory.db"

        if not db_path.exists():
            return {
                "status": "error",
                "message": "No memory database found"
            }

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        # Export all memories
        cursor = conn.execute("""
            SELECT m.id, m.category, m.scope, m.confidence, m.created_at,
                   m.last_accessed, m.access_count, m.metadata,
                   f.content
            FROM memory_store m
            JOIN memory_fts f ON m.id = f.id
            ORDER BY m.created_at
        """)

        memories = []
        counts = {"preference": 0, "decision": 0, "correction": 0}

        for row in cursor.fetchall():
            memory = {
                "id": row["id"],
                "category": row["category"],
                "scope": row["scope"],
                "content": row["content"],
                "confidence": row["confidence"],
                "created_at": row["created_at"],
                "last_accessed": row["last_accessed"],
                "access_count": row["access_count"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
            }
            memories.append(memory)
            counts[row["category"]] = counts.get(row["category"], 0) + 1

        conn.close()

        export_data = {
            "exported_at": datetime.now().isoformat(),
            "version": "2.0",
            "source": "cerberus-memory-sqlite",
            "memories": memories
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)

        return {
            "status": "exported",
            "path": output_path,
            "entries": counts,
            "total": len(memories)
        }

    @mcp.tool()
    def memory_import(input_path: str, merge: bool = True) -> dict:
        """
        Import memory from backup.

        Restores previously exported memory into SQLite database.
        Can either merge with existing memory or replace it entirely.

        Args:
            input_path: Path to the export JSON file to import
            merge: If True, merge with existing memory. If False, replace existing.

        Returns:
            dict with:
            - status: "imported" on success
            - merged: Whether merge mode was used
            - counts: Number of imported memories by category
        """
        import json
        import sqlite3
        from pathlib import Path

        with open(input_path, "r", encoding="utf-8") as f:
            import_data = json.load(f)

        if "memories" not in import_data:
            return {
                "status": "error",
                "message": "Invalid export format - missing 'memories' field"
            }

        db_path = Path.home() / ".cerberus" / "memory.db"
        conn = sqlite3.connect(str(db_path))

        try:
            if not merge:
                # Clear existing memories
                conn.execute("DELETE FROM memory_store")
                conn.execute("DELETE FROM memory_fts")

            counts = {"preference": 0, "decision": 0, "correction": 0}

            for memory in import_data["memories"]:
                # Skip if already exists (based on ID) when merging
                if merge:
                    cursor = conn.execute("SELECT id FROM memory_store WHERE id = ?", (memory["id"],))
                    if cursor.fetchone():
                        continue

                # Insert into memory_store
                conn.execute("""
                    INSERT INTO memory_store
                    (id, category, scope, confidence, created_at, last_accessed, access_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory["id"],
                    memory["category"],
                    memory["scope"],
                    memory["confidence"],
                    memory["created_at"],
                    memory.get("last_accessed", memory["created_at"]),
                    memory.get("access_count", 0),
                    json.dumps(memory.get("metadata", {}))
                ))

                # Insert into FTS table
                conn.execute("""
                    INSERT INTO memory_fts (id, content)
                    VALUES (?, ?)
                """, (memory["id"], memory["content"]))

                counts[memory["category"]] = counts.get(memory["category"], 0) + 1

            conn.commit()

            return {
                "status": "imported",
                "merged": merge,
                "counts": counts,
                "total": sum(counts.values())
            }

        except Exception as e:
            conn.rollback()
            return {
                "status": "error",
                "message": f"Import failed: {str(e)}"
            }
        finally:
            conn.close()

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
