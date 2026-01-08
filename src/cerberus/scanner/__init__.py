"""
This facade exposes the public API for the scanner module.
Following the Self-Similarity Mandate, other parts of the application
should only import from here, not from internal modules.
"""
from .facade import scan

__all__ = ["scan"]
