"""
Session Memory Module (Phase 18)

Captures developer preferences, decisions, and learnings across sessions.
Injects context into future AI sessions to eliminate repetitive explanation.

Key constraints:
- Maximum injection size: 4KB / 150 lines
- Maximum profile size: 1KB / 50 lines
- Store verbose, inject terse (90%+ compression target)
"""

from cerberus.memory.store import MemoryStore
from cerberus.memory.profile import ProfileManager
from cerberus.memory.context import ContextGenerator
from cerberus.memory.decisions import DecisionManager
from cerberus.memory.corrections import CorrectionManager
from cerberus.memory.prompts import PromptManager
from cerberus.memory.extract import GitExtractor

__all__ = [
    'MemoryStore',
    'ProfileManager',
    'ContextGenerator',
    'DecisionManager',
    'CorrectionManager',
    'PromptManager',
    'GitExtractor',
]
