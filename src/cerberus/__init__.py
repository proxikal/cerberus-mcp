"""
Cerberus - Intelligent Code Context Engine

MCP-based interface for code indexing, retrieval, and memory.
"""

__version__ = "2.0.0"

# Core exports
from cerberus.index import build_index, load_index
from cerberus.retrieval import hybrid_search
from cerberus.retrieval.utils import find_symbol_fts, read_range
from cerberus.storage import SQLiteIndexStore, ScanResultAdapter
from cerberus.schemas import CodeSymbol, ScanResult

# MCP server
from cerberus.mcp import create_server, run_server

__all__ = [
    "__version__",
    "build_index",
    "load_index",
    "hybrid_search",
    "find_symbol_fts",
    "read_range",
    "SQLiteIndexStore",
    "ScanResultAdapter",
    "CodeSymbol",
    "ScanResult",
    "create_server",
    "run_server",
]
