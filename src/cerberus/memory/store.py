"""
Memory Storage Module

Handles JSON file operations for Session Memory.
Storage location: ~/.config/cerberus/memory/

Key design:
- Thread-safe file operations
- Atomic writes (write to temp, then rename)
- Schema versioning for future migrations
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import tempfile
import shutil

from cerberus.logging_config import logger


class MemoryStore:
    """
    Handles low-level storage operations for Session Memory.

    Storage structure:
    ~/.config/cerberus/memory/
    ├── profile.json              # Global preferences
    ├── corrections.json          # Patterns you repeatedly fix
    ├── prompts/                  # Effective prompts by task type
    └── projects/                 # Per-project decisions
    """

    # Size limits (in bytes)
    MAX_PROFILE_SIZE = 1024  # 1KB
    MAX_CONTEXT_SIZE = 4096  # 4KB

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize the memory store.

        Args:
            base_path: Override the default storage location (for testing)
        """
        if base_path is None:
            # Default: ~/.config/cerberus/memory/
            config_home = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
            self.base_path = Path(config_home) / 'cerberus' / 'memory'
        else:
            self.base_path = base_path

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create the directory structure if it doesn't exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / 'prompts').mkdir(exist_ok=True)
        (self.base_path / 'projects').mkdir(exist_ok=True)

    @property
    def profile_path(self) -> Path:
        """Path to the profile.json file."""
        return self.base_path / 'profile.json'

    @property
    def corrections_path(self) -> Path:
        """Path to the corrections.json file."""
        return self.base_path / 'corrections.json'

    def project_path(self, project_name: str) -> Path:
        """Path to a project-specific decisions file."""
        # Sanitize project name for filesystem
        safe_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in project_name)
        return self.base_path / 'projects' / f'{safe_name}.json'

    def prompt_path(self, task_type: str) -> Path:
        """Path to a prompt file by task type."""
        safe_name = "".join(c if c.isalnum() or c in '-_' else '_' for c in task_type)
        return self.base_path / 'prompts' / f'{safe_name}.json'

    def read_json(self, path: Path) -> Optional[Dict[str, Any]]:
        """
        Read a JSON file safely.

        Args:
            path: Path to the JSON file

        Returns:
            Parsed JSON data, or None if file doesn't exist
        """
        if not path.exists():
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading {path}: {e}")
            return None

    def write_json(self, path: Path, data: Dict[str, Any], check_size: bool = False, max_size: int = 0) -> bool:
        """
        Write JSON data atomically (write to temp file, then rename).

        Args:
            path: Target path for the JSON file
            data: Data to write
            check_size: Whether to enforce size limits
            max_size: Maximum size in bytes (only if check_size=True)

        Returns:
            True if write succeeded, False otherwise
        """
        try:
            # Serialize to check size
            json_str = json.dumps(data, indent=2, ensure_ascii=False)

            if check_size and max_size > 0:
                size = len(json_str.encode('utf-8'))
                if size > max_size:
                    logger.error(f"Data exceeds size limit: {size} > {max_size} bytes")
                    return False

            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write: write to temp file, then rename
            fd, temp_path = tempfile.mkstemp(
                dir=path.parent,
                prefix='.tmp_',
                suffix='.json'
            )
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(json_str)

                # Atomic rename
                shutil.move(temp_path, path)
                return True

            except Exception:
                # Clean up temp file on error
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                raise

        except Exception as e:
            logger.error(f"Error writing {path}: {e}")
            return False

    def delete_file(self, path: Path) -> bool:
        """
        Delete a memory file.

        Args:
            path: Path to the file to delete

        Returns:
            True if deleted (or didn't exist), False on error
        """
        try:
            if path.exists():
                path.unlink()
            return True
        except Exception as e:
            logger.error(f"Error deleting {path}: {e}")
            return False

    def list_projects(self) -> list[str]:
        """List all projects with stored decisions."""
        projects_dir = self.base_path / 'projects'
        if not projects_dir.exists():
            return []

        return [
            p.stem for p in projects_dir.glob('*.json')
            if p.is_file()
        ]

    def list_prompts(self) -> list[str]:
        """List all stored prompt task types."""
        prompts_dir = self.base_path / 'prompts'
        if not prompts_dir.exists():
            return []

        return [
            p.stem for p in prompts_dir.glob('*.json')
            if p.is_file()
        ]

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memory."""
        stats = {
            'base_path': str(self.base_path),
            'profile_exists': self.profile_path.exists(),
            'corrections_exists': self.corrections_path.exists(),
            'project_count': len(self.list_projects()),
            'prompt_count': len(self.list_prompts()),
            'total_size_bytes': 0,
        }

        # Calculate total size
        if self.base_path.exists():
            for f in self.base_path.rglob('*.json'):
                if f.is_file():
                    stats['total_size_bytes'] += f.stat().st_size

        return stats

    @staticmethod
    def timestamp() -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(tz=None).astimezone().isoformat()
