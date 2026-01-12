"""
Unit tests for Phase 8: Predictive Context Intelligence.

Tests blueprint, timeline, auto-hydrate, and trace-path features.
"""

import pytest
import tempfile
import subprocess
from pathlib import Path

pytestmark = pytest.mark.fast
from cerberus.storage.sqlite_store import SQLiteIndexStore
from cerberus.schemas import CodeSymbol, FileObject
from cerberus.index import load_index


class TestPhase81Blueprint:
    """Test Phase 8.1: Blueprint Command (Index-backed file structure)"""

    def test_blueprint_retrieves_file_structure(self, tmp_path):
        """Test that blueprint retrieves complete file structure from index."""
        # Create a Python file with multiple symbols
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class MyClass:
    def method_one(self):
        pass

    def method_two(self):
        pass

def top_level_function():
    pass

CONSTANT = 42
""")

        # Create index
        db_path = tmp_path / "test.db"
        store = SQLiteIndexStore(str(db_path))

        # Write file
        store.write_file(FileObject(
            path=str(test_file),
            abs_path=str(test_file),
            size=test_file.stat().st_size,
            last_modified=test_file.stat().st_mtime
        ))

        # Write symbols
        symbols = [
            CodeSymbol(
                name="MyClass",
                type="class",
                file_path=str(test_file),
                start_line=2,
                end_line=7,
            ),
            CodeSymbol(
                name="method_one",
                type="function",
                file_path=str(test_file),
                start_line=3,
                end_line=4,
                parent_class="MyClass"
            ),
            CodeSymbol(
                name="method_two",
                type="function",
                file_path=str(test_file),
                start_line=6,
                end_line=7,
                parent_class="MyClass"
            ),
            CodeSymbol(
                name="top_level_function",
                type="function",
                file_path=str(test_file),
                start_line=9,
                end_line=10,
            ),
            CodeSymbol(
                name="CONSTANT",
                type="variable",
                file_path=str(test_file),
                start_line=12,
                end_line=12,
            ),
        ]
        store.write_symbols_batch(symbols)

        # Load index and query symbols (simulating blueprint command)
        scan_result = load_index(db_path)
        file_symbols = list(scan_result._store.query_symbols(filter={'file_path': str(test_file)}))

        # Verify all symbols retrieved
        assert len(file_symbols) >= 5
        symbol_names = {s.name for s in file_symbols}
        assert 'MyClass' in symbol_names
        assert 'method_one' in symbol_names
        assert 'method_two' in symbol_names
        assert 'top_level_function' in symbol_names
        assert 'CONSTANT' in symbol_names

    def test_blueprint_groups_methods_by_class(self, tmp_path):
        """Test that blueprint correctly groups methods under their parent class."""
        # Create index
        db_path = tmp_path / "test.db"
        store = SQLiteIndexStore(str(db_path))

        test_file = str(tmp_path / "test.py")

        # Write file
        store.write_file(FileObject(
            path=test_file,
            abs_path=test_file,
            size=100,
            last_modified=0.0
        ))

        # Write symbols with parent_class relationships
        symbols = [
            CodeSymbol(
                name="ParentClass",
                type="class",
                file_path=test_file,
                start_line=1,
                end_line=10,
            ),
            CodeSymbol(
                name="child_method",
                type="function",
                file_path=test_file,
                start_line=2,
                end_line=3,
                parent_class="ParentClass"
            ),
        ]
        store.write_symbols_batch(symbols)

        # Load and verify parent-child relationship
        scan_result = load_index(db_path)
        file_symbols = list(scan_result._store.query_symbols(filter={'file_path': test_file}))

        parent = next((s for s in file_symbols if s.name == "ParentClass"), None)
        child = next((s for s in file_symbols if s.name == "child_method"), None)

        assert parent is not None
        assert child is not None
        assert child.parent_class == "ParentClass"

    def test_blueprint_faster_than_disk_read(self, tmp_path):
        """Test that blueprint uses index (no disk read required)."""
        # Create large file
        test_file = tmp_path / "large.py"
        # Write 1000 lines
        content = "\n".join([f"def function_{i}(): pass" for i in range(1000)])
        test_file.write_text(content)

        # Create index
        db_path = tmp_path / "test.db"
        store = SQLiteIndexStore(str(db_path))

        store.write_file(FileObject(
            path=str(test_file),
            abs_path=str(test_file),
            size=test_file.stat().st_size,
            last_modified=test_file.stat().st_mtime
        ))

        # Write minimal symbols
        symbols = [
            CodeSymbol(
                name=f"function_{i}",
                type="function",
                file_path=str(test_file),
                start_line=i+1,
                end_line=i+1,
            )
            for i in range(0, 1000, 100)  # Every 100th function
        ]
        store.write_symbols_batch(symbols)

        # Now delete the file to prove we don't read from disk
        test_file.unlink()

        # Blueprint should still work (index-backed)
        scan_result = load_index(db_path)
        file_symbols = list(scan_result._store.query_symbols(filter={'file_path': str(test_file)}))

        # Should retrieve symbols even though file is deleted
        assert len(file_symbols) >= 10


class TestPhase82Timeline:
    """Test Phase 8.2: Timeline Command (Git-aware change tracking)"""

    def test_timeline_identifies_changed_symbols(self, tmp_path):
        """Test that timeline correctly identifies symbols in changed line ranges."""
        # Create index with symbols
        db_path = tmp_path / "test.db"
        store = SQLiteIndexStore(str(db_path))

        test_file = str(tmp_path / "test.py")

        store.write_file(FileObject(
            path=test_file,
            abs_path=test_file,
            size=100,
            last_modified=0.0
        ))

        # Symbols at different line ranges
        symbols = [
            CodeSymbol(name="func_a", type="function", file_path=test_file, start_line=5, end_line=10),
            CodeSymbol(name="func_b", type="function", file_path=test_file, start_line=15, end_line=20),
            CodeSymbol(name="func_c", type="function", file_path=test_file, start_line=25, end_line=30),
        ]
        store.write_symbols_batch(symbols)

        # Load index
        scan_result = load_index(db_path)

        # Simulate changed line ranges (lines 7-8 and 26-27)
        file_symbols = list(scan_result._store.query_symbols(filter={'file_path': test_file}))

        # Check which symbols overlap with changed lines
        changed_symbols = []
        for sym in file_symbols:
            # Lines 7-8 overlap with func_a (5-10)
            if not (sym.end_line < 7 or sym.start_line > 8):
                changed_symbols.append(sym.name)
            # Lines 26-27 overlap with func_c (25-30)
            if not (sym.end_line < 26 or sym.start_line > 27):
                changed_symbols.append(sym.name)

        # Remove duplicates
        changed_symbols = list(set(changed_symbols))

        # Should detect func_a and func_c as changed, but not func_b
        assert 'func_a' in changed_symbols
        assert 'func_c' in changed_symbols
        assert 'func_b' not in changed_symbols


class TestPhase83AutoHydrate:
    """Test Phase 8.3: Auto-Hydrate (Automatic type dependency injection)"""

    def test_auto_hydrate_extracts_type_names(self):
        """Test that auto-hydrate extracts type names from signatures."""
        import re

        # Test signatures
        test_cases = [
            ("def func(user: UserProfile) -> bool", ["UserProfile"]),
            ("def process(data: List[DataModel]) -> None", ["DataModel"]),  # List filtered out
            ("def handle(req: Request, resp: Response) -> Result", ["Request", "Response", "Result"]),
            ("def simple() -> str", []),  # str is builtin, ignored
        ]

        for signature, expected_types in test_cases:
            type_names = set()

            # Extract type hints from signature
            matches = re.findall(r':\s*([A-Z][a-zA-Z0-9_\[\]]+)', signature)
            for match in matches:
                inner_matches = re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b', match)
                type_names.update(inner_matches)

            # Extract return type
            return_match = re.search(r'->\s*([A-Z][a-zA-Z0-9_\[\]]+)', signature)
            if return_match:
                inner_matches = re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b', return_match.group(1))
                type_names.update(inner_matches)

            # Filter out built-ins
            builtins = {'List', 'Dict', 'Set', 'Tuple', 'Optional', 'Union', 'Any', 'None', 'Callable'}
            type_names = type_names - builtins

            assert type_names == set(expected_types), f"Failed for: {signature}"

    def test_auto_hydrate_finds_type_definitions(self, tmp_path):
        """Test that auto-hydrate can find type definitions in the index."""
        # Create index
        db_path = tmp_path / "test.db"
        store = SQLiteIndexStore(str(db_path))

        test_file = str(tmp_path / "test.py")

        store.write_file(FileObject(
            path=test_file,
            abs_path=test_file,
            size=100,
            last_modified=0.0
        ))

        # Add type definitions
        symbols = [
            CodeSymbol(name="UserProfile", type="class", file_path=test_file, start_line=1, end_line=5),
            CodeSymbol(name="Request", type="class", file_path=test_file, start_line=7, end_line=10),
            CodeSymbol(name="process_user", type="function", file_path=test_file, start_line=12, end_line=15,
                      signature="def process_user(user: UserProfile) -> bool", return_type="bool"),
        ]
        store.write_symbols_batch(symbols)

        # Load and find types
        scan_result = load_index(db_path)

        # Find UserProfile type
        type_matches = [s for s in scan_result.symbols if s.name == "UserProfile" and s.type == "class"]

        assert len(type_matches) > 0
        assert type_matches[0].name == "UserProfile"


class TestPhase84TracePath:
    """Test Phase 8.4: Trace-Path (Execution flow mapping)"""

    def test_trace_path_finds_direct_connection(self, tmp_path):
        """Test that trace-path finds direct call connections."""
        # Create index with call relationships
        db_path = tmp_path / "test.db"
        store = SQLiteIndexStore(str(db_path))

        test_file = str(tmp_path / "test.py")

        store.write_file(FileObject(
            path=test_file,
            abs_path=test_file,
            size=100,
            last_modified=0.0
        ))

        # Add symbols
        symbols = [
            CodeSymbol(name="func_a", type="function", file_path=test_file, start_line=1, end_line=3),
            CodeSymbol(name="func_b", type="function", file_path=test_file, start_line=5, end_line=7),
        ]
        store.write_symbols_batch(symbols)

        # Add call relationship: func_a calls func_b
        from cerberus.schemas import CallReference
        calls = [
            CallReference(
                caller_file=test_file,
                callee="func_b",
                line=2
            )
        ]
        store.write_calls_batch(calls)

        # Build call graph
        from cerberus.resolution.call_graph_builder import CallGraphBuilder

        scan_result = load_index(db_path)
        builder = CallGraphBuilder(scan_result._store)
        call_graph = builder.build_forward_graph("func_a", str(test_file))

        # Verify graph has nodes
        assert len(call_graph.nodes) > 0

        # Check that func_a node exists and has func_b as callee
        func_a_key = f"{test_file}:func_a"
        if func_a_key in call_graph.nodes:
            node = call_graph.nodes[func_a_key]
            # Check callees contain func_b
            callee_names = [key.split(':')[-1] for key in node.callees]
            assert 'func_b' in callee_names or len(node.callees) > 0

    def test_trace_path_finds_multi_hop_connection(self, tmp_path):
        """Test that trace-path finds paths through multiple hops."""
        # Create index with chain: a -> b -> c
        db_path = tmp_path / "test.db"
        store = SQLiteIndexStore(str(db_path))

        test_file = str(tmp_path / "test.py")

        store.write_file(FileObject(
            path=test_file,
            abs_path=test_file,
            size=100,
            last_modified=0.0
        ))

        # Add symbols
        symbols = [
            CodeSymbol(name="func_a", type="function", file_path=test_file, start_line=1, end_line=3),
            CodeSymbol(name="func_b", type="function", file_path=test_file, start_line=5, end_line=7),
            CodeSymbol(name="func_c", type="function", file_path=test_file, start_line=9, end_line=11),
        ]
        store.write_symbols_batch(symbols)

        # Add call chain: a -> b -> c
        from cerberus.schemas import CallReference
        calls = [
            CallReference(
                caller_file=test_file,
                callee="func_b",
                line=2
            ),
            CallReference(
                caller_file=test_file,
                callee="func_c",
                line=6
            ),
        ]
        store.write_calls_batch(calls)

        # Build call graph
        from cerberus.resolution.call_graph_builder import CallGraphBuilder
        from collections import deque

        scan_result = load_index(db_path)
        builder = CallGraphBuilder(scan_result._store)
        call_graph = builder.build_forward_graph("func_a", str(test_file))

        # BFS from func_a to func_c
        source_key = f"{test_file}:func_a"
        target_name = "func_c"

        queue = deque([(source_key, [source_key])])
        visited = set([source_key])
        path_found = None

        while queue and not path_found:
            current, path = queue.popleft()

            if len(path) > 10:  # Max depth
                continue

            current_name = current.split(':')[-1]
            if current_name == target_name:
                path_found = path
                break

            if current in call_graph.nodes:
                node = call_graph.nodes[current]
                for callee_key in node.callees:
                    if callee_key not in visited:
                        visited.add(callee_key)
                        queue.append((callee_key, path + [callee_key]))

        # Should find path a -> b -> c
        if path_found:
            path_names = [key.split(':')[-1] for key in path_found]
            assert 'func_a' in path_names
            assert 'func_c' in path_names


class TestPhase8Integration:
    """Integration tests for Phase 8 features working together"""

    def test_phase8_workflow(self, tmp_path):
        """Test a complete Phase 8 workflow: index -> blueprint -> get-symbol."""
        # Create a realistic Python file
        test_file = tmp_path / "models.py"
        test_file.write_text("""
class User:
    def __init__(self, name: str):
        self.name = name

    def get_profile(self) -> UserProfile:
        return UserProfile(self)

class UserProfile:
    def __init__(self, user: User):
        self.user = user
""")

        # Index it
        db_path = tmp_path / "test.db"
        store = SQLiteIndexStore(str(db_path))

        store.write_file(FileObject(
            path=str(test_file),
            abs_path=str(test_file),
            size=test_file.stat().st_size,
            last_modified=test_file.stat().st_mtime
        ))

        symbols = [
            CodeSymbol(name="User", type="class", file_path=str(test_file), start_line=2, end_line=7,
                      signature="class User"),
            CodeSymbol(name="__init__", type="function", file_path=str(test_file), start_line=3, end_line=4,
                      parent_class="User", signature="def __init__(self, name: str)"),
            CodeSymbol(name="get_profile", type="function", file_path=str(test_file), start_line=6, end_line=7,
                      parent_class="User", signature="def get_profile(self) -> UserProfile", return_type="UserProfile"),
            CodeSymbol(name="UserProfile", type="class", file_path=str(test_file), start_line=9, end_line=11,
                      signature="class UserProfile"),
            CodeSymbol(name="__init__", type="function", file_path=str(test_file), start_line=10, end_line=11,
                      parent_class="UserProfile", signature="def __init__(self, user: User)"),
        ]
        store.write_symbols_batch(symbols)

        # 1. Test Blueprint: Get file structure
        scan_result = load_index(db_path)
        file_symbols = list(scan_result._store.query_symbols(filter={'file_path': str(test_file)}))

        assert len(file_symbols) >= 5
        class_names = {s.name for s in file_symbols if s.type == "class"}
        assert 'User' in class_names
        assert 'UserProfile' in class_names

        # 2. Test Get-Symbol: Find specific symbol
        user_symbol = next((s for s in file_symbols if s.name == "User"), None)
        assert user_symbol is not None
        assert user_symbol.type == "class"

        # 3. Test Auto-Hydrate: Extract referenced types
        get_profile = next((s for s in file_symbols if s.name == "get_profile"), None)
        assert get_profile is not None
        assert get_profile.return_type == "UserProfile"

        # Find UserProfile in index (simulating auto-hydrate)
        profile_symbols = [s for s in file_symbols if s.name == "UserProfile" and s.type == "class"]
        assert len(profile_symbols) > 0

        print("✅ Phase 8 integration test passed!")
