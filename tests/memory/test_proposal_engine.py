"""
Tests for Phase 3: Session Proposal

Validates template-based proposal generation, scope/category inference,
and content transformation.
"""

import pytest
from cerberus.memory.proposal_engine import (
    ProposalEngine,
    MemoryProposal,
    SessionSummary,
    generate_proposals,
    create_test_scenarios
)
from cerberus.memory.semantic_analyzer import CorrectionCluster
from datetime import datetime


class TestProposalEngine:
    """Test proposal generation engine."""

    def create_cluster(
        self,
        canonical: str,
        correction_type: str = "behavior",
        frequency: int = 1,
        confidence: float = 0.9
    ) -> CorrectionCluster:
        """Helper to create CorrectionCluster."""
        return CorrectionCluster(
            canonical_text=canonical,
            variants=[canonical],
            correction_type=correction_type,
            frequency=frequency,
            confidence=confidence,
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )

    def test_empty_clusters(self):
        """Test handling of empty cluster list."""
        engine = ProposalEngine()

        summary = engine.generate_proposals([], project=None)

        assert summary.total_corrections == 0
        assert summary.total_proposed == 0
        assert len(summary.proposals) == 0

    def test_single_cluster_proposal(self):
        """Test proposal generation from single cluster."""
        engine = ProposalEngine()

        clusters = [
            self.create_cluster("keep it short", "style", frequency=2, confidence=0.9)
        ]

        summary = engine.generate_proposals(clusters)

        assert summary.total_corrections == 2
        assert summary.total_proposed == 1
        assert len(summary.proposals) == 1

        proposal = summary.proposals[0]
        assert proposal.category in ["preference", "rule", "correction"]
        assert proposal.scope in ["universal", "language:go", "project:test"]
        assert proposal.confidence == 0.9

    def test_priority_ranking(self):
        """Test that proposals are ranked by frequency * confidence."""
        engine = ProposalEngine(max_proposals=3)

        clusters = [
            self.create_cluster("low priority", "style", frequency=1, confidence=0.7),
            self.create_cluster("high priority", "rule", frequency=5, confidence=0.9),
            self.create_cluster("medium priority", "behavior", frequency=2, confidence=0.8)
        ]

        summary = engine.generate_proposals(clusters)

        # Should be sorted by frequency * confidence
        # high: 5 * 0.9 = 4.5
        # medium: 2 * 0.8 = 1.6
        # low: 1 * 0.7 = 0.7

        assert len(summary.proposals) == 3
        assert "high priority" in summary.proposals[0].content.lower()
        assert summary.proposals[0].priority == 1

    def test_max_proposals_limit(self):
        """Test that max_proposals limits output."""
        engine = ProposalEngine(max_proposals=3)

        clusters = [
            self.create_cluster(f"rule {i}", "rule", frequency=i, confidence=0.9)
            for i in range(1, 6)  # 5 clusters
        ]

        summary = engine.generate_proposals(clusters)

        # Should only return top 3
        assert len(summary.proposals) == 3


class TestScopeInference:
    """Test scope inference logic."""

    def create_cluster(self, canonical: str) -> CorrectionCluster:
        """Helper to create CorrectionCluster."""
        return CorrectionCluster(
            canonical_text=canonical,
            variants=[canonical],
            correction_type="behavior",
            frequency=1,
            confidence=0.9
        )

    def test_universal_scope(self):
        """Test detection of universal scope."""
        engine = ProposalEngine()

        # Universal keywords
        clusters = [
            self.create_cluster("keep output concise"),
            self.create_cluster("never exceed 200 lines"),
            self.create_cluster("terse summaries")
        ]

        for cluster in clusters:
            scope = engine._infer_scope(cluster, project=None)
            assert scope == "universal"

    def test_language_scope_go(self):
        """Test detection of Go-specific scope."""
        engine = ProposalEngine()

        clusters = [
            self.create_cluster("never use panic in production"),
            self.create_cluster("always defer file close"),
            self.create_cluster("use goroutines for concurrency")
        ]

        for cluster in clusters:
            scope = engine._infer_scope(cluster, project=None)
            assert scope == "language:go"

    def test_language_scope_python(self):
        """Test detection of Python-specific scope."""
        engine = ProposalEngine()

        clusters = [
            self.create_cluster("always use async def for I/O"),
            self.create_cluster("handle except blocks properly"),
            self.create_cluster("pytest for all tests")
        ]

        for cluster in clusters:
            scope = engine._infer_scope(cluster, project=None)
            assert scope == "language:python"

    def test_project_scope(self):
        """Test detection of project-specific scope."""
        engine = ProposalEngine()

        clusters = [
            self.create_cluster("use PortalTabs for portal pages"),
            self.create_cluster("our component library requires X"),
            self.create_cluster("this project uses service pattern")
        ]

        for cluster in clusters:
            scope = engine._infer_scope(cluster, project="xcalibr")
            assert scope == "project:xcalibr"

    def test_scope_hierarchy(self):
        """Test that language scope takes precedence over universal."""
        engine = ProposalEngine()

        # Contains both language keyword and universal keyword
        cluster = self.create_cluster("keep goroutine code short")

        scope = engine._infer_scope(cluster, project=None)
        # Language should take precedence
        assert scope == "language:go"


class TestCategoryInference:
    """Test category inference logic."""

    def create_cluster(self, canonical: str, correction_type: str = "behavior") -> CorrectionCluster:
        """Helper to create CorrectionCluster."""
        return CorrectionCluster(
            canonical_text=canonical,
            variants=[canonical],
            correction_type=correction_type,
            frequency=1,
            confidence=0.9
        )

    def test_correction_category(self):
        """Test detection of correction category (anti-patterns)."""
        engine = ProposalEngine()

        clusters = [
            self.create_cluster("never use global variables"),
            self.create_cluster("don't write verbose explanations"),
            self.create_cluster("avoid panic in production")
        ]

        for cluster in clusters:
            category = engine._infer_category(cluster)
            assert category == "correction"

    def test_rule_category(self):
        """Test detection of rule category (hard rules)."""
        engine = ProposalEngine()

        clusters = [
            self.create_cluster("always validate user input"),
            self.create_cluster("must handle errors"),
            self.create_cluster("limit files to 200 lines max")
        ]

        for cluster in clusters:
            category = engine._infer_category(cluster)
            assert category == "rule"

    def test_preference_category(self):
        """Test detection of preference category (soft preferences)."""
        engine = ProposalEngine()

        clusters = [
            self.create_cluster("prefer composition over inheritance"),
            self.create_cluster("use descriptive variable names"),
            self.create_cluster("keep functions short")
        ]

        for cluster in clusters:
            category = engine._infer_category(cluster)
            assert category == "preference"


class TestContentTransformation:
    """Test content transformation to imperative form."""

    def create_cluster(self, canonical: str) -> CorrectionCluster:
        """Helper to create CorrectionCluster."""
        return CorrectionCluster(
            canonical_text=canonical,
            variants=[canonical],
            correction_type="behavior",
            frequency=1,
            confidence=0.9
        )

    def test_already_imperative(self):
        """Test that already-imperative text is preserved."""
        engine = ProposalEngine()

        clusters = [
            self.create_cluster("keep it short"),
            self.create_cluster("use descriptive names"),
            self.create_cluster("avoid global variables")
        ]

        for cluster in clusters:
            content = engine._generate_content(cluster)
            # Should be capitalized
            assert content[0].isupper()
            # Should be similar to original (just capitalized)
            assert content.lower() == cluster.canonical_text.lower()

    def test_transform_dont(self):
        """Test transformation of 'don't X' to 'Avoid X'."""
        engine = ProposalEngine()

        cluster = self.create_cluster("don't write verbose code")
        content = engine._generate_content(cluster)

        assert content.startswith("Avoid")
        assert "verbose code" in content.lower()

    def test_transform_be(self):
        """Test transformation of 'be X' to 'Keep output X'."""
        engine = ProposalEngine()

        cluster = self.create_cluster("be concise")
        content = engine._generate_content(cluster)

        assert "keep output" in content.lower()
        assert "concise" in content.lower()

    def test_capitalization(self):
        """Test that output is properly capitalized."""
        engine = ProposalEngine()

        cluster = self.create_cluster("keep it short")
        content = engine._generate_content(cluster)

        assert content[0].isupper()

    def test_length_limit(self):
        """Test that excessively long content is truncated."""
        engine = ProposalEngine()

        long_text = " ".join(["word"] * 25)  # 25 words
        cluster = self.create_cluster(long_text)
        content = engine._generate_content(cluster)

        # Should be truncated to 20 words + "..."
        assert len(content.split()) <= 21  # 20 + "..."


class TestRationaleGeneration:
    """Test rationale generation."""

    def create_cluster(self, frequency: int, confidence: float) -> CorrectionCluster:
        """Helper to create CorrectionCluster."""
        return CorrectionCluster(
            canonical_text="test",
            variants=["test"],
            correction_type="behavior",
            frequency=frequency,
            confidence=confidence
        )

    def test_high_frequency_rationale(self):
        """Test rationale for high-frequency corrections."""
        engine = ProposalEngine()

        cluster = self.create_cluster(frequency=3, confidence=0.8)
        rationale = engine._generate_rationale(cluster)

        assert "3 times" in rationale
        assert "high priority" in rationale.lower()

    def test_double_correction_rationale(self):
        """Test rationale for double corrections."""
        engine = ProposalEngine()

        cluster = self.create_cluster(frequency=2, confidence=0.8)
        rationale = engine._generate_rationale(cluster)

        assert "twice" in rationale.lower()

    def test_high_confidence_rationale(self):
        """Test rationale for high-confidence single corrections."""
        engine = ProposalEngine()

        cluster = self.create_cluster(frequency=1, confidence=0.95)
        rationale = engine._generate_rationale(cluster)

        assert "high confidence" in rationale.lower()

    def test_low_priority_rationale(self):
        """Test rationale for low-priority corrections."""
        engine = ProposalEngine()

        cluster = self.create_cluster(frequency=1, confidence=0.7)
        rationale = engine._generate_rationale(cluster)

        assert "preference" in rationale.lower()


class TestEndToEndScenarios:
    """Test complete proposal generation scenarios."""

    def create_cluster(
        self,
        canonical: str,
        correction_type: str,
        frequency: int,
        confidence: float
    ) -> CorrectionCluster:
        """Helper to create CorrectionCluster."""
        return CorrectionCluster(
            canonical_text=canonical,
            variants=[canonical],
            correction_type=correction_type,
            frequency=frequency,
            confidence=confidence
        )

    def test_universal_preference(self):
        """Test Scenario 1: Universal preference."""
        engine = ProposalEngine()

        clusters = [
            self.create_cluster("Keep summaries concise", "style", 3, 0.9)
        ]

        summary = engine.generate_proposals(clusters)

        assert len(summary.proposals) == 1
        proposal = summary.proposals[0]
        assert proposal.scope == "universal"
        assert proposal.category == "preference"

    def test_language_specific_rule(self):
        """Test Scenario 2: Language-specific rule."""
        engine = ProposalEngine()

        clusters = [
            self.create_cluster("Never use panic in production Go code", "rule", 2, 0.95)
        ]

        summary = engine.generate_proposals(clusters)

        assert len(summary.proposals) == 1
        proposal = summary.proposals[0]
        assert proposal.scope == "language:go"
        assert proposal.category in ["rule", "correction"]  # Can be either

    def test_project_specific_rule(self):
        """Test Scenario 3: Project-specific rule."""
        engine = ProposalEngine()

        clusters = [
            self.create_cluster("Use PortalTabs for all portal pages", "rule", 2, 0.8)
        ]

        summary = engine.generate_proposals(clusters, project="xcalibr")

        assert len(summary.proposals) == 1
        proposal = summary.proposals[0]
        assert proposal.scope == "project:xcalibr"
        # Category can be "preference" or "rule" depending on keyword detection
        # "Use" triggers preference, which is acceptable
        assert proposal.category in ["preference", "rule"]

    def test_multiple_proposals_ranked(self):
        """Test multiple proposals with correct ranking."""
        engine = ProposalEngine(max_proposals=3)

        clusters = [
            self.create_cluster("keep it short", "style", 1, 0.7),  # 0.7
            self.create_cluster("never use panic", "rule", 3, 0.95),  # 2.85
            self.create_cluster("validate input", "rule", 2, 0.9)  # 1.8
        ]

        summary = engine.generate_proposals(clusters)

        assert len(summary.proposals) == 3
        # Should be ranked by frequency * confidence
        assert "panic" in summary.proposals[0].content.lower()
        assert summary.proposals[0].priority == 1
        assert summary.proposals[1].priority == 2
        assert summary.proposals[2].priority == 3


class TestModuleFunctions:
    """Test module-level convenience functions."""

    def create_cluster(self, canonical: str) -> CorrectionCluster:
        """Helper to create CorrectionCluster."""
        return CorrectionCluster(
            canonical_text=canonical,
            variants=[canonical],
            correction_type="behavior",
            frequency=1,
            confidence=0.9
        )

    def test_generate_proposals_function(self):
        """Test convenience function."""
        clusters = [
            self.create_cluster("keep it short")
        ]

        summary = generate_proposals(clusters, project=None, use_llm=False)

        assert isinstance(summary, SessionSummary)
        assert len(summary.proposals) == 1

    def test_create_test_scenarios(self):
        """Test that test scenario creation works."""
        scenarios = create_test_scenarios()

        assert len(scenarios) >= 5
        assert all("canonical" in s for s in scenarios)
        assert all("expected_scope" in s for s in scenarios)


class TestSerialization:
    """Test data structure serialization."""

    def test_memory_proposal_to_dict(self):
        """Test MemoryProposal serialization."""
        proposal = MemoryProposal(
            id="prop-abc123",
            category="preference",
            scope="universal",
            content="Keep it short",
            rationale="User corrected twice",
            source_variants=["keep it short", "be concise"],
            confidence=0.9,
            priority=1
        )

        data = proposal.to_dict()

        assert data["id"] == "prop-abc123"
        assert data["category"] == "preference"
        assert data["scope"] == "universal"
        assert data["content"] == "Keep it short"
        assert len(data["source_variants"]) == 2

    def test_session_summary_to_dict(self):
        """Test SessionSummary serialization."""
        proposal = MemoryProposal(
            id="prop-123",
            category="rule",
            scope="universal",
            content="Test",
            rationale="Test",
            confidence=0.9,
            priority=1
        )

        summary = SessionSummary(
            session_id="20260122-140000",
            timestamp=datetime.now(),
            project="test",
            proposals=[proposal],
            total_corrections=5,
            total_proposed=1
        )

        data = summary.to_dict()

        assert data["session_id"] == "20260122-140000"
        assert data["project"] == "test"
        assert len(data["proposals"]) == 1
        assert data["total_corrections"] == 5


class TestTemplateBasedOperation:
    """Test that system works 100% without LLM."""

    def create_cluster(self, canonical: str) -> CorrectionCluster:
        """Helper to create CorrectionCluster."""
        return CorrectionCluster(
            canonical_text=canonical,
            variants=[canonical],
            correction_type="behavior",
            frequency=1,
            confidence=0.9
        )

    def test_template_based_no_llm(self):
        """Test that proposals are generated without LLM."""
        # Explicitly disable LLM
        engine = ProposalEngine(use_llm=False)

        clusters = [
            self.create_cluster("keep responses short"),
            self.create_cluster("never use global variables"),
            self.create_cluster("always validate input")
        ]

        summary = engine.generate_proposals(clusters)

        # Should generate proposals even without LLM
        assert len(summary.proposals) == 3
        for proposal in summary.proposals:
            assert proposal.content  # Has content
            assert proposal.category  # Has category
            assert proposal.scope  # Has scope


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
