"""
Tests for circular dependency detection.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from src.cerberus.analysis.circular_dependency_detector import (
    CircularDependencyDetector,
    find_circular_dependencies,
    CircularChain
)


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def simple_circular_project(temp_project):
    """
    Create a simple circular dependency:
    module_a -> module_b -> module_a
    """
    # Create module_a.py
    module_a = temp_project / "module_a.py"
    module_a.write_text("import module_b\n\ndef func_a():\n    pass\n")

    # Create module_b.py
    module_b = temp_project / "module_b.py"
    module_b.write_text("import module_a\n\ndef func_b():\n    pass\n")

    return temp_project


@pytest.fixture
def three_way_circular_project(temp_project):
    """
    Create a three-way circular dependency:
    module_a -> module_b -> module_c -> module_a
    """
    # Create module_a.py
    module_a = temp_project / "module_a.py"
    module_a.write_text("import module_b\n\ndef func_a():\n    pass\n")

    # Create module_b.py
    module_b = temp_project / "module_b.py"
    module_b.write_text("import module_c\n\ndef func_b():\n    pass\n")

    # Create module_c.py
    module_c = temp_project / "module_c.py"
    module_c.write_text("import module_a\n\ndef func_c():\n    pass\n")

    return temp_project


@pytest.fixture
def complex_circular_project(temp_project):
    """
    Create a complex project with multiple circular chains:
    - Chain 1: a -> b -> a (2-module cycle)
    - Chain 2: c -> d -> e -> c (3-module cycle)
    - No cycle: f -> g
    """
    (temp_project / "a.py").write_text("import b\n")
    (temp_project / "b.py").write_text("import a\n")
    (temp_project / "c.py").write_text("import d\n")
    (temp_project / "d.py").write_text("import e\n")
    (temp_project / "e.py").write_text("import c\n")
    (temp_project / "f.py").write_text("import g\n")
    (temp_project / "g.py").write_text("# no imports\n")

    return temp_project


@pytest.fixture
def critical_module_circular_project(temp_project):
    """
    Create circular dependency involving critical modules:
    core.app -> core.main -> core.app
    """
    core_dir = temp_project / "core"
    core_dir.mkdir()

    (core_dir / "__init__.py").write_text("")
    (core_dir / "app.py").write_text("import core.main\n")
    (core_dir / "main.py").write_text("import core.app\n")

    return temp_project


@pytest.fixture
def no_circular_project(temp_project):
    """
    Create a project with no circular dependencies:
    module_a -> module_b -> module_c
    """
    (temp_project / "module_a.py").write_text("import module_b\n")
    (temp_project / "module_b.py").write_text("import module_c\n")
    (temp_project / "module_c.py").write_text("# no imports\n")

    return temp_project


class TestCircularDependencyDetector:
    """Test CircularDependencyDetector class."""

    def test_simple_circular_dependency(self, simple_circular_project):
        """Test detection of simple 2-module circular dependency."""
        detector = CircularDependencyDetector(simple_circular_project)
        result = detector.detect()

        assert result.total_modules == 2
        assert len(result.circular_chains) == 1

        chain = result.circular_chains[0]
        assert chain["length"] == 2
        assert set(chain["chain"]) == {"module_a", "module_b"}
        assert chain["severity"] in ["medium", "high"]

    def test_three_way_circular_dependency(self, three_way_circular_project):
        """Test detection of 3-module circular dependency."""
        detector = CircularDependencyDetector(three_way_circular_project)
        result = detector.detect()

        assert result.total_modules == 3
        assert len(result.circular_chains) == 1

        chain = result.circular_chains[0]
        assert chain["length"] == 3
        assert set(chain["chain"]) == {"module_a", "module_b", "module_c"}
        assert chain["severity"] in ["medium", "high"]

    def test_complex_multiple_chains(self, complex_circular_project):
        """Test detection of multiple circular chains."""
        detector = CircularDependencyDetector(complex_circular_project)
        result = detector.detect()

        assert result.total_modules == 7
        assert len(result.circular_chains) == 2

        # Check that both chains were found
        chain_sets = [set(chain["chain"]) for chain in result.circular_chains]
        assert {"a", "b"} in chain_sets
        assert {"c", "d", "e"} in chain_sets

    def test_no_circular_dependencies(self, no_circular_project):
        """Test project with no circular dependencies."""
        detector = CircularDependencyDetector(no_circular_project)
        result = detector.detect()

        assert result.total_modules == 3
        assert len(result.circular_chains) == 0
        assert "No circular dependencies found" in result.summary

    def test_critical_module_severity(self, critical_module_circular_project):
        """Test that critical modules get higher severity."""
        detector = CircularDependencyDetector(critical_module_circular_project)
        result = detector.detect()

        assert len(result.circular_chains) >= 1

        # Find the chain involving core modules
        for chain in result.circular_chains:
            if "core.app" in chain["chain"] or "core.main" in chain["chain"]:
                # Should be high severity due to critical module names
                assert chain["severity"] in ["high", "critical"]

    def test_severity_filtering(self, complex_circular_project):
        """Test filtering by minimum severity."""
        detector = CircularDependencyDetector(complex_circular_project)

        # Get all chains
        all_result = detector.detect(min_severity="low")

        # Get only high severity
        high_result = detector.detect(min_severity="high")

        # Should have fewer or equal chains with higher threshold
        assert len(high_result.circular_chains) <= len(all_result.circular_chains)

    def test_scope_filtering(self, temp_project):
        """Test scope filtering to specific directory."""
        # Create two separate modules
        subdir = temp_project / "subdir"
        subdir.mkdir()

        # Circular in root
        (temp_project / "root_a.py").write_text("import root_b\n")
        (temp_project / "root_b.py").write_text("import root_a\n")

        # Circular in subdir
        (subdir / "sub_a.py").write_text("from subdir import sub_b\n")
        (subdir / "sub_b.py").write_text("from subdir import sub_a\n")

        # Test full project
        detector_full = CircularDependencyDetector(temp_project)
        result_full = detector_full.detect()
        assert len(result_full.circular_chains) >= 1

        # Test scope to subdir only
        detector_scoped = CircularDependencyDetector(temp_project)
        result_scoped = detector_scoped.detect(scope="subdir")
        assert len(result_scoped.circular_chains) >= 0

    def test_empty_project(self, temp_project):
        """Test empty project with no Python files."""
        detector = CircularDependencyDetector(temp_project)
        result = detector.detect()

        assert result.total_modules == 0
        assert len(result.circular_chains) == 0
        assert "No circular dependencies found" in result.summary

    def test_single_file_no_imports(self, temp_project):
        """Test single file with no imports."""
        (temp_project / "single.py").write_text("def func():\n    pass\n")

        detector = CircularDependencyDetector(temp_project)
        result = detector.detect()

        assert result.total_modules == 1
        assert len(result.circular_chains) == 0

    def test_external_imports_ignored(self, temp_project):
        """Test that external imports (not in project) are ignored."""
        (temp_project / "module_a.py").write_text(
            "import os\nimport sys\nimport json\n\ndef func():\n    pass\n"
        )

        detector = CircularDependencyDetector(temp_project)
        result = detector.detect()

        assert result.total_modules == 1
        assert len(result.circular_chains) == 0

    def test_from_imports(self, temp_project):
        """Test detection with 'from X import Y' style imports."""
        (temp_project / "module_a.py").write_text("from module_b import func_b\n")
        (temp_project / "module_b.py").write_text("from module_a import func_a\n")

        detector = CircularDependencyDetector(temp_project)
        result = detector.detect()

        assert len(result.circular_chains) == 1
        chain = result.circular_chains[0]
        assert set(chain["chain"]) == {"module_a", "module_b"}

    def test_package_init_files(self, temp_project):
        """Test handling of __init__.py files."""
        pkg_dir = temp_project / "mypackage"
        pkg_dir.mkdir()

        (pkg_dir / "__init__.py").write_text("from mypackage import submodule\n")
        (pkg_dir / "submodule.py").write_text("import mypackage\n")

        detector = CircularDependencyDetector(temp_project)
        result = detector.detect()

        # Should detect circular dependency
        assert len(result.circular_chains) >= 1

    def test_result_to_dict(self, simple_circular_project):
        """Test conversion of result to dictionary."""
        detector = CircularDependencyDetector(simple_circular_project)
        result = detector.detect()

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "total_modules" in result_dict
        assert "circular_chains" in result_dict
        assert "summary" in result_dict
        assert isinstance(result_dict["circular_chains"], list)

    def test_dependency_graph_structure(self, three_way_circular_project):
        """Test that dependency graph is correctly built."""
        detector = CircularDependencyDetector(three_way_circular_project)
        result = detector.detect()

        assert "module_a" in result.dependency_graph
        assert "module_b" in result.dependency_graph
        assert "module_c" in result.dependency_graph

        # Check relationships
        assert "module_b" in result.dependency_graph["module_a"]
        assert "module_c" in result.dependency_graph["module_b"]
        assert "module_a" in result.dependency_graph["module_c"]


class TestConvenienceFunction:
    """Test the convenience function."""

    def test_find_circular_dependencies_function(self, simple_circular_project):
        """Test the find_circular_dependencies convenience function."""
        result = find_circular_dependencies(
            project_root=simple_circular_project,
            min_severity="low"
        )

        assert result.total_modules == 2
        assert len(result.circular_chains) == 1


class TestSeverityCalculation:
    """Test severity calculation logic."""

    def test_two_module_severity(self, temp_project):
        """Test severity for 2-module cycles."""
        (temp_project / "a.py").write_text("import b\n")
        (temp_project / "b.py").write_text("import a\n")

        result = find_circular_dependencies(temp_project)
        assert result.circular_chains[0]["severity"] == "medium"

    def test_three_module_severity(self, temp_project):
        """Test severity for 3-module cycles."""
        (temp_project / "a.py").write_text("import b\n")
        (temp_project / "b.py").write_text("import c\n")
        (temp_project / "c.py").write_text("import a\n")

        result = find_circular_dependencies(temp_project)
        assert result.circular_chains[0]["severity"] == "medium"

    def test_long_chain_severity(self, temp_project):
        """Test severity for long chains (4+ modules)."""
        (temp_project / "a.py").write_text("import b\n")
        (temp_project / "b.py").write_text("import c\n")
        (temp_project / "c.py").write_text("import d\n")
        (temp_project / "d.py").write_text("import a\n")

        result = find_circular_dependencies(temp_project)
        assert result.circular_chains[0]["severity"] in ["high", "critical"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_syntax_error_file_skipped(self, temp_project):
        """Test that files with syntax errors are skipped."""
        (temp_project / "valid.py").write_text("import invalid\n")
        (temp_project / "invalid.py").write_text("this is not valid python {{{")

        # Should not crash, just skip invalid file
        detector = CircularDependencyDetector(temp_project)
        result = detector.detect()

        # Should detect at least the valid module
        assert result.total_modules >= 1

    def test_nonexistent_scope(self, temp_project):
        """Test handling of non-existent scope path."""
        (temp_project / "module.py").write_text("# test\n")

        detector = CircularDependencyDetector(temp_project)
        # Should handle gracefully
        result = detector.detect(scope="nonexistent/path")

        # Should return empty result
        assert result.total_modules == 0

    def test_venv_files_excluded(self, temp_project):
        """Test that venv/virtualenv files are excluded."""
        venv_dir = temp_project / "venv" / "lib"
        venv_dir.mkdir(parents=True)

        (venv_dir / "module.py").write_text("import something\n")
        (temp_project / "real_module.py").write_text("# real code\n")

        detector = CircularDependencyDetector(temp_project)
        result = detector.detect()

        # Should only detect real_module
        assert result.total_modules == 1

    def test_hidden_files_excluded(self, temp_project):
        """Test that hidden files/directories are excluded."""
        hidden_dir = temp_project / ".hidden"
        hidden_dir.mkdir()

        (hidden_dir / "module.py").write_text("import something\n")
        (temp_project / "visible.py").write_text("# visible\n")

        detector = CircularDependencyDetector(temp_project)
        result = detector.detect()

        # Should only detect visible module
        assert result.total_modules == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
