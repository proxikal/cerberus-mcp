"""
Unit tests for Phase 5: Symbolic Intelligence

Tests method call extraction, symbol resolution, and type tracking.
"""

import pytest
from pathlib import Path

from cerberus.parser.dependencies import extract_method_calls
from cerberus.schemas import MethodCall


class TestPhase51MethodCallExtraction:
    """Test Phase 5.1: Method call extraction with receivers."""

    def test_simple_method_call(self):
        """Test extraction of simple method call like obj.method()."""
        code = "optimizer.step()"
        file_path = Path("/tmp/test.py")

        calls = extract_method_calls(file_path, code)

        assert len(calls) == 1
        assert calls[0].receiver == "optimizer"
        assert calls[0].method == "step"
        assert calls[0].line == 1

    def test_multiple_method_calls(self):
        """Test extraction of multiple method calls in same file."""
        code = """
model.train()
optimizer.step()
model.eval()
"""
        file_path = Path("/tmp/test.py")

        calls = extract_method_calls(file_path, code)

        assert len(calls) == 3
        receivers = [c.receiver for c in calls]
        methods = [c.method for c in calls]

        assert "model" in receivers
        assert "optimizer" in receivers
        assert "train" in methods
        assert "step" in methods
        assert "eval" in methods

    def test_self_method_call(self):
        """Test extraction of self.method() calls."""
        code = """
class MyClass:
    def process(self):
        self.helper()
"""
        file_path = Path("/tmp/test.py")

        calls = extract_method_calls(file_path, code)

        assert len(calls) == 1
        assert calls[0].receiver == "self"
        assert calls[0].method == "helper"

    def test_chained_method_call(self):
        """Test extraction of chained calls like obj.attr.method()."""
        code = "obj.attr.method()"
        file_path = Path("/tmp/test.py")

        calls = extract_method_calls(file_path, code)

        assert len(calls) == 1
        assert calls[0].receiver == "obj.attr"
        assert calls[0].method == "method"

    def test_skip_definition_lines(self):
        """Test that def/class lines are skipped."""
        code = """
def my_function(param):
    pass

class MyClass(Base):
    def method(self):
        pass
"""
        file_path = Path("/tmp/test.py")

        calls = extract_method_calls(file_path, code)

        # Should not extract function/class definitions
        assert len(calls) == 0

    def test_multiple_calls_same_line(self):
        """Test extraction of multiple calls on same line."""
        code = "optimizer.zero_grad(); model.eval()"
        file_path = Path("/tmp/test.py")

        calls = extract_method_calls(file_path, code)

        assert len(calls) == 2
        receivers = {c.receiver for c in calls}
        assert receivers == {"optimizer", "model"}

    def test_method_call_with_arguments(self):
        """Test that method calls with arguments are captured."""
        code = 'model.forward(x, y, z=10)'
        file_path = Path("/tmp/test.py")

        calls = extract_method_calls(file_path, code)

        assert len(calls) == 1
        assert calls[0].receiver == "model"
        assert calls[0].method == "forward"

    def test_nested_method_call(self):
        """Test extraction of nested calls like func(obj.method())."""
        code = "result = transform(model.predict())"
        file_path = Path("/tmp/test.py")

        calls = extract_method_calls(file_path, code)

        assert len(calls) == 1
        assert calls[0].receiver == "model"
        assert calls[0].method == "predict"

    def test_typescript_method_call(self):
        """Test that method calls work for TypeScript/JavaScript."""
        code = """
const result = this.service.getData();
window.addEventListener('click', handler);
"""
        file_path = Path("/tmp/test.ts")

        calls = extract_method_calls(file_path, code)

        assert len(calls) == 2
        receivers = [c.receiver for c in calls]
        assert "this.service" in receivers
        assert "window" in receivers

    def test_method_call_line_numbers(self):
        """Test that line numbers are correct."""
        code = """
# Line 1

optimizer.step()  # Line 4

# Line 6
model.eval()      # Line 7
"""
        file_path = Path("/tmp/test.py")

        calls = extract_method_calls(file_path, code)

        assert len(calls) == 2
        lines = [c.line for c in calls]
        assert 4 in lines
        assert 7 in lines


class TestPhase52ImportResolution:
    """Test Phase 5.2: Import resolution engine."""

    def test_import_resolver_creation(self):
        """Test that ImportResolver can be created."""
        from cerberus.resolution.resolver import ImportResolver
        from cerberus.storage.sqlite_store import SQLiteIndexStore
        import tempfile
        from pathlib import Path

        # Create temporary store
        temp_dir = Path(tempfile.mkdtemp())
        try:
            store = SQLiteIndexStore(temp_dir / "test.db")
            resolver = ImportResolver(store, str(temp_dir))

            assert resolver.store == store
            assert resolver.project_root == temp_dir
            assert isinstance(resolver._symbol_cache, dict)
        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_module_to_path_conversion(self):
        """Test module name to path conversion."""
        from cerberus.resolution.resolver import ImportResolver
        from cerberus.storage.sqlite_store import SQLiteIndexStore
        import tempfile
        from pathlib import Path

        temp_dir = Path(tempfile.mkdtemp())
        try:
            store = SQLiteIndexStore(temp_dir / "test.db")
            resolver = ImportResolver(store, str(temp_dir))

            # Absolute import
            result = resolver._module_to_path("utils", "main.py")
            assert "utils.py" in result

            # Package import
            result = resolver._module_to_path("package.module", "main.py")
            assert "package/module.py" in result

        finally:
            import shutil
            shutil.rmtree(temp_dir)


class TestPhase53TypeTracking:
    """Test Phase 5.3: Type tracking and method resolution."""

    def test_type_tracker_creation(self):
        """Test that TypeTracker can be created."""
        from cerberus.resolution.type_tracker import TypeTracker
        from cerberus.storage.sqlite_store import SQLiteIndexStore
        import tempfile
        from pathlib import Path

        temp_dir = Path(tempfile.mkdtemp())
        try:
            store = SQLiteIndexStore(temp_dir / "test.db")
            tracker = TypeTracker(store)

            assert tracker.store == store
            assert isinstance(tracker._type_map, dict)
            assert isinstance(tracker._symbol_by_name, dict)
        finally:
            import shutil
            shutil.rmtree(temp_dir)

    def test_extract_base_type(self):
        """Test base type extraction from type annotations."""
        from cerberus.resolution.type_tracker import TypeTracker
        from cerberus.storage.sqlite_store import SQLiteIndexStore
        import tempfile
        from pathlib import Path

        temp_dir = Path(tempfile.mkdtemp())
        try:
            store = SQLiteIndexStore(temp_dir / "test.db")
            tracker = TypeTracker(store)

            # Simple types
            assert tracker._extract_base_type("int") == "int"
            assert tracker._extract_base_type("str") == "str"

            # Generic types
            assert tracker._extract_base_type("List[int]") == "List"
            assert tracker._extract_base_type("Dict[str, int]") == "Dict"
            assert tracker._extract_base_type("Optional[MyClass]") == "MyClass"

            # Module paths
            assert tracker._extract_base_type("torch.optim.Adam") == "Adam"

            # Return type annotations
            assert tracker._extract_base_type("-> str") == "str"

        finally:
            import shutil
            shutil.rmtree(temp_dir)
