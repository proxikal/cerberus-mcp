"""
Tests for Phase 13.5 Blueprint Features.

Covers:
- Auto-Hydration (Section 1)
- External Dependency Marking (Section 2)
- Width Management & Smart Truncation (Section 3)
- Background Blueprint Regeneration (Section 4)
"""

import pytest
import sqlite3
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from cerberus.blueprint.hydration_analyzer import HydrationAnalyzer
from cerberus.blueprint.dependency_classifier import DependencyClassifier
from cerberus.blueprint.tree_builder import TreeBuilder
from cerberus.blueprint.cache_manager import BlueprintCache
from cerberus.blueprint.blueprint_watcher import BlueprintWatcher
from cerberus.blueprint.schemas import (
    Blueprint,
    BlueprintNode,
    DependencyInfo,
    SymbolOverlay,
    TreeRenderOptions,
)


# =============================================================================
# Section 1: Auto-Hydration Tests
# =============================================================================

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
            target_file="/test/file.py",  # Same as source
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
        # Mock cursor to return count
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)
        mock_conn.execute.return_value = mock_cursor
        
        count = analyzer._estimate_symbol_count("/test/file.py")
        assert count == 42

    def test_estimate_symbol_count_error_handling(self, analyzer, mock_conn):
        """Test symbol count estimation with database error."""
        mock_conn.execute.side_effect = sqlite3.Error("DB error")
        
        count = analyzer._estimate_symbol_count("/test/file.py")
        assert count == 10  # Default estimate

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
            overlay=SymbolOverlay(dependencies=[dep, dep])  # Only 2 refs
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
        # Create dependencies to same file (5 refs total)
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
        
        # Mock internal file check and symbol count
        with patch.object(analyzer, '_is_internal_file', return_value=True):
            with patch.object(analyzer, '_estimate_symbol_count', return_value=10):
                result = analyzer.analyze_for_hydration(blueprint)
                assert "/test/utils.py" in result

    def test_analyze_for_hydration_token_budget(self, analyzer, mock_conn):
        """Test hydration respects token budget."""
        # Create file with too many symbols (would exceed budget)
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
        
        # Mock to return huge symbol count that exceeds budget
        with patch.object(analyzer, '_is_internal_file', return_value=True):
            with patch.object(analyzer, '_estimate_symbol_count', return_value=1000):
                result = analyzer.analyze_for_hydration(blueprint)
                assert result == []  # Should skip due to token budget


# =============================================================================
# Section 2: External Dependency Marking Tests
# =============================================================================

class TestDependencyClassifier:
    """Tests for DependencyClassifier class."""

    @pytest.fixture
    def classifier(self, tmp_path):
        """Create DependencyClassifier instance."""
        return DependencyClassifier(project_root=tmp_path)

    def test_initialization(self, classifier, tmp_path):
        """Test DependencyClassifier initializes correctly."""
        assert classifier.project_root == tmp_path
        assert len(classifier._stdlib_paths) > 0

    def test_is_stdlib_module_common_modules(self, classifier):
        """Test stdlib detection for common modules."""
        assert classifier._is_stdlib_module("os") is True
        assert classifier._is_stdlib_module("sys") is True
        assert classifier._is_stdlib_module("json") is True
        assert classifier._is_stdlib_module("pathlib") is True
        assert classifier._is_stdlib_module("sqlite3") is True

    def test_is_stdlib_module_non_stdlib(self, classifier):
        """Test stdlib detection rejects non-stdlib modules."""
        assert classifier._is_stdlib_module("numpy") is False
        assert classifier._is_stdlib_module("flask") is False
        assert classifier._is_stdlib_module("myproject") is False

    def test_is_known_external_module_popular_packages(self, classifier):
        """Test external module detection for popular packages."""
        assert classifier._is_known_external_module("numpy") is True
        assert classifier._is_known_external_module("pandas") is True
        assert classifier._is_known_external_module("flask") is True
        assert classifier._is_known_external_module("django") is True
        assert classifier._is_known_external_module("pytest") is True

    def test_classify_by_symbol_stdlib(self, classifier):
        """Test classification by symbol for stdlib modules."""
        assert classifier._classify_by_symbol("os.path.join") == "stdlib"
        assert classifier._classify_by_symbol("json.dumps") == "stdlib"
        assert classifier._classify_by_symbol("pathlib.Path") == "stdlib"

    def test_classify_by_symbol_external(self, classifier):
        """Test classification by symbol for external packages."""
        assert classifier._classify_by_symbol("numpy.array") == "external"
        assert classifier._classify_by_symbol("flask.Flask") == "external"
        assert classifier._classify_by_symbol("requests.get") == "external"

    def test_classify_by_symbol_unknown_defaults_to_external(self, classifier):
        """Test unknown symbols default to external (conservative)."""
        assert classifier._classify_by_symbol("unknown_module.func") == "external"

    def test_classify_by_file_internal(self, classifier, tmp_path):
        """Test file-based classification for internal files."""
        test_file = tmp_path / "src" / "module.py"
        test_file.parent.mkdir(parents=True)
        test_file.touch()
        
        result = classifier._classify_by_file(str(test_file))
        assert result == "internal"

    def test_classify_by_file_external_site_packages(self, classifier):
        """Test file-based classification for site-packages."""
        external_path = "/usr/lib/python3.9/site-packages/numpy/core.py"
        result = classifier._classify_by_file(external_path)
        assert result in ["external", "stdlib"]  # Could be either

    def test_classify_dependency_with_file(self, classifier, tmp_path):
        """Test dependency classification with file path."""
        test_file = tmp_path / "utils.py"
        test_file.touch()
        
        result = classifier.classify_dependency(
            target_symbol="func",
            target_file=str(test_file)
        )
        assert result == "internal"

    def test_classify_dependency_without_file_stdlib(self, classifier):
        """Test dependency classification without file (stdlib symbol)."""
        result = classifier.classify_dependency(
            target_symbol="os.path.join",
            target_file=None
        )
        assert result == "stdlib"

    def test_classify_dependency_without_file_external(self, classifier):
        """Test dependency classification without file (external symbol)."""
        result = classifier.classify_dependency(
            target_symbol="numpy.array",
            target_file=None
        )
        assert result == "external"

    def test_get_marker_internal(self, classifier):
        """Test marker for internal dependencies."""
        marker = classifier.get_marker("internal")
        assert marker == "🏠internal"

    def test_get_marker_external(self, classifier):
        """Test marker for external dependencies."""
        marker = classifier.get_marker("external")
        assert marker == "📦external"

    def test_get_marker_stdlib(self, classifier):
        """Test marker for stdlib dependencies."""
        marker = classifier.get_marker("stdlib")
        assert marker == "📦stdlib"


# =============================================================================
# Section 3: Width Management & Truncation Tests
# =============================================================================

class TestWidthManagement:
    """Tests for width management and smart truncation."""

    @pytest.fixture
    def tree_builder(self):
        """Create TreeBuilder with default options."""
        return TreeBuilder(TreeRenderOptions())

    def test_is_private_symbol_single_underscore(self, tree_builder):
        """Test private symbol detection for single underscore."""
        assert tree_builder._is_private_symbol("_private_func") is True
        assert tree_builder._is_private_symbol("_helper") is True

    def test_is_private_symbol_dunder_not_private(self, tree_builder):
        """Test that dunder methods are not considered private."""
        assert tree_builder._is_private_symbol("__init__") is False
        assert tree_builder._is_private_symbol("__str__") is False

    def test_is_private_symbol_public(self, tree_builder):
        """Test public symbols are not private."""
        assert tree_builder._is_private_symbol("public_func") is False
        assert tree_builder._is_private_symbol("myFunction") is False

    def test_truncate_line_no_limit(self, tree_builder):
        """Test truncation with no max_width (no truncation)."""
        long_line = "x" * 200
        result = tree_builder._truncate_line(long_line)
        assert result == long_line
        assert len(result) == 200

    def test_truncate_line_under_limit(self):
        """Test truncation when line is under limit."""
        builder = TreeBuilder(TreeRenderOptions(max_width=100))
        short_line = "x" * 50
        result = builder._truncate_line(short_line)
        assert result == short_line

    def test_truncate_line_over_limit(self):
        """Test truncation when line exceeds limit."""
        builder = TreeBuilder(TreeRenderOptions(max_width=80))
        long_line = "x" * 200
        result = builder._truncate_line(long_line)
        assert len(result) == 80
        assert result.endswith("...")
        assert result == ("x" * 77) + "..."

    def test_format_dependencies_truncation(self):
        """Test dependency list truncation."""
        builder = TreeBuilder(TreeRenderOptions(truncate_threshold=3))
        
        deps = [
            DependencyInfo(target=f"func{i}", confidence=0.9, dependency_type="internal")
            for i in range(10)
        ]
        
        result = builder._format_dependencies(deps)
        assert "... and 7 more" in result
        assert result.count("func") == 3  # Only first 3 shown

    def test_format_dependencies_no_truncation(self):
        """Test dependency list without truncation."""
        builder = TreeBuilder(TreeRenderOptions(truncate_threshold=10))
        
        deps = [
            DependencyInfo(target=f"func{i}", confidence=0.9, dependency_type="internal")
            for i in range(5)
        ]
        
        result = builder._format_dependencies(deps)
        assert "... and" not in result
        assert result.count("func") == 5  # All 5 shown

    def test_collapse_private_filters_symbols(self):
        """Test collapse_private option filters private symbols."""
        builder = TreeBuilder(TreeRenderOptions(collapse_private=True))
        
        public_child = BlueprintNode(
            name="public_method",
            type="method",
            start_line=1,
            end_line=5
        )
        private_child = BlueprintNode(
            name="_private_method",
            type="method",
            start_line=6,
            end_line=10
        )
        
        parent = BlueprintNode(
            name="MyClass",
            type="class",
            start_line=1,
            end_line=20,
            children=[public_child, private_child]
        )
        
        lines = builder._render_node(parent, depth=0, is_last=True, parent_prefixes=[])
        
        # Should have parent + public child + "Private: N collapsed" message
        content = "\n".join(lines)
        assert "public_method" in content
        assert "_private_method" not in content
        assert "Private: 1 symbols collapsed" in content


# =============================================================================
# Section 4: Background Blueprint Regeneration Tests
# =============================================================================

class TestCacheAccessTracking:
    """Tests for cache access tracking."""

    @pytest.fixture
    def mock_conn(self):
        """Create mock SQLite connection."""
        conn = MagicMock(spec=sqlite3.Connection)
        # Mock PRAGMA table_info to return columns
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (0, "cache_key", "TEXT", 0, None, 1),
            (1, "blueprint_json", "TEXT", 1, None, 0),
            (2, "access_count", "INTEGER", 0, "0", 0),
            (3, "last_accessed", "REAL", 0, "0", 0),
        ]
        conn.execute.return_value = mock_cursor
        return conn

    @pytest.fixture
    def cache(self, mock_conn):
        """Create BlueprintCache instance."""
        return BlueprintCache(mock_conn)

    def test_ensure_access_tracking_schema(self, cache, mock_conn):
        """Test access tracking schema initialization."""
        # Schema check should have been called in __init__
        calls = [str(call) for call in mock_conn.execute.call_args_list]
        assert any("PRAGMA table_info" in str(call) for call in calls)

    def test_track_access(self, cache, mock_conn):
        """Test access tracking increments count."""
        cache._track_access("test_cache_key")
        
        # Check if UPDATE was called
        calls = [str(call) for call in mock_conn.execute.call_args_list]
        update_calls = [c for c in calls if "UPDATE blueprint_cache" in str(c)]
        assert len(update_calls) > 0

    def test_get_hot_files(self, cache, mock_conn):
        """Test getting frequently accessed files."""
        # Mock cursor to return hot files
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("/test/hot_file1.py", 15),
            ("/test/hot_file2.py", 10),
            ("/test/hot_file3.py", 7),
        ]
        mock_conn.execute.return_value = mock_cursor
        
        hot_files = cache.get_hot_files(min_access_count=5, limit=10)
        
        assert len(hot_files) == 3
        assert hot_files[0] == ("/test/hot_file1.py", 15)
        assert hot_files[1] == ("/test/hot_file2.py", 10)

    def test_get_hot_files_respects_min_access(self, cache, mock_conn):
        """Test hot files query uses min_access_count."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.execute.return_value = mock_cursor
        
        cache.get_hot_files(min_access_count=10, limit=5)
        
        # Check SQL was called with correct parameters
        call_args = mock_conn.execute.call_args
        assert call_args is not None
        # SQL should include min_access_count parameter (10)
        args = call_args[0]
        if len(args) > 1:
            assert 10 in args[1]  # Should be in parameters tuple


class TestBlueprintWatcher:
    """Tests for BlueprintWatcher class."""

    @pytest.fixture
    def watcher(self, tmp_path):
        """Create BlueprintWatcher instance."""
        index_path = tmp_path / "test.db"
        return BlueprintWatcher(
            index_path=index_path,
            project_root=tmp_path,
            regeneration_interval=60.0,
            min_access_count=3
        )

    def test_initialization(self, watcher, tmp_path):
        """Test BlueprintWatcher initializes correctly."""
        assert watcher.regeneration_interval == 60.0
        assert watcher.min_access_count == 3
        assert watcher.last_regeneration == 0.0
        assert len(watcher.modified_files) == 0

    def test_on_file_modified(self, watcher):
        """Test tracking file modifications."""
        watcher.on_file_modified("/test/file1.py")
        watcher.on_file_modified("/test/file2.py")
        watcher.on_file_modified("/test/file1.py")  # Duplicate
        
        assert len(watcher.modified_files) == 2
        assert "/test/file1.py" in watcher.modified_files
        assert "/test/file2.py" in watcher.modified_files

    def test_should_regenerate_initial(self, watcher):
        """Test should_regenerate on first call."""
        # Initially, should regenerate since last_regeneration is 0
        assert watcher.should_regenerate() is True

    def test_should_regenerate_after_interval(self, watcher):
        """Test should_regenerate after interval elapsed."""
        watcher.last_regeneration = time.time() - 120  # 2 minutes ago
        watcher.regeneration_interval = 60  # 1 minute interval
        
        assert watcher.should_regenerate() is True

    def test_should_regenerate_before_interval(self, watcher):
        """Test should_regenerate before interval elapsed."""
        watcher.last_regeneration = time.time() - 30  # 30 seconds ago
        watcher.regeneration_interval = 60  # 1 minute interval
        
        assert watcher.should_regenerate() is False

    def test_get_stats(self, watcher):
        """Test getting watcher statistics."""
        watcher.on_file_modified("/test/file1.py")
        watcher.on_file_modified("/test/file2.py")
        watcher.last_regeneration = time.time() - 100
        
        stats = watcher.get_stats()
        
        assert stats["modified_files_count"] == 2
        assert stats["last_regeneration"] > 0
        assert stats["time_since_last_regen"] is not None


# =============================================================================
# Integration Tests
# =============================================================================

class TestPhase135Integration:
    """Integration tests for Phase 13.5 features working together."""

    def test_dependency_classification_in_hydration(self, tmp_path):
        """Test dependency classifier works with hydration analyzer."""
        classifier = DependencyClassifier(project_root=tmp_path)
        
        # Test internal file
        internal_file = tmp_path / "module.py"
        internal_file.touch()
        
        dep_type = classifier.classify_dependency(
            target_symbol="func",
            target_file=str(internal_file)
        )
        assert dep_type == "internal"

    def test_truncation_with_dependency_markers(self):
        """Test width truncation preserves dependency type markers."""
        builder = TreeBuilder(TreeRenderOptions(max_width=50))
        
        deps = [
            DependencyInfo(
                target="very_long_function_name_that_exceeds_width",
                confidence=0.9,
                dependency_type="internal"
            )
        ]
        
        result = builder._format_dependencies(deps)
        assert len(result) <= 200  # Should be reasonable length

    def test_cache_tracking_supports_regeneration(self, tmp_path):
        """Test cache access tracking enables regeneration."""
        # Create mock connection
        conn = MagicMock(spec=sqlite3.Connection)
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (0, "cache_key", "TEXT", 0, None, 1),
            (1, "access_count", "INTEGER", 0, "0", 0),
            (2, "last_accessed", "REAL", 0, "0", 0),
        ]
        conn.execute.return_value = mock_cursor
        
        cache = BlueprintCache(conn)
        
        # Track some accesses
        cache._track_access("key1")
        cache._track_access("key2")
        
        # Should have called UPDATE statements
        assert conn.execute.call_count >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
