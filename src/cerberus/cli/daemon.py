"""
Daemon management CLI commands.

Phase 9.4: Command routing for daemon lifecycle.
"""

import json
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table

from ..daemon import (
    start_daemon,
    stop_daemon,
    daemon_status,
    health_check,
    is_daemon_running,
    send_rpc_request,
)
from ..logging_config import logger

app = typer.Typer()
console = Console()


@app.command("start")
def start_daemon_cmd(
    index_path: Path = typer.Option(
        Path("cerberus.db"),
        "--index",
        "-i",
        help="Path to SQLite index file",
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help="HTTP port (default: 9876)",
    ),
    foreground: bool = typer.Option(
        False,
        "--foreground",
        "-f",
        help="Run in foreground (default: background)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
):
    """
    Start the Cerberus Daemon server.

    The daemon runs a persistent HTTP server that eliminates
    the Python startup tax for queries.
    """
    logger.info(f"Starting daemon with index: {index_path}")

    # Phase 9.6: Pass current directory as project_path for file watching
    project_path = Path.cwd()

    result = start_daemon(
        index_path=index_path,
        port=port,
        detach=not foreground,
        project_path=project_path,
    )

    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return

    # Human-readable output
    if result["status"] == "started":
        console.print(f"[green]✓[/green] Daemon started successfully")
        console.print(f"  PID: {result['pid']}")
        console.print(f"  Port: {result['port']}")
        console.print(f"  Mode: {result['mode']}")
    elif result["status"] == "already_running":
        console.print(f"[yellow]⚠[/yellow] Daemon already running (PID: {result['pid']})")
    else:
        console.print(f"[red]✗[/red] Failed to start daemon")
        if "error" in result:
            console.print(f"  Error: {result['error']}")


@app.command("stop")
def stop_daemon_cmd(
    timeout: float = typer.Option(
        5.0,
        "--timeout",
        "-t",
        help="Graceful shutdown timeout (seconds)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
):
    """
    Stop the running Cerberus Daemon.

    Sends SIGTERM for graceful shutdown, waits for timeout,
    then sends SIGKILL if necessary.
    """
    logger.info("Stopping daemon")

    result = stop_daemon(timeout=timeout)

    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return

    # Human-readable output
    if result["status"] == "stopped":
        console.print(f"[green]✓[/green] Daemon stopped gracefully")
        if result.get("uptime_seconds"):
            uptime = int(result["uptime_seconds"])
            console.print(f"  Uptime: {uptime}s")
    elif result["status"] == "not_running":
        console.print(f"[yellow]⚠[/yellow] Daemon not running")
    elif result["status"] == "timeout":
        console.print(f"[red]✗[/red] Daemon did not stop gracefully (force killed)")


@app.command("status")
def status_cmd(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
):
    """
    Check the status of the Cerberus Daemon.

    Returns daemon PID, uptime, memory usage, and index status.
    """
    result = daemon_status()

    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return

    # Human-readable output
    if not result["running"]:
        console.print(f"[yellow]Daemon: Not Running[/yellow]")
        return

    table = Table(title="Daemon Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Status", "Running")
    table.add_row("PID", str(result["pid"]))
    if result.get("uptime_seconds"):
        uptime = int(result["uptime_seconds"])
        table.add_row("Uptime", f"{uptime}s")
    table.add_row("Index Loaded", "Yes" if result["index_loaded"] else "No")
    table.add_row("Active Sessions", str(result.get("active_sessions", 0)))
    table.add_row("Port", str(result.get("port", "N/A")))

    console.print(table)


@app.command("health")
def health_cmd(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON",
    ),
):
    """
    Perform a health check on the daemon.

    Tests daemon responsiveness and index accessibility.
    """
    result = health_check()

    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return

    # Human-readable output
    if result["healthy"]:
        console.print(f"[green]✓ Daemon is healthy[/green]")
        console.print(f"  Index accessible: {result['index_accessible']}")
        console.print(f"  Latency: {result['latency_ms']:.2f}ms")
    else:
        console.print(f"[red]✗ Daemon is unhealthy[/red]")


@app.command("rpc")
def rpc_cmd(
    method: str = typer.Argument(
        ...,
        help="RPC method name (e.g., get_symbol, search)",
    ),
    params_json: str = typer.Option(
        "{}",
        "--params",
        "-p",
        help="JSON parameters",
    ),
    pretty: bool = typer.Option(
        True,
        "--pretty/--compact",
        help="Pretty print output",
    ),
):
    """
    Send a raw JSON-RPC request to the daemon.

    Useful for testing and debugging RPC methods.

    Example:
      cerberus daemon rpc get_symbol --params '{"name": "MyClass"}'
    """
    # Check if daemon is running
    if not is_daemon_running():
        console.print("[red]Error: Daemon not running[/red]")
        console.print("Start daemon with: cerberus daemon start")
        raise typer.Exit(1)

    # Parse params
    try:
        params = json.loads(params_json)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON params: {e}[/red]")
        raise typer.Exit(1)

    # Send RPC request
    response = send_rpc_request(method=method, params=params)

    # Output response
    indent = 2 if pretty else None
    typer.echo(json.dumps(response, indent=indent))
