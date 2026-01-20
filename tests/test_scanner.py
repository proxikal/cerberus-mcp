"""Unit tests for the scanner module."""

import os
import pytest
from pathlib import Path

pytestmark = pytest.mark.fast

# This import will fail until we create the scanner module
# We are practicing Test-Driven Development (TDD)
from cerberus.scanner import scan
from cerberus.schemas import FileObject

TEST_PROJECT_DIR = Path(__file__).parent / "test_project"
TEST_FILES_DIR = Path(__file__).parent / "test_files"
LARGE_FILE = TEST_FILES_DIR / "large.bin"

def test_scan_finds_all_files_when_not_respecting_gitignore():
    """
    Tests that the scanner finds all files when specifically told
    not to respect the .gitignore file.
    """
    # This will fail until we implement the scanner
    scan_result = scan(TEST_PROJECT_DIR, respect_gitignore=False)
    
    # README.md is filtered (non-workflow markdown) so expect 5 files including .gitignore
    assert scan_result.total_files == 5
    
    found_paths = {f.path for f in scan_result.files}
    
    assert "app.py" in found_paths
    assert "data.json" in found_paths
    assert "secret.log" in found_paths
    assert ".gitignore" in found_paths
    assert os.path.join("node_modules", "some_lib.js") in found_paths

def test_scan_respects_gitignore_by_default():
    """
    Tests that the scanner correctly ignores files specified in .gitignore.
    This is the default and most common behavior.
    """
    scan_result = scan(TEST_PROJECT_DIR) # respect_gitignore should be True by default
    
    # README.md filtered (non-workflow markdown); node_modules/log ignored by patterns
    assert scan_result.total_files == 2
    
    found_paths = {f.path for f in scan_result.files}
    ignored_paths = {
        "secret.log",
        os.path.join("node_modules", "some_lib.js")
    }
    
    assert "app.py" in found_paths
    assert "data.json" in found_paths
    assert not (found_paths & ignored_paths) # Assert no overlap with ignored files

def test_scan_populates_file_object_correctly():
    """
    Tests that the scanner correctly populates the FileObject schema
    with all the required metadata.
    """
    scan_result = scan(TEST_PROJECT_DIR, respect_gitignore=False)
    
    # Find the app.py file object
    app_py_file = next((f for f in scan_result.files if f.path == "app.py"), None)
    
    assert app_py_file is not None
    assert isinstance(app_py_file, FileObject)
    
    # Check path attributes
    assert app_py_file.path == "app.py"
    assert os.path.isabs(app_py_file.abs_path)
    assert app_py_file.abs_path.endswith("tests/test_project/app.py")
    
    # Check metadata
    assert app_py_file.size > 0
    assert isinstance(app_py_file.last_modified, float)

def test_scan_with_file_extensions_filter():
    """
    Tests that the scanner can filter results by a list of file extensions.
    """
    # Only find python files
    scan_result = scan(TEST_PROJECT_DIR, extensions=[".py"])
    assert scan_result.total_files == 1
    assert scan_result.files[0].path == "app.py"
    
    # Find python and markdown files
    scan_result_multi = scan(TEST_PROJECT_DIR, extensions=[".py", ".md"])
    # README.md skipped (non-workflow); only app.py remains
    assert scan_result_multi.total_files == 1
    found_paths = {f.path for f in scan_result_multi.files}
    assert found_paths == {"app.py"}

def test_scan_collects_symbols_from_supported_files():
    """
    Tests that scan integrates with the parser and returns extracted symbols.
    """
    scan_result = scan(TEST_FILES_DIR, respect_gitignore=False)

    # Note: test_files directory has grown over time with phase-specific test files
    # Just verify we scanned files and extracted symbols (at least the originals)
    assert scan_result.total_files >= 5  # At least the original 5 files
    symbol_names = {s.name for s in scan_result.symbols}

    expected_symbols = {
        "MyClass",
        "__init__",
        "greet",
        "top_level_function",
        "MyJsClass",
        "topLevelJsFunction",
        "MyTsClass",
        "topLevelTsFunction",
        "UserProfile",
        "Status",
        "Widget",
        "Greet",
        "add",
    }

    assert expected_symbols.issubset(symbol_names)


def test_scan_respects_max_bytes_filter():
    """
    Tests that large files can be skipped using max_bytes.
    """
    # Ensure the large file exists and is larger than threshold
    assert LARGE_FILE.stat().st_size > 1000

    scan_result = scan(TEST_FILES_DIR, respect_gitignore=False, max_bytes=1000)
    paths = {f.path for f in scan_result.files}
    assert "large.bin" not in paths


def test_scan_collects_imports_and_calls():
    """
    Tests that imports and calls are extracted for dependency mapping.
    """
    scan_result = scan(TEST_FILES_DIR, respect_gitignore=False)

    modules = {imp.module for imp in scan_result.imports}
    assert {"math", "collections", "fs", "path", "fmt"}.issubset(modules)

    callees = {call.callee for call in scan_result.calls}
    assert {"sqrt", "readFileSync", "join"}.issubset(callees)
