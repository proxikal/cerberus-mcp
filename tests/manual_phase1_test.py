#!/usr/bin/env python3
"""
Manual integration test for Phase 1 features.
Run this directly to test without pytest.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cerberus.scanner import scan
from cerberus.graph import build_recursive_call_graph, format_call_graph
from cerberus.parser.type_resolver import extract_python_types, build_type_map
from cerberus.parser.dependencies import extract_import_links


def test_basic_scan():
    """Test basic scanning with Phase 1 features."""
    print("=" * 60)
    print("TEST 1: Basic Scan with Phase 1 Features")
    print("=" * 60)

    test_dir = Path(__file__).parent / "test_files"
    print(f"Scanning directory: {test_dir}")

    scan_result = scan(
        test_dir,
        respect_gitignore=False,
        extensions=[".py"],
    )

    print(f"✓ Files scanned: {scan_result.total_files}")
    print(f"✓ Symbols extracted: {len(scan_result.symbols)}")
    print(f"✓ Imports found: {len(scan_result.imports)}")
    print(f"✓ Calls tracked: {len(scan_result.calls)}")
    print(f"✓ Type infos (Phase 1.2): {len(scan_result.type_infos)}")
    print(f"✓ Import links (Phase 1.3): {len(scan_result.import_links)}")

    assert scan_result.total_files > 0, "Should find files"
    assert len(scan_result.symbols) > 0, "Should extract symbols"
    print("\n✅ Basic scan test PASSED\n")

    return scan_result


def test_type_extraction():
    """Test type resolution (Phase 1.2)."""
    print("=" * 60)
    print("TEST 2: Type Resolution (Phase 1.2)")
    print("=" * 60)

    content = """
from typing import List, Dict

def process_data(items: List[str]) -> Dict[str, int]:
    result: Dict[str, int] = {}
    service = AuthService()
    return result
"""

    file_path = Path("test.py")
    types = extract_python_types(file_path, content)

    print(f"✓ Extracted {len(types)} type annotations")

    for t in types[:5]:  # Show first 5
        annotation = t.type_annotation or t.inferred_type or "unknown"
        print(f"  - {t.name}: {annotation} (line {t.line})")

    type_map = build_type_map(types)
    print(f"✓ Built type map with {len(type_map)} unique names")

    assert len(types) > 0, "Should extract type info"
    print("\n✅ Type extraction test PASSED\n")


def test_import_linkage():
    """Test import linkage (Phase 1.3)."""
    print("=" * 60)
    print("TEST 3: Import Linkage (Phase 1.3)")
    print("=" * 60)

    content = """
from typing import List, Dict, Optional
from collections import defaultdict
import os
import sys as system
"""

    file_path = Path("test.py")
    links = extract_import_links(file_path, content)

    print(f"✓ Extracted {len(links)} import links")

    for link in links[:5]:  # Show first 5
        symbols_str = ", ".join(link.imported_symbols[:3]) if link.imported_symbols else "(all)"
        print(f"  - {link.imported_module}: [{symbols_str}] (line {link.import_line})")

    assert len(links) > 0, "Should extract import links"
    print("\n✅ Import linkage test PASSED\n")


def test_recursive_call_graph():
    """Test recursive call graph (Phase 1.1)."""
    print("=" * 60)
    print("TEST 4: Recursive Call Graph (Phase 1.1)")
    print("=" * 60)

    test_dir = Path(__file__).parent / "test_files"
    scan_result = scan(
        test_dir,
        respect_gitignore=False,
        extensions=[".py"],
    )

    # Find a symbol that has callers
    symbols_with_calls = set(c.callee for c in scan_result.calls)

    if not symbols_with_calls:
        print("⚠ No function calls found in test files")
        print("  Creating synthetic test data...")

        from cerberus.schemas import CodeSymbol, CallReference, ScanResult

        # Create test data
        symbols = [
            CodeSymbol(name="main", type="function", file_path="test.py", start_line=1, end_line=3),
            CodeSymbol(name="helper", type="function", file_path="test.py", start_line=5, end_line=7),
            CodeSymbol(name="utility", type="function", file_path="test.py", start_line=9, end_line=11),
        ]

        calls = [
            CallReference(caller_file="test.py", callee="main", line=6),  # helper calls main
            CallReference(caller_file="test.py", callee="helper", line=10),  # utility calls helper
        ]

        scan_result = ScanResult(
            total_files=1,
            files=[],
            scan_duration=0.0,
            symbols=symbols,
            calls=calls,
        )

        symbols_with_calls = {"main", "helper"}

    target_symbol = list(symbols_with_calls)[0]
    print(f"✓ Building call graph for: {target_symbol}")

    graph = build_recursive_call_graph(target_symbol, scan_result, max_depth=2)

    print(f"✓ Graph nodes: {graph.total_nodes}")
    print(f"✓ Max depth: {graph.max_depth}")

    if graph.root_node:
        print(f"✓ Root: {graph.root_node.symbol_name}")
        print(f"✓ Direct callers: {len(graph.root_node.callers)}")

        # Format and display
        print("\nFormatted call graph:")
        print("-" * 40)
        formatted = format_call_graph(graph)
        print(formatted)
        print("-" * 40)

    assert graph is not None, "Should build call graph"
    print("\n✅ Recursive call graph test PASSED\n")


def test_index_persistence():
    """Test that Phase 1 data persists to index."""
    print("=" * 60)
    print("TEST 5: Index Persistence")
    print("=" * 60)

    from cerberus.index import build_index, load_index
    import tempfile
    import os

    test_dir = Path(__file__).parent / "test_files"

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        index_path = Path(f.name)

    try:
        print(f"✓ Building index: {index_path}")

        scan_result = build_index(
            test_dir,
            index_path,
            respect_gitignore=False,
            extensions=[".py"],
        )

        print(f"✓ Index created with {scan_result.total_files} files")
        print(f"  - Type infos: {len(scan_result.type_infos)}")
        print(f"  - Import links: {len(scan_result.import_links)}")

        print(f"✓ Loading index from disk...")
        loaded = load_index(index_path)

        print(f"✓ Loaded {loaded.total_files} files")
        print(f"  - Type infos: {len(loaded.type_infos)}")
        print(f"  - Import links: {len(loaded.import_links)}")

        # Verify Phase 1 data preserved
        assert len(loaded.type_infos) == len(scan_result.type_infos), "Type infos should match"
        assert len(loaded.import_links) == len(scan_result.import_links), "Import links should match"

        print("\n✅ Index persistence test PASSED\n")

    finally:
        if index_path.exists():
            os.unlink(index_path)
            print(f"✓ Cleaned up test index")


def main():
    """Run all manual tests."""
    print("\n" + "=" * 60)
    print("PHASE 1 MANUAL INTEGRATION TESTS")
    print("=" * 60 + "\n")

    try:
        scan_result = test_basic_scan()
        test_type_extraction()
        test_import_linkage()
        test_recursive_call_graph()
        test_index_persistence()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60 + "\n")

        return 0

    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60 + "\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
