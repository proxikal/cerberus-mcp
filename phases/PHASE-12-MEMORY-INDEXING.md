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
Migrate memories and sessions to unified SQLite database. Memories use FTS5 for full-text search. Sessions use regular tables for scope-based queries.

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

**Note:** Memories use FTS5 (full-text search). Sessions use regular tables.

```sql
-- Memories table with FTS5
CREATE VIRTUAL TABLE IF NOT EXISTS memories USING fts5(
    id UNINDEXED,           -- UUID, not searchable
    content,                -- Memory rule text (searchable)
    category,               -- preference, rule, correction, decision
    scope,                  -- universal, language:X, project:Y, project:Y:task:Z
    confidence,             -- 0.0-1.0
    created_at,             -- ISO timestamp
    last_accessed,          -- ISO timestamp (for stale detection)
    access_count,           -- Usage tracking
    metadata,               -- JSON blob (rationale, evidence, etc.)
    tokensize=porter        -- Porter stemming for better search
);

-- Metadata table (non-FTS)
CREATE TABLE IF NOT EXISTS memory_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Initial metadata
INSERT OR IGNORE INTO memory_metadata (key, value) VALUES
    ('version', '1.0'),
    ('migrated_from_json', 'false'),
    ('last_migration', NULL);

-- Index for non-FTS queries
CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope);
CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);

-- Sessions table (Phase 8)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,           -- UUID
    scope TEXT NOT NULL,            -- "global" or "project:{name}"
    project_path TEXT,              -- Absolute path (null for global)
    phase TEXT,                     -- Current phase/feature being worked on
    context_data TEXT,              -- JSON blob: {files, functions, decisions, blockers, next_actions}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    turn_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',   -- "active", "idle", "archived"
    UNIQUE(scope, status) WHERE status = 'active'
);

-- Session activity tracking (Phase 8)
CREATE TABLE IF NOT EXISTS session_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER,
    activity_type TEXT NOT NULL,    -- correction, pattern, task_start, etc.
    activity_data TEXT,             -- JSON blob
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Indexes for session queries
CREATE INDEX IF NOT EXISTS idx_sessions_scope ON sessions(scope, status);
CREATE INDEX IF NOT EXISTS idx_sessions_last_accessed ON sessions(last_accessed);
CREATE INDEX IF NOT EXISTS idx_sessions_project_path ON sessions(project_path) WHERE project_path IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_activity_session ON session_activity(session_id);
```

---

## Data Structures

```python
@dataclass
class IndexedMemory:
    """Memory stored in SQLite."""
    id: str  # UUID
    content: str
    category: str
    scope: str
    confidence: float
    created_at: str
    last_accessed: str
    access_count: int
    metadata: Dict[str, Any]

@dataclass
class SessionRecord:
    """Session stored in SQLite (Phase 8)."""
    id: str  # UUID
    scope: str  # "global" or "project:{name}"
    project_path: Optional[str]
    phase: Optional[str]  # Current phase/feature
    context_data: Dict[str, Any]  # {files, functions, decisions, blockers, next_actions}
    created_at: str
    last_accessed: str
    last_activity: str
    turn_count: int
    status: str  # "active", "idle", "archived"
```

---

## Memory Index Manager

```python
class MemoryIndexManager:
    """
    Manage SQLite database for memories (FTS5) and sessions (regular tables).
    """

    def __init__(self, base_path: Path):
        self.db_path = base_path / "memory.db"
        self.json_path = base_path / "memory"  # Legacy JSON location
        self._init_db()

    def _init_db(self):
        """
        Initialize database with schema.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency

        # Create tables
        conn.executescript(SCHEMA_SQL)  # Schema from above

        conn.commit()
        conn.close()

    def migrate_from_json(self) -> Dict[str, int]:
        """
        One-time migration from JSON files to SQLite.
        Returns counts of migrated memories by scope.
        """
        # Check if already migrated
        if self._is_migrated():
            return {"status": "already_migrated"}

        conn = sqlite3.connect(self.db_path)
        counts = {
            "universal": 0,
            "language": 0,
            "project": 0,
            "total": 0
        }

        try:
            # Migrate universal (profile.json, corrections.json)
            counts["universal"] += self._migrate_file(
                conn,
                self.json_path / "profile.json",
                "general",
                "universal"
            )
            counts["universal"] += self._migrate_file(
                conn,
                self.json_path / "corrections.json",
                "corrections",
                "universal"
            )

            # Migrate languages
            lang_dir = self.json_path / "languages"
            if lang_dir.exists():
                for lang_file in lang_dir.glob("*.json"):
                    lang = lang_file.stem
                    counts["language"] += self._migrate_file(
                        conn,
                        lang_file,
                        "preferences",
                        f"language:{lang}"
                    )

            # Migrate projects
            proj_dir = self.json_path / "projects"
            if proj_dir.exists():
                for proj in proj_dir.iterdir():
                    if not proj.is_dir():
                        continue

                    # Project decisions
                    counts["project"] += self._migrate_file(
                        conn,
                        proj / "decisions.json",
                        "decisions",
                        f"project:{proj.name}"
                    )

                    # Task-specific
                    task_dir = proj / "tasks"
                    if task_dir.exists():
                        for task_file in task_dir.glob("*.json"):
                            task = task_file.stem
                            counts["project"] += self._migrate_file(
                                conn,
                                task_file,
                                "rules",
                                f"project:{proj.name}:task:{task}"
                            )

            counts["total"] = sum(v for k, v in counts.items() if k != "total")

            # Mark as migrated
            conn.execute(
                "UPDATE memory_metadata SET value = ? WHERE key = ?",
                ("true", "migrated_from_json")
            )
            conn.execute(
                "UPDATE memory_metadata SET value = ? WHERE key = ?",
                (datetime.now().isoformat(), "last_migration")
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            raise

        finally:
            conn.close()

        return counts

    def migrate_sessions_from_json(self) -> Dict[str, int]:
        """
        Migrate session summaries from JSON to SQLite (Phase 8).

        Legacy location: ~/.cerberus/session_summary.json (temporary, global only)
        New location: SQLite sessions table (multi-tier: global + project)
        """
        legacy_path = Path.home() / ".cerberus" / "session_summary.json"

        if not legacy_path.exists():
            return {"status": "no_legacy_sessions", "migrated": 0}

        conn = sqlite3.connect(self.db_path)
        migrated = 0

        try:
            with open(legacy_path) as f:
                legacy_data = json.load(f)

            # Legacy format: single global session
            session_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO sessions (
                    id, scope, project_path, context_data,
                    created_at, last_accessed, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                "global",  # Legacy sessions were global
                None,
                json.dumps(legacy_data),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                "ended"  # Mark legacy as ended
            ))

            migrated = 1
            conn.commit()

            # Backup and remove legacy file
            legacy_path.rename(legacy_path.with_suffix(".json.migrated"))

        except (json.JSONDecodeError, IOError) as e:
            conn.rollback()
            return {"status": "error", "message": str(e), "migrated": 0}

        finally:
            conn.close()

        return {"status": "success", "migrated": migrated}

    def _migrate_file(
        self,
        conn: sqlite3.Connection,
        file_path: Path,
        data_key: str,
        scope: str
    ) -> int:
        """
        Migrate single JSON file to SQLite.
        """
        if not file_path.exists():
            return 0

        try:
            with open(file_path) as f:
                data = json.load(f)

            if data_key not in data:
                return 0

            count = 0
            for item in data[data_key]:
                memory_id = str(uuid.uuid4())

                conn.execute("""
                    INSERT INTO memories (
                        id, content, category, scope, confidence,
                        created_at, last_accessed, access_count, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_id,
                    item["content"],
                    data_key,  # Use data_key as category
                    scope,
                    item.get("confidence", 1.0),
                    item.get("timestamp", datetime.now().isoformat()),
                    datetime.now().isoformat(),
                    0,
                    json.dumps(item.get("metadata", {}))
                ))

                count += 1

            return count

        except (json.JSONDecodeError, IOError):
            return 0

    def _is_migrated(self) -> bool:
        """
        Check if JSON → SQLite migration already done.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT value FROM memory_metadata WHERE key = ?",
            ("migrated_from_json",)
        )
        result = cursor.fetchone()
        conn.close()

        return result and result[0] == "true"

    def verify_integrity(self) -> Dict[str, Any]:
        """
        Verify database integrity and return stats.
        """
        conn = sqlite3.connect(self.db_path)

        # Check schema exists
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]

        if "memories" not in tables:
            return {"status": "error", "message": "Schema missing"}

        # Count memories
        cursor = conn.execute("SELECT COUNT(*) FROM memories")
        total_count = cursor.fetchone()[0]

        # Count by scope
        cursor = conn.execute("""
            SELECT
                CASE
                    WHEN scope = 'universal' THEN 'universal'
                    WHEN scope LIKE 'language:%' THEN 'language'
                    WHEN scope LIKE 'project:%' THEN 'project'
                    ELSE 'other'
                END as scope_type,
                COUNT(*)
            FROM memories
            GROUP BY scope_type
        """)
        scope_counts = dict(cursor.fetchall())

        # Count sessions (Phase 8)
        session_stats = {}
        if "sessions" in tables:
            cursor = conn.execute("SELECT COUNT(*) FROM sessions")
            session_stats["total_sessions"] = cursor.fetchone()[0]

            cursor = conn.execute("""
                SELECT status, COUNT(*)
                FROM sessions
                GROUP BY status
            """)
            session_stats["by_status"] = dict(cursor.fetchall())

        # Database size
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        conn.close()

        return {
            "status": "ok",
            "total_memories": total_count,
            "by_scope": scope_counts,
            "sessions": session_stats,
            "db_size_bytes": db_size,
            "db_size_mb": round(db_size / 1024 / 1024, 2),
            "tables": tables
        }
```

---

## Backward Compatibility

```python
class LegacyJSONFallback:
    """
    Fallback to JSON if SQLite fails.
    """

    def __init__(self, json_path: Path):
        self.json_path = json_path

    def load_all(self) -> List[Dict]:
        """
        Load all memories from JSON (legacy Phase 5-6 logic).
        """
        # Same logic as Phase 6 _load_all_memories()
        # Kept for backward compatibility
        pass

    def is_available(self) -> bool:
        """
        Check if JSON files exist.
        """
        return (self.json_path / "profile.json").exists()
```

---

## Integration with Phase 5-6

```python
def get_index_manager() -> MemoryIndexManager:
    """
    Get index manager, handle migration automatically.
    """
    manager = MemoryIndexManager(Path.home() / ".cerberus")

    # Auto-migrate on first access
    if not manager._is_migrated():
        try:
            counts = manager.migrate_from_json()
            print(f"✓ Migrated {counts['total']} memories to SQLite")
        except Exception as e:
            print(f"⚠ Migration failed: {e}")
            print("Falling back to JSON")

    return manager
```

---

## CLI Tool

```python
# cerberus memory migrate
def cli_migrate():
    """
    CLI command to manually trigger migration.
    """
    manager = MemoryIndexManager(Path.home() / ".cerberus")

    if manager._is_migrated():
        print("Already migrated. Use --force to re-migrate.")
        return

    print("Migrating memories from JSON to SQLite...")
    counts = manager.migrate_from_json()

    print(f"✓ Migrated {counts['total']} memories:")
    print(f"  - Universal: {counts['universal']}")
    print(f"  - Language: {counts['language']}")
    print(f"  - Project: {counts['project']}")

# cerberus memory verify
def cli_verify():
    """
    CLI command to verify index integrity.
    """
    manager = MemoryIndexManager(Path.home() / ".cerberus")
    stats = manager.verify_integrity()

    if stats["status"] == "error":
        print(f"✗ {stats['message']}")
        return

    print(f"✓ Index healthy:")
    print(f"  - Total memories: {stats['total_memories']}")
    print(f"  - Database size: {stats['db_size_mb']} MB")
    print(f"  - By scope: {stats['by_scope']}")

    # Show session stats if available (Phase 8)
    if "sessions" in stats and stats["sessions"]:
        print(f"  - Sessions: {stats['sessions'].get('total_sessions', 0)}")
        if "by_status" in stats["sessions"]:
            print(f"    - By status: {stats['sessions']['by_status']}")

# cerberus memory migrate-sessions
def cli_migrate_sessions():
    """
    CLI command to migrate legacy session summaries (Phase 8).
    """
    manager = MemoryIndexManager(Path.home() / ".cerberus")

    print("Migrating legacy session summaries to SQLite...")
    result = manager.migrate_sessions_from_json()

    if result["status"] == "no_legacy_sessions":
        print("No legacy session summaries found.")
    elif result["status"] == "error":
        print(f"✗ Migration failed: {result['message']}")
    else:
        print(f"✓ Migrated {result['migrated']} session(s)")
```

---

## Exit Criteria

```
✓ MemoryIndexManager class implemented
✓ SQLite schema created: FTS5 for memories + regular tables for sessions
✓ Migration from JSON working (memories + sessions)
✓ Backward compatibility (JSON fallback)
✓ Integrity verification working (includes sessions)
✓ Auto-migration on first access
✓ CLI tools (migrate, verify, migrate-sessions)
✓ WAL mode enabled (concurrency)
✓ Tests: 12 indexing scenarios (10 memories + 2 sessions)
```

---

## Test Scenarios

```python
# Scenario 1: Fresh database creation
→ expect: schema created, tables exist, no errors

# Scenario 2: Migrate from JSON
JSON: 50 memories (20 universal, 15 language, 15 project)
→ expect: 50 memories in SQLite, correct scopes

# Scenario 3: Re-migration check
migrate once → migrate again
→ expect: second migration skipped, "already_migrated"

# Scenario 4: Corrupted JSON
JSON: malformed, missing keys
→ expect: skip file, continue with others, no crash

# Scenario 5: Empty JSON
JSON: exists but empty
→ expect: 0 memories migrated, no error

# Scenario 6: Integrity check
50 memories in DB
→ verify_integrity()
→ expect: total=50, scopes breakdown correct

# Scenario 7: Missing database
delete memory.db → get_index_manager()
→ expect: recreates DB, migrates from JSON

# Scenario 8: Legacy fallback
SQLite fails → fallback to JSON
→ expect: LegacyJSONFallback used, no data loss

# Scenario 9: Concurrent access
2 processes access DB simultaneously
→ expect: WAL mode handles, no locks

# Scenario 10: Large migration
JSON: 500 memories
→ expect: all migrated, < 5 seconds

# Scenario 11: Session migration (Phase 8)
Legacy session_summary.json exists
→ migrate_sessions_from_json()
→ expect: 1 session migrated, status="ended", scope="global"

# Scenario 12: No legacy sessions
No session_summary.json
→ migrate_sessions_from_json()
→ expect: status="no_legacy_sessions", migrated=0
```

---

## Dependencies

```bash
pip install sqlite3  # Built-in, no install needed
```

---

## Performance

- Schema creation: < 10ms
- Migration (100 memories): < 500ms
- Migration (1000 memories): < 3 seconds
- Integrity check: < 50ms
- Database size: ~1KB per memory (~1MB for 1000 memories)

---

## Migration Strategy

**Phase 1: Add indexing (this phase)**
- SQLite schema
- Migration tool
- Backward compatibility

**Phase 2: Update writes (Phase 13)**
- Phase 5 writes to SQLite
- Keep JSON for backward compat (deferred removal)

**Phase 3: Update reads (Phase 13)**
- Phase 6 queries SQLite FTS5
- Fallback to JSON if SQLite fails

**Phase 4: Deprecate JSON (future)**
- After 3+ months stability
- Remove JSON write logic
- Keep JSON read for recovery

---

## File Structure

```
~/.cerberus/
├── memory.db              # Unified SQLite (FTS5 for memories + regular tables for sessions)
├── memory.db-wal          # Write-ahead log (SQLite)
├── memory.db-shm          # Shared memory (SQLite)
├── memory/                # Legacy JSON (kept for compat)
│   ├── profile.json
│   ├── corrections.json
│   ├── languages/
│   └── projects/
└── session_summary.json   # Legacy sessions (Phase 8 - migrated to DB)
```

---

## Error Handling

```python
def safe_index_operation(func):
    """
    Decorator for index operations with fallback.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as e:
            logger.error(f"SQLite error: {e}")
            # Fallback to JSON
            fallback = LegacyJSONFallback(Path.home() / ".cerberus" / "memory")
            if fallback.is_available():
                logger.info("Falling back to JSON")
                return fallback.load_all()
            raise
    return wrapper
```

---

## Key Design Decisions

**Why SQLite + FTS5 for memories:**
- FTS5 provides full-text search for memory content
- Same as Cerberus code indexing (proven)
- No daemon, no server, just a file
- Scales to 10,000+ memories
- Sessions use regular SQLite tables (no FTS5 needed - queries by scope/status)

**Why keep JSON:**
- Backward compatibility
- Recovery if SQLite corrupted
- Gradual rollout (defer removal)

**Why WAL mode:**
- Better concurrency (reads don't block writes)
- Reduces lock contention
- Standard for Cerberus

**Why auto-migration:**
- Zero user intervention
- Happens on first access
- Transparent upgrade

---

## Integration Points

**Phase 5 (Storage):** Will write to SQLite in Phase 13
**Phase 6 (Retrieval):** Will query SQLite in Phase 13
**Phase 8 (Sessions):** Unified database for memories + sessions
**Phase 11 (Maintenance):** Update for SQLite stale detection (memories + sessions)
**MCP Tools:** New `memory_search()` in Phase 13, session tools in Phase 8
