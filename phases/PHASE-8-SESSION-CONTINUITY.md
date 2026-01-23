# PHASE 8: SESSION CONTINUITY

**Rollout Phase:** Gamma (Weeks 5-6)
**Status:** Enhancement layer - deferred until core stable
**Storage:** SQLite (unified with Phase 12 memory database)

## Prerequisites

⚠️ **DO NOT implement until Phase Beta complete**

**Required:**
- ✅ Phase Beta complete (SQLite stable, 2+ weeks production)
- ✅ Phases 1-7, 12-13 validated and stable
- ✅ Token savings achieved (80%+ measured)
- ✅ Core memory system proven in real-world usage

## Objective
Capture session context during work, inject at next session start. Zero re-explanation needed. NO LLM.

**Multi-tier session scopes:**
- **Global scope**: Brainstorming, non-project work
- **Project scope**: Project-specific work (per git repo)
- **Concurrent sessions**: Multiple projects simultaneously

**Why Phase Gamma (not Alpha/Beta):**
- Core memory system must be stable first
- Session continuity is enhancement, not blocker
- Can be added incrementally without risk
- Depends on stable Phase 7 injection and Phase 12 SQLite

---

## Implementation Location

**File:** `src/cerberus/memory/session_continuity.py`

---

## Data Structures

```python
@dataclass
class SessionContext:
    """Active session context."""
    id: str  # UUID
    scope: str  # "global" or "project:{name}"
    project_path: Optional[str]  # Full path to project root (NULL for global)
    phase: Optional[str]  # "PHASE-2-SEMANTIC", "feature-auth", etc.
    completed: List[str]  # ["impl:semantic_analyzer.py", "test:clustering"]
    next_actions: List[str]  # ["test:deduplication", "integrate:phase3"]
    decisions: List[str]  # ["dec:threshold=0.75-precision"]
    blockers: List[str]  # ["block:need:ollama", "block:unclear:storage"]
    files_modified: List[str]
    key_functions: List[str]  # ["cluster_corrections", "detect_patterns"]
    created_at: datetime
    last_accessed: datetime
    last_activity: datetime
    turn_count: int
    status: str  # "active", "idle", "archived"

@dataclass
class InjectionPackage:
    """Ready-to-inject codes."""
    codes: str  # Raw codes, newline-separated
    token_count: int
    session_id: str
    scope: str
```

---

## Storage Schema (SQLite)

**Database:** `~/.cerberus/memory.db` (unified with Phase 12)

**Schema location:** Phase 12 (PHASE-12-MEMORY-INDEXING.md)

Phase 12 contains the complete sessions schema including:
- `sessions` table: Stores session context (scope, project_path, phase, context_data, timestamps, turn_count, status)
- `session_activity` table: Tracks session activity events (turn_number, activity_type, activity_data)
- Indexes: scope+status, last_accessed, project_path (conditional)

**Key schema details:**
- `scope`: "global" or "project:{name}" (multi-tier sessions)
- `status`: "active", "idle", "archived"
- `context_data`: JSON blob with {files, functions, decisions, blockers, next_actions}
- Constraint: Only ONE active session per scope (UNIQUE constraint)

**Migration from JSON:**

Phase 12 handles migration via `MemoryIndexManager.migrate_sessions_from_json()`. See Phase 12 for complete implementation.

---

## Scope Detection

```python
def detect_session_scope() -> tuple[str, Optional[str]]:
    """
    Detect session scope (global vs project).

    Strategy:
    1. Check if in git repo (walk up to find .git)
    2. If in git repo → project scope (use repo name + path)
    3. If not in git repo → global scope

    Returns:
        (scope, project_path)
        Examples:
            ("global", None)
            ("project:cerberus", "/Users/user/dev/cerberus")
    """
    from pathlib import Path

    cwd = Path.cwd()

    # Walk up to find .git
    current = cwd
    while current != current.parent:
        if (current / ".git").exists():
            # Found git repo
            project_name = current.name
            return f"project:{project_name}", str(current)
        current = current.parent

    # Not in git repo → global scope
    return "global", None
```

---

## Context Capture

```python
class SessionContextCapture:
    """
    Captures session context during work.
    Called by MCP tool handlers or hooks.

    Uses SQLite for persistence (not JSON).
    """

    def __init__(self, db_path: Path = Path.home() / ".cerberus" / "memory.db"):
        self.db_path = db_path
        self.scope, self.project_path = detect_session_scope()
        self.session_id = self._get_or_create_session()

        # In-memory cache (synced to DB on each record)
        self.completed: List[str] = []
        self.next_actions: List[str] = []
        self.decisions: List[str] = []
        self.blockers: List[str] = []
        self.files_modified: List[str] = []
        self.key_functions: List[str] = []
        self._load_from_db()

    def _get_or_create_session(self) -> str:
        """Get active session for scope or create new one."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Check for active session
        row = conn.execute("""
            SELECT id, context_data FROM sessions
            WHERE scope = ? AND status = 'active'
        """, (self.scope,)).fetchone()

        if row:
            return row['id']

        # Create new session
        import uuid
        session_id = f"session-{uuid.uuid4().hex[:12]}"

        conn.execute("""
            INSERT INTO sessions (id, scope, project_path, status, context_data)
            VALUES (?, ?, ?, 'active', '{}')
        """, (session_id, self.scope, self.project_path))

        conn.commit()
        conn.close()

        return session_id

    def _load_from_db(self):
        """Load existing context from database."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        row = conn.execute("""
            SELECT context_data FROM sessions WHERE id = ?
        """, (self.session_id,)).fetchone()

        if row and row['context_data']:
            data = json.loads(row['context_data'])
            self.completed = data.get("completed", [])
            self.next_actions = data.get("next_actions", [])
            self.decisions = data.get("decisions", [])
            self.blockers = data.get("blockers", [])
            self.files_modified = data.get("files", [])
            self.key_functions = data.get("functions", [])

        conn.close()

    def _sync_to_db(self):
        """Sync in-memory state to database."""
        import sqlite3

        context_data = json.dumps({
            "completed": self.completed,
            "next_actions": self.next_actions,
            "decisions": self.decisions,
            "blockers": self.blockers,
            "files": self.files_modified,
            "functions": self.key_functions
        })

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE sessions
            SET context_data = ?, last_activity = CURRENT_TIMESTAMP, turn_count = turn_count + 1
            WHERE id = ?
        """, (context_data, self.session_id))
        conn.commit()
        conn.close()

    def record_completion(self, action: str):
        """Record completed action. Format: impl:target"""
        if action not in self.completed:
            self.completed.append(action)
            self._sync_to_db()

    def record_next(self, action: str):
        """Record next action. Format: next:action"""
        if action not in self.next_actions:
            self.next_actions.append(action)
            self._sync_to_db()

    def record_decision(self, choice: str, reason: str):
        """Record decision. Format: dec:choice-reason"""
        code = f"dec:{choice}-{reason}".replace(" ", "-")
        if code not in self.decisions:
            self.decisions.append(code)
            self._sync_to_db()

    def record_blocker(self, blocker_type: str, description: str):
        """Record blocker. Format: block:type:desc"""
        code = f"block:{blocker_type}:{description}".replace(" ", "-")
        if code not in self.blockers:
            self.blockers.append(code)
            self._sync_to_db()

    def record_file_modified(self, file_path: str):
        """Track files modified. Format: impl:filename"""
        code = f"impl:{Path(file_path).name}"
        if code not in self.files_modified:
            self.files_modified.append(code)
            self._sync_to_db()

    def record_function(self, func_name: str):
        """Track functions. Format: impl:func_name"""
        code = f"impl:{func_name}"
        if code not in self.key_functions:
            self.key_functions.append(code)
            self._sync_to_db()

    def to_context(self, phase: Optional[str] = None) -> SessionContext:
        """Convert to SessionContext object."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        row = conn.execute("""
            SELECT * FROM sessions WHERE id = ?
        """, (self.session_id,)).fetchone()

        conn.close()

        return SessionContext(
            id=self.session_id,
            scope=self.scope,
            project_path=self.project_path,
            phase=phase,
            completed=self.completed,
            next_actions=self.next_actions,
            decisions=self.decisions,
            blockers=self.blockers,
            files_modified=self.files_modified,
            key_functions=self.key_functions,
            created_at=datetime.fromisoformat(row['created_at']),
            last_accessed=datetime.fromisoformat(row['last_accessed']),
            last_activity=datetime.fromisoformat(row['last_activity']),
            turn_count=row['turn_count'],
            status=row['status']
        )
```

---

## Context Injection (NO LLM)

```python
class SessionContextInjector:
    """
    Load codes from SQLite, inject at session start.
    NO LLM. NO PROSE. Pure data injection.
    """

    def __init__(self, db_path: Path = Path.home() / ".cerberus" / "memory.db"):
        self.db_path = db_path

    def inject(self, scope: Optional[str] = None) -> Optional[InjectionPackage]:
        """
        Load codes for injection. Return None if no active session.

        Args:
            scope: Optional scope override. If None, auto-detects.
        """
        if scope is None:
            scope, _ = detect_session_scope()

        context = self._load_active_session(scope)

        if not context:
            return None

        # Check if idle (>7 days since last access)
        if self._is_idle(context):
            self._archive_session(context['id'])
            return None

        # Update last_accessed
        self._touch_session(context['id'])

        codes = self._format_codes(context)
        token_count = self._count_tokens(codes)

        return InjectionPackage(
            codes=codes,
            token_count=token_count,
            session_id=context['id'],
            scope=context['scope']
        )

    def _load_active_session(self, scope: str) -> Optional[Dict]:
        """Load active session from SQLite."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        row = conn.execute("""
            SELECT * FROM sessions
            WHERE scope = ? AND status = 'active'
        """, (scope,)).fetchone()

        conn.close()

        if not row:
            return None

        return dict(row)

    def _is_idle(self, session: Dict) -> bool:
        """Check if session idle (>7 days since last access)."""
        try:
            last_accessed = datetime.fromisoformat(session['last_accessed'])
            return (datetime.now() - last_accessed).days > 7
        except (ValueError, TypeError):
            return True

    def _archive_session(self, session_id: str):
        """Archive idle session."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE sessions
            SET status = 'archived'
            WHERE id = ?
        """, (session_id,))
        conn.commit()
        conn.close()

    def _touch_session(self, session_id: str):
        """Update last_accessed timestamp."""
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE sessions
            SET last_accessed = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (session_id,))
        conn.commit()
        conn.close()

    def _format_codes(self, session: Dict) -> str:
        """
        Format codes for injection.
        NO PROSE. NO MARKDOWN. Pure data.
        """
        data = json.loads(session['context_data'])

        lines = [f"scope:{session['scope']}"]

        if session['phase']:
            lines.append(f"phase:{session['phase']}")

        for item in data.get("files", []):
            lines.append(item)
        for item in data.get("functions", []):
            lines.append(item)
        for item in data.get("decisions", []):
            lines.append(item)
        for item in data.get("blockers", []):
            lines.append(item)
        for item in data.get("next_actions", []):
            lines.append(item)
        for item in data.get("completed", []):
            lines.append(f"done:{item}")

        return "\n".join(lines)

    def _count_tokens(self, text: str) -> int:
        """Count tokens (rough estimate)."""
        return int(len(text.split()) * 1.3)

    def mark_complete(self, scope: Optional[str] = None):
        """Mark session as completed (archived)."""
        import sqlite3

        if scope is None:
            scope, _ = detect_session_scope()

        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE sessions
            SET status = 'archived'
            WHERE scope = ? AND status = 'active'
        """, (scope,))
        conn.commit()
        conn.close()
```

---

## Auto-Capture Integration

```python
class AutoCapture:
    """
    Automatically capture session context from tool usage.
    Called by MCP tool handlers.
    """

    def __init__(self):
        self.capture = SessionContextCapture()

    def on_tool_use(self, tool_name: str, params: Dict, result: Any):
        """
        Hook called after each tool use.
        Auto-capture relevant context.
        """
        # File modifications
        if tool_name in ["Edit", "Write"]:
            file_path = params.get("file_path")
            if file_path:
                self.capture.record_file_modified(file_path)

        # Function implementations (detect from Write/Edit content)
        if tool_name in ["Write", "Edit"]:
            content = params.get("content", "") + params.get("new_string", "")
            import re
            funcs = re.findall(r'def\s+(\w+)|func\s+(\w+)|function\s+(\w+)', content)
            for match in funcs:
                func_name = next(f for f in match if f)
                self.capture.record_function(func_name)

        # Test execution
        if tool_name == "Bash":
            cmd = params.get("command", "")
            if "test" in cmd or "pytest" in cmd or "go test" in cmd:
                self.capture.record_completion(f"test:{cmd.split()[0]}")

    def on_user_message(self, message: str):
        """
        Hook called on user message.
        Detect decisions, blockers, next actions.
        """
        msg_lower = message.lower()

        if any(kw in msg_lower for kw in ["let's use", "we'll use", "decision:"]):
            self.capture.record_decision("user_specified", "explicit")

        if any(kw in msg_lower for kw in ["blocked", "unclear", "need", "issue"]):
            self.capture.record_blocker("user_reported", message[:30])

    def get_context(self, phase: Optional[str] = None) -> SessionContext:
        """Get captured context."""
        return self.capture.to_context(phase)
```

---

## Cleanup Manager

```python
class SessionCleanupManager:
    """Auto-cleanup idle sessions."""

    def __init__(self, db_path: Path = Path.home() / ".cerberus" / "memory.db"):
        self.db_path = db_path

    def cleanup_idle(self, days: int = 7) -> int:
        """
        Archive all idle sessions (>N days since last access).

        Returns:
            Count of sessions archived
        """
        import sqlite3

        conn = sqlite3.connect(self.db_path)

        cutoff = datetime.now() - timedelta(days=days)

        result = conn.execute("""
            UPDATE sessions
            SET status = 'archived'
            WHERE status = 'active'
            AND last_accessed < ?
        """, (cutoff.isoformat(),))

        count = result.rowcount
        conn.commit()
        conn.close()

        return count
```

---

## Integration Pipeline

```python
def on_session_start(scope: Optional[str] = None) -> Optional[str]:
    """
    Load session context at session start.
    Returns codes for injection or None.

    Called by Phase 7 (memory_context MCP tool).
    """
    injector = SessionContextInjector()
    package = injector.inject(scope)

    if package:
        return package.codes
    return None
```

---

## Integration with Phase 7

```python
def inject_all(scope: Optional[str] = None) -> str:
    """
    Combined injection: Memory (Phase 7) + Session (Phase 8).

    Called by memory_context() MCP tool.
    """
    if scope is None:
        scope, _ = detect_session_scope()

    # Phase 7: Memory injection
    memory_context = memory_injector.inject_by_scope(scope)

    # Phase 8: Session injection
    session_pkg = session_injector.inject(scope)

    parts = []
    if memory_context:
        parts.append(memory_context)
    if session_pkg:
        parts.append(session_pkg.codes)

    return "\n\n".join(parts)
```

**Token budget:** Memory (1500) + Session (1000-1500) = 2500-3000 tokens max

---

## MCP Tools

**Extension to Phase 7 tool:**

```python
@mcp_tool
def memory_context(scope: Optional[str] = None) -> str:
    """
    Load memories + active session for current scope.

    Auto-detects scope (global vs project) if not specified.
    """
    return inject_all(scope)

@mcp_tool
def session_history(scope: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """
    List recent sessions for scope.

    Returns:
        List of {id, scope, created_at, last_accessed, turn_count, status}
    """
    import sqlite3

    if scope is None:
        scope, _ = detect_session_scope()

    db_path = Path.home() / ".cerberus" / "memory.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT id, scope, created_at, last_accessed, turn_count, status
        FROM sessions
        WHERE scope = ?
        ORDER BY last_accessed DESC
        LIMIT ?
    """, (scope, limit)).fetchall()

    conn.close()

    return [dict(row) for row in rows]

@mcp_tool
def session_resume(session_id: str) -> str:
    """
    Resume archived session (load context codes).

    Returns:
        Session codes as plain text
    """
    import sqlite3

    db_path = Path.home() / ".cerberus" / "memory.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    row = conn.execute("""
        SELECT scope, context_data, phase FROM sessions WHERE id = ?
    """, (session_id,)).fetchone()

    conn.close()

    if not row:
        return "Session not found"

    data = json.loads(row['context_data'])
    lines = [f"scope:{row['scope']}"]

    if row['phase']:
        lines.append(f"phase:{row['phase']}")

    for key in ["files", "functions", "decisions", "blockers", "next_actions"]:
        for item in data.get(key, []):
            lines.append(item)

    return "\n".join(lines)
```

---

## Token Budget Allocation

**Session context budget: 1000-1500 tokens**

```
Files:          300-500 tokens (ALL files modified)
Functions:      200-400 tokens (ALL functions touched)
Decisions:      200-300 tokens (ALL decisions made)
Blockers:       100-200 tokens (ALL blockers)
Next actions:   100-200 tokens (ALL next actions)
Metadata:        50-100 tokens (scope, phase)
────────────────────────────────────────────────────
Total:         1000-1500 tokens (comprehensive)
```

**Why generous budget:**
- Goal is ZERO re-explanation
- Worth extra tokens to maintain momentum
- No LLM cost (pure data)
- Persistent across sessions (not temporary)

---

## Injection Format Example

**Stored in SQLite:**
```json
{
  "files": ["impl:proxy.go", "impl:supervisor.go"],
  "functions": ["impl:supervisor.Process", "impl:config.Load"],
  "decisions": ["dec:split-proxy-3-files", "dec:plan-splits-before-writing"],
  "blockers": ["block:race:test-failure-line-712"],
  "next_actions": ["next:add-mutex-to-process-struct", "next:rerun-race-detector"],
  "completed": ["impl:proxy-split", "test:unit-tests"]
}
```

**Injected:**
```
scope:project:hydra
phase:proxy-refactor
impl:proxy.go
impl:supervisor.go
impl:supervisor.Process
impl:config.Load
dec:split-proxy-3-files
dec:plan-splits-before-writing
block:race:test-failure-line-712
next:add-mutex-to-process-struct
next:rerun-race-detector
done:impl:proxy-split
done:test:unit-tests
```

**Agent reads:** Project hydra, proxy refactor phase, files touched, decisions made, race blocker, next actions, completed items.
**Zero re-explanation needed.**

---

## Concurrent Sessions Example

**User workflow:**
1. Working on `project:cerberus` (session A active)
2. Switch to `project:hydra` (session B active, A remains)
3. Switch to `/tmp/brainstorm` (global session C active, A+B remain)
4. Back to `project:cerberus` (resume session A)

**Storage:**
```sql
sessions table:
id          | scope              | status  | last_accessed
session-abc | project:cerberus   | active  | 2026-01-22 14:00
session-def | project:hydra      | active  | 2026-01-22 14:15
session-ghi | global             | active  | 2026-01-22 14:30
```

**No data loss. All sessions preserved.**

---

## Exit Criteria

```
✓ SQLite schema added to Phase 12
✓ SessionContextCapture using SQLite
✓ AutoCapture integration working
✓ SessionContextInjector using SQLite
✓ SessionCleanupManager using SQLite
✓ Scope detection (global vs project) working
✓ Concurrent sessions working (multiple projects)
✓ Save/load from SQLite working
✓ Idle detection (7 days) working
✓ Archival working (status='archived')
✓ Integration with Phase 7 complete
✓ MCP tools: memory_context, session_history, session_resume
✓ Migration from JSON (Phase 12) complete
✓ Token budget: 1000-1500 tokens
✓ Tests: 15 scenarios (includes concurrent sessions)
```

---

## Test Scenarios

```python
# Scenario 1: Basic capture (project scope)
cd ~/projects/cerberus
session: implemented 3 functions, modified 2 files
→ expect: context with scope="project:cerberus", files=[impl:f1, impl:f2], functions=[...]

# Scenario 2: Global scope
cd /tmp/notes
session: brainstorming ideas
→ expect: context with scope="global"

# Scenario 3: Save and load (same project)
cd ~/projects/hydra
save context
→ exit and restart
→ load on next session
→ expect: same codes returned, session resumed

# Scenario 4: Concurrent sessions
cd ~/projects/cerberus (session A)
→ cd ~/projects/hydra (session B)
→ cd ~/projects/cerberus (back to A)
→ expect: session A context restored, B still active

# Scenario 5: Idle detection
session: last_accessed 8 days ago
→ expect: archived, not returned

# Scenario 6: Multiple scopes
sessions: global, project:cerberus, project:hydra
→ load project:cerberus
→ expect: only cerberus codes returned

# Scenario 7: Migration from JSON
existing: active-cerberus.json, active-hydra.json
→ run Phase 12 migration
→ expect: both in SQLite, JSON archived

# Scenario 8: Session history
3 sessions: archived, archived, active
→ session_history(scope="project:hydra")
→ expect: list of 3 sessions, sorted by last_accessed

# Scenario 9: Session resume
archived session_id
→ session_resume(session_id)
→ expect: codes returned

# Scenario 10: Cleanup idle
3 sessions: active (5 days), active (8 days), active (10 days)
→ cleanup_idle(days=7)
→ expect: 2 archived, 1 active remains

# Scenario 11: Token budget
context: 15 files, 8 decisions, 3 blockers
→ expect: total < 1500 tokens

# Scenario 12: Integration with Phase 7
session codes: 1000-1500 tokens
memory injection: 1500 tokens
→ memory_context()
→ expect: combined < 3000 tokens

# Scenario 13: Scope detection
cd ~/projects/cerberus/.git/../src
→ detect_session_scope()
→ expect: ("project:cerberus", "/Users/user/projects/cerberus")

# Scenario 14: No active session
new project, no previous session
→ inject()
→ expect: None, no error

# Scenario 15: Concurrent terminals
Terminal 1: cd ~/projects/cerberus (session A)
Terminal 2: cd ~/projects/hydra (session B)
→ both active simultaneously
→ expect: no conflicts, no overwrites
```

---

## Dependencies

- Phase 7 (ContextInjector for memory integration)
- Phase 12 (SQLite schema, migration)
- Phase 6 (MemoryRetrieval used by Phase 7)

---

## Performance

- Load codes: < 10ms (SQLite read)
- Format codes: < 1ms (string join)
- Save codes: < 10ms (SQLite write)
- Cleanup idle: < 50ms (SQLite UPDATE)
- Scope detection: < 5ms (filesystem walk)
