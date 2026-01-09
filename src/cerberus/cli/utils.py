"""
Utility commands for Cerberus CLI.

This module contains standalone utility commands that don't fit other categories:
- stats: Index statistics display
- bench: Performance benchmarking
- generate-tools: Manifest generation
- summarize: LLM-based code summarization
- verify-context: CERBERUS.md verification
- generate-context: CERBERUS.md generation

Extracted from main.py as part of Phase 7 Track B CLI de-monolithization.
"""

import json
import typer
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.markup import escape

from cerberus.logging_config import logger
from cerberus.index import load_index, compute_stats
from cerberus.benchmark import run_benchmark
from .output import get_console

app = typer.Typer()
console = get_console()


@app.command()
def stats(
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to a previously generated index file. Defaults to 'cerberus.db' in CWD.",
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
    # Default to cerberus.db in CWD if not provided
    if index_path is None:
        index_path = Path("cerberus.db")
        if not index_path.exists():
            console.print(f"[red]Error: Index file 'cerberus.db' not found in current directory.[/red]")
            console.print(f"[dim]Run 'cerberus index .' first or provide --index path.[/dim]")
            raise typer.Exit(code=1)

    scan_result = load_index(index_path)
    stats = compute_stats(scan_result)

    if json_output:
        payload = stats.model_dump()
        payload["imports"] = [imp.model_dump() for imp in scan_result.imports]
        payload["calls"] = [c.model_dump() for c in scan_result.calls]
        payload["type_infos"] = [t.model_dump() for t in scan_result.type_infos]
        payload["import_links"] = [il.model_dump() for il in scan_result.import_links]
        typer.echo(json.dumps(payload, indent=2))
        return

    summary = Table(title=f"Index Stats for '{index_path}'")
    summary.add_column("Metric", style="cyan", no_wrap=True)
    summary.add_column("Value", style="magenta")
    summary.add_row("Total Files", str(stats.total_files))
    summary.add_row("Total Symbols", str(stats.total_symbols))
    summary.add_row("Avg Symbols/File", f"{stats.average_symbols_per_file:.2f}")
    summary.add_row("Total Imports", str(len(scan_result.imports)))
    summary.add_row("Total Calls", str(len(scan_result.calls)))
    summary.add_row("Type Info Entries", str(len(scan_result.type_infos)))
    summary.add_row("Import Links", str(len(scan_result.import_links)))

    breakdown = Table(title="Symbol Types Breakdown")
    breakdown.add_column("Type", style="green", no_wrap=True)
    breakdown.add_column("Count", style="yellow")
    for symbol_type, count in stats.symbol_types.items():
        breakdown.add_row(symbol_type, str(count))

    console.print(summary)
    console.print(breakdown)


@app.command()
def bench(
    directory: Path = typer.Argument(
        ".", help="Directory to benchmark.", exists=True, file_okay=False, readable=True
    ),
    query: str = typer.Option(
        "example", "--query", "-q", help="Query to use for semantic search benchmark."
    ),
    output: Path = typer.Option(
        "cerberus.db",
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


@app.command("generate-tools")
def generate_tools(
    output: Path = typer.Option("tools.json", "--output", "-o", help="Path to write the tools manifest."),
    json_output: bool = typer.Option(False, "--json", help="Print manifest as JSON instead of writing file."),
):
    """
    Generates a tools.json manifest for agent integrations.
    """
    from cerberus.manifest import generate_manifest

    manifest_path = generate_manifest(output)

    if json_output:
        typer.echo(Path(manifest_path).read_text())
    else:
        console.print(f"Generated tools manifest at [bold]{manifest_path}[/bold].")


@app.command("summarize")
def summarize(
    target: str = typer.Argument(..., help="File path or symbol name to summarize."),
    summary_type: str = typer.Option(
        "auto", "--type", "-t", help="Summary type: auto, file, symbol, architecture, layer"
    ),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file (required for symbol/architecture summaries). Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [LOW PRIORITY - OPTIONAL] Summarize code using local LLM (Phase 2).

    NOTE: This is a low-priority optional feature. Cerberus is designed to provide
    context TO AI agents, not to use LLMs itself. Most users will not need this.

    Requires ollama to be running locally.
    """
    from cerberus.summarization import get_summarization_facade
    from cerberus.index import load_index

    facade = get_summarization_facade()

    # Default to cerberus.db in CWD if not provided and needed
    if index_path is None:
        default_db = Path("cerberus.db")
        if default_db.exists():
            index_path = default_db

    # Auto-detect type
    if summary_type == "auto":
        target_path = Path(target)
        if target_path.exists():
            summary_type = "file"
        elif index_path and index_path.exists():
            summary_type = "symbol"
        else:
            console.print("[red]Cannot auto-detect summary type. Specify --type or provide --index for symbols.[/red]")
            raise typer.Exit(code=1)

    try:
        summary = None

        if summary_type == "file":
            target_path = Path(target)
            if not target_path.exists():
                console.print(f"[red]File not found: {target}[/red]")
                raise typer.Exit(code=1)
            summary = facade.summarize_file(str(target_path))

        elif summary_type == "symbol":
            if not index_path or not index_path.exists():
                console.print("[red]--index required for symbol summaries (and cerberus.db not found)[/red]")
                raise typer.Exit(code=1)

            scan_result = load_index(index_path)
            target_symbol = next(
                (s for s in scan_result.symbols if s.name == target),
                None
            )

            if not target_symbol:
                console.print(f"[red]Symbol '{target}' not found in index.[/red]")
                raise typer.Exit(code=1)

            summary = facade.summarize_symbol(target_symbol, scan_result)

        elif summary_type in ["architecture", "layer"]:
            console.print("[yellow]Architecture/layer summarization not yet fully implemented.[/yellow]")
            raise typer.Exit(code=1)

        if not summary:
            console.print("[yellow]LLM not available or summarization failed. Ensure ollama is running.[/yellow]")
            raise typer.Exit(code=1)

        if json_output:
            typer.echo(json.dumps(summary.model_dump(), indent=2))
            return

        # Pretty print summary
        console.print(f"\n[bold]Summary of {summary.target}[/bold]")
        console.print(f"Type: {summary.summary_type}")
        console.print(f"Model: {summary.model_used}\n")
        console.print(f"[cyan]Purpose:[/cyan]\n{summary.summary_text}\n")

        if summary.key_points:
            console.print("[cyan]Key Points:[/cyan]")
            for point in summary.key_points:
                console.print(f"  • {point}")
            console.print()

        if summary.dependencies:
            console.print(f"[cyan]Dependencies:[/cyan] {', '.join(summary.dependencies)}\n")

        if summary.complexity_score:
            console.print(f"[cyan]Complexity:[/cyan] {summary.complexity_score}/10\n")

    except Exception as e:
        logger.error(f"Failed to summarize: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        raise typer.Exit(code=1)


@app.command("verify-context")
def verify_context(
    context_file: Path = typer.Option("CERBERUS.md", "--file", "-f", help="Path to context file to verify."),
    fix: bool = typer.Option(False, "--fix", help="Auto-fix discrepancies by regenerating CERBERUS.md."),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
):
    """
    Verify CERBERUS.md matches actual codebase state.

    Checks version, test counts, phase status, architecture compliance.
    Use --fix to regenerate CERBERUS.md if discrepancies found.

    Examples:
      cerberus verify-context
      cerberus verify-context --fix
      cerberus verify-context --json
    """
    from cerberus.context_verification import verify_context_file

    result = verify_context_file(context_file)

    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return

    # Display results
    console.print(f"\n[bold]Verifying {context_file}[/bold]\n")

    if result["valid"]:
        console.print("[green]✓ Context file is valid and up-to-date![/green]")
    else:
        console.print("[red]✗ Context file has discrepancies:[/red]\n")
        for issue in result["issues"]:
            console.print(f"  [yellow]•[/yellow] {issue}")

    console.print(f"\n[dim]Checks performed: {result['checks_performed']}[/dim]")

    if not result["valid"] and fix:
        console.print("\n[yellow]Running generate-context to fix...[/yellow]")
        from cerberus.context_verification import generate_context_file
        generate_context_file(context_file)
        console.print(f"[green]✓ {context_file} regenerated![/green]")
    elif not result["valid"]:
        console.print("\n[dim]Run with --fix to auto-regenerate CERBERUS.md[/dim]")
        raise typer.Exit(code=1)


@app.command("generate-context")
def generate_context(
    output: Path = typer.Option("CERBERUS.md", "--output", "-o", help="Path to write context file."),
    json_output: bool = typer.Option(False, "--json", help="Output generated data as JSON instead of writing file."),
):
    """
    Generate fresh CERBERUS.md from current codebase state.

    Scans codebase using Cerberus's own tools to extract:
    - Version, phase status, test counts
    - Architecture compliance, command counts
    - Performance metrics

    Examples:
      cerberus generate-context
      cerberus generate-context --output CERBERUS_NEW.md
      cerberus generate-context --json
    """
    from cerberus.context_verification import generate_context_file, collect_context_data

    data = collect_context_data()

    if json_output:
        typer.echo(json.dumps(data, indent=2))
        return

    generate_context_file(output, data)
    console.print(f"[green]✓ Generated {output}[/green]")
    console.print(f"[dim]Version: {data['version']} | Tests: {data['tests_passed']}/{data['tests_total']} | Commands: {data['command_count']}[/dim]")


@app.command()
def schema(
    command: Optional[str] = typer.Argument(None, help="Command name to introspect (e.g., 'get-symbol', 'scan')"),
    list_commands: bool = typer.Option(False, "--list", "-l", help="List all available commands"),
):
    """
    [PHASE 10] Introspect command schemas for agent usage.

    Returns JSON schema for command arguments and options, enabling
    agents to discover interfaces without hallucination.

    Examples:
      cerberus schema --list                    # List all commands
      cerberus schema get-symbol                # Schema for get-symbol
      cerberus schema scan                      # Schema for scan
    """
    from cerberus.cli.config import CLIConfig

    # Command registry - maps command names to their info
    # This is a simplified version; a full implementation would introspect typer apps
    command_registry = {
        "hello": {
            "description": "Basic check to ensure CLI is working",
            "arguments": [],
            "options": []
        },
        "version": {
            "description": "Prints the current version of Cerberus",
            "arguments": [],
            "options": []
        },
        "doctor": {
            "description": "Runs a diagnostic check on the Cerberus environment",
            "arguments": [],
            "options": [
                {"name": "--index", "short": "-i", "type": "Path", "required": False, "help": "Path to index file to validate"},
                {"name": "--json", "type": "bool", "default": False, "help": "Output results as JSON"}
            ]
        },
        "scan": {
            "description": "Scans a directory to build a symbol index",
            "arguments": [
                {"name": "root_dir", "type": "Path", "required": True, "help": "Root directory to scan"}
            ],
            "options": [
                {"name": "--output", "short": "-o", "type": "Path", "required": False, "help": "Output file path for the index"},
                {"name": "--json", "type": "bool", "default": False, "help": "Output scan result as JSON"}
            ]
        },
        "index": {
            "description": "Build/update index for a directory",
            "arguments": [
                {"name": "root_dir", "type": "Path", "required": True, "help": "Root directory to index"}
            ],
            "options": [
                {"name": "--output", "short": "-o", "type": "Path", "required": False, "help": "Output file path"},
                {"name": "--no-incremental", "type": "bool", "default": False, "help": "Force full rebuild"}
            ]
        },
        "get-symbol": {
            "description": "Retrieves code for a symbol from the index",
            "arguments": [
                {"name": "name", "type": "str", "required": False, "help": "Name of the symbol to retrieve"}
            ],
            "options": [
                {"name": "--index", "short": "-i", "type": "Path", "required": False, "help": "Path to index file"},
                {"name": "--padding", "short": "-p", "type": "int", "default": 3, "help": "Context lines before/after"},
                {"name": "--skeleton", "type": "bool", "default": False, "help": "Return skeletonized view"},
                {"name": "--json", "type": "bool", "default": False, "help": "Output as JSON"},
                {"name": "--fuzzy", "type": "bool", "default": False, "help": "Enable fuzzy matching"},
                {"name": "--file", "type": "str", "required": False, "help": "Show all symbols in file"},
                {"name": "--type", "type": "str", "required": False, "help": "Filter by symbol type"},
                {"name": "--auto-hydrate", "type": "bool", "default": False, "help": "Auto-fetch referenced types"}
            ],
            "output_schema": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "object", "description": "Symbol metadata"},
                    "snippet": {"type": "object", "description": "Code snippet with context"},
                    "callers": {"type": "array", "description": "List of call sites"},
                    "imports": {"type": "array", "description": "Import information"}
                }
            }
        },
        "search": {
            "description": "Search for symbols using keyword or semantic search",
            "arguments": [
                {"name": "query", "type": "str", "required": True, "help": "Search query"}
            ],
            "options": [
                {"name": "--index", "short": "-i", "type": "Path", "required": False, "help": "Path to index file"},
                {"name": "--mode", "type": "str", "default": "keyword", "help": "Search mode: keyword or semantic"},
                {"name": "--top-k", "type": "int", "default": 10, "help": "Number of results to return"},
                {"name": "--json", "type": "bool", "default": False, "help": "Output as JSON"}
            ]
        }
    }

    if list_commands:
        # List all available commands
        result = {
            "commands": list(command_registry.keys()),
            "count": len(command_registry)
        }
        print(json.dumps(result, indent=2 if not CLIConfig.is_machine_mode() else None))
        return

    if not command:
        console.print("[red]Error: Provide a command name or use --list[/red]")
        console.print("Example: cerberus schema get-symbol")
        raise typer.Exit(code=1)

    # Look up command schema
    if command not in command_registry:
        from cerberus.cli.output import structured_error
        if CLIConfig.is_machine_mode():
            error = structured_error(
                code="COMMAND_NOT_FOUND",
                message=f"Command '{command}' not found",
                input_value=command,
                suggestions=list(command_registry.keys())[:5],
                actionable_fix="cerberus schema --list"
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: Command '{command}' not found[/red]")
            console.print(f"[dim]Use 'cerberus schema --list' to see available commands[/dim]")
        raise typer.Exit(code=1)

    # Return command schema
    schema_data = command_registry[command]
    print(json.dumps(schema_data, indent=2 if not CLIConfig.is_machine_mode() else None))


@app.command()
def batch(
    file: Path = typer.Option(..., "--file", "-f", help="JSON file containing batch requests", exists=True, readable=True),
    parallel: bool = typer.Option(True, "--parallel/--sequential", "-p", help="Execute requests in parallel (default: parallel)"),
    workers: int = typer.Option(4, "--workers", "-w", help="Number of parallel workers (default: 4)"),
    index_path: Optional[Path] = typer.Option(
        None, "--index", "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
    ),
):
    """
    [PHASE 10] Execute multiple commands atomically from a JSON file.

    Direct in-process execution with thread pool parallelism.
    Zero daemon dependency - loads index ONCE and executes all queries locally.
    SQLite handles concurrent read access safely.

    JSON format:
      {
        "requests": [
          {"command": "get-symbol", "args": {"name": "MyClass"}},
          {"command": "search", "args": {"query": "parser", "mode": "keyword"}}
        ]
      }

    Supported commands: get-symbol, search, stats, deps, calls, references

    Examples:
      cerberus batch --file commands.json              # Parallel (default)
      cerberus batch --file commands.json --sequential # Sequential
      cerberus batch --file commands.json --workers 8  # 8 parallel workers
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from cerberus.cli.config import CLIConfig

    # Default index path
    if index_path is None:
        index_path = Path("cerberus.db")
        if not index_path.exists():
            from cerberus.cli.output import structured_error
            if CLIConfig.is_machine_mode():
                error = structured_error(
                    code="INDEX_NOT_FOUND",
                    message="Index file 'cerberus.db' not found in current directory",
                    actionable_fix="cerberus index ."
                )
                print(json.dumps(error, separators=(',', ':')))
            else:
                console.print("[red]Error: Index file 'cerberus.db' not found.[/red]")
                console.print("[dim]Run 'cerberus index .' first.[/dim]")
            raise typer.Exit(code=1)

    # Read batch file
    try:
        with open(file, 'r') as f:
            batch_data = json.load(f)
    except Exception as e:
        from cerberus.cli.output import structured_error
        if CLIConfig.is_machine_mode():
            error = structured_error(
                code="BATCH_FILE_ERROR",
                message=f"Failed to read batch file: {str(e)}",
                input_value=str(file)
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error reading batch file: {e}[/red]")
        raise typer.Exit(code=1)

    if "requests" not in batch_data or not isinstance(batch_data["requests"], list):
        from cerberus.cli.output import structured_error
        if CLIConfig.is_machine_mode():
            error = structured_error(
                code="INVALID_BATCH_FORMAT",
                message="Batch file must contain 'requests' array",
                input_value=str(file)
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print("[red]Error: Batch file must contain 'requests' array[/red]")
        raise typer.Exit(code=1)

    batch_requests = batch_data["requests"]

    # Load index ONCE into memory - all queries share this
    try:
        scan_result = load_index(index_path)
    except Exception as e:
        from cerberus.cli.output import structured_error
        if CLIConfig.is_machine_mode():
            error = structured_error(
                code="INDEX_LOAD_ERROR",
                message=f"Failed to load index: {str(e)}",
                input_value=str(index_path)
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error loading index: {e}[/red]")
        raise typer.Exit(code=1)

    # ========== Command Handlers (in-process execution) ==========
    from .batch_handlers import BATCH_HANDLERS as HANDLERS

    # ========== Request Execution ==========

    def execute_request(idx: int, req: dict) -> dict:
        """Execute a single request and return result."""
        if "command" not in req:
            return {
                "index": idx,
                "success": False,
                "error": "Missing 'command' field",
            }

        command = req["command"]
        args = req.get("args", {})

        handler = HANDLERS.get(command)
        if not handler:
            return {
                "index": idx,
                "command": command,
                "success": False,
                "error": f"Unknown command: {command}. Supported: {', '.join(HANDLERS.keys())}",
            }

        try:
            result = handler(args, scan_result, index_path)
            # Check if handler returned an error
            if "error" in result and len(result) == 1:
                return {
                    "index": idx,
                    "command": command,
                    "success": False,
                    "error": result["error"],
                }
            return {
                "index": idx,
                "command": command,
                "success": True,
                "result": result,
            }
        except Exception as e:
            return {
                "index": idx,
                "command": command,
                "success": False,
                "error": str(e),
            }

    # ========== Parallel or Sequential Execution ==========

    results = []

    if parallel and len(batch_requests) > 1:
        # Thread pool execution - SQLite handles concurrent reads safely
        with ThreadPoolExecutor(max_workers=min(workers, len(batch_requests))) as executor:
            futures = {
                executor.submit(execute_request, idx, req): idx
                for idx, req in enumerate(batch_requests)
            }
            for future in as_completed(futures):
                results.append(future.result())
    else:
        # Sequential execution
        for idx, req in enumerate(batch_requests):
            results.append(execute_request(idx, req))

    # Sort results by original index
    results.sort(key=lambda x: x["index"])

    # ========== Output ==========

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    output = {
        "total_requests": len(batch_requests),
        "successful": len(successful),
        "failed": len(failed),
        "results": results,
    }

    print(json.dumps(output, indent=2 if not CLIConfig.is_machine_mode() else None))