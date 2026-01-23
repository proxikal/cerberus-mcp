# PHASE 16: INTEGRATION SPECIFICATION

## Objective
Define concrete integration mechanism between memory system and Claude Code CLI. Specify hook implementation, IPC protocol, environment setup.

---

## Implementation Location

**Files:**
- `src/cerberus/memory/hooks.py` (hook implementation)
- `src/cerberus/memory/ipc.py` (inter-process communication)
- Integration patches for Claude Code (if needed)

---

## Phase Assignment

**Rollout:** Phase Epsilon (Post-Delta)

**Prerequisites:**
- ✅ Phase Alpha complete (Phases 1-7 working with JSON)
- ✅ Phase 7 complete (injection logic proven)

**Why Phase Epsilon:**
- Integration can use Phase Alpha's JSON first (simple)
- Prove integration works before SQLite complexity
- Can be developed in parallel with Beta/Gamma/Delta

---

## Integration Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        USER                                   │
│                          ↓                                    │
│                   claude-code CLI                             │
│                          ↓                                    │
│                 SESSION STARTS                                │
│                          ↓                                    │
│              ┌───────────────────────┐                        │
│              │  MCP Server Running   │                        │
│              └───────────────────────┘                        │
│                          ↓                                    │
│    ┌─────────────────────────────────────────────┐           │
│    │  Auto-call MCP tool: memory_context()       │           │
│    │  (ONE-TIME at session start - no bash hook) │           │
│    └─────────────────────────────────────────────┘           │
│                          ↓                                    │
│    Phase 7 + 8: Startup auto-injection (2000 tokens)         │
│    ├─ Phase 7 Memories: 1200 tokens                          │
│    │   ├─ Universal preferences: 300 tokens                  │
│    │   ├─ Language rules: 300 tokens                         │
│    │   ├─ Project decisions: 400 tokens                      │
│    │   └─ Reserve: 200 tokens                                │
│    └─ Phase 8 Session codes: 800 tokens                      │
│        ├─ impl: 300 tokens                                   │
│        ├─ dec: 200 tokens                                    │
│        └─ block: + next: 300 tokens                          │
│                          ↓                                    │
│         Returns: ~2000 tokens (AI-native format)              │
│                          ↓                                    │
│              Claude has full context                          │
│                          ↓                                    │
│                   USER CONVERSATION                           │
│              (zero re-explanation needed)                     │
│                          ↓                                    │
│              ┌───────────────────────┐                        │
│              │  Session End Hook     │                        │
│              │  (bash - MCP shutting │                        │
│              │   down, must use CLI) │                        │
│              └───────────────────────┘                        │
│                          ↓                                    │
│    ┌─────────────────────────────────────────────┐           │
│    │  cerberus memory propose                    │           │
│    │  (CLI command via bash hook)                │           │
│    └─────────────────────────────────────────────┘           │
│                          ↓                                    │
│         Phases 1-4: Detect, cluster, propose, approve         │
│                          ↓                                    │
│              Phase 5: Store approved                          │
└──────────────────────────────────────────────────────────────┘
```

**Key Integration Points:**
- Session start: MCP tool `memory_context()` auto-called (2000 tokens ONE-TIME, no bash hook)
- Startup injection: Memories (1200 tokens) + Session codes (800 tokens)
- On-demand queries: `memory_context(query)` MCP tool available during work (500 tokens per query, max 2)
- Total cap: 3000 tokens per session (2000 startup + 1000 on-demand max)
- Session end: Bash hook calls CLI (MCP shutting down, can't use MCP tools)

---

## Integration Methods

### Method 1: MCP Session Start + Bash Session End (Recommended)

**Session START (MCP tool - no bash hook needed):**
- Claude Code auto-calls `memory_context()` MCP tool at session start
- MCP server is already running, tool returns startup injection (2000 tokens)
- No bash script needed - MCP handles this directly

**Session END (bash hook required):**
```bash
# ~/.claude/hooks/session-end.sh
#!/bin/bash
# Must use CLI because MCP is shutting down
cerberus memory propose --interactive
```

**Implementation in `src/cerberus/memory/hooks.py`:**
```python
def propose_hook() -> None:
    """
    CLI entrypoint for session end hook.

    Runs full pipeline: detect → cluster → propose → approve → store
    """
    from cerberus.memory.session_analyzer import SessionAnalyzer
    from cerberus.memory.semantic_analyzer import SemanticAnalyzer
    from cerberus.memory.proposal_engine import ProposalEngine
    from cerberus.memory.approval_cli import ApprovalCLI
    from cerberus.memory.storage import MemoryStorage

    # Phase 1: Detect corrections
    analyzer = SessionAnalyzer()
    candidates = analyzer.get_candidates()

    if not candidates:
        print("No corrections detected this session.")
        return

    # Phase 2: Cluster
    semantic = SemanticAnalyzer()
    clusters = semantic.cluster_corrections(candidates)

    # Phase 3: Generate proposals
    engine = ProposalEngine()
    proposals = engine.generate_proposals(clusters)

    # Phase 4: CLI approval
    cli = ApprovalCLI()
    approved_ids = cli.run(proposals)

    # Phase 5: Store
    storage = MemoryStorage()
    approved = [p for p in proposals if p.id in approved_ids]
    storage.store_batch(approved)

    print(f"Stored {len(approved)} memories.")
```

**CLI commands:**
```bash
# Session end
cerberus memory propose --interactive

# Session end (batch mode, auto-approve high confidence)
cerberus memory propose --batch --threshold 0.85
```

**Note:** Session start uses MCP tool `memory_context()` - Claude Code auto-calls this when session starts. No bash hook needed. On-demand `memory_context(query)` available during work if Claude needs additional context.

---

## Data Structures

```python
@dataclass
class HookContext:
    """Context passed to hooks."""
    session_id: str
    working_directory: str
    git_repo: Optional[str]
    project_name: Optional[str]
    language: Optional[str]
    timestamp: datetime

@dataclass
class ProposalResult:
    """Result from propose hook."""
    proposals: List[MemoryProposal]
    approved_ids: List[str]
    stored_count: int
    session_stats: Dict[str, int]  # {"candidates": 15, "clusters": 4, "proposals": 8}
```

---

## Context Detection Algorithm

```python
def detect_context() -> HookContext:
    """
    Detect session context for hook execution.

    Strategy:
    1. Get working directory (from PWD or CLI arg)
    2. Detect git repo (walk up to find .git)
    3. Infer project name (from git remote or directory name)
    4. Infer language (from file extensions in cwd)

    Returns:
        HookContext with detected values
    """
    import os
    import subprocess
    from pathlib import Path

    # Working directory
    cwd = os.getcwd()

    # Git repo detection
    git_repo = _find_git_repo(cwd)

    # Project name
    if git_repo:
        # Try git remote
        try:
            remote = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=git_repo,
                text=True
            ).strip()
            # "git@github.com:user/project.git" → "project"
            project_name = remote.split("/")[-1].replace(".git", "")
        except:
            # Fallback to directory name
            project_name = Path(git_repo).name
    else:
        project_name = Path(cwd).name

    # Language detection
    language = _detect_language(cwd)

    return HookContext(
        session_id=_generate_session_id(),
        working_directory=cwd,
        git_repo=git_repo,
        project_name=project_name,
        language=language,
        timestamp=datetime.now()
    )


def _find_git_repo(start_path: str) -> Optional[str]:
    """Walk up directory tree to find .git"""
    path = Path(start_path).resolve()

    while path != path.parent:
        if (path / ".git").exists():
            return str(path)
        path = path.parent

    return None


def _detect_language(cwd: str) -> Optional[str]:
    """
    Detect primary language from file extensions.

    Strategy:
    1. Count files by extension in cwd (non-recursive)
    2. Return most common extension
    """
    from collections import Counter

    extensions = Counter()

    for file in Path(cwd).iterdir():
        if file.is_file():
            ext = file.suffix.lstrip(".")
            if ext in LANGUAGE_EXTENSIONS.values():
                extensions[ext] += 1

    if extensions:
        most_common_ext = extensions.most_common(1)[0][0]
        # Reverse lookup: ext → language
        for lang, ext in LANGUAGE_EXTENSIONS.items():
            if ext == most_common_ext:
                return lang

    return None


def _generate_session_id() -> str:
    """Generate unique session ID."""
    import uuid
    return f"session-{uuid.uuid4().hex[:12]}"


LANGUAGE_EXTENSIONS = {
    "python": "py",
    "javascript": "js",
    "typescript": "ts",
    "go": "go",
    "rust": "rs",
}
```

---

## Session Tracking

### Session State File

**Location:** `.cerberus-session.json` (project root, temporary runtime state)

**Purpose:** Track active session for correction detection

**Note:** This is the ONLY local project file. All persistent data (memories, sessions, history) is stored in `~/.cerberus/memory.db` global database.

**Schema:**
```json
{
  "session_id": "session-abc123def456",
  "started_at": "2026-01-22T10:30:00Z",
  "working_directory": "/Users/user/projects/myapp",
  "project_name": "myapp",
  "language": "python",
  "turn_count": 0,
  "corrections": []
}
```

**Operations:**
```python
def start_session(context: HookContext) -> None:
    """Initialize session state at session start."""
    state = {
        "session_id": context.session_id,
        "started_at": context.timestamp.isoformat(),
        "working_directory": context.working_directory,
        "project_name": context.project_name,
        "language": context.language,
        "turn_count": 0,
        "corrections": []
    }

    with open(".cerberus-session.json", "w") as f:
        json.dump(state, f, indent=2)


def end_session() -> Dict[str, Any]:
    """Load and cleanup session state at session end."""
    try:
        with open(".cerberus-session.json", "r") as f:
            state = json.load(f)
    except FileNotFoundError:
        return {}

    # Session data is already in global DB (~/.cerberus/memory.db)
    # Just delete the temp runtime file
    os.remove(".cerberus-session.json")

    return state
```

---

## Hook Installation

### Automatic Installation

```bash
# Install hooks for Claude Code
cerberus memory install-hooks --cli claude-code

# Install hooks for other CLIs
cerberus memory install-hooks --cli codex-cli
cerberus memory install-hooks --cli gemini-cli
```

**Implementation:**
```python
def install_hooks(cli_name: str) -> None:
    """
    Install session end hook for CLI tool.

    Note: Session START uses MCP tool (no bash hook needed).
    Only session END needs bash hook (MCP shutting down).
    """

    # Hook directory mapping
    HOOK_DIRS = {
        "claude-code": "~/.claude/hooks",
        "codex-cli": "~/.codex/hooks",
        "gemini-cli": "~/.gemini/hooks",
    }

    hook_dir = Path(HOOK_DIRS[cli_name]).expanduser()
    hook_dir.mkdir(parents=True, exist_ok=True)

    # Session end hook (only hook needed)
    end_hook = hook_dir / "session-end.sh"
    end_hook.write_text("""#!/bin/bash
# Cerberus memory proposal hook
# Runs after Claude exits (MCP shutting down)
cerberus memory propose --interactive
""")
    end_hook.chmod(0o755)

    print(f"Installed session-end hook for {cli_name} in {hook_dir}")
```

---

## Error Handling

```python
def propose_hook_with_error_handling() -> None:
    """
    Safe proposal hook with fallback.

    If proposal fails, skip silently (don't block session end).
    """
    try:
        propose_hook()
    except Exception as e:
        # Log error
        log_error(f"Memory proposal failed: {e}")

        # Continue silently (don't block user)
        print("Memory proposal skipped due to error.")
```

---

## CLI Commands

```bash
# Session end (propose memories)
cerberus memory propose
cerberus memory propose --interactive
cerberus memory propose --batch --threshold 0.85

# Install session-end hook
cerberus memory install-hooks --cli claude-code
cerberus memory install-hooks --cli codex-cli

# Test hooks
cerberus memory test-hooks
```

**Note:** No CLI command for session start - handled by MCP tool `memory_context()` automatically.

---

## Token Costs

**Session start (MCP tool - automatic):**
- MCP tool `memory_context()` returns: 2000 tokens (AI-native format)
  - Phase 7 Memories: 1200 tokens
    - Universal preferences: 300 tokens
    - Language rules: 300 tokens
    - Project decisions: 400 tokens
    - Reserve: 200 tokens
  - Phase 8 Session codes: 800 tokens
    - impl: 300 tokens
    - dec: 200 tokens
    - block: + next: 300 tokens

**On-demand queries (during work - optional):**
- memory_context(query): 500 tokens per query
- Max 2 queries per session: 1000 tokens total

**Total per session:** 2000-3000 tokens (2000 startup + 0-1000 on-demand)

**Proposal (session end):**
- Phase 1-2: 0 tokens (TF-IDF)
- Phase 3: 0-500 tokens (template-based, LLM optional)
- Phase 4: 0 tokens (CLI)
- Phase 5: 0 tokens (storage)
- Total: 0-500 tokens

**Total per session:** 1500-2000 tokens (~$0.03 @ Sonnet rates)

---

## Validation Gates

**Phase 16 complete when:**
- ✅ Session-end hook installs successfully
- ✅ MCP tool startup injection works (memories appear in Claude's context at session start)
- ✅ Proposal works (corrections detected and stored via bash hook at session end)
- ✅ Error handling works (proposal failures don't block session end)
- ✅ Works with 3+ CLI tools (Claude Code, Codex, Gemini)
- ✅ 5+ real sessions tested

**Testing:**
- Manual: Install session-end hook, start session, verify MCP injection at startup, make corrections, end session, verify proposal
- Automated: Mock MCP tool call + bash hook execution, verify output formats
- Integration: Full session with corrections → verify startup injection + end hook storage

---

## Dependencies

**Phase Dependencies:**
- Phase 7 (Context Injection) - inject hook calls this
- Phase 1-5 (Detection → Storage) - propose hook calls these

**External Dependencies:**
- None (pure Python subprocess calls)

**CLI Requirements:**
- Claude Code must support session hooks (or use environment variable method)
- Hook directory must be writable

---

## Implementation Checklist

- [ ] Write `src/cerberus/memory/hooks.py`
- [ ] Implement `propose_hook()` function (session end CLI entrypoint)
- [ ] Ensure MCP tool `memory_context()` implements startup injection (Phase 7)
- [ ] Implement context detection (`detect_context()`)
- [ ] Implement session tracking (start/end session state)
- [ ] Add CLI commands (`cerberus memory propose`, `install-hooks`)
- [ ] Write session-end hook installation script
- [ ] Add error handling for propose hook (fallback on failure)
- [ ] Write unit tests (context detection, propose hook execution)
- [ ] Write integration tests (full session: MCP start + bash end)
- [ ] Test with Claude Code
- [ ] Test with other CLIs (Codex, Gemini if available)
- [ ] Document hook setup in user guide (MCP auto-start, bash end hook)

---

**Last Updated:** 2026-01-22
**Version:** 1.0
**Status:** Specification complete, ready for implementation in Phase Epsilon
