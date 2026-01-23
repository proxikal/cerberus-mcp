"""
Phase 7: Context-Aware Injection

Hybrid memory injection - auto-inject at session start, on-demand during work.
Uses Phase 6 retrieval to load memories and formats for Claude.

Phase 14 Integration: Includes code examples from anchored memories.
Phase 15 Integration: Filters memories by detected user intent mode.

Token budget:
- Session start: 1200 tokens (auto-injection)
  - 40% text rules (480 tokens)
  - 60% code examples (720 tokens)
- On-demand queries: 500 tokens each (max 2 queries = 1000 tokens)
- Total cap: 2200 tokens per session
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass
import tiktoken

from cerberus.memory.retrieval import MemoryRetrieval, RetrievedMemory

# Phase 14: Dynamic Anchoring
from cerberus.memory.anchoring import AnchorEngine

# Phase 15: Mode-Aware Context
from cerberus.memory.mode_detection import ModeDetector

# Session Continuity: Load previous session work context
from cerberus.memory.session_continuity import SessionContextInjector


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

    def __init__(self, base_dir: Optional[str] = None, encoding: str = "cl100k_base", enable_anchoring: bool = True, enable_mode_filtering: bool = False):
        """
        Args:
            base_dir: Base directory for storage (default: ~/.cerberus/memory)
            encoding: Tokenizer encoding (default: cl100k_base for GPT-4)
            enable_anchoring: Enable Phase 14 code examples (default: True)
            enable_mode_filtering: Enable Phase 15 mode-aware filtering (default: True)
        """
        self.retrieval = MemoryRetrieval(base_dir=base_dir, encoding=encoding)
        self.tokenizer = tiktoken.get_encoding(encoding)
        self.session_tokens_used = 0
        self.ondemand_queries_count = 0
        self.enable_anchoring = enable_anchoring
        self._anchor_engine = AnchorEngine() if enable_anchoring else None
        self.enable_mode_filtering = enable_mode_filtering
        self._mode_detector = ModeDetector() if enable_mode_filtering else None

    def inject_startup(
        self,
        context: Optional[DetectedContext] = None,
        user_prompt: Optional[str] = None,
        min_relevance: float = 0.5
    ) -> str:
        """
        Auto-inject memories at session start.

        Budget: 1200 tokens
        Priority: High relevance only (min_relevance=0.5)

        Phase 15: Filters by detected mode if user_prompt provided
        Phase 17+: Includes previous session work context (read-once-delete)

        Args:
            context: Optional detected context (auto-detects if None)
            user_prompt: Optional user prompt for mode detection (Phase 15)
            min_relevance: Minimum relevance score (default: 0.5)

        Returns:
            Markdown-formatted memories for injection with optional session context
        """
        if context is None:
            detector = ContextDetector()
            context = detector.detect()

        output_sections = []
        has_session_context = False

        # Try to load previous session work context (read-once-delete pattern)
        try:
            session_injector = SessionContextInjector()
            session_package = session_injector.inject()

            if session_package:
                has_session_context = True
                # Format session context section - clean AI format
                session_lines = [
                    "## Session Context",
                    f"*{session_package.scope}*",
                    "",
                    session_package.codes
                ]
                output_sections.append("\n".join(session_lines))
        except Exception:
            # Silently fail if session loading fails - don't block startup
            pass

        # Retrieve memories with startup budget
        memories = self.retrieval.retrieve(
            language=context.language,
            project=context.project,
            token_budget=self.STARTUP_BUDGET,
            min_relevance=min_relevance
        )

        # Phase 15: Filter by mode if enabled
        if memories and self.enable_mode_filtering and user_prompt and self._mode_detector:
            memories = self._filter_by_mode(memories, user_prompt, context)

        # Format memories
        if memories:
            formatted = self._format_memories(memories, context, has_session=has_session_context)
            output_sections.append(formatted)
        else:
            # No memories - minimal output
            if not has_session_context:
                # Only show if we also have no session
                header_lines = [
                    "## Memory Context",
                    f"*Project: {context.project} | Language: {context.language}*" if context.project and context.language else ""
                ]
                output_sections.append("\n".join([l for l in header_lines if l]))

        # Combine all sections
        final_output = "\n\n".join(output_sections)

        # Track token usage
        self.session_tokens_used += self._count_tokens(final_output)

        return final_output

    def inject_query(
        self,
        query: str,
        context: Optional[DetectedContext] = None,
        user_prompt: Optional[str] = None,
        min_relevance: float = 0.3
    ) -> str:
        """
        On-demand memory injection for specific query.

        Budget: 500 tokens per query, max 2 queries (1000 tokens total)

        Phase 15: Filters by detected mode if user_prompt provided

        Args:
            query: Query string (used for filtering, not semantic search)
            context: Optional detected context
            user_prompt: Optional user prompt for mode detection (Phase 15)
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

        # Phase 15: Filter by mode if enabled (use query as prompt if no user_prompt)
        if self.enable_mode_filtering and self._mode_detector:
            prompt_for_mode = user_prompt if user_prompt else query
            memories = self._filter_by_mode(memories, prompt_for_mode, context)

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
        query: Optional[str] = None,
        has_session: bool = False
    ) -> str:
        """
        Format memories as markdown for Claude.

        Args:
            memories: List of retrieved memories
            context: Detected context
            query: Optional query string (for on-demand)
            has_session: Whether session context was already loaded (for status reporting)

        Returns:
            Markdown-formatted string
        """
        if not memories:
            return ""

        lines = []

        # Minimal header - AI Format
        lines.append("## Memory Context")
        lines.append(f"*Project: {context.project} | Language: {context.language}*" if context.project and context.language else "")
        lines.append("")

        # Group by category
        by_category = {
            "preference": [],
            "rule": [],
            "decision": [],
            "correction": []
        }

        for memory in memories:
            by_category[memory.category].append(memory)

        # Format each category
        category_labels = {
            "preference": "Preferences",
            "rule": "Rules",
            "decision": "Decisions",
            "correction": "Corrections"
        }

        # NO HEADERS. NO PROSE. AI Format only (like session codes)
        for category in ["preference", "rule", "decision", "correction"]:
            items = by_category[category]
            if not items:
                continue

            for memory in items:
                # Format: category:content[scope]
                # NO PROSE. NO MARKDOWN. Pure data.
                scope_suffix = ""
                if memory.scope != "universal":
                    if memory.scope.startswith("language:"):
                        lang = memory.scope.split(":", 1)[1]
                        scope_suffix = f"[{lang}]"
                    elif memory.scope.startswith("project:"):
                        proj = memory.scope.split(":", 1)[1]
                        scope_suffix = f"[{proj}]"

                # Map category to prefix
                prefix_map = {
                    "preference": "pref",
                    "rule": "rule",
                    "decision": "decision",
                    "correction": "correction"
                }
                prefix = prefix_map.get(category, category)

                lines.append(f"{prefix}:{memory.content}{scope_suffix}")

                # Phase 14: Add code example if anchored
                if self.enable_anchoring and self._anchor_engine and hasattr(memory, 'anchor_file') and memory.anchor_file:
                    try:
                        # Read anchor code
                        code_snippet = self._anchor_engine.read_anchor_code(
                            file_path=memory.anchor_file,
                            symbol_name=getattr(memory, 'anchor_symbol', None),
                            max_lines=30
                        )

                        # Detect language from file extension
                        file_ext = Path(memory.anchor_file).suffix.lstrip('.')
                        lang_tag = file_ext if file_ext else ""

                        # Format code example
                        lines.append(f"  Example: `{memory.anchor_file}`")
                        lines.append(f"  ```{lang_tag}")
                        lines.append(f"  {code_snippet.strip()}")
                        lines.append(f"  ```")
                    except Exception:
                        # Skip anchor if reading fails
                        pass

        return "\n".join([l for l in lines if l])

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

    def _filter_by_mode(
        self,
        memories: List[RetrievedMemory],
        user_prompt: str,
        context: DetectedContext
    ) -> List[RetrievedMemory]:
        """
        Filter memories by detected user intent mode.

        Phase 15: Mode-aware filtering.

        Backward compatibility: Memories without valid_modes are included (default to all modes).

        Args:
            memories: List of retrieved memories
            user_prompt: User's prompt for mode detection
            context: Detected context

        Returns:
            Filtered list of memories matching detected mode
        """
        if not self._mode_detector:
            return memories

        # Build context dict for mode detection
        mode_context = {
            "modified_files": [],  # Would come from session tracking
            "tools_used": [],      # Would come from session tracking
        }

        # Detect mode
        mode_result = self._mode_detector.detect(user_prompt, mode_context)
        primary_mode = mode_result.primary_mode.mode

        # Filter memories
        filtered = []
        for memory in memories:
            # Parse valid_modes from memory
            valid_modes = None
            if hasattr(memory, 'valid_modes') and memory.valid_modes:
                try:
                    if isinstance(memory.valid_modes, str):
                        valid_modes = json.loads(memory.valid_modes)
                    elif isinstance(memory.valid_modes, list):
                        valid_modes = memory.valid_modes
                except (json.JSONDecodeError, TypeError):
                    # Failed to parse - include memory (backward compat)
                    valid_modes = None

            # Backward compatibility: If no valid_modes, include the memory (applies to all modes)
            # Otherwise, check if primary mode is in valid_modes
            if valid_modes is None or primary_mode in valid_modes:
                filtered.append(memory)

        return filtered

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
