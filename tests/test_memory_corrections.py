"""Tests for Correction, CorrectionStore, and CorrectionManager."""

import pytest
import tempfile
import shutil
from pathlib import Path

pytestmark = pytest.mark.memory

from cerberus.memory.store import MemoryStore
from cerberus.memory.corrections import CorrectionManager, Correction, CorrectionStore


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
def correction_manager(store):
    """Create a CorrectionManager with temp store."""
    return CorrectionManager(store)


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
        correction_manager.learn_correction("c1")

        summary = correction_manager.get_summary()

        assert summary["total_count"] == 2
        assert summary["total_frequency"] == 3
