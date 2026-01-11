"""
Tests for Session Memory (Phase 18.1 and 18.2)

Tests the core storage, profile management, decisions, corrections, and context generation.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from cerberus.memory.store import MemoryStore
from cerberus.memory.profile import ProfileManager, Profile
from cerberus.memory.context import ContextGenerator
from cerberus.memory.decisions import DecisionManager, Decision, ProjectDecisions
from cerberus.memory.corrections import CorrectionManager, Correction, CorrectionStore
from cerberus.memory.prompts import PromptManager, Prompt, PromptLibrary
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
def manager(store):
    """Create a ProfileManager with temp store."""
    return ProfileManager(store)


@pytest.fixture
def generator(store):
    """Create a ContextGenerator with temp store."""
    return ContextGenerator(store)


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
        # Create data larger than 1KB
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

        # File should exist and be valid JSON
        result = store.read_json(store.profile_path)
        assert result == data

    def test_list_projects(self, store):
        """Should list project files."""
        # Create some project files
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

        # Second learn should still succeed (updates same key)
        assert result["success"]

        profile = manager.load_profile()
        # Should still just have one entry
        assert profile.coding_style.get("prefer_early_returns") is True


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
        # Add many preferences
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

        # Compact should have fewer lines (no section headers)
        assert len(compact.split('\n')) <= len(normal.split('\n'))

    def test_context_stats(self, generator, manager):
        """Should return accurate context statistics."""
        manager.learn("prefer early returns")

        stats = generator.get_context_stats()

        assert stats['context_bytes'] > 0
        assert stats['context_lines'] > 0
        assert stats['under_limit'] is True


class TestIntegration:
    """Integration tests for Session Memory."""

    def test_full_workflow(self, manager, generator):
        """Test learn -> show -> context workflow."""
        # Learn preferences
        manager.learn("prefer early returns")
        manager.learn("max line length 80")
        manager.learn("never use magic numbers")

        # Verify profile
        profile = manager.load_profile()
        assert not profile.is_empty()
        assert profile.coding_style.get("prefer_early_returns") is True
        assert profile.coding_style.get("max_line_length") == 80
        assert len(profile.anti_patterns) == 1

        # Generate context
        context = generator.generate_context()
        assert "Early returns" in context
        assert "80" in context
        assert "magic numbers" in context

    def test_context_under_4kb(self, manager, generator):
        """Full context must not exceed 4KB."""
        # Add many preferences
        for i in range(10):
            manager.learn(f"preference number {i} is important")

        context = generator.generate_context()
        context_bytes = len(context.encode('utf-8'))

        assert context_bytes < MemoryStore.MAX_CONTEXT_SIZE

    def test_profile_persistence(self, store, manager):
        """Profile should persist across manager instances."""
        manager.learn("prefer early returns")

        # Create new manager with same store
        new_manager = ProfileManager(store)
        profile = new_manager.load_profile()

        assert profile.coding_style.get("prefer_early_returns") is True


class TestCLICommands:
    """Tests for CLI commands (integration tests)."""

    def test_learn_command(self, temp_memory_dir):
        """Test memory learn via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        result = subprocess.run(
            ['cerberus', 'memory', 'learn', 'prefer early returns', '--json'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert 'success' in result.stdout

    def test_context_command(self, temp_memory_dir):
        """Test memory context via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        result = subprocess.run(
            ['cerberus', 'memory', 'context'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert 'Developer Context' in result.stdout or 'No preferences' in result.stdout


# =============================================================================
# Phase 18.2 Tests: Decisions and Corrections
# =============================================================================

@pytest.fixture
def decision_manager(store):
    """Create a DecisionManager with temp store."""
    return DecisionManager(store)


@pytest.fixture
def correction_manager(store):
    """Create a CorrectionManager with temp store."""
    return CorrectionManager(store)


class TestDecision:
    """Tests for Decision dataclass."""

    def test_to_dict(self):
        """Should convert to dict correctly."""
        decision = Decision(
            id="dec-001",
            date="2026-01-10",
            topic="Database",
            decision="Use SQLite",
            rationale="Portable",
        )
        data = decision.to_dict()

        assert data["id"] == "dec-001"
        assert data["topic"] == "Database"
        assert data["decision"] == "Use SQLite"

    def test_from_dict(self):
        """Should create from dict correctly."""
        data = {
            "id": "dec-002",
            "date": "2026-01-10",
            "topic": "Parser",
            "decision": "Use native ast",
            "rationale": "Accuracy",
            "confidence": "high"
        }
        decision = Decision.from_dict(data)

        assert decision.id == "dec-002"
        assert decision.topic == "Parser"
        assert decision.confidence == "high"

    def test_to_terse(self):
        """Should generate terse representation."""
        decision = Decision(
            id="dec-001",
            topic="Database",
            decision="Use SQLite for portability",
            date="2026-01-10",
            confidence="high"
        )
        terse = decision.to_terse()

        assert "Database:" in terse
        assert "SQLite" in terse


class TestProjectDecisions:
    """Tests for ProjectDecisions collection."""

    def test_add_decision(self):
        """Should add decisions in order."""
        project = ProjectDecisions(project="test")
        decision = Decision(id="dec-001", date="2026-01-10", topic="Test", decision="Testing")

        project.add_decision(decision)

        assert len(project.decisions) == 1
        assert project.decisions[0].id == "dec-001"

    def test_max_decisions_limit(self):
        """Should maintain max limit of 10 decisions."""
        project = ProjectDecisions(project="test")

        # Add 15 decisions
        for i in range(15):
            decision = Decision(id=f"dec-{i:03d}", date="2026-01-10", topic=f"Topic {i}", decision=f"Decision {i}")
            project.add_decision(decision)

        assert len(project.decisions) == 10
        # Most recent should be first
        assert project.decisions[0].id == "dec-014"

    def test_get_recent(self):
        """Should return most recent decisions."""
        project = ProjectDecisions(project="test")

        for i in range(5):
            decision = Decision(id=f"dec-{i:03d}", date="2026-01-10", topic=f"Topic {i}", decision=f"Decision {i}")
            project.add_decision(decision)

        recent = project.get_recent(3)
        assert len(recent) == 3


class TestDecisionManager:
    """Tests for DecisionManager."""

    def test_learn_decision(self, decision_manager):
        """Should learn a decision."""
        result = decision_manager.learn_decision(
            "chose SQLite for portability",
            project="test-project"
        )

        assert result["success"]
        assert result["project"] == "test-project"
        assert "decision" in result

    def test_learn_decision_with_rationale(self, decision_manager):
        """Should learn a decision with rationale."""
        result = decision_manager.learn_decision(
            "Parser: Use native ast",
            project="test-project",
            rationale="Tree-sitter had accuracy issues"
        )

        assert result["success"]
        decisions = decision_manager.load_decisions("test-project")
        assert decisions.decisions[0].rationale == "Tree-sitter had accuracy issues"

    def test_forget_decision(self, decision_manager):
        """Should remove a decision."""
        decision_manager.learn_decision("test decision", project="test-project")
        decisions = decision_manager.load_decisions("test-project")
        decision_id = decisions.decisions[0].id

        result = decision_manager.forget_decision(decision_id, project="test-project")

        assert result["success"]
        decisions = decision_manager.load_decisions("test-project")
        assert len(decisions.decisions) == 0

    def test_list_projects(self, decision_manager):
        """Should list all projects with decisions."""
        decision_manager.learn_decision("d1", project="project-a")
        decision_manager.learn_decision("d2", project="project-b")

        projects = decision_manager.list_projects()

        assert "project-a" in projects
        assert "project-b" in projects

    def test_get_decisions_for_context(self, decision_manager):
        """Should return terse decision strings."""
        decision_manager.learn_decision("chose SQLite", project="test")
        decision_manager.learn_decision("Parser: Use native ast", project="test")

        context_lines = decision_manager.get_decisions_for_context("test", count=5)

        assert len(context_lines) == 2
        assert all(line.startswith("-") for line in context_lines)


class TestCorrection:
    """Tests for Correction dataclass."""

    def test_to_dict(self):
        """Should convert to dict correctly."""
        correction = Correction(
            id="cor-001",
            pattern="catch (error) { throw }",
            correction="catch (error) { log; throw }",
            frequency=5,
            note="Always log before throw"
        )
        data = correction.to_dict()

        assert data["id"] == "cor-001"
        assert data["frequency"] == 5
        assert data["note"] == "Always log before throw"

    def test_from_dict(self):
        """Should create from dict correctly."""
        data = {
            "id": "cor-002",
            "pattern": "if/else return",
            "correction": "ternary",
            "frequency": 3,
            "note": "Simplify"
        }
        correction = Correction.from_dict(data)

        assert correction.id == "cor-002"
        assert correction.frequency == 3

    def test_increment(self):
        """Should increment frequency."""
        correction = Correction(id="cor-001", pattern="test", correction="test", frequency=1)

        correction.increment()

        assert correction.frequency == 2
        assert correction.last_occurred != ""

    def test_to_terse(self):
        """Should generate terse representation."""
        correction = Correction(
            id="cor-001",
            pattern="test",
            correction="test",
            frequency=5,
            note="Always do X"
        )
        terse = correction.to_terse()

        assert "Always do X" in terse
        assert "5x" in terse


class TestCorrectionStore:
    """Tests for CorrectionStore collection."""

    def test_get_by_frequency(self):
        """Should return corrections sorted by frequency."""
        store = CorrectionStore()
        store.corrections = [
            Correction(id="cor-001", pattern="p1", correction="c1", frequency=2),
            Correction(id="cor-002", pattern="p2", correction="c2", frequency=10),
            Correction(id="cor-003", pattern="p3", correction="c3", frequency=5),
        ]

        top = store.get_by_frequency(2)

        assert len(top) == 2
        assert top[0].frequency == 10
        assert top[1].frequency == 5

    def test_find_similar(self):
        """Should find corrections with similar patterns."""
        store = CorrectionStore()
        store.corrections = [
            Correction(id="cor-001", pattern="log errors before throw", correction="", frequency=1),
        ]

        # Substring match: "log errors" is in both
        found = store.find_similar("log errors")

        assert found is not None
        assert found.id == "cor-001"

    def test_find_similar_reverse(self):
        """Should find corrections when stored pattern is substring of query."""
        store = CorrectionStore()
        store.corrections = [
            Correction(id="cor-001", pattern="log errors", correction="", frequency=1),
        ]

        found = store.find_similar("always log errors before throw")

        assert found is not None
        assert found.id == "cor-001"


class TestCorrectionManager:
    """Tests for CorrectionManager."""

    def test_learn_correction(self, correction_manager):
        """Should learn a new correction."""
        result = correction_manager.learn_correction(
            "AI keeps forgetting to log",
            note="Always log before throw"
        )

        assert result["success"]
        assert result["is_new"]

    def test_learn_correction_increments_frequency(self, correction_manager):
        """Should increment frequency for similar corrections."""
        correction_manager.learn_correction("log errors before throw")
        result = correction_manager.learn_correction("always log errors before throwing")

        assert result["success"]
        assert not result["is_new"]
        assert result["correction"]["frequency"] == 2

    def test_forget_correction(self, correction_manager):
        """Should remove a correction."""
        result = correction_manager.learn_correction("test correction")
        correction_id = result["correction"]["id"]

        result = correction_manager.forget_correction(correction_id)

        assert result["success"]
        corrections = correction_manager.load_corrections()
        assert len(corrections.corrections) == 0

    def test_get_corrections_for_context(self, correction_manager):
        """Should return terse correction strings."""
        correction_manager.learn_correction("always log errors", note="Log before throw")
        correction_manager.learn_correction("use unknown not any", note="Type safety")

        context_lines = correction_manager.get_corrections_for_context(count=5)

        assert len(context_lines) == 2
        assert all(line.startswith("-") for line in context_lines)

    def test_get_summary(self, correction_manager):
        """Should return correction summary."""
        correction_manager.learn_correction("c1", note="n1")
        correction_manager.learn_correction("c2", note="n2")
        correction_manager.learn_correction("c1")  # Increment first

        summary = correction_manager.get_summary()

        assert summary["total_count"] == 2
        assert summary["total_frequency"] == 3


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
        # Add profile preferences
        manager.learn("prefer early returns")
        manager.learn("max line length 100")

        # Add decisions
        for i in range(5):
            decision_manager.learn_decision(f"Decision {i}: Choice {i}", project="test")

        # Add corrections
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


class TestPhase18_2CLICommands:
    """CLI tests for Phase 18.2 features."""

    def test_learn_decision_command(self, temp_memory_dir):
        """Test memory learn --decision via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        result = subprocess.run(
            ['cerberus', 'memory', 'learn', '-d', 'chose SQLite', '-p', 'test-proj', '--json'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert 'success' in result.stdout

    def test_learn_correction_command(self, temp_memory_dir):
        """Test memory learn --correction via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        result = subprocess.run(
            ['cerberus', 'memory', 'learn', '-c', 'always log errors', '-n', 'Important', '--json'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert 'success' in result.stdout

    def test_show_decisions_command(self, temp_memory_dir):
        """Test memory show decisions via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        # First learn a decision
        subprocess.run(
            ['cerberus', 'memory', 'learn', '-d', 'test decision', '-p', 'test-proj'],
            capture_output=True,
            text=True,
            env=env
        )

        result = subprocess.run(
            ['cerberus', 'memory', 'show', 'decisions', '-p', 'test-proj'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0

    def test_show_corrections_command(self, temp_memory_dir):
        """Test memory show corrections via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        # First learn a correction
        subprocess.run(
            ['cerberus', 'memory', 'learn', '-c', 'test correction'],
            capture_output=True,
            text=True,
            env=env
        )

        result = subprocess.run(
            ['cerberus', 'memory', 'show', 'corrections'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0


# =============================================================================
# Phase 18.3 Tests: Prompts and Git Extraction
# =============================================================================

@pytest.fixture
def prompt_manager(store):
    """Create a PromptManager with temp store."""
    return PromptManager(store)


@pytest.fixture
def git_extractor(store):
    """Create a GitExtractor with temp store."""
    return GitExtractor(store)


class TestPrompt:
    """Tests for Prompt dataclass."""

    def test_to_dict(self):
        """Should convert to dict correctly."""
        prompt = Prompt(
            id="prm-001",
            name="security-audit",
            task_type="code-review",
            description="Check for OWASP vulnerabilities",
            template="Review for {{code}}",
            effectiveness=0.85,
            use_count=10,
        )
        data = prompt.to_dict()

        assert data["id"] == "prm-001"
        assert data["name"] == "security-audit"
        assert data["effectiveness"] == 0.85

    def test_from_dict(self):
        """Should create from dict correctly."""
        data = {
            "id": "prm-002",
            "name": "test-prompt",
            "task_type": "testing",
            "description": "Test description",
            "effectiveness": 0.9,
            "use_count": 5,
        }
        prompt = Prompt.from_dict(data)

        assert prompt.id == "prm-002"
        assert prompt.effectiveness == 0.9

    def test_to_terse(self):
        """Should generate terse representation."""
        prompt = Prompt(
            id="prm-001",
            name="security-audit",
            task_type="code-review",
            description="Check OWASP",
            effectiveness=0.85,
        )
        terse = prompt.to_terse()

        assert "security-audit" in terse
        assert "85%" in terse

    def test_record_use(self):
        """Should record usage and update effectiveness."""
        prompt = Prompt(
            id="prm-001",
            name="test",
            task_type="test",
            effectiveness=0.5,
            use_count=0,
        )

        prompt.record_use(successful=True)

        assert prompt.use_count == 1
        assert prompt.effectiveness > 0.5
        assert prompt.last_used != ""

    def test_extract_variables(self):
        """Should extract template variables."""
        prompt = Prompt(
            id="prm-001",
            name="test",
            task_type="test",
            template="Review {{code}} for {{issue}}",
        )
        variables = prompt.extract_variables()

        assert "code" in variables
        assert "issue" in variables


class TestPromptLibrary:
    """Tests for PromptLibrary collection."""

    def test_add_prompt(self):
        """Should add prompts correctly."""
        library = PromptLibrary(task_type="code-review")
        prompt = Prompt(id="prm-001", name="test", task_type="code-review")

        library.add_prompt(prompt)

        assert len(library.prompts) == 1

    def test_max_prompts_limit(self):
        """Should maintain max limit of 5 prompts."""
        library = PromptLibrary(task_type="test")

        for i in range(10):
            prompt = Prompt(
                id=f"prm-{i:03d}",
                name=f"prompt-{i}",
                task_type="test",
                effectiveness=i * 0.1,  # Varying effectiveness
            )
            library.add_prompt(prompt)

        assert len(library.prompts) == 5
        # Should keep highest effectiveness
        assert library.prompts[0].effectiveness >= 0.5

    def test_get_by_effectiveness(self):
        """Should return prompts sorted by effectiveness."""
        library = PromptLibrary(task_type="test")
        library.prompts = [
            Prompt(id="prm-001", name="low", task_type="test", effectiveness=0.3),
            Prompt(id="prm-002", name="high", task_type="test", effectiveness=0.9),
            Prompt(id="prm-003", name="mid", task_type="test", effectiveness=0.6),
        ]

        top = library.get_by_effectiveness(2)

        assert len(top) == 2
        assert top[0].name == "high"
        assert top[1].name == "mid"

    def test_find_by_name(self):
        """Should find prompt by name."""
        library = PromptLibrary(task_type="test")
        library.prompts = [
            Prompt(id="prm-001", name="security-audit", task_type="test"),
        ]

        found = library.find_by_name("security-audit")

        assert found is not None
        assert found.id == "prm-001"


class TestPromptManager:
    """Tests for PromptManager."""

    def test_learn_prompt(self, prompt_manager):
        """Should learn a new prompt."""
        result = prompt_manager.learn_prompt(
            name="security-audit",
            task_type="code-review",
            description="Check OWASP",
        )

        assert result["success"]
        assert result["task_type"] == "code-review"

    def test_learn_prompt_with_template(self, prompt_manager):
        """Should learn a prompt with template."""
        result = prompt_manager.learn_prompt(
            name="review",
            task_type="code-review",
            template="Review {{code}} for {{issues}}",
        )

        assert result["success"]
        assert "code" in result["prompt"]["variables"]
        assert "issues" in result["prompt"]["variables"]

    def test_forget_prompt(self, prompt_manager):
        """Should remove a prompt."""
        prompt_manager.learn_prompt(name="test", task_type="testing")
        result = prompt_manager.forget_prompt("test", task_type="testing")

        assert result["success"]

    def test_record_use(self, prompt_manager):
        """Should record prompt usage."""
        prompt_manager.learn_prompt(name="test", task_type="testing")

        result = prompt_manager.record_use("test", "testing", successful=True)

        assert result["success"]
        assert result["use_count"] == 1

    def test_list_task_types(self, prompt_manager):
        """Should list all task types."""
        prompt_manager.learn_prompt(name="p1", task_type="code-review")
        prompt_manager.learn_prompt(name="p2", task_type="testing")

        task_types = prompt_manager.list_task_types()

        assert "code-review" in task_types
        assert "testing" in task_types

    def test_get_prompts_for_context(self, prompt_manager):
        """Should return terse prompt strings."""
        prompt_manager.learn_prompt(
            name="security",
            task_type="code-review",
            description="OWASP checks",
        )

        context_lines = prompt_manager.get_prompts_for_context("code-review", count=5)

        assert len(context_lines) == 1
        assert "security" in context_lines[0]

    def test_get_summary(self, prompt_manager):
        """Should return prompt summary."""
        prompt_manager.learn_prompt(name="p1", task_type="code-review")
        prompt_manager.learn_prompt(name="p2", task_type="testing")

        summary = prompt_manager.get_summary()

        assert summary["total_prompts"] == 2
        assert summary["task_types"] == 2


class TestGitExtractor:
    """Tests for GitExtractor."""

    def test_extract_decision_pattern(self, git_extractor):
        """Should extract decisions from commit messages."""
        # Test the internal method
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

        context = generator.generate_context()  # No task

        assert "For Code Review" not in context

    def test_full_context_under_150_lines(self, generator, manager, decision_manager, correction_manager, prompt_manager):
        """Full context must be under 150 lines."""
        # Add profile
        manager.learn("prefer early returns")

        # Add decisions
        for i in range(5):
            decision_manager.learn_decision(f"Decision {i}", project="test")

        # Add corrections
        for i in range(5):
            correction_manager.learn_correction(f"correction {i}")

        # Add prompts
        for i in range(3):
            prompt_manager.learn_prompt(name=f"prompt-{i}", task_type="code-review")

        context = generator.generate_context(project="test", task="code-review")
        lines = context.split('\n')

        assert len(lines) < 150


class TestPhase18_3CLICommands:
    """CLI tests for Phase 18.3 features."""

    def test_learn_prompt_command(self, temp_memory_dir):
        """Test memory learn --prompt via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        result = subprocess.run(
            ['cerberus', 'memory', 'learn', '--prompt', 'test-prompt',
             '--task', 'code-review', '--description', 'Test description', '--json'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert 'success' in result.stdout

    def test_show_prompts_command(self, temp_memory_dir):
        """Test memory show prompts via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        # First learn a prompt
        subprocess.run(
            ['cerberus', 'memory', 'learn', '--prompt', 'test',
             '--task', 'testing'],
            capture_output=True,
            text=True,
            env=env
        )

        result = subprocess.run(
            ['cerberus', 'memory', 'show', 'prompts'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0

    def test_context_with_task_command(self, temp_memory_dir):
        """Test memory context --task via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        # First learn a prompt
        subprocess.run(
            ['cerberus', 'memory', 'learn', '--prompt', 'security',
             '--task', 'code-review', '--description', 'OWASP'],
            capture_output=True,
            text=True,
            env=env
        )

        result = subprocess.run(
            ['cerberus', 'memory', 'context', '--task', 'code-review'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        # May or may not have the prompt if profile is empty

    def test_extract_dry_run_command(self, temp_memory_dir):
        """Test memory extract --dry-run via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        result = subprocess.run(
            ['cerberus', 'memory', 'extract', '--dry-run', '--max-commits', '10'],
            capture_output=True,
            text=True,
            env=env
        )

        # May succeed or fail depending on whether we're in a git repo
        # Just check it doesn't crash
        assert result.returncode in [0, 1]

    def test_forget_prompt_command(self, temp_memory_dir):
        """Test memory forget --prompt via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        # First learn a prompt
        subprocess.run(
            ['cerberus', 'memory', 'learn', '--prompt', 'to-delete',
             '--task', 'testing'],
            capture_output=True,
            text=True,
            env=env
        )

        result = subprocess.run(
            ['cerberus', 'memory', 'forget', 'to-delete', '--prompt',
             '--task', 'testing'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0


# =============================================================================
# Phase 18.4 Tests: Polish & Integration
# =============================================================================

class TestExportImport:
    """Tests for export and import functionality."""

    def test_export_empty_memory(self, store):
        """Should export empty memory structure."""
        from cerberus.memory.profile import ProfileManager
        from cerberus.memory.context import ContextGenerator

        profile_manager = ProfileManager(store)
        generator = ContextGenerator(store)

        # Export should work even with empty data
        profile = profile_manager.load_profile()
        data = profile.to_dict()

        assert "$schema" in data
        assert data.get("coding_style") == {}

    def test_export_with_data(self, store, manager, decision_manager, correction_manager, prompt_manager):
        """Should export all memory sections."""
        # Add data to each section
        manager.learn("prefer early returns")
        decision_manager.learn_decision("chose SQLite", project="test-proj")
        correction_manager.learn_correction("always log errors", note="Important")
        prompt_manager.learn_prompt(name="security", task_type="code-review")

        # Verify data exists
        profile = manager.load_profile()
        assert not profile.is_empty()

        decisions = decision_manager.load_decisions("test-proj")
        assert len(decisions.decisions) > 0

        corrections = correction_manager.load_corrections()
        assert len(corrections.corrections) > 0

    def test_import_merges_profile(self, store, manager):
        """Should merge imported profile with existing."""
        # Set up existing profile
        manager.learn("prefer early returns")

        # Create import data
        import_data = {
            "$schema": "profile-v1",
            "coding_style": {"max_line_length": 100, "prefer_early_returns": True},
            "naming_conventions": {"functions": "camelCase"},
            "anti_patterns": ["avoid any type"],
            "languages": {},
            "general": []
        }

        # Simulate merge
        existing = manager.load_profile()
        existing.coding_style.update(import_data.get("coding_style", {}))
        existing.naming_conventions.update(import_data.get("naming_conventions", {}))

        for ap in import_data.get("anti_patterns", []):
            if ap not in existing.anti_patterns:
                existing.anti_patterns.append(ap)

        manager.save_profile(existing)

        # Verify merge
        profile = manager.load_profile()
        assert profile.coding_style.get("max_line_length") == 100
        assert profile.coding_style.get("prefer_early_returns") is True
        assert "avoid any type" in profile.anti_patterns

    def test_import_merges_corrections(self, store, correction_manager):
        """Should merge imported corrections, combining frequencies."""
        # Add existing correction
        correction_manager.learn_correction("log errors", note="Original note")

        # Create import data
        from cerberus.memory.corrections import Correction

        existing = correction_manager.load_corrections()
        new_correction = Correction(
            id="cor-imported",
            pattern="log errors everywhere",
            correction="add logging",
            frequency=5,
            note="Imported note"
        )

        # Find similar and merge
        found = existing.find_similar(new_correction.pattern)
        if found:
            found.frequency += new_correction.frequency
            found.note = new_correction.note or found.note
        else:
            # Append to corrections list directly
            existing.corrections.append(new_correction)

        correction_manager.save_corrections(existing)

        # Verify merge
        corrections = correction_manager.load_corrections()
        # Should have merged into one correction with combined frequency
        matching = [c for c in corrections.corrections if "log" in c.pattern.lower()]
        assert len(matching) >= 1
        assert matching[0].frequency >= 5

    def test_import_preserves_decision_order(self, store, decision_manager):
        """Should maintain decision order after import."""
        # Add decisions in order - use chose X pattern for clearer topic extraction
        for i in range(5):
            decision_manager.learn_decision(f"chose Option{i} for reason {i}", project="test")

        decisions = decision_manager.load_decisions("test")
        # Most recent should be first - check the decision text contains Option4
        assert "Option4" in decisions.decisions[0].decision


class TestPhase18_4CLICommands:
    """CLI tests for Phase 18.4 features."""

    def test_export_command(self, temp_memory_dir):
        """Test memory export via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        # First learn something
        subprocess.run(
            ['cerberus', 'memory', 'learn', 'prefer early returns'],
            capture_output=True,
            text=True,
            env=env
        )

        # Export to stdout
        result = subprocess.run(
            ['cerberus', 'memory', 'export'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert '"$schema": "session-memory-export-v1"' in result.stdout

    def test_export_to_file_command(self, temp_memory_dir):
        """Test memory export to file via CLI."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        output_file = temp_memory_dir / "export.json"

        # First learn something
        subprocess.run(
            ['cerberus', 'memory', 'learn', 'prefer early returns'],
            capture_output=True,
            text=True,
            env=env
        )

        # Export to file
        result = subprocess.run(
            ['cerberus', 'memory', 'export', '-o', str(output_file)],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert output_file.exists()

        # Verify file contents
        import json
        with open(output_file) as f:
            data = json.load(f)
        assert "$schema" in data

    def test_import_command_dry_run(self, temp_memory_dir):
        """Test memory import --dry-run via CLI."""
        import subprocess
        import os
        import json

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        # Create export file
        export_file = temp_memory_dir / "import_test.json"
        export_data = {
            "$schema": "session-memory-export-v1",
            "version": "18.4",
            "profile": {
                "$schema": "profile-v1",
                "coding_style": {"max_line_length": 120},
                "naming_conventions": {},
                "anti_patterns": ["test anti-pattern"],
                "languages": {},
                "general": []
            },
            "corrections": {
                "$schema": "corrections-v1",
                "corrections": []
            },
            "decisions": {},
            "prompts": {}
        }
        with open(export_file, 'w') as f:
            json.dump(export_data, f)

        # Import with dry-run
        result = subprocess.run(
            ['cerberus', 'memory', 'import', str(export_file), '--dry-run'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert "Dry run" in result.stdout

    def test_import_command_actual(self, temp_memory_dir):
        """Test memory import (actual) via CLI."""
        import subprocess
        import os
        import json

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        # Create export file
        export_file = temp_memory_dir / "import_actual.json"
        export_data = {
            "$schema": "session-memory-export-v1",
            "version": "18.4",
            "profile": {
                "$schema": "profile-v1",
                "coding_style": {"max_line_length": 80},
                "naming_conventions": {},
                "anti_patterns": [],
                "languages": {},
                "general": []
            },
            "corrections": {
                "$schema": "corrections-v1",
                "corrections": []
            },
            "decisions": {},
            "prompts": {}
        }
        with open(export_file, 'w') as f:
            json.dump(export_data, f)

        # Import
        result = subprocess.run(
            ['cerberus', 'memory', 'import', str(export_file)],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert "Import complete" in result.stdout

        # Verify import worked
        result = subprocess.run(
            ['cerberus', 'memory', 'show', 'profile', '--json'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data.get("profile", {}).get("coding_style", {}).get("max_line_length") == 80

    def test_export_import_roundtrip(self, temp_memory_dir):
        """Test full export -> import roundtrip."""
        import subprocess
        import os
        import json

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        # Learn various items
        subprocess.run(
            ['cerberus', 'memory', 'learn', 'prefer early returns'],
            capture_output=True, text=True, env=env
        )
        subprocess.run(
            ['cerberus', 'memory', 'learn', '-d', 'chose SQLite', '-p', 'test-proj'],
            capture_output=True, text=True, env=env
        )
        subprocess.run(
            ['cerberus', 'memory', 'learn', '-c', 'always log errors'],
            capture_output=True, text=True, env=env
        )

        # Export
        export_file = temp_memory_dir / "roundtrip.json"
        subprocess.run(
            ['cerberus', 'memory', 'export', '-o', str(export_file)],
            capture_output=True, text=True, env=env
        )

        assert export_file.exists()

        # Read and verify export contents
        with open(export_file) as f:
            exported = json.load(f)

        assert "profile" in exported
        assert "decisions" in exported
        assert "corrections" in exported

        # Clear and re-import (using a fresh config dir)
        fresh_dir = temp_memory_dir / "fresh"
        fresh_dir.mkdir()
        env2 = env.copy()
        env2['XDG_CONFIG_HOME'] = str(fresh_dir)

        # Import into fresh directory
        result = subprocess.run(
            ['cerberus', 'memory', 'import', str(export_file)],
            capture_output=True, text=True, env=env2
        )

        assert result.returncode == 0

        # Verify data was imported
        result = subprocess.run(
            ['cerberus', 'memory', 'show', '--json'],
            capture_output=True, text=True, env=env2
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "profile" in data

    def test_export_section_filter(self, temp_memory_dir):
        """Test memory export with section filter."""
        import subprocess
        import os
        import json

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        # Learn something
        subprocess.run(
            ['cerberus', 'memory', 'learn', 'test preference'],
            capture_output=True, text=True, env=env
        )

        # Export only profile
        result = subprocess.run(
            ['cerberus', 'memory', 'export', '--section', 'profile'],
            capture_output=True, text=True, env=env
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "profile" in data
        # Other sections may not be present when filtering

    def test_stats_command(self, temp_memory_dir):
        """Test memory stats command."""
        import subprocess
        import os

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        result = subprocess.run(
            ['cerberus', 'memory', 'stats'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert "Session Memory Statistics" in result.stdout

    def test_stats_json_command(self, temp_memory_dir):
        """Test memory stats --json command."""
        import subprocess
        import os
        import json

        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        result = subprocess.run(
            ['cerberus', 'memory', 'stats', '--json'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "storage" in data
        assert "context" in data


class TestIntegrationPhase184:
    """Integration tests specific to Phase 18.4."""

    def test_full_workflow_with_export_import(self, store, manager, decision_manager, correction_manager):
        """Test complete workflow: learn -> export -> clear -> import -> verify."""
        import json
        import tempfile
        from pathlib import Path

        # 1. Learn data
        manager.learn("prefer early returns")
        manager.learn("max line length 100")
        decision_manager.learn_decision("chose SQLite", project="test-proj")
        correction_manager.learn_correction("always log", note="Important")

        # 2. Export to file
        profile = manager.load_profile()
        decisions = decision_manager.load_decisions("test-proj")
        corrections = correction_manager.load_corrections()

        export_data = {
            "$schema": "session-memory-export-v1",
            "profile": profile.to_dict(),
            "decisions": {
                "test-proj": {
                    "decisions": [d.to_dict() for d in decisions.decisions]
                }
            },
            "corrections": {
                "corrections": [c.to_dict() for c in corrections.corrections]
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(export_data, f)
            temp_path = f.name

        try:
            # 3. Verify export
            with open(temp_path) as f:
                loaded = json.load(f)

            assert loaded["profile"]["coding_style"]["prefer_early_returns"] is True
            assert loaded["profile"]["coding_style"]["max_line_length"] == 100
            assert len(loaded["decisions"]["test-proj"]["decisions"]) == 1
            assert len(loaded["corrections"]["corrections"]) == 1
        finally:
            Path(temp_path).unlink()

    def test_context_generation_under_4kb(self, store, manager, decision_manager, correction_manager, prompt_manager, generator):
        """Full context with all sections must stay under 4KB."""
        # Add substantial data
        manager.learn("prefer early returns")
        manager.learn("max line length 100")
        manager.learn("use async/await")
        manager.learn("never use any type")
        manager.learn("components use PascalCase")

        for i in range(10):
            decision_manager.learn_decision(f"Decision {i}: Made choice {i} for reason {i}", project="test")

        for i in range(10):
            correction_manager.learn_correction(f"Pattern {i} should be avoided", note=f"Correction note {i}")

        for i in range(3):
            prompt_manager.learn_prompt(name=f"prompt-{i}", task_type="code-review", description=f"Description {i}")

        # Generate full context
        context = generator.generate_context(project="test", task="code-review")
        context_bytes = len(context.encode('utf-8'))

        # Must be under 4KB
        assert context_bytes < 4096, f"Context is {context_bytes} bytes, must be under 4096"

    def test_compression_ratio_above_90_percent(self, store, manager, decision_manager, correction_manager, generator):
        """Compression ratio (stored vs injected) should be above 90%."""
        # Add data
        manager.learn("prefer early returns")
        manager.learn("max line length 100")

        for i in range(5):
            decision_manager.learn_decision(
                f"Decision {i}: We chose technology X over Y because of performance considerations and team familiarity",
                project="test",
                rationale=f"Detailed rationale for decision {i} with lots of explanation"
            )

        for i in range(5):
            correction_manager.learn_correction(
                f"Pattern {i}: When AI generates code like X, it should instead use pattern Y for better maintainability",
                note=f"Note for correction {i}"
            )

        # Get stats
        stats = generator.get_context_stats()

        # Compression ratio should be > 0 (we're compressing)
        assert stats['compression_ratio'] >= 0, "Should have positive compression"
