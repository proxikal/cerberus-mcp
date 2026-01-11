"""CLI tests for Session Memory (Phases 18.1, 18.2, 18.3)."""

import pytest
import subprocess
import os
import tempfile
import shutil
from pathlib import Path

pytestmark = [pytest.mark.memory, pytest.mark.integration]


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for memory storage."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestCLICommands:
    """Tests for CLI commands (integration tests)."""

    def test_learn_command(self, temp_memory_dir):
        """Test memory learn via CLI."""
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


class TestPhase18_2CLICommands:
    """CLI tests for Phase 18.2 features."""

    def test_learn_decision_command(self, temp_memory_dir):
        """Test memory learn --decision via CLI."""
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
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

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
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

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


class TestPhase18_3CLICommands:
    """CLI tests for Phase 18.3 features."""

    def test_learn_prompt_command(self, temp_memory_dir):
        """Test memory learn --prompt via CLI."""
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
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

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
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

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

    def test_extract_dry_run_command(self, temp_memory_dir):
        """Test memory extract --dry-run via CLI."""
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

        result = subprocess.run(
            ['cerberus', 'memory', 'extract', '--dry-run', '--max-commits', '10'],
            capture_output=True,
            text=True,
            env=env
        )

        assert result.returncode in [0, 1]

    def test_forget_prompt_command(self, temp_memory_dir):
        """Test memory forget --prompt via CLI."""
        env = os.environ.copy()
        env['XDG_CONFIG_HOME'] = str(temp_memory_dir.parent)

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
