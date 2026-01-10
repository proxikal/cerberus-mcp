"""
Mutation package for Phase 11: The Surgical Writer (Symbolic Editing).

Provides AST-based code editing operations that work on symbol names
rather than line numbers, enabling precise surgical edits.
"""

from .facade import MutationFacade
from .locator import SymbolLocator
from .editor import CodeEditor
from .formatter import CodeFormatter
from .validator import CodeValidator
from .import_manager import ImportManager
from .ledger import DiffLedger
from .guard import SymbolGuard
from .undo import UndoStack
from .style_guard import StyleGuard
from .config import (
    MUTATION_CONFIG,
    FORMATTERS,
    SAFETY_THRESHOLDS,
    INDENT_DETECTION,
)

__all__ = [
    # Main facade
    "MutationFacade",

    # Components
    "SymbolLocator",
    "CodeEditor",
    "CodeFormatter",
    "CodeValidator",
    "ImportManager",
    "DiffLedger",
    "SymbolGuard",
    "UndoStack",
    "StyleGuard",

    # Configuration
    "MUTATION_CONFIG",
    "FORMATTERS",
    "SAFETY_THRESHOLDS",
    "INDENT_DETECTION",
]
