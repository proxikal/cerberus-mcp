"""Tests for ContextGenerator and context generation with all data types."""

import pytest
import tempfile
import shutil
from pathlib import Path

pytestmark = pytest.mark.memory

from cerberus.memory.store import MemoryStore
from cerberus.memory.profile import ProfileManager
from cerberus.memory.context import ContextGenerator
from cerberus.memory.decisions import DecisionManager
from cerberus.memory.corrections import CorrectionManager
from cerberus.memory.prompts import PromptManager


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


@pytest.fixture
def generator(store):
    """Create a ContextGenerator with temp store."""
    return ContextGenerator(store)


@pytest.fixture
def decision_manager(store):
    """Create a DecisionManager with temp store."""
    return DecisionManager(store)


@pytest.fixture
def correction_manager(store):
    """Create a CorrectionManager with temp store."""
    return CorrectionManager(store)


@pytest.fixture
def prompt_manager(store):
    """Create a PromptManager with temp store."""
    return PromptManager(store)


class TestContextGenerator:
    """Tests for ContextGenerator."""

    def test_empty_context(self, generator):
        """Should generate helpful message for empty profile."""
        context = generator.generate_context()

        assert "No preferences stored" in context
        assert "cerberus memory learn" in context

    def test_profile_context(self, generator, manager):
        """Should generate context from profile."""
        manager.learn("prefer early returns")
        manager.learn("max line length 100")

        context = generator.generate_context()

        assert "Developer Context" in context
        assert "Early returns" in context
        assert "100" in context

    def test_context_size_limit(self, generator, manager):
        """Context should stay under 50 lines for profile only."""
        manager.learn("prefer early returns")
        manager.learn("always use async/await")
        manager.learn("max line length 100")
        manager.learn("never use any type")
        manager.learn("components use PascalCase")

        context = generator.generate_profile_context()
        lines = context.split('\n')

        assert len(lines) <= ContextGenerator.MAX_PROFILE_LINES

    def test_compact_mode(self, generator, manager):
        """Compact mode should produce fewer lines."""
        manager.learn("prefer early returns")
        manager.learn("max line length 100")

        normal = generator.generate_context(compact=False)
        compact = generator.generate_context(compact=True)

        assert len(compact.split('\n')) <= len(normal.split('\n'))

    def test_context_stats(self, generator, manager):
        """Should return accurate context statistics."""
        manager.learn("prefer early returns")

        stats = generator.get_context_stats()

        assert stats['context_bytes'] > 0
        assert stats['context_lines'] > 0
        assert stats['under_limit'] is True


class TestContextWithDecisionsAndCorrections:
    """Tests for context generation with decisions and corrections."""

    def test_context_includes_decisions(self, generator, decision_manager):
        """Context should include project decisions."""
        decision_manager.learn_decision("chose SQLite", project="test-proj")

        context = generator.generate_context(project="test-proj")

        assert "test-proj" in context
        assert "SQLite" in context

    def test_context_includes_corrections(self, generator, correction_manager):
        """Context should include corrections."""
        correction_manager.learn_correction("always log errors", note="Log before throw")

        context = generator.generate_context()

        assert "Corrections" in context
        assert "Log before throw" in context

    def test_context_under_100_lines(self, generator, manager, decision_manager, correction_manager):
        """Full context with decisions/corrections should be under 100 lines."""
        manager.learn("prefer early returns")
        manager.learn("max line length 100")

        for i in range(5):
            decision_manager.learn_decision(f"Decision {i}: Choice {i}", project="test")

        for i in range(5):
            correction_manager.learn_correction(f"pattern {i} -> fix {i}", note=f"Note {i}")

        context = generator.generate_context(project="test")
        lines = context.split('\n')

        assert len(lines) < 100

    def test_context_stats_includes_all_data(self, generator, manager, decision_manager, correction_manager):
        """Context stats should account for all stored data."""
        manager.learn("prefer early returns")
        decision_manager.learn_decision("chose X", project="test")
        correction_manager.learn_correction("pattern", note="fix")

        stats = generator.get_context_stats()

        assert stats["stored_bytes"] > 0
        assert stats["context_bytes"] > 0
        assert stats["under_limit"]


class TestContextWithPrompts:
    """Tests for context generation with prompts."""

    def test_context_includes_prompts_for_task(self, generator, prompt_manager):
        """Context should include prompts when task is specified."""
        prompt_manager.learn_prompt(
            name="security",
            task_type="code-review",
            description="Check OWASP",
        )

        context = generator.generate_context(task="code-review")

        assert "security" in context
        assert "Code Review" in context

    def test_context_without_task_excludes_prompts(self, generator, prompt_manager):
        """Context should not include prompts when no task specified."""
        prompt_manager.learn_prompt(
            name="security",
            task_type="code-review",
            description="Check OWASP",
        )

        context = generator.generate_context()

        assert "For Code Review" not in context

    def test_full_context_under_150_lines(self, generator, manager, decision_manager, correction_manager, prompt_manager):
        """Full context must be under 150 lines."""
        manager.learn("prefer early returns")

        for i in range(5):
            decision_manager.learn_decision(f"Decision {i}", project="test")

        for i in range(5):
            correction_manager.learn_correction(f"correction {i}")

        for i in range(3):
            prompt_manager.learn_prompt(name=f"prompt-{i}", task_type="code-review")

        context = generator.generate_context(project="test", task="code-review")
        lines = context.split('\n')

        assert len(lines) < 150
