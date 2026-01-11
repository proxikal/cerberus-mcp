"""
CLI Metrics Commands (Phase 19.3)

Commands for viewing and managing efficiency metrics.
"""

import json
import typer
from typing import Optional

from cerberus.cli.output import get_console
from cerberus.cli.config import CLIConfig
from cerberus.metrics.efficiency import (
    generate_efficiency_report,
    MetricsStore,
    EfficiencyTracker,
)

app = typer.Typer()
console = get_console()


def _format_number(n: int) -> str:
    """Format number with thousands separator."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


@app.command("report")
def report_cmd(
    days: int = typer.Option(
        7,
        "--days",
        "-d",
        help="Number of days to include in report.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON.",
    ),
):
    """
    Generate efficiency report for the specified period.

    Shows command usage patterns, workflow efficiency, and suggestions
    for improvement.

    Examples:
      cerberus metrics report              # Last 7 days
      cerberus metrics report --days 30    # Last 30 days
    """
    report = generate_efficiency_report(days)

    if json_output or CLIConfig.is_machine_mode():
        output = {
            "period_days": report.period_days,
            "total_sessions": report.total_sessions,
            "total_commands": report.total_commands,
            "command_counts": report.command_counts,
            "flag_usage": report.flag_usage,
            "workflow_patterns": {
                "blueprint_then_read": report.blueprint_then_read,
                "direct_get_symbol": report.direct_get_symbol,
                "memory_context_sessions": report.memory_context_sessions,
            },
            "token_efficiency": {
                "total_saved": report.total_tokens_saved,
                "avg_efficiency_percent": report.avg_efficiency_percent,
            },
            "hints": {
                "shown": report.hints_shown,
                "followed": report.hints_followed,
            },
            "suggestions": report.suggestions,
        }
        typer.echo(json.dumps(output, separators=(",", ":")))
        return

    # Human mode output
    console.print(f"\n[bold]Cerberus Efficiency Report (Last {days} Days)[/bold]")
    console.print("─" * 45)

    console.print(f"Sessions: {report.total_sessions}")
    console.print(f"Commands: {report.total_commands}")

    # Command breakdown
    if report.command_counts:
        console.print("\n[cyan]Command Usage:[/cyan]")
        sorted_cmds = sorted(
            report.command_counts.items(), key=lambda x: x[1], reverse=True
        )
        for cmd, count in sorted_cmds[:10]:
            console.print(f"  {cmd}: {count}")

    # Workflow patterns
    console.print("\n[cyan]Workflow Patterns:[/cyan]")
    if report.blueprint_then_read > 0:
        console.print(f"  Blueprint -> Read: {report.blueprint_then_read} [green](efficient)[/green]")
    if report.direct_get_symbol > 0:
        console.print(f"  Direct get-symbol: {report.direct_get_symbol} [yellow](review these)[/yellow]")
    if report.total_sessions > 0:
        memory_pct = (report.memory_context_sessions / report.total_sessions) * 100
        console.print(
            f"  Memory context used: {report.memory_context_sessions}/{report.total_sessions} sessions ({memory_pct:.0f}%)"
        )

    # Token efficiency
    if report.total_tokens_saved > 0:
        console.print("\n[cyan]Token Efficiency:[/cyan]")
        console.print(f"  Estimated saved: {_format_number(report.total_tokens_saved)} tokens")

    # Hints
    if report.hints_shown > 0:
        console.print("\n[cyan]Hints:[/cyan]")
        follow_pct = (
            (report.hints_followed / report.hints_shown) * 100
            if report.hints_shown > 0
            else 0
        )
        console.print(f"  Shown: {report.hints_shown}, Followed: {report.hints_followed} ({follow_pct:.0f}%)")

    # Suggestions
    if report.suggestions:
        console.print("\n[yellow]Suggestions:[/yellow]")
        for suggestion in report.suggestions:
            console.print(f"  - {suggestion}")

    if report.total_commands == 0:
        console.print("\n[dim]No data yet. Run some Cerberus commands to start tracking.[/dim]")

    console.print()


@app.command("clear")
def clear_cmd(
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt.",
    ),
):
    """
    Clear all stored metrics data.

    This removes all efficiency metrics history. Token tracking is unaffected.
    """
    if not confirm:
        console.print("[yellow]This will delete all efficiency metrics data.[/yellow]")
        confirmed = typer.confirm("Are you sure?")
        if not confirmed:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(code=0)

    store = MetricsStore()
    store.clear()

    console.print("[green]Metrics data cleared.[/green]")


@app.command("status")
def status_cmd(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON.",
    ),
):
    """
    Show metrics collection status.

    Displays whether metrics collection is enabled and storage location.
    """
    import os
    from cerberus.metrics.efficiency import METRICS_DIR

    is_disabled = os.getenv("CERBERUS_NO_METRICS", "").lower() in ("true", "1", "yes")
    store_path = METRICS_DIR / "efficiency_metrics.json"
    store_exists = store_path.exists()

    store_size = 0
    event_count = 0
    session_count = 0

    if store_exists:
        store_size = store_path.stat().st_size
        try:
            store = MetricsStore()
            aggregates = store.get_aggregates()
            event_count = len(store._data.get("events", []))
            session_count = len(store._data.get("sessions", []))
        except Exception:
            pass

    if json_output or CLIConfig.is_machine_mode():
        output = {
            "enabled": not is_disabled,
            "storage_path": str(store_path),
            "storage_exists": store_exists,
            "storage_size_bytes": store_size,
            "event_count": event_count,
            "session_count": session_count,
        }
        typer.echo(json.dumps(output, separators=(",", ":")))
        return

    console.print("\n[bold]Metrics Status[/bold]")
    console.print("─" * 20)

    if is_disabled:
        console.print("Collection: [red]Disabled[/red] (CERBERUS_NO_METRICS=true)")
    else:
        console.print("Collection: [green]Enabled[/green]")

    console.print(f"Storage: {store_path}")

    if store_exists:
        console.print(f"Size: {_format_number(store_size)} bytes")
        console.print(f"Events: {event_count}")
        console.print(f"Sessions: {session_count}")
    else:
        console.print("[dim]No data stored yet.[/dim]")

    console.print()
