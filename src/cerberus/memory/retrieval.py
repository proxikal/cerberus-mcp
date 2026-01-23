"""
Phase 6: Retrieval Operations (Version 1 - JSON)

Query and filter memories from JSON for context-aware injection.
This is Phase Alpha implementation - will be replaced with SQLite FTS5 in Phase Beta (Phase 13).

Zero token cost (pure retrieval, tokens counted in Phase 7).
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
import tiktoken


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
            "token_count": self.token_count
        }


class MemoryRetrieval:
    """
    JSON-based memory retrieval with relevance scoring.

    Phase Alpha (MVP): JSON file loading
    Phase Beta: Will be replaced with SQLite FTS5 queries
    """

    # Scope factors for relevance scoring
    SCOPE_FACTORS = {
        "universal": 1.0,    # Always relevant
        "language": 0.8,     # Language-specific slightly lower
        "project": 1.0       # Project-specific highly relevant
    }

    def __init__(self, base_dir: Optional[str] = None, encoding: str = "cl100k_base"):
        """
        Args:
            base_dir: Base directory for storage (default: ~/.cerberus/memory)
            encoding: Tokenizer encoding for token counting (default: cl100k_base for GPT-4)
        """
        if base_dir is None:
            base_dir = Path.home() / ".cerberus" / "memory"
        else:
            base_dir = Path(base_dir)

        self.base_dir = base_dir
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
        # Load memories from relevant files
        memories = self._load_relevant_memories(language, project)

        # Apply filters
        if scope:
            memories = [m for m in memories if m["scope"] == scope]
        if category:
            memories = [m for m in memories if m["category"] == category]

        if not memories:
            return []

        # Convert to RetrievedMemory with relevance scoring
        retrieved = []
        for memory in memories:
            relevance = self._calculate_relevance(
                memory, language, project
            )

            if relevance < min_relevance:
                continue

            token_count = self._count_tokens(memory["content"])

            retrieved.append(RetrievedMemory(
                id=memory["id"],
                category=memory["category"],
                scope=memory["scope"],
                content=memory["content"],
                rationale=memory["rationale"],
                confidence=memory["confidence"],
                timestamp=memory["timestamp"],
                access_count=memory.get("access_count", 0),
                last_accessed=memory.get("last_accessed"),
                relevance_score=relevance,
                token_count=token_count
            ))

        # Sort by relevance (highest first)
        retrieved.sort(key=lambda m: m.relevance_score, reverse=True)

        # Apply token budget
        budgeted = self._apply_budget(retrieved, token_budget)

        return budgeted

    def _load_relevant_memories(
        self,
        language: Optional[str],
        project: Optional[str]
    ) -> List[Dict]:
        """
        Load memories from relevant files based on context.

        Loads in order: universal → language → project

        Args:
            language: Current language context
            project: Current project context

        Returns:
            List of memory dicts
        """
        memories = []

        # Load universal memories
        memories.extend(self._load_file(self.base_dir / "profile.json"))
        memories.extend(self._load_file(self.base_dir / "corrections.json"))

        # Load language-specific memories
        if language:
            lang_file = self.base_dir / "languages" / f"{language}.json"
            memories.extend(self._load_file(lang_file))

        # Load project-specific memories
        if project:
            project_file = self.base_dir / "projects" / project / "decisions.json"
            memories.extend(self._load_file(project_file))

        return memories

    def _load_file(self, file_path: Path) -> List[Dict]:
        """
        Load memories from a JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            List of memory dicts (empty if file doesn't exist)
        """
        if not file_path.exists():
            return []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "memories" in data:
                    return data["memories"]
                else:
                    return []
        except (json.JSONDecodeError, IOError):
            return []

    def _calculate_relevance(
        self,
        memory: Dict,
        language: Optional[str],
        project: Optional[str]
    ) -> float:
        """
        Calculate relevance score for a memory.

        Formula: scope_factor * recency_score * confidence_weight

        Args:
            memory: Memory dict
            language: Current language context
            project: Current project context

        Returns:
            Relevance score (0.0-1.0+)
        """
        # Scope factor
        scope = memory["scope"]
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

        # Recency score (standardized decay curve)
        recency_score = self._calculate_recency(memory["timestamp"])

        # Confidence weight
        confidence = memory.get("confidence", 0.5)

        # Final relevance score
        relevance = scope_factor * recency_score * confidence

        return relevance

    def _calculate_recency(self, timestamp: str) -> float:
        """
        Calculate recency score using standardized decay curve.

        From PHASE-0B-ARCHITECTURE.md:
        - < 7 days: 1.0
        - < 30 days: 0.8
        - < 90 days: 0.6
        - < 180 days: 0.4
        - >= 180 days: 0.2

        Args:
            timestamp: ISO format timestamp string

        Returns:
            Recency score (0.2-1.0)
        """
        try:
            created = datetime.fromisoformat(timestamp)
            now = datetime.now()
            days_ago = (now - created).days

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
        Get retrieval statistics.

        Returns:
            Dict with memory counts and locations
        """
        stats = {
            "total_files": 0,
            "total_memories": 0,
            "by_scope": {
                "universal": 0,
                "language": 0,
                "project": 0
            }
        }

        # Check all possible files
        files_to_check = [
            self.base_dir / "profile.json",
            self.base_dir / "corrections.json"
        ]

        # Add language files
        languages_dir = self.base_dir / "languages"
        if languages_dir.exists():
            files_to_check.extend(languages_dir.glob("*.json"))

        # Add project files
        projects_dir = self.base_dir / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir():
                    decisions_file = project_dir / "decisions.json"
                    if decisions_file.exists():
                        files_to_check.append(decisions_file)

        # Count memories
        for file_path in files_to_check:
            if file_path.exists():
                memories = self._load_file(file_path)
                if memories:
                    stats["total_files"] += 1
                    stats["total_memories"] += len(memories)

                    # Categorize by scope
                    for memory in memories:
                        scope = memory.get("scope", "universal")
                        if scope == "universal":
                            stats["by_scope"]["universal"] += 1
                        elif scope.startswith("language:"):
                            stats["by_scope"]["language"] += 1
                        elif scope.startswith("project:"):
                            stats["by_scope"]["project"] += 1

        return stats


def retrieve_memories(
    language: Optional[str] = None,
    project: Optional[str] = None,
    category: Optional[str] = None,
    token_budget: int = 1200,
    min_relevance: float = 0.0,
    base_dir: Optional[str] = None
) -> List[RetrievedMemory]:
    """
    Convenience function to retrieve memories.

    Args:
        language: Current language context (e.g., "python", "go")
        project: Current project context (e.g., "cerberus")
        category: Optional category filter (preference, rule, correction)
        token_budget: Maximum tokens to retrieve (default: 1200)
        min_relevance: Minimum relevance score (default: 0.0)
        base_dir: Optional base directory (default: ~/.cerberus/memory)

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


def create_test_scenarios():
    """
    Create test scenarios for validation.

    Returns:
        List of test scenario dictionaries
    """
    return [
        {
            "name": "Universal only",
            "language": None,
            "project": None,
            "expected_scopes": ["universal"]
        },
        {
            "name": "Language-specific",
            "language": "python",
            "project": None,
            "expected_scopes": ["universal", "language:python"]
        },
        {
            "name": "Project-specific",
            "language": None,
            "project": "cerberus",
            "expected_scopes": ["universal", "project:cerberus"]
        },
        {
            "name": "Full context",
            "language": "go",
            "project": "myapp",
            "expected_scopes": ["universal", "language:go", "project:myapp"]
        },
        {
            "name": "Token budget enforcement",
            "token_budget": 100,
            "expected_behavior": "stops when budget exhausted"
        },
        {
            "name": "Relevance scoring",
            "recency_test": True,
            "expected_order": "recent > old, high confidence > low"
        }
    ]
