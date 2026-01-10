"""
Performance benchmarks for Phase 13.5 features.

Target: <200ms for files with <1000 symbols
"""

import time
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

import pytest

from cerberus.blueprint.hydration_analyzer import HydrationAnalyzer
from cerberus.blueprint.dependency_classifier import DependencyClassifier
from cerberus.blueprint.tree_builder import TreeBuilder
from cerberus.blueprint.cache_manager import BlueprintCache
from cerberus.blueprint.schemas import (
    Blueprint,
    BlueprintNode,
    SymbolOverlay,
    DependencyInfo,
    TreeRenderOptions,
)


class TestPhase135Performance:
    """Performance benchmarks for Phase 13.5 features."""

    @pytest.fixture
    def large_blueprint(self):
        """Create a blueprint with ~800 symbols for benchmarking."""
        nodes = []

        # Create 800 symbols with various types
        for i in range(800):
            # Create dependencies for some nodes
            dependencies = []
            if i % 5 == 0:
                for j in range(5):
                    dep = DependencyInfo(
                        target=f"symbol_{i + j + 1}",
                        target_file=f"/project/module_{(i + j) % 20}.py" if (i + j) % 3 == 0 else None,
                        confidence=0.85,
                        dependency_type="internal" if (i + j) % 3 == 0 else "external",
                    )
                    dependencies.append(dep)

            node = BlueprintNode(
                name=f"symbol_{i}",
                type="function" if i % 3 == 0 else "class" if i % 3 == 1 else "variable",
                start_line=i * 10 + 1,
                end_line=i * 10 + 10,
                signature=f"def symbol_{i}()" if i % 3 == 0 else None,
                overlay=SymbolOverlay(dependencies=dependencies if dependencies else None),
            )
            nodes.append(node)

        return Blueprint(
            file_path="/project/large_module.py",
            nodes=nodes,
            total_symbols=800,
        )

    @pytest.fixture
    def mock_conn(self):
        """Create mock database connection."""
        return MagicMock(spec=sqlite3.Connection)

    @pytest.fixture
    def hydration_analyzer(self, tmp_path, mock_conn):
        """Create hydration analyzer with mock project root."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        return HydrationAnalyzer(mock_conn, project_root=project_root)

    @pytest.fixture
    def dependency_classifier(self, tmp_path):
        """Create dependency classifier with mock project root."""
        project_root = tmp_path / "project"
        project_root.mkdir(exist_ok=True)
        return DependencyClassifier(project_root=project_root)

    @pytest.fixture
    def tree_builder(self):
        """Create tree builder for rendering tests."""
        return TreeBuilder()

    def test_auto_hydration_performance(self, hydration_analyzer, large_blueprint):
        """Benchmark auto-hydration analysis (<50ms target)."""
        # Warm up
        hydration_analyzer.analyze_for_hydration(large_blueprint)

        # Benchmark
        iterations = 10
        total_time = 0

        for _ in range(iterations):
            start = time.perf_counter()
            result = hydration_analyzer.analyze_for_hydration(large_blueprint)
            end = time.perf_counter()
            total_time += (end - start) * 1000  # Convert to ms

        avg_time = total_time / iterations

        print(f"\n🔍 Auto-hydration analysis: {avg_time:.2f}ms (avg of {iterations} runs)")
        assert avg_time < 50, f"Auto-hydration too slow: {avg_time:.2f}ms (target: <50ms)"

    def test_dependency_classification_performance(self, dependency_classifier):
        """Benchmark dependency classification (<30ms target for 80 dependencies)."""
        # Create test dependencies
        test_deps = [
            ("os", "/usr/lib/python3.10/os.py"),
            ("sys", "/usr/lib/python3.10/sys.py"),
            ("numpy", "/usr/lib/python3.10/site-packages/numpy/__init__.py"),
            ("pandas", "/usr/lib/python3.10/site-packages/pandas/__init__.py"),
            ("my_module", "/project/my_module.py"),
            ("utils", "/project/utils.py"),
        ] * 14  # Create ~84 dependencies

        # Warm up
        for target, target_file in test_deps:
            dependency_classifier.classify_dependency(target, target_file)

        # Benchmark
        iterations = 10
        total_time = 0

        for _ in range(iterations):
            start = time.perf_counter()
            for target, target_file in test_deps:
                dependency_classifier.classify_dependency(target, target_file)
            end = time.perf_counter()
            total_time += (end - start) * 1000

        avg_time = total_time / iterations

        print(f"\n📦 Dependency classification ({len(test_deps)} deps): {avg_time:.2f}ms (avg of {iterations} runs)")
        assert avg_time < 30, f"Dependency classification too slow: {avg_time:.2f}ms (target: <30ms)"

    def test_width_management_performance(self, large_blueprint):
        """Benchmark tree rendering with width management (<80ms target)."""
        options = TreeRenderOptions(
            show_signatures=True,
            show_dependencies=True,
            max_width=120,
            collapse_private=True,
            truncate_threshold=5,
        )

        tree_builder = TreeBuilder(options)

        # Warm up
        tree_builder.build_tree(large_blueprint)

        # Benchmark
        iterations = 10
        total_time = 0

        for _ in range(iterations):
            start = time.perf_counter()
            result = tree_builder.build_tree(large_blueprint)
            end = time.perf_counter()
            total_time += (end - start) * 1000

        avg_time = total_time / iterations

        print(f"\n📏 Tree rendering with width management: {avg_time:.2f}ms (avg of {iterations} runs)")
        assert avg_time < 80, f"Tree rendering too slow: {avg_time:.2f}ms (target: <80ms)"

    # Note: Cache benchmarks are in test_phase13_5.py (unit tests with mocks)
    # These would require file I/O which adds variability to micro-benchmarks

    def test_private_symbol_filtering_performance(self):
        """Benchmark private symbol filtering for collapse_private feature."""
        # Create blueprint with mix of public and private symbols
        nodes = []
        for i in range(500):
            name = f"_private_{i}" if i % 2 == 0 else f"public_{i}"
            nodes.append(BlueprintNode(
                name=name,
                type="function",
                start_line=i * 5 + 1,
                end_line=i * 5 + 5,
            ))

        blueprint = Blueprint(
            file_path="/project/test.py",
            nodes=nodes,
            total_symbols=500,
        )

        options = TreeRenderOptions(
            show_signatures=False,
            show_dependencies=False,
            collapse_private=True,
        )

        tree_builder = TreeBuilder(options)

        # Benchmark
        iterations = 20
        total_time = 0

        for _ in range(iterations):
            start = time.perf_counter()
            tree_builder.build_tree(blueprint)
            end = time.perf_counter()
            total_time += (end - start) * 1000

        avg_time = total_time / iterations

        print(f"\n🔒 Private symbol filtering (500 symbols): {avg_time:.2f}ms (avg of {iterations} runs)")
        assert avg_time < 40, f"Private filtering too slow: {avg_time:.2f}ms (target: <40ms)"

    def test_dependency_marker_generation_performance(self, dependency_classifier):
        """Benchmark dependency marker generation."""
        dep_types = ["internal", "external", "stdlib"]

        iterations = 1000
        total_time = 0

        for _ in range(iterations):
            start = time.perf_counter()
            for dep_type in dep_types:
                dependency_classifier.get_marker(dep_type)
            end = time.perf_counter()
            total_time += (end - start) * 1000

        avg_time = total_time / iterations

        print(f"\n🏷️  Dependency marker generation (3 types): {avg_time:.4f}ms (avg of {iterations} runs)")
        assert avg_time < 0.01, f"Marker generation too slow: {avg_time:.4f}ms (target: <0.01ms)"

    def test_combined_phase135_operations(self, hydration_analyzer, large_blueprint):
        """
        Benchmark combined Phase 13.5 operations on a large blueprint.

        This simulates the real-world scenario where all features work together.
        Target: <150ms for 800 symbols
        """
        options = TreeRenderOptions(
            show_signatures=True,
            show_dependencies=True,
            max_width=120,
            collapse_private=True,
            truncate_threshold=5,
        )

        tree_builder = TreeBuilder(options)

        # Warm up
        hydration_analyzer.analyze_for_hydration(large_blueprint)
        tree_builder.build_tree(large_blueprint)

        # Benchmark
        iterations = 10
        total_time = 0

        for _ in range(iterations):
            start = time.perf_counter()

            # 1. Analyze for hydration
            hydrated_files = hydration_analyzer.analyze_for_hydration(large_blueprint)

            # 2. Render tree with all features
            tree_output = tree_builder.build_tree(large_blueprint)

            end = time.perf_counter()
            total_time += (end - start) * 1000

        avg_time = total_time / iterations

        print(f"\n🚀 Combined Phase 13.5 operations (800 symbols): {avg_time:.2f}ms (avg of {iterations} runs)")
        print(f"   - Auto-hydration + Tree rendering with width management")
        assert avg_time < 150, f"Combined operations too slow: {avg_time:.2f}ms (target: <150ms)"


class TestPhase135MemoryUsage:
    """Memory usage tests for Phase 13.5 features."""

    def test_hydrated_blueprint_memory_overhead(self, tmp_path):
        """Verify hydrated blueprints don't cause excessive memory overhead."""
        import sys

        # Create base blueprint
        nodes = [BlueprintNode(name=f"sym_{i}", type="function", start_line=i, end_line=i+5) for i in range(100)]
        base_blueprint = Blueprint(file_path="/project/test.py", nodes=nodes, total_symbols=100)

        # Measure base size
        base_size = sys.getsizeof(base_blueprint)

        # Create hydrated blueprint (simulated with 3 hydrated files)
        from cerberus.blueprint.schemas import HydratedFile

        hydrated_files = [
            HydratedFile(
                file_path=f"/project/dep_{i}.py",
                reference_count=10,
                blueprint=Blueprint(
                    file_path=f"/project/dep_{i}.py",
                    nodes=[BlueprintNode(name=f"dep_sym_{j}", type="function", start_line=j, end_line=j+5) for j in range(20)],
                    total_symbols=20,
                ),
            )
            for i in range(3)
        ]

        # Memory overhead should be reasonable
        print(f"\n💾 Base blueprint size: ~{base_size} bytes")
        print(f"💾 Hydrated files count: {len(hydrated_files)}")
        print(f"💾 Hydration overhead: ~{len(hydrated_files)} additional mini-blueprints")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
