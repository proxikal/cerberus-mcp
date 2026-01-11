"""Tests for MemoryStore, Profile, and ProfileManager."""

import pytest
import tempfile
import shutil
from pathlib import Path

pytestmark = pytest.mark.memory

from cerberus.memory.store import MemoryStore
from cerberus.memory.profile import ProfileManager, Profile


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
def manager(store):
    """Create a ProfileManager with temp store."""
    return ProfileManager(store)


class TestMemoryStore:
    """Tests for MemoryStore."""

    def test_directory_creation(self, temp_memory_dir):
        """Store should create directory structure."""
        store = MemoryStore(base_path=temp_memory_dir)
        assert temp_memory_dir.exists()
        assert (temp_memory_dir / 'prompts').exists()
        assert (temp_memory_dir / 'projects').exists()

    def test_read_nonexistent_file(self, store):
        """Reading non-existent file should return None."""
        result = store.read_json(store.profile_path)
        assert result is None

    def test_write_and_read_json(self, store):
        """Should write and read JSON correctly."""
        data = {"key": "value", "nested": {"a": 1}}
        assert store.write_json(store.profile_path, data)

        result = store.read_json(store.profile_path)
        assert result == data

    def test_size_limit_enforcement(self, store):
        """Should reject writes that exceed size limit."""
        large_data = {"content": "x" * 2000}

        result = store.write_json(
            store.profile_path,
            large_data,
            check_size=True,
            max_size=1024
        )
        assert result is False

    def test_atomic_write(self, store):
        """Writes should be atomic (no partial writes)."""
        data = {"test": "data"}
        store.write_json(store.profile_path, data)

        result = store.read_json(store.profile_path)
        assert result == data

    def test_list_projects(self, store):
        """Should list project files."""
        store.write_json(store.project_path("project1"), {"name": "p1"})
        store.write_json(store.project_path("project2"), {"name": "p2"})

        projects = store.list_projects()
        assert "project1" in projects
        assert "project2" in projects
        assert len(projects) == 2

    def test_storage_stats(self, store):
        """Should return storage statistics."""
        stats = store.get_storage_stats()

        assert 'base_path' in stats
        assert 'profile_exists' in stats
        assert 'project_count' in stats


class TestProfile:
    """Tests for Profile dataclass."""

    def test_to_dict(self):
        """Should convert to dict correctly."""
        profile = Profile(
            coding_style={"early_returns": True},
            anti_patterns=["bad thing"]
        )
        data = profile.to_dict()

        assert "$schema" in data
        assert data["coding_style"]["early_returns"] is True
        assert "bad thing" in data["anti_patterns"]

    def test_from_dict(self):
        """Should create from dict correctly."""
        data = {
            "$schema": "profile-v1",
            "coding_style": {"max_line_length": 80},
            "anti_patterns": ["avoid this"],
            "naming_conventions": {},
            "languages": {},
            "general": []
        }
        profile = Profile.from_dict(data)

        assert profile.coding_style["max_line_length"] == 80
        assert "avoid this" in profile.anti_patterns

    def test_is_empty(self):
        """Should detect empty profiles."""
        empty_profile = Profile()
        assert empty_profile.is_empty()

        non_empty = Profile(coding_style={"key": "value"})
        assert not non_empty.is_empty()


class TestProfileManager:
    """Tests for ProfileManager."""

    def test_empty_profile(self, manager):
        """New profile should be empty."""
        profile = manager.load_profile()
        assert profile.is_empty()

    def test_learn_early_returns(self, manager):
        """Should learn early returns preference."""
        result = manager.learn("prefer early returns")

        assert result["success"]
        assert result["category"] == "coding_style"
        assert result["key"] == "prefer_early_returns"
        assert result["value"] is True

        profile = manager.load_profile()
        assert profile.coding_style.get("prefer_early_returns") is True

    def test_learn_async_await(self, manager):
        """Should learn async/await preference."""
        result = manager.learn("always use async/await")

        assert result["success"]
        assert result["key"] == "async_style"
        assert result["value"] == "async_await"

    def test_learn_line_length(self, manager):
        """Should learn max line length."""
        result = manager.learn("max line length 100")

        assert result["success"]
        assert result["key"] == "max_line_length"
        assert result["value"] == 100

    def test_learn_anti_pattern(self, manager):
        """Should learn anti-patterns."""
        result = manager.learn("never use any type")

        assert result["success"]
        assert result["category"] == "anti_patterns"

        profile = manager.load_profile()
        assert len(profile.anti_patterns) == 1

    def test_learn_naming_convention(self, manager):
        """Should learn naming conventions."""
        result = manager.learn("components use PascalCase")

        assert result["success"]
        assert result["category"] == "naming_conventions"
        assert result["key"] == "components"
        assert result["value"] == "PascalCase"

    def test_learn_general_preference(self, manager):
        """Should store unrecognized patterns as general preferences."""
        result = manager.learn("prefer functional programming style")

        assert result["success"]
        assert result["category"] == "general"

        profile = manager.load_profile()
        assert "prefer functional programming style" in profile.general

    def test_forget_preference(self, manager):
        """Should remove preferences."""
        manager.learn("prefer early returns")
        result = manager.forget("early_returns")

        assert result["success"]

        profile = manager.load_profile()
        assert "prefer_early_returns" not in profile.coding_style

    def test_duplicate_prevention(self, manager):
        """Should not add duplicate preferences."""
        manager.learn("prefer early returns")
        result = manager.learn("early returns over nested conditionals")

        assert result["success"]

        profile = manager.load_profile()
        assert profile.coding_style.get("prefer_early_returns") is True
