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
def doctor(
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Optional path to an index file to validate its health.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
):
    """
    Runs a diagnostic check on the Cerberus environment.
    """
    logger.info("Running diagnostic checks...")
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
    skeleton: bool = typer.Option(
        False, "--skeleton", help="Return a skeletonized view of the file instead of full context."
    ),
    show_imports: bool = typer.Option(
        False, "--show-imports", help="Display detailed import information for the symbol's file."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output results as JSON for agents."
    ),
):
    """
    Retrieves code for a symbol from the index with minimal context.
    Supports displaying import linkage with --show-imports flag.
    """
    scan_result = load_index(index_path)
    matches = find_symbol(name, scan_result)

    if not matches:
        console.print(f"[red]No symbol named '{name}' found in index '{index_path}'.[/red]")
        raise typer.Exit(code=1)

    enriched = []
    for symbol in matches:
        snippet = read_range(
            Path(symbol.file_path),
            symbol.start_line,
            symbol.end_line,
            padding=padding,
            skeleton=skeleton,
        )
        # Collect callsites referencing this symbol
        callers = [
            c.model_dump()
            for c in scan_result.calls
            if c.callee == symbol.name
        ]

        # Phase 1.3: Collect import links for this symbol's file
        import_info = []
        if show_imports:
            import_info = [
                il.model_dump()
                for il in scan_result.import_links
                if il.importer_file == symbol.file_path
            ]

        enriched.append(
            {
                "symbol": symbol.model_dump(),
                "snippet": snippet.model_dump(),
                "callers": callers,
                "imports": import_info if show_imports else [],
            }
        )

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

        if item.get("callers"):
            caller_table = Table(title="Callers")
            caller_table.add_column("File", style="cyan")
            caller_table.add_column("Line", style="yellow")
            for call in item["callers"]:
                caller_table.add_row(call["caller_file"], str(call["line"]))
            console.print(caller_table)

        if show_imports and item.get("imports"):
            import_table = Table(title="Imports in this file")
            import_table.add_column("Module", style="green")
            import_table.add_column("Symbols", style="cyan")
            import_table.add_column("Line", style="yellow")
            for imp in item["imports"]:
                symbols_str = ", ".join(imp["imported_symbols"]) if imp["imported_symbols"] else "(all)"
                import_table.add_row(imp["imported_module"], symbols_str, str(imp["import_line"]))
            console.print(import_table)

@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (keyword or natural language)."),
    index_path: Path = typer.Option(
        "cerberus_index.json",
        "--index",
        "-i",
        help="Path to a previously generated index file.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    mode: str = typer.Option(
        "auto",
        "--mode",
        "-m",
        help="Search mode: auto (default), keyword, semantic, or balanced.",
    ),
    limit: int = typer.Option(10, "--limit", "-k", help="Number of results to return."),
    padding: int = typer.Option(3, "--padding", "-p", help="Context lines to include in snippets."),
    keyword_weight: Optional[float] = typer.Option(
        None,
        "--keyword-weight",
        help="Weight for keyword scores (0-1, for balanced mode)."
    ),
    semantic_weight: Optional[float] = typer.Option(
        None,
        "--semantic-weight",
        help="Weight for semantic scores (0-1, for balanced mode)."
    ),
    fusion_method: str = typer.Option(
        "rrf",
        "--fusion",
        help="Fusion method: rrf (Reciprocal Rank Fusion) or weighted.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON for agents."),
):
    """
    [ENHANCED - CORE FEATURE] Hybrid search combining BM25 keyword and vector semantic search (Phase 3).

    Automatically detects query type and uses the best search strategy:
    - Keyword queries (e.g., "MyClass", "get_user_data") → BM25 exact matching
    - Semantic queries (e.g., "code that handles authentication") → Vector search
    - Balanced mode → Combines both with intelligent ranking fusion

    Examples:
      cerberus search "DatabaseConnection"              # Auto-detects keyword
      cerberus search "authentication logic"            # Auto-detects semantic
      cerberus search "user" --mode balanced            # Force hybrid mode
      cerberus search "auth" --keyword-weight 0.7       # Emphasize keywords
    """
    from cerberus.retrieval import hybrid_search

    try:
        # Validate mode
        if mode not in ["auto", "keyword", "semantic", "balanced"]:
            console.print(f"[red]Invalid mode '{mode}'. Use: auto, keyword, semantic, or balanced.[/red]")
            raise typer.Exit(code=1)

        # Validate fusion method
        if fusion_method not in ["rrf", "weighted"]:
            console.print(f"[red]Invalid fusion method '{fusion_method}'. Use: rrf or weighted.[/red]")
            raise typer.Exit(code=1)

        # Perform hybrid search
        results = hybrid_search(
            query=query,
            index_path=index_path,
            mode=mode,
            top_k=limit,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight,
            fusion_method=fusion_method,
            padding=padding,
        )

        if not results:
            if json_output:
                typer.echo("[]")
                return
            console.print(f"[red]No results found for query '{query}'.[/red]")
            return

        # Prepare response
        response = []
        for res in results:
            response.append(
                {
                    "rank": res.rank,
                    "hybrid_score": res.hybrid_score,
                    "bm25_score": res.bm25_score,
                    "vector_score": res.vector_score,
                    "match_type": res.match_type,
                    "symbol": res.symbol.model_dump(),
                }
            )

        if json_output:
            typer.echo(json.dumps(response, indent=2))
            return

        # Display results
        table = Table(title=f"Hybrid Search: '{query}' (mode: {mode})")
        table.add_column("Rank", justify="right", style="white")
        table.add_column("Score", justify="right", style="yellow")
        table.add_column("Type", justify="center", style="dim")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Symbol Type", style="green")
        table.add_column("File", style="magenta")
        table.add_column("Lines", style="white")

        for res in response:
            sym = res["symbol"]
            # Create match type indicator
            match_indicator = {
                "keyword": "🔤",
                "semantic": "🧠",
                "both": "⚡"
            }.get(res["match_type"], "•")

            table.add_row(
                str(res["rank"]),
                f"{res['hybrid_score']:.3f}",
                match_indicator,
                sym["name"],
                sym["type"],
                sym["file_path"],
                f"{sym['start_line']}-{sym['end_line']}",
            )

        console.print(table)

        # Show score breakdown for top result
        if results:
            top = response[0]
            console.print(f"\n[dim]Top result score breakdown:[/dim]")
            console.print(f"  BM25 (keyword): {top['bm25_score']:.3f}")
            console.print(f"  Vector (semantic): {top['vector_score']:.3f}")
            console.print(f"  Hybrid (fused): {top['hybrid_score']:.3f}")
            console.print(f"  Match type: {top['match_type']}")

    except Exception as e:
        logger.error(f"Search failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)

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


@app.command("skeleton-file")
def skeleton_file(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="File to skeletonize."),
    json_output: bool = typer.Option(False, "--json", help="Output skeleton as JSON."),
):
    """
    Outputs a skeletonized view (signatures/docstrings) of a file.
    """
    snippet = read_range(file, 1, 10_000_000, skeleton=True)

    if json_output:
        typer.echo(json.dumps(snippet.model_dump(), indent=2))
        return

    console.print(f"[bold]Skeleton for {file}[/bold]:\n{snippet.content}")


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


@app.command("deps")
def deps(
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Symbol name to inspect callers for."),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File to list imports for."),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Build recursive call graph for symbol (requires --symbol)."),
    depth: int = typer.Option(3, "--depth", "-d", help="Maximum depth for recursive call graph (default: 3)."),
    index_path: Path = typer.Option(
        "cerberus_index.json",
        "--index",
        "-i",
        help="Path to a previously generated index file.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
):
    """
    Display dependency info: callers for a symbol and imports for a file.
    Supports recursive call graph analysis with --recursive flag.
    """
    scan_result = load_index(index_path)
    response: dict = {}

    if symbol:
        if recursive:
            # Build recursive call graph
            from cerberus.graph import build_recursive_call_graph, format_call_graph

            graph_result = build_recursive_call_graph(symbol, scan_result, max_depth=depth)

            if json_output:
                response["symbol"] = symbol
                response["recursive"] = True
                response["graph"] = graph_result.model_dump()
                typer.echo(json.dumps(response, indent=2))
                return
            else:
                formatted_graph = format_call_graph(graph_result)
                console.print(formatted_graph)
                return
        else:
            # Simple caller list (non-recursive)
            callers = [
                c.model_dump()
                for c in scan_result.calls
                if c.callee == symbol
            ]
            response["symbol"] = symbol
            response["callers"] = callers

    if file:
        file_imports = [
            imp.model_dump()
            for imp in scan_result.imports
            if Path(imp.file_path).name == file.name
        ]
        response["file"] = str(file)
        response["imports"] = file_imports

    if json_output:
        typer.echo(json.dumps(response, indent=2))
        return

    if symbol and not recursive:
        table = Table(title=f"Callers for '{symbol}'")
        table.add_column("File", style="cyan")
        table.add_column("Line", style="yellow")
        for c in response.get("callers", []):
            table.add_row(c["caller_file"], str(c["line"]))
        console.print(table)

    if file:
        table = Table(title=f"Imports in '{file}'")
        table.add_column("Module", style="green")
        table.add_column("Line", style="yellow")
        for imp in response.get("imports", []):
            table.add_row(imp["module"], str(imp["line"]))
        console.print(table)


# ===== Phase 2: Context Synthesis & Compaction Commands =====

@app.command("skeletonize")
def skeletonize_cmd(
    file_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="File to skeletonize."),
    preserve: Optional[List[str]] = typer.Option(
        None, "--preserve", "-p", help="Symbol names to preserve (not skeletonize). Can be used multiple times."
    ),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file for skeleton (defaults to stdout)."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [CORE FEATURE] Skeletonize a source file using AST-aware pruning (Phase 2).
    Removes function bodies while keeping signatures, docstrings, and type annotations.
    """
    from cerberus.synthesis import skeletonize_file

    try:
        skeleton = skeletonize_file(str(file_path), preserve_symbols=preserve or [])

        if json_output:
            typer.echo(json.dumps(skeleton.model_dump(), indent=2))
            return

        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(skeleton.content)
            console.print(f"[green]Skeleton written to {output}[/green]")
            console.print(f"Compression: {skeleton.compression_ratio:.1%} ({skeleton.original_lines} → {skeleton.skeleton_lines} lines)")
        else:
            console.print(f"[bold]Skeleton for {file_path}[/bold]")
            console.print(f"Compression: {skeleton.compression_ratio:.1%} ({skeleton.original_lines} → {skeleton.skeleton_lines} lines)")
            console.print(skeleton.content)

    except Exception as e:
        logger.error(f"Failed to skeletonize {file_path}: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("get-context")
def get_context(
    symbol_name: str = typer.Argument(..., help="Symbol name to get context for."),
    index_path: Path = typer.Option(
        "cerberus_index.json",
        "--index",
        "-i",
        help="Path to index file.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    include_callers: bool = typer.Option(True, "--callers/--no-callers", help="Include recursive call graph."),
    max_depth: int = typer.Option(2, "--depth", "-d", help="Maximum call graph depth."),
    max_tokens: Optional[int] = typer.Option(None, "--max-tokens", "-t", help="Maximum token budget for payload."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [CORE FEATURE] Get synthesized context payload for a symbol (Phase 2).
    Combines target implementation, skeleton context, and resolved imports.
    """
    from cerberus.index import load_index
    from cerberus.synthesis import get_synthesis_facade

    try:
        # Load index
        scan_result = load_index(index_path)

        # Get synthesis facade
        facade = get_synthesis_facade()

        # Build payload
        payload = facade.get_context_for_symbol(
            symbol_name=symbol_name,
            scan_result=scan_result,
            include_callers=include_callers,
            max_depth=max_depth,
            max_tokens=max_tokens
        )

        if not payload:
            console.print(f"[red]Symbol '{symbol_name}' not found in index.[/red]")
            raise typer.Exit(code=1)

        if json_output:
            typer.echo(json.dumps(payload.model_dump(), indent=2))
            return

        # Format for human readability
        formatted = facade.format_payload_for_agent(payload)
        console.print(formatted)

    except Exception as e:
        logger.error(f"Failed to build context payload: {e}")
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


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
        help="Path to index file (required for symbol/architecture summaries).",
        exists=True,
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

    # Auto-detect type
    if summary_type == "auto":
        target_path = Path(target)
        if target_path.exists():
            summary_type = "file"
        elif index_path:
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
            if not index_path:
                console.print("[red]--index required for symbol summaries[/red]")
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
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("update")
def update(
    index_path: Path = typer.Option(
        "cerberus_index.json",
        "--index",
        "-i",
        help="Path to index file to update.",
        exists=True,
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
        console.print(f"[red]Error: {e}[/red]")
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
    index_path: Path = typer.Option(
        "cerberus_index.json",
        "--index",
        "-i",
        help="Path to index file.",
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
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
