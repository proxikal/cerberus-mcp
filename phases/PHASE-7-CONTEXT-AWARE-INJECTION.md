# PHASE 7: CONTEXT-AWARE INJECTION

**Rollout Phase:** Alpha (Weeks 1-2)
**Status:** Implement after Phase 6

## Prerequisites

- ✅ Phase 6 complete (retrieval working)
- ✅ Phases 1-5 tested (end-to-end pipeline validated)

---

## Objective
Hybrid memory injection: Auto-inject high-relevance memories at session start (preferences, project context, session continuity), provide on-demand MCP tool for additional context during work.

**Injection Strategy:**
- **Session Start (Auto):** Load critical context immediately (1200 tokens: memories + 800 tokens: session codes = 2000 tokens total)
- **During Work (On-Demand):** MCP tool `memory_context(query)` for specific topics (500 tokens per query, max 2 queries)
- **Total Budget:** 3000 tokens per session (2000 startup + 1000 on-demand max)

---

## Implementation Location

**File:** `src/cerberus/memory/context_injector.py`

---

## Data Structures

```python
@dataclass
class InjectionContext:
    project: Optional[str]
    language: Optional[str]
    task: Optional[str]  # "coding", "debugging", "documentation", "architecture"
    file_path: Optional[str]

@dataclass
class ScoredMemory:
    content: str
    category: str
    scope: str
    score: float  # 0.0-1.0
    token_cost: int

@dataclass
class InjectionResult:
    memories: List[ScoredMemory]
    total_tokens: int
    budget_used: float  # percentage
    truncated: bool
```

---

## Injection Modes

### Mode 1: Session Start Auto-Injection

**When:** Agent Initialization (First Message). The Agent calls the `memory_context()` tool. No shell hook required.

**What gets auto-loaded:**

**Phase 7 Memories (1200 tokens):**
- Universal preferences (always relevant) → 300 tokens
- Language-specific rules (if language detected) → 300 tokens
- Project-specific decisions (if in project directory) → 400 tokens
- Reserve buffer → 200 tokens

**Phase 8 Session Codes (800 tokens):**
- impl: completed work → 300 tokens
- dec: architectural decisions → 200 tokens
- block: blockers + next: actions → 300 tokens

**Total:** 2000 tokens (AI-native format, extremely dense)

**Selection criteria:**
- Relevance score > 0.7 (high-relevance only)
- Scope match (project + language + universal)
- Recency (recent corrections prioritized)

**Format:** Markdown list injected at session start

---

### Mode 2: On-Demand Query (During Work)

**When:** Claude calls `memory_context(query="topic")` MCP tool

**What gets loaded:**
- Query-specific memories matching topic
- Examples: `memory_context(query="error handling")`, `memory_context(query="testing")`

**Per-query budget:** ~500 tokens

**Max queries per session:** 2 (to stay under 2000 token total cap)

**Selection criteria:**
- Relevance score > 0.5 (broader threshold)
- Query text match (keyword or semantic)
- Scope match (same as Mode 1)

**Format:** Markdown list with query context

---

## Token Budget Breakdown

```
Session Start (Auto):         2000 tokens
  ├─ Phase 7 Memories:        1200 tokens
  │   ├─ Universal preferences: 300 tokens
  │   ├─ Language rules:        300 tokens
  │   ├─ Project decisions:     400 tokens
  │   └─ Reserve:               200 tokens
  └─ Phase 8 Session codes:    800 tokens
      ├─ impl: (completed)      300 tokens
      ├─ dec: (decisions)       200 tokens
      └─ block: + next:         300 tokens

On-Demand Queries:            1000 tokens max
  ├─ Query 1:                  500 tokens
  └─ Query 2:                  500 tokens

Total Cap:                    3000 tokens per session
```

**Enforcement:**
- Hard cap at 2000 tokens total
- If on-demand query would exceed cap, truncate to fit
- Startup injection never skipped (always runs)

---

## Relevance Scoring

```python
class RelevanceScorer:
    """
    Score memories based on context match.
    """

    # Scoring weights
    WEIGHTS = {
        "scope_match": 0.4,      # Universal=0.4, language=0.7, project=1.0
        "frequency": 0.3,        # Correction frequency
        "recency": 0.2,          # Recent corrections higher
        "task_relevance": 0.1    # Task-specific boost
    }

    def score_memory(
        self,
        memory: Dict[str, Any],
        context: InjectionContext
    ) -> float:
        """
        Calculate relevance score 0.0-1.0.
        """
        scores = {}

        # Scope match
        scores["scope_match"] = self._score_scope(memory, context)

        # Frequency (for corrections)
        scores["frequency"] = self._score_frequency(memory)

        # Recency
        scores["recency"] = self._score_recency(memory)

        # Task relevance
        scores["task_relevance"] = self._score_task(memory, context)

        # Weighted sum
        total = sum(
            scores[key] * self.WEIGHTS[key]
            for key in scores
        )

        return min(total, 1.0)

    def _score_scope(self, memory: Dict, context: InjectionContext) -> float:
        """
        Score based on scope match.
        Universal < Language < Project in relevance.
        """
        scope = memory.get("scope", "universal")

        if scope == "universal":
            return 0.4  # Always relevant but low priority

        if scope.startswith("language:"):
            lang = scope.split(":")[1]
            if context.language and context.language == lang:
                return 0.7
            return 0.1  # Wrong language = low relevance

        if scope.startswith("project:"):
            proj = scope.split(":")[1]
            if context.project and context.project == proj:
                return 1.0
            return 0.05  # Wrong project = almost irrelevant

        return 0.4  # Default

    def _score_frequency(self, memory: Dict) -> float:
        """
        Higher frequency corrections = more important.
        """
        freq = memory.get("frequency", 1)
        # Normalize: freq 1-10 → score 0.1-1.0
        return min(freq / 10.0, 1.0)

    def _score_recency(self, memory: Dict) -> float:
        """
        Recent corrections more relevant.
        Standardized decay curve (matches Phase 6).
        """
        last_occurred = memory.get("last_occurred")
        if not last_occurred:
            return 0.5  # Unknown = medium

        try:
            last_date = datetime.fromisoformat(last_occurred)
            days_ago = (datetime.now() - last_date).days

            # Standardized decay curve
            if days_ago < 7:
                return 1.0
            elif days_ago < 30:
                return 0.8
            elif days_ago < 90:
                return 0.6
            elif days_ago < 180:
                return 0.4
            else:
                return 0.2
        except:
            return 0.5

    def _score_task(self, memory: Dict, context: InjectionContext) -> float:
        """
        Boost score if memory relevant to current task.
        """
        if not context.task:
            return 0.5

        content = memory.get("content", "").lower()
        task = context.task.lower()

        # Task-specific keywords
        task_keywords = {
            "coding": ["implement", "write", "create", "function", "class"],
            "debugging": ["error", "bug", "fix", "debug", "test"],
            "documentation": ["doc", "comment", "readme", "explain"],
            "architecture": ["design", "pattern", "structure", "module"]
        }

        keywords = task_keywords.get(task, [])
        matches = sum(1 for kw in keywords if kw in content)

        return min(matches / len(keywords), 1.0) if keywords else 0.5
```

---

## Token Budget Enforcement

```python
class TokenBudgetEnforcer:
    """
    Enforce strict token limits for injected context.

    Two modes:
    - Startup injection: 2000 tokens (1200 memories + 800 session codes)
    - On-demand query: 500 tokens (per query, max 2 queries)

    Total cap: 3000 tokens per session
    """

    # Session start auto-injection budget (total: 2000 tokens)
    # Phase 7 memories: 1200 tokens
    MEMORY_BUDGET = {
        "universal": 300,   # Universal preferences
        "language": 300,    # Language-specific rules
        "project": 400,     # Project-specific decisions
        "reserve": 200,     # Reserve buffer
    }

    # Phase 8 session codes: 800 tokens (handled by Phase 8)
    SESSION_CODES_BUDGET = 800

    # On-demand query budget (per query: 500 tokens)
    QUERY_BUDGET = {
        "universal": 150,
        "language": 150,
        "project": 200,
    }

    STARTUP_TOTAL = 2000  # 1200 + 800
    QUERY_TOTAL = 500
    SESSION_CAP = 3000  # Hard cap per session

    def __init__(self):
        self.tokenizer = TokenCounter()

    def enforce_budget(
        self,
        scored_memories: List[ScoredMemory]
    ) -> List[ScoredMemory]:
        """
        Select memories that fit within token budget.
        Priority: highest score first, respect scope budgets.
        """
        # Group by scope
        by_scope = {
            "universal": [],
            "language": [],
            "project": []
        }

        for mem in scored_memories:
            scope_type = self._get_scope_type(mem.scope)
            by_scope[scope_type].append(mem)

        # Sort each scope by score (descending)
        for scope in by_scope:
            by_scope[scope].sort(key=lambda m: m.score, reverse=True)

        # Allocate tokens per scope
        selected = []
        for scope, budget in self.BUDGET.items():
            selected.extend(
                self._allocate_scope(by_scope[scope], budget)
            )

        return selected

    def _allocate_scope(
        self,
        memories: List[ScoredMemory],
        budget: int
    ) -> List[ScoredMemory]:
        """
        Greedy allocation: take highest scored until budget exhausted.
        """
        selected = []
        used = 0

        for mem in memories:
            if used + mem.token_cost <= budget:
                selected.append(mem)
                used += mem.token_cost

        return selected

    def _get_scope_type(self, scope: str) -> str:
        """Extract scope type from scope string."""
        if scope == "universal":
            return "universal"
        elif scope.startswith("language:"):
            return "language"
        elif scope.startswith("project:"):
            return "project"
        return "universal"
```

---

## Context Injector

```python
class ContextInjector:
    """
    Main class: Score, filter, format memories for injection.
    """

    def __init__(self, memory_store: MemoryStore):
        self.store = memory_store
        self.scorer = RelevanceScorer()
        self.enforcer = TokenBudgetEnforcer()
        self.tokenizer = TokenCounter()

    def inject(self, context: InjectionContext) -> str:
        """
        Generate context string for prompt injection.
        """
        # Load all memories
        all_memories = self._load_all_memories(context)

        if not all_memories:
            return ""

        # Score each memory
        scored = [
            ScoredMemory(
                content=mem["content"],
                category=mem["category"],
                scope=mem.get("scope", "universal"),
                score=self.scorer.score_memory(mem, context),
                token_cost=self.tokenizer.count(mem["content"])
            )
            for mem in all_memories
        ]

        # Filter low-relevance (score < 0.3)
        scored = [m for m in scored if m.score >= 0.3]

        # Enforce budget
        selected = self.enforcer.enforce_budget(scored)

        # Format for injection
        return self._format_context(selected, context)

    def _load_all_memories(self, context: InjectionContext) -> List[Dict]:
        """
        Load relevant memories from all layers.
        """
        memories = []

        # Global preferences
        profile_mgr = ProfileManager(self.store)
        profile = profile_mgr.load_profile()
        memories.extend(self._profile_to_memories(profile))

        # Language-specific
        if context.language and profile.languages:
            lang_prefs = profile.languages.get(context.language, [])
            memories.extend([
                {
                    "content": pref,
                    "category": "preference",
                    "scope": f"language:{context.language}"
                }
                for pref in lang_prefs
            ])

        # Project-specific
        if context.project:
            decision_mgr = DecisionManager(self.store)
            decisions = decision_mgr.load_decisions(context.project)
            memories.extend([
                {
                    "content": d.decision,
                    "category": "decision",
                    "scope": f"project:{context.project}",
                    "last_occurred": d.timestamp
                }
                for d in decisions.decisions
            ])

        # Corrections
        correction_mgr = CorrectionManager(self.store)
        corrections = correction_mgr.load_corrections()
        memories.extend([
            {
                "content": c.pattern,
                "category": "correction",
                "scope": "universal",
                "frequency": c.frequency,
                "last_occurred": c.last_occurred
            }
            for c in corrections.corrections
        ])

        return memories

    def _profile_to_memories(self, profile: Profile) -> List[Dict]:
        """Convert profile to memory format."""
        memories = []

        # General preferences
        for pref in profile.general or []:
            memories.append({
                "content": pref,
                "category": "preference",
                "scope": "universal"
            })

        # Anti-patterns
        for ap in profile.anti_patterns or []:
            memories.append({
                "content": f"Avoid: {ap}",
                "category": "anti_pattern",
                "scope": "universal"
            })

        return memories

    def _format_context(
        self,
        memories: List[ScoredMemory],
        context: InjectionContext
    ) -> str:
        """
        Format memories as markdown for injection.
        """
        lines = ["## Developer Memory"]
        lines.append("")

        # Group by scope
        universal = [m for m in memories if m.scope == "universal"]
        language = [m for m in memories if m.scope.startswith("language:")]
        project = [m for m in memories if m.scope.startswith("project:")]

        if universal:
            lines.append("### Universal Rules")
            for mem in sorted(universal, key=lambda m: m.score, reverse=True):
                lines.append(f"- {mem.content}")
            lines.append("")

        if language and context.language:
            lines.append(f"### {context.language.title()} Preferences")
            for mem in sorted(language, key=lambda m: m.score, reverse=True):
                lines.append(f"- {mem.content}")
            lines.append("")

        if project and context.project:
            lines.append(f"### {context.project.title()} Decisions")
            for mem in sorted(project, key=lambda m: m.score, reverse=True):
                lines.append(f"- {mem.content}")
            lines.append("")

        return "\n".join(lines)
```

---

## Context Detection

```python
class ContextDetector:
    """
    Auto-detect injection context from environment.
    """

    def detect(self) -> InjectionContext:
        """
        Detect current context from cwd, files, etc.
        """
        cwd = Path.cwd()

        # Detect project
        project = self._detect_project(cwd)

        # Detect language
        language = self._detect_language(cwd)

        # Detect task (requires session analysis - Phase 8)
        task = self._detect_task()

        return InjectionContext(
            project=project,
            language=language,
            task=task,
            file_path=None
        )

    def _detect_project(self, cwd: Path) -> Optional[str]:
        """Detect project name from directory or git."""
        # Check for .git
        if (cwd / ".git").exists():
            return cwd.name

        # Check for pyproject.toml, package.json, etc.
        if (cwd / "pyproject.toml").exists():
            # Parse project name from pyproject.toml
            pass

        return None

    def _detect_language(self, cwd: Path) -> Optional[str]:
        """Detect primary language from file extensions."""
        files = list(cwd.rglob("*"))
        extensions = [f.suffix for f in files if f.is_file()]

        # Count extensions
        from collections import Counter
        counts = Counter(extensions)

        # Map extensions to languages
        ext_map = {
            ".py": "python",
            ".go": "go",
            ".ts": "typescript",
            ".js": "javascript",
            ".rs": "rust"
        }

        # Return most common
        for ext, _ in counts.most_common():
            if ext in ext_map:
                return ext_map[ext]

        return None

    def _detect_task(self) -> Optional[str]:
        """
        Detect current task from recent session activity.
        Requires integration with session tracker (Phase 8).
        """
        # Stub: Analyze last 5 messages for task indicators
        return None
```

---

## Integration Points (Hybrid Model)

### 1. Session Start Auto-Injection

**Called by:** Agent internally via MCP tool call at initialization (Phase 16)

```python
def inject_session_start() -> str:
    """
    Auto-inject high-relevance memories at session start.

    Called internally when the Agent initializes and calls memory_context().

    Returns:
        Markdown-formatted memories (~1000 tokens)
    """
    # Detect context
    detector = ContextDetector()
    context = detector.detect()

    # Retrieve high-relevance only (score > 0.7)
    injector = ContextInjector(get_memory_store())
    return injector.inject_startup(context, budget=STARTUP_BUDGET)
```

**Budget:** 1000 tokens (200 universal + 200 language + 300 project + 300 session)

---

### 2. On-Demand Query (MCP Tool)

**Called by:** Claude during work (when needs additional context)

```python
@mcp_tool
def memory_context(
    query: Optional[str] = None,
    scope: Optional[str] = None,
    category: Optional[str] = None
) -> str:
    """
    MCP tool: Retrieve memories on-demand during work.

    Claude calls this when needs specific context not in startup injection.

    Args:
        query: Optional text query (e.g., "error handling", "testing")
        scope: Filter by scope (universal, language:X, project:Y)
        category: Filter by category (preference, rule, correction)

    Returns:
        Markdown-formatted memories (~500 tokens)
    """
    # Detect context
    detector = ContextDetector()
    context = detector.detect()

    # Override with explicit scope if provided
    if scope:
        if scope.startswith("language:"):
            context.language = scope.split(":")[1]
        elif scope.startswith("project:"):
            context.project = scope.split(":")[1]

    # Add query filter
    context.query = query

    # Retrieve memories (broader threshold: score > 0.5)
    injector = ContextInjector(get_memory_store())
    return injector.inject_query(context, budget=QUERY_BUDGET)
```

**Budget:** 500 tokens per query, max 2 queries per session

---

**Architecture (Hybrid Model):**
- Database: `~/.cerberus/memory.db` (global SQLite database)
- Startup cost: 1000 tokens (auto-injected at session start)
- On-demand cost: 0-1000 tokens (if Claude calls tool 1-2 times)
- Total cap: 2000 tokens per session

**Example Usage:**
```python
# Claude's internal thought process:
# "User asked about Python style preferences, let me check memories"
result = memory_context(scope="language:python", category="preference")

# "User corrected me about this project, check project decisions"
result = memory_context(scope="project:myapp")
```

---

## Exit Criteria

```
✓ RelevanceScorer class implemented
✓ TokenBudgetEnforcer class implemented (with MEMORY_BUDGET, SESSION_CODES_BUDGET, and QUERY_BUDGET)
✓ ContextInjector class implemented (inject_startup and inject_query methods)
✓ ContextDetector class implemented
✓ SessionStart auto-injection working (2000 tokens: 1200 memories + 800 session codes)
✓ MCP tool: memory_context(query) registered for on-demand queries (500 tokens)
✓ Total cap enforcement (3000 tokens per session)
✓ Phase 8 integration: Session codes injected with memories at startup
✓ Phase 16 integration: SessionStart hook calls inject_session_start()
✓ Tests: 15 scenarios (startup injection + on-demand queries)
```

---

## Token Budget Summary

**Hybrid Model:**

```
Session Start (Auto):              2000 tokens
  ├─ Phase 7 Memories:             1200 tokens
  │   ├─ Universal preferences:     300 tokens  (score > 0.7)
  │   ├─ Language rules:            300 tokens  (score > 0.7)
  │   ├─ Project decisions:         400 tokens  (score > 0.7)
  │   └─ Reserve:                   200 tokens
  └─ Phase 8 Session codes:         800 tokens  (AI-native format)
      ├─ impl: completed work       300 tokens
      ├─ dec: decisions             200 tokens
      └─ block: + next:             300 tokens

On-Demand Queries (Optional):      0-1000 tokens
  ├─ Query 1: memory_context():     500 tokens  (score > 0.5)
  └─ Query 2: memory_context():     500 tokens  (score > 0.5)

Total Per Session:                 2000-3000 tokens
```

**Benefits:**
- Critical context available immediately (no wasted turns)
- AI-native codes = 3x more dense than prose (800 tokens = ~40 items)
- Additional context available when needed (flexibility)
- Token efficient (only loads what's relevant)
- Hard cap prevents runaway costs (3000 tokens max)
- Cost: ~$0.003 per session with Sonnet 4.5

---

## Test Scenarios

```python
# Scenario 1: Universal only (no project/language detected)
context = InjectionContext(project=None, language=None, task="coding")
memories = [universal rules, corrections]
→ expect: Only universal (budget: 500 tokens)

# Scenario 2: Go project
context = InjectionContext(project="hydra", language="go", task="coding")
→ expect: Universal + Go-specific + Hydra-specific (total: 1000 tokens)

# Scenario 3: Budget exceeded
memories = 50 rules (3000 tokens total)
→ expect: Top 20-25 by score (exactly 1500 tokens)

# Scenario 4: Low relevance filtered
context = InjectionContext(project="cerberus", language="python", task="coding")
memories include Go-specific rules (score < 0.3)
→ expect: Go rules excluded
```

---

## Dependencies

```bash
pip install tiktoken  # Token counting
```

---

## Token Budget

- Injection output: 1500 tokens max (enforced)
- Scoring computation: 0 tokens (local)
- Context detection: 0 tokens (file system analysis)

**Note:** Phase 8 extends this with session context (1000-1500 tokens), bringing total injection budget to 2500-3000 tokens.

---

## Performance

- Scoring: O(n) for n memories
- Budget allocation: O(n log n) for sorting
- Total time: < 100ms for typical memory set (< 100 items)
