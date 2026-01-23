"""
PHASE 12: MEMORY INDEXING

Migrate memories and sessions to unified SQLite database with FTS5 search.

Architecture:
- Split-table design: memory_store (metadata) + memory_fts (FTS5 search)
- Pre-provisioned columns for Phase Delta (anchoring, mode detection)
- Sessions tables for Phase 8
- WAL mode for concurrency

Zero token cost (one-time migration, no LLM).
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import sqlite3
import uuid


# SQL Schema
SCHEMA_SQL = """
-- 1. Metadata Store (Standard Table)
-- Supports ALTER TABLE, Indices, and structured queries
CREATE TABLE IF NOT EXISTS memory_store (
    id TEXT PRIMARY KEY,
    category TEXT,          -- preference, rule, correction, decision
    scope TEXT,             -- universal, language:X, project:Y, project:Y:task:Z
    confidence REAL,        -- 0.0-1.0
    created_at TEXT,        -- ISO timestamp
    last_accessed TEXT,     -- ISO timestamp (for stale detection)
    access_count INTEGER DEFAULT 0,
    metadata TEXT,          -- JSON blob (rationale, evidence, etc.)

    -- Pre-provisioned columns for Delta phases (to avoid ALTER TABLE issues)
    anchor_file TEXT,
    anchor_symbol TEXT,
    anchor_score REAL,
    anchor_metadata TEXT,   -- JSON blob
    valid_modes TEXT,       -- JSON array
    mode_priority TEXT      -- JSON object
);

-- 2. Search Index (FTS5 Virtual Table)
-- Optimized for full-text search over content
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    id UNINDEXED,           -- Join key to memory_store
    content,                -- Searchable text
    tokenize = 'porter'     -- Porter stemming for better search
);

-- 3. Indices (on standard table only)
CREATE INDEX IF NOT EXISTS idx_mem_scope ON memory_store(scope);
CREATE INDEX IF NOT EXISTS idx_mem_category ON memory_store(category);
CREATE INDEX IF NOT EXISTS idx_mem_created ON memory_store(created_at);

-- 4. Sessions table (Phase 8)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    project_path TEXT,
    phase TEXT,
    context_data TEXT,      -- JSON blob
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    turn_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active'
);

-- 5. Session activity tracking (Phase 8)
CREATE TABLE IF NOT EXISTS session_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER,
    activity_type TEXT NOT NULL,
    activity_data TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Indices for session queries
CREATE INDEX IF NOT EXISTS idx_sess_scope ON sessions(scope, status);
CREATE INDEX IF NOT EXISTS idx_sess_path ON sessions(project_path) WHERE project_path IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_active_session ON sessions(scope, status) WHERE status = 'active';
"""


@dataclass
class IndexedMemory:
    """Memory stored in SQLite."""
    id: str
    content: str
    category: str
    scope: str
    confidence: float
    created_at: str
    last_accessed: Optional[str] = None
    access_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Delta fields (pre-provisioned)
    anchor_file: Optional[str] = None
    anchor_symbol: Optional[str] = None
    anchor_score: Optional[float] = None
    anchor_metadata: Dict[str, Any] = field(default_factory=dict)
    valid_modes: List[str] = field(default_factory=list)
    mode_priority: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "scope": self.scope,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "metadata": self.metadata,
            "anchor_file": self.anchor_file,
            "anchor_symbol": self.anchor_symbol,
            "anchor_score": self.anchor_score,
            "anchor_metadata": self.anchor_metadata,
            "valid_modes": self.valid_modes,
            "mode_priority": self.mode_priority,
        }


@dataclass
class SessionRecord:
    """Session stored in SQLite."""
    id: str
    scope: str
    project_path: Optional[str]
    phase: Optional[str]
    context_data: Dict[str, Any]
    created_at: str
    last_accessed: str
    last_activity: str
    turn_count: int
    status: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "scope": self.scope,
            "project_path": self.project_path,
            "phase": self.phase,
            "context_data": self.context_data,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "last_activity": self.last_activity,
            "turn_count": self.turn_count,
            "status": self.status,
        }


class MemoryIndexManager:
    """
    Manage SQLite database for memories and sessions.

    Split-table architecture:
    - memory_store: Standard table with metadata (supports indices, ALTER TABLE)
    - memory_fts: FTS5 virtual table for full-text search
    """

    def __init__(self, base_path: Path):
        """
        Initialize memory index manager.

        Args:
            base_path: Base directory (e.g., ~/.cerberus)
        """
        self.db_path = base_path / "memory.db"
        self.json_path = base_path / "memory"
        self._init_db()

    def _init_db(self):
        """Initialize database with schema and WAL mode."""
        conn = sqlite3.connect(str(self.db_path))

        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")

        # Create schema
        conn.executescript(SCHEMA_SQL)

        conn.commit()
        conn.close()

    def _is_migrated(self) -> bool:
        """Check if migration has already been performed."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check if we have any memories in the database
        cursor.execute("SELECT COUNT(*) FROM memory_store")
        count = cursor.fetchone()[0]

        conn.close()

        return count > 0

    def migrate_from_json(self) -> Dict[str, int]:
        """
        One-time migration from JSON to SQLite.

        Returns:
            Dict with migration statistics
        """
        if self._is_migrated():
            return {"status": "already_migrated", "total": 0}

        if not self.json_path.exists():
            return {"status": "no_json_found", "total": 0}

        conn = sqlite3.connect(str(self.db_path))
        counts = {
            "universal": 0,
            "languages": 0,
            "projects": 0,
            "total": 0,
        }

        try:
            # Migrate universal memories
            for filename in ["profile.json", "corrections.json"]:
                file_path = self.json_path / filename
                if file_path.exists():
                    with open(file_path) as f:
                        memories = json.load(f)
                        if isinstance(memories, list):
                            for mem in memories:
                                self._insert_memory(conn, mem)
                                counts["universal"] += 1
                                counts["total"] += 1

            # Migrate language memories
            lang_dir = self.json_path / "languages"
            if lang_dir.exists():
                for lang_file in lang_dir.glob("*.json"):
                    with open(lang_file) as f:
                        memories = json.load(f)
                        if isinstance(memories, list):
                            for mem in memories:
                                self._insert_memory(conn, mem)
                                counts["languages"] += 1
                                counts["total"] += 1

            # Migrate project memories
            proj_dir = self.json_path / "projects"
            if proj_dir.exists():
                for proj_path in proj_dir.iterdir():
                    if proj_path.is_dir():
                        decisions_file = proj_path / "decisions.json"
                        if decisions_file.exists():
                            with open(decisions_file) as f:
                                memories = json.load(f)
                                if isinstance(memories, list):
                                    for mem in memories:
                                        self._insert_memory(conn, mem)
                                        counts["projects"] += 1
                                        counts["total"] += 1

            conn.commit()
            counts["status"] = "success"

        except Exception as e:
            conn.rollback()
            counts["status"] = f"error: {str(e)}"

        finally:
            conn.close()

        return counts

    def _insert_memory(self, conn: sqlite3.Connection, memory: Dict[str, Any]):
        """
        Insert a memory into both memory_store and memory_fts.

        Args:
            conn: Database connection
            memory: Memory dict from JSON
        """
        # Extract fields
        mem_id = memory.get("id", f"mem-{uuid.uuid4().hex[:8]}")
        content = memory.get("content", "")
        category = memory.get("category", "preference")
        scope = memory.get("scope", "universal")
        confidence = memory.get("confidence", 0.9)
        created_at = memory.get("timestamp", datetime.now().isoformat())
        last_accessed = memory.get("last_accessed")
        access_count = memory.get("access_count", 0)

        # Metadata (rationale, evidence, etc.)
        metadata = {}
        for key in ["rationale", "evidence", "source_variants"]:
            if key in memory:
                metadata[key] = memory[key]

        # Insert into memory_store
        conn.execute("""
            INSERT OR REPLACE INTO memory_store
            (id, category, scope, confidence, created_at, last_accessed, access_count, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mem_id,
            category,
            scope,
            confidence,
            created_at,
            last_accessed,
            access_count,
            json.dumps(metadata) if metadata else None,
        ))

        # Insert into memory_fts
        conn.execute("""
            INSERT OR REPLACE INTO memory_fts (id, content)
            VALUES (?, ?)
        """, (mem_id, content))

    def get_memory(self, memory_id: str) -> Optional[IndexedMemory]:
        """
        Retrieve a memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            IndexedMemory or None if not found
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Join memory_store and memory_fts
        cursor.execute("""
            SELECT
                ms.id, mf.content, ms.category, ms.scope, ms.confidence,
                ms.created_at, ms.last_accessed, ms.access_count, ms.metadata,
                ms.anchor_file, ms.anchor_symbol, ms.anchor_score, ms.anchor_metadata,
                ms.valid_modes, ms.mode_priority
            FROM memory_store ms
            JOIN memory_fts mf ON ms.id = mf.id
            WHERE ms.id = ?
        """, (memory_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return IndexedMemory(
            id=row[0],
            content=row[1],
            category=row[2],
            scope=row[3],
            confidence=row[4],
            created_at=row[5],
            last_accessed=row[6],
            access_count=row[7],
            metadata=json.loads(row[8]) if row[8] else {},
            anchor_file=row[9],
            anchor_symbol=row[10],
            anchor_score=row[11],
            anchor_metadata=json.loads(row[12]) if row[12] else {},
            valid_modes=json.loads(row[13]) if row[13] else [],
            mode_priority=json.loads(row[14]) if row[14] else {},
        )

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify database integrity.

        Checks:
        - All memory_store entries have corresponding memory_fts entries
        - All memory_fts entries have corresponding memory_store entries
        - No orphaned records

        Returns:
            Dict with verification results
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        results = {
            "status": "ok",
            "issues": [],
        }

        # Check for orphaned memory_store entries
        cursor.execute("""
            SELECT COUNT(*) FROM memory_store ms
            WHERE NOT EXISTS (SELECT 1 FROM memory_fts mf WHERE mf.id = ms.id)
        """)
        orphaned_store = cursor.fetchone()[0]
        if orphaned_store > 0:
            results["status"] = "issues_found"
            results["issues"].append(f"{orphaned_store} memory_store entries missing from memory_fts")

        # Check for orphaned memory_fts entries
        cursor.execute("""
            SELECT COUNT(*) FROM memory_fts mf
            WHERE NOT EXISTS (SELECT 1 FROM memory_store ms WHERE ms.id = mf.id)
        """)
        orphaned_fts = cursor.fetchone()[0]
        if orphaned_fts > 0:
            results["status"] = "issues_found"
            results["issues"].append(f"{orphaned_fts} memory_fts entries missing from memory_store")

        # Count totals
        cursor.execute("SELECT COUNT(*) FROM memory_store")
        results["memory_store_count"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM memory_fts")
        results["memory_fts_count"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sessions")
        results["sessions_count"] = cursor.fetchone()[0]

        conn.close()

        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get database statistics.

        Returns:
            Dict with counts by scope, category, etc.
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        stats = {}

        # Total memories
        cursor.execute("SELECT COUNT(*) FROM memory_store")
        stats["total_memories"] = cursor.fetchone()[0]

        # By scope
        cursor.execute("""
            SELECT scope, COUNT(*) FROM memory_store
            GROUP BY scope
        """)
        stats["by_scope"] = dict(cursor.fetchall())

        # By category
        cursor.execute("""
            SELECT category, COUNT(*) FROM memory_store
            GROUP BY category
        """)
        stats["by_category"] = dict(cursor.fetchall())

        # Sessions
        cursor.execute("SELECT COUNT(*) FROM sessions WHERE status = 'active'")
        stats["active_sessions"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM sessions WHERE status = 'completed'")
        stats["completed_sessions"] = cursor.fetchone()[0]

        conn.close()

        return stats


def migrate_memories(base_path: Path = None) -> Dict[str, int]:
    """
    CLI helper: Migrate memories from JSON to SQLite.

    Args:
        base_path: Base directory (default: ~/.cerberus)

    Returns:
        Migration statistics
    """
    if base_path is None:
        base_path = Path.home() / ".cerberus"

    manager = MemoryIndexManager(base_path)
    return manager.migrate_from_json()


def verify_database(base_path: Path = None) -> Dict[str, Any]:
    """
    CLI helper: Verify database integrity.

    Args:
        base_path: Base directory (default: ~/.cerberus)

    Returns:
        Verification results
    """
    if base_path is None:
        base_path = Path.home() / ".cerberus"

    manager = MemoryIndexManager(base_path)
    return manager.verify_integrity()


def show_stats(base_path: Path = None) -> Dict[str, Any]:
    """
    CLI helper: Show database statistics.

    Args:
        base_path: Base directory (default: ~/.cerberus)

    Returns:
        Database statistics
    """
    if base_path is None:
        base_path = Path.home() / ".cerberus"

    manager = MemoryIndexManager(base_path)
    return manager.get_stats()
