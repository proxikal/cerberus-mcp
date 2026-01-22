# PHASE 9: SESSION SUMMARY

## Objective
Generate LLM summary from session context, inject at session start. 500 token budget.

---

## Implementation Location

**File:** `src/cerberus/memory/session_summary.py`

---

## Data Structures

```python
@dataclass
class SessionContext:
    """Raw context from Phase 8 capture."""
    session_id: str
    project: str
    timestamp: str
    files: List[str]  # impl:file.py codes
    functions: List[str]  # impl:module.func codes
    decisions: List[str]  # dec:choice codes
    blockers: List[str]  # block:type:desc codes
    next_actions: List[str]  # next:action codes
    raw_context: Dict[str, Any]  # Full capture data

@dataclass
class SessionSummary:
    """LLM-generated summary for injection."""
    session_id: str
    project: str
    summary: str  # 2-3 sentences
    key_context: List[str]  # Top 5 most important items
    next_actions: List[str]  # Unprefixed actions
    token_estimate: int
    timestamp: str
    expires_at: str  # 7 days from creation

@dataclass
class InjectionPackage:
    """Ready-to-inject summary."""
    markdown: str  # Formatted for prompt injection
    token_count: int
    session_info: SessionSummary
```

---

## Session Summarizer

```python
class SessionSummarizer:
    """
    Generate LLM summary from session context.
    """

    def __init__(self, llm_client: Any):
        self.llm = llm_client

    def generate_summary(
        self,
        context: SessionContext
    ) -> SessionSummary:
        """
        Generate 2-3 sentence summary from context.
        """
        # Build prompt
        prompt = self._build_prompt(context)

        # Call LLM
        response = self.llm.generate(
            prompt=prompt,
            max_tokens=200,
            temperature=0.3
        )

        # Parse response
        summary_text = self._extract_summary(response)

        # Identify key context items
        key_context = self._select_key_items(context, limit=5)

        # Token estimate
        token_est = self._estimate_tokens(summary_text, key_context)

        return SessionSummary(
            session_id=context.session_id,
            project=context.project,
            summary=summary_text,
            key_context=key_context,
            next_actions=context.next_actions,
            token_estimate=token_est,
            timestamp=datetime.now().isoformat(),
            expires_at=self._calc_expiry()
        )

    def _build_prompt(self, context: SessionContext) -> str:
        """
        Build LLM prompt from context codes.
        """
        return f"""Summarize this coding session in 2-3 sentences:

Project: {context.project}

Files modified: {len(context.files)}
{chr(10).join(f"- {f}" for f in context.files[:5])}

Key decisions:
{chr(10).join(f"- {d}" for d in context.decisions[:3])}

Blockers:
{chr(10).join(f"- {b}" for b in context.blockers)}

Output format (2-3 sentences):
1. What was accomplished
2. Key decisions made
3. What's next (if clear)

Keep it terse, imperative, AI-readable."""

    def _extract_summary(self, response: str) -> str:
        """
        Extract clean summary from LLM response.
        """
        # Remove any preamble
        lines = response.strip().split("\n")
        summary_lines = [
            line for line in lines
            if line.strip() and not line.startswith("#")
        ]

        # Join and limit to 3 sentences
        text = " ".join(summary_lines)
        sentences = text.split(". ")[:3]
        return ". ".join(sentences).strip()

    def _select_key_items(
        self,
        context: SessionContext,
        limit: int
    ) -> List[str]:
        """
        Select most important context items.
        Priority: blockers > decisions > files > functions
        """
        key_items = []

        # Blockers (highest priority)
        key_items.extend(context.blockers)

        # Decisions
        key_items.extend(context.decisions[:3])

        # Files (top 3)
        key_items.extend(context.files[:3])

        # Functions (if space)
        remaining = limit - len(key_items)
        if remaining > 0:
            key_items.extend(context.functions[:remaining])

        return key_items[:limit]

    def _estimate_tokens(
        self,
        summary: str,
        key_context: List[str]
    ) -> int:
        """
        Estimate tokens for injection.
        """
        # Summary
        tokens = len(summary.split()) * 1.3

        # Key context items
        tokens += sum(len(item.split()) * 1.3 for item in key_context)

        # Formatting overhead
        tokens += 50

        return int(tokens)

    def _calc_expiry(self) -> str:
        """
        Calculate 7-day expiry timestamp.
        """
        expiry = datetime.now() + timedelta(days=7)
        return expiry.isoformat()
```

---

## Session Context Injector

```python
class SessionContextInjector:
    """
    Load and inject session context at session start.
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path / "memory" / "sessions"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def inject(self, project: str) -> Optional[InjectionPackage]:
        """
        Load and format session context for injection.
        """
        # Find active session for project
        summary = self._load_active_session(project)

        if not summary:
            return None

        # Check expiry
        if self._is_expired(summary):
            self._archive(summary)
            return None

        # Format for injection
        markdown = self._format_markdown(summary)
        token_count = self._count_tokens(markdown)

        return InjectionPackage(
            markdown=markdown,
            token_count=token_count,
            session_info=summary
        )

    def save_context(
        self,
        summary: SessionSummary
    ):
        """
        Save session summary to storage.
        """
        file_path = self.base_path / f"active-{summary.project}.json"

        data = {
            "session_id": summary.session_id,
            "project": summary.project,
            "summary": summary.summary,
            "key_context": summary.key_context,
            "next_actions": summary.next_actions,
            "token_estimate": summary.token_estimate,
            "timestamp": summary.timestamp,
            "expires_at": summary.expires_at
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_active_session(
        self,
        project: str
    ) -> Optional[SessionSummary]:
        """
        Load active session for project.
        """
        file_path = self.base_path / f"active-{project}.json"

        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)

            return SessionSummary(**data)

        except (json.JSONDecodeError, IOError, TypeError):
            return None

    def _is_expired(self, summary: SessionSummary) -> bool:
        """
        Check if summary has expired (>7 days).
        """
        try:
            expires = datetime.fromisoformat(summary.expires_at)
            return datetime.now() > expires
        except (ValueError, TypeError):
            return True

    def _archive(self, summary: SessionSummary):
        """
        Move expired session to archive.
        """
        # Remove active file
        active_path = self.base_path / f"active-{summary.project}.json"
        if active_path.exists():
            active_path.unlink()

        # Save to archive (optional)
        archive_dir = self.base_path / "archive"
        archive_dir.mkdir(exist_ok=True)

        archive_path = archive_dir / f"{summary.session_id}.json"
        with open(archive_path, "w") as f:
            json.dump({
                "session_id": summary.session_id,
                "project": summary.project,
                "summary": summary.summary,
                "timestamp": summary.timestamp,
                "archived_at": datetime.now().isoformat()
            }, f, indent=2)

    def _format_markdown(self, summary: SessionSummary) -> str:
        """
        Format summary as markdown for injection.
        """
        lines = [
            "## Previous Session Context",
            "",
            f"**Project:** {summary.project}",
            "",
            f"**Summary:** {summary.summary}",
            ""
        ]

        # Key context
        if summary.key_context:
            lines.append("**Context:**")
            for item in summary.key_context:
                lines.append(f"- {item}")
            lines.append("")

        # Next actions
        if summary.next_actions:
            lines.append("**Next:**")
            for action in summary.next_actions:
                lines.append(f"- {action}")
            lines.append("")

        return "\n".join(lines)

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in markdown text.
        """
        return int(len(text.split()) * 1.3)
```

---

## Integration Pipeline

```python
def on_session_end():
    """
    Phase 8 → Phase 9: Capture → Summary
    """
    # Phase 8: Capture context during session
    capture_engine = SessionContextCapture()
    context = capture_engine.get_context()

    # Phase 9: Generate summary
    summarizer = SessionSummarizer(llm_client)
    summary = summarizer.generate_summary(context)

    # Save for next session
    injector = SessionContextInjector(Path.home() / ".cerberus")
    injector.save_context(summary)

    print(f"✓ Session context saved ({summary.token_estimate} tokens)")

def on_session_start(project: str):
    """
    Phase 9: Inject previous session context
    Phase 7: Inject memories
    """
    # Phase 9: Load session context
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
        full_context = memory_context + "\n\n" + session_pkg.markdown
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
                expires = datetime.fromisoformat(data["expires_at"])
                if datetime.now() > expires:
                    # Archive
                    self._archive_file(file_path, data)
                    archived += 1

            except (json.JSONDecodeError, IOError, KeyError, ValueError):
                # Malformed file, remove
                file_path.unlink()

        return archived

    def _archive_file(self, file_path: Path, data: Dict):
        """
        Move file to archive.
        """
        archive_dir = self.sessions_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        archive_path = archive_dir / f"{data['session_id']}.json"

        # Add archive timestamp
        data["archived_at"] = datetime.now().isoformat()

        # Save to archive
        with open(archive_path, "w") as f:
            json.dump(data, f, indent=2)

        # Remove active file
        file_path.unlink()
```

---

## Exit Criteria

```
✓ SessionSummarizer class implemented
✓ LLM summary generation working (2-3 sentences)
✓ SessionContextInjector implemented
✓ Session storage working (active-{project}.json)
✓ Expiry detection working (7 days)
✓ Archival working
✓ Integration with Phase 8 complete
✓ Integration with Phase 7 complete
✓ Token budget enforced (500 tokens)
✓ Tests: 10 summary scenarios
```

---

## Test Scenarios

```python
# Scenario 1: Basic summary generation
context: 5 files, 3 decisions, 1 blocker
→ expect: 2-3 sentence summary, < 150 tokens

# Scenario 2: Save and load
save summary for project "hydra"
→ load on next session
→ expect: same summary returned

# Scenario 3: Expiry detection
summary: created 8 days ago
→ expect: archived, not returned

# Scenario 4: Priority selection
context: 2 blockers, 5 decisions, 10 files
→ expect: key_context = [2 blockers, 3 decisions]

# Scenario 5: No previous session
project: "new-project"
→ expect: inject() returns None, no error

# Scenario 6: Token budget enforcement
summary: 300 tokens
key_context: 5 items × 50 tokens = 250 tokens
→ expect: total < 500 tokens

# Scenario 7: Malformed session file
storage: corrupted JSON
→ expect: skip, return None, no crash

# Scenario 8: Multiple projects
save summaries for "hydra", "cerberus"
→ load "hydra"
→ expect: only hydra summary returned

# Scenario 9: Cleanup expired
3 sessions: expired, expired, active
→ cleanup_expired()
→ expect: 2 archived, 1 active remains

# Scenario 10: Integration with Phase 7
session context: 200 tokens
memory injection: 1500 tokens
→ expect: combined < 2000 tokens
```

---

## Dependencies

- LLM client (ollama-python or anthropic SDK)
- Phase 8 (SessionContextCapture for raw context)
- Phase 7 (ContextInjector for memory integration)
- Phase 6 (MemoryRetrieval used by Phase 7)

---

## Performance

- LLM summary generation: < 2 seconds
- Save context: < 5ms
- Load context: < 10ms
- Cleanup expired: < 100ms (10 sessions)

---

## Token Budget Breakdown

**Session End (500 tokens):**
```
LLM prompt:         150 tokens (context codes)
LLM response:       100 tokens (2-3 sentences)
Key context:        200 tokens (5 items)
Formatting:          50 tokens (markdown)
─────────────────────────────
Total:              500 tokens
```

**Session Start (500 tokens):**
```
Summary text:       100 tokens (2-3 sentences)
Key context:        200 tokens (5 items)
Next actions:       150 tokens (3-5 actions)
Formatting:          50 tokens (markdown headers)
─────────────────────────────
Total:              500 tokens (injection)
```

**Combined with Phase 7:**
```
Memory injection:   1500 tokens (Phase 7 budget)
Session context:     500 tokens (Phase 9 budget)
─────────────────────────────
Total start:        2000 tokens (session start total)
```

---

## AI-Native Storage Codes

**Phase 8 captures in terse codes, Phase 9 summarizes:**

```
Input (Phase 8 codes):
- impl:proxy.go
- impl:supervisor.Process
- dec:split-proxy-3-files
- block:test:race-condition
- next:fix-race-add-mutex

Output (Phase 9 summary):
"Split proxy.go into 3 files (forwarding, recording, state).
Decided to modularize for 200-line limit.
Next: Fix race condition with mutex."
```

**Token efficiency:** Codes = 50 tokens, Summary = 100 tokens (vs 300+ verbose)
