"""Tests for Phase 13.5 Section 2: External Dependency Marking."""

import pytest
from pathlib import Path

pytestmark = [pytest.mark.fast, pytest.mark.blueprint]

from cerberus.blueprint.dependency_classifier import DependencyClassifier


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
        assert result in ["external", "stdlib"]

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
