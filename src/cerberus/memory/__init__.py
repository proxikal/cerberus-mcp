"""
Session Memory Module - SQLite-based Memory System

Captures developer preferences, decisions, and learnings across sessions.
Injects context into future AI sessions to eliminate repetitive explanation.

Storage: ~/.cerberus/memory.db (SQLite)
"""

from cerberus.memory.extract import GitExtractor
from cerberus.memory.storage import MemoryStorage
from cerberus.memory.retrieval import MemoryRetrieval
from cerberus.memory.search import MemorySearchEngine
from cerberus.memory.context_injector import inject_startup_context, inject_query_context

__all__ = [
    'GitExtractor',
    'MemoryStorage',
    'MemoryRetrieval',
    'MemorySearchEngine',
    'inject_startup_context',
    'inject_query_context',
]
