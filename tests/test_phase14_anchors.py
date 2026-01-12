"""
Phase 14.2 Tests: Context Anchors

Tests for GPS metadata generation and hallucination prevention.
"""

import pytest
import tempfile
import os
from pathlib import Path

pytestmark = pytest.mark.fast

from cerberus.anchoring import (
    ContextAnchorV2,
    AnchorConfig,
    AnchorGenerator,
    GPSLocation,
    DependencyInfo,
    RiskInfo,
    RiskLevel,
    TemporalInfo,
    SafetyInfo,
    GuardStatus,
    AnchorMetadata,
)


class TestGPSLocation:
    """Test GPS location metadata."""

    def test_gps_creation(self):
        """Test creating GPS location."""
        gps = GPSLocation(
            file="src/main.py",
            symbol="foo",
            lines={"start": 10, "end": 20},
            symbol_type="function",
        )

        assert gps.file == "src/main.py"
        assert gps.symbol == "foo"
        assert gps.lines["start"] == 10
        assert gps.lines["end"] == 20

    def test_gps_to_dict(self):
        """Test GPS to dictionary conversion."""
        gps = GPSLocation(
            file="src/main.py",
            symbol="foo",
            lines={"start": 10, "end": 20},
        )

        d = gps.to_dict()
        assert d["file"] == "src/main.py"
        assert d["symbol"] == "foo"
        assert d["lines"] == {"start": 10, "end": 20}

    def test_gps_compact(self):
        """Test GPS compact representation."""
        gps = GPSLocation(
            file="src/main.py",
            symbol="foo",
            lines={"start": 10, "end": 20},
        )

        compact = gps.to_compact_dict()
        assert "f" in compact
        assert "s" in compact
        assert "l" in compact
        assert compact["f"] == "src/main.py"


class TestDependencyInfo:
    """Test dependency metadata."""

    def test_dependency_creation(self):
        """Test creating dependency info."""
        dep = DependencyInfo(
            name="bar",
            confidence=1.0,
            type="call",
            file="src/util.py",
            line=45,
        )

        assert dep.name == "bar"
        assert dep.confidence == 1.0
        assert dep.type == "call"

    def test_dependency_compact(self):
        """Test dependency compact representation."""
        dep = DependencyInfo(
            name="bar",
            confidence=0.9,
            type="call",
        )

        compact = dep.to_compact_dict()
        assert compact["n"] == "bar"
        assert compact["c"] == 0.9
        assert compact["t"] == "call"


class TestRiskInfo:
    """Test risk/stability metadata."""

    def test_risk_levels(self):
        """Test risk level enumeration."""
        assert RiskLevel.SAFE.value == "SAFE"
        assert RiskLevel.MEDIUM.value == "MEDIUM"
        assert RiskLevel.HIGH.value == "HIGH"

    def test_risk_creation(self):
        """Test creating risk info."""
        risk = RiskInfo(
            level=RiskLevel.MEDIUM,
            score=0.65,
            factors={"churn_per_week": 0.8, "test_coverage": 0.85},
        )

        assert risk.level == RiskLevel.MEDIUM
        assert risk.score == 0.65
        assert "churn_per_week" in risk.factors

    def test_risk_compact(self):
        """Test risk compact representation."""
        risk = RiskInfo(
            level=RiskLevel.HIGH,
            score=0.87,
        )

        compact = risk.to_compact_dict()
        assert compact["l"] == "H"
        assert compact["s"] == 0.87


class TestAnchorMetadata:
    """Test complete anchor metadata."""

    def test_anchor_creation(self):
        """Test creating complete anchor."""
        gps = GPSLocation(
            file="src/main.py",
            symbol="foo",
            lines={"start": 10, "end": 20},
        )

        dep = DependencyInfo(
            name="bar",
            confidence=1.0,
            type="call",
        )

        risk = RiskInfo(
            level=RiskLevel.SAFE,
            score=0.2,
        )

        anchor = AnchorMetadata(
            gps=gps,
            dependencies=[dep],
            risk=risk,
        )

        assert anchor.gps.symbol == "foo"
        assert len(anchor.dependencies) == 1
        assert anchor.risk.level == RiskLevel.SAFE

    def test_anchor_to_dict_full(self):
        """Test anchor full JSON format."""
        gps = GPSLocation(
            file="src/main.py",
            symbol="foo",
            lines={"start": 10, "end": 20},
        )

        anchor = AnchorMetadata(gps=gps)
        d = anchor.to_dict(compact=False)

        assert "gps" in d
        assert d["gps"]["file"] == "src/main.py"

    def test_anchor_to_dict_compact(self):
        """Test anchor compact JSON format (<5% overhead)."""
        gps = GPSLocation(
            file="src/main.py",
            symbol="foo",
            lines={"start": 10, "end": 20},
        )

        anchor = AnchorMetadata(gps=gps)
        compact = anchor.to_dict(compact=True)

        assert "gps" in compact
        assert "f" in compact["gps"]

    def test_anchor_human_string(self):
        """Test anchor human-readable format."""
        gps = GPSLocation(
            file="src/main.py",
            symbol="foo",
            lines={"start": 10, "end": 20},
        )

        anchor = AnchorMetadata(gps=gps)
        human = anchor.to_human_string()

        assert "GPS" in human
        assert "src/main.py" in human
        assert "foo" in human
        assert "10-20" in human


class TestAnchorConfig:
    """Test anchor configuration."""

    def test_default_mode(self):
        """Test default anchor mode is JSON."""
        # Clear env
        os.environ.pop("CERBERUS_ANCHORS", None)
        os.environ.pop("CERBERUS_ANCHOR_COMPACT", None)

        mode = AnchorConfig.get_mode()
        assert mode.value == "json"

    def test_compact_mode(self):
        """Test compact mode from env."""
        os.environ["CERBERUS_ANCHORS"] = "compact"
        mode = AnchorConfig.get_mode()
        assert mode.value == "compact"

        # Cleanup
        os.environ.pop("CERBERUS_ANCHORS")

    def test_off_mode(self):
        """Test disabled anchors."""
        os.environ["CERBERUS_ANCHORS"] = "off"
        mode = AnchorConfig.get_mode()
        assert mode.value == "off"
        assert not AnchorConfig.is_enabled()

        # Cleanup
        os.environ.pop("CERBERUS_ANCHORS")


class TestAnchorGenerator:
    """Test anchor generator."""

    def test_generator_creation(self):
        """Test creating anchor generator."""
        gen = AnchorGenerator()
        assert gen is not None

    def test_gps_extraction_no_store(self):
        """Test GPS extraction without store (fallback)."""
        gen = AnchorGenerator()
        gps = gen._extract_gps("test.py", "foo")

        assert gps is not None
        assert gps.file == "test.py"
        assert gps.symbol == "foo"


class TestContextAnchorV2:
    """Test main anchor system."""

    def test_anchor_system_creation(self):
        """Test creating anchor system."""
        system = ContextAnchorV2()
        assert system is not None

    def test_wrap_symbol_output_disabled(self):
        """Test wrapping when anchors disabled."""
        os.environ["CERBERUS_ANCHORS"] = "off"
        system = ContextAnchorV2()

        body = {"code": "def foo(): pass"}
        result = system.wrap_symbol_output(
            file_path="test.py",
            symbol_name="foo",
            body=body,
        )

        assert result == body

        # Cleanup
        os.environ.pop("CERBERUS_ANCHORS")

    def test_validate_symbol_location(self):
        """Test symbol location validation (hallucination detection)."""
        system = ContextAnchorV2()

        # This will fail without store, but should return gracefully
        is_valid, error = system.validate_symbol_location("test.py", "foo")

        # Without store, validation should fail
        assert not is_valid
        assert error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
