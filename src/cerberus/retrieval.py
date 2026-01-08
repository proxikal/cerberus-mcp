"""
Backward compatibility shim for retrieval functions.

This module is deprecated. Use cerberus.retrieval package instead.
"""

# Import from new retrieval package for backward compatibility
from cerberus.retrieval.utils import find_symbol, read_range

__all__ = ["find_symbol", "read_range"]
