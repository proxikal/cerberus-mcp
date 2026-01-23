# PHASE 17: SESSION LIFECYCLE & RECOVERY

## Objective
Define session boundaries, detect session end, handle crashes, implement recovery mechanisms.

---

## Implementation Location

**File:** `src/cerberus/memory/session_lifecycle.py`

---

## Phase Assignment

**Rollout:** Phase Epsilon (Post-Delta)

**Prerequisites:**
- ✅ Phase 16 complete (integration hooks working)
- ✅ Phase 1 complete (correction detection tracking turns)

**Why Phase Epsilon:**
- Session management needed for reliable correction detection
- Crash recovery prevents data loss
- Can be added after basic hooks work

---

## Session Boundary Detection

### Session Start Triggers

```python
SESSION_START_TRIGGERS = [
    "cli_process_start",     # CLI binary execution
    "explicit_start_command", # User runs `cerberus memory session-start`
    "hook_execution",        # session-start.sh hook fires
]
```

### Session End Triggers

```python
SESSION_END_TRIGGERS = [
    "cli_process_exit",      # CLI binary terminates (SIGTERM, SIGINT)
    "explicit_end_command",  # User runs `cerberus memory session-end`
    "idle_timeout",          # No activity for N minutes
    "crash_detection",       # Process killed (SIGKILL) or unexpected exit
]
```

### Session Timeout Configuration

```python
# Configurable timeout values (can be overridden via environment or config)
SESSION_TIMEOUTS = {
    "stale_detection_seconds": 300,   # 5 minutes - crashed session detection
    "idle_timeout_minutes": 30,       # 30 minutes - active session timeout
    "check_interval_seconds": 60      # 60 seconds - daemon check frequency
}
```

**Timeout Purposes:**
- **stale_detection** (5 min): Detect crashed sessions on startup (session file exists but old)
- **idle_timeout** (30 min): Auto-end active sessions with no activity
- **check_interval** (60 sec): How often daemon checks for idle timeout

---

## Data Structures

```python
@dataclass
class SessionState:
    """Active session state."""
    session_id: str
    started_at: datetime
    last_activity: datetime
    working_directory: str
    project_name: Optional[str]
    language: Optional[str]
    turn_count: int
    corrections: List[CorrectionCandidate]
    tools_used: List[str]  # ["Read", "Write", "Edit", "Bash"]
    modified_files: List[str]
    status: str  # "active", "idle", "crashed", "ended"

@dataclass
class SessionRecovery:
    """Crash recovery state."""
    session_id: str
    crashed_at: datetime
    last_known_state: SessionState
    recovery_actions: List[str]  # ["propose", "archive", "discard"]
    auto_recovered: bool
```

---

## Session Lifecycle Implementation

### Session Start

```python
def start_session(context: HookContext) -> SessionState:
    """
    Initialize new session.

    Strategy:
    1. Check for crashed session (stale .cerberus-session.json)
    2. If crashed: Mark in global DB (~/.cerberus/memory.db), delete temp file
    3. Initialize new session state
    4. Write to .cerberus-session.json (temp runtime)
    5. Create session record in global DB

    Note: All persistent session data stored in ~/.cerberus/memory.db

    Returns:
        SessionState object
    """
    import fcntl
    from pathlib import Path

    # Check for existing session
    session_file = Path(".cerberus-session.json")

    if session_file.exists():
        # Previous session didn't end cleanly
        old_state = _load_session_state(session_file)

        # Check if it's actually stale (not a race condition)
        age_seconds = (datetime.now() - old_state.last_activity).total_seconds()
        stale_threshold = SESSION_TIMEOUTS["stale_detection_seconds"]

        if age_seconds > stale_threshold:  # Default 5 minutes
            # Crashed session detected
            _handle_crashed_session(old_state)

    # Initialize new session
    state = SessionState(
        session_id=_generate_session_id(),
        started_at=datetime.now(),
        last_activity=datetime.now(),
        working_directory=context.working_directory,
        project_name=context.project_name,
        language=context.language,
        turn_count=0,
        corrections=[],
        tools_used=[],
        modified_files=[],
        status="active"
    )

    # Write state (with file lock to prevent races)
    _write_session_state(state, session_file)

    return state


def _handle_crashed_session(old_state: SessionState) -> None:
    """
    Handle crashed session recovery.

    Strategy:
    1. Update session in global DB: status='crashed', ended_at=now
    2. If corrections exist: Keep in DB for recovery
    3. Delete temp .cerberus-session.json file
    4. Log crash event

    All data is in ~/.cerberus/memory.db, not local files.
    """
    db_path = Path.home() / ".cerberus" / "memory.db"

    # Update session status in global DB
    # UPDATE sessions SET status='crashed', ended_at=? WHERE session_id=?

    if old_state.corrections:
        print(f"Recovered crashed session: {old_state.session_id}")
        print(f"Found {len(old_state.corrections)} corrections.")
        print("Session data saved to global DB. Run `cerberus memory recover` to process.")
    else:
        print(f"Cleaned up stale session: {old_state.session_id}")
```

---

### Session Activity Tracking

```python
def update_session_activity(
    action: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Update session state with activity.

    Called after each user/AI turn.

    Args:
        action: "correction", "tool_use", "file_modified"
        details: Action-specific data
    """
    state = _load_session_state()

    # Update timestamp
    state.last_activity = datetime.now()
    state.turn_count += 1

    # Record action
    if action == "correction":
        state.corrections.append(details["candidate"])
    elif action == "tool_use":
        state.tools_used.append(details["tool"])
    elif action == "file_modified":
        state.modified_files.append(details["file_path"])

    # Write back
    _write_session_state(state)
```

---

### Session End

```python
def end_session(trigger: str) -> SessionState:
    """
    End session and cleanup.

    Strategy:
    1. Load session state
    2. Mark as ended
    3. Archive session
    4. Remove active state file
    5. Return final state for proposal hook

    Args:
        trigger: Reason for ending ("explicit", "timeout", "process_exit")

    Returns:
        Final SessionState
    """
    state = _load_session_state()

    # Update session in global DB
    db_path = Path.home() / ".cerberus" / "memory.db"
    ended_at = datetime.now()

    # UPDATE sessions SET
    #   status='completed',
    #   ended_at=?,
    #   end_trigger=?,
    #   turn_count=?
    # WHERE session_id=?

    # Delete temp runtime file
    Path(".cerberus-session.json").unlink(missing_ok=True)

    # All session history is in ~/.cerberus/memory.db
    return state
```

---

## Idle Timeout Detection

```python
def check_idle_timeout(timeout_minutes: int = 30) -> bool:
    """
    Check if session has been idle too long.

    Strategy:
    1. Load session state
    2. Check last_activity timestamp
    3. If > timeout_minutes, trigger session end

    Returns:
        True if session should end, False otherwise
    """
    try:
        state = _load_session_state()
    except FileNotFoundError:
        return False

    idle_seconds = (datetime.now() - state.last_activity).total_seconds()
    idle_minutes = idle_seconds / 60

    if idle_minutes > timeout_minutes:
        print(f"Session idle for {idle_minutes:.1f} minutes. Ending session.")
        return True

    return False


# Background task (optional)
def idle_timeout_daemon(interval_seconds: int = 60, timeout_minutes: int = 30) -> None:
    """
    Background daemon to check idle timeout.

    Runs in separate thread, checks every interval_seconds.
    """
    import time
    import threading

    def check_loop():
        while True:
            time.sleep(interval_seconds)

            if check_idle_timeout(timeout_minutes):
                # Trigger session end
                state = end_session("timeout")

                # Run proposal hook
                from cerberus.memory.hooks import propose_hook
                propose_hook()

    thread = threading.Thread(target=check_loop, daemon=True)
    thread.start()
```

---

