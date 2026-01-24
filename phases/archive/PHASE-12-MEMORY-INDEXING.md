# PHASE 12: MEMORY INDEXING

**Rollout Phase:** Beta (Weeks 3-4)
**Status:** Deferred until Phase Alpha validated

## Prerequisites

⚠️ **DO NOT implement until Phase Alpha complete**

**Required validation gates:**
- ✅ Phases 1-7 implemented with JSON storage
- ✅ Detection accuracy: 90%+
- ✅ Clustering compression: 60%+
- ✅ User approval rate: 70%+
- ✅ Token budget: <1500 tokens
- ✅ Real-world testing: 5+ sessions successful

## Objective
Migrate memories and sessions to unified SQLite database. Use a "Split Table" architecture to support standard indexing, future schema updates (ALTER TABLE), and full-text search.

**Why Phase Beta (not Alpha):**
- Database complexity isolated from learning logic
- Can measure actual token savings empirically
- MVP proves value before optimization investment
- Rollback to JSON if issues

---

## Implementation Location

**File:** `src/cerberus/memory/indexing.py`

**Database:** `~/.cerberus/memory.db`

---

## Schema Design

**IMPORTANT:** SQLite does not support `ALTER TABLE` or regular indices on FTS5 virtual tables. We use a standard table for metadata and a virtual table for search.

```sql
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
    status TEXT DEFAULT 'active',
    UNIQUE(scope, status) WHERE status = 'active'
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
```

---

## Data Structures

```python
@dataclass
class IndexedMemory:
    """Memory stored in SQLite."""
    id: str
    content: str
    category: str
    scope: str
    confidence: float
    created_at: str
    last_accessed: str
    access_count: int
    metadata: Dict[str, Any]
    # Delta fields
    anchor_file: Optional[str] = None
    valid_modes: List[str] = field(default_factory=list)

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
```

---

## Memory Index Manager

```python
class MemoryIndexManager:
    """
    Manage SQLite database for memories and sessions.
    """

    def __init__(self, base_path: Path):
        self.db_path = base_path / "memory.db"
        self.json_path = base_path / "memory"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        conn.close()

    def migrate_from_json(self) -> Dict[str, int]:
        """One-time migration from JSON to SQLite."""
        if self._is_migrated():
            return {"status": "already_migrated"}

        conn = sqlite3.connect(self.db_path)
        counts = {"total": 0}

        try:
            # Migration logic for each JSON file...
            # Note: INSERT into memory_store AND memory_fts
            pass
        finally:
            conn.close()
```

---

## Exit Criteria

```
✓ MemoryIndexManager implemented
✓ Split schema created: memory_store (metadata) + memory_fts (search)
✓ Typo corrected: tokenize = 'porter'
✓ Indices correctly applied to standard table
✓ Pre-provisioned columns for anchoring and mode detection
✓ Migration from JSON functional
✓ CLI tools (migrate, verify) updated for split schema
```

---

**Last Updated:** 2026-01-22
**Version:** 2.0 (Fixed syntax typos and virtual table architectural limitations)