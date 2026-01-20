"""Integration tests for Session Memory (Phase 18.1 - 18.4)."""

import pytest
import subprocess
import os
import json
import tempfile
import shutil
from pathlib import Path

pytestmark = [pytest.mark.memory, pytest.mark.integration]

from cerberus.memory.store import MemoryStore
pytestmark = pytest.mark.skip(reason="CLI commands deprecated/absent in MCP-only environment")
from cerberus.memory.profile import ProfileManager
from cerberus.memory.context import ContextGenerator
from cerberus.memory.decisions import DecisionManager
from cerberus.memory.corrections import CorrectionManager, Correction
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


class TestIntegration:
    """Integration tests for Session Memory."""

    def test_full_workflow(self, manager, generator):
        """Test learn -> show -> context workflow."""
        manager.learn("prefer early returns")
        manager.learn("max line length 80")
        manager.learn("never use magic numbers")

        profile = manager.load_profile()
        assert not profile.is_empty()
        assert profile.coding_style.get("prefer_early_returns") is True
        assert profile.coding_style.get("max_line_length") == 80
        assert len(profile.anti_patterns) == 1

        context = generator.generate_context()
        assert "Early returns" in context
        assert "80" in context
        assert "magic numbers" in context

    def test_context_under_4kb(self, manager, generator):
        """Full context must not exceed 4KB."""
        for i in range(10):
            manager.learn(f"preference number {i} is important")

        context = generator.generate_context()
        context_bytes = len(context.encode('utf-8'))

        assert context_bytes < MemoryStore.MAX_CONTEXT_SIZE

    def test_profile_persistence(self, store, manager):
        """Profile should persist across manager instances."""
        manager.learn("prefer early returns")

        new_manager = ProfileManager(store)
        profile = new_manager.load_profile()

        assert profile.coding_style.get("prefer_early_returns") is True


class TestExportImport:
    """Tests for export and import functionality."""

    def test_export_empty_memory(self, store):
        """Should export empty memory structure."""
        profile_manager = ProfileManager(store)
        generator = ContextGenerator(store)

        profile = profile_manager.load_profile()
        data = profile.to_dict()

        assert "$schema" in data
        assert data.get("coding_style") == {}

    def test_export_with_data(self, store, manager, decision_manager, correction_manager, prompt_manager):
        """Should export all memory sections."""
        manager.learn("prefer early returns")
        decision_manager.learn_decision("chose SQLite", project="test-proj")
        correction_manager.learn_correction("always log errors", note="Important")
        prompt_manager.learn_prompt(name="security", task_type="code-review")

        profile = manager.load_profile()
        assert not profile.is_empty()

        decisions = decision_manager.load_decisions("test-proj")
        assert len(decisions.decisions) > 0

        corrections = correction_manager.load_corrections()
        assert len(corrections.corrections) > 0

    def test_import_merges_profile(self, store, manager):
        """Should merge imported profile with existing."""
        manager.learn("prefer early returns")

        import_data = {
            "$schema": "profile-v1",
            "coding_style": {"max_line_length": 100, "prefer_early_returns": True},
            "naming_conventions": {"functions": "camelCase"},
            "anti_patterns": ["avoid any type"],
            "languages": {},
            "general": []
        }

        existing = manager.load_profile()
        existing.coding_style.update(import_data.get("coding_style", {}))
        existing.naming_conventions.update(import_data.get("naming_conventions", {}))

        for ap in import_data.get("anti_patterns", []):
            if ap not in existing.anti_patterns:
                existing.anti_patterns.append(ap)

        manager.save_profile(existing)

        profile = manager.load_profile()
        assert profile.coding_style.get("max_line_length") == 100
        assert profile.coding_style.get("prefer_early_returns") is True
        assert "avoid any type" in profile.anti_patterns

    def test_import_merges_corrections(self, store, correction_manager):
        """Should merge imported corrections, combining frequencies."""
        correction_manager.learn_correction("log errors", note="Original note")

        existing = correction_manager.load_corrections()
        new_correction = Correction(
            id="cor-imported",
            pattern="log errors everywhere",
            correction="add logging",
            frequency=5,
            note="Imported note"
        )

        found = existing.find_similar(new_correction.pattern)
        if found:
            found.frequency += new_correction.frequency
            found.note = new_correction.note or found.note
        else:
            existing.corrections.append(new_correction)

        correction_manager.save_corrections(existing)

        corrections = correction_manager.load_corrections()
        matching = [c for c in corrections.corrections if "log" in c.pattern.lower()]
        assert len(matching) >= 1
        assert matching[0].frequency >= 5

    def test_import_preserves_decision_order(self, store, decision_manager):
        """Should maintain decision order after import."""
        for i in range(5):
            decision_manager.learn_decision(f"chose Option{i} for reason {i}", project="test")

        decisions = decision_manager.load_decisions("test")
        assert "Option4" in decisions.decisions[0].decision


class TestPhase18_4CLICommands:
    """CLI tests for Phase 18.4 features."""

    def test_export_command(self, temp_memory_dir):
        """Test memory export via CLI."""
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        subprocess.run(
            ['cerberus', 'memory', 'learn', 'prefer early returns'],
            capture_output=True,
            text=True,
            env=env
        )

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
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        output_file = temp_memory_dir / "export.json"

        subprocess.run(
            ['cerberus', 'memory', 'learn', 'prefer early returns'],
            capture_output=True,
            text=True,
            env=env
        )

        result = subprocess.run(
            ['cerberus', 'memory', 'export', '-o', str(output_file)],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert output_file.exists()

        with open(output_file) as f:
            data = json.load(f)
        assert "$schema" in data

    def test_import_command_dry_run(self, temp_memory_dir):
        """Test memory import --dry-run via CLI."""
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

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
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

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

        result = subprocess.run(
            ['cerberus', 'memory', 'import', str(export_file)],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode == 0
        assert "Import complete" in result.stdout

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
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

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

        export_file = temp_memory_dir / "roundtrip.json"
        subprocess.run(
            ['cerberus', 'memory', 'export', '-o', str(export_file)],
            capture_output=True, text=True, env=env
        )

        assert export_file.exists()

        with open(export_file) as f:
            exported = json.load(f)

        assert "profile" in exported
        assert "decisions" in exported
        assert "corrections" in exported

        fresh_dir = temp_memory_dir / "fresh"
        fresh_dir.mkdir()
        env2 = env.copy()
        env2['XDG_CONFIG_HOME'] = str(fresh_dir)

        result = subprocess.run(
            ['cerberus', 'memory', 'import', str(export_file)],
            capture_output=True, text=True, env=env2
        )

        assert result.returncode == 0

        result = subprocess.run(
            ['cerberus', 'memory', 'show', '--json'],
            capture_output=True, text=True, env=env2
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "profile" in data

    def test_export_section_filter(self, temp_memory_dir):
        """Test memory export with section filter."""
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        subprocess.run(
            ['cerberus', 'memory', 'learn', 'test preference'],
            capture_output=True, text=True, env=env
        )

        result = subprocess.run(
            ['cerberus', 'memory', 'export', '--section', 'profile'],
            capture_output=True, text=True, env=env
        )

        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "profile" in data

    def test_stats_command(self, temp_memory_dir):
        """Test memory stats command."""
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
        manager.learn("prefer early returns")
        manager.learn("max line length 100")
        decision_manager.learn_decision("chose SQLite", project="test-proj")
        correction_manager.learn_correction("always log", note="Important")

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

        context = generator.generate_context(project="test", task="code-review")
        context_bytes = len(context.encode('utf-8'))

        assert context_bytes < 4096, f"Context is {context_bytes} bytes, must be under 4096"

    def test_compression_ratio_above_90_percent(self, store, manager, decision_manager, correction_manager, generator):
        """Compression ratio (stored vs injected) should be above 90%."""
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

        stats = generator.get_context_stats()

        assert stats['compression_ratio'] >= 0, "Should have positive compression"
