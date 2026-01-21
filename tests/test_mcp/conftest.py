"""Shared fixtures for MCP tests."""
import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from cerberus.index import build_index
from cerberus.mcp import create_server
import cerberus.mcp.index_manager as index_manager_module


def unwrap_result(result):
    """
    Normalize FastMCP CallToolResult to plain Python data.

    Prefers structured_content (unwrapped if FastMCP wraps under 'result'),
    otherwise falls back to parsing text content when available.
    """
    structured = getattr(result, "structured_content", None)
    if structured is not None:
        # Unwrap 'result' key if present (ignoring metadata like _token_info)
        if isinstance(structured, dict) and "result" in structured:
            return structured["result"]
        return structured

    content = getattr(result, "content", None) or []
    texts = [getattr(block, "text", None) for block in content if getattr(block, "text", None)]
    if len(texts) == 1:
        text = texts[0]
        try:
            return json.loads(text)
        except Exception:
            return text
    if texts:
        return texts

    return result


@pytest.fixture(autouse=True)
def reset_index_manager():
    """Reset the global IndexManager singleton before each test."""
    from cerberus.mcp.index_manager import IndexManager

    # Clear the module-level singleton
    index_manager_module._manager = None

    # Clear the class-level singleton
    IndexManager._instance = None

    yield

    # Clean up after test
    if index_manager_module._manager is not None:
        try:
            index_manager_module._manager.shutdown()
        except Exception:
            pass
    index_manager_module._manager = None
    IndexManager._instance = None


@pytest.fixture
def temp_project():
    """Create a temporary project with sample files."""
    temp_dir = tempfile.mkdtemp()
    project = Path(temp_dir)

    (project / "src").mkdir()
    (project / "src" / "main.py").write_text(
        '''"""
Main module."""

def hello(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

class Calculator:
    """Simple calculator."""

    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b
'''
    )

    (project / "src" / "utils.py").write_text(
        '''"""
Utility functions."""
from .main import add

def sum_list(numbers: list) -> int:
    """Sum a list of numbers."""
    total = 0
    for n in numbers:
        total = add(total, n)
    return total
'''
    )

    cwd_before = Path.cwd()
    os.chdir(project)
    try:
        yield project
    finally:
        os.chdir(cwd_before)
        shutil.rmtree(temp_dir)


@pytest.fixture
def indexed_project(temp_project):
    """Create a temporary project with index built."""
    index_path = temp_project / ".cerberus" / "cerberus.db"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    (temp_project / ".cerberus" / "history").mkdir(parents=True, exist_ok=True)

    build_index(
        directory=temp_project,
        extensions=[".py"],
        output_path=index_path,
    )

    return temp_project, index_path


@pytest.fixture(scope="session")
def mcp_server():
    """Create an MCP server instance for testing."""
    return create_server()


@pytest_asyncio.fixture
async def mcp_client(mcp_server):
    """Async FastMCP client connected to in-process server."""
    from fastmcp import Client

    client = Client(mcp_server)
    async with client:
        yield client
# CI test trigger
