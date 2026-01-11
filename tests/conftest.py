"""
Pytest configuration for Cerberus test suite.

This conftest.py provides:
- Machine-mode logging (suppresses console output)
- Common fixtures for temp directories, DB connections, indexes
- Output capture for AI-friendly test runs
- Marker-based test organization
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

import pytest

from cerberus.logging_config import setup_logging


# ============================================================================
# GLOBAL CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest for AI-friendly operation."""
    # Set machine mode environment variable
    os.environ.setdefault("CERBERUS_MACHINE_MODE", "1")
    os.environ.setdefault("CERBERUS_SILENT_METRICS", "1")
    os.environ.setdefault("CERBERUS_NO_TRACK", "true")


# ============================================================================
# LOGGING FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_logging():
    """
    Machine mode by default - suppress console logs for clean test output.
    """
    setup_logging(level="DEBUG", suppress_console=True)


@pytest.fixture
def capture_prints(capsys):
    """
    Fixture to capture and discard print output.
    Use this in tests that have unavoidable print statements.

    Usage:
        def test_something(capture_prints):
            # prints are captured, not shown
            some_function_that_prints()
            captured = capture_prints.readouterr()
            # captured.out contains the print output if needed
    """
    yield capsys


# ============================================================================
# TEMPORARY DIRECTORY FIXTURES
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory that's cleaned up after the test."""
    tmp = Path(tempfile.mkdtemp(prefix="cerberus_test_"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def temp_project(temp_dir):
    """
    Create a temporary project directory with sample Python files.

    Returns:
        Path to the temp directory containing sample files.
    """
    # Create sample Python file
    sample = temp_dir / "sample.py"
    sample.write_text('''
def hello():
    """Say hello."""
    return "hello"

def world():
    """Say world."""
    return "world"

class Greeter:
    """A greeting class."""

    def greet(self, name):
        """Greet someone."""
        return f"Hello, {name}!"
''')

    # Create a second file
    utils = temp_dir / "utils.py"
    utils.write_text('''
def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b
''')

    yield temp_dir


@pytest.fixture
def temp_memory_dir(temp_dir):
    """Create a temporary directory for memory storage."""
    return temp_dir


# ============================================================================
# INDEX FIXTURES
# ============================================================================

@pytest.fixture
def temp_index(temp_project):
    """
    Create a temporary index from the temp_project.

    Returns:
        Tuple of (project_path, index_path)
    """
    from cerberus.index import build_index

    index_path = temp_project / "test.db"
    build_index(temp_project, str(index_path))

    yield temp_project, index_path


@pytest.fixture
def sqlite_store(temp_index):
    """
    Create a SQLiteIndexStore from the temp_index.

    Returns:
        SQLiteIndexStore instance
    """
    from cerberus.storage.sqlite_store import SQLiteIndexStore

    project_path, index_path = temp_index
    store = SQLiteIndexStore(str(index_path))
    yield store
    store.close()


# ============================================================================
# BENCHMARK HELPERS
# ============================================================================

@pytest.fixture
def benchmark_silent():
    """
    Fixture for benchmark tests that suppresses timing output.

    Usage:
        @pytest.mark.benchmark
        def test_performance(benchmark_silent):
            result = benchmark_silent(my_function, arg1, arg2)
            assert result < 0.1  # 100ms threshold
    """
    import time

    def run_benchmark(func, *args, iterations=10, **kwargs):
        """Run function multiple times and return average time in seconds."""
        # Warmup
        func(*args, **kwargs)

        total = 0
        for _ in range(iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            total += time.perf_counter() - start

        return total / iterations

    return run_benchmark


# ============================================================================
# SKIP CONDITIONS
# ============================================================================

def _check_faiss_available():
    """Check if FAISS is available."""
    try:
        import faiss
        return True
    except ImportError:
        return False


requires_git = pytest.mark.skipif(
    shutil.which("git") is None,
    reason="Git not available"
)

requires_faiss = pytest.mark.skipif(
    not _check_faiss_available(),
    reason="FAISS not available"
)
