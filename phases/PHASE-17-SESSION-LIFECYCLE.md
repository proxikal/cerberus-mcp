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

## Crash Detection & Recovery

### Crash Detection

```python
def detect_crash() -> Optional[SessionState]:
    """
    Detect if previous session crashed.

    Strategy:
    1. Check for .cerberus/session_active.json
    2. If exists and last_activity > 5 minutes ago, assume crash

    Returns:
        Crashed SessionState if detected, None otherwise
    """
    session_file = Path(".cerberus/session_active.json")

    if not session_file.exists():
        return None

    state = _load_session_state(session_file)

    # Check staleness
    age_seconds = (datetime.now() - state.last_activity).total_seconds()

    if age_seconds > 300:  # 5 minutes
        return state

    return None
```

### Auto-Recovery

```python
def auto_recover_crash(crashed_state: SessionState) -> SessionRecovery:
    """
    Automatically recover crashed session.

    Strategy:
    1. If corrections exist: Run proposal pipeline
    2. Archive original state
    3. Return recovery result

    Args:
        crashed_state: Crashed session state

    Returns:
        SessionRecovery result
    """
    recovery = SessionRecovery(
        session_id=crashed_state.session_id,
        crashed_at=datetime.now(),
        last_known_state=crashed_state,
        recovery_actions=[],
        auto_recovered=False
    )

    if crashed_state.corrections:
        # Attempt auto-recovery
        try:
            from cerberus.memory.semantic_analyzer import SemanticAnalyzer
            from cerberus.memory.proposal_engine import ProposalEngine
            from cerberus.memory.storage import MemoryStorage

            # Cluster corrections
            semantic = SemanticAnalyzer()
            clusters = semantic.cluster_corrections(crashed_state.corrections)

            # Generate proposals
            engine = ProposalEngine()
            proposals = engine.generate_proposals(clusters)

            # Auto-approve high-confidence proposals
            storage = MemoryStorage()
            high_confidence = [p for p in proposals if p.confidence >= 0.9]

            if high_confidence:
                storage.store_batch(high_confidence)
                recovery.recovery_actions.append(
                    f"auto-approved {len(high_confidence)} high-confidence proposals"
                )

            # Archive remaining for manual review
            if len(proposals) > len(high_confidence):
                archive_proposals(proposals, crashed_state.session_id)
                recovery.recovery_actions.append(
                    f"archived {len(proposals) - len(high_confidence)} proposals for review"
                )

            recovery.auto_recovered = True

        except Exception as e:
            recovery.recovery_actions.append(f"auto-recovery failed: {e}")

    return recovery
```

### Manual Recovery CLI

```bash
# List crashed sessions
cerberus memory recover --list

# Recover specific session
cerberus memory recover <session_id>

# Discard crashed session
cerberus memory recover <session_id> --discard
```

**Implementation:**
```python
def recover_crashed_session(session_id: str, discard: bool = False) -> None:
    """
    Manually recover crashed session.

    Args:
        session_id: Crashed session ID
        discard: If True, discard without processing
    """
    archive_file = Path(f".cerberus/sessions/crashed/{session_id}.json")

    if not archive_file.exists():
        print(f"No crashed session found: {session_id}")
        return

    if discard:
        archive_file.unlink()
        print(f"Discarded crashed session: {session_id}")
        return

    # Load state
    with open(archive_file, "r") as f:
        state_data = json.load(f)

    state = SessionState(**state_data)

    # Run proposal pipeline
    from cerberus.memory.hooks import propose_hook

    # Temporarily restore session state for proposal
    _write_session_state(state)

    # Run proposals
    propose_hook()

    # Cleanup
    archive_file.unlink()
    print(f"Recovered session: {session_id}")
```

---

## File Locking (Prevent Race Conditions)

```python
def _write_session_state(state: SessionState, file_path: Optional[Path] = None) -> None:
    """
    Write session state with file lock.

    Prevents race conditions from multiple processes.
    """
    import fcntl

    if file_path is None:
        file_path = Path(".cerberus/session_active.json")

    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Open with exclusive lock
    with open(file_path, "w") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(asdict(state), f, indent=2, default=str)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _load_session_state(file_path: Optional[Path] = None) -> SessionState:
    """
    Load session state with shared lock.
    """
    import fcntl

    if file_path is None:
        file_path = Path(".cerberus/session_active.json")

    with open(file_path, "r") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        data = json.load(f)
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    # Convert corrections back to dataclass
    if "corrections" in data:
        data["corrections"] = [
            CorrectionCandidate(**c) for c in data["corrections"]
        ]

    return SessionState(**data)
```

---

## Session History & Analytics

```python
def get_session_history(days: int = 7) -> List[Dict[str, Any]]:
    """
    Get session history for last N days.

    Returns:
        List of session summaries
    """
    archive_dir = Path(".cerberus/sessions/ended")

    if not archive_dir.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    sessions = []

    for file in archive_dir.glob("*.json"):
        with open(file, "r") as f:
            session = json.load(f)

        started = datetime.fromisoformat(session["started_at"])

        if started > cutoff:
            sessions.append({
                "session_id": session["session_id"],
                "started_at": session["started_at"],
                "ended_at": session.get("ended_at"),
                "duration_minutes": _calculate_duration(session),
                "correction_count": len(session["corrections"]),
                "tool_count": len(session["tools_used"]),
                "modified_files": len(session["modified_files"]),
            })

    return sorted(sessions, key=lambda s: s["started_at"], reverse=True)


def _calculate_duration(session: Dict[str, Any]) -> float:
    """Calculate session duration in minutes."""
    started = datetime.fromisoformat(session["started_at"])
    ended = datetime.fromisoformat(session.get("ended_at", datetime.now().isoformat()))
    duration = (ended - started).total_seconds() / 60
    return round(duration, 1)
```

---

## CLI Commands

```bash
# Manual session control
cerberus memory session-start
cerberus memory session-end

# Check session status
cerberus memory session-status

# Session history
cerberus memory session-history --days 7

# Crash recovery
cerberus memory recover --list
cerberus memory recover <session_id>
cerberus memory recover <session_id> --discard

# Cleanup old sessions
cerberus memory session-cleanup --older-than 30d
```

---

## Token Costs

**Session lifecycle operations:**
- Start/end session: 0 tokens (pure file I/O)
- Crash recovery: 0-500 tokens (if running proposal pipeline)
- Session tracking: 0 tokens (file updates)

**Total per session:** 0 tokens (lifecycle overhead is free)

---

## Validation Gates

**Phase 17 complete when:**
- ✅ Session start/end works reliably
- ✅ Crash detection works (stale session detected)
- ✅ Auto-recovery works (high-confidence proposals stored)
- ✅ Manual recovery works (user can recover crashed sessions)
- ✅ Idle timeout works (sessions end after inactivity)
- ✅ File locking prevents race conditions
- ✅ 10+ sessions tested (including deliberate crashes)

**Testing:**
- Manual crash test: SIGKILL during session, verify recovery
- Idle timeout test: Leave session idle, verify auto-end
- Race condition test: Multiple processes writing session state
- Recovery test: Crash with corrections, verify proposals generated

---

## Dependencies

**Phase Dependencies:**
- Phase 16 (Integration) - uses session hooks
- Phase 1 (Detection) - tracks corrections in session state

**External Dependencies:**
- None (pure Python file I/O)

---

## Implementation Checklist

- [ ] Write `src/cerberus/memory/session_lifecycle.py`
- [ ] Implement `start_session()` function
- [ ] Implement `end_session()` function
- [ ] Implement `update_session_activity()` function
- [ ] Implement crash detection (`detect_crash()`)
- [ ] Implement auto-recovery (`auto_recover_crash()`)
- [ ] Implement manual recovery CLI
- [ ] Implement idle timeout detection
- [ ] Implement file locking (prevent races)
- [ ] Implement session history/analytics
- [ ] Add CLI commands (`session-start`, `session-end`, `recover`)
- [ ] Write unit tests (start/end, crash detection)
- [ ] Write integration tests (full lifecycle with crash)
- [ ] Test deliberate crashes (SIGKILL, SIGTERM)
- [ ] Test idle timeout (30+ minute wait)
- [ ] Test race conditions (concurrent writes)

---

**Last Updated:** 2026-01-22
**Version:** 1.0
**Status:** Specification complete, ready for implementation in Phase Epsilon
