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
    1. Check for crashed session (stale .cerberus/session_active.json)
    2. If crashed, attempt recovery
    3. Initialize new session state
    4. Write to .cerberus/session_active.json

    Returns:
        SessionState object
    """
    import fcntl
    from pathlib import Path

    # Check for existing session
    session_file = Path(".cerberus/session_active.json")

    if session_file.exists():
        # Previous session didn't end cleanly
        old_state = _load_session_state(session_file)

        # Check if it's actually stale (not a race condition)
        age_seconds = (datetime.now() - old_state.last_activity).total_seconds()

        if age_seconds > 300:  # 5 minutes = definitely stale
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
    1. If corrections exist: Archive for manual review
    2. If no corrections: Discard
    3. Log crash event
    """
    if old_state.corrections:
        # Archive for recovery
        archive_dir = Path(".cerberus/sessions/crashed")
        archive_dir.mkdir(parents=True, exist_ok=True)

        archive_file = archive_dir / f"{old_state.session_id}.json"
        with open(archive_file, "w") as f:
            json.dump(asdict(old_state), f, indent=2, default=str)

        print(f"Recovered crashed session: {old_state.session_id}")
        print(f"Found {len(old_state.corrections)} corrections.")
        print(f"Archived to: {archive_file}")
        print("Run `cerberus memory recover` to process.")
    else:
        # No data to recover, just log
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

    # Mark ended
    state.status = "ended"
    ended_at = datetime.now()

    # Archive session
    archive_dir = Path(".cerberus/sessions/ended")
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_file = archive_dir / f"{state.session_id}.json"
    session_data = asdict(state)
    session_data["ended_at"] = ended_at.isoformat()
    session_data["end_trigger"] = trigger

    with open(archive_file, "w") as f:
        json.dump(session_data, f, indent=2, default=str)

    # Remove active state
    Path(".cerberus/session_active.json").unlink(missing_ok=True)

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

