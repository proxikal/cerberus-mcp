"""
Unit tests for Phase 18: Approval Optimization (A/B)

Tests:
- Auto-approval algorithm (18A)
- Batching algorithm (18A)
- Theme extraction (18A)
- Optimized approval interface (18B)
- Batch mode (18B)
- Approval history learning (18B)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from cerberus.memory.approval_optimizer import (
    ApprovalBatch,
    ApprovalStrategy,
    ApprovalResult,
    auto_approve_high_confidence,
    batch_similar_proposals,
    run_optimized_approval,
    batch_mode_approval,
    learn_from_approval_history,
    get_all_approved_ids,
    _is_safe_to_auto_approve,
    _extract_theme
)
from cerberus.memory.proposal_engine import MemoryProposal


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def high_confidence_proposals():
    """High-confidence proposals (0.9+)."""
    return [
        MemoryProposal(
            id="prop-1",
            content="Use early returns over nested conditionals",
            category="preference",
            scope="universal",
            confidence=0.95,
            rationale="Repeated pattern",
            source_variants=["Use early returns", "Avoid nested ifs"],
            priority=1.0
        ),
        MemoryProposal(
            id="prop-2",
            content="Always use async/await for I/O operations",
            category="rule",
            scope="language:python",
            confidence=0.92,
            rationale="Consistent pattern",
            source_variants=["Use async/await"],
            priority=0.9
        )
    ]


@pytest.fixture
def medium_confidence_proposals():
    """Medium-confidence proposals (0.6-0.8)."""
    return [
        MemoryProposal(
            id="prop-3",
            content="Prefer docstrings for public functions",
            category="preference",
            scope="universal",
            confidence=0.75,
            rationale="Good practice",
            source_variants=["Add docstrings"],
            priority=0.7
        ),
        MemoryProposal(
            id="prop-4",
            content="Use meaningful variable names",
            category="preference",
            scope="universal",
            confidence=0.7,
            rationale="Common feedback",
            source_variants=["Better naming"],
            priority=0.6
        )
    ]


@pytest.fixture
def low_confidence_proposals():
    """Low-confidence proposals (< 0.5)."""
    return [
        MemoryProposal(
            id="prop-5",
            content="Maybe use tabs instead of spaces",
            category="preference",
            scope="universal",
            confidence=0.3,
            rationale="Unclear",
            source_variants=["Tabs?"],
            priority=0.2
        )
    ]


@pytest.fixture
def mixed_proposals(high_confidence_proposals, medium_confidence_proposals, low_confidence_proposals):
    """Mixed confidence proposals."""
    return high_confidence_proposals + medium_confidence_proposals + low_confidence_proposals


@pytest.fixture
def negation_proposal():
    """Proposal with negation (higher risk)."""
    return MemoryProposal(
        id="prop-neg",
        content="Never use global variables in production code",
        category="rule",
        scope="universal",
        confidence=0.95,
        rationale="Critical rule",
        source_variants=["Avoid globals"],
        priority=1.0
    )


@pytest.fixture
def long_proposal():
    """Proposal with long content (> 200 chars)."""
    return MemoryProposal(
        id="prop-long",
        content="Use dependency injection pattern for all service classes to ensure testability and maintainability, following SOLID principles and ensuring proper separation of concerns across the entire application architecture",
        category="rule",
        scope="universal",
        confidence=0.95,
        rationale="Architecture rule",
        source_variants=["DI pattern"],
        priority=1.0
    )


@pytest.fixture
def similar_style_proposals():
    """Similar proposals about code style (for batching)."""
    return [
        MemoryProposal(
            id="style-1",
            content="Use 2-space indentation",
            category="preference",
            scope="universal",
            confidence=0.8,
            rationale="Consistent",
            source_variants=["2 spaces"],
            priority=0.8
        ),
        MemoryProposal(
            id="style-2",
            content="Format code with prettier",
            category="preference",
            scope="universal",
            confidence=0.85,
            rationale="Automation",
            source_variants=["Use prettier"],
            priority=0.85
        ),
        MemoryProposal(
            id="style-3",
            content="Keep lines under 80 characters",
            category="preference",
            scope="universal",
            confidence=0.75,
            rationale="Readability",
            source_variants=["80 char limit"],
            priority=0.75
        )
    ]


@pytest.fixture
def similar_error_proposals():
    """Similar proposals about error handling (for batching)."""
    return [
        MemoryProposal(
            id="error-1",
            content="Always log exceptions with context",
            category="rule",
            scope="universal",
            confidence=0.9,
            rationale="Debugging",
            source_variants=["Log errors"],
            priority=0.9
        ),
        MemoryProposal(
            id="error-2",
            content="Use custom error types for domain errors",
            category="preference",
            scope="project:cerberus",
            confidence=0.8,
            rationale="Better errors",
            source_variants=["Custom errors"],
            priority=0.8
        )
    ]


# ============================================================================
# Phase 18A: Auto-Approval Algorithm Tests
# ============================================================================


def test_auto_approve_high_confidence_basic(high_confidence_proposals):
    """Test basic auto-approval of high-confidence proposals."""
    auto_ids, remaining, skipped = auto_approve_high_confidence(
        high_confidence_proposals,
        threshold=0.9
    )

    assert len(auto_ids) == 2
    assert "prop-1" in auto_ids
    assert "prop-2" in auto_ids
    assert len(remaining) == 0
    assert len(skipped) == 0


def test_auto_approve_with_remaining(mixed_proposals):
    """Test auto-approval leaves medium-confidence proposals."""
    auto_ids, remaining, skipped = auto_approve_high_confidence(
        mixed_proposals,
        threshold=0.9
    )

    # High-confidence auto-approved
    assert len(auto_ids) == 2

    # Medium-confidence remain for review
    assert len(remaining) == 2
    assert remaining[0].id == "prop-3"
    assert remaining[1].id == "prop-4"

    # Low-confidence skipped
    assert len(skipped) == 1
    assert skipped[0].id == "prop-5"


def test_auto_approve_skips_low_confidence(mixed_proposals):
    """Test auto-approval skips low-confidence proposals."""
    auto_ids, remaining, skipped = auto_approve_high_confidence(
        mixed_proposals,
        threshold=0.9
    )

    # Low-confidence in skipped
    assert len(skipped) == 1
    assert skipped[0].id == "prop-5"

    # Not in auto or remaining
    all_ids = auto_ids + [p.id for p in remaining]
    assert "prop-5" not in all_ids


def test_auto_approve_custom_threshold():
    """Test auto-approval with custom threshold."""
    proposals = [
        MemoryProposal(
            id="p1", content="Short rule", category="rule",
            scope="universal", confidence=0.85, rationale="", source_variants=[], priority=1.0
        ),
        MemoryProposal(
            id="p2", content="Another rule", category="rule",
            scope="universal", confidence=0.8, rationale="", source_variants=[], priority=1.0
        )
    ]

    # Threshold 0.85: only p1 approved
    auto_ids, remaining, skipped = auto_approve_high_confidence(proposals, threshold=0.85)
    assert len(auto_ids) == 1
    assert "p1" in auto_ids

    # Threshold 0.8: both approved
    auto_ids, remaining, skipped = auto_approve_high_confidence(proposals, threshold=0.8)
    assert len(auto_ids) == 2


def test_is_safe_to_auto_approve_negation(negation_proposal):
    """Test safety check rejects negation patterns."""
    assert not _is_safe_to_auto_approve(negation_proposal)


def test_is_safe_to_auto_approve_long_content(long_proposal):
    """Test safety check rejects long content."""
    assert not _is_safe_to_auto_approve(long_proposal)


def test_is_safe_to_auto_approve_safe_proposal(high_confidence_proposals):
    """Test safety check approves safe proposals."""
    assert _is_safe_to_auto_approve(high_confidence_proposals[0])


def test_auto_approve_respects_safety_checks(negation_proposal, long_proposal):
    """Test auto-approval respects safety checks."""
    proposals = [negation_proposal, long_proposal]

    auto_ids, remaining, skipped = auto_approve_high_confidence(proposals, threshold=0.9)

    # Both high-confidence but unsafe
    assert len(auto_ids) == 0
    assert len(remaining) == 2
    assert len(skipped) == 0


# ============================================================================
# Phase 18A: Batching Algorithm Tests
# ============================================================================


def test_batch_similar_proposals_style(similar_style_proposals):
    """Test batching groups similar style proposals."""
    batches = batch_similar_proposals(similar_style_proposals)

    # Should create 1-2 batches (style-related)
    assert 1 <= len(batches) <= 2
    assert all(isinstance(b, ApprovalBatch) for b in batches)


def test_batch_similar_proposals_mixed(similar_style_proposals, similar_error_proposals):
    """Test batching separates different themes."""
    all_proposals = similar_style_proposals + similar_error_proposals

    batches = batch_similar_proposals(all_proposals)

    # Should create 2+ batches (style vs error handling)
    assert len(batches) >= 2

    # Verify themes extracted
    themes = [b.theme for b in batches]
    assert any("style" in t.lower() or "general" in t.lower() for t in themes)


def test_batch_avg_confidence(similar_style_proposals):
    """Test batch calculates average confidence correctly."""
    batches = batch_similar_proposals(similar_style_proposals)

    for batch in batches:
        expected_avg = sum(p.confidence for p in batch.proposals) / len(batch.proposals)
        assert abs(batch.avg_confidence - expected_avg) < 0.01


def test_batch_recommended_action_high():
    """Test batch recommends approve_all for high confidence."""
    proposals = [
        MemoryProposal(
            id=f"p{i}", content=f"Rule {i}", category="rule",
            scope="universal", confidence=0.9, rationale="", source_variants=[], priority=1.0
        )
        for i in range(4)
    ]

    batches = batch_similar_proposals(proposals)

    # High avg confidence -> approve_all
    assert any(b.recommended_action == "approve_all" for b in batches)


def test_batch_recommended_action_medium():
    """Test batch recommends review for medium confidence."""
    proposals = [
        MemoryProposal(
            id=f"p{i}", content=f"Rule {i}", category="rule",
            scope="universal", confidence=0.7, rationale="", source_variants=[], priority=1.0
        )
        for i in range(4)
    ]

    batches = batch_similar_proposals(proposals)

    # Medium avg confidence -> review
    assert any(b.recommended_action == "review" for b in batches)


def test_batch_too_few_proposals():
    """Test batching with too few proposals (≤3)."""
    proposals = [
        MemoryProposal(
            id="p1", content="Rule 1", category="rule",
            scope="universal", confidence=0.8, rationale="", source_variants=[], priority=1.0
        ),
        MemoryProposal(
            id="p2", content="Rule 2", category="rule",
            scope="universal", confidence=0.7, rationale="", source_variants=[], priority=1.0
        )
    ]

    batches = batch_similar_proposals(proposals)

    # Too few to batch -> single batch with all proposals
    assert len(batches) == 1
    assert len(batches[0].proposals) == 2
    assert batches[0].theme == "General"


def test_extract_theme_style():
    """Test theme extraction for style keywords."""
    proposals = [
        MemoryProposal(
            id="p1", content="Use consistent spacing", category="preference",
            scope="universal", confidence=0.8, rationale="", source_variants=[], priority=1.0
        ),
        MemoryProposal(
            id="p2", content="Format code properly", category="preference",
            scope="universal", confidence=0.8, rationale="", source_variants=[], priority=1.0
        )
    ]

    theme = _extract_theme(proposals)
    assert theme == "Code style"


def test_extract_theme_error():
    """Test theme extraction for error keywords."""
    proposals = [
        MemoryProposal(
            id="p1", content="Handle exceptions gracefully", category="rule",
            scope="universal", confidence=0.8, rationale="", source_variants=[], priority=1.0
        ),
        MemoryProposal(
            id="p2", content="Log errors with context", category="rule",
            scope="universal", confidence=0.8, rationale="", source_variants=[], priority=1.0
        )
    ]

    theme = _extract_theme(proposals)
    assert theme == "Error handling"


def test_extract_theme_no_keywords():
    """Test theme extraction with no matching keywords."""
    proposals = [
        MemoryProposal(
            id="p1", content="Some random rule", category="rule",
            scope="universal", confidence=0.8, rationale="", source_variants=[], priority=1.0
        )
    ]

    theme = _extract_theme(proposals)
    assert theme == "General"


# ============================================================================
# Phase 18B: Optimized Approval Interface Tests
# ============================================================================


@patch('cerberus.memory.approval_optimizer._show_individual_approval')
def test_run_optimized_approval_all_auto(mock_approval, high_confidence_proposals):
    """Test optimized approval when all proposals auto-approved."""
    result = run_optimized_approval(high_confidence_proposals, interactive=True)

    assert len(result.auto_approved) == 2
    assert len(result.user_approved) == 0
    assert len(result.skipped) == 0
    assert result.stats["total"] == 2
    assert result.stats["auto"] == 2

    # Individual approval not called (all auto-approved)
    mock_approval.assert_not_called()


@patch('cerberus.memory.approval_optimizer._show_individual_approval')
def test_run_optimized_approval_mixed(mock_approval, mixed_proposals):
    """Test optimized approval with mixed confidence proposals."""
    # Mock user approval of medium-confidence
    mock_approval.return_value = ["prop-3", "prop-4"]

    result = run_optimized_approval(mixed_proposals, interactive=True)

    # High-confidence auto-approved
    assert len(result.auto_approved) == 2

    # Medium-confidence user-approved (mocked)
    assert len(result.user_approved) == 2

    # Low-confidence skipped
    assert len(result.skipped) == 1
    assert "prop-5" in result.skipped


@patch('cerberus.memory.approval_optimizer._show_batched_approval')
def test_run_optimized_approval_batching(mock_batched, similar_style_proposals):
    """Test optimized approval uses batching for 4+ proposals."""
    # Add one more proposal to trigger batching (need > 3)
    proposals = similar_style_proposals + [
        MemoryProposal(
            id="style-4",
            content="Use consistent naming",
            category="preference",
            scope="universal",
            confidence=0.8,
            rationale="Consistency",
            source_variants=["Naming"],
            priority=0.8
        )
    ]

    mock_batched.return_value = ["style-1", "style-2"]

    strategy = ApprovalStrategy(
        auto_approve_threshold=0.95,  # None meet this threshold
        batch_similar=True
    )

    result = run_optimized_approval(proposals, strategy=strategy, interactive=True)

    # Batching was called (4+ proposals)
    mock_batched.assert_called_once()

    # User approved via batching
    assert len(result.user_approved) == 2


@patch('cerberus.memory.approval_optimizer._show_individual_approval')
def test_run_optimized_approval_no_batching(mock_approval):
    """Test optimized approval skips batching for 3 or fewer proposals."""
    proposals = [
        MemoryProposal(
            id=f"p{i}", content=f"Rule {i}", category="rule",
            scope="universal", confidence=0.7, rationale="", source_variants=[], priority=1.0
        )
        for i in range(3)
    ]

    mock_approval.return_value = ["p0", "p1"]

    strategy = ApprovalStrategy(
        auto_approve_threshold=0.95,  # None meet this
        batch_similar=True
    )

    result = run_optimized_approval(proposals, strategy=strategy, interactive=True)

    # Individual approval called (not batching)
    mock_approval.assert_called_once()


def test_run_optimized_approval_non_interactive(mixed_proposals):
    """Test optimized approval in non-interactive mode (batch mode)."""
    result = run_optimized_approval(mixed_proposals, interactive=False)

    # Only high-confidence auto-approved
    assert len(result.auto_approved) == 2

    # Remaining skipped (non-interactive)
    assert len(result.skipped) == 3  # 2 medium + 1 low
    assert len(result.user_approved) == 0


def test_run_optimized_approval_empty_proposals():
    """Test optimized approval with no proposals."""
    result = run_optimized_approval([], interactive=True)

    assert len(result.auto_approved) == 0
    assert len(result.user_approved) == 0
    assert result.stats["total"] == 0


def test_run_optimized_approval_custom_strategy():
    """Test optimized approval with custom strategy."""
    proposals = [
        MemoryProposal(
            id="p1", content="Rule 1", category="rule",
            scope="universal", confidence=0.85, rationale="", source_variants=[], priority=1.0
        ),
        MemoryProposal(
            id="p2", content="Rule 2", category="rule",
            scope="universal", confidence=0.55, rationale="", source_variants=[], priority=1.0
        ),
        MemoryProposal(
            id="p3", content="Rule 3", category="rule",
            scope="universal", confidence=0.45, rationale="", source_variants=[], priority=1.0
        )
    ]

    strategy = ApprovalStrategy(
        auto_approve_threshold=0.85,  # p1 auto-approved
        review_threshold=0.55,        # p2 shown for review
        skip_threshold=0.5            # p3 skipped
    )

    with patch('cerberus.memory.approval_optimizer._show_individual_approval') as mock_approval:
        mock_approval.return_value = ["p2"]
        result = run_optimized_approval(proposals, strategy=strategy, interactive=True)

    assert len(result.auto_approved) == 1
    assert "p1" in result.auto_approved
    assert len(result.user_approved) == 1
    assert "p2" in result.user_approved
    assert len(result.skipped) == 1
    assert "p3" in result.skipped


# ============================================================================
# Phase 18B: Batch Mode Tests
# ============================================================================


def test_batch_mode_approval_auto_approves(mixed_proposals):
    """Test batch mode auto-approves high-confidence proposals."""
    approved_ids = batch_mode_approval(mixed_proposals, threshold=0.85)

    # Only proposals >= 0.85 auto-approved
    assert len(approved_ids) == 2
    assert "prop-1" in approved_ids
    assert "prop-2" in approved_ids


def test_batch_mode_approval_custom_threshold():
    """Test batch mode with custom threshold."""
    proposals = [
        MemoryProposal(
            id="p1", content="Rule 1", category="rule",
            scope="universal", confidence=0.9, rationale="", source_variants=[], priority=1.0
        ),
        MemoryProposal(
            id="p2", content="Rule 2", category="rule",
            scope="universal", confidence=0.8, rationale="", source_variants=[], priority=1.0
        )
    ]

    # Threshold 0.85: only p1
    approved = batch_mode_approval(proposals, threshold=0.85)
    assert len(approved) == 1

    # Threshold 0.8: both
    approved = batch_mode_approval(proposals, threshold=0.8)
    assert len(approved) == 2


def test_batch_mode_approval_respects_safety(negation_proposal):
    """Test batch mode respects safety checks."""
    proposals = [negation_proposal]

    approved = batch_mode_approval(proposals, threshold=0.9)

    # High-confidence but unsafe (negation)
    assert len(approved) == 0


# ============================================================================
# Phase 18B: Approval History Learning Tests
# ============================================================================


def test_learn_from_approval_history_no_db(tmp_path):
    """Test history learning with no database (returns defaults)."""
    db_path = tmp_path / "nonexistent.db"

    strategy = learn_from_approval_history(db_path)

    # Should return default strategy
    assert strategy.auto_approve_threshold == 0.9
    assert strategy.review_threshold == 0.6
    assert strategy.skip_threshold == 0.5


def test_learn_from_approval_history_default():
    """Test history learning without db_path (uses default)."""
    strategy = learn_from_approval_history()

    # Should return default strategy (no history yet)
    assert isinstance(strategy, ApprovalStrategy)


# ============================================================================
# Helper Function Tests
# ============================================================================


def test_get_all_approved_ids():
    """Test get_all_approved_ids helper."""
    result = ApprovalResult(
        auto_approved=["a1", "a2"],
        user_approved=["u1", "u2"],
        user_rejected=[],
        skipped=[],
        stats={}
    )

    all_ids = get_all_approved_ids(result)

    assert len(all_ids) == 4
    assert "a1" in all_ids
    assert "u2" in all_ids


# ============================================================================
# Integration Tests
# ============================================================================


@patch('cerberus.memory.approval_optimizer._show_individual_approval')
def test_full_optimized_workflow(mock_approval, mixed_proposals):
    """Test full optimized approval workflow."""
    mock_approval.return_value = ["prop-3"]

    strategy = ApprovalStrategy(
        auto_approve_threshold=0.9,
        review_threshold=0.6,
        skip_threshold=0.5
    )

    result = run_optimized_approval(mixed_proposals, strategy=strategy, interactive=True)

    # Verify complete workflow
    assert len(result.auto_approved) == 2  # prop-1, prop-2 (0.95, 0.92)
    assert len(result.user_approved) == 1  # prop-3 (0.75)
    assert len(result.user_rejected) == 1  # prop-4 (0.7) not approved by user
    assert len(result.skipped) == 1        # prop-5 (0.3)

    # Verify stats
    assert result.stats["total"] == 5
    assert result.stats["auto"] == 2
    assert result.stats["approved"] == 1
    assert result.stats["rejected"] == 1
    assert result.stats["skipped"] == 1
