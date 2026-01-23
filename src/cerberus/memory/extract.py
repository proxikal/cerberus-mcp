"""
Git Extraction Module (Phase 18.3)

Extracts patterns from git history to learn developer preferences.
Analyzes commit messages for decision patterns and coding conventions.

Key features:
- Extract decisions from commit messages
- Detect coding patterns from diffs
- Suggest corrections from repeated fixes
"""

import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from cerberus.logging_config import logger


@dataclass
class ExtractedPattern:
    """A pattern extracted from git history."""
    type: str  # "decision", "correction", "preference"
    content: str
    source: str  # commit hash or file
    confidence: float  # 0.0 to 1.0
    frequency: int = 1


class GitExtractor:
    """
    Extracts patterns from git history.

    Analyzes:
    - Commit messages for decisions (keywords: chose, decided, using, prefer)
    - Repeated fixes for corrections
    - Code patterns for style preferences
    """

    # Decision keywords in commit messages
    DECISION_PATTERNS = [
        r"(?:chose|choose|decided|decision|switch(?:ed)?(?:\s+to)?|use|using|prefer|adopt(?:ed)?)\s+(.+?)(?:\s+(?:over|instead|for|because)(.+))?$",
        r"(?:migrate|migrated|refactor|refactored)\s+(?:to|from)\s+(.+)",
        r"replace(?:d)?\s+(.+?)\s+with\s+(.+)",
    ]

    # Correction keywords (indicate fixing a mistake)
    CORRECTION_PATTERNS = [
        r"(?:fix|fixed|fixup|correct|corrected)\s*:?\s*(.+)",
        r"(?:always|never|should|must)\s+(.+)",
        r"(?:forgot|forgotten|missing)\s+(.+)",
    ]

    # Skip patterns (not useful for extraction)
    SKIP_PATTERNS = [
        r"^merge\s+",
        r"^wip\s*:?",  # WIP with or without colon
        r"^temp\s*:",
        r"^\d+\.\d+",  # Version numbers
    ]

    def __init__(self, storage: Optional['MemoryStorage'] = None):
        """
        Initialize the git extractor.

        Args:
            storage: MemoryStorage instance (creates default if not provided)
        """
        from cerberus.memory.storage import MemoryStorage
        from cerberus.memory.proposal_engine import MemoryProposal

        self.storage = storage or MemoryStorage()
        self._MemoryProposal = MemoryProposal

    def _detect_project_name(self) -> Optional[str]:
        """
        Detect project name from git repository or current directory.

        Returns:
            Project name or None if not in a git repo
        """
        try:
            # Try to get git repo name
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                from pathlib import Path
                repo_path = Path(result.stdout.strip())
                return repo_path.name
        except Exception:
            pass

        return None

    def extract_from_git(
        self,
        since: Optional[str] = None,
        max_commits: int = 100,
        project: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract patterns from git history.

        Args:
            since: Git date string (e.g., "1 week ago", "2024-01-01")
            max_commits: Maximum number of commits to analyze
            project: Project name (auto-detected if not provided)

        Returns:
            Dict with extracted 'decisions', 'corrections', 'summary'
        """
        # Get project name
        if project is None:
            project = self._detect_project_name()
            if project is None:
                return {
                    "success": False,
                    "message": "Not in a git repository",
                }

        # Get commit messages
        commits = self._get_commits(since, max_commits)
        if not commits:
            return {
                "success": True,
                "project": project,
                "decisions": [],
                "corrections": [],
                "summary": {"commits_analyzed": 0, "patterns_found": 0},
            }

        # Extract patterns
        decisions = []
        corrections = []

        for commit_hash, message in commits:
            # Skip noise
            if self._should_skip(message):
                continue

            # Try to extract decision
            decision = self._extract_decision(message, commit_hash)
            if decision:
                decisions.append(decision)

            # Try to extract correction
            correction = self._extract_correction(message, commit_hash)
            if correction:
                corrections.append(correction)

        return {
            "success": True,
            "project": project,
            "decisions": decisions,
            "corrections": corrections,
            "summary": {
                "commits_analyzed": len(commits),
                "patterns_found": len(decisions) + len(corrections),
                "decisions_found": len(decisions),
                "corrections_found": len(corrections),
            },
        }

    def learn_from_git(
        self,
        since: Optional[str] = None,
        max_commits: int = 100,
        project: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Extract patterns and learn them into Session Memory using SQLite.

        Args:
            since: Git date string (e.g., "1 week ago")
            max_commits: Maximum commits to analyze
            project: Project name
            dry_run: If True, don't actually save

        Returns:
            Dict with learned items and summary
        """
        import uuid

        extraction = self.extract_from_git(since, max_commits, project)
        if not extraction["success"]:
            return extraction

        project = extraction["project"]
        learned_decisions = []
        learned_corrections = []

        # Learn decisions using new SQLite storage
        for pattern in extraction["decisions"]:
            if dry_run:
                learned_decisions.append(pattern)
            else:
                try:
                    proposal = self._MemoryProposal(
                        id=str(uuid.uuid4()),
                        category="decision",
                        scope=f"project:{project}",
                        content=pattern["content"],
                        rationale=f"Extracted from git commit {pattern['source'][:7]}",
                        source_variants=[],
                        confidence=pattern["confidence"],
                        priority=3
                    )
                    self.storage.store(proposal)
                    learned_decisions.append(pattern)
                except Exception as e:
                    logger.debug(f"Failed to store decision: {e}")

        # Learn corrections using new SQLite storage
        for pattern in extraction["corrections"]:
            if dry_run:
                learned_corrections.append(pattern)
            else:
                try:
                    proposal = self._MemoryProposal(
                        id=str(uuid.uuid4()),
                        category="correction",
                        scope="universal",
                        content=pattern["content"],
                        rationale=f"Extracted from git commit {pattern['source'][:7]}",
                        source_variants=[],
                        confidence=pattern["confidence"],
                        priority=3
                    )
                    self.storage.store(proposal)
                    learned_corrections.append(pattern)
                except Exception as e:
                    logger.debug(f"Failed to store correction: {e}")

        return {
            "success": True,
            "project": project,
            "dry_run": dry_run,
            "learned_decisions": learned_decisions,
            "learned_corrections": learned_corrections,
            "summary": {
                "commits_analyzed": extraction["summary"]["commits_analyzed"],
                "decisions_learned": len(learned_decisions),
                "corrections_learned": len(learned_corrections),
            },
        }

    def _get_commits(
        self,
        since: Optional[str],
        max_commits: int,
    ) -> List[Tuple[str, str]]:
        """
        Get commits from git log.

        Returns:
            List of (commit_hash, message) tuples
        """
        cmd = ["git", "log", f"-{max_commits}", "--pretty=format:%H|%s"]

        if since:
            cmd.append(f"--since={since}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                logger.debug(f"Git log failed: {result.stderr}")
                return []

            commits = []
            for line in result.stdout.strip().split('\n'):
                if '|' in line:
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        commits.append((parts[0], parts[1]))

            return commits

        except Exception as e:
            logger.debug(f"Error getting git commits: {e}")
            return []

    def _should_skip(self, message: str) -> bool:
        """Check if a commit message should be skipped."""
        message_lower = message.lower()
        for pattern in self.SKIP_PATTERNS:
            if re.match(pattern, message_lower, re.IGNORECASE):
                return True
        return False

    def _extract_decision(
        self,
        message: str,
        commit_hash: str,
    ) -> Optional[Dict[str, Any]]:
        """Try to extract a decision from a commit message."""
        message_lower = message.lower()

        for pattern in self.DECISION_PATTERNS:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                # Clean up the extracted content
                content = match.group(0).strip()
                if len(content) > 20:  # Minimum meaningful length
                    return {
                        "type": "decision",
                        "content": content,
                        "source": commit_hash,
                        "confidence": 0.7,
                    }

        return None

    def _extract_correction(
        self,
        message: str,
        commit_hash: str,
    ) -> Optional[Dict[str, Any]]:
        """Try to extract a correction pattern from a commit message."""
        message_lower = message.lower()

        for pattern in self.CORRECTION_PATTERNS:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                content = match.group(1).strip() if match.groups() else match.group(0)
                if len(content) > 10:  # Minimum meaningful length
                    return {
                        "type": "correction",
                        "content": content,
                        "source": commit_hash,
                        "confidence": 0.6,
                    }

        return None

    def analyze_repeated_fixes(
        self,
        since: Optional[str] = None,
        min_frequency: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Analyze git history for repeated fix patterns.

        Args:
            since: Git date string
            min_frequency: Minimum times a pattern must occur

        Returns:
            List of repeated patterns with frequency
        """
        commits = self._get_commits(since, max_commits=500)

        # Count fix patterns
        fix_counts: Dict[str, int] = {}
        for _, message in commits:
            correction = self._extract_correction(message, "")
            if correction:
                key = correction["content"].lower()[:50]  # Normalize
                fix_counts[key] = fix_counts.get(key, 0) + 1

        # Filter by frequency
        repeated = [
            {"pattern": pattern, "frequency": count}
            for pattern, count in fix_counts.items()
            if count >= min_frequency
        ]

        return sorted(repeated, key=lambda x: x["frequency"], reverse=True)
