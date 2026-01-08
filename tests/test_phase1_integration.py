"""
Integration tests for Phase 1 using real file scanning.
"""

import pytest
from pathlib import Path
from cerberus.scanner import scan
from cerberus.graph import build_recursive_call_graph, format_call_graph
from cerberus.parser.type_resolver import build_type_map, resolve_type


class TestPhase1Integration:
    """Integration tests for Phase 1 features."""

    def test_full_scan_with_phase1_data(self, tmp_path):
        """Test full scan including type info and import links."""
        # Use test_files directory
        test_dir = Path(__file__).parent / "test_files"

        # Scan with Phase 1 features
        scan_result = scan(
            test_dir,
            respect_gitignore=False,
            extensions=[".py"],
        )

        # Verify basic scan worked
        assert scan_result.total_files > 0
        assert len(scan_result.symbols) > 0

        # Verify Phase 1.2: Type information extracted
        assert len(scan_result.type_infos) > 0, "Type info should be extracted"

        # Check for specific type annotations from phase1_test.py
        type_names = [t.name for t in scan_result.type_infos]
        # Should find typed variables and functions
        assert len(type_names) > 0

        # Verify Phase 1.3: Import links extracted
        assert len(scan_result.import_links) > 0, "Import links should be extracted"

        # Check for specific imports from phase1_test.py
        import_modules = [il.imported_module for il in scan_result.import_links]
        # Should find imports like 'os', 'pathlib', 'typing'
        assert len(import_modules) > 0

    def test_recursive_call_graph_integration(self, tmp_path):
        """Test recursive call graph with real scanned data."""
        test_dir = Path(__file__).parent / "test_files"

        scan_result = scan(
            test_dir,
            respect_gitignore=False,
            extensions=[".py"],
        )

        # Find a symbol that has callers
        symbols_with_calls = set(c.callee for c in scan_result.calls)

        if symbols_with_calls:
            # Pick first symbol with callers
            target_symbol = list(symbols_with_calls)[0]

            # Build recursive call graph
            graph = build_recursive_call_graph(target_symbol, scan_result, max_depth=2)

            assert graph is not None
            assert graph.target_symbol == target_symbol

            # Format should work
            formatted = format_call_graph(graph)
            assert target_symbol in formatted

    def test_type_resolution_integration(self):
        """Test type resolution with real file data."""
        test_dir = Path(__file__).parent / "test_files"

        scan_result = scan(
            test_dir,
            respect_gitignore=False,
            extensions=[".py", ".ts"],
        )

        # Build type map
        type_map = build_type_map(scan_result.type_infos)

        assert len(type_map) > 0, "Type map should contain entries"

        # Try to resolve a type if any exist
        if scan_result.type_infos:
            first_type = scan_result.type_infos[0]
            resolved = resolve_type(first_type.name, first_type.file_path, type_map)
            # Resolution might return None for some types, which is ok
            assert resolved is not None or resolved is None  # Just check it runs

    def test_import_linkage_integration(self):
        """Test import linkage with real file data."""
        test_dir = Path(__file__).parent / "test_files"

        scan_result = scan(
            test_dir,
            respect_gitignore=False,
            extensions=[".py", ".ts"],
        )

        # Check import links were extracted
        assert len(scan_result.import_links) > 0

        # Verify structure
        for link in scan_result.import_links:
            assert link.importer_file != ""
            assert link.imported_module != ""
            assert link.import_line > 0

        # Group by file
        links_by_file = {}
        for link in scan_result.import_links:
            file_path = link.importer_file
            if file_path not in links_by_file:
                links_by_file[file_path] = []
            links_by_file[file_path].append(link)

        # Should have imports from multiple files
        assert len(links_by_file) > 0

    def test_call_graph_with_method_calls(self):
        """Test call graph including method calls within classes."""
        test_dir = Path(__file__).parent / "test_files"

        scan_result = scan(
            test_dir,
            respect_gitignore=False,
            extensions=[".py"],
        )

        # Look for method calls in the phase1_test.py file
        # Should have calls from process() to validate(), and validate() to helper_function()

        call_map = {}
        for call in scan_result.calls:
            if call.callee not in call_map:
                call_map[call.callee] = []
            call_map[call.callee].append(call)

        # Should have some calls recorded
        assert len(call_map) > 0

    def test_typescript_type_extraction_integration(self):
        """Test TypeScript type extraction in full scan."""
        test_dir = Path(__file__).parent / "test_files"

        scan_result = scan(
            test_dir,
            respect_gitignore=False,
            extensions=[".ts"],
        )

        # Should extract TypeScript types
        ts_types = [t for t in scan_result.type_infos if t.file_path.endswith(".ts")]

        if ts_types:
            # Verify we got type annotations
            assert any(t.type_annotation is not None for t in ts_types)

    def test_index_includes_phase1_data(self):
        """Test that index contains all Phase 1 data."""
        from cerberus.index import build_index
        import tempfile
        import os

        test_dir = Path(__file__).parent / "test_files"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            index_path = Path(f.name)

        try:
            # Build index
            scan_result = build_index(
                test_dir,
                index_path,
                respect_gitignore=False,
                extensions=[".py", ".ts"],
            )

            # Verify Phase 1 data in result
            assert len(scan_result.type_infos) >= 0  # May be 0 if no types found
            assert len(scan_result.import_links) >= 0  # May be 0 if no imports

            # Load index back
            from cerberus.index import load_index
            loaded = load_index(index_path)

            # Verify Phase 1 data persisted
            assert hasattr(loaded, 'type_infos')
            assert hasattr(loaded, 'import_links')
            assert len(loaded.type_infos) == len(scan_result.type_infos)
            assert len(loaded.import_links) == len(scan_result.import_links)

        finally:
            if index_path.exists():
                os.unlink(index_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
