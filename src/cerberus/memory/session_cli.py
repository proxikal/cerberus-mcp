"""
Session CLI - Command-line Interface for Session Management

This module provides CLI commands for manual session operations and crash recovery.
It wraps session_continuity.py (core implementation) with a user-friendly CLI interface.

Key features:
- Session start/end detection
- Crash detection and auto-recovery
- Idle timeout monitoring
- Session history and analytics

CRITICAL ARCHITECTURE:
- ALL storage: ~/.cerberus/memory.db (SQLite database)
- NO temp files - everything in memory.db
- Sessions and session_activity tables

Zero file touching during session - only SQLite writes.
"""

import sqlite3
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from cerberus.memory.session_continuity import (
    SessionContextCapture,
    detect_session_scope
)


# ============================================================================
# Configuration
# ============================================================================

SESSION_TIMEOUTS = {
    "stale_detection_seconds": 300,   # 5 minutes - crashed session detection
    "idle_timeout_minutes": 30,       # 30 minutes - active session timeout
    "check_interval_seconds": 60      # 60 seconds - daemon check frequency
}

DB_PATH = Path.home() / ".cerberus" / "memory.db"


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class SessionState:
    """Session state (for compatibility with CLI)."""
    session_id: str
    working_directory: str
    project_name: Optional[str]
    language: Optional[str]
    started_at: datetime
    last_activity: datetime
    turn_count: int
    corrections: List[Dict[str, Any]]
    tools_used: List[str]
    modified_files: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat()
        data["last_activity"] = self.last_activity.isoformat()
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SessionState":
        """Create from dictionary."""
        data["started_at"] = datetime.fromisoformat(data["started_at"])
        data["last_activity"] = datetime.fromisoformat(data["last_activity"])
        return SessionState(**data)


# ============================================================================
# Session Start
# ============================================================================

def start_session(
    working_directory: Optional[str] = None,
    project_name: Optional[str] = None,
    language: Optional[str] = None
) -> SessionState:
    """
    Initialize new session (SQLite only).

    Args:
        working_directory: Working directory (defaults to cwd)
        project_name: Project name (optional)
        language: Primary language (optional)

    Returns:
        SessionState for the new session
    """
    working_directory = working_directory or str(Path.cwd())

    # Create session capture (handles SQLite)
    capture = SessionContextCapture(db_path=DB_PATH)

    # Build state
    state = SessionState(
        session_id=capture.session_id,
        working_directory=working_directory,
        project_name=project_name or Path(working_directory).name,
        language=language,
        started_at=datetime.now(),
        last_activity=datetime.now(),
        turn_count=0,
        corrections=[],
        tools_used=[],
        modified_files=[]
    )

    return state


# ============================================================================
# Session End
# ============================================================================

def end_session(reason: str = "explicit") -> Optional[SessionState]:
    """
    End active session (SQLite only).

    Args:
        reason: Reason for ending ("explicit", "idle", "crashed")

    Returns:
        SessionState if session was active, None otherwise
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        scope, project_path = detect_session_scope()

        # Get active session
        row = conn.execute("""
            SELECT id, project_path, context_data, created_at, last_activity, turn_count
            FROM sessions
            WHERE scope = ? AND status = 'active'
        """, (scope,)).fetchone()

        if not row:
            return None

        # Mark as ended
        conn.execute("""
            UPDATE sessions
            SET status = ?, last_activity = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (reason, row['id']))

        conn.commit()

        # Build state for return
        state = SessionState(
            session_id=row['id'],
            working_directory=str(Path.cwd()),
            project_name=Path(row['project_path'] or ".").name,
            language=None,
            started_at=datetime.fromisoformat(row['created_at']),
            last_activity=datetime.fromisoformat(row['last_activity']),
            turn_count=row['turn_count'],
            corrections=[],
            tools_used=[],
            modified_files=[]
        )

        return state
    finally:
        conn.close()


# ============================================================================
# Session Status
# ============================================================================

def get_session_state_info() -> Optional[Dict[str, Any]]:
    """
    Get information about active session.

    Returns:
        Dict with session info, or None if no active session
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        scope, _ = detect_session_scope()

        row = conn.execute("""
            SELECT id, project_path, created_at, last_activity, turn_count
            FROM sessions
            WHERE scope = ? AND status = 'active'
        """, (scope,)).fetchone()

        if not row:
            return None

        started_at = datetime.fromisoformat(row['created_at'])
        last_activity = datetime.fromisoformat(row['last_activity'])
        now = datetime.now()

        return {
            "session_id": row['id'],
            "started_at": started_at.isoformat(),
            "duration_minutes": (now - started_at).total_seconds() / 60,
            "idle_minutes": (now - last_activity).total_seconds() / 60,
            "project_name": Path(row['project_path'] or ".").name,
            "language": None,
            "turn_count": row['turn_count'],
            "correction_count": 0,
            "tools_used_count": 0,
            "modified_files_count": 0
        }
    finally:
        conn.close()


# ============================================================================
# Crash Recovery
# ============================================================================

def list_crashed_sessions(working_directory: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List crashed sessions.

    Returns:
        List of crashed session info dicts
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute("""
            SELECT id, scope, project_path, created_at, last_activity
            FROM sessions
            WHERE status = 'crashed'
            ORDER BY last_activity DESC
        """).fetchall()

        return [{
            "session_id": row['id'],
            "scope": row['scope'],
            "project_path": row['project_path'],
            "crashed_at": row['last_activity'],
            "correction_count": 0
        } for row in rows]
    finally:
        conn.close()


def recover_crashed_session(session_id: str, discard: bool = False) -> bool:
    """
    Recover or discard a crashed session.

    Args:
        session_id: Session ID to recover
        discard: If True, discard the session. If False, mark as recovered.

    Returns:
        True if successful, False otherwise
    """
    conn = sqlite3.connect(DB_PATH)

    try:
        if discard:
            # Delete the session
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        else:
            # Mark as recovered (archived)
            conn.execute("""
                UPDATE sessions
                SET status = 'archived'
                WHERE id = ?
            """, (session_id,))

        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# ============================================================================
# Session Activity Tracking
# ============================================================================

def update_session_activity(
    activity_type: str,
    activity_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Record session activity (SQLite only).

    Args:
        activity_type: Type of activity ("correction", "tool_use", "file_modified")
        activity_data: Optional activity metadata
    """
    try:
        capture = SessionContextCapture(db_path=DB_PATH)

        # Record in session_activity table
        conn = sqlite3.connect(DB_PATH)

        # Increment turn count
        conn.execute("""
            UPDATE sessions
            SET turn_count = turn_count + 1, last_activity = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (capture.session_id,))

        # Log activity
        import json
        conn.execute("""
            INSERT INTO session_activity (session_id, activity_type, activity_data)
            VALUES (?, ?, ?)
        """, (capture.session_id, activity_type, json.dumps(activity_data) if activity_data else None))

        conn.commit()
        conn.close()
    except Exception:
        # Silently fail - don't disrupt operations
        pass
