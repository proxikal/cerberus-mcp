"""
Tests for Phase 5: Storage Operations (JSON)

Validates:
- Hierarchical routing (universal → language → project)
- Batch optimization (group by file, write once)
- Metadata tracking (timestamp, confidence, access_count)
- Directory auto-creation
- No data loss
- Atomic writes
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from cerberus.memory.storage import (
    MemoryStorage,
    store_proposals,
    get_storage_stats
)
from cerberus.memory.proposal_engine import MemoryProposal


# Test fixtures

def create_mock_proposal(
    id_suffix: str,
    content: str,
    scope: str,
    category: str,
    confidence: float = 0.9
) -> MemoryProposal:
    """Create a mock memory proposal."""
    return MemoryProposal(
        id=f"mem-{id_suffix}",
        category=category,
        scope=scope,
        content=content,
        rationale="Test rationale",
        source_variants=[content],
        confidence=confidence,
        priority=3
    )


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(temp_storage_dir):
    """Create MemoryStorage instance with temp directory."""
    return MemoryStorage(base_dir=temp_storage_dir)


# Test hierarchical routing

def test_universal_preference_routing(storage, temp_storage_dir):
    """Universal preferences should go to profile.json."""
    proposals = [
        create_mock_proposal("001", "Keep output concise", "universal", "preference")
    ]

    results = storage.store_batch(proposals)

    # Check file was created
    profile_path = Path(temp_storage_dir) / "profile.json"
    assert profile_path.exists()
    assert str(profile_path) in results
    assert results[str(profile_path)] == 1


def test_universal_correction_routing(storage, temp_storage_dir):
    """Universal corrections/rules should go to corrections.json."""
    proposals = [
        create_mock_proposal("002", "Never use panic", "universal", "correction"),
        create_mock_proposal("003", "Always log errors", "universal", "rule")
    ]

    results = storage.store_batch(proposals)

    # Check file was created
    corrections_path = Path(temp_storage_dir) / "corrections.json"
    assert corrections_path.exists()
    assert str(corrections_path) in results
    assert results[str(corrections_path)] == 2


def test_language_routing(storage, temp_storage_dir):
    """Language-specific memories should go to languages/{lang}.json."""
    proposals = [
        create_mock_proposal("004", "Use defer for cleanup", "language:go", "rule"),
        create_mock_proposal("005", "Use async/await", "language:python", "rule")
    ]

    results = storage.store_batch(proposals)

    # Check files were created
    go_path = Path(temp_storage_dir) / "languages" / "go.json"
    python_path = Path(temp_storage_dir) / "languages" / "python.json"

    assert go_path.exists()
    assert python_path.exists()
    assert results[str(go_path)] == 1
    assert results[str(python_path)] == 1


def test_project_routing(storage, temp_storage_dir):
    """Project-specific memories should go to projects/{project}/decisions.json."""
    proposals = [
        create_mock_proposal("006", "Use PortalTabs", "project:xcalibr", "rule"),
        create_mock_proposal("007", "Use golden egg docs", "project:cerberus", "rule")
    ]

    results = storage.store_batch(proposals)

    # Check files were created
    xcalibr_path = Path(temp_storage_dir) / "projects" / "xcalibr" / "decisions.json"
    cerberus_path = Path(temp_storage_dir) / "projects" / "cerberus" / "decisions.json"

    assert xcalibr_path.exists()
    assert cerberus_path.exists()
    assert results[str(xcalibr_path)] == 1
    assert results[str(cerberus_path)] == 1


# Test batch optimization

def test_batch_optimization_same_file(storage, temp_storage_dir):
    """Multiple proposals to same file should be written in one batch."""
    proposals = [
        create_mock_proposal("008", "Rule 1", "universal", "preference"),
        create_mock_proposal("009", "Rule 2", "universal", "preference"),
        create_mock_proposal("010", "Rule 3", "universal", "preference")
    ]

    results = storage.store_batch(proposals)

    # All should go to same file
    profile_path = Path(temp_storage_dir) / "profile.json"
    assert len(results) == 1
    assert results[str(profile_path)] == 3

    # Verify all stored
    with open(profile_path, 'r') as f:
        data = json.load(f)
        assert len(data) == 3


def test_batch_optimization_multiple_files(storage, temp_storage_dir):
    """Proposals to different files should be grouped correctly."""
    proposals = [
        create_mock_proposal("011", "Pref 1", "universal", "preference"),
        create_mock_proposal("012", "Pref 2", "universal", "preference"),
        create_mock_proposal("013", "Rule 1", "language:go", "rule"),
        create_mock_proposal("014", "Rule 2", "language:go", "rule"),
        create_mock_proposal("015", "Corr 1", "universal", "correction")
    ]

    results = storage.store_batch(proposals)

    # Should write to 3 files
    assert len(results) == 3

    # Verify counts
    profile_path = Path(temp_storage_dir) / "profile.json"
    corrections_path = Path(temp_storage_dir) / "corrections.json"
    go_path = Path(temp_storage_dir) / "languages" / "go.json"

    assert results[str(profile_path)] == 2
    assert results[str(corrections_path)] == 1
    assert results[str(go_path)] == 2


# Test metadata tracking

def test_metadata_fields(storage, temp_storage_dir):
    """Stored memories should have all metadata fields."""
    proposals = [
        create_mock_proposal("016", "Test memory", "universal", "preference", 0.95)
    ]

    storage.store_batch(proposals)

    # Load and verify metadata
    profile_path = Path(temp_storage_dir) / "profile.json"
    with open(profile_path, 'r') as f:
        data = json.load(f)
        memory = data[0]

        # Check all required fields
        assert "id" in memory
        assert "category" in memory
        assert "scope" in memory
        assert "content" in memory
        assert "rationale" in memory
        assert "confidence" in memory
        assert "timestamp" in memory
        assert "access_count" in memory
        assert "last_accessed" in memory

        # Verify values
        assert memory["id"] == "mem-016"
        assert memory["confidence"] == 0.95
        assert memory["access_count"] == 0
        assert memory["last_accessed"] is None

        # Verify timestamp is valid ISO format
        datetime.fromisoformat(memory["timestamp"])


# Test directory auto-creation

def test_auto_create_directories(storage, temp_storage_dir):
    """Directories should be created automatically."""
    proposals = [
        create_mock_proposal("017", "Go rule", "language:rust", "rule"),
        create_mock_proposal("018", "Project rule", "project:newproject", "rule")
    ]

    storage.store_batch(proposals)

    # Verify directories were created
    languages_dir = Path(temp_storage_dir) / "languages"
    projects_dir = Path(temp_storage_dir) / "projects"
    project_dir = Path(temp_storage_dir) / "projects" / "newproject"

    assert languages_dir.exists()
    assert languages_dir.is_dir()
    assert projects_dir.exists()
    assert projects_dir.is_dir()
    assert project_dir.exists()
    assert project_dir.is_dir()


# Test no data loss

def test_merge_with_existing(storage, temp_storage_dir):
    """New memories should merge with existing without loss."""
    # First batch
    proposals1 = [
        create_mock_proposal("019", "Memory 1", "universal", "preference"),
        create_mock_proposal("020", "Memory 2", "universal", "preference")
    ]
    storage.store_batch(proposals1)

    # Second batch
    proposals2 = [
        create_mock_proposal("021", "Memory 3", "universal", "preference"),
        create_mock_proposal("022", "Memory 4", "universal", "preference")
    ]
    storage.store_batch(proposals2)

    # Verify all 4 memories are stored
    profile_path = Path(temp_storage_dir) / "profile.json"
    with open(profile_path, 'r') as f:
        data = json.load(f)
        assert len(data) == 4

        ids = {m["id"] for m in data}
        assert ids == {"mem-019", "mem-020", "mem-021", "mem-022"}


def test_no_duplicate_ids(storage, temp_storage_dir):
    """Duplicate IDs should not be stored twice."""
    # First batch
    proposals1 = [
        create_mock_proposal("023", "Memory 1", "universal", "preference")
    ]
    storage.store_batch(proposals1)

    # Second batch with same ID
    proposals2 = [
        create_mock_proposal("023", "Memory 1 modified", "universal", "preference")
    ]
    storage.store_batch(proposals2)

    # Should only have 1 memory
    profile_path = Path(temp_storage_dir) / "profile.json"
    with open(profile_path, 'r') as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["id"] == "mem-023"


# Test atomic writes

def test_atomic_write_no_partial_data(storage, temp_storage_dir):
    """Failed writes should not leave partial data."""
    proposals = [
        create_mock_proposal("024", "Test", "universal", "preference")
    ]

    # This should succeed
    storage.store_batch(proposals)

    profile_path = Path(temp_storage_dir) / "profile.json"
    assert profile_path.exists()

    # Verify no .tmp file left behind
    temp_path = profile_path.with_suffix('.tmp')
    assert not temp_path.exists()


# Test empty proposals

def test_empty_proposals(storage):
    """Empty proposal list should return empty results."""
    results = storage.store_batch([])
    assert results == {}


# Test storage stats

def test_storage_stats(storage, temp_storage_dir):
    """get_stats should return correct counts."""
    proposals = [
        create_mock_proposal("025", "Pref 1", "universal", "preference"),
        create_mock_proposal("026", "Pref 2", "universal", "preference"),
        create_mock_proposal("027", "Corr 1", "universal", "correction"),
        create_mock_proposal("028", "Go 1", "language:go", "rule"),
        create_mock_proposal("029", "Proj 1", "project:test", "rule")
    ]

    storage.store_batch(proposals)

    stats = storage.get_stats()

    assert stats["profile.json"] == 2
    assert stats["corrections.json"] == 1
    assert stats["languages/go.json"] == 1
    assert stats["projects/test/decisions.json"] == 1


def test_storage_stats_empty(storage):
    """get_stats should handle empty storage."""
    stats = storage.get_stats()
    assert stats == {}


# Test convenience functions

def test_store_proposals_convenience(temp_storage_dir):
    """store_proposals convenience function should work."""
    proposals = [
        create_mock_proposal("030", "Test", "universal", "preference")
    ]

    results = store_proposals(proposals, base_dir=temp_storage_dir)

    profile_path = Path(temp_storage_dir) / "profile.json"
    assert profile_path.exists()
    assert results[str(profile_path)] == 1


def test_get_storage_stats_convenience(temp_storage_dir):
    """get_storage_stats convenience function should work."""
    proposals = [
        create_mock_proposal("031", "Test", "universal", "preference")
    ]

    store_proposals(proposals, base_dir=temp_storage_dir)
    stats = get_storage_stats(base_dir=temp_storage_dir)

    assert stats["profile.json"] == 1


# Test file format

def test_json_format_readable(storage, temp_storage_dir):
    """JSON files should be human-readable (indented)."""
    proposals = [
        create_mock_proposal("032", "Test", "universal", "preference")
    ]

    storage.store_batch(proposals)

    profile_path = Path(temp_storage_dir) / "profile.json"
    with open(profile_path, 'r') as f:
        content = f.read()
        # Should be indented (not minified)
        assert '\n' in content
        assert '  ' in content  # 2-space indent


# Test corrupted file handling

def test_corrupted_file_recovery(storage, temp_storage_dir):
    """Corrupted JSON file should be handled gracefully."""
    # Create corrupted file
    profile_path = Path(temp_storage_dir) / "profile.json"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    with open(profile_path, 'w') as f:
        f.write("{invalid json")

    # Should handle gracefully and overwrite
    proposals = [
        create_mock_proposal("033", "Test", "universal", "preference")
    ]

    results = storage.store_batch(proposals)

    # Should succeed
    assert results[str(profile_path)] == 1

    # File should now be valid
    with open(profile_path, 'r') as f:
        data = json.load(f)
        assert len(data) == 1


# Integration test

def test_full_integration(temp_storage_dir):
    """Full integration test with multiple proposals."""
    storage = MemoryStorage(base_dir=temp_storage_dir)

    # Mixed proposals
    proposals = [
        create_mock_proposal("034", "Pref 1", "universal", "preference", 0.95),
        create_mock_proposal("035", "Pref 2", "universal", "preference", 0.88),
        create_mock_proposal("036", "Corr 1", "universal", "correction", 0.92),
        create_mock_proposal("037", "Go 1", "language:go", "rule", 0.90),
        create_mock_proposal("038", "Py 1", "language:python", "rule", 0.85),
        create_mock_proposal("039", "Proj 1", "project:cerberus", "rule", 0.93)
    ]

    # Store batch
    results = storage.store_batch(proposals)

    # Verify files created
    assert len(results) == 5

    # Verify stats
    stats = storage.get_stats()
    assert stats["profile.json"] == 2
    assert stats["corrections.json"] == 1
    assert stats["languages/go.json"] == 1
    assert stats["languages/python.json"] == 1
    assert stats["projects/cerberus/decisions.json"] == 1

    # Verify metadata in one file
    profile_path = Path(temp_storage_dir) / "profile.json"
    with open(profile_path, 'r') as f:
        data = json.load(f)
        assert len(data) == 2
        for memory in data:
            assert memory["access_count"] == 0
            assert memory["confidence"] in [0.95, 0.88]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
