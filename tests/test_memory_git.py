"""Tests for GitExtractor."""

import pytest
import tempfile
import shutil
from pathlib import Path

pytestmark = pytest.mark.memory

from cerberus.memory.store import MemoryStore
from cerberus.memory.extract import GitExtractor


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for memory storage."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def store(temp_memory_dir):
    """Create a MemoryStore with temp directory."""
    return MemoryStore(base_path=temp_memory_dir)


@pytest.fixture
def git_extractor(store):
    """Create a GitExtractor with temp store."""
    return GitExtractor(store)


class TestGitExtractor:
    """Tests for GitExtractor."""

    def test_extract_decision_pattern(self, git_extractor):
        """Should extract decisions from commit messages."""
        result = git_extractor._extract_decision(
            "chose SQLite for portability",
            "abc123"
        )

        assert result is not None
        assert "SQLite" in result["content"].lower() or "chose" in result["content"].lower()

    def test_extract_correction_pattern(self, git_extractor):
        """Should extract corrections from commit messages."""
        result = git_extractor._extract_correction(
            "fix: always log errors before throwing",
            "abc123"
        )

        assert result is not None
        assert "log" in result["content"].lower() or "error" in result["content"].lower()

    def test_should_skip_merge_commits(self, git_extractor):
        """Should skip merge commits."""
        assert git_extractor._should_skip("Merge branch 'main' into develop")
        assert git_extractor._should_skip("merge pull request #123")

    def test_should_skip_wip_commits(self, git_extractor):
        """Should skip WIP commits."""
        assert git_extractor._should_skip("wip: unfinished work")
        assert git_extractor._should_skip("WIP stuff")
