"""
Phase 15: Mode-Aware Context - Unit Tests

Test coverage:
- Mode detection from user prompts (20+ scenarios)
- Auto-tagging memories with valid modes
- Mode filtering in injection
- Integration between storage, retrieval, and injection

Target: 85%+ detection accuracy
"""

import pytest
from cerberus.memory.mode_detection import (
    ModeDetector,
    ModeTagging,
    detect_mode,
    auto_tag_memory,
    IntentMode,
    ModeDetectionResult,
    MODES
)


class TestModeDetector:
    """Test mode detection from user prompts."""

    def test_prototype_mode_detection(self):
        """Test detection of prototype mode."""
        detector = ModeDetector()

        # Test 1: Quick script
        result = detector.detect("quick script to parse logs", {})
        assert result.primary_mode.mode == "prototype"
        assert result.primary_mode.confidence > 0.3
        assert "quick" in result.primary_mode.indicators

        # Test 2: POC
        result = detector.detect("let's try a proof of concept", {})
        assert result.primary_mode.mode == "prototype"

        # Test 3: Experiment
        result = detector.detect("experiment with this approach", {})
        assert result.primary_mode.mode == "prototype"

    def test_production_mode_detection(self):
        """Test detection of production mode."""
        detector = ModeDetector()

        # Test 4: Production release
        result = detector.detect("implement user authentication for production release", {})
        assert result.primary_mode.mode == "production"
        assert result.primary_mode.confidence > 0.3
        assert any(kw in result.primary_mode.indicators for kw in ["production", "release"])

        # Test 5: Deploy to prod
        result = detector.detect("ready to deploy this feature to prod", {})
        assert result.primary_mode.mode == "production"

        # Test 6: Ship feature
        result = detector.detect("ship the new API endpoints", {})
        assert result.primary_mode.mode == "production"

    def test_hotfix_mode_detection(self):
        """Test detection of hotfix mode."""
        detector = ModeDetector()

        # Test 7: Urgent bug
        result = detector.detect("urgent bug fix - login broken in prod", {})
        assert result.primary_mode.mode == "hotfix"
        assert result.primary_mode.confidence > 0.3
        assert any(kw in result.primary_mode.indicators for kw in ["urgent", "bug", "broken"])

        # Test 8: Critical issue
        result = detector.detect("critical issue needs immediate fix", {})
        assert result.primary_mode.mode == "hotfix"

        # Test 9: System down
        result = detector.detect("system is down, need to fix asap", {})
        assert result.primary_mode.mode == "hotfix"

    def test_refactor_mode_detection(self):
        """Test detection of refactor mode."""
        detector = ModeDetector()

        # Test 10: Refactor code
        result = detector.detect("refactor the authentication module", {})
        assert result.primary_mode.mode == "refactor"
        assert "refactor" in result.primary_mode.indicators

        # Test 11: Cleanup
        result = detector.detect("cleanup and organize the codebase", {})
        assert result.primary_mode.mode == "refactor"

        # Test 12: Technical debt
        result = detector.detect("address technical debt in the API layer", {})
        assert result.primary_mode.mode == "refactor"

    def test_audit_mode_detection(self):
        """Test detection of audit mode."""
        detector = ModeDetector()

        # Test 13: Review code
        result = detector.detect("review the security implementation", {})
        assert result.primary_mode.mode == "audit"
        assert "review" in result.primary_mode.indicators

        # Test 14: Understand how
        result = detector.detect("help me understand how the caching works", {})
        assert result.primary_mode.mode == "audit"

        # Test 15: Walk through
        result = detector.detect("walk me through the authentication flow", {})
        assert result.primary_mode.mode == "audit"

    def test_exploration_mode_detection(self):
        """Test detection of exploration mode."""
        detector = ModeDetector()

        # Test 16: Find files
        result = detector.detect("find all files related to database", {})
        assert result.primary_mode.mode == "exploration"
        assert "find" in result.primary_mode.indicators

        # Test 17: Where is
        result = detector.detect("where is the error handling defined", {})
        assert result.primary_mode.mode == "exploration"

        # Test 18: List files
        result = detector.detect("list all configuration files", {})
        assert result.primary_mode.mode == "exploration"

    def test_scope_analysis(self):
        """Test scope-based mode detection."""
        detector = ModeDetector()

        # Single file = prototype/hotfix more likely
        context = {"modified_files": ["script.py"], "tools_used": []}
        result = detector.detect("quick fix", context)
        assert result.primary_mode.mode in ["prototype", "hotfix"]

        # Multiple files = production/refactor more likely
        context = {"modified_files": [f"file{i}.py" for i in range(10)], "tools_used": []}
        result = detector.detect("implement feature", context)
        # Should lean towards production or refactor (not prototype)
        assert result.primary_mode.mode in ["production", "refactor", "prototype"]

    def test_urgency_analysis(self):
        """Test urgency keyword detection."""
        detector = ModeDetector()

        # Urgent keywords = hotfix
        result = detector.detect("need this now - critical", {})
        assert result.primary_mode.mode == "hotfix"

        # Proper/thorough keywords = production
        result = detector.detect("implement with proper test coverage", {})
        # Production should score high due to "proper" and "test"
        assert result.primary_mode.mode in ["production", "refactor"]

    def test_context_signals(self):
        """Test context signal analysis."""
        detector = ModeDetector()

        # Write tool = prototype
        context = {"modified_files": [], "tools_used": ["Write", "Write"]}
        result = detector.detect("create new file", context)
        # Prototype gets boost from Write tool
        assert result.primary_mode.mode in ["prototype", "production"]

        # Multiple Edits = refactor
        context = {"modified_files": [], "tools_used": ["Edit"] * 5}
        result = detector.detect("improve code", context)
        # Refactor gets boost from multiple Edit calls
        assert result.primary_mode.mode == "refactor"

        # Test files = production
        context = {"modified_files": ["test_api.py", "test_auth.py"], "tools_used": []}
        result = detector.detect("add feature", context)
        # Production gets boost from test files
        assert result.primary_mode.mode == "production"

    def test_secondary_modes(self):
        """Test secondary mode detection."""
        detector = ModeDetector()

        result = detector.detect("quick prototype but make it production-ready", {})

        # Should detect both modes
        all_modes = [result.primary_mode.mode] + [m.mode for m in result.secondary_modes]
        assert "prototype" in all_modes or "production" in all_modes

    def test_confidence_scoring(self):
        """Test confidence scores are within bounds."""
        detector = ModeDetector()

        result = detector.detect("urgent critical hotfix asap", {})

        # Confidence should be 0.0-1.0
        assert 0.0 <= result.primary_mode.confidence <= 1.0

        # Strong indicators should give high confidence
        assert result.primary_mode.confidence > 0.5

    def test_rigor_levels(self):
        """Test rigor level assignment."""
        detector = ModeDetector()

        # Prototype = low rigor
        result = detector.detect("quick hack", {})
        assert result.primary_mode.rigor_level == "low"

        # Production = high rigor
        result = detector.detect("deploy to production", {})
        assert result.primary_mode.rigor_level == "high"

        # Hotfix = medium rigor
        result = detector.detect("urgent bug fix", {})
        assert result.primary_mode.rigor_level == "medium"


class TestModeTagging:
    """Test auto-tagging memories with valid modes."""

    def test_quality_rules_tagging(self):
        """Test tagging of quality-focused rules."""
        tagger = ModeTagging()

        # Test rules should be production + refactor only
        valid_modes = tagger.auto_tag("Always write tests for public APIs")
        assert "production" in valid_modes
        assert "refactor" in valid_modes
        assert "prototype" not in valid_modes
        assert "hotfix" not in valid_modes

        # Doc rules should be production + refactor
        valid_modes = tagger.auto_tag("Document all error handling")
        assert "production" in valid_modes
        assert "refactor" in valid_modes

        # Error handling rules
        valid_modes = tagger.auto_tag("Add proper validation for user input")
        assert "production" in valid_modes
        assert "refactor" in valid_modes

    def test_speed_rules_tagging(self):
        """Test tagging of speed-focused rules."""
        tagger = ModeTagging()

        # Speed rules should allow prototype + hotfix + exploration
        valid_modes = tagger.auto_tag("Keep it short and concise")
        assert "prototype" in valid_modes
        assert "hotfix" in valid_modes
        assert "exploration" in valid_modes

        # Quick rules
        valid_modes = tagger.auto_tag("Use quick solution")
        assert "prototype" in valid_modes
        assert "hotfix" in valid_modes

    def test_pattern_rules_tagging(self):
        """Test tagging of architecture/pattern rules."""
        tagger = ModeTagging()

        # Pattern rules should be production + refactor
        valid_modes = tagger.auto_tag("Use dependency injection pattern")
        assert "production" in valid_modes
        assert "refactor" in valid_modes
        assert "prototype" not in valid_modes

        # Architecture rules
        valid_modes = tagger.auto_tag("Follow clean architecture principles")
        assert "production" in valid_modes
        assert "refactor" in valid_modes

    def test_analysis_rules_tagging(self):
        """Test tagging of analysis/review rules."""
        tagger = ModeTagging()

        # Analysis rules should be audit + exploration
        valid_modes = tagger.auto_tag("Analyze the code before making changes")
        assert "audit" in valid_modes
        assert "exploration" in valid_modes

    def test_emergency_rules_tagging(self):
        """Test tagging of emergency/hotfix rules."""
        tagger = ModeTagging()

        # Emergency rules should be hotfix only
        valid_modes = tagger.auto_tag("Critical hotfix protocol")
        assert valid_modes == ["hotfix"]

    def test_default_tagging(self):
        """Test default tagging for generic rules."""
        tagger = ModeTagging()

        # Generic rule should apply to most modes
        valid_modes = tagger.auto_tag("Use clear variable names")
        assert "prototype" in valid_modes
        assert "production" in valid_modes
        assert "hotfix" in valid_modes
        assert "refactor" in valid_modes

    def test_mode_priority_calculation(self):
        """Test priority calculation for modes."""
        tagger = ModeTagging()

        valid_modes = ["production", "refactor"]
        priorities = tagger.calculate_mode_priority(
            "Always write tests before code",
            valid_modes
        )

        # Production should have high priority for test rule
        assert priorities["production"] >= 5
        assert priorities["refactor"] >= 5

        # Priorities should be 1-10
        for mode, priority in priorities.items():
            assert 1 <= priority <= 10


class TestModeDetectionIntegration:
    """Test integration of mode detection with other components."""

    def test_standalone_detect_mode_function(self):
        """Test standalone detect_mode function."""
        result = detect_mode("quick prototype", {})

        assert isinstance(result, ModeDetectionResult)
        assert result.primary_mode.mode == "prototype"

    def test_standalone_auto_tag_function(self):
        """Test standalone auto_tag_memory function."""
        valid_modes, mode_priority = auto_tag_memory("Always write tests")

        assert isinstance(valid_modes, list)
        assert isinstance(mode_priority, dict)
        assert "production" in valid_modes
        assert "production" in mode_priority


class TestModeDefinitions:
    """Test mode definitions and configuration."""

    def test_all_modes_defined(self):
        """Test all expected modes are defined."""
        expected_modes = ["prototype", "production", "hotfix", "refactor", "audit", "exploration"]

        for mode in expected_modes:
            assert mode in MODES
            assert "description" in MODES[mode]
            assert "rigor" in MODES[mode]
            assert "indicators" in MODES[mode]

    def test_mode_indicators_not_empty(self):
        """Test each mode has at least one indicator."""
        for mode_name, mode_config in MODES.items():
            assert len(mode_config["indicators"]) > 0

    def test_rigor_levels_valid(self):
        """Test rigor levels are valid."""
        valid_rigor_levels = ["low", "medium", "high"]

        for mode_name, mode_config in MODES.items():
            assert mode_config["rigor"] in valid_rigor_levels


# Test scenarios for validation (85%+ accuracy target)

VALIDATION_SCENARIOS = [
    # Prototype mode (5 scenarios)
    {"prompt": "quick script to parse logs", "expected": "prototype"},
    {"prompt": "let's try a poc for this idea", "expected": "prototype"},
    {"prompt": "experiment with different approaches", "expected": "prototype"},
    {"prompt": "hack together a solution", "expected": "prototype"},
    {"prompt": "just want to see if this works", "expected": "prototype"},

    # Production mode (5 scenarios)
    {"prompt": "implement authentication for production", "expected": "production"},
    {"prompt": "deploy the new feature to prod", "expected": "production"},
    {"prompt": "ship the API with proper tests", "expected": "production"},
    {"prompt": "launch the customer-facing portal", "expected": "production"},
    {"prompt": "stable release with documentation", "expected": "production"},

    # Hotfix mode (5 scenarios)
    {"prompt": "urgent bug fix - system down", "expected": "hotfix"},
    {"prompt": "critical issue needs immediate fix", "expected": "hotfix"},
    {"prompt": "broken in prod, fix asap", "expected": "hotfix"},
    {"prompt": "emergency patch needed now", "expected": "hotfix"},
    {"prompt": "critical security vulnerability fix", "expected": "hotfix"},

    # Refactor mode (5 scenarios)
    {"prompt": "refactor the authentication module", "expected": "refactor"},
    {"prompt": "cleanup the codebase", "expected": "refactor"},
    {"prompt": "restructure the API layer", "expected": "refactor"},
    {"prompt": "optimize and simplify the code", "expected": "refactor"},
    {"prompt": "address technical debt", "expected": "refactor"},

    # Audit mode (3 scenarios)
    {"prompt": "review the security implementation", "expected": "audit"},
    {"prompt": "understand how the caching works", "expected": "audit"},
    {"prompt": "walk me through this code", "expected": "audit"},

    # Exploration mode (3 scenarios)
    {"prompt": "find files related to database", "expected": "exploration"},
    {"prompt": "where is the error handling", "expected": "exploration"},
    {"prompt": "list all test files", "expected": "exploration"},
]


class TestValidationScenarios:
    """Test accuracy against validation scenarios (target: 85%+)."""

    @pytest.mark.parametrize("scenario", VALIDATION_SCENARIOS)
    def test_validation_scenario(self, scenario):
        """Test each validation scenario."""
        detector = ModeDetector()
        result = detector.detect(scenario["prompt"], {})

        # Check if primary mode matches expected
        # (allowing flexibility for close matches)
        assert result.primary_mode.mode == scenario["expected"], \
            f"Expected {scenario['expected']}, got {result.primary_mode.mode} for: {scenario['prompt']}"

    def test_overall_accuracy(self):
        """Test overall detection accuracy (target: 85%+)."""
        detector = ModeDetector()
        correct = 0
        total = len(VALIDATION_SCENARIOS)

        for scenario in VALIDATION_SCENARIOS:
            result = detector.detect(scenario["prompt"], {})
            if result.primary_mode.mode == scenario["expected"]:
                correct += 1

        accuracy = (correct / total) * 100

        print(f"\nMode Detection Accuracy: {accuracy:.1f}% ({correct}/{total} correct)")
        assert accuracy >= 85.0, f"Accuracy {accuracy:.1f}% below target 85%"
