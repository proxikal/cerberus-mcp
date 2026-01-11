"""
Tests for Phase 1: Advanced Dependency Intelligence

Tests recursive call graphs, type resolution, and import linkage.
"""

import pytest
from pathlib import Path

pytestmark = [pytest.mark.fast, pytest.mark.phase1]
from cerberus.graph import build_recursive_call_graph, format_call_graph, get_recursive_callers
from cerberus.parser.type_resolver import (
    extract_python_types,
    extract_typescript_types,
    extract_go_types,
    extract_types_from_file,
    build_type_map,
    resolve_type,
)
from cerberus.parser.dependencies import extract_import_links
from cerberus.schemas import ScanResult, CodeSymbol, CallReference, TypeInfo, ImportLink


class TestRecursiveCallGraph:
    """Test recursive call graph functionality (Phase 1.1)."""

    def test_build_simple_call_graph(self):
        """Test building a simple call graph with direct callers."""
        # Create mock scan result with symbols and calls
        symbols = [
            CodeSymbol(name="target", type="function", file_path="test.py", start_line=1, end_line=3),
            CodeSymbol(name="caller1", type="function", file_path="test.py", start_line=5, end_line=7),
            CodeSymbol(name="caller2", type="function", file_path="test.py", start_line=9, end_line=11),
        ]

        calls = [
            CallReference(caller_file="test.py", callee="target", line=6),
            CallReference(caller_file="test.py", callee="target", line=10),
        ]

        scan_result = ScanResult(
            total_files=1,
            files=[],
            scan_duration=0.0,
            symbols=symbols,
            calls=calls,
        )

        # Build call graph
        graph = build_recursive_call_graph("target", scan_result, max_depth=1)

        assert graph.target_symbol == "target"
        assert graph.max_depth == 1
        assert graph.root_node is not None
        assert graph.root_node.symbol_name == "target"
        assert len(graph.root_node.callers) == 2

    def test_recursive_call_graph_depth(self):
        """Test multi-level recursive call graph."""
        symbols = [
            CodeSymbol(name="level0", type="function", file_path="test.py", start_line=1, end_line=3),
            CodeSymbol(name="level1", type="function", file_path="test.py", start_line=5, end_line=7),
            CodeSymbol(name="level2", type="function", file_path="test.py", start_line=9, end_line=11),
        ]

        calls = [
            CallReference(caller_file="test.py", callee="level0", line=6),  # level1 calls level0
            CallReference(caller_file="test.py", callee="level1", line=10), # level2 calls level1
        ]

        scan_result = ScanResult(
            total_files=1,
            files=[],
            scan_duration=0.0,
            symbols=symbols,
            calls=calls,
        )

        # Build graph with depth 2
        graph = build_recursive_call_graph("level0", scan_result, max_depth=2)

        assert graph.root_node is not None
        assert graph.root_node.symbol_name == "level0"
        assert len(graph.root_node.callers) == 1
        assert graph.root_node.callers[0].symbol_name == "level1"
        assert len(graph.root_node.callers[0].callers) == 1
        assert graph.root_node.callers[0].callers[0].symbol_name == "level2"

    def test_call_graph_missing_symbol(self):
        """Test call graph with non-existent symbol."""
        scan_result = ScanResult(
            total_files=0,
            files=[],
            scan_duration=0.0,
            symbols=[],
            calls=[],
        )

        graph = build_recursive_call_graph("nonexistent", scan_result, max_depth=1)

        assert graph.root_node is None
        assert graph.total_nodes == 0

    def test_format_call_graph(self):
        """Test call graph formatting."""
        symbols = [
            CodeSymbol(name="main", type="function", file_path="test.py", start_line=1, end_line=3),
            CodeSymbol(name="helper", type="function", file_path="test.py", start_line=5, end_line=7),
        ]

        calls = [
            CallReference(caller_file="test.py", callee="main", line=6),
        ]

        scan_result = ScanResult(
            total_files=1,
            files=[],
            scan_duration=0.0,
            symbols=symbols,
            calls=calls,
        )

        graph = build_recursive_call_graph("main", scan_result, max_depth=1)
        formatted = format_call_graph(graph)

        assert "main" in formatted
        assert "helper" in formatted
        assert "test.py" in formatted

    def test_get_recursive_callers(self):
        """Test flattening call graph to caller list."""
        symbols = [
            CodeSymbol(name="target", type="function", file_path="test.py", start_line=1, end_line=3),
            CodeSymbol(name="caller1", type="function", file_path="test.py", start_line=5, end_line=7),
            CodeSymbol(name="caller2", type="function", file_path="test.py", start_line=9, end_line=11),
        ]

        calls = [
            CallReference(caller_file="test.py", callee="target", line=6),
            CallReference(caller_file="test.py", callee="target", line=10),
        ]

        scan_result = ScanResult(
            total_files=1,
            files=[],
            scan_duration=0.0,
            symbols=symbols,
            calls=calls,
        )

        callers = get_recursive_callers("target", scan_result, depth=1)

        assert len(callers) >= 1  # At least the target itself
        caller_names = [c.symbol_name for c in callers]
        assert "target" in caller_names


class TestTypeResolution:
    """Test type resolution and extraction (Phase 1.2)."""

    def test_extract_python_function_return_type(self):
        """Test extracting Python function return types."""
        content = """
def calculate(x: int, y: int) -> int:
    return x + y

def get_name() -> str:
    return "Alice"
"""
        file_path = Path("test.py")
        types = extract_python_types(file_path, content)

        assert len(types) >= 2
        type_names = [t.name for t in types]
        assert "calculate" in type_names
        assert "get_name" in type_names

        calc_type = next(t for t in types if t.name == "calculate")
        assert calc_type.type_annotation == "int"

    def test_extract_python_variable_annotations(self):
        """Test extracting Python variable type annotations."""
        content = """
name: str = "Alice"
age: int = 30
data: List[str] = []
"""
        file_path = Path("test.py")
        types = extract_python_types(file_path, content)

        assert len(types) >= 3
        type_map = {t.name: t.type_annotation for t in types}
        assert type_map.get("name") == "str"
        assert type_map.get("age") == "int"

    def test_extract_python_class_instantiation(self):
        """Test inferring types from class instantiation."""
        content = """
service = AuthService()
handler = RequestHandler(config)
"""
        file_path = Path("test.py")
        types = extract_python_types(file_path, content)

        assert len(types) >= 2
        type_map = {t.name: t.inferred_type for t in types}
        assert type_map.get("service") == "AuthService"
        assert type_map.get("handler") == "RequestHandler"

    def test_extract_typescript_types(self):
        """Test extracting TypeScript type information."""
        content = """
function process(x: number): string {
    return String(x);
}

const name: string = "Alice";
const user = new UserService();
"""
        file_path = Path("test.ts")
        types = extract_typescript_types(file_path, content)

        assert len(types) >= 3
        type_names = [t.name for t in types]
        assert "process" in type_names
        assert "name" in type_names
        assert "user" in type_names

    def test_extract_go_types(self):
        """Test extracting Go type information."""
        content = """
func Calculate(a int, b int) int {
    return a + b
}

var name string
var count int
"""
        file_path = Path("test.go")
        types = extract_go_types(file_path, content)

        assert len(types) >= 3
        type_names = [t.name for t in types]
        assert "Calculate" in type_names
        assert "name" in type_names

    def test_extract_types_from_file_router(self):
        """Test file extension router for type extraction."""
        py_content = "def foo() -> int:\n    return 42"
        ts_content = "function bar(): string { return 'hello'; }"
        go_content = "func baz() int { return 1 }"

        py_types = extract_types_from_file(Path("test.py"), py_content)
        ts_types = extract_types_from_file(Path("test.ts"), ts_content)
        go_types = extract_types_from_file(Path("test.go"), go_content)

        assert len(py_types) > 0
        assert len(ts_types) > 0
        assert len(go_types) > 0

    def test_build_type_map(self):
        """Test building type map from TypeInfo list."""
        types = [
            TypeInfo(name="foo", type_annotation="int", file_path="a.py", line=1),
            TypeInfo(name="bar", type_annotation="str", file_path="a.py", line=2),
            TypeInfo(name="foo", type_annotation="float", file_path="b.py", line=1),
        ]

        type_map = build_type_map(types)

        assert "foo" in type_map
        assert "bar" in type_map
        assert len(type_map["foo"]) == 2  # foo appears in two files
        assert len(type_map["bar"]) == 1

    def test_resolve_type(self):
        """Test type resolution from type map."""
        types = [
            TypeInfo(name="user", type_annotation="User", file_path="app.py", line=1),
            TypeInfo(name="config", inferred_type="Config", file_path="app.py", line=2),
        ]

        type_map = build_type_map(types)

        user_type = resolve_type("user", "app.py", type_map)
        config_type = resolve_type("config", "app.py", type_map)

        assert user_type == "User"
        assert config_type == "Config"


class TestImportLinkage:
    """Test import linkage enhancement (Phase 1.3)."""

    def test_extract_python_from_imports(self):
        """Test extracting Python 'from X import Y' statements."""
        content = """
from typing import List, Dict
from collections import defaultdict
import os
"""
        file_path = Path("test.py")
        links = extract_import_links(file_path, content)

        assert len(links) >= 2

        # Check 'from typing import List, Dict'
        typing_link = next((l for l in links if l.imported_module == "typing"), None)
        assert typing_link is not None
        assert "List" in typing_link.imported_symbols
        assert "Dict" in typing_link.imported_symbols

    def test_extract_typescript_named_imports(self):
        """Test extracting TypeScript named imports."""
        content = """
import { Component, useState } from 'react';
import path from 'path';
"""
        file_path = Path("test.ts")
        links = extract_import_links(file_path, content)

        assert len(links) >= 2

        # Check named import
        react_link = next((l for l in links if l.imported_module == "react"), None)
        assert react_link is not None
        assert "Component" in react_link.imported_symbols
        assert "useState" in react_link.imported_symbols

        # Check default import
        path_link = next((l for l in links if l.imported_module == "path"), None)
        assert path_link is not None
        assert "path" in path_link.imported_symbols

    def test_extract_go_imports(self):
        """Test extracting Go import statements."""
        content = """
import "fmt"
import alias "some/package"
"""
        file_path = Path("test.go")
        links = extract_import_links(file_path, content)

        assert len(links) >= 2

        # Check simple import
        fmt_link = next((l for l in links if l.imported_module == "fmt"), None)
        assert fmt_link is not None

        # Check aliased import
        alias_link = next((l for l in links if "alias" in l.imported_symbols), None)
        assert alias_link is not None

    def test_import_link_schema(self):
        """Test ImportLink schema validation."""
        link = ImportLink(
            importer_file="app.py",
            imported_module="utils",
            imported_symbols=["helper", "Config"],
            import_line=5,
            definition_file="utils.py",
            definition_symbol="helper",
        )

        assert link.importer_file == "app.py"
        assert link.imported_module == "utils"
        assert len(link.imported_symbols) == 2
        assert link.import_line == 5
        assert link.definition_file == "utils.py"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
