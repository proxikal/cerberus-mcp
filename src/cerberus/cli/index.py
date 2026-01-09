"""
CLI Index Commands

Commands for scanning and indexing codebases.
"""

import json
import typer
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from cerberus.scanner import scan as perform_scan
from cerberus.index import build_index

app = typer.Typer()
console = Console()


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
    output: Path = typer.Option(
        "cerberus.db", "--output", "-o", help="Path to save the index file."
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
        False, "--store-embeddings/--no-store-embeddings", help="Persist embeddings in the index for faster search."
    ),
    model_name: str = typer.Option(
        "all-MiniLM-L6-v2", "--model-name", help="Embedding model name when storing embeddings."
    ),
    max_bytes: Optional[int] = typer.Option(
        None, "--max-bytes", help="Skip files larger than this size (in bytes)."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output results as JSON for agents."
    ),
):
    """
    Runs a scan and writes the results to a SQLite index.
    """
    respect_gitignore = not no_gitignore
    scan_result = build_index(
        directory,
        output,
        respect_gitignore=respect_gitignore,
        extensions=ext,
        incremental=incremental,
        store_embeddings=store_embeddings,
        model_name=model_name,
        max_bytes=max_bytes,
    )

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
