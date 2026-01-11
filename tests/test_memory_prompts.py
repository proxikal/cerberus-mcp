"""Tests for Prompt, PromptLibrary, and PromptManager."""

import pytest
import tempfile
import shutil
from pathlib import Path

pytestmark = pytest.mark.memory

from cerberus.memory.store import MemoryStore
from cerberus.memory.prompts import PromptManager, Prompt, PromptLibrary


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
def prompt_manager(store):
    """Create a PromptManager with temp store."""
    return PromptManager(store)


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
                effectiveness=i * 0.1,
            )
            library.add_prompt(prompt)

        assert len(library.prompts) == 5
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
