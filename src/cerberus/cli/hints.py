"""
Efficiency Hints System (Phase 19.2)

Provides soft guidance hints that append to command output.
Non-blocking, informational suggestions for more efficient workflows.

Principles:
- Hints are NEVER blocking - they append to output
- Hints are contextual - only shown when relevant
- Hints provide actionable alternatives
- Machine mode includes hints in JSON, human mode shows formatted tips
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path

from cerberus.logging_config import logger


@dataclass
class Hint:
    """A single efficiency hint."""

    type: str  # "efficiency", "memory", "correction"
    message: str
    alternative: Optional[str] = None
    command: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        result = {
            "type": self.type,
            "message": self.message,
        }
        if self.alternative:
            result["alternative"] = self.alternative
        if self.command:
            result["command"] = self.command
        return result

    def to_human(self) -> str:
        """Format for human-readable output."""
        parts = [f"Tip: {self.message}"]
        if self.command:
            parts.append(f"  Try: {self.command}")
        return "\n".join(parts)


class EfficiencyHints:
    """
    Static methods to check for efficiency hints.

    All methods return Optional[Hint] - None if no hint is applicable.
    """

    # Thresholds
    LARGE_RESPONSE_THRESHOLD = 500  # lines

    @staticmethod
    def check_large_response(
        lines: int,
        file_path: Optional[str] = None,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        used_snippet: bool = False,
    ) -> Optional[Hint]:
        """
        Check if a get-symbol response is too large.

        Returns a hint suggesting direct read or --snippet flag.
        """
        if lines <= EfficiencyHints.LARGE_RESPONSE_THRESHOLD:
            return None

        if used_snippet:
            return None  # Already using efficient mode

        message = f"Large response ({lines} lines)."

        if file_path and start_line and end_line:
            command = f"read {file_path} lines {start_line}-{end_line}"
            alternative = f"cerberus go {file_path}"
            message += f" For code editing, try: {command}"
        else:
            command = None
            alternative = "Use --snippet for raw code only"
            message += " Consider using --snippet for efficiency."

        return Hint(
            type="efficiency",
            message=message,
            alternative=alternative,
            command=command,
        )

    @staticmethod
    def check_memory_available(
        project: Optional[str] = None,
        used_with_memory: bool = False,
    ) -> Optional[Hint]:
        """
        Check if Session Memory has relevant decisions for the project.

        Returns a hint suggesting --with-memory flag for blueprint.
        """
        if used_with_memory:
            return None  # Already using memory

        try:
            from cerberus.memory.store import MemoryStore
            from cerberus.memory.decisions import DecisionManager
            from cerberus.memory.profile import ProfileManager

            store = MemoryStore()
            decision_manager = DecisionManager(store)
            profile_manager = ProfileManager(store)

            # Auto-detect project if not provided
            detected_project = project or decision_manager.detect_project_name()

            # Count available context
            decision_count = 0
            if detected_project:
                decisions = decision_manager.load_decisions(detected_project)
                decision_count = len(decisions.decisions)

            profile = profile_manager.load_profile()
            has_profile = not profile.is_empty()

            # Only show hint if there's something to include
            if decision_count == 0 and not has_profile:
                return None

            parts = []
            if decision_count > 0:
                parts.append(f"{decision_count} decisions")
            if has_profile:
                parts.append("profile preferences")

            message = f"Session Memory has {', '.join(parts)} for this project."

            return Hint(
                type="memory",
                message=message,
                alternative="Use --with-memory to include developer context",
                command="cerberus retrieval blueprint <file> --with-memory",
            )

        except Exception as e:
            logger.debug(f"Error checking memory availability: {e}")
            return None

    @staticmethod
    def check_corrections_available(
        file_path: Optional[str] = None,
        symbol_name: Optional[str] = None,
        used_check_corrections: bool = False,
    ) -> Optional[Hint]:
        """
        Check if Session Memory has relevant corrections.

        Returns a hint suggesting --check-corrections flag for mutations.
        """
        if used_check_corrections:
            return None  # Already checking corrections

        try:
            from cerberus.memory.store import MemoryStore
            from cerberus.memory.corrections import CorrectionManager

            store = MemoryStore()
            correction_manager = CorrectionManager(store)
            corrections = correction_manager.load_corrections()

            if not corrections.corrections:
                return None

            # Count relevant corrections (simple keyword matching)
            relevant_count = 0
            search_terms = []

            if file_path:
                # Extract meaningful parts from file path
                path = Path(file_path)
                search_terms.extend([
                    path.stem,  # filename without extension
                    path.parent.name,  # parent directory
                ])

            if symbol_name:
                search_terms.append(symbol_name.lower())

            # Check corrections for relevance
            for correction in corrections.corrections:
                pattern_lower = correction.pattern.lower()
                note_lower = (correction.note or "").lower()

                for term in search_terms:
                    if term and (term.lower() in pattern_lower or term.lower() in note_lower):
                        relevant_count += 1
                        break

            # If no search terms, count total corrections
            if not search_terms:
                relevant_count = len(corrections.corrections)

            if relevant_count == 0:
                return None

            context = ""
            if symbol_name:
                context = f" related to '{symbol_name}'"
            elif file_path:
                context = f" related to '{Path(file_path).stem}'"

            message = f"You have {relevant_count} corrections{context}."

            return Hint(
                type="correction",
                message=message,
                alternative="Use --check-corrections to review before editing",
                command="cerberus mutations edit <file> --symbol <name> --code '...' --check-corrections",
            )

        except Exception as e:
            logger.debug(f"Error checking corrections: {e}")
            return None

    @staticmethod
    def check_index_stale(
        index_path: Optional[Path] = None,
        threshold_minutes: int = 60,
    ) -> Optional[Hint]:
        """
        Check if the index is stale and suggest update.
        """
        from datetime import datetime

        if index_path is None:
            index_path = Path("cerberus.db")

        if not index_path.exists():
            return Hint(
                type="efficiency",
                message="No index found.",
                alternative="Create index for faster exploration",
                command="cerberus index .",
            )

        try:
            mtime = datetime.fromtimestamp(index_path.stat().st_mtime)
            age_minutes = (datetime.now() - mtime).total_seconds() / 60

            if age_minutes > threshold_minutes:
                return Hint(
                    type="efficiency",
                    message=f"Index is {int(age_minutes)} minutes old.",
                    alternative="Update for latest changes",
                    command="cerberus update",
                )
        except Exception as e:
            logger.debug(f"Error checking index staleness: {e}")

        return None

    @staticmethod
    def check_watcher_not_running(
        project_path: Optional[Path] = None,
    ) -> Optional[Hint]:
        """
        Check if watcher is not running and suggest starting it.
        """
        try:
            from cerberus.watcher import is_watcher_running

            if project_path is None:
                project_path = Path.cwd()

            if not is_watcher_running(project_path):
                return Hint(
                    type="efficiency",
                    message="File watcher not running.",
                    alternative="Start watcher for automatic index updates",
                    command="cerberus watcher start",
                )
        except Exception as e:
            logger.debug(f"Error checking watcher status: {e}")

        return None

    @staticmethod
    def check_protocol_refresh() -> Optional[Hint]:
        """
        Check if protocol refresh should be suggested.

        Returns a hint if:
        - 20+ cerberus commands without refresh
        - 10+ minutes since session start without refresh
        - 30+ minutes since last refresh
        """
        try:
            from cerberus.protocol import get_protocol_tracker

            tracker = get_protocol_tracker()

            if tracker.should_suggest_refresh():
                reason = tracker.get_refresh_reason()
                return Hint(
                    type="efficiency",
                    message=f"Protocol memory may be degraded: {reason}",
                    alternative="Refresh CERBERUS.md rules to ensure compliance",
                    command="cerberus refresh",
                )
        except Exception as e:
            logger.debug(f"Error checking protocol refresh: {e}")

        return None


class HintCollector:
    """
    Collects hints during command execution and formats output.
    """

    def __init__(self):
        self.hints: List[Hint] = []

    def add(self, hint: Optional[Hint]) -> None:
        """Add a hint if not None."""
        if hint is not None:
            self.hints.append(hint)

    def has_hints(self) -> bool:
        """Check if any hints were collected."""
        return len(self.hints) > 0

    def to_dict(self) -> List[Dict[str, Any]]:
        """Get hints as list of dictionaries for JSON output."""
        return [h.to_dict() for h in self.hints]

    def format_human(self) -> str:
        """Format hints for human-readable output."""
        if not self.hints:
            return ""

        lines = [""]  # Start with blank line
        for hint in self.hints:
            lines.append(hint.to_human())

        return "\n".join(lines)

    def inject_into_json(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject hints into a JSON output dictionary.

        Adds "hints" key if there are any hints.
        """
        if self.hints:
            output["hints"] = self.to_dict()
        return output


def get_hint_collector() -> HintCollector:
    """Get a new HintCollector instance."""
    return HintCollector()
