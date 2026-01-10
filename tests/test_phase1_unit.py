#!/usr/bin/env python3
"""
Unit tests for Phase 1 that don't require external dependencies.
Tests pure Python logic without scanning infrastructure.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cerberus.parser.type_resolver import (
    extract_python_types,
    extract_typescript_types,
    extract_go_types,
    build_type_map,
    resolve_type,
)
from cerberus.parser.dependencies import extract_import_links
from cerberus.graph import build_recursive_call_graph, format_call_graph
from cerberus.schemas import (
    CodeSymbol, CallReference, ScanResult, TypeInfo, ImportLink
)


def test_python_type_extraction():
    """Test Python type extraction without dependencies."""
    print("\n" + "=" * 60)
    print("TEST: Python Type Extraction")
    print("=" * 60)

    content = """
from typing import List, Dict, Optional

def calculate(x: int, y: int) -> int:
    return x + y

def get_name() -> str:
    return "Alice"

def process(data: List[str]) -> Dict[str, int]:
    count: int = 0
    result: Dict[str, int] = {}
    service = AuthService()
    handler = RequestHandler(config)
    return result
"""

    file_path = Path("test.py")
    types = extract_python_types(file_path, content)

    print(f"✓ Extracted {len(types)} type annotations")

    # Check function return types
    func_types = [t for t in types if t.name in ["calculate", "get_name", "process"]]
    print(f"✓ Function return types: {len(func_types)}")
    for t in func_types:
        print(f"  - {t.name} -> {t.type_annotation}")

    # Check variable annotations
    var_types = [t for t in types if t.name in ["count", "result"]]
    print(f"✓ Variable annotations: {len(var_types)}")

    # Check inferred types from instantiation
    inferred = [t for t in types if t.inferred_type]
    print(f"✓ Inferred types (instantiation): {len(inferred)}")
    for t in inferred:
        print(f"  - {t.name} = {t.inferred_type}()")

    assert len(types) >= 7, f"Expected at least 7 types, got {len(types)}"
    assert any(t.name == "calculate" and t.type_annotation == "int" for t in types)
    assert any(t.name == "service" and t.inferred_type == "AuthService" for t in types)

    print("✅ PASSED\n")



def test_typescript_type_extraction():
    """Test TypeScript type extraction."""
    print("=" * 60)
    print("TEST: TypeScript Type Extraction")
    print("=" * 60)

    content = """
function process(x: number): string {
    return String(x);
}

async function fetchData(): Promise<Data> {
    return {} as Data;
}

const name: string = "Alice";
const age: number = 30;
const user = new UserService();
const handler = new RequestHandler(config);
"""

    file_path = Path("test.ts")
    types = extract_typescript_types(file_path, content)

    print(f"✓ Extracted {len(types)} type annotations")

    func_types = [t for t in types if t.name in ["process", "fetchData"]]
    print(f"✓ Function return types: {len(func_types)}")
    for t in func_types:
        print(f"  - {t.name}: {t.type_annotation}")

    var_types = [t for t in types if t.type_annotation and t.name in ["name", "age"]]
    print(f"✓ Variable annotations: {len(var_types)}")

    inferred = [t for t in types if t.inferred_type]
    print(f"✓ Inferred types: {len(inferred)}")
    for t in inferred[:3]:
        print(f"  - {t.name} = new {t.inferred_type}()")

    assert len(types) >= 6, f"Expected at least 6 types, got {len(types)}"
    assert any(t.name == "process" and "string" in t.type_annotation for t in types)

    print("✅ PASSED\n")


def test_go_type_extraction():
    """Test Go type extraction."""
    print("=" * 60)
    print("TEST: Go Type Extraction")
    print("=" * 60)

    content = """
func Calculate(a int, b int) int {
    return a + b
}

func GetName() string {
    return "Alice"
}

var count int
var name string
var handler *RequestHandler

data := DataStruct{
    value: 42,
}
"""

    file_path = Path("test.go")
    types = extract_go_types(file_path, content)

    print(f"✓ Extracted {len(types)} type annotations")

    func_types = [t for t in types if t.name in ["Calculate", "GetName"]]
    print(f"✓ Function return types: {len(func_types)}")
    for t in func_types:
        print(f"  - {t.name}: {t.type_annotation}")

    var_types = [t for t in types if t.type_annotation and t.name in ["count", "name", "handler"]]
    print(f"✓ Variable declarations: {len(var_types)}")

    assert len(types) >= 5, f"Expected at least 5 types, got {len(types)}"

    print("✅ PASSED\n")


def test_type_map_and_resolution():
    """Test type map building and resolution."""
    print("=" * 60)
    print("TEST: Type Map and Resolution")
    print("=" * 60)

    types = [
        TypeInfo(name="user", type_annotation="User", file_path="app.py", line=10),
        TypeInfo(name="config", type_annotation="Config", file_path="app.py", line=11),
        TypeInfo(name="handler", inferred_type="RequestHandler", file_path="app.py", line=12),
        TypeInfo(name="user", type_annotation="AdminUser", file_path="admin.py", line=5),
    ]

    type_map = build_type_map(types)

    print(f"✓ Built type map with {len(type_map)} unique names")
    print(f"  - user: {len(type_map['user'])} definitions")
    print(f"  - config: {len(type_map['config'])} definitions")
    print(f"  - handler: {len(type_map['handler'])} definitions")

    # Resolve from same file (should prefer local)
    user_type_app = resolve_type("user", "app.py", type_map)
    config_type = resolve_type("config", "app.py", type_map)
    handler_type = resolve_type("handler", "app.py", type_map)

    print(f"✓ Resolved types in app.py:")
    print(f"  - user: {user_type_app}")
    print(f"  - config: {config_type}")
    print(f"  - handler: {handler_type}")

    assert user_type_app == "User", f"Expected User, got {user_type_app}"
    assert config_type == "Config"
    assert handler_type == "RequestHandler"

    print("✅ PASSED\n")


def test_import_linkage():
    """Test import link extraction."""
    print("=" * 60)
    print("TEST: Import Linkage Extraction")
    print("=" * 60)

    # Python imports
    py_content = """
from typing import List, Dict, Optional
from collections import defaultdict, Counter
import os
import sys as system
"""

    py_links = extract_import_links(Path("test.py"), py_content)

    print(f"✓ Python: Extracted {len(py_links)} import links")
    for link in py_links[:4]:
        symbols = ", ".join(link.imported_symbols[:3]) if link.imported_symbols else "(all)"
        print(f"  - {link.imported_module}: [{symbols}]")

    # TypeScript imports
    ts_content = """
import { Component, useState, useEffect } from 'react';
import path from 'path';
import * as fs from 'fs';
"""

    ts_links = extract_import_links(Path("test.ts"), ts_content)

    print(f"✓ TypeScript: Extracted {len(ts_links)} import links")
    for link in ts_links[:3]:
        symbols = ", ".join(link.imported_symbols[:3]) if link.imported_symbols else "(all)"
        print(f"  - {link.imported_module}: [{symbols}]")

    # Go imports
    go_content = """
import "fmt"
import "os"
import alias "some/package"
"""

    go_links = extract_import_links(Path("test.go"), go_content)

    print(f"✓ Go: Extracted {len(go_links)} import links")
    for link in go_links:
        symbols = ", ".join(link.imported_symbols) if link.imported_symbols else "(all)"
        print(f"  - {link.imported_module}: [{symbols}]")

    assert len(py_links) >= 3, f"Expected at least 3 Python imports, got {len(py_links)}"
    assert len(ts_links) >= 2, f"Expected at least 2 TS imports, got {len(ts_links)}"
    assert len(go_links) >= 2, f"Expected at least 2 Go imports, got {len(go_links)}"

    # Verify structure
    typing_link = next((l for l in py_links if l.imported_module == "typing"), None)
    assert typing_link is not None
    assert "List" in typing_link.imported_symbols
    assert "Dict" in typing_link.imported_symbols

    print("✅ PASSED\n")


def test_recursive_call_graph():
    """Test recursive call graph building."""
    print("=" * 60)
    print("TEST: Recursive Call Graph")
    print("=" * 60)

    # Create test data with multi-level calls
    symbols = [
        CodeSymbol(name="level0", type="function", file_path="test.py", start_line=1, end_line=3),
        CodeSymbol(name="level1a", type="function", file_path="test.py", start_line=5, end_line=7),
        CodeSymbol(name="level1b", type="function", file_path="test.py", start_line=9, end_line=11),
        CodeSymbol(name="level2", type="function", file_path="test.py", start_line=13, end_line=15),
    ]

    calls = [
        CallReference(caller_file="test.py", callee="level0", line=6),   # level1a calls level0
        CallReference(caller_file="test.py", callee="level0", line=10),  # level1b calls level0
        CallReference(caller_file="test.py", callee="level1a", line=14), # level2 calls level1a
    ]

    scan_result = ScanResult(
        total_files=1,
        files=[],
        scan_duration=0.0,
        symbols=symbols,
        calls=calls,
    )

    # Build graph with depth 0 (target only)
    graph0 = build_recursive_call_graph("level0", scan_result, max_depth=0)
    print(f"✓ Depth 0: {graph0.total_nodes} nodes")
    assert graph0.root_node.symbol_name == "level0"
    assert len(graph0.root_node.callers) == 0  # No callers at depth 0

    # Build graph with depth 1 (direct callers)
    graph1 = build_recursive_call_graph("level0", scan_result, max_depth=1)
    print(f"✓ Depth 1: {graph1.total_nodes} nodes")
    assert len(graph1.root_node.callers) == 2  # level1a and level1b

    # Build graph with depth 2 (indirect callers)
    graph2 = build_recursive_call_graph("level0", scan_result, max_depth=2)
    print(f"✓ Depth 2: {graph2.total_nodes} nodes")
    assert graph2.total_nodes >= 3  # level0 + level1a + level1b + potentially level2

    # Format graph
    formatted = format_call_graph(graph2)
    print("\nFormatted call graph (depth 2):")
    print("-" * 40)
    print(formatted)
    print("-" * 40)

    assert "level0" in formatted
    assert "level1a" in formatted or "level1b" in formatted

    print("✅ PASSED\n")


def test_call_graph_cycle_detection():
    """Test that call graph handles cycles gracefully."""
    print("=" * 60)
    print("TEST: Call Graph Cycle Detection")
    print("=" * 60)

    # Create circular call chain
    symbols = [
        CodeSymbol(name="funcA", type="function", file_path="test.py", start_line=1, end_line=3),
        CodeSymbol(name="funcB", type="function", file_path="test.py", start_line=5, end_line=7),
    ]

    calls = [
        CallReference(caller_file="test.py", callee="funcA", line=6),  # funcB calls funcA
        CallReference(caller_file="test.py", callee="funcB", line=2),  # funcA calls funcB (cycle!)
    ]

    scan_result = ScanResult(
        total_files=1,
        files=[],
        scan_duration=0.0,
        symbols=symbols,
        calls=calls,
    )

    # Should not infinite loop
    graph = build_recursive_call_graph("funcA", scan_result, max_depth=3)
    print(f"✓ Built graph with {graph.total_nodes} nodes (no infinite loop)")
    assert graph.total_nodes < 100, "Should detect and prevent cycles"

    print("✅ PASSED\n")


def main():
    """Run all unit tests."""
    print("\n" + "=" * 70)
    print(" " * 15 + "PHASE 1 UNIT TESTS")
    print(" " * 10 + "(No External Dependencies Required)")
    print("=" * 70)

    try:
        test_python_type_extraction()
        test_typescript_type_extraction()
        test_go_type_extraction()
        test_type_map_and_resolution()
        test_import_linkage()
        test_recursive_call_graph()
        test_call_graph_cycle_detection()

        print("=" * 70)
        print(" " * 20 + "✅ ALL TESTS PASSED!")
        print("=" * 70 + "\n")

        return 0

    except AssertionError as e:
        print("\n" + "=" * 70)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 70 + "\n")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ UNEXPECTED ERROR: {e}")
        print("=" * 70 + "\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
