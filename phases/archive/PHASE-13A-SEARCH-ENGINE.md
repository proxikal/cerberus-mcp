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
FTS5 search queries, **replace** Phase 5-6 code with SQLite versions, add MCP `memory_search()` tool.

**What this phase does:**
1. **Replaces Phase 5** (storage.py): JSON writes → SQLite writes (Version 2 code in PHASE-13B)
2. **Replaces Phase 6** (retrieval.py): JSON reads → SQLite FTS5 queries (Version 2 code in PHASE-13B)
3. Adds FTS5 search engine (search.py): New functionality
4. Adds new MCP tool: `memory_search()`
5. Measures actual token savings (target: 80%+)

**IMPORTANT: This phase REWRITES Phase 5 & 6, not updates them.**
- Phase 5/6 Alpha code (JSON) is replaced entirely
- New Beta code (SQLite) is in PHASE-13B-INTEGRATION.md
- JSON becomes read-only backup (fallback if SQLite fails)

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

