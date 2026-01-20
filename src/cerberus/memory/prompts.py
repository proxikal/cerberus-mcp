"""
Prompts Module (Phase 18.3)

Manages a library of effective prompts by task type.
Stored in ~/.config/cerberus/memory/prompts/

Key constraints:
- Max 5 prompts per task type
- Prompts are ranked by effectiveness and usage
- Store full template, inject terse summary
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import date

from cerberus.memory.store import MemoryStore
from cerberus.memory import config
from cerberus.logging_config import logger


# Common task types
KNOWN_TASK_TYPES = [
    "code-review",
    "refactor",
    "testing",
    "debugging",
    "documentation",
    "security-audit",
    "performance",
    "migration",
    "feature",
    "bugfix",
]


@dataclass
class Prompt:
    """A single prompt template."""
    id: str
    name: str
    task_type: str
    description: str = ""
    template: str = ""
    variables: List[str] = field(default_factory=list)
    effectiveness: float = 0.5  # 0.0 to 1.0
    use_count: int = 0
    last_used: str = ""
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "description": self.description,
            "template": self.template,
            "variables": self.variables,
            "effectiveness": self.effectiveness,
            "use_count": self.use_count,
            "last_used": self.last_used,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Prompt":
        """Create Prompt from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            task_type=data.get("task_type", ""),
            description=data.get("description", ""),
            template=data.get("template", ""),
            variables=data.get("variables", []),
            effectiveness=data.get("effectiveness", 0.5),
            use_count=data.get("use_count", 0),
            last_used=data.get("last_used", ""),
            notes=data.get("notes", ""),
        )

    def to_terse(self) -> str:
        """Generate terse representation for context injection."""
        # Format: "- Name: Description (effectiveness%)"
        eff_pct = int(self.effectiveness * 100)
        if self.description:
            return f"- {self.name}: {self.description} ({eff_pct}% effective)"
        else:
            return f"- {self.name} ({eff_pct}% effective, {self.use_count} uses)"

    def record_use(self, successful: bool = True) -> None:
        """Record a use of this prompt."""
        self.use_count += 1
        self.last_used = date.today().isoformat()

        # Update effectiveness with exponential moving average
        if successful:
            self.effectiveness = min(1.0, self.effectiveness * 0.9 + 0.1)
        else:
            self.effectiveness = max(0.0, self.effectiveness * 0.9)

    def extract_variables(self) -> List[str]:
        """Extract variable placeholders from template."""
        # Matches {{variable_name}}
        pattern = r'\{\{(\w+)\}\}'
        return list(set(re.findall(pattern, self.template)))


@dataclass
class PromptLibrary:
    """Collection of prompts for a task type."""
    schema_version: str = "prompt-v1"
    task_type: str = ""
    prompts: List[Prompt] = field(default_factory=list)

    # Maximum prompts per task type configured in config.py

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "$schema": self.schema_version,
            "task_type": self.task_type,
            "prompts": [p.to_dict() for p in self.prompts],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptLibrary":
        """Create PromptLibrary from dictionary."""
        prompts = [Prompt.from_dict(p) for p in data.get("prompts", [])]
        return cls(
            schema_version=data.get("$schema", "prompt-v1"),
            task_type=data.get("task_type", ""),
            prompts=prompts,
        )

    def add_prompt(self, prompt: Prompt) -> None:
        """Add a prompt, maintaining the max limit."""
        # Check if prompt with same name exists
        for i, p in enumerate(self.prompts):
            if p.name == prompt.name:
                # Update existing prompt
                self.prompts[i] = prompt
                return

        self.prompts.insert(0, prompt)  # Most recent first

        max_prompts = config.max_prompts_per_project()
        if len(self.prompts) > max_prompts:
            # Remove lowest effectiveness prompts
            self.prompts = sorted(
                self.prompts,
                key=lambda p: (p.effectiveness, p.use_count),
                reverse=True
            )[:max_prompts]

    def get_by_effectiveness(self, count: int = 5) -> List[Prompt]:
        """Get prompts sorted by effectiveness."""
        sorted_prompts = sorted(
            self.prompts,
            key=lambda p: (p.effectiveness, p.use_count),
            reverse=True
        )
        return sorted_prompts[:count]

    def find_by_name(self, name: str) -> Optional[Prompt]:
        """Find a prompt by name."""
        name_lower = name.lower()
        for p in self.prompts:
            if p.name.lower() == name_lower:
                return p
        return None


class PromptManager:
    """
    Manages the prompt library.

    Prompts are stored per task type in separate JSON files.
    """

    def __init__(self, store: Optional[MemoryStore] = None):
        """
        Initialize the prompt manager.

        Args:
            store: MemoryStore instance (creates default if not provided)
        """
        self.store = store or MemoryStore()

    def load_library(self, task_type: str) -> PromptLibrary:
        """Load prompts for a task type."""
        path = self.store.prompt_path(task_type)
        data = self.store.read_json(path)
        if data is None:
            return PromptLibrary(task_type=task_type)
        return PromptLibrary.from_dict(data)

    def save_library(self, task_type: str, library: PromptLibrary) -> bool:
        """Save prompts for a task type."""
        library.task_type = task_type
        path = self.store.prompt_path(task_type)
        return self.store.write_json(path, library.to_dict())

    def _generate_id(self, library: PromptLibrary) -> str:
        """Generate a unique prompt ID."""
        existing_ids = {p.id for p in library.prompts}
        counter = len(library.prompts) + 1
        while f"prm-{counter:03d}" in existing_ids:
            counter += 1
        return f"prm-{counter:03d}"

    def learn_prompt(
        self,
        name: str,
        task_type: str,
        template: Optional[str] = None,
        description: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Learn a new prompt.

        Args:
            name: Prompt name (e.g., "security-audit")
            task_type: Task type (e.g., "code-review")
            template: Full prompt template (optional for simple prompts)
            description: Brief description
            notes: Usage notes

        Returns:
            Dict with 'success', 'prompt', 'message'
        """
        # Normalize task type
        task_type = self._normalize_task_type(task_type)

        library = self.load_library(task_type)

        # Create new prompt
        prompt = Prompt(
            id=self._generate_id(library),
            name=name,
            task_type=task_type,
            description=description or "",
            template=template or "",
            variables=[] if not template else self._extract_variables(template),
            effectiveness=0.5,
            use_count=0,
            last_used=date.today().isoformat(),
            notes=notes or "",
        )

        # Add to library
        library.add_prompt(prompt)

        if self.save_library(task_type, library):
            return {
                "success": True,
                "prompt": prompt.to_dict(),
                "task_type": task_type,
                "message": f"Learned prompt '{name}' for {task_type}",
            }
        else:
            return {
                "success": False,
                "message": "Failed to save prompt",
            }

    def _normalize_task_type(self, task_type: str) -> str:
        """Normalize task type to a known type or sanitize it."""
        task_lower = task_type.lower().strip()

        # Check for known task types
        for known in KNOWN_TASK_TYPES:
            if known in task_lower or task_lower in known:
                return known

        # Sanitize for filesystem
        return "".join(c if c.isalnum() or c in '-_' else '-' for c in task_lower)

    def _extract_variables(self, template: str) -> List[str]:
        """Extract variable placeholders from template."""
        pattern = r'\{\{(\w+)\}\}'
        return list(set(re.findall(pattern, template)))

    def forget_prompt(self, name: str, task_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Remove a prompt by name.

        Args:
            name: Prompt name
            task_type: Task type (if known, otherwise searches all)

        Returns:
            Dict with 'success' and 'message'
        """
        if task_type:
            task_types = [self._normalize_task_type(task_type)]
        else:
            task_types = self.list_task_types()

        for tt in task_types:
            library = self.load_library(tt)
            for i, p in enumerate(library.prompts):
                if p.name.lower() == name.lower():
                    removed = library.prompts.pop(i)
                    self.save_library(tt, library)
                    return {
                        "success": True,
                        "message": f"Removed prompt '{removed.name}' from {tt}",
                    }

        return {
            "success": False,
            "message": f"Prompt '{name}' not found",
        }

    def record_use(
        self,
        name: str,
        task_type: str,
        successful: bool = True
    ) -> Dict[str, Any]:
        """
        Record a use of a prompt.

        Args:
            name: Prompt name
            task_type: Task type
            successful: Whether the use was successful

        Returns:
            Dict with 'success' and updated 'effectiveness'
        """
        task_type = self._normalize_task_type(task_type)
        library = self.load_library(task_type)

        prompt = library.find_by_name(name)
        if prompt:
            prompt.record_use(successful)
            self.save_library(task_type, library)
            return {
                "success": True,
                "effectiveness": prompt.effectiveness,
                "use_count": prompt.use_count,
            }

        return {
            "success": False,
            "message": f"Prompt '{name}' not found in {task_type}",
        }

    def list_task_types(self) -> List[str]:
        """List all task types with stored prompts."""
        return self.store.list_prompts()

    def get_prompts_for_context(self, task_type: str, count: int = 3) -> List[str]:
        """
        Get terse prompt strings for context injection.

        Args:
            task_type: Task type
            count: Maximum number of prompts to include

        Returns:
            List of terse prompt strings
        """
        task_type = self._normalize_task_type(task_type)
        library = self.load_library(task_type)
        top_prompts = library.get_by_effectiveness(count)
        return [p.to_terse() for p in top_prompts]

    def get_all_prompts_for_context(self, count: int = 5) -> Dict[str, List[str]]:
        """
        Get terse prompts for all task types.

        Returns:
            Dict mapping task_type -> list of terse prompt strings
        """
        result = {}
        for task_type in self.list_task_types():
            library = self.load_library(task_type)
            if library.prompts:
                result[task_type] = [
                    p.to_terse() for p in library.get_by_effectiveness(count)
                ]
        return result

    def get_prompt_template(self, name: str, task_type: str) -> Optional[str]:
        """
        Get the full template for a prompt.

        Args:
            name: Prompt name
            task_type: Task type

        Returns:
            Template string or None if not found
        """
        task_type = self._normalize_task_type(task_type)
        library = self.load_library(task_type)
        prompt = library.find_by_name(name)
        return prompt.template if prompt else None

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of stored prompts."""
        task_types = self.list_task_types()
        total_prompts = 0
        by_type = {}

        for tt in task_types:
            library = self.load_library(tt)
            count = len(library.prompts)
            total_prompts += count
            by_type[tt] = count

        return {
            "total_prompts": total_prompts,
            "task_types": len(task_types),
            "by_type": by_type,
        }
