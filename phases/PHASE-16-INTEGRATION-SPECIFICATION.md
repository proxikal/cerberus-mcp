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
│              │  SessionStart Hook    │                        │
│              └───────────────────────┘                        │
│                          ↓                                    │
│    ┌─────────────────────────────────────────────┐           │
│    │  Auto-call: memory_context()                │           │
│    │  (ONE-TIME at session start)                │           │
│    └─────────────────────────────────────────────┘           │
│                          ↓                                    │
│    Phase 7: Context-aware memory injection                    │
│    (1500 tokens: universal + language + project)             │
│                          ↓                                    │
│    Phase 8: Active session injection                          │
│    (1000-1500 tokens: files, decisions, blockers)            │
│                          ↓                                    │
│         Returns: 2500-3000 tokens (relevant only)             │
│                          ↓                                    │
│              Claude has full context                          │
│                          ↓                                    │
│                   USER CONVERSATION                           │
│              (zero re-explanation needed)                     │
│                          ↓                                    │
│              ┌───────────────────────┐                        │
│              │  Session End Hook     │                        │
│              └───────────────────────┘                        │
│                          ↓                                    │
│    ┌─────────────────────────────────────────────┐           │
│    │  cerberus memory propose                    │           │
│    │  (Python subprocess or MCP call)            │           │
│    └─────────────────────────────────────────────┘           │
│                          ↓                                    │
│         Phases 1-4: Detect, cluster, propose, approve         │
│                          ↓                                    │
│              Phase 5: Store approved                          │
└──────────────────────────────────────────────────────────────┘
```

**Key Integration Points:**
- SessionStart hook: Auto-calls memory_context() (2500-3000 tokens ONE-TIME)
- Context-aware injection: Tiered filtering ensures relevance (Phase 7 + 8)
- Session-end hook: Captures session codes + runs proposal pipeline
- Zero tokens after startup (all context injected once at start)

---

## Integration Methods

### Method 1: SessionStart + SessionEnd Hooks (Recommended)

**Claude Code hooks:**
```bash
# ~/.claude/hooks/session-start.sh
#!/bin/bash
# Auto-calls memory_context() via MCP (built-in, no manual call needed)

# ~/.claude/hooks/session-end.sh
#!/bin/bash
cerberus memory propose --interactive
```

**Implementation in `src/cerberus/memory/hooks.py`:**
```python
# SessionStart handled by MCP auto-call to memory_context() (Phase 7 + 8)

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

**Note:** SessionStart hook auto-calls memory_context() - zero manual intervention

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

**Location:** `.cerberus/session_active.json`

**Purpose:** Track active session for correction detection

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

    with open(".cerberus/session_active.json", "w") as f:
        json.dump(state, f, indent=2)


def end_session() -> Dict[str, Any]:
    """Load and cleanup session state at session end."""
    try:
        with open(".cerberus/session_active.json", "r") as f:
            state = json.load(f)
    except FileNotFoundError:
        return {}

    # Archive session state
    session_id = state["session_id"]
    archive_path = f".cerberus/sessions/archive/{session_id}.json"
    os.makedirs(os.path.dirname(archive_path), exist_ok=True)

    with open(archive_path, "w") as f:
        json.dump(state, f, indent=2)

    # Remove active state
    os.remove(".cerberus/session_active.json")

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
    Install session hooks for CLI tool.

    Creates hook scripts in CLI's hook directory.
    """

    # Hook directory mapping
    HOOK_DIRS = {
        "claude-code": "~/.claude/hooks",
        "codex-cli": "~/.codex/hooks",
        "gemini-cli": "~/.gemini/hooks",
    }

    hook_dir = Path(HOOK_DIRS[cli_name]).expanduser()
    hook_dir.mkdir(parents=True, exist_ok=True)

    # Session start hook
    start_hook = hook_dir / "session-start.sh"
    start_hook.write_text("""#!/bin/bash
# Cerberus memory injection hook
cerberus memory inject --format markdown
""")
    start_hook.chmod(0o755)

    # Session end hook
    end_hook = hook_dir / "session-end.sh"
    end_hook.write_text("""#!/bin/bash
# Cerberus memory proposal hook
cerberus memory propose --interactive
""")
    end_hook.chmod(0o755)

    print(f"Installed hooks for {cli_name} in {hook_dir}")
```

---

## Error Handling

```python
def inject_hook_with_error_handling() -> str:
    """
    Safe injection hook with fallback.

    If injection fails, return empty string (session continues without memories).
    """
    try:
        return inject_hook()
    except Exception as e:
        # Log error
        log_error(f"Memory injection failed: {e}")

        # Return empty (session continues)
        return ""


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
# Inject memories (session start)
cerberus memory inject
cerberus memory inject --format markdown
cerberus memory inject --format json

# Propose memories (session end)
cerberus memory propose
cerberus memory propose --interactive
cerberus memory propose --batch --threshold 0.85

# Install hooks
cerberus memory install-hooks --cli claude-code
cerberus memory install-hooks --cli codex-cli

# Test hooks
cerberus memory test-hooks
```

---

## Token Costs

**Injection (session start):**
- Context detection: 0 tokens (Python)
- Phase 7 injection: 1500 tokens max
- Total: 1500 tokens

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
- ✅ Hooks install successfully
- ✅ Injection works (memories appear in Claude's context)
- ✅ Proposal works (corrections detected and stored)
- ✅ Error handling works (failures don't break session)
- ✅ Works with 3+ CLI tools (Claude Code, Codex, Gemini)
- ✅ 5+ real sessions tested

**Testing:**
- Manual: Run `cerberus memory install-hooks`, start session, verify injection
- Automated: Mock hook execution, verify output format
- Integration: Full session with corrections → verify storage

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
- [ ] Implement `inject_hook()` function
- [ ] Implement `propose_hook()` function
- [ ] Write `src/cerberus/memory/ipc.py` (if needed for IPC)
- [ ] Implement context detection (`detect_context()`)
- [ ] Implement session tracking (start/end session state)
- [ ] Add CLI commands (`cerberus memory inject`, `propose`, `install-hooks`)
- [ ] Write hook installation script
- [ ] Add error handling (fallback to empty on failure)
- [ ] Write unit tests (context detection, hook execution)
- [ ] Write integration tests (full session with hooks)
- [ ] Test with Claude Code
- [ ] Test with other CLIs (Codex, Gemini if available)
- [ ] Document hook setup in user guide

---

**Last Updated:** 2026-01-22
**Version:** 1.0
**Status:** Specification complete, ready for implementation in Phase Epsilon
