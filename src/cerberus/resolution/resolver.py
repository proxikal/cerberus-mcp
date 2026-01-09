"""
Import resolution engine for Phase 5.2.

Resolves ImportLink.definition_file and definition_symbol fields
for internal project imports.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from cerberus.logging_config import logger
from cerberus.schemas import ImportLink, CodeSymbol
from cerberus.storage.sqlite_store import SQLiteIndexStore
from .config import CONFIDENCE_THRESHOLDS, RESOLUTION_CONFIG


class ImportResolver:
    """
    Resolves import links to their internal definitions.

    Phase 5.2: Import-Based Resolution (confidence: 1.0).

    Handles:
    - Direct module imports: from utils import helper -> utils.py::helper
    - Package imports: from package.module import func -> package/module.py::func
    - Relative imports: from . import local -> ./local.py
    """

    def __init__(self, store: SQLiteIndexStore, project_root: str):
        """
        Initialize resolver with storage and project context.

        Args:
            store: SQLite storage containing index data
            project_root: Root directory of the project
        """
        self.store = store
        self.project_root = Path(project_root)
        self._symbol_cache: Dict[str, List[CodeSymbol]] = {}
        self._build_symbol_cache()

    def _build_symbol_cache(self):
        """
        Build in-memory cache of symbols by name for fast lookup.

        Maps symbol_name -> List[CodeSymbol] for all symbols in index.
        """
        logger.debug("Building symbol cache for import resolution...")

        for symbol in self.store.query_symbols():
            name = symbol.name
            if name not in self._symbol_cache:
                self._symbol_cache[name] = []
            self._symbol_cache[name].append(symbol)

        logger.debug(f"Symbol cache built: {len(self._symbol_cache)} unique names")

    def resolve_import_links(self) -> List[Tuple[int, str, str]]:
        """
        Resolve all unresolved import links in the index.

        Returns:
            List of (link_id, definition_file, definition_symbol) tuples
            for links that were successfully resolved.
        """
        resolved = []
        unresolved_count = 0

        logger.info("Starting import link resolution...")

        # Query all import links where definition is NULL
        for link in self.store.query_import_links():
            # Skip already resolved links
            if link.definition_file is not None:
                continue

            unresolved_count += 1

            # Attempt to resolve each imported symbol
            for symbol_name in link.imported_symbols:
                result = self._resolve_import(link, symbol_name)

                if result:
                    definition_file, definition_symbol = result
                    # Store link_id and resolution
                    resolved.append((
                        self._get_link_id(link),
                        definition_file,
                        definition_symbol
                    ))
                    logger.debug(f"Resolved: {link.imported_module}.{symbol_name} -> {definition_file}::{definition_symbol}")

        logger.info(f"Resolved {len(resolved)}/{unresolved_count} import links")
        return resolved

    def _resolve_import(self, link: ImportLink, symbol_name: str) -> Optional[Tuple[str, str]]:
        """
        Resolve a single imported symbol to its definition.

        Args:
            link: ImportLink containing import information
            symbol_name: Name of the symbol being imported

        Returns:
            Tuple of (definition_file, definition_symbol) if resolved, else None
        """
        # Strategy 1: Direct symbol name lookup in cache
        candidates = self._symbol_cache.get(symbol_name, [])

        if not candidates:
            return None

        # Strategy 2: Try to match by module path
        module_path = self._module_to_path(link.imported_module, link.importer_file)

        for candidate in candidates:
            # Check if candidate file matches expected module path
            if self._path_matches_module(candidate.file_path, module_path, symbol_name):
                return (candidate.file_path, candidate.name)

        # Strategy 3: Fallback - if only one candidate, use it (heuristic)
        if len(candidates) == 1:
            logger.debug(f"Using single candidate for {symbol_name}: {candidates[0].file_path}")
            return (candidates[0].file_path, candidates[0].name)

        # Could not resolve
        return None

    def _module_to_path(self, module: str, importer_file: str) -> Optional[str]:
        """
        Convert module name to expected file path.

        Examples:
            "utils" -> "utils.py"
            "package.module" -> "package/module.py"
            ".local" -> "local.py" (relative to importer)

        Args:
            module: Module name from import statement
            importer_file: File that contains the import

        Returns:
            Expected file path, or None if cannot be determined
        """
        # Handle relative imports
        if module.startswith('.'):
            importer_path = Path(importer_file)
            parent_dir = importer_path.parent

            # Count dots for parent traversal
            dots = len(re.match(r'^\.+', module).group())
            remaining = module[dots:]

            # Navigate up directories
            target_dir = parent_dir
            for _ in range(dots - 1):
                target_dir = target_dir.parent

            if remaining:
                # from .module import X
                return str(target_dir / f"{remaining}.py")
            else:
                # from . import X
                return str(target_dir / "__init__.py")

        # Absolute import: convert dots to slashes
        path_parts = module.split('.')

        # Try with .py extension
        potential_paths = [
            '/'.join(path_parts) + '.py',
            '/'.join(path_parts) + '/__init__.py',
        ]

        return potential_paths[0]  # Return most likely path

    def _path_matches_module(self, candidate_path: str, expected_path: Optional[str], symbol_name: str) -> bool:
        """
        Check if a candidate file path matches expected module path.

        Args:
            candidate_path: Actual file path of symbol
            expected_path: Expected path from module conversion
            symbol_name: Name of symbol being imported

        Returns:
            True if paths match, considering various equivalences
        """
        if expected_path is None:
            return False

        # Normalize paths for comparison
        candidate = Path(candidate_path).as_posix()
        expected = Path(expected_path).as_posix()

        # Direct match
        if candidate == expected:
            return True

        # Check if candidate ends with expected (handles subdirectories)
        if candidate.endswith(expected):
            return True

        # Check stem match (filename without extension)
        if Path(candidate).stem == Path(expected).stem:
            return True

        return False

    def _get_link_id(self, link: ImportLink) -> int:
        """
        Get database ID for an ImportLink (hacky but works for now).

        In a real implementation, ImportLink would have an 'id' field.
        For now, we query by unique fields.
        """
        # Query database to get the ID
        conn = self.store._get_connection()
        try:
            cursor = conn.execute("""
                SELECT id FROM import_links
                WHERE importer_file = ? AND imported_module = ? AND import_line = ?
                LIMIT 1
            """, (link.importer_file, link.imported_module, link.import_line))

            row = cursor.fetchone()
            return row[0] if row else -1
        finally:
            conn.close()

    def update_resolved_links(self, resolved: List[Tuple[int, str, str]]):
        """
        Write resolved import links back to database.

        Args:
            resolved: List of (link_id, definition_file, definition_symbol) tuples
        """
        if not resolved:
            logger.info("No import links to update")
            return

        conn = self.store._get_connection()
        try:
            conn.executemany("""
                UPDATE import_links
                SET definition_file = ?, definition_symbol = ?
                WHERE id = ?
            """, [(def_file, def_sym, link_id) for link_id, def_file, def_sym in resolved])

            conn.commit()
            logger.info(f"Updated {len(resolved)} import links in database")
        finally:
            conn.close()
