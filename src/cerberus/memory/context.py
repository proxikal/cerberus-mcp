"""
Context Generation Module

Generates terse, AI-optimized context from stored memory.
This is the "inject" side of "store verbose, inject terse".

Key constraints:
- Phase 18.1: Profile only, <50 lines
- Phase 18.2: With decisions/corrections, <100 lines
- Phase 18.3+: Full context, <150 lines / 4KB
- Target: 90%+ compression from stored data
"""

from typing import Dict, Any, List, Optional

from cerberus.memory.store import MemoryStore
from cerberus.memory.profile import ProfileManager, Profile
from cerberus.memory.decisions import DecisionManager
from cerberus.memory.corrections import CorrectionManager
from cerberus.memory.prompts import PromptManager


class ContextGenerator:
    """
    Generates compressed context for AI session injection.

    The output is optimized for:
    - Token efficiency (terse, no redundancy)
    - AI comprehension (structured, clear)
    - Human readability (markdown format)
    """

    # Maximum lines for context output
    MAX_PROFILE_LINES = 50
    MAX_FULL_CONTEXT_LINES = 150

    # Limits for each section
    MAX_DECISIONS_IN_CONTEXT = 5
    MAX_CORRECTIONS_IN_CONTEXT = 5
    MAX_PROMPTS_IN_CONTEXT = 3

    # Style key to human-readable descriptions
    STYLE_DESCRIPTIONS = {
        "prefer_early_returns": "Early returns over nested conditionals",
        "async_style": {
            "async_await": "async/await over raw Promises",
            "promises": "Promises over async/await",
        },
        "error_handling": {
            "log_then_throw": "Log errors before rethrowing",
        },
        "imports": {
            "named_over_default": "Named imports over default imports",
            "default_preferred": "Default imports preferred",
        },
        "quotes": {
            "single": "Single quotes for strings",
            "double": "Double quotes for strings",
        },
        "max_line_length": "Max line length: {}",
    }

    def __init__(self, store: Optional[MemoryStore] = None):
        """
        Initialize the context generator.

        Args:
            store: MemoryStore instance (creates default if not provided)
        """
        self.store = store or MemoryStore()
        self.profile_manager = ProfileManager(self.store)
        self.decision_manager = DecisionManager(self.store)
        self.correction_manager = CorrectionManager(self.store)
        self.prompt_manager = PromptManager(self.store)

    def generate_profile_context(self, compact: bool = False) -> str:
        """
        Generate context from profile only (Phase 18.1).

        Args:
            compact: If True, even more minimal output

        Returns:
            Markdown string optimized for AI injection
        """
        profile = self.profile_manager.load_profile()

        if profile.is_empty():
            return "## Developer Context\n\nNo preferences stored yet. Use `cerberus memory learn` to add preferences."

        lines = []
        lines.append("## Developer Context (Session Memory)")
        lines.append("")

        # Coding style section
        style_items = self._format_coding_style(profile.coding_style)
        if style_items:
            if not compact:
                lines.append("### Style")
            for item in style_items:
                lines.append(f"- {item}")
            lines.append("")

        # Naming conventions
        if profile.naming_conventions:
            if not compact:
                lines.append("### Naming")
            for context, convention in profile.naming_conventions.items():
                display_context = context.replace("_", " ").title()
                lines.append(f"- {display_context}: {convention}")
            lines.append("")

        # Anti-patterns
        if profile.anti_patterns:
            if not compact:
                lines.append("### Avoid")
            for ap in profile.anti_patterns[:5]:  # Limit to top 5
                lines.append(f"- {ap}")
            lines.append("")

        # General preferences
        if profile.general:
            if not compact:
                lines.append("### Preferences")
            for pref in profile.general[:5]:  # Limit to top 5
                lines.append(f"- {pref}")
            lines.append("")

        # Ensure we don't exceed the limit
        result = "\n".join(lines)
        line_count = len(lines)

        if line_count > self.MAX_PROFILE_LINES:
            # Truncate if needed
            lines = lines[:self.MAX_PROFILE_LINES - 1]
            lines.append(f"\n(Truncated to {self.MAX_PROFILE_LINES} lines)")
            result = "\n".join(lines)

        return result.strip()

    def generate_context(
        self,
        project: Optional[str] = None,
        task: Optional[str] = None,
        compact: bool = False,
    ) -> str:
        """
        Generate full context for injection.

        Args:
            project: Project name for project-specific decisions (auto-detected if None)
            task: Task type for relevant prompts (Phase 18.3)
            compact: If True, minimal output

        Returns:
            Markdown string optimized for AI injection
        """
        profile = self.profile_manager.load_profile()
        lines = []

        # Check if we have any content
        has_profile = not profile.is_empty()

        # Auto-detect project if not provided
        detected_project = project or self.decision_manager.detect_project_name()
        decisions = []
        if detected_project:
            project_decisions = self.decision_manager.load_decisions(detected_project)
            decisions = project_decisions.get_recent(self.MAX_DECISIONS_IN_CONTEXT)

        corrections = self.correction_manager.load_corrections()
        top_corrections = corrections.get_by_frequency(self.MAX_CORRECTIONS_IN_CONTEXT)

        # Check if we have prompts for the task
        prompts = []
        if task:
            prompts = self.prompt_manager.get_prompts_for_context(
                task, count=self.MAX_PROMPTS_IN_CONTEXT
            )

        # If nothing stored, return empty message
        if not has_profile and not decisions and not top_corrections and not prompts:
            return "## Developer Context\n\nNo preferences stored yet. Use `cerberus memory learn` to add preferences."

        # Header
        lines.append("## Developer Context (Session Memory)")
        lines.append("")

        # Profile section (always first)
        if has_profile:
            # Coding style
            style_items = self._format_coding_style(profile.coding_style)
            if style_items:
                if not compact:
                    lines.append("### Style")
                for item in style_items:
                    lines.append(f"- {item}")
                lines.append("")

            # Naming conventions
            if profile.naming_conventions:
                if not compact:
                    lines.append("### Naming")
                for context, convention in profile.naming_conventions.items():
                    display_context = context.replace("_", " ").title()
                    lines.append(f"- {display_context}: {convention}")
                lines.append("")

            # Anti-patterns
            if profile.anti_patterns:
                if not compact:
                    lines.append("### Avoid")
                for ap in profile.anti_patterns[:5]:
                    lines.append(f"- {ap}")
                lines.append("")

            # General preferences
            if profile.general:
                if not compact:
                    lines.append("### Preferences")
                for pref in profile.general[:5]:
                    lines.append(f"- {pref}")
                lines.append("")

        # Decisions section (project-specific)
        if decisions:
            if not compact:
                lines.append(f"### Project: {detected_project} (Decisions)")
            else:
                lines.append(f"### {detected_project}")
            for d in decisions:
                lines.append(d.to_terse())
            lines.append("")

        # Corrections section (frequency-ranked)
        if top_corrections:
            if not compact:
                lines.append("### Common Corrections")
                lines.append("When generating code, remember:")
            for c in top_corrections:
                lines.append(c.to_terse())
            lines.append("")

        # Prompts section (task-specific) - use already-fetched prompts
        if prompts:
            task_display = task.replace("-", " ").title()
            if not compact:
                lines.append(f"### For {task_display} Tasks")
            for p in prompts:
                lines.append(p)
            lines.append("")

        # Ensure we don't exceed the limit
        result = "\n".join(lines)
        line_count = len(lines)

        if line_count > self.MAX_FULL_CONTEXT_LINES:
            lines = lines[:self.MAX_FULL_CONTEXT_LINES - 1]
            lines.append(f"\n(Truncated to {self.MAX_FULL_CONTEXT_LINES} lines)")
            result = "\n".join(lines)

        return result.strip()

    def _format_coding_style(self, style: Dict[str, Any]) -> List[str]:
        """Format coding style preferences for output."""
        items = []

        for key, value in style.items():
            if key in self.STYLE_DESCRIPTIONS:
                desc = self.STYLE_DESCRIPTIONS[key]

                if isinstance(desc, dict):
                    # Lookup value in nested dict
                    if value in desc:
                        items.append(desc[value])
                    else:
                        items.append(f"{key}: {value}")
                elif "{}" in desc:
                    # Format string with value
                    items.append(desc.format(value))
                elif isinstance(value, bool) and value:
                    # Boolean True - use the description
                    items.append(desc)
                else:
                    items.append(f"{key}: {value}")
            else:
                # Unknown key - format as-is
                display_key = key.replace("_", " ").title()
                items.append(f"{display_key}: {value}")

        return items

    def get_context_stats(self) -> Dict[str, Any]:
        """Get statistics about the generated context."""
        context = self.generate_context()
        context_bytes = len(context.encode('utf-8'))

        # Calculate total stored bytes
        stored_bytes = 0

        # Profile
        profile = self.profile_manager.load_profile()
        stored_bytes += len(str(profile.to_dict()).encode('utf-8'))

        # Decisions (all projects)
        for project in self.decision_manager.list_projects():
            decisions = self.decision_manager.load_decisions(project)
            stored_bytes += len(str(decisions.to_dict()).encode('utf-8'))

        # Corrections
        corrections = self.correction_manager.load_corrections()
        stored_bytes += len(str(corrections.to_dict()).encode('utf-8'))

        # Prompts (all task types)
        for task_type in self.prompt_manager.list_task_types():
            library = self.prompt_manager.load_library(task_type)
            stored_bytes += len(str(library.to_dict()).encode('utf-8'))

        # Calculate compression ratio
        compression_ratio = 0.0
        if stored_bytes > 0:
            compression_ratio = 1 - (context_bytes / stored_bytes)

        return {
            "context_bytes": context_bytes,
            "context_lines": len(context.split('\n')),
            "stored_bytes": stored_bytes,
            "compression_ratio": round(compression_ratio * 100, 1),
            "under_limit": context_bytes <= MemoryStore.MAX_CONTEXT_SIZE,
        }
