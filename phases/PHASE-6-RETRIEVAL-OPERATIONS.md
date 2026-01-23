# ⚠️ AI AGENT INSTRUCTION (PHASE ALPHA)
# IMPLEMENT "VERSION 1: JSON RETRIEVAL" ONLY.
# DO NOT READ OR IMPLEMENT "VERSION 2: SQLITE".
# IGNORE FTS5/SEARCH ENGINE REFERENCES FOR THIS PHASE.

# PHASE 6: RETRIEVAL OPERATIONS

**Rollout Phase:** Alpha (JSON) → Beta (SQLite)
**Status:** Implemented in 2 stages

## Prerequisites

- ✅ Phase 5 complete (storage working, memories exist to retrieve)

---

## Objective
Query and filter memories for context-aware injection. Read operations only.

## Implementation Strategy & Retrieval Evolution Timeline

**IMPORTANT: This file documents BOTH versions. Phase 6 gets rewritten in Beta.**

```
┌─────────────────────────────────────────────────────────────────┐
│                   RETRIEVAL EVOLUTION TIMELINE                   │
└─────────────────────────────────────────────────────────────────┘

PHASE ALPHA (Weeks 1-2):
  ┌─────────────────────────────────────┐
  │ Phase 6: JSON Retrieval (Version 1) │
  │ - Read from ~/.cerberus/memory.db   │
  │ - (JSON for Alpha, SQLite in Beta)  │
  │ - Simple, works for MVP             │
  └─────────────────────────────────────┘
                    ↓
  Validation Gates (70%+ approval, 90%+ accuracy)
                    ↓
PHASE BETA (Weeks 3-4):
  ┌─────────────────────────────────────┐
  │ Phase 12: SQLite Migration          │
  │ - JSON data migrated to memory.db   │
  │ - FTS5 indexes created              │
  └─────────────────────────────────────┘
                    ↓
  ┌─────────────────────────────────────┐
  │ Phase 13: Rewrite Phase 6           │
  │ - Phase 6: NOW queries SQLite FTS5  │
  │ - 80% token savings (targeted query)│
  │ - Fallback to JSON if SQLite fails  │
  └─────────────────────────────────────┘

RESULT:
  Phase 6 code exists in TWO versions:
  - Version 1 (Alpha): JSON reads (this file, below)
  - Version 2 (Beta):  SQLite FTS5 queries (PHASE-13B-INTEGRATION.md)
```

**Implementation versions:**
- **Phase Alpha:** Use code in this file (JSON loading)
- **Phase Beta:** Replace with code from PHASE-13B-INTEGRATION.md (SQLite queries)

---

## Implementation Location

**File:** `src/cerberus/memory/retrieval.py`

---

## Data Structures

```python
@dataclass
class MemoryQuery:
    """Query parameters for memory retrieval."""
    scope: Optional[str] = None  # Filter by scope
    category: Optional[str] = None  # Filter by category
    max_results: int = 50
    min_confidence: float = 0.0

@dataclass
class RetrievedMemory:
    """Single memory with relevance score."""
    content: str
    scope: str
    category: str
    confidence: float
    timestamp: str
    relevance_score: float  # 0.0-1.0
    reason: str  # Why this memory matched

@dataclass
class RetrievalResult:
    """Query results with metadata."""
    memories: List[RetrievedMemory]
    total_found: int
    total_returned: int
    token_estimate: int
```

---

## Memory Retrieval

```python
class MemoryRetrieval:
    """
    Load memories from hierarchical storage.
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path / "memory"

    def query(
        self,
        context: Dict[str, Any],
        query: MemoryQuery
    ) -> RetrievalResult:
        """
        Load memories matching query and context.
        """
        # Load from storage
        all_memories = self._load_all_memories(query)

        # Score relevance
        scorer = RelevanceScorer(context)
        scored = [
            (mem, scorer.score(mem))
            for mem in all_memories
        ]

        # Filter by min confidence
        filtered = [
            (mem, score)
            for mem, score in scored
            if mem.confidence >= query.min_confidence
        ]

        # Sort by relevance
        sorted_mems = sorted(filtered, key=lambda x: x[1], reverse=True)

        # Limit results
        top_n = sorted_mems[:query.max_results]

        # Create result objects
        results = [
            RetrievedMemory(
                content=mem.content,
                scope=mem.scope,
                category=mem.category,
                confidence=mem.confidence,
                timestamp=mem.timestamp,
                relevance_score=score,
                reason=scorer.explain(mem, score)
            )
            for mem, score in top_n
        ]

        # Token estimate
        token_est = self._estimate_tokens(results)

        return RetrievalResult(
            memories=results,
            total_found=len(all_memories),
            total_returned=len(results),
            token_estimate=token_est
        )

    def _load_all_memories(self, query: MemoryQuery) -> List[Dict]:
        """
        Load memories from files based on query scope.
        """
        memories = []

        # Universal
        memories.extend(self._load_file(self.base_path / "profile.json", "general"))
        memories.extend(self._load_file(self.base_path / "corrections.json", "corrections"))

        # Language (if scope specified)
        if query.scope and query.scope.startswith("language:"):
            lang = query.scope.split(":")[1]
            memories.extend(self._load_file(
                self.base_path / "languages" / f"{lang}.json",
                "preferences"
            ))
        else:
            # Load all languages
            lang_dir = self.base_path / "languages"
            if lang_dir.exists():
                for lang_file in lang_dir.glob("*.json"):
                    memories.extend(self._load_file(lang_file, "preferences"))

        # Project (if scope specified)
        if query.scope and query.scope.startswith("project:"):
            parts = query.scope.split(":")
            project = parts[1]

            # Project decisions
            memories.extend(self._load_file(
                self.base_path / "projects" / project / "decisions.json",
                "decisions"
            ))

            # Task-specific (if specified)
            if len(parts) >= 4 and parts[2] == "task":
                task = parts[3]
                memories.extend(self._load_file(
                    self.base_path / "projects" / project / "tasks" / f"{task}.json",
                    "rules"
                ))
        else:
            # Load all projects
            proj_dir = self.base_path / "projects"
            if proj_dir.exists():
                for proj in proj_dir.iterdir():
                    if proj.is_dir():
                        memories.extend(self._load_file(proj / "decisions.json", "decisions"))

                        # Load all tasks
                        task_dir = proj / "tasks"
                        if task_dir.exists():
                            for task_file in task_dir.glob("*.json"):
                                memories.extend(self._load_file(task_file, "rules"))

        # Filter by category if specified
        if query.category:
            memories = [m for m in memories if m.get("category") == query.category]

        return memories

    def _load_file(self, path: Path, data_key: str) -> List[Dict]:
        """Load memories from single file."""
        if not path.exists():
            return []

        try:
            with open(path) as f:
                data = json.load(f)

            if data_key not in data:
                return []

            # Add metadata
            memories = []
            for item in data[data_key]:
                mem = {
                    "content": item["content"],
                    "timestamp": item["timestamp"],
                    "confidence": item.get("confidence", 1.0),
                    "scope": self._infer_scope(path),
                    "category": data_key
                }
                memories.append(mem)

            return memories

        except (json.JSONDecodeError, IOError):
            return []

    def _infer_scope(self, path: Path) -> str:
        """Infer scope from file path."""
        path_str = str(path)

        if "languages" in path_str:
            # Extract language
            lang = path.stem
            return f"language:{lang}"

        if "projects" in path_str:
            # Extract project name
            parts = path.parts
            proj_idx = parts.index("projects") + 1
            project = parts[proj_idx]

            # Check if task-specific
            if "tasks" in path_str:
                task = path.stem
                return f"project:{project}:task:{task}"

            return f"project:{project}"

        return "universal"

    def _estimate_tokens(self, memories: List[RetrievedMemory]) -> int:
        """Estimate token count for memories."""
        total = 0
        for mem in memories:
            # Content + metadata overhead
            total += len(mem.content.split()) * 1.3  # ~1.3 tokens/word
            total += 10  # Metadata overhead

        return int(total)
```

---

## Relevance Scoring

```python
class RelevanceScorer:
    """
    Score memory relevance for current context.
    """

    def __init__(self, context: Dict[str, Any]):
        self.context = context

    def score(self, memory: Dict) -> float:
        """
        Calculate relevance score (0.0-1.0).
        """
        score = 0.0

        # Scope match (0.5 weight)
        scope_score = self._scope_match(memory["scope"])
        score += scope_score * 0.5

        # Recency (0.2 weight)
        recency_score = self._recency_score(memory["timestamp"])
        score += recency_score * 0.2

        # Confidence (0.2 weight)
        score += memory.get("confidence", 1.0) * 0.2

        # Task match (0.1 weight)
        task_score = self._task_match(memory["scope"])
        score += task_score * 0.1

        return min(1.0, score)

    def _scope_match(self, mem_scope: str) -> float:
        """
        Score how well memory scope matches context.
        """
        ctx_project = self.context.get("project")
        ctx_language = self.context.get("language")
        ctx_task = self.context.get("task")

        # Universal always matches
        if mem_scope == "universal":
            return 0.8

        # Language match
        if mem_scope.startswith("language:"):
            mem_lang = mem_scope.split(":")[1]
            if mem_lang == ctx_language:
                return 1.0
            return 0.3  # Wrong language = low relevance

        # Project match
        if mem_scope.startswith("project:"):
            parts = mem_scope.split(":")
            mem_project = parts[1]

            if mem_project != ctx_project:
                return 0.2  # Different project = low relevance

            # Project-level match
            if len(parts) == 2:
                return 0.9

            # Task-level match
            if len(parts) >= 4 and parts[2] == "task":
                mem_task = parts[3]
                if mem_task == ctx_task:
                    return 1.0
                return 0.7  # Same project, different task

        return 0.5  # Default

    def _recency_score(self, timestamp: str) -> float:
        """
        Score based on how recent the memory is.
        """
        try:
            mem_time = datetime.fromisoformat(timestamp)
            now = datetime.now()
            age_days = (now - mem_time).days

            # Decay curve
            if age_days < 7:
                return 1.0
            elif age_days < 30:
                return 0.8
            elif age_days < 90:
                return 0.6
            elif age_days < 180:
                return 0.4
            else:
                return 0.2

        except (ValueError, TypeError):
            return 0.5  # Unknown timestamp

    def _task_match(self, mem_scope: str) -> float:
        """
        Score task-specific match.
        """
        ctx_task = self.context.get("task")

        if not ctx_task:
            return 0.5

        if f"task:{ctx_task}" in mem_scope:
            return 1.0

        return 0.3

    def explain(self, memory: Dict, score: float) -> str:
        """
        Generate explanation for score.
        """
        reasons = []

        # Scope
        mem_scope = memory["scope"]
        if mem_scope == "universal":
            reasons.append("universal")
        elif mem_scope.startswith("language:"):
            lang = mem_scope.split(":")[1]
            if lang == self.context.get("language"):
                reasons.append(f"lang:{lang}")
        elif mem_scope.startswith("project:"):
            parts = mem_scope.split(":")
            if parts[1] == self.context.get("project"):
                if len(parts) >= 4 and parts[2] == "task":
                    if parts[3] == self.context.get("task"):
                        reasons.append(f"task:{parts[3]}")
                    else:
                        reasons.append("project")
                else:
                    reasons.append("project")

        # Recency
        try:
            mem_time = datetime.fromisoformat(memory["timestamp"])
            age_days = (datetime.now() - mem_time).days
            if age_days < 7:
                reasons.append("recent")
            elif age_days > 90:
                reasons.append("old")
        except:
            pass

        # Confidence
        if memory.get("confidence", 1.0) >= 0.8:
            reasons.append("high-conf")

        return ", ".join(reasons) if reasons else "default"
```

---

## Budget-Aware Retrieval

```python
class BudgetAwareRetrieval:
    """
    Enforce token budget during retrieval.
    """

    def __init__(self, retrieval: MemoryRetrieval):
        self.retrieval = retrieval

    def query_within_budget(
        self,
        context: Dict[str, Any],
        budget: int
    ) -> RetrievalResult:
        """
        Query memories, stop when budget reached.
        """
        # Initial query (get all)
        query = MemoryQuery(max_results=1000)
        result = self.retrieval.query(context, query)

        # Take memories until budget exhausted
        selected = []
        tokens_used = 0

        for mem in result.memories:
            # Estimate tokens for this memory
            mem_tokens = len(mem.content.split()) * 1.3 + 10

            if tokens_used + mem_tokens > budget:
                break

            selected.append(mem)
            tokens_used += int(mem_tokens)

        return RetrievalResult(
            memories=selected,
            total_found=result.total_found,
            total_returned=len(selected),
            token_estimate=tokens_used
        )
```

---

## Integration with Phase 7

```python
def inject_memories(context: Dict[str, Any]) -> str:
    """
    Phase 7 integration: Load memories for injection.
    """
    # Retrieval (Phase 6)
    retrieval = MemoryRetrieval(Path.home() / ".cerberus")
    budget_retrieval = BudgetAwareRetrieval(retrieval)

    # Budget allocation
    total_budget = 1500
    universal_budget = 700
    language_budget = 500
    project_budget = 300

    # Query universal
    universal_result = budget_retrieval.query_within_budget(
        {**context, "scope": "universal"},
        universal_budget
    )

    # Query language
    language_result = budget_retrieval.query_within_budget(
        {**context, "scope": f"language:{context.get('language')}"},
        language_budget
    )

    # Query project
    project_result = budget_retrieval.query_within_budget(
        {**context, "scope": f"project:{context.get('project')}"},
        project_budget
    )

    # Combine
    all_memories = (
        universal_result.memories +
        language_result.memories +
        project_result.memories
    )

    # Format for injection (Phase 7 handles formatting)
    return all_memories
```

---

## Exit Criteria

```
✓ MemoryRetrieval class implemented
✓ Scope-based loading working (universal, language, project, task)
✓ RelevanceScorer implemented with 4 factors
✓ Budget-aware retrieval working
✓ Integration with Phase 7 complete
✓ Token estimation accurate
✓ Tests: 10 retrieval scenarios
```

---

## Test Scenarios

```python
# Scenario 1: Universal only
context: {}
→ expect: all universal memories loaded, sorted by relevance

# Scenario 2: Language-specific
context: {"language": "go"}
→ expect: universal + go.json memories

# Scenario 3: Project-specific
context: {"project": "hydra", "language": "go"}
→ expect: universal + go.json + hydra/decisions.json

# Scenario 4: Task-specific
context: {"project": "hydra", "task": "coding", "language": "go"}
→ expect: universal + go.json + hydra/decisions.json + hydra/tasks/coding.json

# Scenario 5: Budget enforcement
budget: 500 tokens, memories: 10 (200 tokens each)
→ expect: first 2-3 memories returned, budget not exceeded

# Scenario 6: Relevance sorting
memories: 5 different scopes
→ expect: sorted by relevance (universal < language < project < task)

# Scenario 7: Recency scoring
memories: same scope, different timestamps (1 day, 30 days, 180 days)
→ expect: sorted by recency (1d > 30d > 180d)

# Scenario 8: Confidence filtering
query: min_confidence=0.8
memories: confidence 0.5, 0.7, 0.9
→ expect: only 0.9 returned

# Scenario 9: Empty storage
context: {"project": "nonexistent"}
→ expect: empty result, no errors

# Scenario 10: Malformed JSON
storage file: corrupted JSON
→ expect: skip file, continue with others
```

---

## Dependencies

```bash
pip install tiktoken  # Token estimation
```

---

## Performance

- Single query: < 100ms (10 files, 50 memories)
- Budget enforcement: < 150ms (sorting + filtering)
- Memory per query: < 5MB (in-memory filtering)

---

## Token Budget Allocation

**Phase 7 uses Phase 6 with this budget:**
```
Universal: 700 tokens  (preferences, corrections)
Language:  500 tokens  (language-specific rules)
Project:   300 tokens  (project decisions)
─────────────────────
Total:     1500 tokens (memory injection budget)
```

**Retrieval prioritizes:**
1. Task-specific (1.0 relevance)
2. Project-specific (0.9 relevance)
3. Language-specific (0.8-1.0 relevance)
4. Universal (0.8 relevance)
5. Recent > old (1.0 → 0.2 decay)
6. High confidence > low (0.2 weight)
