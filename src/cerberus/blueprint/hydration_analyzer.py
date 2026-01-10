"""Auto-hydration analyzer for smart dependency inclusion.

Phase 13.5: Automatically includes mini-blueprints of heavily-referenced internal files.
"""

import sqlite3
from collections import Counter
from pathlib import Path
from typing import List, Set, Optional, Tuple
import sys

from cerberus.logging_config import logger
from .schemas import Blueprint, BlueprintNode, DependencyInfo


class HydrationAnalyzer:
    """Analyzes dependencies to determine which files should be auto-hydrated."""

    # Thresholds
    MIN_REFERENCES_THRESHOLD = 3  # Minimum references to trigger hydration
    MAX_HYDRATED_TOKENS = 2000    # Maximum total tokens for hydrated content
    APPROX_TOKENS_PER_SYMBOL = 40 # Rough estimate: symbol name + signature

    def __init__(
        self,
        conn: sqlite3.Connection,
        project_root: Optional[Path] = None
    ):
        """
        Initialize hydration analyzer.

        Args:
            conn: SQLite connection to database
            project_root: Project root directory (for internal file detection)
        """
        self.conn = conn
        self.project_root = project_root or Path.cwd()
        
    def analyze_for_hydration(
        self,
        blueprint: Blueprint,
        max_hydrated_files: int = 5
    ) -> List[str]:
        """
        Analyze blueprint to determine which files should be auto-hydrated.

        Args:
            blueprint: Main blueprint to analyze
            max_hydrated_files: Maximum number of files to hydrate

        Returns:
            List of file paths that should be hydrated
        """
        # Count references to external files
        file_references = self._count_file_references(blueprint)
        
        if not file_references:
            logger.debug("No external file references found for hydration")
            return []
        
        # Filter for internal files with sufficient references
        candidates = []
        for file_path, ref_count in file_references.items():
            if ref_count >= self.MIN_REFERENCES_THRESHOLD:
                if self._is_internal_file(file_path):
                    candidates.append((file_path, ref_count))
        
        if not candidates:
            logger.debug("No hydration candidates found")
            return []
        
        # Sort by reference count (most referenced first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Select files to hydrate while staying under token budget
        selected_files = []
        estimated_tokens = 0
        
        for file_path, ref_count in candidates[:max_hydrated_files]:
            # Estimate token cost for this file
            symbol_count = self._estimate_symbol_count(file_path)
            file_tokens = symbol_count * self.APPROX_TOKENS_PER_SYMBOL
            
            # Check if adding this file would exceed budget
            if estimated_tokens + file_tokens > self.MAX_HYDRATED_TOKENS:
                logger.debug(
                    f"Skipping {file_path} for hydration: "
                    f"would exceed token budget ({estimated_tokens + file_tokens} > {self.MAX_HYDRATED_TOKENS})"
                )
                break
            
            selected_files.append(file_path)
            estimated_tokens += file_tokens
            logger.debug(
                f"Selected {file_path} for hydration "
                f"({ref_count} refs, ~{file_tokens} tokens)"
            )
        
        return selected_files

    def _count_file_references(self, blueprint: Blueprint) -> Counter:
        """
        Count references to external files from blueprint dependencies.

        Args:
            blueprint: Blueprint to analyze

        Returns:
            Counter mapping file paths to reference counts
        """
        file_refs = Counter()
        
        def count_node_refs(node: BlueprintNode):
            """Recursively count references in node and children."""
            if node.overlay.dependencies:
                for dep in node.overlay.dependencies:
                    # Only count if we have a target file and it's not the source file
                    if dep.target_file and dep.target_file != blueprint.file_path:
                        file_refs[dep.target_file] += 1
            
            # Recurse into children
            for child in node.children:
                count_node_refs(child)
        
        # Count references in all top-level nodes
        for node in blueprint.nodes:
            count_node_refs(node)
        
        return file_refs

    def _is_internal_file(self, file_path: str) -> bool:
        """
        Determine if a file is internal (project code) vs external (stdlib/third-party).

        Args:
            file_path: Absolute file path

        Returns:
            True if file is internal project code
        """
        path = Path(file_path)
        
        # Check if file is under project root
        try:
            path.relative_to(self.project_root)
            is_under_root = True
        except ValueError:
            is_under_root = False
        
        if not is_under_root:
            return False
        
        # Exclude common third-party and stdlib locations
        path_str = str(path).lower()
        excluded_patterns = [
            'site-packages',
            'dist-packages',
            '/lib/python',
            '/lib64/python',
            '.venv',
            'venv',
            'virtualenv',
            '__pycache__',
        ]
        
        for pattern in excluded_patterns:
            if pattern in path_str:
                return False
        
        # Check if it's a stdlib module (common Python stdlib paths)
        try:
            # Get Python's stdlib path
            stdlib_paths = set()
            for path_item in sys.path:
                if 'site-packages' not in path_item and 'dist-packages' not in path_item:
                    stdlib_paths.add(Path(path_item).resolve())
            
            # Check if file is under any stdlib path
            for stdlib_path in stdlib_paths:
                try:
                    path.relative_to(stdlib_path)
                    return False  # It's in stdlib
                except ValueError:
                    continue
        except Exception:
            pass
        
        return True

    def _estimate_symbol_count(self, file_path: str) -> int:
        """
        Estimate number of symbols in a file.

        Args:
            file_path: File to estimate

        Returns:
            Estimated symbol count
        """
        try:
            cursor = self.conn.execute(
                "SELECT COUNT(*) FROM symbols WHERE file_path = ?",
                (file_path,)
            )
            count = cursor.fetchone()[0]
            return count
        except Exception as e:
            logger.warning(f"Error estimating symbols for {file_path}: {e}")
            return 10  # Default estimate
