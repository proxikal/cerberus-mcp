"""Git churn analyzer for blueprint overlays.

Phase 13.2: Analyzes git history to provide churn metrics (edits, authors, recency).
"""

import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import re

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol
from .schemas import ChurnMetrics


class ChurnAnalyzer:
    """Analyzes git blame and log data to compute churn metrics."""

    def __init__(self, repo_root: Optional[Path] = None):
        """
        Initialize churn analyzer.

        Args:
            repo_root: Root of git repository (auto-detected if None)
        """
        self.repo_root = repo_root or self._find_repo_root()
        self._cache: Dict[str, List[Tuple[int, datetime, str]]] = {}

    def _find_repo_root(self) -> Optional[Path]:
        """
        Find the git repository root.

        Returns:
            Path to .git directory's parent, or None if not in a git repo
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True
            )
            return Path(result.stdout.strip())
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("Not in a git repository - churn analysis unavailable")
            return None

    def analyze(self, symbol: CodeSymbol) -> Optional[ChurnMetrics]:
        """
        Analyze git churn for a symbol.

        Args:
            symbol: CodeSymbol to analyze

        Returns:
            ChurnMetrics or None if git data unavailable
        """
        if not self.repo_root:
            return None

        file_path = Path(symbol.file_path)
        if not file_path.exists():
            return None

        # Get blame data for the symbol's line range
        blame_data = self._get_blame_data(file_path, symbol.start_line, symbol.end_line)
        if not blame_data:
            return None

        # Compute metrics
        last_modified_ts = self._get_last_modified(blame_data)
        edit_frequency = self._get_edit_frequency(blame_data, days=7)
        unique_authors = self._get_unique_authors(blame_data)
        last_author = self._get_last_author(blame_data)

        # Format human-readable time
        last_modified_str = self._format_relative_time(last_modified_ts) if last_modified_ts else None

        return ChurnMetrics(
            last_modified=last_modified_str,
            last_modified_timestamp=last_modified_ts,
            edit_frequency=edit_frequency,
            unique_authors=len(unique_authors),
            last_author=last_author
        )

    def _get_blame_data(
        self,
        file_path: Path,
        start_line: int,
        end_line: int
    ) -> List[Tuple[int, datetime, str]]:
        """
        Get git blame data for line range.

        Args:
            file_path: File to analyze
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed)

        Returns:
            List of (line_num, commit_date, author) tuples
        """
        # Check cache
        cache_key = str(file_path)
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            # Filter to line range
            return [(ln, dt, auth) for ln, dt, auth in cached if start_line <= ln <= end_line]

        try:
            # Run git blame with porcelain format for easier parsing
            result = subprocess.run(
                [
                    "git", "blame",
                    "--porcelain",
                    str(file_path)
                ],
                capture_output=True,
                text=True,
                cwd=self.repo_root,
                check=True
            )

            # Parse porcelain output
            blame_data = self._parse_blame_porcelain(result.stdout)

            # Cache the full file data
            self._cache[cache_key] = blame_data

            # Return filtered range
            return [(ln, dt, auth) for ln, dt, auth in blame_data if start_line <= ln <= end_line]

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.warning(f"Git blame failed for {file_path}: {e}")
            return []

    def _parse_blame_porcelain(self, porcelain_output: str) -> List[Tuple[int, datetime, str]]:
        """
        Parse git blame --porcelain output.

        Format:
        <commit-hash> <original-line> <final-line> <group-lines>
        author <author-name>
        author-mail <author-email>
        author-time <unix-timestamp>
        ...
        \t<line-content>

        Returns:
            List of (line_num, commit_date, author) tuples
        """
        lines = porcelain_output.split('\n')
        result = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Header line: <hash> <orig-line> <final-line> <num-lines>
            if line and not line.startswith('\t'):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        final_line = int(parts[2])
                    except ValueError:
                        i += 1
                        continue

                    # Look ahead for author and author-time
                    author = None
                    timestamp = None

                    for j in range(i + 1, min(i + 15, len(lines))):
                        next_line = lines[j].strip()
                        if next_line.startswith('author '):
                            author = next_line[7:]  # Remove 'author ' prefix
                        elif next_line.startswith('author-time '):
                            try:
                                timestamp = int(next_line[12:])
                            except ValueError:
                                pass
                        elif next_line.startswith('\t'):
                            # Reached the content line
                            break

                    if author and timestamp:
                        commit_date = datetime.fromtimestamp(timestamp)
                        result.append((final_line, commit_date, author))

            i += 1

        return result

    def _get_last_modified(self, blame_data: List[Tuple[int, datetime, str]]) -> Optional[float]:
        """Get most recent modification timestamp."""
        if not blame_data:
            return None

        latest = max(blame_data, key=lambda x: x[1])
        return latest[1].timestamp()

    def _get_edit_frequency(self, blame_data: List[Tuple[int, datetime, str]], days: int = 7) -> int:
        """Count unique edits in the last N days."""
        if not blame_data:
            return 0

        cutoff = datetime.now() - timedelta(days=days)
        recent_commits = set()

        for _, commit_date, _ in blame_data:
            if commit_date >= cutoff:
                # Count unique days (not commits) to avoid counting refactors
                recent_commits.add(commit_date.date())

        return len(recent_commits)

    def _get_unique_authors(self, blame_data: List[Tuple[int, datetime, str]]) -> set:
        """Get set of unique authors."""
        if not blame_data:
            return set()

        return {author for _, _, author in blame_data}

    def _get_last_author(self, blame_data: List[Tuple[int, datetime, str]]) -> Optional[str]:
        """Get the most recent author."""
        if not blame_data:
            return None

        latest = max(blame_data, key=lambda x: x[1])
        return latest[2]

    def _format_relative_time(self, timestamp: float) -> str:
        """
        Format timestamp as human-readable relative time.

        Args:
            timestamp: Unix timestamp

        Returns:
            String like "2h ago", "3d ago", "5mo ago"
        """
        now = time.time()
        delta = now - timestamp

        if delta < 60:
            return "just now"
        elif delta < 3600:
            minutes = int(delta / 60)
            return f"{minutes}min ago"
        elif delta < 86400:
            hours = int(delta / 3600)
            return f"{hours}h ago"
        elif delta < 604800:
            days = int(delta / 86400)
            return f"{days}d ago"
        elif delta < 2592000:
            weeks = int(delta / 604800)
            return f"{weeks}w ago"
        elif delta < 31536000:
            months = int(delta / 2592000)
            return f"{months}mo ago"
        else:
            years = int(delta / 31536000)
            return f"{years}y ago"
