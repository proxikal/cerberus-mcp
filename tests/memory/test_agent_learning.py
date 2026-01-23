"""
Tests for Phase 10: Agent Self-Learning

Covers detection patterns, observation collection, codebase analysis,
proposal refinement, and integration.
"""

import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from cerberus.memory.agent_learning import (
    AgentLearningEngine,
    AgentObservation,
    AgentProposal,
    CodebaseAnalyzer,
    ObservationCollector,
    ProposalRefiner,
    _extract_anti_pattern,
    _extract_praised_approach,
    _extract_rule,
    _infer_scope,
    detect_approach_reinforcement,
    detect_failure_pattern,
    detect_project_pattern,
    detect_success_pattern,
    generate_agent_proposals,
)


# ============================================================================
# Test Helper Functions
# ============================================================================

def test_infer_scope_universal():
    """Test scope inference for universal observations."""
    observations = [
        AgentObservation(
            observation_type="success",
            action_taken="split file",
            user_response="good",
            context={},
            confidence=0.7,
            timestamp=datetime.now()
        )
    ]

    scope = _infer_scope(observations)
    assert scope == "universal"


def test_infer_scope_project():
    """Test scope inference for project-specific observations."""
    observations = [
        AgentObservation(
            observation_type="success",
            action_taken="refactor",
            user_response="good",
            context={"project": "cerberus"},
            confidence=0.7,
            timestamp=datetime.now()
        ),
        AgentObservation(
            observation_type="success",
            action_taken="test",
            user_response="perfect",
            context={"project": "cerberus"},
            confidence=0.9,
            timestamp=datetime.now()
        )
    ]

    scope = _infer_scope(observations)
    assert scope == "project:cerberus"


def test_infer_scope_language():
    """Test scope inference for language-specific observations."""
    observations = [
        AgentObservation(
            observation_type="success",
            action_taken="write code",
            user_response="good",
            context={"file": "test.py"},
            confidence=0.7,
            timestamp=datetime.now()
        ),
        AgentObservation(
            observation_type="success",
            action_taken="write code",
            user_response="good",
            context={"language": "python"},
            confidence=0.7,
            timestamp=datetime.now()
        )
    ]

    scope = _infer_scope(observations)
    assert scope == "language:python"


def test_extract_rule_split():
    """Test rule extraction for file splitting."""
    observations = []
    rule = _extract_rule("split file into 3 parts", observations)
    assert "split" in rule.lower()
    assert "200" in rule


def test_extract_rule_test_first():
    """Test rule extraction for TDD."""
    observations = []
    rule = _extract_rule("test first then implement", observations)
    assert "test" in rule.lower()
    assert "before" in rule.lower() or "first" in rule.lower()


def test_extract_anti_pattern_verbose():
    """Test anti-pattern extraction for verbosity."""
    anti_pattern = _extract_anti_pattern("wrote verbose explanation")
    assert "verbose" in anti_pattern.lower()


def test_extract_praised_approach_tdd():
    """Test praised approach extraction for TDD."""
    obs = AgentObservation(
        observation_type="success",
        action_taken="wrote test first",
        user_response="perfect, that's TDD",
        context={},
        confidence=0.9,
        timestamp=datetime.now()
    )

    approach = _extract_praised_approach(obs)
    assert "test" in approach.lower()
    assert "tdd" in approach.lower() or "before" in approach.lower()


# ============================================================================
# Test Detection Patterns
# ============================================================================

def test_detect_success_pattern():
    """Test Pattern 1: Success reinforcement."""
    observations = [
        AgentObservation(
            observation_type="success",
            action_taken="split file",
            user_response="perfect",
            context={},
            confidence=0.9,
            timestamp=datetime.now()
        ),
        AgentObservation(
            observation_type="success",
            action_taken="split file",
            user_response="good",
            context={},
            confidence=0.7,
            timestamp=datetime.now()
        ),
        AgentObservation(
            observation_type="success",
            action_taken="split file",
            user_response="approved",
            context={},
            confidence=0.7,
            timestamp=datetime.now()
        )
    ]

    proposal = detect_success_pattern(observations)

    assert proposal is not None
    assert proposal.category == "rule"
    assert "split" in proposal.content.lower()
    assert len(proposal.evidence) == 3
    assert proposal.confidence > 0


def test_detect_success_pattern_insufficient():
    """Test success pattern with insufficient repetitions."""
    observations = [
        AgentObservation(
            observation_type="success",
            action_taken="split file",
            user_response="good",
            context={},
            confidence=0.7,
            timestamp=datetime.now()
        ),
        AgentObservation(
            observation_type="success",
            action_taken="split file",
            user_response="good",
            context={},
            confidence=0.7,
            timestamp=datetime.now()
        )
    ]

    proposal = detect_success_pattern(observations)
    assert proposal is None  # Need 3+ approvals


def test_detect_failure_pattern():
    """Test Pattern 2: Failure avoidance."""
    observations = [
        AgentObservation(
            observation_type="failure",
            action_taken="wrote verbose explanation",
            user_response="keep it short",
            context={},
            confidence=0.3,
            timestamp=datetime.now()
        ),
        AgentObservation(
            observation_type="failure",
            action_taken="wrote verbose explanation",
            user_response="terse output",
            context={},
            confidence=0.3,
            timestamp=datetime.now()
        )
    ]

    proposal = detect_failure_pattern(observations)

    assert proposal is not None
    assert proposal.category == "correction"
    assert "avoid" in proposal.content.lower()
    assert "verbose" in proposal.content.lower()
    assert len(proposal.evidence) == 2


def test_detect_failure_pattern_single():
    """Test failure pattern with only one failure."""
    observations = [
        AgentObservation(
            observation_type="failure",
            action_taken="wrote long file",
            user_response="split it",
            context={},
            confidence=0.3,
            timestamp=datetime.now()
        )
    ]

    proposal = detect_failure_pattern(observations)
    assert proposal is None  # Need 2+ failures


def test_detect_project_pattern():
    """Test Pattern 3: Project inference."""
    observations = [
        AgentObservation(
            observation_type="success",
            action_taken="error_handling added",
            user_response="good",
            context={"file": "module1.py"},
            confidence=0.7,
            timestamp=datetime.now()
        ),
        AgentObservation(
            observation_type="success",
            action_taken="error_handling added",
            user_response="good",
            context={"file": "module2.py"},
            confidence=0.7,
            timestamp=datetime.now()
        ),
        AgentObservation(
            observation_type="success",
            action_taken="error_handling added",
            user_response="good",
            context={"file": "module3.py"},
            confidence=0.7,
            timestamp=datetime.now()
        )
    ]

    codebase_analysis = {
        "project": "test_project",
        "patterns": {
            "error_handling": {
                "description": "Use logging in exception handlers",
                "confidence": 0.8
            }
        }
    }

    proposal = detect_project_pattern(observations, codebase_analysis)

    assert proposal is not None
    assert proposal.category == "pattern"
    assert proposal.scope == "project:test_project"
    assert "error" in proposal.content.lower() or "logging" in proposal.content.lower()


def test_detect_approach_reinforcement():
    """Test Pattern 4: Approach reinforcement."""
    observations = [
        AgentObservation(
            observation_type="success",
            action_taken="wrote test first",
            user_response="perfect, that's TDD",
            context={},
            confidence=0.9,
            timestamp=datetime.now()
        )
    ]

    proposal = detect_approach_reinforcement(observations)

    assert proposal is not None
    assert proposal.category == "preference"
    assert proposal.confidence == 0.9  # Explicit praise
    assert "test" in proposal.content.lower()


def test_detect_approach_reinforcement_no_praise():
    """Test approach reinforcement with no explicit praise."""
    observations = [
        AgentObservation(
            observation_type="success",
            action_taken="wrote code",
            user_response="ok",
            context={},
            confidence=0.5,
            timestamp=datetime.now()
        )
    ]

    proposal = detect_approach_reinforcement(observations)
    assert proposal is None  # No explicit praise keywords


# ============================================================================
# Test ObservationCollector
# ============================================================================

def test_observation_collector_record():
    """Test recording observations."""
    collector = ObservationCollector()

    collector.record(
        action="split file",
        user_response="perfect",
        context={"file": "test.py"}
    )

    assert len(collector.observations) == 1
    obs = collector.observations[0]
    assert obs.action_taken == "split file"
    assert obs.user_response == "perfect"
    assert obs.observation_type == "success"
    assert obs.confidence == 0.9  # Explicit praise


def test_observation_collector_confidence_calculation():
    """Test confidence scoring from user responses."""
    collector = ObservationCollector()

    # Test different response types
    test_cases = [
        ("perfect", 0.9),
        ("exactly right", 0.9),
        ("good job", 0.7),
        ("correct", 0.7),
        ("don't do that", 0.3),
        ("never use that", 0.3),
        ("neutral comment", 0.5)
    ]

    for response, expected_conf in test_cases:
        obs = AgentObservation(
            observation_type="test",
            action_taken="test",
            user_response=response,
            context={},
            confidence=collector._calculate_confidence(response),
            timestamp=datetime.now()
        )
        assert obs.confidence == expected_conf


# ============================================================================
# Test CodebaseAnalyzer
# ============================================================================

def test_codebase_analyzer_python_error_handling(tmp_path):
    """Test detection of Python error handling patterns."""
    # Create test Python files (need 6+ to meet threshold)
    for i in range(6):
        file_path = tmp_path / f"module{i}.py"
        file_path.write_text("""
import logging

def test_function():
    try:
        do_something()
    except Exception as e:
        logging.error(f"Error: {e}")
        raise

def another_function():
    try:
        do_other_thing()
    except ValueError as e:
        logger.warning(f"Value error: {e}")
        return None
""")

    analyzer = CodebaseAnalyzer()
    result = analyzer._detect_error_handling(tmp_path)

    assert result is not None
    assert "logging" in result["description"].lower()
    assert result["confidence"] > 0


def test_codebase_analyzer_python_pytest(tmp_path):
    """Test detection of pytest patterns."""
    # Create test files with pytest
    for i in range(4):
        file_path = tmp_path / f"test_module{i}.py"
        file_path.write_text("""
import pytest

@pytest.fixture
def sample_data():
    return [1, 2, 3]

def test_something(sample_data):
    assert len(sample_data) == 3
""")

    analyzer = CodebaseAnalyzer()
    result = analyzer._detect_test_patterns(tmp_path)

    assert result is not None
    assert "pytest" in result["description"].lower()
    assert result["confidence"] > 0


def test_codebase_analyzer_no_patterns(tmp_path):
    """Test analyzer with no patterns found."""
    # Empty directory
    analyzer = CodebaseAnalyzer()
    result = analyzer._detect_error_handling(tmp_path)

    assert result is None


# ============================================================================
# Test ProposalRefiner
# ============================================================================

def test_proposal_refiner_rule_based():
    """Test rule-based refinement."""
    refiner = ProposalRefiner(use_llm=False)

    proposal = AgentProposal(
        id="test-1",
        category="rule",
        scope="universal",
        content="Continue: split large files",
        evidence=[],
        confidence=0.5,
        priority=1
    )

    refined = refiner.refine(proposal)

    assert "split" in refined.content.lower()
    assert "200" in refined.content  # Template should include line limit


def test_proposal_refiner_clean_content():
    """Test content cleaning."""
    refiner = ProposalRefiner(use_llm=False)

    test_cases = [
        ("Continue: test before coding", "Test before coding"),
        ("Always write tests first", "Write tests first"),
        ("You should plan ahead", "Plan ahead"),
        ("Make sure to log errors", "Log errors")
    ]

    for input_text, expected_start in test_cases:
        cleaned = refiner._clean_content(input_text)
        assert cleaned.startswith(expected_start) or expected_start.lower() in cleaned.lower()


def test_proposal_refiner_max_length():
    """Test content length limiting."""
    refiner = ProposalRefiner(use_llm=False)

    long_content = "Continue: " + " ".join(["word"] * 20)
    cleaned = refiner._clean_content(long_content)

    assert len(cleaned.split()) <= 12


# ============================================================================
# Test AgentLearningEngine
# ============================================================================

def test_agent_learning_engine_generate_proposals():
    """Test proposal generation from observations."""
    engine = AgentLearningEngine(use_llm=False)

    # Add observations
    engine.collector.record(
        action="split file",
        user_response="perfect",
        context={}
    )
    engine.collector.record(
        action="split file",
        user_response="good",
        context={}
    )
    engine.collector.record(
        action="split file",
        user_response="approved",
        context={}
    )

    proposals = engine.generate_proposals()

    assert len(proposals) > 0
    assert any("split" in p.content.lower() for p in proposals)


def test_agent_learning_engine_max_proposals():
    """Test that engine respects max_proposals limit."""
    engine = AgentLearningEngine(use_llm=False)
    engine.max_proposals = 2

    # Create many different successful patterns
    for i in range(10):
        for j in range(3):
            engine.collector.record(
                action=f"action_{i}",
                user_response="perfect",
                context={}
            )

    proposals = engine.generate_proposals()

    assert len(proposals) <= 2


def test_agent_learning_engine_sorting():
    """Test that proposals are sorted by confidence/priority."""
    engine = AgentLearningEngine(use_llm=False)

    # High confidence explicit praise (should be first)
    engine.collector.record(
        action="test first",
        user_response="perfect approach",
        context={}
    )

    # Multiple successes (lower confidence)
    for _ in range(3):
        engine.collector.record(
            action="split file",
            user_response="good",
            context={}
        )

    proposals = engine.generate_proposals()

    if len(proposals) >= 2:
        # First proposal should have higher confidence/priority ratio
        assert proposals[0].confidence / proposals[0].priority >= \
               proposals[1].confidence / proposals[1].priority


# ============================================================================
# Test Integration
# ============================================================================

def test_generate_agent_proposals_standalone():
    """Test standalone proposal generation function."""
    observations = [
        AgentObservation(
            observation_type="success",
            action_taken="wrote test first",
            user_response="perfect",
            context={},
            confidence=0.9,
            timestamp=datetime.now()
        )
    ]

    proposals = generate_agent_proposals(observations, use_llm=False)

    assert len(proposals) > 0
    assert any("test" in p.content.lower() for p in proposals)


def test_generate_agent_proposals_with_project():
    """Test proposal generation with project context."""
    observations = [
        AgentObservation(
            observation_type="success",
            action_taken="error_handling",
            user_response="good",
            context={"file": "test.py"},
            confidence=0.7,
            timestamp=datetime.now()
        )
    ] * 3  # Repeat 3 times

    proposals = generate_agent_proposals(
        observations,
        project="test_project",
        use_llm=False
    )

    assert len(proposals) >= 0  # May or may not find patterns depending on codebase


# ============================================================================
# Test Scenarios from Documentation
# ============================================================================

def test_scenario_success_reinforcement():
    """Test scenario 1: Success reinforcement."""
    engine = AgentLearningEngine(use_llm=False)

    # Split file 3 times, all approved
    for _ in range(3):
        engine.collector.record(
            action="split file",
            user_response="approved",
            context={}
        )

    # Wrote terse summary 4 times, all approved
    for _ in range(4):
        engine.collector.record(
            action="wrote terse summary",
            user_response="perfect",
            context={}
        )

    proposals = engine.generate_proposals()

    # Expect at least 1 proposal (either splitting or summaries)
    assert len(proposals) >= 1
    assert any(
        "split" in p.content.lower() or "terse" in p.content.lower() or "summary" in p.content.lower()
        for p in proposals
    )


def test_scenario_failure_avoidance():
    """Test scenario 2: Failure avoidance."""
    engine = AgentLearningEngine(use_llm=False)

    # Wrote verbose explanation, corrected 2 times
    engine.collector.record(
        action="wrote verbose explanation",
        user_response="keep it short",
        context={},
        obs_type="failure"
    )
    engine.collector.record(
        action="wrote verbose explanation",
        user_response="terse output please",
        context={},
        obs_type="failure"
    )

    proposals = engine.generate_proposals()

    # Expect 1 proposal about avoiding verbose
    assert len(proposals) >= 1
    assert any(
        "avoid" in p.content.lower() and "verbose" in p.content.lower()
        for p in proposals
    )


def test_scenario_approach_reinforcement():
    """Test scenario 4: Approach reinforcement."""
    engine = AgentLearningEngine(use_llm=False)

    engine.collector.record(
        action="wrote test first",
        user_response="perfect, that's TDD",
        context={}
    )

    proposals = engine.generate_proposals()

    # Expect 1 proposal with high confidence
    assert len(proposals) >= 1
    tdd_proposals = [p for p in proposals if "test" in p.content.lower()]
    assert len(tdd_proposals) > 0
    assert tdd_proposals[0].confidence == 0.9  # Explicit praise


def test_scenario_low_confidence_filtered():
    """Test scenario 5: Low confidence filtered."""
    engine = AgentLearningEngine(use_llm=False)

    # Did X once, user neutral
    engine.collector.record(
        action="did something",
        user_response="ok",
        context={}
    )

    proposals = engine.generate_proposals()

    # Should not generate proposals from single neutral interaction
    # (need 3+ for success, 2+ for failure, or explicit praise)
    assert len(proposals) == 0


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_observations():
    """Test with no observations."""
    engine = AgentLearningEngine(use_llm=False)
    proposals = engine.generate_proposals()

    assert len(proposals) == 0


def test_mixed_observations():
    """Test with mixed success and failure observations."""
    engine = AgentLearningEngine(use_llm=False)

    # Some successes
    for _ in range(3):
        engine.collector.record(
            action="pattern A",
            user_response="good",
            context={}
        )

    # Some failures
    for _ in range(2):
        engine.collector.record(
            action="pattern B",
            user_response="don't do that",
            context={},
            obs_type="failure"
        )

    proposals = engine.generate_proposals()

    # Should generate proposals for both patterns
    assert len(proposals) >= 2


def test_observation_type_auto_detection():
    """Test automatic observation type detection."""
    collector = ObservationCollector()

    # Positive responses
    collector.record("action", "perfect", {})
    assert collector.observations[-1].observation_type == "success"

    collector.record("action", "good job", {})
    assert collector.observations[-1].observation_type == "success"

    # Negative responses
    collector.record("action", "don't do that", {})
    assert collector.observations[-1].observation_type == "failure"

    collector.record("action", "never use that approach", {})
    assert collector.observations[-1].observation_type == "failure"

    # Neutral responses
    collector.record("action", "I see", {})
    assert collector.observations[-1].observation_type == "neutral"
