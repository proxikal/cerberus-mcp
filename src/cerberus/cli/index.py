"""
CLI Index Commands

Commands for scanning and indexing codebases.

Bloat Protection:
    Default limits protect against runaway indexing:
    - 1MB max file size
    - 500 symbols per file
    - 100,000 total symbols
    - 100MB index size

    Override via env vars or CLI flags for large projects.
"""

import json
import os
import typer
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from cerberus.scanner import scan as perform_scan
from cerberus.index import build_index
from cerberus.paths import get_paths
from cerberus.limits import get_limits_config, reset_limits_config
from cerberus.exceptions import PreflightError
from .output import get_console

app = typer.Typer()
console = get_console()


def _get_default_index_output() -> Path:
    """Get default output path for index, ensuring directory exists."""
    paths = get_paths()
    paths.ensure_dirs()
    return paths.index_db


@app.command()
def scan(
    directory: Path = typer.Argument(
        ".", help="The directory to scan.", exists=True, file_okay=False, readable=True
    ),
    no_gitignore: bool = typer.Option(
        False, "--no-gitignore", help="Do not respect .gitignore files."
    ),
    ext: Optional[List[str]] = typer.Option(
        None, "--ext", help="File extensions to include (e.g., .py, .md). Can be used multiple times."
    ),
    max_bytes: Optional[int] = typer.Option(
        None, "--max-bytes", help="Skip files larger than this size (in bytes)."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output results as JSON for agents."
    ),
):
    """
    Scans a directory to map its file structure and metadata.
    """
    respect_gitignore = not no_gitignore

    scan_result = perform_scan(directory, respect_gitignore, extensions=ext, max_bytes=max_bytes)

    if json_output:
        typer.echo(json.dumps(scan_result.model_dump(), indent=2))
        return

    table = Table(title=f"Scan Results for '{directory}'")
    table.add_column("File Path", style="cyan", no_wrap=True)
    table.add_column("Size (Bytes)", justify="right", style="magenta")
    table.add_column("Last Modified", justify="right", style="green")

    for file_obj in scan_result.files:
        table.add_row(
            file_obj.path,
            str(file_obj.size),
            str(round(file_obj.last_modified))
        )

    console.print(table)
    console.print(f"Found [bold blue]{scan_result.total_files}[/bold blue] files in [bold yellow]{scan_result.scan_duration:.4f}s[/bold yellow].")
    console.print(f"Extracted [bold green]{len(scan_result.symbols)}[/bold green] symbols from supported files.")


@app.command()
def index(
    directory: Path = typer.Argument(
        ".", help="The directory to index.", exists=True, file_okay=False, readable=True
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Path to save the index file. Defaults to .cerberus/cerberus.db"
    ),
    no_gitignore: bool = typer.Option(
        False, "--no-gitignore", help="Do not respect .gitignore files."
    ),
    ext: Optional[List[str]] = typer.Option(
        None, "--ext", help="File extensions to include (e.g., .py, .md). Can be used multiple times."
    ),
    incremental: bool = typer.Option(
        False, "--incremental", help="Reuse existing index to skip unchanged files."
    ),
    store_embeddings: bool = typer.Option(
        True, "--store-embeddings/--no-store-embeddings", help="Persist embeddings in the index for faster semantic search. Default: enabled."
    ),
    model_name: str = typer.Option(
        "all-MiniLM-L6-v2", "--model-name", help="Embedding model name when storing embeddings."
    ),
    max_bytes: Optional[int] = typer.Option(
        None, "--max-bytes", help="Skip files larger than this size (in bytes). Default: 1MB."
    ),
    max_symbols_per_file: Optional[int] = typer.Option(
        None, "--max-symbols-per-file", help="Max symbols per file before truncation. Default: 500."
    ),
    max_total_symbols: Optional[int] = typer.Option(
        None, "--max-total-symbols", help="Max total symbols in index. Default: 100,000."
    ),
    skip_preflight: bool = typer.Option(
        False, "--skip-preflight", help="Skip disk space and permission pre-flight checks."
    ),
    strict: bool = typer.Option(
        False, "--strict", help="Exit with error if validation produces warnings."
    ),
    show_limits: bool = typer.Option(
        False, "--show-limits", help="Display current limits configuration and exit."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output results as JSON for agents."
    ),
):
    """
    Runs a scan and writes the results to a SQLite index.

    Bloat Protection: Default limits protect against runaway indexing.
    Use --show-limits to see current values. Override with --max-* flags
    or environment variables (CERBERUS_MAX_TOTAL_SYMBOLS, etc).
    """
    # Handle --show-limits: display config and exit
    if show_limits:
        config = get_limits_config()
        limits_info = config.to_dict()
        if json_output:
            typer.echo(json.dumps(limits_info, indent=2))
        else:
            console.print("[bold]Current Index Limits[/bold]")
            console.print(f"  Max file size: [cyan]{limits_info['max_file_bytes'] / (1024*1024):.1f}MB[/cyan]")
            console.print(f"  Max symbols/file: [cyan]{limits_info['max_symbols_per_file']:,}[/cyan]")
            console.print(f"  Max total symbols: [cyan]{limits_info['max_total_symbols']:,}[/cyan]")
            console.print(f"  Max index size: [cyan]{limits_info['max_index_size_mb']}MB[/cyan]")
            console.print(f"  Max vectors: [cyan]{limits_info['max_vectors']:,}[/cyan]")
            console.print(f"  Min free disk: [cyan]{limits_info['min_free_disk_mb']}MB[/cyan]")
            console.print(f"  Warn threshold: [cyan]{int(limits_info['warn_threshold'] * 100)}%[/cyan]")
            console.print("")
            console.print("[dim]Override with env vars: CERBERUS_MAX_TOTAL_SYMBOLS, CERBERUS_MAX_FILE_BYTES, etc.[/dim]")
        return

    # Apply CLI overrides to limits config via env vars (takes precedence)
    if max_bytes is not None:
        os.environ["CERBERUS_MAX_FILE_BYTES"] = str(max_bytes)
        reset_limits_config()  # Force reload
    if max_symbols_per_file is not None:
        os.environ["CERBERUS_MAX_SYMBOLS_PER_FILE"] = str(max_symbols_per_file)
        reset_limits_config()
    if max_total_symbols is not None:
        os.environ["CERBERUS_MAX_TOTAL_SYMBOLS"] = str(max_total_symbols)
        reset_limits_config()
    if strict:
        os.environ["CERBERUS_LIMITS_STRICT"] = "true"
        reset_limits_config()

    # Use new default path if not specified
    if output is None:
        output = _get_default_index_output()

    respect_gitignore = not no_gitignore

    try:
        scan_result = build_index(
            directory,
            output,
            respect_gitignore=respect_gitignore,
            extensions=ext,
            incremental=incremental,
            store_embeddings=store_embeddings,
            model_name=model_name,
            max_bytes=max_bytes,
            skip_preflight=skip_preflight,
        )
    except PreflightError as e:
        console.print(f"[bold red]Pre-flight check failed:[/bold red] {e}")
        console.print("[dim]Use --skip-preflight to bypass (not recommended)[/dim]")
        raise typer.Exit(code=1)

    if json_output:
        payload = {
            "index_path": str(output),
            "total_files": scan_result.total_files,
            "total_symbols": len(scan_result.symbols),
            "scan_duration": scan_result.scan_duration,
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    console.print(f"Indexed [bold blue]{scan_result.total_files}[/bold blue] files and [bold green]{len(scan_result.symbols)}[/bold green] symbols to [bold]{output}[/bold].")
