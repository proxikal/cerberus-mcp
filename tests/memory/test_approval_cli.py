"""
Tests for Phase 4: CLI Approval Interface

Validates:
- Batch mode auto-approval (>= 0.9 confidence)
- Interactive mode with bulk operations
- Input validation
- Approval timing (< 30s requirement)
- No special dependencies (standard library only)
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from cerberus.memory.approval_cli import (
    ApprovalCLI,
    ApprovalResult,
    approve_proposals
)
from cerberus.memory.proposal_engine import MemoryProposal


# Test fixtures

def create_mock_proposal(
    id_suffix: str,
    content: str,
    confidence: float,
    scope: str = "universal",
    category: str = "preference"
) -> MemoryProposal:
    """Create a mock memory proposal."""
    return MemoryProposal(
        id=f"prop-{id_suffix}",
        category=category,
        scope=scope,
        content=content,
        rationale="Test rationale",
        source_variants=[content],
        confidence=confidence,
        priority=3
    )


@pytest.fixture
def sample_proposals():
    """Create sample proposals with varying confidence."""
    return [
        create_mock_proposal("001", "Keep summaries concise", 0.95),
        create_mock_proposal("002", "Avoid verbose output", 0.85),
        create_mock_proposal("003", "Split large files", 0.92),
        create_mock_proposal("004", "Use early returns", 0.88),
        create_mock_proposal("005", "Never exceed 200 lines", 0.91),
    ]


# Test batch mode auto-approval

def test_batch_mode_auto_approves_high_confidence(sample_proposals):
    """Batch mode should auto-approve proposals >= 0.9 confidence."""
    cli = ApprovalCLI(auto_approve_threshold=0.9)
    result = cli.run(sample_proposals, interactive=False)

    # High confidence: 0.95, 0.92, 0.91 (3 proposals)
    assert result.approved_count == 3
    assert result.rejected_count == 2
    assert result.auto_approved_count == 3
    assert "prop-001" in result.approved_ids  # 0.95
    assert "prop-003" in result.approved_ids  # 0.92
    assert "prop-005" in result.approved_ids  # 0.91
    assert "prop-002" in result.rejected_ids  # 0.85
    assert "prop-004" in result.rejected_ids  # 0.88


def test_batch_mode_respects_custom_threshold(sample_proposals):
    """Batch mode should respect custom threshold."""
    cli = ApprovalCLI(auto_approve_threshold=0.93)
    result = cli.run(sample_proposals, interactive=False)

    # Only 0.95 meets >= 0.93 threshold
    assert result.approved_count == 1
    assert result.rejected_count == 4
    assert "prop-001" in result.approved_ids  # 0.95


def test_batch_mode_with_empty_proposals():
    """Batch mode with no proposals should return empty result."""
    cli = ApprovalCLI()
    result = cli.run([], interactive=False)

    assert result.total == 0
    assert result.approved_count == 0
    assert result.rejected_count == 0
    assert result.approved_ids == []
    assert result.rejected_ids == []


# Test interactive mode

@patch('builtins.input', return_value='all')
@patch('builtins.print')
def test_interactive_mode_approve_all(mock_print, mock_input, sample_proposals):
    """Interactive mode: 'all' should approve all proposals."""
    cli = ApprovalCLI()
    result = cli.run(sample_proposals, interactive=True)

    assert result.approved_count == 5
    assert result.rejected_count == 0
    assert len(result.approved_ids) == 5
    assert len(result.rejected_ids) == 0


@patch('builtins.input', return_value='none')
@patch('builtins.print')
def test_interactive_mode_approve_none(mock_print, mock_input, sample_proposals):
    """Interactive mode: 'none' should reject all proposals."""
    cli = ApprovalCLI()
    result = cli.run(sample_proposals, interactive=True)

    assert result.approved_count == 0
    assert result.rejected_count == 5
    assert len(result.approved_ids) == 0
    assert len(result.rejected_ids) == 5


@patch('builtins.input', return_value='1,3,5')
@patch('builtins.print')
def test_interactive_mode_specific_comma(mock_print, mock_input, sample_proposals):
    """Interactive mode: '1,3,5' should approve specific proposals."""
    cli = ApprovalCLI()
    result = cli.run(sample_proposals, interactive=True)

    assert result.approved_count == 3
    assert result.rejected_count == 2
    assert "prop-001" in result.approved_ids  # Index 1
    assert "prop-003" in result.approved_ids  # Index 3
    assert "prop-005" in result.approved_ids  # Index 5
    assert "prop-002" in result.rejected_ids  # Index 2
    assert "prop-004" in result.rejected_ids  # Index 4


@patch('builtins.input', return_value='2 4')
@patch('builtins.print')
def test_interactive_mode_specific_space(mock_print, mock_input, sample_proposals):
    """Interactive mode: '2 4' should approve specific proposals."""
    cli = ApprovalCLI()
    result = cli.run(sample_proposals, interactive=True)

    assert result.approved_count == 2
    assert result.rejected_count == 3
    assert "prop-002" in result.approved_ids  # Index 2
    assert "prop-004" in result.approved_ids  # Index 4


@patch('builtins.input', return_value='q')
@patch('builtins.print')
def test_interactive_mode_quit(mock_print, mock_input, sample_proposals):
    """Interactive mode: 'q' should quit and reject all."""
    cli = ApprovalCLI()
    result = cli.run(sample_proposals, interactive=True)

    assert result.approved_count == 0
    assert result.rejected_count == 5


@patch('builtins.input', side_effect=['invalid', 'all'])
@patch('builtins.print')
def test_interactive_mode_invalid_then_valid(mock_print, mock_input, sample_proposals):
    """Interactive mode: invalid input should retry."""
    cli = ApprovalCLI()
    result = cli.run(sample_proposals, interactive=True)

    # Should eventually accept 'all'
    assert result.approved_count == 5


@patch('builtins.input', side_effect=['99', 'all'])
@patch('builtins.print')
def test_interactive_mode_out_of_range(mock_print, mock_input, sample_proposals):
    """Interactive mode: out-of-range number should retry."""
    cli = ApprovalCLI()
    result = cli.run(sample_proposals, interactive=True)

    # Should eventually accept 'all'
    assert result.approved_count == 5


@patch('builtins.input', side_effect=KeyboardInterrupt())
@patch('builtins.print')
def test_interactive_mode_keyboard_interrupt(mock_print, mock_input, sample_proposals):
    """Interactive mode: KeyboardInterrupt should quit gracefully."""
    cli = ApprovalCLI()
    result = cli.run(sample_proposals, interactive=True)

    assert result.approved_count == 0
    assert result.rejected_count == 5


# Test timing requirement

@patch('builtins.input', return_value='all')
@patch('builtins.print')
def test_approval_time_under_30_seconds(mock_print, mock_input, sample_proposals):
    """Approval should complete in under 30 seconds (fast approval)."""
    cli = ApprovalCLI()
    start = datetime.now()
    result = cli.run(sample_proposals, interactive=True)
    duration = (datetime.now() - start).total_seconds()

    # Interactive mode with mocked input should be instant
    assert duration < 30
    assert result.duration_seconds < 30


def test_batch_mode_timing(sample_proposals):
    """Batch mode should be fast (< 1 second)."""
    cli = ApprovalCLI()
    start = datetime.now()
    result = cli.run(sample_proposals, interactive=False)
    duration = (datetime.now() - start).total_seconds()

    # Batch mode should be nearly instant
    assert duration < 1
    assert result.duration_seconds < 1


# Test convenience function

@patch('builtins.input', return_value='all')
@patch('builtins.print')
def test_convenience_function_interactive(mock_print, mock_input, sample_proposals):
    """approve_proposals convenience function should work."""
    result = approve_proposals(
        user_proposals=sample_proposals,
        interactive=True
    )

    assert result.approved_count == 5


def test_convenience_function_batch(sample_proposals):
    """approve_proposals convenience function should work in batch mode."""
    result = approve_proposals(
        user_proposals=sample_proposals,
        interactive=False,
        auto_approve_threshold=0.9
    )

    assert result.approved_count == 3  # 0.95, 0.92, 0.91


# Test with agent proposals

@patch('builtins.input', return_value='all')
@patch('builtins.print')
def test_combined_user_and_agent_proposals(mock_print, mock_input, sample_proposals):
    """Should handle both user and agent proposals."""
    # Create mock agent proposals (same structure)
    agent_proposals = [
        create_mock_proposal("agent-001", "Agent rule 1", 0.88),
        create_mock_proposal("agent-002", "Agent rule 2", 0.92),
    ]

    cli = ApprovalCLI()
    result = cli.run(sample_proposals, agent_proposals, interactive=True)

    # 5 user + 2 agent = 7 total
    assert result.total == 7
    assert result.approved_count == 7


# Test display formatting

@patch('builtins.input', return_value='all')
@patch('builtins.print')
def test_display_shows_all_fields(mock_print, mock_input):
    """Display should show all proposal fields."""
    proposals = [
        MemoryProposal(
            id="prop-test",
            category="rule",
            scope="language:python",
            content="Test rule content",
            rationale="Test rationale",
            source_variants=["variant 1", "variant 2"],
            confidence=0.92,
            priority=1
        )
    ]

    cli = ApprovalCLI()
    cli.run(proposals, interactive=True)

    # Check that print was called with proposal details
    call_args = [str(call) for call in mock_print.call_args_list]
    combined_output = ' '.join(call_args)

    assert 'Test rule content' in combined_output
    assert 'language:python' in combined_output
    assert 'rule' in combined_output
    assert '92%' in combined_output or '0.92' in combined_output


# Test no special dependencies

def test_no_special_dependencies():
    """approval_cli should only use standard library."""
    import sys
    import cerberus.memory.approval_cli as approval_module

    # Get module imports
    module_file = approval_module.__file__
    with open(module_file, 'r') as f:
        content = f.read()

    # Should not import any non-standard libraries
    forbidden_imports = [
        'keyboard',
        'curses',
        'blessed',
        'prompt_toolkit',
        'click',
        'typer'
    ]

    for lib in forbidden_imports:
        assert f'import {lib}' not in content, f"Found forbidden import: {lib}"
        assert f'from {lib}' not in content, f"Found forbidden import: from {lib}"


# Test edge cases

def test_empty_proposals_interactive():
    """Interactive mode with no proposals should return empty result."""
    cli = ApprovalCLI()
    result = cli.run([], interactive=True)

    assert result.total == 0
    assert result.approved_count == 0


@patch('builtins.input', return_value='1')
@patch('builtins.print')
def test_single_proposal(mock_print, mock_input):
    """Should handle single proposal correctly."""
    proposals = [
        create_mock_proposal("001", "Single rule", 0.9)
    ]

    cli = ApprovalCLI()
    result = cli.run(proposals, interactive=True)

    assert result.approved_count == 1
    assert result.total == 1


@patch('builtins.input', return_value='1,1,1')
@patch('builtins.print')
def test_duplicate_numbers(mock_print, mock_input):
    """Duplicate numbers should be deduplicated."""
    proposals = [
        create_mock_proposal("001", "Rule 1", 0.9),
        create_mock_proposal("002", "Rule 2", 0.85),
    ]

    cli = ApprovalCLI()
    result = cli.run(proposals, interactive=True)

    # Should only count proposal 1 once
    assert result.approved_count == 1
    assert "prop-001" in result.approved_ids


# Integration test

@patch('builtins.input', return_value='1,3,5')
@patch('builtins.print')
def test_full_integration(mock_print, mock_input, sample_proposals):
    """Full integration test mimicking real usage."""
    # Simulate Phase 3 output feeding into Phase 4
    cli = ApprovalCLI(auto_approve_threshold=0.9)

    # Interactive mode
    result = cli.run(sample_proposals, interactive=True)

    assert result.total == 5
    assert result.approved_count == 3
    assert result.rejected_count == 2
    assert result.duration_seconds > 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
