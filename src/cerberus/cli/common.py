"""
Common imports and utilities for CLI commands.
"""

import json
import typer
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from cerberus.logging_config import logger
from .output import get_console

console = get_console()
