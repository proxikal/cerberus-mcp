# PHASE 8: SESSION CONTINUITY

## Objective
Capture session context during work, inject at next session start. Zero re-explanation needed. NO LLM.

---

## Implementation Location

**File:** `src/cerberus/memory/session_continuity.py`

---

## Data Structures

```python
@dataclass
class SessionContext:
    """Active session context."""
    id: str  # "20260122-133514"
    project: str
    phase: Optional[str]  # "PHASE-2-SEMANTIC", "feature-auth", etc.
    completed: List[str]  # ["impl:semantic_analyzer.py", "test:clustering"]
    next_actions: List[str]  # ["test:deduplication", "integrate:phase3"]
    decisions: List[Dict]  # [{"choice": "threshold=0.75", "why": "precision"}]
    blockers: List[str]  # ["need:ollama", "unclear:storage_format"]
    files_modified: List[str]
    key_functions: List[str]  # ["cluster_corrections", "detect_patterns"]
    timestamp: datetime
    expires: datetime  # 7 days from creation
    status: str  # "active", "completed", "expired"

@dataclass
class InjectionPackage:
    """Ready-to-inject codes."""
    codes: str  # Raw codes, newline-separated
    token_count: int
    session_id: str
    expires_at: str
```

---

## Storage Format (AI-Native)

**File:** `~/.cerberus/memory/sessions/active-{project}.json`

```json
{
  "session_id": "20260122-133514",
  "project": "cerberus",
  "timestamp": "2026-01-22T13:35:14Z",
  "files": [
    "impl:agent_learning.py",
    "impl:session_continuity.py"
  ],
  "functions": [
    "impl:SessionContextCapture.record",
    "impl:detect_success_pattern"
  ],
  "decisions": [
    "dec:threshold-3-min-repetitions",
    "dec:no-llm-pure-data"
  ],
  "blockers": [
    "block:need:codebase_analyzer"
  ],
  "next_actions": [
    "next:impl-failure-pattern",
    "next:test-5-scenarios"
  ],
  "metadata": {
    "expires_at": "2026-01-29T13:35:14Z"
  }
}
```

**Code Format:**
- `impl:file.py` - File implemented/modified
- `impl:Module.method` - Function implemented
- `dec:choice-reason` - Decision made
- `block:type:desc` - Blocker encountered
- `next:action` - Next action to do

---

## Context Capture

```python
class SessionContextCapture:
    """
    Captures session context during work.
    Called by MCP tool handlers or hooks.
    """

    def __init__(self, session_id: str, project: str):
        self.session_id = session_id
        self.project = project
        self.completed: List[str] = []
        self.next_actions: List[str] = []
        self.decisions: List[str] = []
        self.blockers: List[str] = []
        self.files_modified: List[str] = []
        self.key_functions: List[str] = []

    def record_completion(self, action: str):
        """Record completed action. Format: impl:target"""
        if action not in self.completed:
            self.completed.append(action)

    def record_next(self, action: str):
        """Record next action. Format: next:action"""
        if action not in self.next_actions:
            self.next_actions.append(action)

    def record_decision(self, choice: str, reason: str):
        """Record decision. Format: dec:choice-reason"""
        code = f"dec:{choice}-{reason}".replace(" ", "-")
        if code not in self.decisions:
            self.decisions.append(code)

    def record_blocker(self, blocker_type: str, description: str):
        """Record blocker. Format: block:type:desc"""
        code = f"block:{blocker_type}:{description}".replace(" ", "-")
        if code not in self.blockers:
            self.blockers.append(code)

    def record_file_modified(self, file_path: str):
        """Track files modified. Format: impl:filename"""
        code = f"impl:{Path(file_path).name}"
        if code not in self.files_modified:
            self.files_modified.append(code)

    def record_function(self, func_name: str):
        """Track functions. Format: impl:func_name"""
        code = f"impl:{func_name}"
        if code not in self.key_functions:
            self.key_functions.append(code)

    def to_context(self, phase: Optional[str] = None) -> SessionContext:
        """Convert to SessionContext object."""
        return SessionContext(
            id=self.session_id,
            project=self.project,
            phase=phase,
            completed=self.completed,
            next_actions=self.next_actions,
            decisions=self.decisions,
            blockers=self.blockers,
            files_modified=self.files_modified,
            key_functions=self.key_functions,
            timestamp=datetime.now(),
            expires=datetime.now() + timedelta(days=7),
            status="active"
        )
```

---

## Context Injection (NO LLM)

```python
class SessionContextInjector:
    """
    Load codes, inject at session start.
    NO LLM. NO PROSE. Pure data injection.
    """

    def __init__(self, base_path: Path):
        self.sessions_dir = base_path / "memory" / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def inject(self, project: str) -> Optional[InjectionPackage]:
        """
        Load codes for injection. Return None if no active session.
        """
        context = self._load_active_session(project)

        if not context:
            return None

        if self._is_expired(context):
            self._archive(context)
            return None

        codes = self._format_codes(context)
        token_count = self._count_tokens(codes)

        return InjectionPackage(
            codes=codes,
            token_count=token_count,
            session_id=context.session_id,
            expires_at=context.metadata.get("expires_at")
        )

    def save_context(self, context: SessionContext):
        """Save session context to storage."""
        file_path = self.sessions_dir / f"active-{context.project}.json"

        data = {
            "session_id": context.id,
            "project": context.project,
            "timestamp": context.timestamp.isoformat(),
            "files": context.files_modified,
            "functions": context.key_functions,
            "decisions": context.decisions,
            "blockers": context.blockers,
            "next_actions": context.next_actions,
            "metadata": {
                "expires_at": (context.timestamp + timedelta(days=7)).isoformat()
            }
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_active_session(self, project: str) -> Optional[Dict]:
        """Load active session data."""
        file_path = self.sessions_dir / f"active-{project}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def _is_expired(self, data: Dict) -> bool:
        """Check if session expired (>7 days)."""
        try:
            expires = data.get("metadata", {}).get("expires_at")
            if not expires:
                return True
            return datetime.now() > datetime.fromisoformat(expires)
        except (ValueError, TypeError):
            return True

    def _archive(self, data: Dict):
        """Move expired session to archive."""
        archive_dir = self.sessions_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        archive_path = archive_dir / f"{data['session_id']}.json"
        data["archived_at"] = datetime.now().isoformat()

        with open(archive_path, "w") as f:
            json.dump(data, f, indent=2)

        # Remove active file
        active_path = self.sessions_dir / f"active-{data['project']}.json"
        if active_path.exists():
            active_path.unlink()

    def _format_codes(self, data: Dict) -> str:
        """
        Format codes for injection.
        NO PROSE. NO MARKDOWN. Pure data.
        """
        lines = [f"proj:{data['project']}"]

        for f in data.get("files", []):
            lines.append(f)
        for f in data.get("functions", []):
            lines.append(f)
        for d in data.get("decisions", []):
            lines.append(d)
        for b in data.get("blockers", []):
            lines.append(b)
        for n in data.get("next_actions", []):
            lines.append(n)

        return "\n".join(lines)

    def _count_tokens(self, text: str) -> int:
        """Count tokens (rough estimate)."""
        return int(len(text.split()) * 1.3)

    def mark_complete(self, project: str):
        """Mark session as completed."""
        file_path = self.sessions_dir / f"active-{project}.json"
        if file_path.exists():
            file_path.unlink()
```

---

## Auto-Capture Integration

```python
class AutoCapture:
    """
    Automatically capture session context from tool usage.
    Called by MCP tool handlers.
    """

    def __init__(self, session_id: str, project: str):
        self.capture = SessionContextCapture(session_id, project)

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
    """Auto-cleanup expired sessions."""

    def __init__(self, base_path: Path):
        self.sessions_dir = base_path / "memory" / "sessions"

    def cleanup_expired(self) -> int:
        """Archive all expired sessions. Returns count archived."""
        if not self.sessions_dir.exists():
            return 0

        archived = 0

        for file_path in self.sessions_dir.glob("active-*.json"):
            try:
                with open(file_path) as f:
                    data = json.load(f)

                expires = data.get("metadata", {}).get("expires_at")
                if expires:
                    if datetime.now() > datetime.fromisoformat(expires):
                        self._archive_file(file_path, data)
                        archived += 1

            except (json.JSONDecodeError, IOError, ValueError):
                file_path.unlink()  # Remove malformed

        return archived

    def _archive_file(self, file_path: Path, data: Dict):
        """Move to archive."""
        archive_dir = self.sessions_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        data["archived_at"] = datetime.now().isoformat()
        archive_path = archive_dir / f"{data['session_id']}.json"

        with open(archive_path, "w") as f:
            json.dump(data, f, indent=2)

        file_path.unlink()
```

---

## Integration Pipeline

```python
def on_session_save(capture: AutoCapture, phase: Optional[str] = None):
    """
    Save session context (called by skill or explicit memory_learn).
    """
    context = capture.get_context(phase)
    injector = SessionContextInjector(Path.home() / ".cerberus")
    injector.save_context(context)
    return len(context.files_modified)

def on_session_start(project: str) -> Optional[str]:
    """
    Load session context at session start.
    Returns codes for injection or None.
    """
    injector = SessionContextInjector(Path.home() / ".cerberus")
    package = injector.inject(project)

    if package:
        return package.codes
    return None
```

---

## Integration with Phase 7

```python
def inject_all(context: InjectionContext) -> str:
    """
    Combined injection: Memory (Phase 7) + Session (Phase 8).
    """
    # Phase 7: Memory injection
    memory_context = memory_injector.inject(context)

    # Phase 8: Session injection
    session_pkg = session_injector.inject(context.project)

    parts = []
    if memory_context:
        parts.append(memory_context)
    if session_pkg:
        parts.append(session_pkg.codes)

    return "\n\n".join(parts)
```

**Token budget:** Memory (1500) + Session (1000) = 2500 tokens max

---

## Token Budget Allocation

**Session context budget: 1000-1500 tokens**

```
Files:          300-500 tokens (ALL files modified)
Functions:      200-400 tokens (ALL functions touched)
Decisions:      200-300 tokens (ALL decisions made)
Blockers:       100-200 tokens (ALL blockers)
Next actions:   100-200 tokens (ALL next actions)
Metadata:        50-100 tokens (proj:, timestamps)
────────────────────────────────────────────────────
Total:         1000-1500 tokens (comprehensive)
```

**Why generous budget:**
- Goal is ZERO re-explanation
- Worth extra tokens to maintain momentum
- No LLM cost (pure data)
- Temporary (deleted after session marked complete)

---

## Injection Format Example

**Stored:**
```json
{
  "session_id": "20260121-143022",
  "project": "hydra",
  "files": ["impl:proxy.go", "impl:supervisor.go"],
  "functions": ["impl:supervisor.Process", "impl:config.Load"],
  "decisions": ["dec:split-proxy-3-files", "dec:plan-splits-before-writing"],
  "blockers": ["block:race:test-failure-line-712"],
  "next_actions": ["next:add-mutex-to-process-struct", "next:rerun-race-detector"]
}
```

**Injected:**
```
proj:hydra
impl:proxy.go
impl:supervisor.go
impl:supervisor.Process
impl:config.Load
dec:split-proxy-3-files
dec:plan-splits-before-writing
block:race:test-failure-line-712
next:add-mutex-to-process-struct
next:rerun-race-detector
```

**Agent reads:** Project hydra, files touched, decisions made, race blocker, next actions.
**Zero re-explanation needed.**

---

## Exit Criteria

```
✓ SessionContextCapture class implemented
✓ AutoCapture integration working
✓ SessionContextInjector (NO LLM) implemented
✓ SessionCleanupManager implemented
✓ Save/load working
✓ Expiry detection (7 days)
✓ Archival working
✓ Integration with Phase 7 complete
✓ AI-native storage format validated
✓ Token budget: 1000-1500 tokens
✓ Tests: 10 injection scenarios
```

---

## Test Scenarios

```python
# Scenario 1: Basic capture
session: implemented 3 functions, modified 2 files
→ expect: context with files=[impl:f1, impl:f2], functions=[impl:fn1, impl:fn2, impl:fn3]

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

- Phase 7 (ContextInjector for memory integration)
- Phase 6 (MemoryRetrieval used by Phase 7)

---

## Performance

- Load codes: < 5ms (JSON read)
- Format codes: < 1ms (string join)
- Save codes: < 5ms (JSON write)
- Cleanup expired: < 100ms (10 sessions)
