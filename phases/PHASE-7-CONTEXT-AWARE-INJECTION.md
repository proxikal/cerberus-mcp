# PHASE 7: CONTEXT-AWARE RETRIEVAL

## Objective
Provide MCP tool for on-demand memory retrieval based on current context. Zero startup cost.

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
        """
        last_occurred = memory.get("last_occurred")
        if not last_occurred:
            return 0.5  # Unknown = medium

        try:
            last_date = datetime.fromisoformat(last_occurred)
            days_ago = (datetime.now() - last_date).days

            # Decay function: recent=1.0, 30days=0.5, 90days=0.1
            if days_ago < 7:
                return 1.0
            elif days_ago < 30:
                return 0.7
            elif days_ago < 90:
                return 0.4
            else:
                return 0.1
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
    """

    # Budget allocation (total: 1500 tokens)
    BUDGET = {
        "universal": 700,   # Cross-project rules
        "language": 500,    # Language-specific rules
        "project": 300,     # Project-specific rules
    }

    TOTAL_BUDGET = 1500

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

        # Detect task (requires session analysis)
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
        Requires integration with session tracker.
        """
        # Stub: Analyze last 5 messages for task indicators
        return None
```

---

## MCP Tool Integration (On-Demand Retrieval)

```python
@mcp_tool
def memory_context(
    scope: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20
) -> str:
    """
    MCP tool: Retrieve memories on-demand (like cerberus search).

    Zero startup cost. Claude calls this when needed.

    Args:
        scope: Filter by scope (universal, language:X, project:Y)
        category: Filter by category (preference, rule, correction)
        limit: Max memories to return

    Returns:
        Markdown-formatted memories
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

    # Retrieve memories
    injector = ContextInjector(get_memory_store())
    return injector.inject(context, limit=limit)
```

**Architecture (Same as Cerberus Indexing):**
- Database: `.cerberus/memory.db`
- Zero startup cost (no auto-injection)
- Claude calls `memory_context()` when needed
- On-demand retrieval only

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
✓ TokenBudgetEnforcer class implemented
✓ ContextInjector class implemented
✓ ContextDetector class implemented
✓ MCP tool: memory_context() registered
✓ Zero startup cost (no auto-injection)
✓ Tests: 10 scenarios with expected memories
```

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

---

## Performance

- Scoring: O(n) for n memories
- Budget allocation: O(n log n) for sorting
- Total time: < 100ms for typical memory set (< 100 items)
