"""
Common CLI helpers to reduce duplication across command modules.

Extracted from Phase 7 Track B de-monolithization.
Contains shared utilities for index handling, error formatting, and output.
"""

from pathlib import Path
from typing import Optional
import typer
from cerberus.index import load_index, ScanResult
from cerberus.paths import get_paths, find_index_path
from .output import get_console

console = get_console()


def get_default_index(index_path: Optional[Path] = None) -> Path:
    """
    Get default index path, checking existence.

    Uses centralized path configuration with legacy fallback.
    Checks .cerberus/cerberus.db first, then cerberus.db in root.

    Args:
        index_path: Optional explicit index path

    Returns:
        Path to index file (defaults to .cerberus/cerberus.db or legacy location)

    Raises:
        typer.Exit: If index file doesn't exist
    """
    if index_path is None:
        # Use centralized path finder that checks all locations
        index_path = find_index_path()

    if index_path is None or not index_path.exists():
        paths = get_paths()
        console.print("[red]Error: Index not found. Checked:[/red]")
        console.print(f"[dim]  - {paths.index_db}[/dim]")
        console.print(f"[dim]  - {paths.legacy_index_db}[/dim]")
        console.print("[dim]Run 'cerberus index .' first or provide --index path.[/dim]")
        raise typer.Exit(code=1)

    return index_path


def load_index_or_exit(index_path: Optional[Path] = None) -> ScanResult:
    """
    Load index from path or exit with error message.

    Args:
        index_path: Optional explicit index path (defaults to cerberus.db)

    Returns:
        Loaded ScanResult

    Raises:
        typer.Exit: If index not found or fails to load
    """
    validated_path = get_default_index(index_path)

    try:
        return load_index(validated_path)
    except Exception as e:
        from rich.markup import escape
        console.print(f"[red]Error loading index: {escape(str(e))}[/red]")
        raise typer.Exit(code=1)


def format_file_location(file_path: str, line: Optional[int] = None) -> str:
    """
    Format file location consistently across commands.

    Args:
        file_path: Path to file
        line: Optional line number

    Returns:
        Formatted string like "path/to/file.py:123"
    """
    if line is not None:
        return f"{file_path}:{line}"
    return file_path


def format_size(size_bytes: int) -> str:
    """
    Format byte size to human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string like "1.5 KB" or "2.3 MB"
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
