"""
PHASE 8: SESSION CONTINUITY

Capture session context during work, inject at next session start.
Zero re-explanation needed. NO LLM.

Multi-tier session scopes:
- Global scope: Brainstorming, non-project work
- Project scope: Project-specific work (per git repo)
- Concurrent sessions: Multiple projects simultaneously

Storage: SQLite (unified with Phase 12 memory database)
"""

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class SessionContext:
    """Active session context."""
    id: str  # UUID
    scope: str  # "universal" or "project:{name}"
    project_path: Optional[str]  # Full path to project root (NULL for universal)
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


# ============================================================================
# Session Cleanup Configuration
# ============================================================================

SESSION_ARCHIVE_THRESHOLDS = {
    "idle_days": 7,  # Days before archiving idle sessions (default)
}


# ============================================================================
# Scope Detection
# ============================================================================

def detect_session_scope() -> tuple[str, Optional[str]]:
    """
    Detect session scope (universal vs project).

    Strategy:
    1. Check if in git repo (walk up to find .git)
    2. If in git repo → project scope (use repo name + path)
    3. If not in git repo → universal scope

    Returns:
        (scope, project_path)
        Examples:
            ("universal", None)
            ("project:cerberus", "/Users/user/dev/cerberus")
    """
    cwd = Path.cwd()

    # Walk up to find .git
    current = cwd
    while current != current.parent:
        if (current / ".git").exists():
            # Found git repo
            project_name = current.name
            return f"project:{project_name}", str(current)
        current = current.parent

    # Not in git repo → universal scope
    return "universal", None


# ============================================================================
# Context Capture
# ============================================================================

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
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Check for active session
        row = conn.execute("""
            SELECT id, context_data FROM sessions
            WHERE scope = ? AND status = 'active'
        """, (self.scope,)).fetchone()

        if row:
            conn.close()
            return row['id']

        # Create new session
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
        code = f"next:{action}" if not action.startswith("next:") else action
        if code not in self.next_actions:
            self.next_actions.append(code)
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


# ============================================================================
# Context Injection (NO LLM)
# ============================================================================

class SessionContextInjector:
    """
    Load codes from SQLite, inject at session start.
    NO LLM. NO PROSE. Pure data injection.
    """

    def __init__(
        self,
        db_path: Path = Path.home() / ".cerberus" / "memory.db",
        idle_days: int = 7
    ):
        self.db_path = db_path
        self.idle_days = idle_days  # Configurable archive threshold

    def inject(self, scope: Optional[str] = None) -> Optional[InjectionPackage]:
        """
        Load codes for injection. Return None if no active session.

        CRITICAL: Deletes session after reading (read-once, dispose).

        Args:
            scope: Optional scope override. If None, auto-detects.
        """
        if scope is None:
            scope, _ = detect_session_scope()

        context = self._load_active_session(scope)

        if not context:
            return None

        # Check if idle (configurable threshold)
        if self._is_idle(context, self.idle_days):
            self._delete_session(context['id'])
            return None

        # Format codes before deleting
        codes = self._format_codes(context)
        token_count = self._count_tokens(codes)

        # Delete session after reading (read-once, dispose)
        self._delete_session(context['id'])

        return InjectionPackage(
            codes=codes,
            token_count=token_count,
            session_id=context['id'],
            scope=context['scope']
        )

    def _load_active_session(self, scope: str) -> Optional[Dict]:
        """Load active session from SQLite."""
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

    def _is_idle(self, session: Dict, idle_days: int = 7) -> bool:
        """Check if session idle (>N days since last access).

        Args:
            session: Session dict with last_accessed timestamp
            idle_days: Days threshold for considering session idle (default 7)
        """
        try:
            last_accessed = datetime.fromisoformat(session['last_accessed'])
            return (datetime.now() - last_accessed).days > idle_days
        except (ValueError, TypeError):
            return True

    def _delete_session(self, session_id: str):
        """
        Delete session after reading (read-once, dispose).

        This prevents database bloat from accumulating sessions.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.execute("DELETE FROM session_activity WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    def _format_codes(self, session: Dict) -> str:
        """
        Format HYBRID codes + details for injection.

        Part 1: Semantic codes (compressed skeleton)
        Part 2: Structured details (why/how/where context)

        NO PROSE. Pure structured data.

        Order: scope → work_streams → files → decisions → blockers → next_actions → completed → details
        """
        data = json.loads(session['context_data'])

        lines = [f"scope:{session['scope']}"]

        if session['phase']:
            lines.append(f"phase:{session['phase']}")

        # Major work streams first (big picture)
        for item in data.get("work_streams", []):
            lines.append(item)

        # Files modified (with context)
        for item in data.get("files", []):
            lines.append(item)

        # Decisions
        for item in data.get("decisions", []):
            lines.append(item)

        # Blockers
        for item in data.get("blockers", []):
            lines.append(item)

        # Next actions
        for item in data.get("next_actions", []):
            lines.append(item)

        # Completions (already have "done:" prefix)
        for item in data.get("completed", []):
            lines.append(item)

        # Add structured details if present (hybrid format)
        if session.get('summary_details'):
            lines.append("")  # Blank line separator
            lines.append(session['summary_details'])

        return "\n".join(lines)

    def _count_tokens(self, text: str) -> int:
        """Count tokens (rough estimate)."""
        return int(len(text.split()) * 1.3)

    def mark_complete(self, scope: Optional[str] = None):
        """Mark session as completed (delete it)."""
        if scope is None:
            scope, _ = detect_session_scope()

        conn = sqlite3.connect(self.db_path)

        # Get session ID first
        row = conn.execute("""
            SELECT id FROM sessions
            WHERE scope = ? AND status = 'active'
        """, (scope,)).fetchone()

        if row:
            session_id = row[0]
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.execute("DELETE FROM session_activity WHERE session_id = ?", (session_id,))

        conn.commit()
        conn.close()


# ============================================================================
# Auto-Capture Integration
# ============================================================================

class AutoCapture:
    """
    Automatically capture session context from tool usage.
    Called by MCP tool handlers.
    """

    def __init__(self, db_path: Path = Path.home() / ".cerberus" / "memory.db"):
        self.capture = SessionContextCapture(db_path=db_path)

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


# ============================================================================
# Cleanup Manager
# ============================================================================

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


# ============================================================================
# Integration Functions
# ============================================================================

def on_session_start(scope: Optional[str] = None, db_path: Path = Path.home() / ".cerberus" / "memory.db") -> Optional[str]:
    """
    Load session context at session start.
    Returns codes for injection or None.

    Called by Phase 7 (memory_context MCP tool).
    """
    injector = SessionContextInjector(db_path=db_path)
    package = injector.inject(scope)

    if package:
        return package.codes
    return None


def inject_all(scope: Optional[str] = None) -> str:
    """
    Combined injection: Memory (Phase 7) + Session (Phase 8).

    Called by memory_context() MCP tool.

    Note: This is a placeholder. Full integration with Phase 7
    requires importing ContextInjector from context_injector.py.
    """
    if scope is None:
        scope, _ = detect_session_scope()

    # Phase 7: Memory injection (placeholder)
    # memory_context = memory_injector.inject_by_scope(scope)

    # Phase 8: Session injection
    session_injector = SessionContextInjector()
    session_pkg = session_injector.inject(scope)

    parts = []
    # if memory_context:
    #     parts.append(memory_context)
    if session_pkg:
        parts.append(session_pkg.codes)

    return "\n\n".join(parts) if parts else ""
