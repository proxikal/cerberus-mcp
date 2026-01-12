"""Tests for Decision, ProjectDecisions, and DecisionManager."""

import pytest
import tempfile
import shutil
from pathlib import Path

pytestmark = pytest.mark.memory

from cerberus.memory.store import MemoryStore
from cerberus.memory.decisions import DecisionManager, Decision, ProjectDecisions


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
def decision_manager(store):
    """Create a DecisionManager with temp store."""
    return DecisionManager(store)


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

        for i in range(15):
            decision = Decision(id=f"dec-{i:03d}", date="2026-01-10", topic=f"Topic {i}", decision=f"Decision {i}")
            project.add_decision(decision)

        assert len(project.decisions) == 10
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
