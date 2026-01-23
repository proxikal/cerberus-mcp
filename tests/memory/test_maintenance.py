"""
Tests for Phase 11: Maintenance & Health

Test scenarios:
1. Stale detection (60+ days)
2. Archive old memories (180+ days)
3. Contradiction detection
4. Redundancy detection
5. Obsolete pattern detection
6. Cross-project promotion
7. Health status calculation
8. Auto-maintenance
9. Archive system
10. Conflict severity
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from cerberus.memory.maintenance import (
    StaleMemoryDetector,
    ConflictDetector,
    PromotionDetector,
    MemoryHealthCheck,
    MemoryHealth,
    ConflictDetection,
    PromotionCandidate,
    scheduled_maintenance
)


@pytest.fixture
def temp_memory_dir():
    """Create temporary memory directory with test data."""
    with TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir)

        # Create directory structure
        (base_path / "languages").mkdir(exist_ok=True)
        (base_path / "projects" / "proj1").mkdir(parents=True, exist_ok=True)
        (base_path / "projects" / "proj2").mkdir(parents=True, exist_ok=True)
        (base_path / "projects" / "proj3").mkdir(parents=True, exist_ok=True)

        yield base_path


def create_memory(content: str, category: str = "preference", scope: str = "universal",
                  timestamp: datetime = None, last_occurred: datetime = None) -> dict:
    """Helper to create memory dict."""
    mem = {
        "id": f"mem-{hash(content) % 100000}",
        "content": content,
        "category": category,
        "scope": scope,
        "confidence": 0.9,
    }

    if timestamp:
        mem["timestamp"] = timestamp.isoformat()
    else:
        mem["timestamp"] = datetime.now().isoformat()

    if last_occurred:
        mem["last_occurred"] = last_occurred.isoformat()

    return mem


# ===== STALE DETECTION TESTS =====

def test_detect_stale_memories(temp_memory_dir):
    """Test detection of memories not used in 60+ days."""
    # Create memories with different ages
    now = datetime.now()

    memories = [
        create_memory("Recent rule", timestamp=now),
        create_memory("Old rule", category="decision", timestamp=now - timedelta(days=70)),
        create_memory("Ancient rule", category="decision", timestamp=now - timedelta(days=200)),
    ]

    # Save to universal
    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    detector = StaleMemoryDetector(temp_memory_dir)
    stale = detector.detect_stale()

    # Should detect 2 stale (70 days, 200 days)
    assert len(stale) == 2
    assert stale[0]["days_stale"] >= 70
    assert stale[1]["days_stale"] >= 200


def test_stale_archive_threshold(temp_memory_dir):
    """Test that only 180+ day memories are marked for archive."""
    now = datetime.now()

    memories = [
        create_memory("Old rule", category="decision", timestamp=now - timedelta(days=70)),
        create_memory("Ancient rule", category="decision", timestamp=now - timedelta(days=200)),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    detector = StaleMemoryDetector(temp_memory_dir)
    stale = detector.detect_stale()

    # 70 days: stale but not archive
    assert not stale[0]["should_archive"]

    # 200 days: archive
    assert stale[1]["should_archive"]


def test_preferences_never_stale(temp_memory_dir):
    """Test that preferences are never flagged as stale."""
    now = datetime.now()

    memories = [
        create_memory("Keep output concise", category="preference", timestamp=now - timedelta(days=300)),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    detector = StaleMemoryDetector(temp_memory_dir)
    stale = detector.detect_stale()

    # Preferences never stale
    assert len(stale) == 0


def test_archive_stale_memories(temp_memory_dir):
    """Test archiving of old memories."""
    now = datetime.now()

    memories = [
        create_memory("Ancient rule 1", category="decision", timestamp=now - timedelta(days=200)),
        create_memory("Ancient rule 2", category="decision", timestamp=now - timedelta(days=250)),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    detector = StaleMemoryDetector(temp_memory_dir)
    stale = detector.detect_stale()
    archived_count = detector.archive_stale(stale)

    # Should archive 2
    assert archived_count == 2

    # Archive file should exist
    archive_dir = temp_memory_dir / "archive"
    assert archive_dir.exists()

    archive_files = list(archive_dir.glob("archived-*.json"))
    assert len(archive_files) == 1

    # Check archive content
    with open(archive_files[0]) as f:
        archived = json.load(f)
    assert len(archived) == 2


# ===== CONFLICT DETECTION TESTS =====

def test_detect_contradiction(temp_memory_dir):
    """Test detection of contradicting rules."""
    memories = [
        create_memory("Always use tabs for indentation", scope="universal"),
        create_memory("Never use tabs, prefer spaces", scope="universal"),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    detector = ConflictDetector(temp_memory_dir)
    conflicts = detector.detect_conflicts()

    # Should detect 1 contradiction
    contradictions = [c for c in conflicts if c.conflict_type == "contradiction"]
    assert len(contradictions) == 1
    assert contradictions[0].severity == "high"


def test_detect_redundancy(temp_memory_dir):
    """Test detection of duplicate/similar rules."""
    memories = [
        create_memory("Always add error handling to API calls", scope="universal"),
        create_memory("Always add error handling to API call", scope="universal"),  # Nearly identical
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    detector = ConflictDetector(temp_memory_dir)
    conflicts = detector.detect_conflicts()

    # Should detect redundancy (high similarity)
    redundancies = [c for c in conflicts if c.conflict_type == "redundancy"]
    assert len(redundancies) == 1
    assert redundancies[0].severity == "low"


def test_detect_obsolete(temp_memory_dir):
    """Test detection of obsolete patterns."""
    memories = [
        create_memory("Always use jQuery for DOM manipulation", scope="universal"),
        create_memory("Prefer python2 for compatibility", scope="universal"),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    detector = ConflictDetector(temp_memory_dir)
    conflicts = detector.detect_conflicts()

    # Should detect 2 obsolete
    obsolete = [c for c in conflicts if c.conflict_type == "obsolete"]
    assert len(obsolete) == 2
    assert all(c.severity == "medium" for c in obsolete)


def test_contradiction_same_scope_only(temp_memory_dir):
    """Test that contradictions only detected within same scope."""
    memories_universal = [
        create_memory("Always use tabs", scope="universal"),
    ]

    memories_project = [
        create_memory("Never use tabs", scope="project:test"),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories_universal, f)

    (temp_memory_dir / "projects" / "test").mkdir(parents=True, exist_ok=True)
    with open(temp_memory_dir / "projects" / "test" / "decisions.json", "w") as f:
        json.dump(memories_project, f)

    detector = ConflictDetector(temp_memory_dir)
    conflicts = detector.detect_conflicts()

    # Should NOT detect contradiction (different scopes)
    contradictions = [c for c in conflicts if c.conflict_type == "contradiction"]
    assert len(contradictions) == 0


# ===== PROMOTION DETECTION TESTS =====

def test_detect_cross_project_pattern(temp_memory_dir):
    """Test detection of patterns in 3+ projects."""
    # Same rule in 3 projects
    rule = "Always add error handling to API calls"

    for proj in ["proj1", "proj2", "proj3"]:
        memories = [create_memory(rule, scope=f"project:{proj}")]
        proj_dir = temp_memory_dir / "projects" / proj
        proj_dir.mkdir(parents=True, exist_ok=True)
        with open(proj_dir / "decisions.json", "w") as f:
            json.dump(memories, f)

    detector = PromotionDetector(temp_memory_dir)
    candidates = detector.detect_candidates()

    # Should detect 1 promotion candidate
    assert len(candidates) == 1
    assert candidates[0].confidence >= 0.3
    assert "3 projects" in candidates[0].reason


def test_suggest_universal_scope(temp_memory_dir):
    """Test that generic patterns suggest universal scope."""
    rule = "Keep code modular and testable"

    for proj in ["proj1", "proj2", "proj3"]:
        memories = [create_memory(rule, scope=f"project:{proj}")]
        proj_dir = temp_memory_dir / "projects" / proj
        proj_dir.mkdir(parents=True, exist_ok=True)
        with open(proj_dir / "decisions.json", "w") as f:
            json.dump(memories, f)

    detector = PromotionDetector(temp_memory_dir)
    candidates = detector.detect_candidates()

    # Should suggest universal scope (no language keywords)
    assert len(candidates) == 1
    assert candidates[0].suggested_scope == "universal"


def test_suggest_language_scope(temp_memory_dir):
    """Test that language-specific patterns suggest language scope."""
    rule = "Always handle panic with defer recover in goroutines"

    for proj in ["proj1", "proj2", "proj3"]:
        memories = [create_memory(rule, scope=f"project:{proj}")]
        proj_dir = temp_memory_dir / "projects" / proj
        proj_dir.mkdir(parents=True, exist_ok=True)
        with open(proj_dir / "decisions.json", "w") as f:
            json.dump(memories, f)

    detector = PromotionDetector(temp_memory_dir)
    candidates = detector.detect_candidates()

    # Should suggest language:go (has "panic", "goroutine", "defer")
    assert len(candidates) == 1
    assert candidates[0].suggested_scope == "language:go"


def test_no_promotion_with_fewer_than_3_projects(temp_memory_dir):
    """Test that patterns in < 3 projects are not promoted."""
    rule = "Use custom validation"

    for proj in ["proj1", "proj2"]:  # Only 2 projects
        memories = [create_memory(rule, scope=f"project:{proj}")]
        proj_dir = temp_memory_dir / "projects" / proj
        proj_dir.mkdir(parents=True, exist_ok=True)
        with open(proj_dir / "decisions.json", "w") as f:
            json.dump(memories, f)

    detector = PromotionDetector(temp_memory_dir)
    candidates = detector.detect_candidates()

    # Should not detect any promotion candidates
    assert len(candidates) == 0


# ===== HEALTH CHECK TESTS =====

def test_health_status_healthy(temp_memory_dir):
    """Test healthy status with few issues."""
    memories = [
        create_memory("Rule 1"),
        create_memory("Rule 2"),
        create_memory("Rule 3"),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    health_check = MemoryHealthCheck(temp_memory_dir)
    health = health_check.run_health_check()

    assert health.status == "healthy"
    assert health.total_memories == 3
    assert health.stale_count == 0
    assert health.conflict_count == 0


def test_health_status_needs_attention(temp_memory_dir):
    """Test needs_attention status with moderate issues."""
    now = datetime.now()

    # Create conflicts (need > 5)
    memories = [
        create_memory("Always use X"),
        create_memory("Never use X"),
        create_memory("Rule 1"),
        create_memory("Rule 1"),  # Duplicate
        create_memory("Rule 2"),
        create_memory("Rule 2"),  # Duplicate
        create_memory("Rule 3"),
        create_memory("Rule 3"),  # Duplicate
        create_memory("Rule 4"),
        create_memory("Rule 4"),  # Duplicate
        create_memory("Rule 5"),
        create_memory("Rule 5"),  # Duplicate
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    health_check = MemoryHealthCheck(temp_memory_dir)
    health = health_check.run_health_check()

    # Should be needs_attention (conflicts > 5)
    assert health.status == "needs_attention"
    assert health.conflict_count >= 5


def test_health_status_critical(temp_memory_dir):
    """Test critical status with many stale memories."""
    now = datetime.now()

    # Create mostly stale memories
    memories = [
        create_memory("Old rule 1", category="decision", timestamp=now - timedelta(days=100)),
        create_memory("Old rule 2", category="decision", timestamp=now - timedelta(days=100)),
        create_memory("Recent rule"),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    health_check = MemoryHealthCheck(temp_memory_dir)
    health = health_check.run_health_check()

    # Should be critical (>50% stale)
    assert health.status == "critical"
    assert health.stale_count == 2


# ===== AUTO-MAINTENANCE TESTS =====

def test_auto_maintain_archives_stale(temp_memory_dir):
    """Test that auto-maintenance archives old memories."""
    now = datetime.now()

    memories = [
        create_memory("Ancient rule", category="decision", timestamp=now - timedelta(days=200)),
        create_memory("Recent rule"),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    health_check = MemoryHealthCheck(temp_memory_dir)
    results = health_check.auto_maintain(approve_promotions=False)

    assert results["archived"] == 1


def test_auto_maintain_reports_conflicts(temp_memory_dir):
    """Test that auto-maintenance reports conflicts."""
    memories = [
        create_memory("Always use X"),
        create_memory("Never use X"),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    health_check = MemoryHealthCheck(temp_memory_dir)
    results = health_check.auto_maintain(approve_promotions=False)

    # Should report conflict (but not auto-fix)
    assert results["conflicts"] >= 1


def test_auto_maintain_promotes_patterns(temp_memory_dir):
    """Test that auto-maintenance can promote high-confidence patterns."""
    rule = "Always add tests"

    for proj in ["proj1", "proj2", "proj3", "proj4"]:
        memories = [create_memory(rule, scope=f"project:{proj}")]
        proj_dir = temp_memory_dir / "projects" / proj
        proj_dir.mkdir(parents=True, exist_ok=True)
        with open(proj_dir / "decisions.json", "w") as f:
            json.dump(memories, f)

    health_check = MemoryHealthCheck(temp_memory_dir)
    results = health_check.auto_maintain(approve_promotions=True)

    # Should promote (confidence = 0.4 for 4 projects, threshold 0.5 not met)
    # Actually, let's check if it was promoted
    # With 4 projects, confidence = min(4/10, 1.0) = 0.4, which is < 0.5
    # So it won't be promoted

    # Let's create 6 projects to get confidence > 0.5
    for proj in ["proj5", "proj6"]:
        memories = [create_memory(rule, scope=f"project:{proj}")]
        proj_dir = temp_memory_dir / "projects" / proj
        proj_dir.mkdir(parents=True, exist_ok=True)
        with open(proj_dir / "decisions.json", "w") as f:
            json.dump(memories, f)

    results = health_check.auto_maintain(approve_promotions=True)

    # With 6 projects, confidence = 0.6 > 0.5, should promote
    assert results["promotions"] >= 1


# ===== SCHEDULED MAINTENANCE TEST =====

def test_scheduled_maintenance(temp_memory_dir):
    """Test scheduled maintenance function."""
    now = datetime.now()

    memories = [
        create_memory("Recent rule"),
        create_memory("Old rule", category="decision", timestamp=now - timedelta(days=100)),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    health = scheduled_maintenance(base_path=temp_memory_dir, approve_promotions=False)

    assert isinstance(health, MemoryHealth)
    assert health.total_memories == 2
    assert health.stale_count >= 1


# ===== EDGE CASES =====

def test_empty_memory_directory(temp_memory_dir):
    """Test with no memories."""
    health_check = MemoryHealthCheck(temp_memory_dir)
    health = health_check.run_health_check()

    assert health.total_memories == 0
    assert health.status == "healthy"


def test_load_memories_from_all_scopes(temp_memory_dir):
    """Test that detector loads from all scope locations."""
    # Universal
    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump([create_memory("Universal rule")], f)

    # Language
    (temp_memory_dir / "languages").mkdir(exist_ok=True)
    with open(temp_memory_dir / "languages" / "python.json", "w") as f:
        json.dump([create_memory("Python rule", scope="language:python")], f)

    # Project
    (temp_memory_dir / "projects" / "test").mkdir(parents=True, exist_ok=True)
    with open(temp_memory_dir / "projects" / "test" / "decisions.json", "w") as f:
        json.dump([create_memory("Project rule", scope="project:test")], f)

    detector = StaleMemoryDetector(temp_memory_dir)
    all_memories = detector._load_all_memories()

    # Should load all 3
    assert len(all_memories) == 3


def test_conflicting_memories_different_categories(temp_memory_dir):
    """Test that conflicts are detected regardless of category."""
    memories = [
        create_memory("Always use X", category="preference"),
        create_memory("Never use X", category="rule"),
    ]

    with open(temp_memory_dir / "profile.json", "w") as f:
        json.dump(memories, f)

    detector = ConflictDetector(temp_memory_dir)
    conflicts = detector.detect_conflicts()

    # Should detect contradiction (category doesn't matter)
    contradictions = [c for c in conflicts if c.conflict_type == "contradiction"]
    assert len(contradictions) == 1


def test_promotion_with_no_projects(temp_memory_dir):
    """Test promotion detector with no project memories."""
    detector = PromotionDetector(temp_memory_dir)
    candidates = detector.detect_candidates()

    # Should return empty list
    assert len(candidates) == 0
