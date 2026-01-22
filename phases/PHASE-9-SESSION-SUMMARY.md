# PHASE 9: SESSION CONTEXT INJECTION

## Objective
Inject Phase 8 codes at session start. Pure data, no LLM, no prose. 1000-1500 token budget.

---

## Implementation Location

**File:** `src/cerberus/memory/session_injection.py`

---

## Data Structures

```python
@dataclass
class SessionContext:
    """Raw codes from Phase 8 capture."""
    session_id: str
    project: str
    timestamp: str
    files: List[str]  # impl:file.py codes
    functions: List[str]  # impl:module.func codes
    decisions: List[str]  # dec:choice codes
    blockers: List[str]  # block:type:desc codes
    next_actions: List[str]  # next:action codes
    metadata: Dict[str, Any]  # Additional context

@dataclass
class InjectionPackage:
    """Ready-to-inject codes."""
    codes: str  # Raw codes, newline-separated
    token_count: int
    session_id: str
    expires_at: str
```

---

## Session Context Injector

```python
class SessionContextInjector:
    """
    Load Phase 8 codes, inject at session start.
    NO LLM. NO PROSE. Pure data injection.
    """

    def __init__(self, base_path: Path):
        self.sessions_dir = base_path / "memory" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def inject(self, project: str) -> Optional[InjectionPackage]:
        """
        Load codes for injection. Return None if no active session.
        """
        # Load active session
        context = self._load_active_session(project)

        if not context:
            return None

        # Check expiry
        if self._is_expired(context):
            self._archive(context)
            return None

        # Format codes (minimal formatting, no prose)
        codes = self._format_codes(context)
        token_count = self._count_tokens(codes)

        return InjectionPackage(
            codes=codes,
            token_count=token_count,
            session_id=context.session_id,
            expires_at=context.metadata.get("expires_at")
        )

    def save_context(self, context: SessionContext):
        """
        Save Phase 8 codes to storage.
        """
        file_path = self.sessions_dir / f"active-{context.project}.json"

        data = {
            "session_id": context.session_id,
            "project": context.project,
            "timestamp": context.timestamp,
            "files": context.files,
            "functions": context.functions,
            "decisions": context.decisions,
            "blockers": context.blockers,
            "next_actions": context.next_actions,
            "metadata": {
                **context.metadata,
                "expires_at": self._calc_expiry()
            }
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_active_session(
        self,
        project: str
    ) -> Optional[SessionContext]:
        """
        Load active session codes.
        """
        file_path = self.sessions_dir / f"active-{project}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)

            return SessionContext(
                session_id=data["session_id"],
                project=data["project"],
                timestamp=data["timestamp"],
                files=data.get("files", []),
                functions=data.get("functions", []),
                decisions=data.get("decisions", []),
                blockers=data.get("blockers", []),
                next_actions=data.get("next_actions", []),
                metadata=data.get("metadata", {})
            )

        except (json.JSONDecodeError, IOError, KeyError):
            return None

    def _is_expired(self, context: SessionContext) -> bool:
        """
        Check if session expired (>7 days).
        """
        try:
            expires = context.metadata.get("expires_at")
            if not expires:
                return True

            expires_dt = datetime.fromisoformat(expires)
            return datetime.now() > expires_dt

        except (ValueError, TypeError):
            return True

    def _archive(self, context: SessionContext):
        """
        Move expired session to archive.
        """
        # Remove active file
        active_path = self.sessions_dir / f"active-{context.project}.json"
        if active_path.exists():
            active_path.unlink()

        # Save to archive
        archive_dir = self.sessions_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        archive_path = archive_dir / f"{context.session_id}.json"
        with open(archive_path, "w") as f:
            json.dump({
                "session_id": context.session_id,
                "project": context.project,
                "timestamp": context.timestamp,
                "archived_at": datetime.now().isoformat()
            }, f, indent=2)

    def _format_codes(self, context: SessionContext) -> str:
        """
        Format codes for injection.
        NO PROSE. NO MARKDOWN. Pure data.
        """
        lines = []

        # Project context
        lines.append(f"proj:{context.project}")

        # Files (all of them)
        if context.files:
            lines.extend(context.files)

        # Functions (all of them)
        if context.functions:
            lines.extend(context.functions)

        # Decisions (all of them)
        if context.decisions:
            lines.extend(context.decisions)

        # Blockers (highest priority)
        if context.blockers:
            lines.extend(context.blockers)

        # Next actions (what to do)
        if context.next_actions:
            lines.extend(context.next_actions)

        return "\n".join(lines)

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens (rough estimate).
        """
        return int(len(text.split()) * 1.3)

    def _calc_expiry(self) -> str:
        """
        Calculate 7-day expiry.
        """
        expiry = datetime.now() + timedelta(days=7)
        return expiry.isoformat()
```

---

## Integration Pipeline

```python
def on_session_end():
    """
    Phase 8 → Phase 9: Capture → Save
    """
    # Phase 8: Get codes
    capture_engine = SessionContextCapture()
    context = capture_engine.get_context()

    # Phase 9: Save codes (no LLM, no processing)
    injector = SessionContextInjector(Path.home() / ".cerberus")
    injector.save_context(context)

    print(f"✓ Session context saved ({len(context.files)} files)")

def on_session_start(project: str):
    """
    Phase 9: Inject codes
    Phase 7: Inject memories
    """
    # Phase 9: Load codes
    injector = SessionContextInjector(Path.home() / ".cerberus")
    session_pkg = injector.inject(project)

    # Phase 7: Load memories (Phase 6 retrieval)
    memory_injector = ContextInjector()
    memory_context = memory_injector.inject({
        "project": project,
        "language": detect_language(),
        "task": detect_task()
    })

    # Combine
    if session_pkg:
        full_context = memory_context + "\n\n" + session_pkg.codes
        total_tokens = memory_context.token_count + session_pkg.token_count
    else:
        full_context = memory_context
        total_tokens = memory_context.token_count

    print(f"✓ Context loaded ({total_tokens} tokens)")
    return full_context
```

---

## Cleanup Manager

```python
class SessionCleanupManager:
    """
    Auto-cleanup expired sessions.
    """

    def __init__(self, base_path: Path):
        self.sessions_dir = base_path / "memory" / "sessions"

    def cleanup_expired(self):
        """
        Archive all expired sessions.
        """
        if not self.sessions_dir.exists():
            return

        archived = 0

        for file_path in self.sessions_dir.glob("active-*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)

                # Check expiry
                expires = data.get("metadata", {}).get("expires_at")
                if expires:
                    expires_dt = datetime.fromisoformat(expires)
                    if datetime.now() > expires_dt:
                        self._archive_file(file_path, data)
                        archived += 1

            except (json.JSONDecodeError, IOError, KeyError, ValueError):
                # Malformed file, remove
                file_path.unlink()

        return archived

    def _archive_file(self, file_path: Path, data: Dict):
        """
        Move to archive.
        """
        archive_dir = self.sessions_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        archive_path = archive_dir / f"{data['session_id']}.json"

        # Add archive timestamp
        data["archived_at"] = datetime.now().isoformat()

        with open(archive_path, "w") as f:
            json.dump(data, f, indent=2)

        file_path.unlink()
```

---

## Token Budget Allocation

**Phase 9 budget: 1000-1500 tokens (TEMPORARY, deleted after injection)**

```
Files:          300-500 tokens (ALL files, not just top 5)
Functions:      200-400 tokens (ALL functions touched)
Decisions:      200-300 tokens (ALL decisions made)
Blockers:       100-200 tokens (ALL blockers)
Next actions:   100-200 tokens (ALL next actions)
Metadata:        50-100 tokens (proj:, timestamps)
────────────────────────────────────────────────────
Total:         1000-1500 tokens (comprehensive, temporary)
```

**Why generous budget:**
- Temporary storage (deleted after read)
- Goal is ZERO re-explanation
- Worth extra tokens to maintain momentum
- No LLM cost (removed)

---

## Injection Format Example

**Input (Phase 8 codes):**
```
impl:proxy.go
impl:supervisor.Process
impl:config_test.go
dec:split-proxy-3-files
dec:plan-splits-before-writing
block:race:test-failure-line-712
next:add-mutex-process-struct
next:rerun-race-detector
```

**Output (Phase 9 injection):**
```
proj:hydra
impl:proxy.go
impl:supervisor.Process
impl:config_test.go
dec:split-proxy-3-files
dec:plan-splits-before-writing
block:race:test-failure-line-712
next:add-mutex-process-struct
next:rerun-race-detector
```

**Agent reads:** Project hydra, files touched, decisions made, race blocker, next actions.
**Zero re-explanation needed.**

---

## Exit Criteria

```
✓ SessionContextInjector class implemented
✓ NO LLM (removed entirely)
✓ Load Phase 8 codes directly
✓ Format codes (minimal, no prose)
✓ Save/load working
✓ Expiry detection (7 days)
✓ Archival working
✓ Integration with Phase 8 complete
✓ Integration with Phase 7 complete
✓ Token budget: 1000-1500 tokens
✓ Tests: 10 injection scenarios
```

---

## Test Scenarios

```python
# Scenario 1: Basic code injection
context: 5 files, 3 decisions, 1 blocker
→ expect: codes injected, < 1500 tokens

# Scenario 2: Save and load
save context for project "hydra"
→ load on next session
→ expect: same codes returned

# Scenario 3: Expiry detection
context: created 8 days ago
→ expect: archived, not returned

# Scenario 4: Comprehensive capture
context: 20 files, 10 decisions, 5 blockers
→ expect: ALL captured, not truncated

# Scenario 5: No previous session
project: "new-project"
→ expect: inject() returns None, no error

# Scenario 6: Token budget
context: 15 files, 8 decisions, 3 blockers
→ expect: total < 1500 tokens

# Scenario 7: Malformed session file
storage: corrupted JSON
→ expect: skip, return None, no crash

# Scenario 8: Multiple projects
save contexts for "hydra", "cerberus"
→ load "hydra"
→ expect: only hydra codes returned

# Scenario 9: Cleanup expired
3 sessions: expired, expired, active
→ cleanup_expired()
→ expect: 2 archived, 1 active remains

# Scenario 10: Integration with Phase 7
session codes: 1000 tokens
memory injection: 1500 tokens
→ expect: combined < 2500 tokens
```

---

## Dependencies

- Phase 8 (SessionContextCapture for codes)
- Phase 7 (ContextInjector for memory integration)
- Phase 6 (MemoryRetrieval used by Phase 7)

---

## Performance

- Load codes: < 5ms (JSON read)
- Format codes: < 1ms (string join)
- Save codes: < 5ms (JSON write)
- Cleanup expired: < 100ms (10 sessions)

---

## Key Changes from V1

**REMOVED:**
- LLM summary generation (was 150 tokens, unnecessary prose)
- Canonical sentence extraction
- Markdown formatting
- Headers, titles, sections
- "Top 5" selection (now captures ALL items)

**ADDED:**
- Direct code injection (Phase 8 → Phase 9, no LLM)
- Comprehensive capture (all files, not top 5)
- Higher budget (500 → 1000-1500 tokens)
- Temporary storage justification

**Result:** Zero re-explanation, pure AI-native data, worth the tokens.
