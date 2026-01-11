"""
Decisions Module (Phase 18.2)

Tracks architectural decisions per project.
Each project has its own decisions file stored in ~/.config/cerberus/memory/projects/

Key constraints:
- Max 10 most recent decisions per project
- Store verbose, inject terse (topic + decision only in context)
"""

import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import date

from cerberus.memory.store import MemoryStore
from cerberus.logging_config import logger


@dataclass
class Decision:
    """A single architectural decision."""
    id: str
    date: str
    topic: str
    decision: str
    rationale: str = ""
    alternatives_rejected: List[str] = field(default_factory=list)
    files_affected: List[str] = field(default_factory=list)
    confidence: str = "medium"  # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "date": self.date,
            "topic": self.topic,
            "decision": self.decision,
            "rationale": self.rationale,
            "alternatives_rejected": self.alternatives_rejected,
            "files_affected": self.files_affected,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        """Create Decision from dictionary."""
        return cls(
            id=data.get("id", ""),
            date=data.get("date", ""),
            topic=data.get("topic", ""),
            decision=data.get("decision", ""),
            rationale=data.get("rationale", ""),
            alternatives_rejected=data.get("alternatives_rejected", []),
            files_affected=data.get("files_affected", []),
            confidence=data.get("confidence", "medium"),
        )

    def to_terse(self) -> str:
        """Generate terse representation for context injection."""
        # Format: "- Topic: Decision (confidence)"
        conf_marker = ""
        if self.confidence == "high":
            conf_marker = ""
        elif self.confidence == "low":
            conf_marker = " [tentative]"

        return f"- {self.topic}: {self.decision}{conf_marker}"


@dataclass
class ProjectDecisions:
    """Collection of decisions for a project."""
    schema_version: str = "decisions-v1"
    project: str = ""
    decisions: List[Decision] = field(default_factory=list)

    # Maximum decisions to keep per project
    MAX_DECISIONS = 10

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "$schema": self.schema_version,
            "project": self.project,
            "decisions": [d.to_dict() for d in self.decisions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectDecisions":
        """Create ProjectDecisions from dictionary."""
        decisions = [Decision.from_dict(d) for d in data.get("decisions", [])]
        return cls(
            schema_version=data.get("$schema", "decisions-v1"),
            project=data.get("project", ""),
            decisions=decisions,
        )

    def add_decision(self, decision: Decision) -> None:
        """Add a decision, maintaining the max limit."""
        self.decisions.insert(0, decision)  # Most recent first
        if len(self.decisions) > self.MAX_DECISIONS:
            self.decisions = self.decisions[:self.MAX_DECISIONS]

    def get_recent(self, count: int = 5) -> List[Decision]:
        """Get the most recent decisions."""
        return self.decisions[:count]


class DecisionManager:
    """
    Manages project decisions.

    Decisions are stored per-project in separate JSON files.
    Auto-detects current project from git if not specified.
    """

    def __init__(self, store: Optional[MemoryStore] = None):
        """
        Initialize the decision manager.

        Args:
            store: MemoryStore instance (creates default if not provided)
        """
        self.store = store or MemoryStore()

    def detect_project_name(self) -> Optional[str]:
        """
        Auto-detect project name from git remote or directory.

        Returns:
            Project name or None if not in a git repo
        """
        try:
            # Try to get project name from git remote
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                # Extract repo name from URL
                # Handles: git@github.com:user/repo.git or https://github.com/user/repo.git
                match = re.search(r'/([^/]+?)(?:\.git)?$', url)
                if match:
                    return match.group(1)

            # Fallback: use git root directory name
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                from pathlib import Path
                return Path(result.stdout.strip()).name

        except Exception as e:
            logger.debug(f"Could not detect project name: {e}")

        return None

    def load_decisions(self, project: str) -> ProjectDecisions:
        """Load decisions for a project."""
        path = self.store.project_path(project)
        data = self.store.read_json(path)
        if data is None:
            return ProjectDecisions(project=project)
        return ProjectDecisions.from_dict(data)

    def save_decisions(self, project: str, decisions: ProjectDecisions) -> bool:
        """Save decisions for a project."""
        decisions.project = project
        path = self.store.project_path(project)
        return self.store.write_json(path, decisions.to_dict())

    def _generate_id(self, decisions: ProjectDecisions) -> str:
        """Generate a unique decision ID."""
        existing_ids = {d.id for d in decisions.decisions}
        counter = len(decisions.decisions) + 1
        while f"dec-{counter:03d}" in existing_ids:
            counter += 1
        return f"dec-{counter:03d}"

    def learn_decision(
        self,
        text: str,
        project: Optional[str] = None,
        rationale: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Learn a new decision from text.

        Args:
            text: The decision text (e.g., "chose SQLite for portability")
            project: Project name (auto-detected if not provided)
            rationale: Optional rationale for the decision

        Returns:
            Dict with 'success', 'project', 'decision', 'message'
        """
        # Auto-detect project if not provided
        if project is None:
            project = self.detect_project_name()
            if project is None:
                return {
                    "success": False,
                    "message": "Could not detect project. Use --project to specify.",
                }

        # Parse the decision text
        topic, decision_text = self._parse_decision_text(text)

        # Load existing decisions
        decisions = self.load_decisions(project)

        # Create new decision
        decision = Decision(
            id=self._generate_id(decisions),
            date=date.today().isoformat(),
            topic=topic,
            decision=decision_text,
            rationale=rationale or "",
            confidence="medium",
        )

        # Add and save
        decisions.add_decision(decision)
        if self.save_decisions(project, decisions):
            return {
                "success": True,
                "project": project,
                "decision": decision.to_dict(),
                "message": f"Learned decision for {project}: {topic}",
            }
        else:
            return {
                "success": False,
                "message": "Failed to save decision",
            }

    def _parse_decision_text(self, text: str) -> tuple[str, str]:
        """
        Parse decision text into topic and decision.

        Handles formats like:
        - "chose SQLite for portability"
        - "Parser: Use native ast over tree-sitter"
        - "using TypeScript instead of JavaScript"
        """
        text = text.strip()

        # Check for explicit "Topic: Decision" format
        if ":" in text:
            parts = text.split(":", 1)
            if len(parts[0]) < 30:  # Topic should be short
                return parts[0].strip(), parts[1].strip()

        # Try to extract topic from common patterns
        patterns = [
            # "chose X for Y" -> topic: "Technology Choice", decision: text
            (r"^chose\s+(\w+)", "Technology Choice"),
            # "using X instead of Y" -> topic: "Technology Choice"
            (r"^using\s+(\w+)", "Technology Choice"),
            # "decided to X" -> extract action as topic
            (r"^decided\s+to\s+(\w+)", "Architecture"),
            # "prefer X over Y" -> topic: "Preference"
            (r"^prefer\s+", "Preference"),
        ]

        for pattern, default_topic in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return default_topic, text

        # Fallback: use first few words as topic
        words = text.split()
        if len(words) > 3:
            topic = " ".join(words[:2]).title()
            return topic, text

        return "Decision", text

    def forget_decision(self, decision_id: str, project: Optional[str] = None) -> Dict[str, Any]:
        """
        Remove a decision by ID.

        Args:
            decision_id: The decision ID (e.g., "dec-001")
            project: Project name (auto-detected if not provided)

        Returns:
            Dict with 'success' and 'message'
        """
        if project is None:
            project = self.detect_project_name()
            if project is None:
                return {
                    "success": False,
                    "message": "Could not detect project. Use --project to specify.",
                }

        decisions = self.load_decisions(project)

        # Find and remove the decision
        for i, d in enumerate(decisions.decisions):
            if d.id == decision_id:
                removed = decisions.decisions.pop(i)
                self.save_decisions(project, decisions)
                return {
                    "success": True,
                    "message": f"Removed decision {decision_id}: {removed.topic}",
                }

        return {
            "success": False,
            "message": f"Decision {decision_id} not found in project {project}",
        }

    def list_projects(self) -> List[str]:
        """List all projects with stored decisions."""
        return self.store.list_projects()

    def get_decisions_for_context(self, project: str, count: int = 5) -> List[str]:
        """
        Get terse decision strings for context injection.

        Args:
            project: Project name
            count: Maximum number of decisions to include

        Returns:
            List of terse decision strings
        """
        decisions = self.load_decisions(project)
        return [d.to_terse() for d in decisions.get_recent(count)]
