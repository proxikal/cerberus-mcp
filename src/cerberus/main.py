import json
import typer
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from cerberus.logging_config import logger
from cerberus.schemas import ScanResult
from cerberus.scanner import scan as perform_scan
from cerberus.benchmark import run_benchmark
from cerberus.index import (
    build_index,
    load_index,
    compute_stats,
    find_symbol,
    read_range,
    semantic_search,
)

app = typer.Typer()
console = Console()

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
    typer.echo("Cerberus v0.1.0 (Aegis Foundation)")

@app.command()
def doctor():
    """
    Runs a diagnostic check on the Cerberus environment.
    """
    logger.info("Running diagnostic checks...")
    typer.echo("🩺 Running Cerberus Doctor...")
    # Placeholder for future checks
    typer.secho("✅ System appears healthy.", fg=typer.colors.GREEN)

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
        "cerberus_index.json", "--output", "-o", help="Path to save the index file."
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
    Runs a scan and writes the results to a JSON index.
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

@app.command()
def stats(
    index_path: Path = typer.Option(
        "cerberus_index.json",
        "--index",
        "-i",
        help="Path to a previously generated index file.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output results as JSON for agents."
    ),
):
    """
    Displays summary statistics for an existing index.
    """
    scan_result = load_index(index_path)
    stats = compute_stats(scan_result)

    if json_output:
        typer.echo(json.dumps(stats.model_dump(), indent=2))
        return

    summary = Table(title=f"Index Stats for '{index_path}'")
    summary.add_column("Metric", style="cyan", no_wrap=True)
    summary.add_column("Value", style="magenta")
    summary.add_row("Total Files", str(stats.total_files))
    summary.add_row("Total Symbols", str(stats.total_symbols))
    summary.add_row("Avg Symbols/File", f"{stats.average_symbols_per_file:.2f}")

    breakdown = Table(title="Symbol Types Breakdown")
    breakdown.add_column("Type", style="green", no_wrap=True)
    breakdown.add_column("Count", style="yellow")
    for symbol_type, count in stats.symbol_types.items():
        breakdown.add_row(symbol_type, str(count))

    console.print(summary)
    console.print(breakdown)

@app.command("get-symbol")
def get_symbol(
    name: str = typer.Argument(..., help="Name of the symbol to retrieve."),
    index_path: Path = typer.Option(
        "cerberus_index.json",
        "--index",
        "-i",
        help="Path to a previously generated index file.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    padding: int = typer.Option(
        3, "--padding", "-p", help="Number of context lines to include before/after the symbol."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output results as JSON for agents."
    ),
):
    """
    Retrieves code for a symbol from the index with minimal context.
    """
    scan_result = load_index(index_path)
    matches = find_symbol(name, scan_result)

    if not matches:
        console.print(f"[red]No symbol named '{name}' found in index '{index_path}'.[/red]")
        raise typer.Exit(code=1)

    enriched = []
    for symbol in matches:
        snippet = read_range(Path(symbol.file_path), symbol.start_line, symbol.end_line, padding=padding)
        enriched.append({"symbol": symbol.model_dump(), "snippet": snippet.model_dump()})

    if json_output:
        typer.echo(json.dumps(enriched, indent=2))
        return

    table = Table(title=f"Matches for '{name}'")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="green")
    table.add_column("File", style="magenta")
    table.add_column("Lines", style="yellow")

    for item in enriched:
        symbol = item["symbol"]
        table.add_row(
            symbol["name"],
            symbol["type"],
            symbol["file_path"],
            f"{symbol['start_line']}-{symbol['end_line']}",
        )

    console.print(table)

    for item in enriched:
        snippet = item["snippet"]
        console.print(f"[bold]Context ({snippet['start_line']}-{snippet['end_line']})[/bold]:\n{snippet['content']}")

@app.command()
def search(
    query: str = typer.Argument(..., help="Natural language search query."),
    index_path: Path = typer.Option(
        "cerberus_index.json",
        "--index",
        "-i",
        help="Path to a previously generated index file.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    limit: int = typer.Option(5, "--limit", "-k", help="Number of results to return."),
    padding: int = typer.Option(3, "--padding", "-p", help="Context lines to include in snippets."),
    min_score: float = typer.Option(0.2, "--min-score", help="Minimum score threshold for results."),
    embeddings: bool = typer.Option(
        True,
        "--embeddings/--no-embeddings",
        help="Use transformer embeddings (default) or fallback token similarity only.",
    ),
    backend: str = typer.Option(
        "memory",
        "--backend",
        help="Vector backend: memory (default) or faiss (optional, if installed).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON for agents."),
):
    """
    Performs a lightweight semantic search over indexed symbols.
    """
    results = semantic_search(
        query,
        index_path,
        limit=limit,
        padding=padding,
        min_score=min_score,
        use_embeddings=embeddings,
        backend=backend,
    )

    if not results:
        if json_output:
            typer.echo("[]")
            return
        console.print(f"[red]No results found for query '{query}'.[/red]")
        return

    response = []
    for res in results:
        response.append(
            {
                "score": res.score,
                "symbol": res.symbol.model_dump(),
                "snippet": res.snippet.model_dump(),
            }
        )

    if json_output:
        typer.echo(json.dumps(response, indent=2))
        return

    table = Table(title=f"Search results for '{query}'")
    table.add_column("Score", justify="right", style="yellow")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="green")
    table.add_column("File", style="magenta")
    table.add_column("Lines", style="white")

    for res in response:
        sym = res["symbol"]
        table.add_row(
            f"{res['score']:.3f}",
            sym["name"],
            sym["type"],
            sym["file_path"],
            f"{sym['start_line']}-{sym['end_line']}",
        )

    console.print(table)

    for res in response:
        snippet = res["snippet"]
        console.print(f"[bold]Context ({snippet['start_line']}-{snippet['end_line']})[/bold]:\n{snippet['content']}")

@app.command()
def bench(
    directory: Path = typer.Argument(
        ".", help="Directory to benchmark.", exists=True, file_okay=False, readable=True
    ),
    query: str = typer.Option(
        "example", "--query", "-q", help="Query to use for semantic search benchmark."
    ),
    output: Path = typer.Option(
        "cerberus_index.json",
        "--output",
        "-o",
        help="Path to write/read the benchmark index.",
    ),
    ext: Optional[List[str]] = typer.Option(
        None, "--ext", help="File extensions to include (e.g., .py, .md). Can be used multiple times."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON for agents."),
):
    """
    Runs a lightweight benchmark for indexing and semantic search.
    """
    metrics = run_benchmark(directory, output, query, extensions=ext)

    if json_output:
        typer.echo(json.dumps(metrics, indent=2))
        return

    table = Table(title="Benchmark Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    for key, value in metrics.items():
        table.add_row(key, f"{value:.4f}" if isinstance(value, float) else str(value))
    console.print(table)


if __name__ == "__main__":
    app()
