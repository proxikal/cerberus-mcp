"""
Tests for the Index Limits (Bloat Protection) module.

Phase 19.6: Preflight, Enforcement, Validation
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from cerberus.limits.config import (
    IndexLimitsConfig,
    get_limits_config,
    reset_limits_config,
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_MAX_SYMBOLS_PER_FILE,
    DEFAULT_MAX_TOTAL_SYMBOLS,
)
from cerberus.limits.preflight import run_preflight_checks, PreflightResult
from cerberus.limits.enforcement import BloatEnforcer, EnforcementResult, EnforcementStats
from cerberus.limits.validation import validate_index_health, ValidationResult
from cerberus.exceptions import IndexLimitExceeded, PreflightError


class TestIndexLimitsConfig:
    """Test configuration loading and defaults."""

    def setup_method(self):
        """Reset config before each test."""
        reset_limits_config()
        # Clear any test env vars
        for key in list(os.environ.keys()):
            if key.startswith("CERBERUS_MAX") or key.startswith("CERBERUS_LIMIT"):
                os.environ.pop(key, None)

    def teardown_method(self):
        """Clean up after each test."""
        reset_limits_config()
        for key in list(os.environ.keys()):
            if key.startswith("CERBERUS_MAX") or key.startswith("CERBERUS_LIMIT"):
                os.environ.pop(key, None)

    def test_default_values(self):
        """Verify conservative defaults are set."""
        config = get_limits_config()
        assert config.max_file_bytes == 1 * 1024 * 1024  # 1MB
        assert config.max_symbols_per_file == 500
        assert config.max_total_symbols == 100_000
        assert config.max_index_size_mb == 100
        assert config.max_vectors == 100_000

    def test_env_var_override(self):
        """Test that env vars override defaults."""
        os.environ["CERBERUS_MAX_TOTAL_SYMBOLS"] = "500000"
        reset_limits_config()
        config = get_limits_config()
        assert config.max_total_symbols == 500_000

    def test_to_dict(self):
        """Test config serialization."""
        config = get_limits_config()
        d = config.to_dict()
        assert "max_file_bytes" in d
        assert "max_symbols_per_file" in d
        assert "max_total_symbols" in d
        assert d["max_file_bytes"] == config.max_file_bytes

    def test_singleton_pattern(self):
        """Test that get_limits_config returns same instance."""
        config1 = get_limits_config()
        config2 = get_limits_config()
        assert config1 is config2

    def test_reset_clears_singleton(self):
        """Test that reset allows new config."""
        config1 = get_limits_config()
        reset_limits_config()
        config2 = get_limits_config()
        # New instance after reset
        assert config1 is not config2


class TestPreflight:
    """Test pre-flight checks."""

    def test_preflight_passes_with_space(self):
        """Test that preflight passes when disk has space."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_preflight_checks(Path(tmpdir))
            assert isinstance(result, PreflightResult)
            assert result.can_proceed is True

    def test_preflight_checks_disk_space(self):
        """Test that disk space check is included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_preflight_checks(Path(tmpdir))
            check_names = [c["name"] for c in result.checks]
            assert "disk_space" in check_names

    def test_preflight_checks_permissions(self):
        """Test that permission check is included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_preflight_checks(Path(tmpdir))
            check_names = [c["name"] for c in result.checks]
            assert "write_permission" in check_names

    def test_preflight_result_to_dict(self):
        """Test PreflightResult serialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_preflight_checks(Path(tmpdir))
            d = result.to_dict()
            assert "status" in d
            assert "can_proceed" in d
            assert "checks" in d


class TestBloatEnforcer:
    """Test real-time enforcement."""

    def setup_method(self):
        """Reset config and clear env vars before each test."""
        for key in list(os.environ.keys()):
            if key.startswith("CERBERUS_MAX") or key.startswith("CERBERUS_LIMIT"):
                os.environ.pop(key, None)
        reset_limits_config()

    def teardown_method(self):
        """Clean up after each test."""
        for key in list(os.environ.keys()):
            if key.startswith("CERBERUS_MAX") or key.startswith("CERBERUS_LIMIT"):
                os.environ.pop(key, None)
        reset_limits_config()

    def test_enforcer_initializes_with_config(self):
        """Test enforcer uses config."""
        enforcer = BloatEnforcer()
        assert enforcer.config is not None
        assert enforcer.stats.total_symbols == 0

    def test_enforce_file_size_allows_small_files(self):
        """Test that small files pass."""
        enforcer = BloatEnforcer()
        result = enforcer.enforce_file_size(Path("test.py"), 1000)
        assert result.allowed is True
        assert result.status == "ok"

    def test_enforce_file_size_skips_large_files(self):
        """Test that large files are skipped."""
        enforcer = BloatEnforcer()
        # 10MB file
        result = enforcer.enforce_file_size(Path("test.py"), 10 * 1024 * 1024)
        assert result.allowed is False
        assert result.status == "skip"
        assert enforcer.stats.files_skipped_size == 1

    def test_enforce_symbols_per_file_allows_normal(self):
        """Test that normal symbol counts pass."""
        enforcer = BloatEnforcer()
        symbols = [MagicMock() for _ in range(100)]
        result_symbols, result = enforcer.enforce_symbols_per_file("test.py", symbols)
        assert len(result_symbols) == 100
        assert result.allowed is True

    def test_enforce_symbols_per_file_truncates_excess(self):
        """Test that excess symbols are truncated."""
        enforcer = BloatEnforcer()
        # Create more symbols than limit
        symbols = [MagicMock() for _ in range(1000)]
        result_symbols, result = enforcer.enforce_symbols_per_file("test.py", symbols)
        assert len(result_symbols) == enforcer.config.max_symbols_per_file
        assert result.status == "warn"
        assert enforcer.stats.symbols_truncated_count > 0

    def test_enforce_total_symbols_allows_under_limit(self):
        """Test that under-limit totals pass."""
        enforcer = BloatEnforcer()
        result = enforcer.enforce_total_symbols(1000)
        assert result.allowed is True
        assert enforcer.stats.total_symbols == 1000

    def test_enforce_total_symbols_stops_at_limit(self):
        """Test that over-limit totals are stopped."""
        # Set low limit for testing
        os.environ["CERBERUS_MAX_TOTAL_SYMBOLS"] = "100"
        reset_limits_config()

        enforcer = BloatEnforcer()
        result = enforcer.enforce_total_symbols(150)
        assert result.allowed is False
        assert result.status == "stop"
        assert enforcer.stats.limit_reached is True

    def test_get_summary(self):
        """Test summary generation."""
        enforcer = BloatEnforcer()
        enforcer.enforce_total_symbols(500)
        summary = enforcer.get_summary()
        assert "stats" in summary
        assert "config" in summary
        assert summary["stats"]["total_symbols"] == 500


class TestValidation:
    """Test post-index validation."""

    def test_validate_nonexistent_index(self):
        """Test validation of missing index."""
        result = validate_index_health(Path("/nonexistent/path"))
        assert isinstance(result, ValidationResult)
        # Should warn or fail on missing index
        assert result.status in ("warn", "fail")

    def test_validation_result_to_dict(self):
        """Test ValidationResult serialization."""
        result = ValidationResult(
            status="ok",
            checks=[{"name": "test", "status": "ok"}],
            summary="All good",
        )
        d = result.to_dict()
        assert d["status"] == "ok"
        assert len(d["checks"]) == 1


class TestExceptions:
    """Test custom exceptions."""

    def test_index_limit_exceeded(self):
        """Test IndexLimitExceeded exception."""
        exc = IndexLimitExceeded(
            limit_name="total_symbols",
            current=150000,
            maximum=100000,
            remediation="Increase limit",
        )
        assert exc.limit_name == "total_symbols"
        assert exc.current == 150000
        assert exc.maximum == 100000
        assert "150,000" in str(exc)
        assert "100,000" in str(exc)

    def test_preflight_error(self):
        """Test PreflightError exception."""
        exc = PreflightError("Disk full", checks=[{"name": "disk", "status": "fail"}])
        assert exc.checks is not None
        assert len(exc.checks) == 1
        assert "Disk full" in str(exc)


class TestEnforcerStreamWrapper:
    """Test the wrap_file_stream functionality."""

    def setup_method(self):
        """Reset config and clear env vars before each test."""
        for key in list(os.environ.keys()):
            if key.startswith("CERBERUS_MAX") or key.startswith("CERBERUS_LIMIT"):
                os.environ.pop(key, None)
        reset_limits_config()

    def teardown_method(self):
        """Clean up after each test."""
        for key in list(os.environ.keys()):
            if key.startswith("CERBERUS_MAX") or key.startswith("CERBERUS_LIMIT"):
                os.environ.pop(key, None)
        reset_limits_config()

    def test_wrap_file_stream_passes_through(self):
        """Test that stream wrapper yields results."""
        enforcer = BloatEnforcer()

        # Create mock file results
        mock_results = []
        for i in range(3):
            result = MagicMock()
            result.file_obj = MagicMock()
            result.file_obj.path = f"file{i}.py"
            result.symbols = [MagicMock() for _ in range(10)]
            mock_results.append(result)

        # Wrap and consume
        wrapped = list(enforcer.wrap_file_stream(iter(mock_results)))

        assert len(wrapped) == 3
        assert enforcer.stats.files_processed == 3
        assert enforcer.stats.total_symbols == 30

    def test_wrap_file_stream_stops_at_limit(self):
        """Test that stream stops when limit reached."""
        # Set very low limit
        os.environ["CERBERUS_MAX_TOTAL_SYMBOLS"] = "15"
        reset_limits_config()

        enforcer = BloatEnforcer()

        # Create mock file results with 10 symbols each
        mock_results = []
        for i in range(5):
            result = MagicMock()
            result.file_obj = MagicMock()
            result.file_obj.path = f"file{i}.py"
            result.symbols = [MagicMock() for _ in range(10)]
            mock_results.append(result)

        # Wrap and consume - should stop early
        wrapped = list(enforcer.wrap_file_stream(iter(mock_results)))

        # Should have stopped before processing all 5
        assert len(wrapped) < 5
        assert enforcer.stats.limit_reached is True


class TestIntegration:
    """Integration tests for the limits system."""

    def setup_method(self):
        """Reset config before each test."""
        reset_limits_config()

    def teardown_method(self):
        """Clean up after each test."""
        reset_limits_config()
        for key in list(os.environ.keys()):
            if key.startswith("CERBERUS_"):
                os.environ.pop(key, None)

    def test_full_flow_preflight_to_enforcement(self):
        """Test preflight check followed by enforcement."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Preflight
            preflight = run_preflight_checks(Path(tmpdir))
            assert preflight.can_proceed is True

            # Enforcement
            enforcer = BloatEnforcer()
            enforcer.enforce_total_symbols(100)
            summary = enforcer.get_summary()

            assert summary["status"] == "ok"
            assert summary["stats"]["total_symbols"] == 100

    def test_config_propagates_through_system(self):
        """Test that config changes affect all components."""
        os.environ["CERBERUS_MAX_TOTAL_SYMBOLS"] = "50"
        reset_limits_config()

        config = get_limits_config()
        assert config.max_total_symbols == 50

        enforcer = BloatEnforcer()
        assert enforcer.config.max_total_symbols == 50

        # 60 symbols should exceed limit
        result = enforcer.enforce_total_symbols(60)
        assert result.allowed is False
