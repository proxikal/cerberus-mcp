# PHASE 8: SESSION CONTINUITY

## Objective
Preserve session context for next session. Zero re-explanation needed.

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
    decisions: List[Dict]  # [{"dec": "threshold=0.75", "why": "precision"}]
    blockers: List[str]  # ["need:ollama", "unclear:storage_format"]
    files_modified: List[str]
    key_functions: List[str]  # ["cluster_corrections", "detect_patterns"]
    timestamp: datetime
    expires: datetime  # 7 days from creation
    status: str  # "active", "completed", "expired"

@dataclass
class SessionSummary:
    """Compressed session summary for next session."""
    session_id: str
    project: str
    context: SessionContext
    summary_text: str  # LLM-generated terse summary (max 3 sentences)
    token_cost: int
```

---

## Storage Format (AI-Native)

**File:** `~/.cerberus/memory/sessions/active-{session_id}.json`

```json
{
  "id": "20260122-133514",
  "proj": "cerberus",
  "phase": "PHASE-7-AGENT-LEARNING",
  "done": [
    "impl:agent_learning.py:ObservationCollector",
    "impl:agent_learning.py:detect_success_pattern",
    "test:success_reinforcement:3_scenarios"
  ],
  "next": [
    "impl:detect_failure_pattern",
    "impl:detect_project_pattern",
    "test:failure_avoidance:5_scenarios",
    "integrate:proposal_engine"
  ],
  "dec": [
    {"choice": "threshold=3", "why": "min_repetitions"},
    {"choice": "confidence=0.9", "why": "explicit_praise"},
    {"choice": "max_proposals=5", "why": "token_budget"}
  ],
  "block": [
    "need:codebase_analyzer",
    "unclear:project_pattern_detection"
  ],
  "files": [
    "src/cerberus/memory/agent_learning.py",
    "tests/test_agent_learning.py"
  ],
  "funcs": [
    "detect_success_pattern",
    "ObservationCollector.record",
    "AgentLearningEngine.generate_proposals"
  ],
  "ts": "2026-01-22T13:35:14Z",
  "exp": "2026-01-29T13:35:14Z",
  "status": "active"
}
```

**Field Codes:**
- `proj`: project name
- `phase`: current phase/feature
- `done`: completed actions (verb:target:detail)
- `next`: next actions (verb:target:detail)
- `dec`: decisions (choice + why)
- `block`: blockers (type:description)
- `files`: modified files
- `funcs`: key functions written/modified
- `ts`: timestamp
- `exp`: expiration (7 days)
- `status`: active, completed, expired

**Action Format:**
```
verb:target:detail
Examples:
- impl:agent_learning.py:ObservationCollector
- test:success_reinforcement:3_scenarios
- refactor:split_file:proxy.go:3_parts
- debug:race_condition:supervisor.go:line_45
- doc:README.md:agent_learning_section
```

**Decision Format:**
```json
{"choice": "what", "why": "reason"}
Examples:
- {"choice": "threshold=0.75", "why": "precision_over_recall"}
- {"choice": "local_embeddings", "why": "zero_cost"}
- {"choice": "testify_suite", "why": "project_pattern"}
```

**Blocker Format:**
```
type:description
Examples:
- need:ollama_running
- need:test_data
- unclear:storage_format
- error:circular_import:hierarchy.py
- decision_needed:scope_inference_strategy
```

---

## Context Capture

```python
class SessionContextCapture:
    """
    Captures session context during work.
    """

    def __init__(self, session_id: str, project: str):
        self.session_id = session_id
        self.project = project
        self.completed: List[str] = []
        self.next_actions: List[str] = []
        self.decisions: List[Dict] = []
        self.blockers: List[str] = []
        self.files_modified: List[str] = []
        self.key_functions: List[str] = []

    def record_completion(self, action: str):
        """
        Record completed action.
        Format: verb:target:detail
        """
        self.completed.append(action)

    def record_next(self, action: str):
        """
        Record next action to do.
        Format: verb:target:detail
        """
        self.next_actions.append(action)

    def record_decision(self, choice: str, reason: str):
        """
        Record decision made.
        """
        self.decisions.append({"choice": choice, "why": reason})

    def record_blocker(self, blocker_type: str, description: str):
        """
        Record blocker encountered.
        """
        self.blockers.append(f"{blocker_type}:{description}")

    def record_file_modified(self, file_path: str):
        """
        Track files modified.
        """
        if file_path not in self.files_modified:
            self.files_modified.append(file_path)

    def record_function(self, func_name: str):
        """
        Track key functions written/modified.
        """
        if func_name not in self.key_functions:
            self.key_functions.append(func_name)

    def to_context(self, phase: Optional[str] = None) -> SessionContext:
        """
        Convert to SessionContext object.
        """
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

## LLM Summary Generation

```python
class SessionSummarizer:
    """
    Generate terse LLM summary from session context.
    """

    def __init__(self, llm_provider: str = "ollama"):
        self.llm = LLMClient(llm_provider)

    def generate_summary(self, context: SessionContext) -> str:
        """
        Generate 2-3 sentence summary for next session.
        """
        prompt = f"""Session context summary (2-3 sentences max, terse):

Project: {context.project}
Phase: {context.phase or 'unknown'}

Completed:
{chr(10).join(f"- {item}" for item in context.completed[:5])}

Next actions:
{chr(10).join(f"- {item}" for item in context.next_actions[:3])}

Decisions:
{chr(10).join(f"- {d['choice']}: {d['why']}" for d in context.decisions[:3])}

Blockers:
{chr(10).join(f"- {b}" for b in context.blockers[:2])}

Output format (terse, imperative):
"Working on [phase/feature]. Completed [key accomplishments]. Next: [next steps]. [Blockers if any]."

Summary:"""

        try:
            summary = self.llm.generate(prompt, max_tokens=150).strip()
            return summary
        except:
            # Fallback: Template-based summary
            return self._fallback_summary(context)

    def _fallback_summary(self, context: SessionContext) -> str:
        """
        Template-based summary if LLM unavailable.
        """
        phase = context.phase or "unknown phase"
        completed = len(context.completed)
        next_item = context.next_actions[0] if context.next_actions else "continue"

        summary = f"Working on {phase}. Completed {completed} tasks. Next: {next_item}."

        if context.blockers:
            summary += f" Blocked: {context.blockers[0]}."

        return summary
```

---

## Context Injection

```python
class SessionContextInjector:
    """
    Inject session context at start of new session.
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path / "sessions"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_context(self, context: SessionContext):
        """
        Save session context to disk.
        """
        file_path = self.base_path / f"active-{context.id}.json"

        data = {
            "id": context.id,
            "proj": context.project,
            "phase": context.phase,
            "done": context.completed,
            "next": context.next_actions,
            "dec": context.decisions,
            "block": context.blockers,
            "files": context.files_modified,
            "funcs": context.key_functions,
            "ts": context.timestamp.isoformat(),
            "exp": context.expires.isoformat(),
            "status": context.status
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_active_context(self, project: str) -> Optional[SessionContext]:
        """
        Load most recent active context for project.
        """
        active_files = list(self.base_path.glob("active-*.json"))

        if not active_files:
            return None

        # Filter by project and status
        for file_path in sorted(active_files, reverse=True):
            with open(file_path) as f:
                data = json.load(f)

            if data["proj"] == project and data["status"] == "active":
                # Check not expired
                exp = datetime.fromisoformat(data["exp"])
                if datetime.now() < exp:
                    return self._data_to_context(data)

        return None

    def inject(self, project: str) -> str:
        """
        Generate injection text for next session.
        """
        context = self.load_active_context(project)

        if not context:
            return ""

        # Generate summary
        summarizer = SessionSummarizer()
        summary = summarizer.generate_summary(context)

        # Format for injection (AI-native)
        lines = ["## Session Context (Previous Session)"]
        lines.append("")
        lines.append(f"**Summary:** {summary}")
        lines.append("")

        if context.next_actions:
            lines.append("**Next:**")
            for action in context.next_actions[:3]:
                lines.append(f"- {action}")
            lines.append("")

        if context.decisions:
            lines.append("**Decisions:**")
            for dec in context.decisions[:3]:
                lines.append(f"- {dec['choice']}: {dec['why']}")
            lines.append("")

        if context.blockers:
            lines.append("**Blockers:**")
            for blocker in context.blockers:
                lines.append(f"- {blocker}")
            lines.append("")

        if context.files_modified:
            lines.append(f"**Files:** {', '.join(context.files_modified[:5])}")
            lines.append("")

        return "\n".join(lines)

    def _data_to_context(self, data: Dict) -> SessionContext:
        """Convert JSON data to SessionContext object."""
        return SessionContext(
            id=data["id"],
            project=data["proj"],
            phase=data.get("phase"),
            completed=data.get("done", []),
            next_actions=data.get("next", []),
            decisions=data.get("dec", []),
            blockers=data.get("block", []),
            files_modified=data.get("files", []),
            key_functions=data.get("funcs", []),
            timestamp=datetime.fromisoformat(data["ts"]),
            expires=datetime.fromisoformat(data["exp"]),
            status=data.get("status", "active")
        )

    def mark_complete(self, session_id: str):
        """
        Mark session as completed (don't inject next time).
        """
        file_path = self.base_path / f"active-{session_id}.json"

        if file_path.exists():
            with open(file_path) as f:
                data = json.load(f)

            data["status"] = "completed"

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)

    def cleanup_expired(self):
        """
        Archive expired sessions.
        """
        archive_dir = self.base_path / "archived"
        archive_dir.mkdir(exist_ok=True)

        for file_path in self.base_path.glob("active-*.json"):
            with open(file_path) as f:
                data = json.load(f)

            exp = datetime.fromisoformat(data["exp"])
            if datetime.now() > exp:
                # Move to archive
                archive_path = archive_dir / file_path.name
                file_path.rename(archive_path)
```

---

## Auto-Capture Integration

```python
class AutoCapture:
    """
    Automatically capture session context from tool usage.
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
                self.capture.record_completion(f"edit:{Path(file_path).name}")

        # Function implementations (detect from Write/Edit content)
        if tool_name in ["Write", "Edit"]:
            content = params.get("content", "") + params.get("new_string", "")
            # Extract function names (basic regex)
            import re
            funcs = re.findall(r'def\s+(\w+)|func\s+(\w+)|function\s+(\w+)', content)
            for match in funcs:
                func_name = next(f for f in match if f)
                self.capture.record_function(func_name)

        # Test execution
        if tool_name == "Bash":
            cmd = params.get("command", "")
            if "test" in cmd or "pytest" in cmd or "go test" in cmd:
                self.capture.record_completion(f"test:executed:{cmd.split()[0]}")

    def on_user_message(self, message: str):
        """
        Hook called on user message.
        Detect decisions, blockers, next actions.
        """
        msg_lower = message.lower()

        # Decision detection
        if any(kw in msg_lower for kw in ["let's use", "we'll use", "decision:"]):
            # Extract decision (basic heuristic)
            self.capture.record_decision("user_specified", "explicit")

        # Blocker detection
        if any(kw in msg_lower for kw in ["blocked", "unclear", "need", "issue"]):
            self.capture.record_blocker("user_reported", message[:50])

        # Next action detection
        if any(kw in msg_lower for kw in ["next", "then", "after this"]):
            # User specifying next steps
            pass  # Extract and record
```

---

## Session End Flow

```python
def on_session_end():
    """
    Called at session end.
    Generate context summary, get user confirmation.
    """
    # Get captured context
    auto_capture = get_auto_capture()
    context = auto_capture.capture.to_context(phase=detect_current_phase())

    # Generate summary
    summarizer = SessionSummarizer()
    summary = summarizer.generate_summary(context)

    # Present to user
    print(f"\n{'='*60}")
    print(f"SESSION CONTEXT SUMMARY")
    print(f"{'='*60}")
    print(f"{summary}\n")

    print(f"Completed: {len(context.completed)} tasks")
    print(f"Next: {len(context.next_actions)} actions")
    print(f"Decisions: {len(context.decisions)}")
    if context.blockers:
        print(f"⚠️  Blockers: {len(context.blockers)}")

    # Ask to save
    response = input("\nSave for next session? (y/n/edit): ").strip().lower()

    if response == "y":
        # Save as-is
        injector = SessionContextInjector(Path.home() / ".cerberus" / "memory")
        injector.save_context(context)
        print("✓ Context saved for next session")

    elif response == "edit":
        # Allow user to edit next actions, remove blockers, etc.
        context = interactive_edit(context)
        injector = SessionContextInjector(Path.home() / ".cerberus" / "memory")
        injector.save_context(context)
        print("✓ Edited context saved")

    elif response == "n":
        print("Context not saved")
```

---

## Session Start Flow

```python
def on_session_start():
    """
    Called at session start.
    Auto-inject previous session context.
    """
    # Detect project
    project = detect_project_name()

    if not project:
        return ""

    # Load active context
    injector = SessionContextInjector(Path.home() / ".cerberus" / "memory")
    context_text = injector.inject(project)

    if context_text:
        print(f"\n{'='*60}")
        print(f"CONTINUING FROM PREVIOUS SESSION")
        print(f"{'='*60}\n")
        # Context_text is injected into system prompt automatically

    return context_text
```

---

## Integration with Phase 4

Modify Phase 4 injection to include session context:

```python
def inject(self, context: InjectionContext) -> str:
    # Existing memory injection
    memory_context = self._inject_memories(context)

    # Add session context
    session_injector = SessionContextInjector(self.base_path)
    session_context = session_injector.inject(context.project)

    # Combine (memory first, session second)
    parts = []
    if memory_context:
        parts.append(memory_context)
    if session_context:
        parts.append(session_context)

    return "\n\n".join(parts)
```

**Token budget:** Memory (1000) + Session (500) = 1500 tokens max

---

## Exit Criteria

```
✓ SessionContextCapture class implemented
✓ Auto-capture from tool usage working
✓ LLM summary generation functional (with fallback)
✓ SessionContextInjector class implemented
✓ Session start/end hooks integrated
✓ AI-native storage format validated
✓ Expiration and cleanup working
✓ Integration with Phase 4 complete
✓ Token budget: 500 tokens (summary + injection)
✓ Tests: 10 scenarios with expected contexts
```

---

## Test Scenarios

```python
# Scenario 1: Basic capture
session: implemented 3 functions, modified 2 files
→ expect: context with done=[impl:func1, impl:func2, impl:func3]

# Scenario 2: Next actions
session: completed phase 2, user says "next: implement phase 3"
→ expect: next=[impl:phase3]

# Scenario 3: Decisions
session: user says "let's use threshold=0.75"
→ expect: dec=[{"choice": "threshold=0.75", "why": "user_specified"}]

# Scenario 4: Blockers
session: user says "blocked: need ollama running"
→ expect: block=["need:ollama_running"]

# Scenario 5: Injection
next session starts in same project
→ expect: context injected automatically, 500 tokens max

# Scenario 6: Expiration
session saved 8 days ago
→ expect: not injected (expired), moved to archive

# Scenario 7: Mark complete
user marks session complete
→ expect: status=completed, not injected next time
```

---

## Dependencies

- Existing: Phase 4 components
- New: LLM client (Ollama or Claude API)

---

## Token Budget

- Summary generation: ~150 tokens (LLM)
- Context injection: ~350 tokens (formatted context)
- Total: 500 tokens per session start

---

## Performance

- Context capture: O(1) per tool call
- Summary generation: < 2 seconds (1 LLM call)
- Context injection: < 50ms (file read + format)
- Cleanup: < 100ms (file operations)
