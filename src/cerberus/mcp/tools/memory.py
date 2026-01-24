"""Memory system tools - cross-project developer memory."""
from typing import Any, Dict, List, Optional
from pathlib import Path

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

# Quality filtering
from cerberus.memory.quality_filter import MemoryQualityFilter


def register(mcp):
    # Lazy singleton for GitExtractor
    _extractor: Optional[GitExtractor] = None
    _quality_filter: Optional[MemoryQualityFilter] = None

    def get_extractor() -> GitExtractor:
        nonlocal _extractor
        if _extractor is None:
            _extractor = GitExtractor(storage=MemoryStorage())
        return _extractor

    def get_quality_filter() -> MemoryQualityFilter:
        nonlocal _quality_filter
        if _quality_filter is None:
            _quality_filter = MemoryQualityFilter()
        return _quality_filter

    @mcp.tool()
    def memory_learn(
        category: str,
        content: str,
        project: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        details: Optional[str] = None,
        relevance_decay_days: int = 90,
        bulk_memories: Optional[List[Dict[str, Any]]] = None,
    ) -> dict:
        """Store preference, decision, or correction in session memory."""
        import uuid
        from datetime import datetime

        # Handle bulk operation
        if bulk_memories:
            storage = MemoryStorage()
            results: list = []
            errors: list = []

            for idx, mem in enumerate(bulk_memories):
                try:
                    # Validate and store each memory
                    mem_category = mem.get("category")
                    mem_content = mem.get("content")
                    mem_project = mem.get("project")
                    mem_metadata = mem.get("metadata", {})
                    mem_details = mem.get("details")
                    mem_decay_days = mem.get("relevance_decay_days", 90)

                    # Quality filters
                    if len(mem_content) > 500:
                        errors.append(f"Memory {idx}: Content too long (max 500 chars)")
                        continue

                    # Advanced quality check (spaCy + textblob)
                    quality_filter = get_quality_filter()
                    quality_score = quality_filter.assess_quality(mem_content)

                    if not (quality_score.is_actionable or quality_score.is_semantic_code):
                        # Use simplified reason from quality_filter
                        reason = quality_score.rejection_reason or "rejected"
                        errors.append(f"Memory {idx}: {reason}")
                        continue

                    # Determine scope
                    if mem_category == "preference":
                        scope = "universal"
                    elif mem_category == "decision":
                        if mem_project is None:
                            from pathlib import Path
                            mem_project = Path.cwd().name
                        scope = f"project:{mem_project}"
                    elif mem_category == "correction":
                        scope = "universal"
                    else:
                        errors.append(f"Memory {idx}: Unknown category '{mem_category}'")
                        continue

                    # Create and store
                    memory_id = str(uuid.uuid4())
                    proposal = MemoryProposal(
                        id=memory_id,
                        category=mem_category,
                        scope=scope,
                        content=mem_content,
                        rationale=mem_metadata.get("rationale", "Bulk memory via memory_learn"),
                        source_variants=[],
                        confidence=1.0,
                        priority=1,
                        details=mem_details,
                        relevance_decay_days=mem_decay_days
                    )

                    stored_id = storage.store(proposal)
                    results.append({
                        "memory_id": stored_id,
                        "category": mem_category,
                        "content": mem_content
                    })

                except Exception as e:
                    errors.append(f"Memory {idx}: {str(e)}")

            return {
                "status": "bulk_learned",
                "stored_count": len(results),
                "error_count": len(errors),
                "memories": results,
                "errors": errors if errors else None
            }

        # Single memory operation (original logic)
        metadata = metadata or {}

        # Quality filter: Reject garbage data
        if len(content) > 500:
            return {
                "status": "error",
                "message": "Content too long (max 500 chars). Use 'details' for explanations."
            }

        # Advanced quality check (spaCy)
        quality_filter = get_quality_filter()
        quality_score = quality_filter.assess_quality(content)

        if not (quality_score.is_actionable or quality_score.is_semantic_code):
            # Compact error for agents (low token cost)
            # rejection_reason already simplified in quality_filter.py
            return {
                "status": "rejected",
                "reason": quality_score.rejection_reason or "not_actionable"
            }

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

        # Create memory proposal (hybrid format)
        memory_id = str(uuid.uuid4())
        proposal = MemoryProposal(
            id=memory_id,
            category=category,
            scope=scope,
            content=content,
            rationale=metadata.get("rationale", "User-provided memory via memory_learn"),
            source_variants=[],
            confidence=1.0,  # User-provided = maximum confidence
            priority=1,
            details=details,
            relevance_decay_days=relevance_decay_days
        )

        # Store to SQLite
        try:
            storage = MemoryStorage()
            stored_id = storage.store(proposal)
            result = {
                "status": "learned",
                "category": category,
                "scope": scope,
                "memory_id": stored_id,
                "content": content,
                "details": details,
                "relevance_decay_days": relevance_decay_days
            }
            # Add project for decisions
            if category == "decision" and project:
                result["project"] = project
            return result
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
        """Display stored memories with optional filtering."""
        import sqlite3
        from pathlib import Path

        db_path = Path.home() / ".cerberus" / "memory.db"

        if not db_path.exists():
            return {"status": "empty", "message": "No memories stored yet"}

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        try:
            # Build query with filters
            query = "SELECT id, category, scope, metadata, created_at, last_accessed, access_count, details, relevance_decay_days FROM memory_store WHERE 1=1"
            params: list = []

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
            memories: list = []
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
                    "details": row["details"],
                    "relevance_decay_days": row["relevance_decay_days"],
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
        """Generate context for prompt injection from session memory."""
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
        """Extract memories from git commit history."""
        import os
        from pathlib import Path
        from cerberus.memory.storage import MemoryStorage

        # Change to the specified path
        original_cwd = os.getcwd()
        try:
            os.chdir(path)

            # Create extractor with SQLite storage
            storage = MemoryStorage()
            extractor = get_extractor()
            extractor.storage = storage

            # Calculate since date
            since = f"{lookback_days} days ago"

            # Learn from git history
            result = extractor.learn_from_git(since=since, max_commits=100)

            return result

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to extract patterns: {str(e)}"
            }
        finally:
            os.chdir(original_cwd)

    @mcp.tool()
    def memory_forget(
        category: str,
        identifier: Optional[str] = None,
        project: Optional[str] = None,
        ids: Optional[List[str]] = None,
    ) -> dict:
        """Remove memory entries by ID or filter criteria."""
        # Validate category
        valid_categories = ["preference", "decision", "correction", "rule"]
        if category and category not in valid_categories:
            return {
                "status": "error",
                "message": f"Invalid category: {category}. Must be one of: {', '.join(valid_categories)}"
            }

        # Handle bulk deletion
        if ids:
            import sqlite3
            from pathlib import Path

            storage = MemoryStorage()
            db_path = Path.home() / ".cerberus" / "memory.db"
            conn = sqlite3.connect(str(db_path))

            deleted: list = []
            not_found: list = []
            errors: list = []

            try:
                for memory_id in ids:
                    try:
                        # Validate ID exists and matches category if provided
                        if category:
                            cursor = conn.execute(
                                "SELECT category FROM memory_store WHERE id = ?",
                                (memory_id,)
                            )
                            row = cursor.fetchone()
                            if not row:
                                not_found.append(memory_id)
                                continue
                            if row[0] != category:
                                errors.append(f"{memory_id}: category mismatch (expected {category}, got {row[0]})")
                                continue

                        # Delete the memory
                        if storage.delete_memory(memory_id):
                            deleted.append(memory_id)
                        else:
                            not_found.append(memory_id)

                    except Exception as e:
                        errors.append(f"{memory_id}: {str(e)}")

                return {
                    "status": "bulk_forgotten",
                    "deleted_count": len(deleted),
                    "not_found_count": len(not_found),
                    "error_count": len(errors),
                    "deleted_ids": deleted,
                    "not_found_ids": not_found if not_found else None,
                    "errors": errors if errors else None
                }

            finally:
                conn.close()

        # Single deletion (original logic)
        if not identifier:
            return {
                "status": "error",
                "message": "Must provide either 'identifier' for single deletion or 'ids' for bulk deletion"
            }

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
        """Show memory storage statistics."""
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
        """Export memories to JSON file."""
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

        memories: list = []
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
        """Import memories from JSON file."""
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
    def memory_propose(
        interactive: bool = True,
        batch_threshold: float = 0.9
    ) -> dict:
        """Manually trigger batch memory collection from conversation."""
        from cerberus.memory.hooks import propose_hook

        try:
            # This calls save_session_context_to_db() FIRST, then does corrections
            result = propose_hook(interactive=interactive, batch_threshold=batch_threshold)

            return {
                "status": "completed",
                "session_summary_saved": True,  # Always saved by propose_hook
                "proposals_generated": len(result.proposals),
                "proposals_approved": len(result.approved_ids),
                "stored_count": result.stored_count,
                "session_stats": result.session_stats,
                "note": "Session summary (semantic codes + details) saved to sessions table"
            }
        except Exception as e:
            return {
                "status": "error",
                "session_summary_saved": False,
                "message": str(e)
            }

    @mcp.tool()
    def memory_search(
        query: Optional[str] = None,
        scope: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
        queries: Optional[List[Dict[str, Any]]] = None,
    ) -> dict:
        """Search memories using FTS5 full-text search."""
        db_path = Path.home() / ".cerberus" / "memory.db"

        if not db_path.exists():
            return {
                "status": "error",
                "message": "Adaptive memory database not found. No memories have been stored yet."
            }

        # Validate inputs
        if not query and not queries:
            return {
                "status": "error",
                "message": "Must provide either query for single search or queries for bulk search"
            }

        search_engine = MemorySearchEngine(db_path)

        # Handle bulk mode
        if queries:
            all_results: list = []
            errors: list = []
            total_found = 0

            for idx, q_spec in enumerate(queries):
                try:
                    q_text = q_spec.get("query")
                    q_scope = q_spec.get("scope")
                    q_category = q_spec.get("category")
                    q_limit = q_spec.get("limit", limit)

                    if not q_text:
                        errors.append(f"Query {idx}: Missing 'query' field")
                        continue

                    search_query = SearchQuery(
                        text=q_text,
                        scope=q_scope,
                        category=q_category,
                        limit=q_limit,
                        order_by="relevance"
                    )

                    results = search_engine.search(search_query)
                    total_found += len(results)

                    all_results.append({
                        "query": q_text,
                        "scope": q_scope,
                        "category": q_category,
                        "result_count": len(results),
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
                    })

                except Exception as e:
                    errors.append(f"Query {idx}: {str(e)}")

            return {
                "status": "bulk_search",
                "requested_count": len(queries),
                "successful_count": len(all_results),
                "total_results": total_found,
                "searches": all_results,
                "errors": errors if errors else None
            }

        # Single mode (original logic)
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

    @mcp.tool()
    def memory_migrate(
        memory_ids: List[str],
        target_project: str,
        dry_run: bool = True
    ) -> dict:
        """
        Migrate memories between project scopes (prevents cross-project contamination).

        Use when memories were stored in wrong project scope.

        Args:
            memory_ids: List of memory IDs to migrate
            target_project: Target project name (e.g., "hydra", "my-app")
            dry_run: If True, preview changes without applying (default: True)

        Returns:
            Migration report with preview/results

        Examples:
            # Preview migration
            memory_migrate(["abc123", "def456"], "hydra", dry_run=True)

            # Execute migration
            memory_migrate(["abc123", "def456"], "hydra", dry_run=False)
        """
        import sqlite3
        from pathlib import Path

        db_path = Path.home() / ".cerberus" / "memory.db"
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row

        migrated: list = []
        not_found: list = []
        errors: list = []

        try:
            for memory_id in memory_ids:
                try:
                    # Fetch current memory
                    cursor = conn.execute(
                        "SELECT id, category, scope, content FROM memory_store WHERE id = ?",
                        (memory_id,)
                    )
                    row = cursor.fetchone()

                    if not row:
                        not_found.append(memory_id)
                        continue

                    old_scope = row["scope"]
                    new_scope = f"project:{target_project}"

                    # Skip if already in target scope
                    if old_scope == new_scope:
                        errors.append(f"{memory_id}: already in {new_scope}")
                        continue

                    migration_info = {
                        "id": memory_id,
                        "category": row["category"],
                        "content": row["content"],
                        "old_scope": old_scope,
                        "new_scope": new_scope
                    }

                    if not dry_run:
                        # Execute migration
                        conn.execute(
                            "UPDATE memory_store SET scope = ? WHERE id = ?",
                            (new_scope, memory_id)
                        )
                        conn.commit()

                    migrated.append(migration_info)

                except Exception as e:
                    errors.append(f"{memory_id}: {str(e)}")

            return {
                "status": "preview" if dry_run else "migrated",
                "dry_run": dry_run,
                "target_project": target_project,
                "migrated_count": len(migrated),
                "not_found_count": len(not_found),
                "error_count": len(errors),
                "migrations": migrated,
                "not_found_ids": not_found if not_found else None,
                "errors": errors if errors else None,
                "hint": "Set dry_run=False to execute migration" if dry_run and migrated else None
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Migration failed: {str(e)}"
            }
        finally:
            conn.close()
