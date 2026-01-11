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
from .common import format_size

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
        help="Action: start, stop, status, restart, logs, health"
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
    blueprints: bool = typer.Option(
        False,
        "--blueprints",
        help="Show blueprint cache metrics (for 'health' action)."
    ),
    auto_blueprint: bool = typer.Option(
        False,
        "--auto-blueprint",
        help="Enable background blueprint regeneration (Phase 13.5, for 'start' action)."
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
      health  - Check watcher health (log size, CPU usage)
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
            pid = start_watcher(project_path, index_path, force=force, auto_blueprint=auto_blueprint)

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
            pid = start_watcher(project_path, index_path, force=True, auto_blueprint=auto_blueprint)

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

        elif action == "health":
            import psutil
            from cerberus.watcher import is_watcher_running, stop_watcher
            from cerberus.watcher.daemon import get_watcher_pid

            # Check if watcher is running
            if not is_watcher_running(project_path):
                if json_output:
                    typer.echo(json.dumps({"status": "stopped", "message": "Watcher is not running"}))
                else:
                    console.print("[yellow]Watcher is not running[/yellow]")
                return

            # Get watcher PID
            pid = get_watcher_pid(project_path)

            # Check log file size
            log_file = get_log_file_path(project_path)
            log_size_bytes = 0
            log_size_mb = 0.0
            if log_file.exists():
                log_size_bytes = log_file.stat().st_size
                log_size_mb = log_size_bytes / (1024 * 1024)

            # Check CPU usage
            cpu_percent = 0.0
            memory_mb = 0.0
            try:
                process = psutil.Process(pid)
                cpu_percent = process.cpu_percent(interval=0.5)
                memory_mb = process.memory_info().rss / (1024 * 1024)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                if json_output:
                    typer.echo(json.dumps({"status": "error", "message": "Could not access watcher process"}))
                else:
                    console.print("[red]Error: Could not access watcher process[/red]")
                raise typer.Exit(code=1)

            # Determine health status
            issues = []
            is_critical = False

            # Check log file size (> 50MB is critical)
            if log_size_mb > 50:
                issues.append(f"Log file exceeded 50MB ({log_size_mb:.1f} MB) - rotation failure")
                is_critical = True
            elif log_size_mb > 20:
                issues.append(f"Log file large ({log_size_mb:.1f} MB) - rotation may be struggling")

            # Check CPU usage (> 80% is critical)
            if cpu_percent > 80:
                issues.append(f"CPU usage excessive ({cpu_percent:.1f}%)")
                is_critical = True
            elif cpu_percent > 50:
                issues.append(f"CPU usage elevated ({cpu_percent:.1f}%)")

            # Determine overall status
            if is_critical:
                status = "critical"
            elif issues:
                status = "warning"
            else:
                status = "healthy"

            # Phase 13.4: Get blueprint cache stats if requested
            blueprint_stats = None
            if blueprints:
                try:
                    import sqlite3
                    from cerberus.blueprint.cache_manager import BlueprintCache

                    conn = sqlite3.connect(str(index_path))
                    cache = BlueprintCache(conn)
                    blueprint_stats = cache.get_stats()
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error getting blueprint cache stats: {e}")
                    blueprint_stats = {"error": str(e)}

            # Build response
            health_data = {
                "status": status,
                "pid": pid,
                "log_size_mb": round(log_size_mb, 2),
                "cpu_percent": round(cpu_percent, 1),
                "memory_mb": round(memory_mb, 1),
                "issues": issues,
            }

            if blueprint_stats:
                health_data["blueprint_cache"] = blueprint_stats

            # If critical, stop the watcher
            if is_critical:
                console.print(f"[bold red]⚠️  CRITICAL: Watcher health check failed![/bold red]")
                for issue in issues:
                    console.print(f"[red]  • {issue}[/red]")
                console.print(f"\n[yellow]Stopping watcher (PID: {pid})...[/yellow]")

                stop_watcher(project_path)
                health_data["action_taken"] = "stopped"

                if json_output:
                    typer.echo(json.dumps(health_data, indent=2))
                else:
                    console.print(f"\n[bold yellow]⚠️  WATCHER STOPPED: {issues[0]}[/bold yellow]\n")
                    console.print("[cyan]Options:[/cyan]")
                    console.print("  1. Clean logs and restart: [bold]cerberus clean --preserve-index && cerberus watcher start[/bold]")
                    console.print("  2. Investigate logs: [bold]cerberus watcher logs[/bold]")
                    console.print("  3. Continue without watcher")
                    console.print("\n[dim]What would you like to do?[/dim]")

                raise typer.Exit(code=1)

            # Output results
            if json_output:
                typer.echo(json.dumps(health_data, indent=2))
            else:
                if status == "healthy":
                    console.print(f"[green]✓ Watcher is healthy[/green]")
                elif status == "warning":
                    console.print(f"[yellow]⚠ Watcher has warnings:[/yellow]")
                    for issue in issues:
                        console.print(f"[yellow]  • {issue}[/yellow]")

                console.print(f"\n[cyan]Metrics:[/cyan]")
                console.print(f"  PID: {pid}")
                console.print(f"  Log size: {log_size_mb:.1f} MB")
                console.print(f"  CPU usage: {cpu_percent:.1f}%")
                console.print(f"  Memory: {memory_mb:.1f} MB")

                # Phase 13.4: Display blueprint cache stats if available
                if blueprint_stats and "error" not in blueprint_stats:
                    console.print(f"\n[cyan]Blueprint Cache:[/cyan]")
                    console.print(f"  Total entries: {blueprint_stats.get('total_entries', 0)}")
                    console.print(f"  Valid entries: {blueprint_stats.get('valid_entries', 0)}")
                    console.print(f"  Expired entries: {blueprint_stats.get('expired_entries', 0)}")
                    console.print(f"  Cache hits: {blueprint_stats.get('cache_hits', 0)}")
                    console.print(f"  Cache misses: {blueprint_stats.get('cache_misses', 0)}")
                    console.print(f"  Hit rate: {blueprint_stats.get('hit_rate_percent', 0.0)}%")
                elif blueprint_stats and "error" in blueprint_stats:
                    console.print(f"\n[yellow]Blueprint Cache: Error - {blueprint_stats['error']}[/yellow]")

        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            console.print("Valid actions: start, stop, status, restart, logs, health")
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


@app.command("clean")
def clean_cmd(
    project_path: Optional[Path] = typer.Option(
        None,
        "--project",
        "-p",
        help="Path to project (default: current directory).",
    ),
    preserve_index: bool = typer.Option(
        False,
        "--preserve-index",
        help="Keep the main index file (cerberus.db)."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be deleted without actually deleting."
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    Clean Cerberus cache, logs, and database files.

    This command removes:
      - .cerberus/ directory (logs, backups, watcher data)
      - cerberus.db (main index database)
      - .cerberus_ledger.db (ledger database)
      - Temporary watcher files (PID files, sockets)

    Use --preserve-index to keep cerberus.db.
    Use --dry-run to see what would be deleted.
    """
    import shutil
    from cerberus.watcher import stop_watcher, is_watcher_running
    from cerberus.watcher.config import get_pid_file_path, get_socket_file_path

    if project_path is None:
        project_path = Path.cwd()

    # Files and directories to clean
    items_to_clean = []

    # .cerberus directory (logs, backups, etc.)
    cerberus_dir = project_path / ".cerberus"
    if cerberus_dir.exists():
        size = sum(f.stat().st_size for f in cerberus_dir.rglob('*') if f.is_file())
        items_to_clean.append({
            "path": cerberus_dir,
            "type": "directory",
            "size": size,
            "description": "Cache directory (logs, backups, watcher data)"
        })

    # Main index database
    if not preserve_index:
        index_db = project_path / "cerberus.db"
        if index_db.exists():
            items_to_clean.append({
                "path": index_db,
                "type": "file",
                "size": index_db.stat().st_size,
                "description": "Main index database"
            })

    # Ledger database
    ledger_db = project_path / ".cerberus_ledger.db"
    if ledger_db.exists():
        items_to_clean.append({
            "path": ledger_db,
            "type": "file",
            "size": ledger_db.stat().st_size,
            "description": "Ledger database"
        })

    # Watcher PID and socket files
    pid_file = get_pid_file_path(project_path)
    if pid_file.exists():
        items_to_clean.append({
            "path": pid_file,
            "type": "file",
            "size": pid_file.stat().st_size,
            "description": "Watcher PID file"
        })

    socket_file = get_socket_file_path(project_path)
    if socket_file.exists():
        items_to_clean.append({
            "path": socket_file,
            "type": "file",
            "size": 0,
            "description": "Watcher socket file"
        })

    if not items_to_clean:
        if json_output:
            typer.echo(json.dumps({"status": "nothing_to_clean", "items": []}))
        else:
            console.print("[green]Nothing to clean - no Cerberus files found.[/green]")
        return

    # Calculate total size
    total_size = sum(item["size"] for item in items_to_clean)

    # Dry run mode
    if dry_run:
        if json_output:
            output = {
                "status": "dry_run",
                "items": [
                    {
                        "path": str(item["path"]),
                        "type": item["type"],
                        "size_bytes": item["size"],
                        "size_formatted": format_size(item["size"]),
                        "description": item["description"]
                    }
                    for item in items_to_clean
                ],
                "total_size_bytes": total_size,
                "total_size_formatted": format_size(total_size)
            }
            typer.echo(json.dumps(output, indent=2))
        else:
            console.print("[bold yellow]DRY RUN - No files will be deleted[/bold yellow]\n")
            console.print(f"[cyan]Items to clean:[/cyan]")
            for item in items_to_clean:
                size_str = format_size(item["size"])
                console.print(f"  • {item['path']} ({size_str}) - {item['description']}")
            console.print(f"\n[bold]Total size: {format_size(total_size)}[/bold]")
        return

    # Show what will be deleted
    if not json_output:
        console.print(f"[bold yellow]⚠️  WARNING: This will delete the following:[/bold yellow]\n")
        for item in items_to_clean:
            size_str = format_size(item["size"])
            console.print(f"  • {item['path']} ({size_str}) - {item['description']}")
        console.print(f"\n[bold]Total size: {format_size(total_size)}[/bold]\n")

    # Stop watcher if running
    if is_watcher_running(project_path):
        console.print("[yellow]Stopping watcher daemon...[/yellow]")
        stop_watcher(project_path)

    # Confirm deletion
    if not force and not json_output:
        confirm = typer.confirm("Are you sure you want to delete these files?")
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=0)

    # Perform deletion
    deleted_items = []
    failed_items = []

    for item in items_to_clean:
        try:
            if item["type"] == "directory":
                shutil.rmtree(item["path"])
            else:
                item["path"].unlink()
            deleted_items.append(str(item["path"]))
            if not json_output:
                console.print(f"[green]✓ Deleted: {item['path']}[/green]")
        except Exception as e:
            failed_items.append({"path": str(item["path"]), "error": str(e)})
            if not json_output:
                console.print(f"[red]✗ Failed to delete {item['path']}: {e}[/red]")

    # Output results
    if json_output:
        output = {
            "status": "completed",
            "deleted_items": deleted_items,
            "failed_items": failed_items,
            "total_size_freed_bytes": total_size,
            "total_size_freed_formatted": format_size(total_size)
        }
        typer.echo(json.dumps(output, indent=2))
    else:
        if deleted_items:
            console.print(f"\n[bold green]✓ Cleaned {len(deleted_items)} items ({format_size(total_size)} freed)[/bold green]")
        if failed_items:
            console.print(f"[bold red]✗ Failed to delete {len(failed_items)} items[/bold red]")
            raise typer.Exit(code=1)
