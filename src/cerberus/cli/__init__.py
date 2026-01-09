"""
CLI Command Modules

Modular command-line interface following the self-similarity mandate.
Each module contains a logical group of related commands.
"""

from cerberus.cli import index, operational, utils, retrieval, symbolic, dogfood

__all__ = ['index', 'operational', 'utils', 'retrieval', 'symbolic', 'dogfood']
