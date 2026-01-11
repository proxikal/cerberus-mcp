"""
CLI Refresh Command (Phase 19.7)

Protocol refresh for AI agents to restore CERBERUS.md context.

Modes:
  (default)   ~150 tokens - Critical rules only
  --rules     ~300 tokens - Tool selection + core rules
  --full      ~1500+ tokens - Complete CERBERUS.md
"""

import json
import typer
from pathlib import Path
from typing import Optional

from cerberus.cli.output import get_console
from cerberus.cli.config import CLIConfig
from cerberus.protocol import (
    get_protocol_light,
    get_protocol_rules,
    get_protocol_full,
    get_protocol_tracker,
    PROTOCOL_VERSION,
)
from cerberus.protocol.content import get_protocol_json

app = typer.Typer()
console = get_console()


@app.command()
def refresh(
    rules: bool = typer.Option(
        False,
        "--rules",
        "-r",
        help="Include tool selection table and core rules (~300 tokens).",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        "-f",
        help="Full CERBERUS.md reload (~1500+ tokens).",
    ),
    status: bool = typer.Option(
        False,
        "--status",
        "-s",
        help="Show protocol tracking status without refresh.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON for agents.",
    ),
):
    """
    Refresh Cerberus protocol context for AI agents.

    Restores critical rules that may have degraded in agent memory
    after many tool calls or context compaction.

    Examples:
      cerberus refresh              # Light refresh (~150 tokens)
      cerberus refresh --rules      # Standard refresh (~300 tokens)
      cerberus refresh --full       # Complete reload (~1500+ tokens)
      cerberus refresh --status     # Check protocol state
    """
    tracker = get_protocol_tracker()

    # Status-only mode
    if status:
        status_info = tracker.get_status()

        if json_output or CLIConfig.is_machine_mode():
            typer.echo(json.dumps(status_info, separators=(",", ":")))
            return

        console.print("\n[bold]Protocol Status[/bold]")
        console.print(f"  Session age: {status_info['session_age_minutes']} minutes")
        console.print(f"  Commands since refresh: {status_info['commands_since_refresh']}")
        console.print(f"  Total commands: {status_info['total_commands']}")
        console.print(f"  Refresh count: {status_info['refresh_count']}")

        if status_info['last_refresh_minutes'] is not None:
            console.print(f"  Last refresh: {status_info['last_refresh_minutes']} minutes ago")
        else:
            console.print("  Last refresh: [yellow]Never[/yellow]")

        if status_info['needs_refresh']:
            console.print(f"\n[yellow]Refresh suggested:[/yellow] {status_info['refresh_reason']}")
            console.print("  Run: cerberus refresh")
        else:
            console.print("\n[green]Protocol state: Current[/green]")

        return

    # Determine content level
    if full:
        content = get_protocol_full()
        level = "full"
    elif rules:
        content = get_protocol_rules()
        level = "rules"
    else:
        content = get_protocol_light()
        level = "light"

    # Record the refresh
    tracker.record_refresh()

    if json_output or CLIConfig.is_machine_mode():
        output = {
            "protocol_version": PROTOCOL_VERSION,
            "refresh_level": level,
            "content": content,
            "structured": get_protocol_json() if not full else None,
            "status": tracker.get_status(),
        }
        typer.echo(json.dumps(output, indent=2))
        return

    # Human mode - just print the content
    console.print(content)
    console.print(f"\n[dim]Protocol refreshed ({level} mode). Status reset.[/dim]")


# Convenience function for programmatic access
def do_refresh(level: str = "light") -> str:
    """
    Perform protocol refresh and return content.

    Args:
        level: "light", "rules", or "full"

    Returns:
        Protocol content string
    """
    tracker = get_protocol_tracker()
    tracker.record_refresh()

    if level == "full":
        return get_protocol_full()
    elif level == "rules":
        return get_protocol_rules()
    else:
        return get_protocol_light()
