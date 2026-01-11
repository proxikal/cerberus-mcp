#!/usr/bin/env python3
"""
Unit tests for Phase 1 that don't require external dependencies.
Tests pure Python logic without scanning infrastructure.
"""

import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast, pytest.mark.phase1]

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

    func_types = [t for t in types if t.name in ["calculate", "get_name", "process"]]
    var_types = [t for t in types if t.name in ["count", "result"]]
    inferred = [t for t in types if t.inferred_type]

    assert len(types) >= 7, f"Expected at least 7 types, got {len(types)}"
    assert any(t.name == "calculate" and t.type_annotation == "int" for t in types)
    assert any(t.name == "service" and t.inferred_type == "AuthService" for t in types)


def test_typescript_type_extraction():
    """Test TypeScript type extraction."""
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

    func_types = [t for t in types if t.name in ["process", "fetchData"]]
    var_types = [t for t in types if t.type_annotation and t.name in ["name", "age"]]
    inferred = [t for t in types if t.inferred_type]

    assert len(types) >= 6, f"Expected at least 6 types, got {len(types)}"
    assert any(t.name == "process" and "string" in t.type_annotation for t in types)


def test_go_type_extraction():
    """Test Go type extraction."""
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

    func_types = [t for t in types if t.name in ["Calculate", "GetName"]]
    var_types = [t for t in types if t.type_annotation and t.name in ["count", "name", "handler"]]

    assert len(types) >= 5, f"Expected at least 5 types, got {len(types)}"


def test_type_map_and_resolution():
    """Test type map building and resolution."""
    types = [
        TypeInfo(name="user", type_annotation="User", file_path="app.py", line=10),
        TypeInfo(name="config", type_annotation="Config", file_path="app.py", line=11),
        TypeInfo(name="handler", inferred_type="RequestHandler", file_path="app.py", line=12),
        TypeInfo(name="user", type_annotation="AdminUser", file_path="admin.py", line=5),
    ]

    type_map = build_type_map(types)

    user_type_app = resolve_type("user", "app.py", type_map)
    config_type = resolve_type("config", "app.py", type_map)
    handler_type = resolve_type("handler", "app.py", type_map)

    assert user_type_app == "User", f"Expected User, got {user_type_app}"
    assert config_type == "Config"
    assert handler_type == "RequestHandler"


def test_import_linkage():
    """Test import link extraction."""
    py_content = """
from typing import List, Dict, Optional
from collections import defaultdict, Counter
import os
import sys as system
"""

    py_links = extract_import_links(Path("test.py"), py_content)

    ts_content = """
import { Component, useState, useEffect } from 'react';
import path from 'path';
import * as fs from 'fs';
"""

    ts_links = extract_import_links(Path("test.ts"), ts_content)

    go_content = """
import "fmt"
import "os"
import alias "some/package"
"""

    go_links = extract_import_links(Path("test.go"), go_content)

    assert len(py_links) >= 3, f"Expected at least 3 Python imports, got {len(py_links)}"
    assert len(ts_links) >= 2, f"Expected at least 2 TS imports, got {len(ts_links)}"
    assert len(go_links) >= 2, f"Expected at least 2 Go imports, got {len(go_links)}"

    typing_link = next((l for l in py_links if l.imported_module == "typing"), None)
    assert typing_link is not None
    assert "List" in typing_link.imported_symbols
    assert "Dict" in typing_link.imported_symbols


def test_recursive_call_graph():
    """Test recursive call graph building."""
    symbols = [
        CodeSymbol(name="level0", type="function", file_path="test.py", start_line=1, end_line=3),
        CodeSymbol(name="level1a", type="function", file_path="test.py", start_line=5, end_line=7),
        CodeSymbol(name="level1b", type="function", file_path="test.py", start_line=9, end_line=11),
        CodeSymbol(name="level2", type="function", file_path="test.py", start_line=13, end_line=15),
    ]

    calls = [
        CallReference(caller_file="test.py", callee="level0", line=6),
        CallReference(caller_file="test.py", callee="level0", line=10),
        CallReference(caller_file="test.py", callee="level1a", line=14),
    ]

    scan_result = ScanResult(
        total_files=1,
        files=[],
        scan_duration=0.0,
        symbols=symbols,
        calls=calls,
    )

    graph0 = build_recursive_call_graph("level0", scan_result, max_depth=0)
    assert graph0.root_node.symbol_name == "level0"
    assert len(graph0.root_node.callers) == 0

    graph1 = build_recursive_call_graph("level0", scan_result, max_depth=1)
    assert len(graph1.root_node.callers) == 2

    graph2 = build_recursive_call_graph("level0", scan_result, max_depth=2)
    assert graph2.total_nodes >= 3

    formatted = format_call_graph(graph2)
    assert "level0" in formatted
    assert "level1a" in formatted or "level1b" in formatted


def test_call_graph_cycle_detection():
    """Test that call graph handles cycles gracefully."""
    symbols = [
        CodeSymbol(name="funcA", type="function", file_path="test.py", start_line=1, end_line=3),
        CodeSymbol(name="funcB", type="function", file_path="test.py", start_line=5, end_line=7),
    ]

    calls = [
        CallReference(caller_file="test.py", callee="funcA", line=6),
        CallReference(caller_file="test.py", callee="funcB", line=2),
    ]

    scan_result = ScanResult(
        total_files=1,
        files=[],
        scan_duration=0.0,
        symbols=symbols,
        calls=calls,
    )

    graph = build_recursive_call_graph("funcA", scan_result, max_depth=3)
    assert graph.total_nodes < 100, "Should detect and prevent cycles"
