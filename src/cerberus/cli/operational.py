"""
CLI Operational Commands

System operational commands: hello, version, doctor, update, watcher, session.
"""

import json
import typer
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.markup import escape

from cerberus.logging_config import logger
from cerberus.agent_session import display_session_summary, get_session_tracker, clear_session
from .output import get_console

app = typer.Typer()
console = get_console()


@app.command()
def hello():
    """
    Basic check to ensure CLI is working.
    """
    logger.info("Cerberus Active. The Gatekeeper is ready.")
    typer.echo("Cerberus Active. The Gatekeeper is ready.")


@app.command()
def version():
    """
    Prints the current version of Cerberus.
    """
    typer.echo("Cerberus v0.5.0")


@app.command()
def doctor(
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Optional path to an index file to validate its health. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
):
    """
    Runs a diagnostic check on the Cerberus environment.
    """
    logger.info("Running diagnostic checks...")

    # Default to cerberus.db in CWD if not provided
    if index_path is None:
        default_db = Path("cerberus.db")
        if default_db.exists():
            index_path = default_db
            logger.info(f"Using default index: {index_path}")

    from cerberus.doctor import run_diagnostics

    results = run_diagnostics(index_path=index_path)

    if json_output:
        typer.echo(json.dumps(results, indent=2))
        return

    table = Table(title="Doctor Diagnostics")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Detail", style="magenta")
    table.add_column("Remediation", style="yellow")

    for item in results:
        status_color = {"ok": "green", "warn": "yellow", "fail": "red"}.get(item["status"], "white")
        table.add_row(item["name"], f"[{status_color}]{item['status']}[/]", item["detail"], item["remediation"])

    console.print("🩺 Running Cerberus Doctor...")
    console.print(table)


@app.command("update")
def update(
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file to update. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    project_path: Optional[Path] = typer.Option(
        None,
        "--project",
        "-p",
        help="Path to project root (auto-detected from index if not provided).",
        exists=True,
        file_okay=False,
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Force full re-index instead of incremental update."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be updated without making changes."
    ),
    stats: bool = typer.Option(
        False,
        "--stats",
        help="Show detailed update statistics."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [CORE FEATURE] Incrementally update an existing index based on git changes (Phase 3).

    Uses git diff to detect changed files and surgically updates only affected symbols.
    10x faster than full re-indexing for small changes.
    """
    from cerberus.incremental import detect_changes, update_index_incrementally
    from cerberus.index import load_index

    # Default to cerberus.db in CWD if not provided
    if index_path is None:
        index_path = Path("cerberus.db")
        if not index_path.exists():
            console.print(f"[red]Error: Index file 'cerberus.db' not found in current directory.[/red]")
            console.print(f"[dim]Run 'cerberus index .' first or provide --index path.[/dim]")
            raise typer.Exit(code=1)

    try:
        # Detect changes
        if not dry_run:
            console.print("[cyan]Detecting changes...[/cyan]")

        if project_path is None:
            # Infer from index
            scan_result = load_index(index_path)
            project_path = Path(scan_result.project_root) if scan_result.project_root else Path.cwd()

        changes = detect_changes(project_path, index_path)

        if changes is None:
            console.print("[yellow]Could not detect changes (not a git repository or no index metadata)[/yellow]")
            console.print("[yellow]Tip: Use 'cerberus index' to create a fresh index with git tracking[/yellow]")
            raise typer.Exit(code=1)

        # Show what would be updated in dry-run mode
        if dry_run:
            if json_output:
                typer.echo(json.dumps(changes.model_dump(), indent=2))
            else:
                console.print(f"\n[bold]Changes Detected:[/bold]")
                console.print(f"  Added files: {len(changes.added)}")
                console.print(f"  Modified files: {len(changes.modified)}")
                console.print(f"  Deleted files: {len(changes.deleted)}")

                if changes.added:
                    console.print(f"\n[green]Added:[/green]")
                    for f in changes.added[:10]:
                        console.print(f"  + {f}")
                    if len(changes.added) > 10:
                        console.print(f"  ... and {len(changes.added) - 10} more")

                if changes.modified:
                    console.print(f"\n[yellow]Modified:[/yellow]")
                    for f in changes.modified[:10]:
                        console.print(f"  ~ {f.path} ({len(f.changed_lines)} ranges)")
                    if len(changes.modified) > 10:
                        console.print(f"  ... and {len(changes.modified) - 10} more")

                if changes.deleted:
                    console.print(f"\n[red]Deleted:[/red]")
                    for f in changes.deleted[:10]:
                        console.print(f"  - {f}")
                    if len(changes.deleted) > 10:
                        console.print(f"  ... and {len(changes.deleted) - 10} more")

            return

        # Perform incremental update
        if not changes.added and not changes.modified and not changes.deleted:
            console.print("[green]No changes detected. Index is up to date.[/green]")
            return

        console.print(f"[cyan]Updating index incrementally...[/cyan]")

        result = update_index_incrementally(
            index_path=index_path,
            project_path=project_path,
            changes=changes,
            force_full_reparse=full,
        )

        if json_output:
            typer.echo(json.dumps(result.model_dump(), indent=2))
            return

        # Show results
        console.print(f"\n[bold green]✓ Index updated successfully[/bold green]")
        console.print(f"  Strategy: {result.strategy}")
        console.print(f"  Files re-parsed: {result.files_reparsed}")
        console.print(f"  Symbols updated: {len(result.updated_symbols)}")
        console.print(f"  Symbols removed: {len(result.removed_symbols)}")
        console.print(f"  Time: {result.elapsed_time:.2f}s")

        if stats and result.updated_symbols:
            console.print(f"\n[cyan]Updated Symbols:[/cyan]")
            for symbol in result.updated_symbols[:10]:
                console.print(f"  • {symbol.name} ({symbol.type}) in {symbol.file_path}")
            if len(result.updated_symbols) > 10:
                console.print(f"  ... and {len(result.updated_symbols) - 10} more")

    except Exception as e:
        logger.error(f"Failed to update index: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command("watcher")
def watcher_cmd(
    action: str = typer.Argument(
        ...,
        help="Action: start, stop, status, restart, logs"
    ),
    project_path: Optional[Path] = typer.Option(
        None,
        "--project",
        "-p",
        help="Path to project (default: current directory).",
    ),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force restart (for 'start' action)."
    ),
    follow: bool = typer.Option(
        False,
        "--follow",
        help="Follow logs in real-time (for 'logs' action)."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [CORE FEATURE] Manage the background watcher daemon (Phase 3).

    The watcher monitors filesystem changes and automatically keeps the index synchronized.
    It auto-starts on most commands, but can be controlled manually.

    Actions:
      start   - Start the watcher daemon
      stop    - Stop the watcher daemon
      status  - Show watcher status
      restart - Restart the watcher daemon
      logs    - View watcher logs
    """
    from cerberus.watcher import start_watcher, stop_watcher, watcher_status
    from cerberus.watcher.config import get_log_file_path

    if project_path is None:
        project_path = Path.cwd()

    # Default to cerberus.db in CWD if not provided
    if index_path is None:
        index_path = Path("cerberus.db")

    try:
        if action == "start":
            pid = start_watcher(project_path, index_path, force=force)

            if json_output:
                typer.echo(json.dumps({"status": "started", "pid": pid}))
            else:
                console.print(f"[green]✓ Watcher started (PID: {pid})[/green]")
                console.print(f"  Watching: {project_path}")
                console.print(f"  Index: {index_path}")

        elif action == "stop":
            success = stop_watcher(project_path)

            if json_output:
                typer.echo(json.dumps({"status": "stopped" if success else "failed"}))
            else:
                if success:
                    console.print("[green]✓ Watcher stopped[/green]")
                else:
                    console.print("[red]✗ Failed to stop watcher[/red]")
                    raise typer.Exit(code=1)

        elif action == "status":
            status = watcher_status(project_path)

            if json_output:
                typer.echo(json.dumps(status.model_dump(), indent=2))
            else:
                if status.running:
                    console.print(f"[green]✓ Watcher running (PID: {status.pid})[/green]")
                    console.print(f"  Watching: {status.watching}")
                    if status.uptime:
                        console.print(f"  Uptime: {status.uptime:.0f}s")
                    if status.last_update:
                        import datetime
                        last_update = datetime.datetime.fromtimestamp(status.last_update)
                        console.print(f"  Last update: {last_update}")
                    console.print(f"  Events processed: {status.events_processed}")
                    console.print(f"  Updates triggered: {status.updates_triggered}")
                else:
                    console.print(f"[yellow]Watcher not running for {project_path}[/yellow]")

        elif action == "restart":
            console.print("[cyan]Restarting watcher...[/cyan]")
            stop_watcher(project_path)
            pid = start_watcher(project_path, index_path, force=True)

            if json_output:
                typer.echo(json.dumps({"status": "restarted", "pid": pid}))
            else:
                console.print(f"[green]✓ Watcher restarted (PID: {pid})[/green]")

        elif action == "logs":
            log_file = get_log_file_path(project_path)

            if not log_file.exists():
                console.print(f"[yellow]No log file found at {log_file}[/yellow]")
                raise typer.Exit(code=1)

            if follow:
                # Follow logs (like tail -f)
                import subprocess
                console.print(f"[cyan]Following logs from {log_file}[/cyan]")
                console.print("[dim](Press Ctrl+C to stop)[/dim]\n")
                subprocess.run(["tail", "-f", str(log_file)])
            else:
                # Show last 50 lines
                console.print(f"[cyan]Last 50 lines from {log_file}:[/cyan]\n")
                import subprocess
                result = subprocess.run(["tail", "-n", "50", str(log_file)], capture_output=True, text=True)
                console.print(result.stdout)

        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            console.print("Valid actions: start, stop, status, restart, logs")
            raise typer.Exit(code=1)

    except Exception as e:
        logger.error(f"Watcher command failed: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command(hidden=True)
def session(
    action: str = typer.Argument("summary", help="Action: summary or clear"),
):
    """
    [DOGFOODING UTILITY] Display or clear agent session tracking.

    Examples:
      cerberus session summary  # Show accumulated metrics
      cerberus session clear    # Reset session tracking
    """
    tracker = get_session_tracker()

    if not tracker.enabled:
        console.print("[yellow]Session tracking is not enabled.[/yellow]")
        console.print("Set CERBERUS_TRACK_SESSION=true to enable.")
        return

    if action == "summary":
        display_session_summary()
    elif action == "clear":
        clear_session()
        console.print("[green]Session cleared.[/green]")
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Valid actions: summary, clear")
        raise typer.Exit(code=1)
