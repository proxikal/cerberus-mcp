"""Tests for Phase 13.5 Section 1: Auto-Hydration."""

import pytest
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

pytestmark = [pytest.mark.fast, pytest.mark.blueprint]

from cerberus.blueprint.hydration_analyzer import HydrationAnalyzer
from cerberus.blueprint.schemas import (
    Blueprint,
    BlueprintNode,
    DependencyInfo,
    SymbolOverlay,
)


class TestHydrationAnalyzer:
    """Tests for HydrationAnalyzer class."""

    @pytest.fixture
    def mock_conn(self):
        """Create mock SQLite connection."""
        conn = MagicMock(spec=sqlite3.Connection)
        return conn

    @pytest.fixture
    def analyzer(self, tmp_path, mock_conn):
        """Create HydrationAnalyzer instance."""
        return HydrationAnalyzer(mock_conn, project_root=tmp_path)

    def test_initialization(self, analyzer, tmp_path):
        """Test HydrationAnalyzer initializes correctly."""
        assert analyzer.project_root == tmp_path
        assert analyzer.MIN_REFERENCES_THRESHOLD == 3
        assert analyzer.MAX_HYDRATED_TOKENS == 2000

    def test_count_file_references_empty_blueprint(self, analyzer):
        """Test counting references with empty blueprint."""
        blueprint = Blueprint(
            file_path="/test/file.py",
            nodes=[],
            total_symbols=0
        )

        refs = analyzer._count_file_references(blueprint)
        assert len(refs) == 0

    def test_count_file_references_with_dependencies(self, analyzer):
        """Test counting file references from dependencies."""
        dep1 = DependencyInfo(
            target="func1",
            target_file="/test/utils.py",
            confidence=0.9
        )
        dep2 = DependencyInfo(
            target="func2",
            target_file="/test/utils.py",
            confidence=0.8
        )
        dep3 = DependencyInfo(
            target="func3",
            target_file="/test/helpers.py",
            confidence=0.7
        )

        node = BlueprintNode(
            name="test_func",
            type="function",
            start_line=1,
            end_line=10,
            overlay=SymbolOverlay(
                dependencies=[dep1, dep2, dep3]
            )
        )

        blueprint = Blueprint(
            file_path="/test/file.py",
            nodes=[node],
            total_symbols=1
        )

        refs = analyzer._count_file_references(blueprint)
        assert refs["/test/utils.py"] == 2
        assert refs["/test/helpers.py"] == 1

    def test_count_file_references_excludes_self(self, analyzer):
        """Test that file references exclude the source file itself."""
        dep = DependencyInfo(
            target="func",
            target_file="/test/file.py",
            confidence=0.9
        )

        node = BlueprintNode(
            name="test_func",
            type="function",
            start_line=1,
            end_line=10,
            overlay=SymbolOverlay(dependencies=[dep])
        )

        blueprint = Blueprint(
            file_path="/test/file.py",
            nodes=[node],
            total_symbols=1
        )

        refs = analyzer._count_file_references(blueprint)
        assert "/test/file.py" not in refs

    def test_is_internal_file_under_project_root(self, analyzer, tmp_path):
        """Test internal file detection for files under project root."""
        test_file = tmp_path / "src" / "test.py"
        test_file.parent.mkdir(parents=True)
        test_file.touch()

        assert analyzer._is_internal_file(str(test_file)) is True

    def test_is_internal_file_site_packages(self, analyzer, tmp_path):
        """Test external file detection for site-packages."""
        external_path = "/usr/lib/python3.9/site-packages/module.py"
        assert analyzer._is_internal_file(external_path) is False

    def test_is_internal_file_venv(self, analyzer, tmp_path):
        """Test external file detection for virtualenv."""
        venv_path = str(tmp_path / ".venv" / "lib" / "module.py")
        assert analyzer._is_internal_file(venv_path) is False

    def test_estimate_symbol_count(self, analyzer, mock_conn):
        """Test symbol count estimation."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)
        mock_conn.execute.return_value = mock_cursor

        count = analyzer._estimate_symbol_count("/test/file.py")
        assert count == 42

    def test_estimate_symbol_count_error_handling(self, analyzer, mock_conn):
        """Test symbol count estimation with database error."""
        mock_conn.execute.side_effect = sqlite3.Error("DB error")

        count = analyzer._estimate_symbol_count("/test/file.py")
        assert count == 10

    def test_analyze_for_hydration_no_dependencies(self, analyzer):
        """Test hydration analysis with no dependencies."""
        blueprint = Blueprint(
            file_path="/test/file.py",
            nodes=[],
            total_symbols=0
        )

        result = analyzer.analyze_for_hydration(blueprint)
        assert result == []

    def test_analyze_for_hydration_insufficient_references(self, analyzer):
        """Test hydration with files below threshold (< 3 refs)."""
        dep = DependencyInfo(
            target="func",
            target_file="/test/utils.py",
            confidence=0.9
        )

        node = BlueprintNode(
            name="test",
            type="function",
            start_line=1,
            end_line=10,
            overlay=SymbolOverlay(dependencies=[dep, dep])
        )

        blueprint = Blueprint(
            file_path="/test/file.py",
            nodes=[node],
            total_symbols=1
        )

        with patch.object(analyzer, '_is_internal_file', return_value=True):
            result = analyzer.analyze_for_hydration(blueprint)
            assert result == []

    def test_analyze_for_hydration_selects_hot_files(self, analyzer, mock_conn):
        """Test hydration selects files with sufficient references."""
        deps = [
            DependencyInfo(
                target=f"func{i}",
                target_file="/test/utils.py",
                confidence=0.9
            )
            for i in range(5)
        ]

        node = BlueprintNode(
            name="test",
            type="function",
            start_line=1,
            end_line=10,
            overlay=SymbolOverlay(dependencies=deps)
        )

        blueprint = Blueprint(
            file_path="/test/file.py",
            nodes=[node],
            total_symbols=1
        )

        with patch.object(analyzer, '_is_internal_file', return_value=True):
            with patch.object(analyzer, '_estimate_symbol_count', return_value=10):
                result = analyzer.analyze_for_hydration(blueprint)
                assert "/test/utils.py" in result

    def test_analyze_for_hydration_token_budget(self, analyzer, mock_conn):
        """Test hydration respects token budget."""
        deps = [
            DependencyInfo(
                target=f"func{i}",
                target_file="/test/large.py",
                confidence=0.9
            )
            for i in range(10)
        ]

        node = BlueprintNode(
            name="test",
            type="function",
            start_line=1,
            end_line=10,
            overlay=SymbolOverlay(dependencies=deps)
        )

        blueprint = Blueprint(
            file_path="/test/file.py",
            nodes=[node],
            total_symbols=1
        )

        with patch.object(analyzer, '_is_internal_file', return_value=True):
            with patch.object(analyzer, '_estimate_symbol_count', return_value=1000):
                result = analyzer.analyze_for_hydration(blueprint)
                assert result == []
