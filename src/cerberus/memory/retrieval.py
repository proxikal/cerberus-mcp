"""
Phase 6: Retrieval Operations (Version 2 - SQLite FTS5)

Query and filter memories from SQLite using FTS5 for context-aware injection.
This is Phase Beta implementation - replaces JSON loading from Phase Alpha.

Zero token cost (pure retrieval, tokens counted in Phase 7).
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import tiktoken

from .search import MemorySearchEngine, SearchQuery, SearchResult


@dataclass
class RetrievedMemory:
    """Represents a retrieved memory with relevance scoring."""
    id: str
    category: str
    scope: str
    content: str
    rationale: str
    confidence: float
    timestamp: str
    access_count: int
    last_accessed: Optional[str]
    relevance_score: float = 0.0
    token_count: int = 0
    # Phase 14: Anchor fields
    anchor_file: Optional[str] = None
    anchor_symbol: Optional[str] = None
    anchor_score: Optional[float] = None
    anchor_metadata: Optional[Dict] = None
    # Phase 15: Mode fields
    valid_modes: Optional[str] = None  # JSON string of list
    mode_priority: Optional[str] = None  # JSON string of dict

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "category": self.category,
            "scope": self.scope,
            "content": self.content,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "relevance_score": self.relevance_score,
            "token_count": self.token_count,
            "anchor_file": self.anchor_file,
            "anchor_symbol": self.anchor_symbol,
            "anchor_score": self.anchor_score,
            "anchor_metadata": self.anchor_metadata,
            "valid_modes": self.valid_modes,
            "mode_priority": self.mode_priority
        }


class MemoryRetrieval:
    """
    SQLite FTS5-based memory retrieval with relevance scoring.

    Phase Alpha (MVP): JSON file loading (deprecated)
    Phase Beta (Current): SQLite FTS5 queries

    Uses Phase 12 schema and Phase 13 search engine.
    """

    # Scope factors for relevance scoring
    SCOPE_FACTORS = {
        "universal": 1.0,    # Always relevant
        "language": 0.8,     # Language-specific slightly lower
        "project": 1.0       # Project-specific highly relevant
    }

    def __init__(self, base_dir: Optional[Path] = None, encoding: str = "cl100k_base"):
        """
        Args:
            base_dir: Base directory for storage (default: ~/.cerberus)
            encoding: Tokenizer encoding for token counting (default: cl100k_base for GPT-4)
        """
        if base_dir is None:
            base_dir = Path.home() / ".cerberus"
        elif isinstance(base_dir, str):
            base_dir = Path(base_dir)

        self.base_dir = base_dir
        self.db_path = base_dir / "memory.db"
        self.search_engine = MemorySearchEngine(self.db_path)
        self.tokenizer = tiktoken.get_encoding(encoding)

    def retrieve(
        self,
        scope: Optional[str] = None,
        language: Optional[str] = None,
        project: Optional[str] = None,
        category: Optional[str] = None,
        token_budget: int = 1200,
        min_relevance: float = 0.0
    ) -> List[RetrievedMemory]:
        """
        Retrieve memories with relevance scoring and budget awareness.

        Args:
            scope: Optional scope filter (universal, language:X, project:X)
            language: Current language context (e.g., "python", "go")
            project: Current project context (e.g., "cerberus")
            category: Optional category filter (preference, rule, correction)
            token_budget: Maximum tokens to retrieve (default: 1200)
            min_relevance: Minimum relevance score (default: 0.0)

        Returns:
            List of RetrievedMemory objects sorted by relevance (high to low)
        """
        if not self.db_path.exists():
            return []

        # Build scope pattern for filtering
        scope_pattern = self._build_scope_pattern(language, project, scope)

        # Query database using search engine
        search_query = SearchQuery(
            text=None,  # No full-text search, just scope filtering
            scope=scope_pattern,
            category=category,
            min_confidence=0.0,  # Apply min_relevance later after scoring
            limit=1000,  # Large limit, will be filtered by budget
            order_by="recency"  # Start with recent memories
        )

        results = self.search_engine.search(search_query)

        # Convert to RetrievedMemory with relevance scoring
        retrieved = []
        for result in results:
            # Calculate relevance score (recency already from DB)
            relevance = self._calculate_relevance(
                result, language, project
            )

            if relevance < min_relevance:
                continue

            # Count tokens
            token_count = self._count_tokens(result.content)

            # Extract rationale from metadata
            rationale = result.metadata.get("rationale", "")

            # Parse anchor metadata if present
            anchor_metadata = None
            if result.anchor_metadata:
                try:
                    anchor_metadata = json.loads(result.anchor_metadata)
                except (json.JSONDecodeError, TypeError):
                    anchor_metadata = None

            retrieved.append(RetrievedMemory(
                id=result.memory_id,
                category=result.category,
                scope=result.scope,
                content=result.content,
                rationale=rationale,
                confidence=result.confidence,
                timestamp=result.created_at,
                access_count=result.access_count,
                last_accessed=result.last_accessed,
                relevance_score=relevance,
                token_count=token_count,
                anchor_file=result.anchor_file,
                anchor_symbol=result.anchor_symbol,
                anchor_score=result.anchor_score,
                anchor_metadata=anchor_metadata,
                valid_modes=getattr(result, 'valid_modes', None),
                mode_priority=getattr(result, 'mode_priority', None)
            ))

        # Sort by relevance (highest first)
        retrieved.sort(key=lambda m: m.relevance_score, reverse=True)

        # Apply token budget
        budgeted = self._apply_budget(retrieved, token_budget)

        return budgeted

    def _build_scope_pattern(
        self,
        language: Optional[str],
        project: Optional[str],
        explicit_scope: Optional[str]
    ) -> Optional[str]:
        """
        Build scope pattern for SQL filtering.

        If explicit_scope provided, use it. Otherwise build from context.

        Args:
            language: Current language context
            project: Current project context
            explicit_scope: Explicit scope filter

        Returns:
            Scope pattern string or None (matches all)
        """
        if explicit_scope:
            return explicit_scope

        # No explicit scope: match multiple scopes using SQL OR logic
        # We'll handle this in the search method by running multiple queries
        return None

    def _calculate_relevance(
        self,
        result: SearchResult,
        language: Optional[str],
        project: Optional[str]
    ) -> float:
        """
        Calculate relevance score for a memory.

        Formula: scope_factor * recency_score * confidence_weight

        Args:
            result: SearchResult from database
            language: Current language context
            project: Current project context

        Returns:
            Relevance score (0.0-1.0+)
        """
        # Scope factor
        scope = result.scope
        if scope == "universal":
            scope_factor = self.SCOPE_FACTORS["universal"]
        elif scope.startswith("language:"):
            memory_lang = scope.split(":", 1)[1]
            # Higher relevance if matches current language
            if language and memory_lang == language:
                scope_factor = self.SCOPE_FACTORS["language"]
            else:
                scope_factor = 0.0  # Language mismatch - not relevant
        elif scope.startswith("project:"):
            memory_project = scope.split(":", 1)[1]
            # Higher relevance if matches current project
            if project and memory_project == project:
                scope_factor = self.SCOPE_FACTORS["project"]
            else:
                scope_factor = 0.0  # Project mismatch - not relevant
        else:
            scope_factor = 0.5  # Unknown scope

        if scope_factor == 0.0:
            return 0.0

        # Recency score with custom decay threshold
        decay_days = getattr(result, 'relevance_decay_days', 90)
        recency_score = self._calculate_recency(result.created_at, decay_days)

        # Confidence weight
        confidence = result.confidence

        # Final relevance score
        relevance = scope_factor * recency_score * confidence

        return relevance

    def _calculate_recency(self, timestamp: str, decay_days: int = 90) -> float:
        """
        Calculate recency score with configurable decay threshold.

        Hybrid format enhancement: Each memory has custom relevance_decay_days.
        - Architectural decisions: decay_days=180 (stay relevant longer)
        - Bug fixes: decay_days=30 (become stale quickly)
        - Universal preferences: decay_days=365 (nearly permanent)

        Default decay curve (decay_days=90):
        - < 7 days: 1.0 (very recent)
        - < 30 days: 0.8 (recent)
        - < decay_days: 0.6 (moderate)
        - < 2*decay_days: 0.4 (old)
        - >= 2*decay_days: 0.2 (stale)

        Args:
            timestamp: ISO format timestamp string
            decay_days: Custom decay threshold (default: 90)

        Returns:
            Recency score (0.2-1.0)
        """
        try:
            created = datetime.fromisoformat(timestamp)
            now = datetime.now()
            days_ago = (now - created).days

            # Standardized thresholds relative to decay_days
            if days_ago < 7:
                return 1.0  # Always 1.0 for very recent (< 1 week)
            elif days_ago < 30:
                return 0.8  # Always 0.8 for recent (< 1 month)
            elif days_ago < decay_days:
                return 0.6  # Moderate (within decay threshold)
            elif days_ago < (decay_days * 2):
                return 0.4  # Old (beyond decay threshold)
            else:
                return 0.2  # Stale (way beyond threshold)
        except (ValueError, TypeError):
            # Invalid timestamp - return lowest score
            return 0.2

    def _count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count

        Returns:
            Token count
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception:
            # Fallback: rough estimate (1 token ≈ 4 chars)
            return len(text) // 4

    def _apply_budget(
        self,
        memories: List[RetrievedMemory],
        token_budget: int
    ) -> List[RetrievedMemory]:
        """
        Apply token budget to retrieved memories.

        Memories are already sorted by relevance (high to low).
        Takes as many high-relevance memories as fit in budget.

        Args:
            memories: List of RetrievedMemory sorted by relevance
            token_budget: Maximum tokens to retrieve

        Returns:
            List of memories within budget
        """
        if not memories:
            return []

        budgeted = []
        total_tokens = 0

        for memory in memories:
            if total_tokens + memory.token_count <= token_budget:
                budgeted.append(memory)
                total_tokens += memory.token_count
            else:
                # Budget exhausted
                break

        return budgeted

    def get_stats(self) -> Dict:
        """
        Get retrieval statistics from SQLite.

        Returns:
            Dict with memory counts and scopes
        """
        if not self.db_path.exists():
            return {
                "total_memories": 0,
                "by_scope": {
                    "universal": 0,
                    "language": 0,
                    "project": 0
                }
            }

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row

        try:
            # Total memories
            cursor = conn.execute("SELECT COUNT(*) as count FROM memory_store")
            total = cursor.fetchone()["count"]

            # By scope type
            cursor = conn.execute("""
                SELECT
                    CASE
                        WHEN scope = 'universal' THEN 'universal'
                        WHEN scope LIKE 'language:%' THEN 'language'
                        WHEN scope LIKE 'project:%' THEN 'project'
                        ELSE 'other'
                    END as scope_type,
                    COUNT(*) as count
                FROM memory_store
                GROUP BY scope_type
            """)

            by_scope = {
                "universal": 0,
                "language": 0,
                "project": 0
            }
            for row in cursor:
                if row["scope_type"] in by_scope:
                    by_scope[row["scope_type"]] = row["count"]

            return {
                "total_memories": total,
                "by_scope": by_scope
            }

        finally:
            conn.close()


def retrieve_memories(
    language: Optional[str] = None,
    project: Optional[str] = None,
    category: Optional[str] = None,
    token_budget: int = 1200,
    min_relevance: float = 0.0,
    base_dir: Optional[Path] = None
) -> List[RetrievedMemory]:
    """
    Convenience function to retrieve memories.

    Args:
        language: Current language context (e.g., "python", "go")
        project: Current project context (e.g., "cerberus")
        category: Optional category filter (preference, rule, correction)
        token_budget: Maximum tokens to retrieve (default: 1200)
        min_relevance: Minimum relevance score (default: 0.0)
        base_dir: Optional base directory (default: ~/.cerberus)

    Returns:
        List of RetrievedMemory objects sorted by relevance
    """
    retrieval = MemoryRetrieval(base_dir=base_dir)
    return retrieval.retrieve(
        language=language,
        project=project,
        category=category,
        token_budget=token_budget,
        min_relevance=min_relevance
    )
