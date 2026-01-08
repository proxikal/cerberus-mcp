import pytest
from pathlib import Path
from cerberus.parser import parse_file

TEST_FILES_DIR = Path(__file__).parent / "test_files"
SAMPLE_PY = TEST_FILES_DIR / "sample.py"
SAMPLE_JS = TEST_FILES_DIR / "sample.js"
SAMPLE_TS = TEST_FILES_DIR / "sample.ts"

def test_parse_python_file():
    """
    Tests that the regex parser can correctly identify symbols in a Python file.
    """
    symbols = parse_file(SAMPLE_PY)
    
    assert len(symbols) == 4
    
    symbol_map = {s.name: s for s in symbols}
    
    assert "MyClass" in symbol_map
    assert symbol_map["MyClass"].type == "class"
    assert symbol_map["MyClass"].start_line == 3
    
    assert "__init__" in symbol_map
    assert symbol_map["__init__"].type == "function"
    assert symbol_map["__init__"].start_line == 5

    assert "greet" in symbol_map
    assert symbol_map["greet"].type == "function"
    assert symbol_map["greet"].start_line == 8
    
    assert "top_level_function" in symbol_map
    assert symbol_map["top_level_function"].type == "function"
    assert symbol_map["top_level_function"].start_line == 12

def test_parse_unsupported_file_returns_empty():
    """
    Tests that parsing an unsupported file type returns an empty list
    and logs a warning, without crashing.
    """
    unsupported_file = TEST_FILES_DIR / ".." / "README.md" # Find a .md file
    symbols = parse_file(unsupported_file)
    assert symbols == []

def test_parse_javascript_file():
    """
    Tests that the regex parser can identify classes and functions in a JS file.
    """
    symbols = parse_file(SAMPLE_JS)

    assert len(symbols) == 2
    symbol_map = {s.name: s for s in symbols}

    assert "MyJsClass" in symbol_map
    assert symbol_map["MyJsClass"].type == "class"
    assert symbol_map["MyJsClass"].start_line == 3

    assert "topLevelJsFunction" in symbol_map
    assert symbol_map["topLevelJsFunction"].type == "function"
    assert symbol_map["topLevelJsFunction"].start_line == 13

def test_parse_typescript_file():
    """
    Tests that the regex parser can identify classes and functions in a TS file.
    """
    symbols = parse_file(SAMPLE_TS)

    assert len(symbols) == 2
    symbol_map = {s.name: s for s in symbols}

    assert "MyTsClass" in symbol_map
    assert symbol_map["MyTsClass"].type == "class"
    assert symbol_map["MyTsClass"].start_line == 3

    assert "topLevelTsFunction" in symbol_map
    assert symbol_map["topLevelTsFunction"].type == "function"
    assert symbol_map["topLevelTsFunction"].start_line == 11
