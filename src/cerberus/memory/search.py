"""
Phase 13A: Indexed Search & FTS5 Search Engine

FTS5-powered memory search with relevance scoring, snippet extraction, and access tracking.

Zero token cost (pure search, no LLM).
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass


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
    memory_id: str
    content: str
    category: str
    scope: str
    confidence: float
    created_at: str
    last_accessed: Optional[str]
    access_count: int
    metadata: Dict[str, Any]
    relevance_score: float  # 0.0-1.0 from FTS5 rank
    match_context: str  # Snippet showing match
    # Phase 14: Anchor fields
    anchor_file: Optional[str] = None
    anchor_symbol: Optional[str] = None
    anchor_score: Optional[float] = None
    anchor_metadata: Optional[str] = None  # JSON string
    # Phase 15: Mode fields
    valid_modes: Optional[str] = None  # JSON string of list
    mode_priority: Optional[str] = None  # JSON string of dict

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "category": self.category,
            "scope": self.scope,
            "confidence": self.confidence,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "metadata": self.metadata,
            "relevance_score": self.relevance_score,
            "match_context": self.match_context,
            "anchor_file": self.anchor_file,
            "anchor_symbol": self.anchor_symbol,
            "anchor_score": self.anchor_score,
            "anchor_metadata": self.anchor_metadata,
            "valid_modes": self.valid_modes,
            "mode_priority": self.mode_priority
        }


class MemorySearchEngine:
    """
    FTS5-powered memory search.

    Features:
    - Full-text search with FTS5 BM25 ranking
    - Scope/category/confidence filtering
    - Relevance scoring from FTS5 rank
    - Snippet extraction showing match context
    - Access tracking (last_accessed, access_count)
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Search memories using FTS5.

        Args:
            query: SearchQuery with filters

        Returns:
            List of SearchResult objects sorted by relevance
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        # Build query
        sql, params = self._build_query(query)

        # Execute
        try:
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
        except sqlite3.OperationalError as e:
            # Handle FTS5 errors gracefully (e.g., invalid search syntax)
            conn.close()
            return []

        # Convert to results
        results = []
        for row in rows:
            # Get relevance score from FTS5 rank
            relevance = self._calculate_relevance(row, query.text)

            # Get match context (snippet)
            match_context = self._extract_snippet(row["content"], query.text)

            results.append(SearchResult(
                memory_id=row["id"],
                content=row["content"],
                category=row["category"],
                scope=row["scope"],
                confidence=row["confidence"],
                created_at=row["created_at"],
                last_accessed=row["last_accessed"],
                access_count=row["access_count"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                relevance_score=relevance,
                match_context=match_context,
                # Phase 14: Anchor fields (sqlite3.Row uses bracket access)
                anchor_file=row["anchor_file"] if "anchor_file" in row.keys() else None,
                anchor_symbol=row["anchor_symbol"] if "anchor_symbol" in row.keys() else None,
                anchor_score=row["anchor_score"] if "anchor_score" in row.keys() else None,
                anchor_metadata=row["anchor_metadata"] if "anchor_metadata" in row.keys() else None,
                # Phase 15: Mode fields
                valid_modes=row["valid_modes"] if "valid_modes" in row.keys() else None,
                mode_priority=row["mode_priority"] if "mode_priority" in row.keys() else None
            ))

        conn.close()

        # Update access tracking
        self._update_access([r.memory_id for r in results])

        return results

    def _build_query(
        self,
        query: SearchQuery
    ) -> Tuple[str, List]:
        """
        Build SQL query from search parameters.

        Uses split-table architecture:
        - memory_store: Standard table with filters
        - memory_fts: FTS5 virtual table for full-text search
        """
        where_clauses = []
        params = []

        # Full-text search: Join FTS5 table with metadata table
        if query.text:
            sql_parts = ["""
                SELECT
                    s.id, f.content, s.category, s.scope, s.confidence,
                    s.created_at, s.last_accessed, s.access_count, s.metadata,
                    s.anchor_file, s.anchor_symbol, s.anchor_score, s.anchor_metadata,
                    f.rank
                FROM memory_store s
                JOIN memory_fts f ON s.id = f.id
                WHERE f.memory_fts MATCH ?
            """]
            params.append(query.text)
        else:
            # No full-text search: Join tables but no MATCH clause
            sql_parts = ["""
                SELECT
                    s.id, f.content, s.category, s.scope, s.confidence,
                    s.created_at, s.last_accessed, s.access_count, s.metadata,
                    s.anchor_file, s.anchor_symbol, s.anchor_score, s.anchor_metadata,
                    NULL as rank
                FROM memory_store s
                JOIN memory_fts f ON s.id = f.id
                WHERE 1=1
            """]

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

        # Add WHERE clauses
        if where_clauses:
            sql_parts.append("AND " + " AND ".join(where_clauses))

        # Order by
        if query.order_by == "relevance" and query.text:
            sql_parts.append("ORDER BY rank")  # FTS5 rank (lower = better)
        elif query.order_by == "recency":
            sql_parts.append("ORDER BY created_at DESC")
        elif query.order_by == "confidence":
            sql_parts.append("ORDER BY confidence DESC")
        else:
            # Default: if text search, by relevance; otherwise by recency
            if query.text:
                sql_parts.append("ORDER BY rank")
            else:
                sql_parts.append("ORDER BY created_at DESC")

        # Limit
        sql_parts.append(f"LIMIT {query.limit}")

        return " ".join(sql_parts), params

    def _calculate_relevance(self, row: sqlite3.Row, search_text: Optional[str]) -> float:
        """
        Calculate relevance score from FTS5 rank.
        FTS5 rank is negative (closer to 0 = more relevant).

        Args:
            row: Database row with rank column
            search_text: Search text (if None, no FTS5 rank available)

        Returns:
            Relevance score 0.0-1.0
        """
        if not search_text or "rank" not in row.keys() or row["rank"] is None:
            return 0.5  # Default relevance when no text search

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

        Args:
            content: Full content text
            search_text: Search text to find

        Returns:
            Snippet with context around match
        """
        if not search_text:
            # No search text: return first 100 chars
            return content[:100] + ("..." if len(content) > 100 else "")

        # Find first occurrence (case-insensitive)
        lower_content = content.lower()
        search_words = search_text.lower().split()

        # Try to find first search word
        for word in search_words:
            idx = lower_content.find(word)
            if idx != -1:
                # Extract context around match
                start = max(0, idx - 30)
                end = min(len(content), idx + len(word) + 50)

                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."

                return snippet

        # No match found: return first 100 chars
        return content[:100] + ("..." if len(content) > 100 else "")

    def _update_access(self, memory_ids: List[str]):
        """
        Update last_accessed and access_count for retrieved memories.

        Args:
            memory_ids: List of memory IDs to update
        """
        if not memory_ids:
            return

        conn = sqlite3.connect(str(self.db_path))

        for memory_id in memory_ids:
            conn.execute("""
                UPDATE memory_store
                SET last_accessed = ?,
                    access_count = access_count + 1
                WHERE id = ?
            """, (datetime.now().isoformat(), memory_id))

        conn.commit()
        conn.close()


class BudgetAwareSearch:
    """
    Enforce token budget during search.

    Prevents token bloat by limiting results to fit within budget.
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

        Args:
            query: SearchQuery parameters
            budget: Maximum tokens to return

        Returns:
            List of SearchResult objects within budget
        """
        # Get all results
        results = self.search_engine.search(query)

        # Take results until budget exhausted
        selected = []
        tokens_used = 0

        for result in results:
            # Estimate tokens for this memory (rough: words * 1.3 + overhead)
            mem_tokens = len(result.content.split()) * 1.3 + 10

            if tokens_used + mem_tokens > budget:
                break

            selected.append(result)
            tokens_used += int(mem_tokens)

        return selected
