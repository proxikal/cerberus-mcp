"""
Unit tests for Phase 6: Advanced Context Synthesis.

Tests inheritance resolution, MRO calculation, and context assembly features.
"""

import pytest
import tempfile
from pathlib import Path
from cerberus.storage.sqlite_store import SQLiteIndexStore
from cerberus.resolution import (
    resolve_inheritance,
    compute_class_mro,
    get_class_descendants,
    get_overridden_methods,
)
from cerberus.schemas import CodeSymbol


class TestPhase61InheritanceResolution:
    """Test Phase 6.1: Inheritance Resolution"""

    def test_inheritance_resolver_creation(self):
        """Test that InheritanceResolver can be created."""
        from cerberus.resolution.inheritance_resolver import InheritanceResolver

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SQLiteIndexStore(db_path)
            resolver = InheritanceResolver(store, "/test")
            assert resolver is not None
            assert resolver.store == store
        finally:
            Path(db_path).unlink()

    def test_resolve_inheritance_with_real_file(self, tmp_path):
        """Test resolve_inheritance with actual Python file."""
        # Create a Python file with inheritance
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class Base:
    pass

class Child(Base):
    pass
""")

        # Create store and add file/symbols
        db_path = tmp_path / "test.db"
        store = SQLiteIndexStore(str(db_path))

        # Manually write file
        from cerberus.schemas import FileObject
        store.write_file(FileObject(
            path=str(test_file),
            abs_path=str(test_file),
            size=test_file.stat().st_size,
            last_modified=test_file.stat().st_mtime
        ))

        # Parse and store symbols
        symbols = [
            CodeSymbol(
                name="Base",
                type="class",
                file_path=str(test_file),
                start_line=2,
                end_line=3,
            ),
            CodeSymbol(
                name="Child",
                type="class",
                file_path=str(test_file),
                start_line=5,
                end_line=6,
            ),
        ]
        store.write_symbols_batch(symbols)

        # Test resolve_inheritance
        count = resolve_inheritance(store, str(tmp_path))
        assert isinstance(count, int)
        assert count >= 0


class TestPhase62MROCalculation:
    """Test Phase 6.2: Method Resolution Order Calculation"""

    def test_mro_calculator_creation(self):
        """Test MRO calculator creation."""
        from cerberus.resolution.mro_calculator import MROCalculator

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SQLiteIndexStore(db_path)
            calculator = MROCalculator(store)
            assert calculator is not None
            assert calculator.store == store
        finally:
            Path(db_path).unlink()

    def test_compute_mro_no_inheritance(self):
        """Test MRO for class with no inheritance."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SQLiteIndexStore(db_path)

            # Create file first (required for foreign key)
            from cerberus.schemas import FileObject
            store.write_file(FileObject(
                path="test.py",
                abs_path="/test/test.py",
                size=100,
                last_modified=0.0
            ))

            # Create a simple class with no inheritance
            symbols = [
                CodeSymbol(
                    name="SimpleClass",
                    type="class",
                    file_path="test.py",
                    start_line=1,
                    end_line=10,
                ),
            ]
            store.write_symbols_batch(symbols)

            # Compute MRO
            mro = compute_class_mro(store, "SimpleClass", "test.py")

            # Should have at least the class itself
            assert len(mro) >= 1
            assert mro[0].class_name == "SimpleClass"
            assert mro[0].depth == 0
        finally:
            Path(db_path).unlink()

    def test_descendants_function(self):
        """Test get_class_descendants function."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SQLiteIndexStore(db_path)

            # Create file first
            from cerberus.schemas import FileObject
            store.write_file(FileObject(
                path="test.py",
                abs_path="/test/test.py",
                size=100,
                last_modified=0.0
            ))

            # Create simple hierarchy
            symbols = [
                CodeSymbol(name="Base", type="class", file_path="test.py", start_line=1, end_line=5),
                CodeSymbol(name="Child", type="class", file_path="test.py", start_line=7, end_line=10),
            ]
            store.write_symbols_batch(symbols)

            # Add inheritance reference
            from cerberus.schemas import SymbolReference
            refs = [
                SymbolReference(
                    source_file="test.py",
                    source_line=7,
                    source_symbol="Child",
                    reference_type="inherits",
                    target_file="test.py",
                    target_symbol="Base",
                    target_type="class",
                    confidence=1.0,
                    resolution_method="test"
                )
            ]
            store.write_symbol_references_batch(refs)

            # Get descendants
            descendants = get_class_descendants(store, "Base", "test.py")
            assert isinstance(descendants, list)
            assert "Child" in descendants
        finally:
            Path(db_path).unlink()


class TestPhase63OverrideDetection:
    """Test Phase 6.3: Override Detection"""

    def test_get_overridden_methods(self):
        """Test get_overridden_methods function."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SQLiteIndexStore(db_path)

            # Should not crash with empty store
            overrides = get_overridden_methods(store, "NonExistent", "test.py")
            assert isinstance(overrides, dict)
            assert len(overrides) == 0
        finally:
            Path(db_path).unlink()


class TestPhase64CallGraphBuilder:
    """Test Phase 6.4: Call Graph Builder"""

    def test_call_graph_builder_creation(self):
        """Test CallGraphBuilder creation."""
        from cerberus.resolution.call_graph_builder import CallGraphBuilder

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SQLiteIndexStore(db_path)
            builder = CallGraphBuilder(store)
            assert builder is not None
            assert builder.store == store
        finally:
            Path(db_path).unlink()

    def test_build_call_graph_facade(self):
        """Test build_call_graph facade function."""
        from cerberus.resolution import build_call_graph

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SQLiteIndexStore(db_path)

            # Should not crash with empty database
            graph = build_call_graph(store, "nonexistent", None, "forward", 3)
            assert graph is not None
            assert graph.root_symbol == "nonexistent"
        finally:
            Path(db_path).unlink()


class TestPhase65TypeInference:
    """Test Phase 6.5: Cross-File Type Inference"""

    def test_type_inference_creation(self):
        """Test TypeInference creation."""
        from cerberus.resolution.type_inference import TypeInference

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SQLiteIndexStore(db_path)
            inference = TypeInference(store)
            assert inference is not None
            assert inference.store == store
        finally:
            Path(db_path).unlink()

    def test_infer_type_facade(self):
        """Test infer_type facade function."""
        from cerberus.resolution import infer_type

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SQLiteIndexStore(db_path)

            # Should return None for non-existent symbol
            result = infer_type(store, "unknown", "test.py", 10)
            assert result is None
        finally:
            Path(db_path).unlink()


class TestPhase66ContextAssembler:
    """Test Phase 6.6: Smart Context Assembler"""

    def test_context_assembler_creation(self):
        """Test ContextAssembler creation."""
        from cerberus.resolution.context_assembler import ContextAssembler

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SQLiteIndexStore(db_path)
            assembler = ContextAssembler(store)
            assert assembler is not None
            assert assembler.store == store
        finally:
            Path(db_path).unlink()

    def test_assemble_context_facade(self):
        """Test assemble_context facade function."""
        from cerberus.resolution import assemble_context

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            store = SQLiteIndexStore(db_path)

            # Should return None for non-existent symbol
            result = assemble_context(store, "nonexistent", None, False)
            assert result is None
        finally:
            Path(db_path).unlink()


class TestPhase6Integration:
    """Integration tests for Phase 6 features."""

    def test_phase6_in_index_pipeline(self, tmp_path):
        """Test that Phase 6 runs during indexing."""
        # Create a simple Python file with inheritance
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class Base:
    pass

class Child(Base):
    pass
""")

        # Index the file
        from cerberus.index import build_index

        db_path = tmp_path / "test.db"
        result = build_index(tmp_path, db_path)

        # Check that inheritance references were created
        store = result._store
        conn = store._get_connection()
        try:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM symbol_references
                WHERE reference_type = 'inherits'
            """)
            count = cursor.fetchone()[0]

            # Should have at least one inheritance reference
            assert count >= 1
        finally:
            conn.close()

    def test_resolution_stats_includes_inheritance(self, tmp_path):
        """Test that resolution stats include inheritance counts."""
        # Create test file
        test_file = tmp_path / "stats_test.py"
        test_file.write_text("""
class Parent:
    pass

class Child(Parent):
    pass
""")

        # Index
        from cerberus.index import build_index
        from cerberus.resolution import get_resolution_stats

        db_path = tmp_path / "stats.db"
        result = build_index(tmp_path, db_path)

        # Get stats
        store = result._store
        stats = get_resolution_stats(store)

        assert "inheritance_references" in stats
        assert stats["inheritance_references"] >= 0
