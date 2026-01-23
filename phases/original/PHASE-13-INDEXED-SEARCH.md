# PHASE 13: INDEXED SEARCH & INTEGRATION

**Rollout Phase:** Beta (Weeks 3-4)
**Status:** Deferred until Phase 12 complete

## Prerequisites

⚠️ **DO NOT implement until Phase 12 complete**

**Required:**
- ✅ Phase 12 implemented (SQLite schema + migration)
- ✅ Migration validated (100% data integrity)
- ✅ Database stable (no corruption, backups work)

## Objective
FTS5 search queries, update Phase 5-6 to use SQLite, add MCP `memory_search()` tool.

**What this phase does:**
1. Updates Phase 5 (storage.py) to write to SQLite
2. Updates Phase 6 (retrieval.py) to query SQLite FTS5
3. Adds FTS5 search engine (search.py)
4. Adds new MCP tool: `memory_search()`
5. Measures actual token savings (target: 80%+)

---

## Implementation Location

**File:** `src/cerberus/memory/search.py`

**Updates:** Phase 5 `storage.py`, Phase 6 `retrieval.py`

---

## Data Structures

```python
@dataclass
class SearchQuery:
    """Memory search query parameters."""
    text: Optional[str] = None  # Full-text search
    scope: Optional[str] = None  # Filter by scope
    category: Optional[str] = None  # Filter by category
    min_confidence: float = 0.0
    limit: int = 20
    order_by: str = "relevance"  # relevance, recency, confidence

@dataclass
class SearchResult:
    """Single search result with relevance."""
    memory: IndexedMemory
    relevance_score: float  # 0.0-1.0 from FTS5 rank
    match_context: str  # Snippet showing match
```

---

## FTS5 Search Engine

```python
class MemorySearchEngine:
    """
    FTS5-powered memory search.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search memories using FTS5.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Build query
        sql, params = self._build_query(query)

        # Execute
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()

        # Convert to results
        results = []
        for row in rows:
            memory = IndexedMemory(
                id=row["id"],
                content=row["content"],
                category=row["category"],
                scope=row["scope"],
                confidence=row["confidence"],
                created_at=row["created_at"],
                last_accessed=row["last_accessed"],
                access_count=row["access_count"],
                metadata=json.loads(row["metadata"])
            )

            # Get relevance score from FTS5 rank
            relevance = self._calculate_relevance(row)

            # Get match context (snippet)
            match_context = self._extract_snippet(row["content"], query.text)

            results.append(SearchResult(
                memory=memory,
                relevance_score=relevance,
                match_context=match_context
            ))

        conn.close()

        # Update access tracking
        self._update_access([r.memory.id for r in results])

        return results

    def _build_query(
        self,
        query: SearchQuery
    ) -> Tuple[str, List]:
        """
        Build SQL query from search parameters.
        """
        sql_parts = ["SELECT *, rank FROM memories"]
        where_clauses = []
        params = []

        # Full-text search
        if query.text:
            where_clauses.append("memories MATCH ?")
            params.append(query.text)

        # Scope filter
        if query.scope:
            if query.scope.endswith("*"):
                # Prefix match: "project:hydra*" matches "project:hydra:task:X"
                where_clauses.append("scope LIKE ?")
                params.append(query.scope.replace("*", "%"))
            else:
                where_clauses.append("scope = ?")
                params.append(query.scope)

        # Category filter
        if query.category:
            where_clauses.append("category = ?")
            params.append(query.category)

        # Confidence filter
        if query.min_confidence > 0:
            where_clauses.append("confidence >= ?")
            params.append(query.min_confidence)

        # Combine WHERE clauses
        if where_clauses:
            sql_parts.append("WHERE " + " AND ".join(where_clauses))

        # Order by
        if query.order_by == "relevance" and query.text:
            sql_parts.append("ORDER BY rank")  # FTS5 rank (lower = better)
        elif query.order_by == "recency":
            sql_parts.append("ORDER BY created_at DESC")
        elif query.order_by == "confidence":
            sql_parts.append("ORDER BY confidence DESC")
        else:
            sql_parts.append("ORDER BY rank")  # Default

        # Limit
        sql_parts.append(f"LIMIT {query.limit}")

        return " ".join(sql_parts), params

    def _calculate_relevance(self, row: sqlite3.Row) -> float:
        """
        Calculate relevance score from FTS5 rank.
        FTS5 rank is negative (closer to 0 = more relevant).
        """
        if "rank" not in row.keys():
            return 0.5

        # Convert FTS5 rank to 0.0-1.0 score
        # Typical rank range: -30 to -1
        rank = row["rank"]
        if rank >= -1:
            return 1.0
        elif rank <= -30:
            return 0.1
        else:
            # Linear mapping: -1 to -30 → 1.0 to 0.1
            return 1.0 - ((abs(rank) - 1) / 29) * 0.9

    def _extract_snippet(
        self,
        content: str,
        search_text: Optional[str]
    ) -> str:
        """
        Extract snippet showing search match.
        """
        if not search_text:
            return content[:100] + "..."

        # Find first occurrence
        lower_content = content.lower()
        lower_search = search_text.lower().split()[0]  # First word

        idx = lower_content.find(lower_search)
        if idx == -1:
            return content[:100] + "..."

        # Extract context around match
        start = max(0, idx - 30)
        end = min(len(content), idx + len(search_text) + 50)

        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def _update_access(self, memory_ids: List[str]):
        """
        Update last_accessed and access_count for retrieved memories.
        """
        if not memory_ids:
            return

        conn = sqlite3.connect(self.db_path)

        for memory_id in memory_ids:
            conn.execute("""
                UPDATE memories
                SET last_accessed = ?,
                    access_count = access_count + 1
                WHERE id = ?
            """, (datetime.now().isoformat(), memory_id))

        conn.commit()
        conn.close()
```

---

## Phase 5 Integration (Storage)

```python
# Update storage.py to write to SQLite

class MemoryStorage:
    """
    Routes approved proposals to SQLite (Phase 12 index).
    """

    def __init__(self, base_path: Path):
        self.db_path = base_path / "memory.db"
        self.index_manager = MemoryIndexManager(base_path)

    def store(self, proposal: Union[MemoryProposal, AgentProposal]):
        """
        Store approved proposal to SQLite.
        """
        conn = sqlite3.connect(self.db_path)

        memory_id = str(uuid.uuid4())

        conn.execute("""
            INSERT INTO memories (
                id, content, category, scope, confidence,
                created_at, last_accessed, access_count, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id,
            proposal.content,
            proposal.category,
            proposal.scope,
            getattr(proposal, "confidence", 1.0),
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            0,
            json.dumps({
                "rationale": getattr(proposal, "rationale", None),
                "evidence": getattr(proposal, "evidence", [])
            })
        ))

        conn.commit()
        conn.close()

    def store_batch(
        self,
        proposals: List[Union[MemoryProposal, AgentProposal]]
    ):
        """
        Store multiple proposals efficiently.
        """
        conn = sqlite3.connect(self.db_path)

        for proposal in proposals:
            memory_id = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO memories (
                    id, content, category, scope, confidence,
                    created_at, last_accessed, access_count, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id,
                proposal.content,
                proposal.category,
                proposal.scope,
                getattr(proposal, "confidence", 1.0),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                0,
                json.dumps({
                    "rationale": getattr(proposal, "rationale", None),
                    "evidence": getattr(proposal, "evidence", [])
                })
            ))

        conn.commit()
        conn.close()
```

---

## Phase 6 Integration (Retrieval)

```python
# Update retrieval.py to query SQLite

class MemoryRetrieval:
    """
    Load memories from SQLite index (Phase 12).
    """

    def __init__(self, base_path: Path):
        self.db_path = base_path / "memory.db"
        self.search_engine = MemorySearchEngine(self.db_path)

    def query(
        self,
        context: Dict[str, Any],
        query: MemoryQuery
    ) -> RetrievalResult:
        """
        Load memories matching query and context.
        """
        # Build search query
        search_query = SearchQuery(
            text=None,  # No full-text search, just scope filtering
            scope=self._build_scope_pattern(context),
            category=query.category,
            min_confidence=query.min_confidence,
            limit=query.max_results,
            order_by="relevance"
        )

        # Search
        results = self.search_engine.search(search_query)

        # Convert to RetrievedMemory objects
        retrieved = []
        for result in results:
            mem = result.memory
            retrieved.append(RetrievedMemory(
                content=mem.content,
                scope=mem.scope,
                category=mem.category,
                confidence=mem.confidence,
                timestamp=mem.created_at,
                relevance_score=result.relevance_score,
                reason=self._explain_relevance(mem, context)
            ))

        # Token estimate
        token_est = self._estimate_tokens(retrieved)

        return RetrievalResult(
            memories=retrieved,
            total_found=len(results),
            total_returned=len(retrieved),
            token_estimate=token_est
        )

    def _build_scope_pattern(self, context: Dict[str, Any]) -> str:
        """
        Build scope pattern from context.
        """
        project = context.get("project")
        language = context.get("language")
        task = context.get("task")

        if task and project:
            return f"project:{project}:task:{task}"
        elif project:
            return f"project:{project}*"  # Match project and all tasks
        elif language:
            return f"language:{language}"
        else:
            return "universal"
```

---

## MCP Tool: memory_search()

```python
def memory_search(
    query: str,
    scope: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    MCP tool: Search memories by text query.

    Args:
        query: Text to search for
        scope: Filter by scope (universal, language:X, project:Y)
        category: Filter by category (preference, rule, correction, decision)
        limit: Max results (default 10)

    Returns:
        Search results with relevance scores
    """
    search_engine = MemorySearchEngine(Path.home() / ".cerberus" / "memory.db")

    search_query = SearchQuery(
        text=query,
        scope=scope,
        category=category,
        limit=limit,
        order_by="relevance"
    )

    results = search_engine.search(search_query)

    return {
        "status": "ok",
        "query": query,
        "total_results": len(results),
        "results": [
            {
                "content": r.memory.content,
                "scope": r.memory.scope,
                "category": r.memory.category,
                "relevance": round(r.relevance_score, 2),
                "snippet": r.match_context,
                "confidence": r.memory.confidence
            }
            for r in results
        ]
    }
```

---

## Budget-Aware Search

```python
class BudgetAwareSearch:
    """
    Enforce token budget during search.
    """

    def __init__(self, search_engine: MemorySearchEngine):
        self.search_engine = search_engine

    def search_within_budget(
        self,
        query: SearchQuery,
        budget: int
    ) -> List[SearchResult]:
        """
        Search memories, stop when budget reached.
        """
        # Get all results
        results = self.search_engine.search(query)

        # Take results until budget exhausted
        selected = []
        tokens_used = 0

        for result in results:
            # Estimate tokens for this memory
            mem_tokens = len(result.memory.content.split()) * 1.3 + 10

            if tokens_used + mem_tokens > budget:
                break

            selected.append(result)
            tokens_used += int(mem_tokens)

        return selected
```

---

## Advanced Search Queries

```python
# Example 1: Find split-related rules in Go
query = SearchQuery(
    text="split files",
    scope="language:go",
    limit=5
)
→ Returns Go-specific memories about file splitting

# Example 2: Find recent project decisions
query = SearchQuery(
    text="",  # All memories
    scope="project:hydra",
    category="decision",
    order_by="recency",
    limit=10
)
→ Returns 10 most recent decisions for hydra project

# Example 3: High-confidence corrections only
query = SearchQuery(
    text="keep output short",
    min_confidence=0.8,
    limit=20
)
→ Returns high-confidence memories about output brevity

# Example 4: Project and task-specific
query = SearchQuery(
    text="race condition",
    scope="project:hydra:task:testing",
    limit=5
)
→ Returns testing-specific memories about race conditions
```

---

## Exit Criteria

```
✓ MemorySearchEngine class implemented
✓ FTS5 queries working
✓ Relevance scoring from rank
✓ Snippet extraction working
✓ Phase 5 updated (write to SQLite)
✓ Phase 6 updated (query SQLite)
✓ MCP tool memory_search() implemented
✓ Budget-aware search working
✓ Access tracking (last_accessed, count)
✓ Tests: 10 search scenarios
```

---

## Test Scenarios

```python
# Scenario 1: Basic text search
query: "split files"
→ expect: memories containing "split" or "files", ranked by relevance

# Scenario 2: Scope filtering
query: text="", scope="language:go"
→ expect: all Go-specific memories, no other languages

# Scenario 3: Category filtering
query: text="", category="correction"
→ expect: only corrections, no preferences or rules

# Scenario 4: Confidence filtering
query: text="", min_confidence=0.8
→ expect: only high-confidence memories

# Scenario 5: Prefix scope match
query: scope="project:hydra*"
→ expect: project:hydra AND project:hydra:task:X memories

# Scenario 6: Relevance ordering
query: "keep output short"
→ expect: exact matches ranked higher than partial matches

# Scenario 7: Recency ordering
query: text="", order_by="recency"
→ expect: newest memories first

# Scenario 8: Budget enforcement
query: limit=100, budget=500 tokens
→ expect: stops at ~25 memories when budget reached

# Scenario 9: Empty results
query: "nonexistent-term-xyz"
→ expect: empty results, no error

# Scenario 10: Access tracking
search memory 3 times
→ expect: access_count=3, last_accessed=recent
```

---

## Dependencies

- Phase 12 (Memory Indexing foundation)
- Phase 5 (Storage, updated)
- Phase 6 (Retrieval, updated)

---

## Performance

- Single search: < 50ms (100 memories)
- Search (1000 memories): < 200ms (FTS5 optimized)
- Batch write: < 100ms (10 proposals)
- Budget-aware search: < 250ms (includes filtering)

---

## Token Efficiency Comparison

**Before (Phase 6 JSON):**
```
Load all memories: 50 × 30 tokens = 1500 tokens
Filter in Python: discard 40, keep 10
Wasted: 1200 tokens (40 irrelevant memories)
```

**After (Phase 13 SQLite FTS5):**
```
FTS5 query returns: 10 matching memories only
Load: 10 × 30 tokens = 300 tokens
Wasted: 0 tokens
```

**Savings: 80% token reduction**

---

## Integration Points

**Phase 5 (Storage):**
- Write to SQLite instead of JSON
- Keep JSON for backward compat (deferred removal)

**Phase 6 (Retrieval):**
- Query SQLite FTS5 instead of loading JSON
- Fallback to JSON if SQLite unavailable

**Phase 7 (Injection):**
- No changes needed (uses Phase 6)
- Benefits from faster retrieval

**MCP Tools:**
- New: `memory_search(query, scope, category, limit)`
- Existing: `memory_learn()`, `memory_context()` unchanged

---

## Migration Path

**Week 1:** Phase 12 (Indexing)
- SQLite schema
- Auto-migration from JSON
- Backward compatibility

**Week 2:** Phase 13 (Search)
- FTS5 search engine
- Update Phase 5-6
- MCP tool

**Week 3:** Testing
- Verify search accuracy
- Performance benchmarks
- Edge cases

**Month 2+:** Deprecate JSON
- Remove JSON write logic
- Keep JSON read for recovery
- Full SQLite migration

---

## Key Design Decisions

**Why update Phase 5-6:**
- Storage/retrieval MUST use same backend
- Inconsistency = data loss risk
- Gradual rollout (SQLite write, JSON fallback)

**Why FTS5 rank for relevance:**
- Built-in relevance scoring
- Proven algorithm (BM25)
- No custom scoring needed

**Why access tracking:**
- Detect stale memories (Phase 11)
- Usage analytics
- Confidence adjustment over time

**Why snippet extraction:**
- Show context of match
- Better UX for search results
- Helps agent understand why matched

---

## Error Handling

```python
@safe_search_operation
def search(self, query: SearchQuery) -> List[SearchResult]:
    """
    Search with automatic fallback.
    """
    try:
        # Try SQLite
        return self._search_sqlite(query)
    except sqlite3.Error:
        # Fallback to JSON (Phase 6 legacy)
        logger.warning("SQLite search failed, falling back to JSON")
        return self._search_json(query)
```

---

## Future Enhancements (Post-MVP)

**Phase 14: Smart Ranking** (optional)
- ML-based relevance scoring
- User feedback loop (approve/reject)
- Personalized ranking

**Phase 15: Memory Clustering** (optional)
- Auto-detect related memories
- Suggest consolidation
- Pattern detection

**Phase 16: Memory Analytics** (optional)
- Usage dashboards
- Trend analysis
- Effectiveness metrics
