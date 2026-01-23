"""
Phase 7: Context-Aware Injection

Hybrid memory injection - auto-inject at session start, on-demand during work.
Uses Phase 6 retrieval to load memories and formats for Claude.

Token budget:
- Session start: 1200 tokens (auto-injection)
- On-demand queries: 500 tokens each (max 2 queries = 1000 tokens)
- Total cap: 2200 tokens per session
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
import tiktoken

from cerberus.memory.retrieval import MemoryRetrieval, RetrievedMemory


@dataclass
class DetectedContext:
    """Detected context from environment and cwd."""
    project: Optional[str] = None
    language: Optional[str] = None
    cwd: Optional[str] = None
    detected_files: List[str] = None

    def __post_init__(self):
        if self.detected_files is None:
            self.detected_files = []


class ContextDetector:
    """
    Auto-detect context from environment.

    Detects:
    - Project name (from cwd or git)
    - Primary language (from file extensions in cwd)
    """

    # Language detection by file extension
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".go": "go",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".js": "javascript",
        ".jsx": "javascript",
        ".rs": "rust",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".rb": "ruby",
        ".php": "php"
    }

    def detect(self, cwd: Optional[str] = None) -> DetectedContext:
        """
        Auto-detect context from current working directory.

        Args:
            cwd: Optional working directory (default: os.getcwd())

        Returns:
            DetectedContext with project and language
        """
        if cwd is None:
            cwd = os.getcwd()

        cwd_path = Path(cwd)

        # Detect project name
        project = self._detect_project(cwd_path)

        # Detect primary language
        language, detected_files = self._detect_language(cwd_path)

        return DetectedContext(
            project=project,
            language=language,
            cwd=str(cwd_path),
            detected_files=detected_files
        )

    def _detect_project(self, cwd: Path) -> Optional[str]:
        """
        Detect project name from directory structure.

        Priority:
        1. Git repository name
        2. Directory name (if not generic)

        Args:
            cwd: Current working directory path

        Returns:
            Project name or None
        """
        # Check for git repository
        git_dir = cwd / ".git"
        if git_dir.exists():
            # Use parent directory name
            return cwd.name

        # Check parent for git (we might be in subdirectory)
        parent_git = cwd.parent / ".git"
        if parent_git.exists():
            return cwd.parent.name

        # Use directory name if not generic
        generic_names = {"src", "lib", "tests", "test", "docs", "examples"}
        if cwd.name.lower() not in generic_names:
            return cwd.name

        return None

    def _detect_language(self, cwd: Path) -> tuple[Optional[str], List[str]]:
        """
        Detect primary language from file extensions.

        Args:
            cwd: Current working directory path

        Returns:
            Tuple of (language, list of detected files)
        """
        # Count file extensions
        extension_counts = {}
        detected_files = []

        # Scan current directory (not recursive to avoid performance issues)
        try:
            for item in cwd.iterdir():
                if item.is_file():
                    ext = item.suffix.lower()
                    if ext in self.LANGUAGE_EXTENSIONS:
                        detected_files.append(item.name)
                        extension_counts[ext] = extension_counts.get(ext, 0) + 1
        except PermissionError:
            pass  # Can't read directory

        if not extension_counts:
            return None, []

        # Return most common extension's language
        most_common_ext = max(extension_counts, key=extension_counts.get)
        language = self.LANGUAGE_EXTENSIONS[most_common_ext]

        return language, detected_files


class ContextInjector:
    """
    Format memories for injection into Claude's context.

    Manages token budgets and formatting.
    """

    # Token budgets
    STARTUP_BUDGET = 1200      # Session start auto-injection
    ONDEMAND_BUDGET = 500      # Per query
    MAX_ONDEMAND_QUERIES = 2   # Maximum on-demand queries
    TOTAL_CAP = 2200          # Total per session (1200 + 1000)

    def __init__(self, base_dir: Optional[str] = None, encoding: str = "cl100k_base"):
        """
        Args:
            base_dir: Base directory for storage (default: ~/.cerberus/memory)
            encoding: Tokenizer encoding (default: cl100k_base for GPT-4)
        """
        self.retrieval = MemoryRetrieval(base_dir=base_dir, encoding=encoding)
        self.tokenizer = tiktoken.get_encoding(encoding)
        self.session_tokens_used = 0
        self.ondemand_queries_count = 0

    def inject_startup(
        self,
        context: Optional[DetectedContext] = None,
        min_relevance: float = 0.5
    ) -> str:
        """
        Auto-inject memories at session start.

        Budget: 1200 tokens
        Priority: High relevance only (min_relevance=0.5)

        Args:
            context: Optional detected context (auto-detects if None)
            min_relevance: Minimum relevance score (default: 0.5)

        Returns:
            Markdown-formatted memories for injection
        """
        if context is None:
            detector = ContextDetector()
            context = detector.detect()

        # Retrieve memories with startup budget
        memories = self.retrieval.retrieve(
            language=context.language,
            project=context.project,
            token_budget=self.STARTUP_BUDGET,
            min_relevance=min_relevance
        )

        if not memories:
            return ""

        # Format for injection
        formatted = self._format_memories(memories, context)

        # Track token usage
        self.session_tokens_used += self._count_tokens(formatted)

        return formatted

    def inject_query(
        self,
        query: str,
        context: Optional[DetectedContext] = None,
        min_relevance: float = 0.3
    ) -> str:
        """
        On-demand memory injection for specific query.

        Budget: 500 tokens per query, max 2 queries (1000 tokens total)

        Args:
            query: Query string (used for filtering, not semantic search)
            context: Optional detected context
            min_relevance: Minimum relevance score (default: 0.3, broader than startup)

        Returns:
            Markdown-formatted memories for query
        """
        # Check query limit
        if self.ondemand_queries_count >= self.MAX_ONDEMAND_QUERIES:
            return "<!-- Memory query limit reached (2 max per session) -->"

        # Check total budget
        remaining_budget = self.TOTAL_CAP - self.session_tokens_used
        if remaining_budget < 100:
            return "<!-- Memory token budget exhausted -->"

        if context is None:
            detector = ContextDetector()
            context = detector.detect()

        # Use remaining budget, capped at ONDEMAND_BUDGET
        query_budget = min(self.ONDEMAND_BUDGET, remaining_budget)

        # Retrieve memories with query budget
        memories = self.retrieval.retrieve(
            language=context.language,
            project=context.project,
            token_budget=query_budget,
            min_relevance=min_relevance
        )

        if not memories:
            return "<!-- No relevant memories found for query -->"

        # Format for injection
        formatted = self._format_memories(memories, context, query=query)

        # Track usage
        tokens_used = self._count_tokens(formatted)
        self.session_tokens_used += tokens_used
        self.ondemand_queries_count += 1

        return formatted

    def _format_memories(
        self,
        memories: List[RetrievedMemory],
        context: DetectedContext,
        query: Optional[str] = None
    ) -> str:
        """
        Format memories as markdown for Claude.

        Args:
            memories: List of retrieved memories
            context: Detected context
            query: Optional query string (for on-demand)

        Returns:
            Markdown-formatted string
        """
        if not memories:
            return ""

        lines = []

        # Header
        if query:
            lines.append(f"## Memory Context (Query: \"{query}\")")
        else:
            lines.append("## Memory Context")

        # Context info
        context_parts = []
        if context.project:
            context_parts.append(f"Project: {context.project}")
        if context.language:
            context_parts.append(f"Language: {context.language}")

        if context_parts:
            lines.append(f"*{' | '.join(context_parts)}*")

        lines.append("")

        # Group by category
        by_category = {
            "preference": [],
            "rule": [],
            "correction": []
        }

        for memory in memories:
            by_category[memory.category].append(memory)

        # Format each category
        category_labels = {
            "preference": "Preferences",
            "rule": "Rules",
            "correction": "Corrections"
        }

        for category in ["preference", "rule", "correction"]:
            items = by_category[category]
            if not items:
                continue

            lines.append(f"### {category_labels[category]}")
            for memory in items:
                # Format: - Content (scope badge if not universal)
                scope_badge = ""
                if memory.scope != "universal":
                    if memory.scope.startswith("language:"):
                        lang = memory.scope.split(":", 1)[1]
                        scope_badge = f" `[{lang}]`"
                    elif memory.scope.startswith("project:"):
                        proj = memory.scope.split(":", 1)[1]
                        scope_badge = f" `[{proj}]`"

                lines.append(f"- {memory.content}{scope_badge}")

            lines.append("")

        # Footer
        lines.append(f"*{len(memories)} memories loaded*")

        return "\n".join(lines)

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
            # Fallback: rough estimate
            return len(text) // 4

    def get_usage_stats(self) -> Dict:
        """
        Get session token usage statistics.

        Returns:
            Dict with usage stats
        """
        return {
            "session_tokens_used": self.session_tokens_used,
            "startup_budget": self.STARTUP_BUDGET,
            "ondemand_queries_count": self.ondemand_queries_count,
            "ondemand_budget_per_query": self.ONDEMAND_BUDGET,
            "max_ondemand_queries": self.MAX_ONDEMAND_QUERIES,
            "total_cap": self.TOTAL_CAP,
            "remaining_budget": self.TOTAL_CAP - self.session_tokens_used
        }


# Module-level convenience functions

def inject_startup_context(
    cwd: Optional[str] = None,
    base_dir: Optional[str] = None,
    min_relevance: float = 0.5
) -> str:
    """
    Convenience function for session start injection.

    Args:
        cwd: Optional working directory (default: os.getcwd())
        base_dir: Optional base directory for storage
        min_relevance: Minimum relevance score (default: 0.5)

    Returns:
        Markdown-formatted memories
    """
    detector = ContextDetector()
    context = detector.detect(cwd=cwd)

    injector = ContextInjector(base_dir=base_dir)
    return injector.inject_startup(context=context, min_relevance=min_relevance)


def inject_query_context(
    query: str,
    cwd: Optional[str] = None,
    base_dir: Optional[str] = None,
    min_relevance: float = 0.3
) -> str:
    """
    Convenience function for on-demand query injection.

    Args:
        query: Query string
        cwd: Optional working directory
        base_dir: Optional base directory for storage
        min_relevance: Minimum relevance score (default: 0.3)

    Returns:
        Markdown-formatted memories
    """
    detector = ContextDetector()
    context = detector.detect(cwd=cwd)

    injector = ContextInjector(base_dir=base_dir)
    return injector.inject_query(query=query, context=context, min_relevance=min_relevance)


def detect_context(cwd: Optional[str] = None) -> DetectedContext:
    """
    Convenience function for context detection.

    Args:
        cwd: Optional working directory

    Returns:
        DetectedContext
    """
    detector = ContextDetector()
    return detector.detect(cwd=cwd)


def create_test_scenarios():
    """
    Create test scenarios for validation.

    Returns:
        List of test scenario dictionaries
    """
    return [
        {
            "name": "Startup injection with context",
            "has_memories": True,
            "expected_budget": 1200,
            "expected_format": "markdown with categories"
        },
        {
            "name": "On-demand query",
            "query": "error handling",
            "expected_budget": 500,
            "expected_format": "markdown with query header"
        },
        {
            "name": "Budget enforcement",
            "startup_tokens": 1200,
            "query_tokens": 500,
            "expected_total": 1700,
            "expected_cap": 2200
        },
        {
            "name": "Query limit enforcement",
            "queries": 3,
            "expected_allowed": 2,
            "expected_rejected": 1
        },
        {
            "name": "Context detection",
            "cwd": "/path/to/project",
            "expected_project": "project",
            "expected_language": "auto-detected"
        },
        {
            "name": "Empty memories",
            "has_memories": False,
            "expected_output": "empty string"
        }
    ]
