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
