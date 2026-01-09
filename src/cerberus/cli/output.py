"""
CLI Output Utilities

Machine-aware output functions that adapt based on MACHINE_MODE.
"""

import sys
import typer
from typing import Any, Optional
from rich.console import Console as RichConsole
from rich.table import Table

from cerberus.cli.config import CLIConfig


class MachineAwareConsole:
    """
    A Console wrapper that automatically adapts output based on machine mode.
    Acts as a drop-in replacement for rich.console.Console.
    """

    def __init__(self):
        self._rich_console = RichConsole()

    def print(self, *args, **kwargs):
        """Print that respects machine mode."""
        if CLIConfig.is_machine_mode():
            # In machine mode, suppress output or convert to minimal text
            import re

            for arg in args:
                if isinstance(arg, str):
                    # Remove rich markup and emojis
                    plain = re.sub(r'\[.*?\]', '', arg)
                    # Remove emojis (comprehensive Unicode ranges)
                    plain = re.sub(r'[\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0000FE00-\U0000FE0F\U0001F000-\U0001F02F\U0001F0A0-\U0001F0FF\U0001FA00-\U0001FA6F\U00002700-\U000027FF]', '', plain)
                    # Only print if there's meaningful content left
                    plain = plain.strip()
                    if plain:
                        print(plain)
                elif isinstance(arg, Table):
                    # Suppress table output in machine mode - should use --json instead
                    pass
                elif hasattr(arg, '__rich__'):
                    # Skip other rich renderables in machine mode
                    pass
                else:
                    # Print other simple types
                    if arg:
                        print(arg)
        else:
            # Human mode - use rich console
            self._rich_console.print(*args, **kwargs)

    def __getattr__(self, name):
        """Delegate all other attributes to the rich console."""
        return getattr(self._rich_console, name)


# Console instance for rich output (machine-aware)
_console = MachineAwareConsole()


def echo(message: str = "", **kwargs) -> None:
    """
    Print a message respecting machine mode.
    In machine mode, strips formatting and prints plain text.
    """
    if CLIConfig.is_machine_mode():
        # Plain text output only
        print(message, **kwargs)
    else:
        typer.echo(message, **kwargs)


def print_rich(renderable: Any, **kwargs) -> None:
    """
    Print rich content (tables, panels, etc.) respecting machine mode.
    In machine mode, this should not be called - use plain output instead.
    """
    if not CLIConfig.is_machine_mode():
        _console.print(renderable, **kwargs)


def print_table(table: Table) -> None:
    """
    Print a rich table respecting machine mode.
    In machine mode, converts table to plain text format.
    """
    if CLIConfig.is_machine_mode():
        # In machine mode, tables should be converted to minimal text
        # This is a placeholder - actual implementation will depend on table content
        echo("[WARN] Table output in machine mode - use structured data instead")
    else:
        _console.print(table)


def print_json(data: dict, minified: bool = None) -> None:
    """
    Print JSON data respecting machine mode.
    In machine mode, always minifies. In human mode, pretty prints.
    """
    import json

    if minified is None:
        minified = CLIConfig.is_machine_mode()

    if minified:
        echo(json.dumps(data, separators=(',', ':')))
    else:
        echo(json.dumps(data, indent=2))


def print_error(message: str, suggest: Optional[list] = None, code: Optional[str] = None,
                input_value: Optional[str] = None, actionable_fix: Optional[str] = None) -> None:
    """
    Print an error message respecting machine mode.
    In machine mode, outputs structured JSON error with actionable suggestions.

    Args:
        message: Error message
        suggest: List of suggestions
        code: Error code (e.g., "SYMBOL_NOT_FOUND")
        input_value: The input that caused the error
        actionable_fix: A command that would fix the issue
    """
    if CLIConfig.is_machine_mode():
        error_obj = {
            "status": "error",
            "message": message
        }
        if code:
            error_obj["code"] = code
        if input_value:
            error_obj["input"] = input_value
        if suggest:
            error_obj["suggestions"] = suggest
        if actionable_fix:
            error_obj["actionable_fix"] = actionable_fix
        print_json(error_obj)
    else:
        typer.echo(f"Error: {message}", err=True)
        if suggest:
            typer.echo(f"Suggestions: {', '.join(suggest)}", err=True)
        if actionable_fix:
            typer.echo(f"Try: {actionable_fix}", err=True)


def structured_error(code: str, message: str, input_value: Optional[str] = None,
                    suggestions: Optional[list] = None, actionable_fix: Optional[str] = None) -> dict:
    """
    Create a structured error object for machine mode.

    Args:
        code: Error code (e.g., "SYMBOL_NOT_FOUND", "FILE_NOT_FOUND")
        message: Human-readable error message
        input_value: The input that caused the error
        suggestions: List of alternative suggestions
        actionable_fix: Command to fix the issue

    Returns:
        Structured error dictionary
    """
    error_obj = {
        "status": "error",
        "code": code,
        "message": message
    }
    if input_value:
        error_obj["input"] = input_value
    if suggestions:
        error_obj["suggestions"] = suggestions
    if actionable_fix:
        error_obj["actionable_fix"] = actionable_fix
    return error_obj


def print_metric(label: str, value: Any) -> None:
    """
    Print a metric line respecting machine mode and metric configuration.
    In machine mode with metrics enabled, outputs minimal format.
    """
    if CLIConfig.is_silent_metrics():
        return

    if CLIConfig.is_machine_mode():
        echo(f"[Meta] {label}: {value}")
    else:
        # Rich formatting for human mode
        _console.print(f"[dim]{label}:[/dim] [bold]{value}[/bold]")


def get_console() -> Console:
    """
    Get the console instance for advanced usage.
    Note: Direct console usage should check machine mode.
    """
    return _console
