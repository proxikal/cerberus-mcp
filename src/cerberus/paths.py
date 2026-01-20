"""
Cerberus Path Configuration

Centralized path management for all Cerberus data files.
All paths are relative to the project root (current working directory).

Directory Structure:
.cerberus/
├── cerberus.db          # Main SQLite index
├── vectors.faiss        # FAISS vector index
├── vector_id_map.pkl    # Vector ID mapping
├── ledger.db            # Mutation ledger
├── session.json         # Agent session metrics
├── dev_session.json     # Dev session metrics (when in Cerberus repo)
├── backups/             # Mutation backups
├── history/             # Query history
└── logs/                # Log files
"""

import os
from pathlib import Path
from typing import Optional


class CerberusPaths:
    """
    Centralized path configuration for Cerberus.

    All paths are lazily resolved relative to project_root.
    Default project_root is current working directory.
    """

    # Directory name for all Cerberus data
    CERBERUS_DIR = ".cerberus"
    GLOBAL_DIR = Path.home() / ".cerberus"

    # File names (without paths)
    INDEX_DB_NAME = "cerberus.db"
    VECTORS_NAME = "vectors.faiss"
    VECTOR_MAP_NAME = "vector_id_map.pkl"
    LEDGER_DB_NAME = "ledger.db"
    SESSION_NAME = "session.json"
    DEV_SESSION_NAME = "dev_session.json"

    # Subdirectory names
    BACKUPS_DIR = "backups"
    HISTORY_DIR = "history"
    LOGS_DIR = "logs"

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize paths configuration.

        Args:
            project_root: Root directory for the project. Defaults to CWD.
        """
        self._project_root = project_root

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        if self._project_root is None:
            return Path.cwd()
        return self._project_root

    @property
    def cerberus_dir(self) -> Path:
        """Get the .cerberus directory path."""
        return self.project_root / self.CERBERUS_DIR

    @property
    def index_db(self) -> Path:
        """Get the main index database path."""
        return self.cerberus_dir / self.INDEX_DB_NAME

    @property
    def vectors_faiss(self) -> Path:
        """Get the FAISS vectors file path."""
        return self.cerberus_dir / self.VECTORS_NAME

    @property
    def vector_id_map(self) -> Path:
        """Get the vector ID map file path."""
        return self.cerberus_dir / self.VECTOR_MAP_NAME

    @property
    def ledger_db(self) -> Path:
        """Get the mutation ledger database path."""
        return self.cerberus_dir / self.LEDGER_DB_NAME

    @property
    def session_file(self) -> Path:
        """Get the session file path."""
        return self.cerberus_dir / self.SESSION_NAME

    @property
    def dev_session_file(self) -> Path:
        """Get the dev session file path."""
        return self.cerberus_dir / self.DEV_SESSION_NAME

    @property
    def backups_dir(self) -> Path:
        """Get the backups directory path."""
        return self.cerberus_dir / self.BACKUPS_DIR

    @property
    def history_dir(self) -> Path:
        """Get the history directory path."""
        return self.cerberus_dir / self.HISTORY_DIR

    @property
    def logs_dir(self) -> Path:
        """Get the logs directory path."""
        return self.cerberus_dir / self.LOGS_DIR

    def ensure_dirs(self) -> None:
        """Create all necessary directories if they don't exist."""
        self.cerberus_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(exist_ok=True)
        self.history_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

    def is_dev_mode(self) -> bool:
        """Check if running in Cerberus development mode."""
        git_dir = self.project_root / ".git"
        return git_dir.exists() and "Cerberus" in str(self.project_root)

    def get_session_file(self) -> Path:
        """Get appropriate session file based on dev mode."""
        if self.is_dev_mode():
            return self.dev_session_file
        return self.session_file

    # Legacy path support for backward compatibility
    @property
    def legacy_index_db(self) -> Path:
        """Legacy path: cerberus.db in project root."""
        return self.project_root / self.INDEX_DB_NAME

    @property
    def legacy_vectors_faiss(self) -> Path:
        """Legacy path: vectors.faiss in project root."""
        return self.project_root / self.VECTORS_NAME

    @property
    def legacy_vector_id_map(self) -> Path:
        """Legacy path: vector_id_map.pkl in project root."""
        return self.project_root / self.VECTOR_MAP_NAME

    @property
    def legacy_ledger_db(self) -> Path:
        """Legacy path: .cerberus_ledger.db in project root."""
        return self.project_root / ".cerberus_ledger.db"

    @property
    def legacy_session_file(self) -> Path:
        """Legacy path: .cerberus_session.json in project root."""
        return self.project_root / ".cerberus_session.json"

    @property
    def legacy_dev_session_file(self) -> Path:
        """Legacy path: .cerberus_dev_session.json in project root."""
        return self.project_root / ".cerberus_dev_session.json"

    @property
    def legacy_backups_dir(self) -> Path:
        """Legacy path: .cerberus_backups in project root."""
        return self.project_root / ".cerberus_backups"

    def get_index_path(self) -> Path:
        """
        Get the index database path, checking legacy location first.

        Returns new path if legacy doesn't exist, otherwise returns legacy path.
        This allows gradual migration.
        """
        if self.legacy_index_db.exists() and not self.index_db.exists():
            return self.legacy_index_db
        return self.index_db

    def needs_migration(self) -> bool:
        """Check if legacy files exist that should be migrated."""
        legacy_files = [
            self.legacy_index_db,
            self.legacy_vectors_faiss,
            self.legacy_vector_id_map,
            self.legacy_ledger_db,
            self.legacy_session_file,
            self.legacy_dev_session_file,
        ]
        return any(f.exists() for f in legacy_files)


# Global instance for convenience
_default_paths: Optional[CerberusPaths] = None


def get_paths(project_root: Optional[Path] = None) -> CerberusPaths:
    """
    Get the paths configuration.

    Args:
        project_root: Optional project root override

    Returns:
        CerberusPaths instance
    """
    global _default_paths
    if project_root is not None:
        return CerberusPaths(project_root)
    if _default_paths is None:
        _default_paths = CerberusPaths()
    return _default_paths


def reset_paths() -> None:
    """Reset the global paths instance (useful for testing)."""
    global _default_paths
    _default_paths = None


def find_index_path() -> Optional[Path]:
    """
    Find the index database path, checking multiple locations.

    Checks in order:
    1. .cerberus/cerberus.db (new location)
    2. cerberus.db (legacy location)

    Returns:
        Path to existing index, or None if not found
    """
    paths = get_paths()
    # Check new location first
    if paths.index_db.exists():
        return paths.index_db
    # Check legacy location
    if paths.legacy_index_db.exists():
        return paths.legacy_index_db
    return None


def get_index_path_or_default() -> Path:
    """
    Get the index path, returning default new location if none exists.

    Returns:
        Path to existing index, or default new path (.cerberus/cerberus.db)
    """
    existing = find_index_path()
    if existing:
        return existing
    # Return new default location (may not exist yet)
    return get_paths().index_db
