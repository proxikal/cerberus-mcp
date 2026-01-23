"""
Phase 5: Storage Operations (Version 1 - JSON)

Write approved proposals to hierarchical JSON storage.
This is Phase Alpha implementation - will be replaced with SQLite in Phase Beta (Phase 13).

Zero token cost (pure storage).
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from collections import defaultdict


class MemoryStorage:
    """
    JSON-based hierarchical storage for memories.

    Phase Alpha (MVP): JSON files
    Phase Beta: Will be replaced with SQLite writes

    Storage structure:
    ~/.cerberus/memory/
    ├── profile.json              # Universal preferences
    ├── corrections.json          # Universal corrections
    ├── languages/
    │   ├── go.json
    │   ├── python.json
    │   └── typescript.json
    └── projects/
        └── {project}/
            └── decisions.json
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Args:
            base_dir: Base directory for storage (default: ~/.cerberus/memory)
        """
        if base_dir is None:
            base_dir = os.path.expanduser("~/.cerberus/memory")

        self.base_dir = Path(base_dir)
        self._ensure_base_dir()

    def store_batch(self, proposals: List) -> Dict[str, int]:
        """
        Store batch of approved proposals.

        Batch optimization: Group proposals by target file, write once per file.

        Args:
            proposals: List of MemoryProposal or AgentProposal objects

        Returns:
            Dict mapping file path to count of memories stored
        """
        if not proposals:
            return {}

        # Group proposals by target file path
        grouped = self._group_by_file(proposals)

        # Write each group to its target file
        results = {}
        for file_path, proposals_for_file in grouped.items():
            count = self._write_to_file(file_path, proposals_for_file)
            results[str(file_path)] = count

        return results

    def _group_by_file(self, proposals: List) -> Dict[Path, List]:
        """
        Group proposals by target file path based on scope and category.

        Routing logic:
        - scope=universal, category=preference → profile.json
        - scope=universal, category=correction/rule → corrections.json
        - scope=language:X → languages/X.json
        - scope=project:X → projects/X/decisions.json

        Args:
            proposals: List of proposals

        Returns:
            Dict mapping file path to list of proposals
        """
        grouped = defaultdict(list)

        for proposal in proposals:
            file_path = self._get_file_path(proposal.scope, proposal.category)
            grouped[file_path].append(proposal)

        return grouped

    def _get_file_path(self, scope: str, category: str) -> Path:
        """
        Get file path for a given scope and category.

        Args:
            scope: Scope string (universal, language:X, project:X)
            category: Category string (preference, rule, correction)

        Returns:
            Path to target JSON file
        """
        # Universal scope
        if scope == "universal":
            if category == "preference":
                return self.base_dir / "profile.json"
            else:  # rule or correction
                return self.base_dir / "corrections.json"

        # Language scope
        if scope.startswith("language:"):
            lang = scope.split(":", 1)[1]
            return self.base_dir / "languages" / f"{lang}.json"

        # Project scope
        if scope.startswith("project:"):
            project = scope.split(":", 1)[1]
            return self.base_dir / "projects" / project / "decisions.json"

        # Default to corrections.json
        return self.base_dir / "corrections.json"

    def _write_to_file(self, file_path: Path, proposals: List) -> int:
        """
        Write proposals to a JSON file.

        Merges with existing content if file exists.
        Creates directories as needed.

        Args:
            file_path: Target file path
            proposals: List of proposals to write

        Returns:
            Number of memories written
        """
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing memories
        existing = self._load_file(file_path)

        # Convert proposals to stored memory format
        new_memories = [self._proposal_to_memory(p) for p in proposals]

        # Merge with existing (avoid duplicates by ID)
        existing_ids = {m["id"] for m in existing}
        for memory in new_memories:
            if memory["id"] not in existing_ids:
                existing.append(memory)

        # Write to file (atomic write via temp file)
        self._atomic_write(file_path, existing)

        return len(new_memories)

    def _proposal_to_memory(self, proposal) -> Dict:
        """
        Convert proposal to stored memory format with metadata.

        Args:
            proposal: MemoryProposal or AgentProposal

        Returns:
            Dict in stored memory format
        """
        return {
            "id": proposal.id,
            "category": proposal.category,
            "scope": proposal.scope,
            "content": proposal.content,
            "rationale": proposal.rationale,
            "confidence": proposal.confidence,
            "timestamp": datetime.now().isoformat(),
            "access_count": 0,
            "last_accessed": None
        }

    def _load_file(self, file_path: Path) -> List[Dict]:
        """
        Load memories from JSON file.

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
                # Handle both list and dict formats
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "memories" in data:
                    return data["memories"]
                else:
                    return []
        except (json.JSONDecodeError, IOError):
            # Corrupted file - return empty list
            return []

    def _atomic_write(self, file_path: Path, memories: List[Dict]) -> None:
        """
        Atomic write to JSON file (via temp file).

        Args:
            file_path: Target file path
            memories: List of memory dicts to write
        """
        # Write to temp file first
        temp_path = file_path.with_suffix('.tmp')

        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(memories, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(file_path)
        except Exception as e:
            # Cleanup temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise e

    def _ensure_base_dir(self) -> None:
        """Ensure base directory exists."""
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_stats(self) -> Dict[str, int]:
        """
        Get storage statistics.

        Returns:
            Dict with counts per file
        """
        stats = {}

        # Check all possible files
        files_to_check = [
            ("profile.json", self.base_dir / "profile.json"),
            ("corrections.json", self.base_dir / "corrections.json"),
        ]

        # Add language files
        languages_dir = self.base_dir / "languages"
        if languages_dir.exists():
            for lang_file in languages_dir.glob("*.json"):
                files_to_check.append(
                    (f"languages/{lang_file.name}", lang_file)
                )

        # Add project files
        projects_dir = self.base_dir / "projects"
        if projects_dir.exists():
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir():
                    decisions_file = project_dir / "decisions.json"
                    if decisions_file.exists():
                        files_to_check.append(
                            (f"projects/{project_dir.name}/decisions.json", decisions_file)
                        )

        # Count memories in each file
        for label, file_path in files_to_check:
            if file_path.exists():
                memories = self._load_file(file_path)
                stats[label] = len(memories)

        return stats


def store_proposals(
    proposals: List,
    base_dir: Optional[str] = None
) -> Dict[str, int]:
    """
    Convenience function to store proposals.

    Args:
        proposals: List of MemoryProposal or AgentProposal objects
        base_dir: Optional base directory (default: ~/.cerberus/memory)

    Returns:
        Dict mapping file path to count of memories stored
    """
    storage = MemoryStorage(base_dir=base_dir)
    return storage.store_batch(proposals)


def get_storage_stats(base_dir: Optional[str] = None) -> Dict[str, int]:
    """
    Get storage statistics.

    Args:
        base_dir: Optional base directory (default: ~/.cerberus/memory)

    Returns:
        Dict with counts per file
    """
    storage = MemoryStorage(base_dir=base_dir)
    return storage.get_stats()


def create_test_scenarios():
    """
    Create test scenarios for validation.

    Returns:
        List of test scenario dictionaries
    """
    return [
        {
            "name": "Universal preference",
            "scope": "universal",
            "category": "preference",
            "expected_file": "profile.json"
        },
        {
            "name": "Universal correction",
            "scope": "universal",
            "category": "correction",
            "expected_file": "corrections.json"
        },
        {
            "name": "Language-specific rule",
            "scope": "language:go",
            "category": "rule",
            "expected_file": "languages/go.json"
        },
        {
            "name": "Project-specific decision",
            "scope": "project:cerberus",
            "category": "rule",
            "expected_file": "projects/cerberus/decisions.json"
        },
        {
            "name": "Batch optimization",
            "proposals": [
                {"scope": "universal", "category": "preference"},
                {"scope": "universal", "category": "preference"},
                {"scope": "language:python", "category": "rule"},
            ],
            "expected_files": 2,  # profile.json + languages/python.json
            "expected_writes": 1  # per file (batch optimization)
        }
    ]
