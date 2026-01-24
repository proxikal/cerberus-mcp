"""
Phase 5: Storage Operations (Version 2 - SQLite)

Write approved proposals to SQLite database using Phase 12 infrastructure.
This is Phase Beta implementation - replaces JSON storage from Phase Alpha.

Phase 14 Integration: Discovers and stores code anchors for memories.
Phase 15 Integration: Auto-tags memories with valid modes.

Zero token cost (pure storage).
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Union

# Phase 14: Dynamic Anchoring
from .anchoring import AnchorEngine, extract_language_from_scope, extract_project_from_scope

# Phase 15: Mode-Aware Context
from .mode_detection import auto_tag_memory


class MemoryStorage:
    """
    SQLite-based hierarchical storage for memories.

    Phase Alpha (MVP): JSON files (deprecated)
    Phase Beta (Current): SQLite writes to ~/.cerberus/memory.db

    Uses Phase 12 schema:
    - memory_store: Standard table with metadata
    - memory_fts: FTS5 virtual table for full-text search
    """

    def __init__(self, base_dir: Optional[Path] = None, enable_anchoring: bool = True):
        """
        Args:
            base_dir: Base directory for storage (default: ~/.cerberus)
            enable_anchoring: Enable Phase 14 anchor discovery (default: True)
        """
        if base_dir is None:
            base_dir = Path.home() / ".cerberus"
        elif isinstance(base_dir, str):
            base_dir = Path(base_dir)

        self.base_dir = base_dir
        self.db_path = base_dir / "memory.db"
        self.enable_anchoring = enable_anchoring
        self._anchor_engine = AnchorEngine() if enable_anchoring else None
        self._ensure_database()

    def store_batch(self, proposals: List) -> Dict[str, int]:
        """
        Store batch of approved proposals to SQLite.

        Args:
            proposals: List of MemoryProposal or AgentProposal objects

        Returns:
            Dict with statistics: {"total_stored": N, "by_scope": {...}}
        """
        if not proposals:
            return {"total_stored": 0, "by_scope": {}}

        conn = sqlite3.connect(str(self.db_path))

        # Track statistics
        total_stored = 0
        by_scope = {}

        try:
            for proposal in proposals:
                # Use proposal's ID directly (MemoryProposal always has id)
                memory_id = proposal.id
                now = datetime.now().isoformat()

                # Extract metadata
                metadata = {
                    "rationale": getattr(proposal, "rationale", None),
                    "evidence": getattr(proposal, "evidence", []),
                    "source_variants": getattr(proposal, "source_variants", [])
                }

                # Phase 14: Discover code anchor
                anchor = None
                if self._anchor_engine and proposal.scope != "universal":
                    try:
                        anchor = self._anchor_engine.anchor_memory(
                            memory_id=memory_id,
                            content=proposal.content,
                            scope=proposal.scope
                        )
                    except Exception:
                        # Anchor discovery failed - continue without anchor
                        pass

                # Prepare anchor metadata
                anchor_file = anchor.file_path if anchor else None
                anchor_symbol = anchor.symbol_name if anchor else None
                anchor_score = anchor.quality_score if anchor else None
                anchor_metadata = json.dumps({
                    "file_size": anchor.file_size,
                    "match_score": anchor.match_score,
                    "recency_score": anchor.recency_score
                }) if anchor else None

                # Phase 15: Auto-tag modes
                valid_modes, mode_priority = auto_tag_memory(proposal.content)

                # Insert into memory_store (metadata table with anchors + modes + hybrid format)
                conn.execute("""
                    INSERT INTO memory_store (
                        id, category, scope, confidence,
                        created_at, last_accessed, access_count, metadata,
                        anchor_file, anchor_symbol, anchor_score, anchor_metadata,
                        valid_modes, mode_priority,
                        details, relevance_decay_days
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_id,
                    proposal.category,
                    proposal.scope,
                    getattr(proposal, "confidence", 1.0),
                    now,
                    now,
                    0,
                    json.dumps(metadata),
                    anchor_file,
                    anchor_symbol,
                    anchor_score,
                    anchor_metadata,
                    json.dumps(valid_modes),
                    json.dumps(mode_priority),
                    getattr(proposal, "details", None),
                    getattr(proposal, "relevance_decay_days", 90)
                ))

                # Insert into memory_fts (FTS5 search table)
                conn.execute("""
                    INSERT INTO memory_fts (id, content)
                    VALUES (?, ?)
                """, (memory_id, proposal.content))

                total_stored += 1
                by_scope[proposal.scope] = by_scope.get(proposal.scope, 0) + 1

            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            raise RuntimeError(f"Failed to store memories to database: {e}")
        finally:
            conn.close()

        return {
            "total_stored": total_stored,
            "by_scope": by_scope,
            "memory_id": memory_id  # Return last stored ID for single store() calls
        }

    def store(self, proposal) -> str:
        """
        Store single approved proposal to SQLite.

        Args:
            proposal: MemoryProposal or AgentProposal object

        Returns:
            Memory ID (UUID string)
        """
        result = self.store_batch([proposal])
        return result.get("memory_id")

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from both storage and FTS tables.

        Phase 19 requirement for conflict resolution.

        Args:
            memory_id: Memory ID to delete

        Returns:
            True if memory was deleted, False if not found
        """
        if not self.db_path.exists():
            return False

        conn = sqlite3.connect(str(self.db_path))

        try:
            # Check if memory exists
            cursor = conn.execute(
                "SELECT id FROM memory_store WHERE id = ?",
                (memory_id,)
            )
            if not cursor.fetchone():
                return False

            # Delete from both tables
            conn.execute("DELETE FROM memory_store WHERE id = ?", (memory_id,))
            conn.execute("DELETE FROM memory_fts WHERE id = ?", (memory_id,))

            conn.commit()
            return True

        except sqlite3.Error as e:
            conn.rollback()
            raise RuntimeError(f"Failed to delete memory {memory_id}: {e}")
        finally:
            conn.close()

    def _ensure_database(self) -> None:
        """
        Ensure database exists with correct schema.

        Creates database if it doesn't exist.
        Uses Phase 12 schema (MemoryIndexManager).
        """
        if not self.db_path.exists():
            # Database doesn't exist - create it
            from .indexing import MemoryIndexManager
            manager = MemoryIndexManager(self.base_dir)
            # Schema is created automatically in __init__

    def get_stats(self) -> Dict[str, any]:
        """
        Get storage statistics from SQLite.

        Returns:
            Dict with memory counts by scope and category
        """
        if not self.db_path.exists():
            return {"total": 0, "by_scope": {}, "by_category": {}}

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        try:
            # Total memories
            cursor = conn.execute("SELECT COUNT(*) as count FROM memory_store")
            total = cursor.fetchone()["count"]

            # By scope
            by_scope = {}
            cursor = conn.execute("""
                SELECT scope, COUNT(*) as count
                FROM memory_store
                GROUP BY scope
                ORDER BY count DESC
            """)
            for row in cursor:
                by_scope[row["scope"]] = row["count"]

            # By category
            by_category = {}
            cursor = conn.execute("""
                SELECT category, COUNT(*) as count
                FROM memory_store
                GROUP BY category
                ORDER BY count DESC
            """)
            for row in cursor:
                by_category[row["category"]] = row["count"]

            return {
                "total": total,
                "by_scope": by_scope,
                "by_category": by_category
            }

        finally:
            conn.close()


def store_proposals(
    proposals: List,
    base_dir: Optional[Path] = None
) -> Dict[str, int]:
    """
    Convenience function to store proposals.

    Args:
        proposals: List of MemoryProposal or AgentProposal objects
        base_dir: Optional base directory (default: ~/.cerberus)

    Returns:
        Dict with storage statistics
    """
    storage = MemoryStorage(base_dir=base_dir)
    return storage.store_batch(proposals)


def get_storage_stats(base_dir: Optional[Path] = None) -> Dict[str, any]:
    """
    Get storage statistics.

    Args:
        base_dir: Optional base directory (default: ~/.cerberus)

    Returns:
        Dict with memory counts by scope and category
    """
    storage = MemoryStorage(base_dir=base_dir)
    return storage.get_stats()
