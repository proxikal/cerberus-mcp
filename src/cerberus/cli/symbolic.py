"""
CLI Symbolic Commands

deps, calls, references, resolution-stats, inherit-tree, descendants, overrides, call-graph, smart-context
"""

import json
import typer
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.markup import escape

from cerberus.logging_config import logger
from cerberus.cli.config import CLIConfig
from cerberus.agent_session import record_operation
from cerberus.index import (
    load_index,
    find_symbol,
    read_range,
    semantic_search,
)
from .output import get_console
from .common import load_index_or_exit, get_default_index

app = typer.Typer()
console = get_console()

@app.command("deps")
def deps(
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Symbol name to inspect callers for."),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File to list imports for."),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Build recursive call graph for symbol (requires --symbol)."),
    depth: int = typer.Option(3, "--depth", "-d", help="Maximum depth for recursive call graph (default: 3)."),
    show_resolution: bool = typer.Option(False, "--show-resolution", help="Show Phase 5 import resolution results (requires --file)."),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to a previously generated index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON."),
):
    """
    Display dependency info: callers for a symbol and imports for a file.
    Supports recursive call graph analysis with --recursive flag.
    Use --show-resolution with --file to see Phase 5 import resolution results.
    """
    index_path = get_default_index(index_path)  # Validate path
    scan_result = load_index(index_path)
    response: dict = {}

    if symbol:
        if recursive:
            # Build recursive call graph
            from cerberus.graph import build_recursive_call_graph, format_call_graph

            graph_result = build_recursive_call_graph(symbol, scan_result, max_depth=depth)

            if CLIConfig.is_machine_mode() or json_output:
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
        if show_resolution:
            # Query import_links from SQLite (Phase 5.2)
            from cerberus.storage import open_index as open_sqlite_index
            store = open_sqlite_index(str(index_path))
            abs_file_path = str(file.absolute())

            import_links = list(store.query_import_links(filter={'importer_file': abs_file_path}))
            file_imports = [
                {
                    "module": link.imported_module,
                    "line": link.import_line,
                    "symbols": link.imported_symbols,
                    "resolved": link.definition_file is not None,
                    "definition_file": link.definition_file,
                    "definition_symbol": link.definition_symbol,
                }
                for link in import_links
            ]
        else:
            # Legacy: use scan_result imports
            file_imports = [
                imp.model_dump()
                for imp in scan_result.imports
                if Path(imp.file_path).name == file.name
            ]
        response["file"] = str(file)
        response["imports"] = file_imports
        response["show_resolution"] = show_resolution

    if CLIConfig.is_machine_mode() or json_output:
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
        if show_resolution:
            table = Table(title=f"Imports in '{file}' (with Phase 5 resolution)")
            table.add_column("Module", style="green")
            table.add_column("Symbols", style="yellow")
            table.add_column("Line", style="cyan")
            table.add_column("Resolved", style="magenta")
            table.add_column("Definition", style="dim")

            for imp in response.get("imports", []):
                resolved_str = "✅" if imp["resolved"] else "❌"
                def_str = imp["definition_file"] or "[dim]external[/dim]"
                symbols_str = ", ".join(imp["symbols"]) if imp["symbols"] else "*"
                table.add_row(
                    imp["module"],
                    symbols_str,
                    str(imp["line"]),
                    resolved_str,
                    def_str,
                )
        else:
            table = Table(title=f"Imports in '{file}'")
            table.add_column("Module", style="green")
            table.add_column("Line", style="yellow")
            for imp in response.get("imports", []):
                table.add_row(imp["module"], str(imp["line"]))
        console.print(table)


# ===== Phase 5: Symbolic Intelligence Commands =====



@app.command("calls")
def calls_cmd(
    method: Optional[str] = typer.Option(None, "--method", "-m", help="Filter by method name."),
    receiver: Optional[str] = typer.Option(None, "--receiver", "-r", help="Filter by receiver variable name."),
    receiver_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by resolved receiver type (class name)."),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Filter by file path."),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum number of results to return."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [PHASE 5.1] Query method calls extracted from the codebase.

    Find all method calls matching the specified filters. This enables AI agents
    to trace where methods are invoked and understand call patterns.

    Examples:
      cerberus calls --method step --json
      cerberus calls --receiver optimizer --json
      cerberus calls --type Adam --method step --json
      cerberus calls --file src/train.py --json
    """
    from cerberus.storage import open_index

    index_path = get_default_index(index_path)

    try:
        store = open_index(str(index_path))

        # Query with filters
        file_path_str = str(file.absolute()) if file else None
        results = list(store.query_method_calls_filtered(
            method=method,
            receiver=receiver,
            receiver_type=receiver_type,
            file_path=file_path_str,
        ))

        # Limit results
        results = results[:limit]

        if CLIConfig.is_machine_mode() or json_output:
            output = {
                "total": len(results),
                "calls": [
                    {
                        "file": call.caller_file,
                        "line": call.line,
                        "receiver": call.receiver,
                        "method": call.method,
                        "receiver_type": call.receiver_type,
                    }
                    for call in results
                ]
            }
            typer.echo(json.dumps(output, indent=2))
        else:
            if not results:
                console.print("[yellow]No method calls found matching the filters.[/yellow]")
                return

            table = Table(title=f"Method Calls ({len(results)} found)")
            table.add_column("File", style="cyan")
            table.add_column("Line", style="yellow")
            table.add_column("Call", style="green bold")
            table.add_column("Type", style="magenta")

            for call in results:
                call_str = f"{call.receiver}.{call.method}()"
                type_str = call.receiver_type or "[dim]unresolved[/dim]"
                table.add_row(
                    call.caller_file,
                    str(call.line),
                    call_str,
                    type_str,
                )

            console.print(table)

    except Exception as e:
        logger.error(f"Failed to query method calls: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        raise typer.Exit(code=1)




@app.command("references")
def references_cmd(
    source_symbol: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source symbol name."),
    target_symbol: Optional[str] = typer.Option(None, "--target", "-t", help="Filter by target symbol name."),
    reference_type: Optional[str] = typer.Option(
        None,
        "--type",
        help="Filter by reference type (method_call, instance_of, inherits, type_annotation, return_type)."
    ),
    min_confidence: Optional[float] = typer.Option(None, "--min-confidence", "-c", help="Minimum confidence score (0.0-1.0)."),
    source_file: Optional[Path] = typer.Option(None, "--source-file", help="Filter by source file path."),
    target_file: Optional[Path] = typer.Option(None, "--target-file", help="Filter by target file path."),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum number of results to return."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [PHASE 5.3] Query symbol references resolved by type tracking.

    Find references from symbol usages to their definitions. This enables AI agents
    to navigate instance→definition relationships and understand type resolution.

    Examples:
      cerberus references --source optimizer --json
      cerberus references --target Adam --type method_call --json
      cerberus references --min-confidence 0.8 --json
      cerberus references --source-file src/train.py --json
    """
    from cerberus.storage import open_index

    index_path = get_default_index(index_path)

    try:
        store = open_index(str(index_path))

        # Query with filters
        source_file_str = str(source_file.absolute()) if source_file else None
        target_file_str = str(target_file.absolute()) if target_file else None

        results = list(store.query_symbol_references_filtered(
            source_symbol=source_symbol,
            target_symbol=target_symbol,
            reference_type=reference_type,
            min_confidence=min_confidence,
            source_file=source_file_str,
            target_file=target_file_str,
        ))

        # Limit results
        results = results[:limit]

        if CLIConfig.is_machine_mode() or json_output:
            output = {
                "total": len(results),
                "references": [
                    {
                        "source_file": ref.source_file,
                        "source_line": ref.source_line,
                        "source_symbol": ref.source_symbol,
                        "reference_type": ref.reference_type,
                        "target_file": ref.target_file,
                        "target_symbol": ref.target_symbol,
                        "target_type": ref.target_type,
                        "confidence": ref.confidence,
                        "resolution_method": ref.resolution_method,
                    }
                    for ref in results
                ]
            }
            typer.echo(json.dumps(output, indent=2))
        else:
            if not results:
                console.print("[yellow]No symbol references found matching the filters.[/yellow]")
                return

            table = Table(title=f"Symbol References ({len(results)} found)")
            table.add_column("Source", style="cyan")
            table.add_column("Type", style="yellow")
            table.add_column("Target", style="green")
            table.add_column("Confidence", style="magenta")
            table.add_column("Method", style="dim")

            for ref in results:
                source_str = f"{ref.source_file}:{ref.source_line} ({ref.source_symbol})"
                target_str = f"{ref.target_symbol or 'unknown'}"
                if ref.target_type:
                    target_str += f" [{ref.target_type}]"
                confidence_str = f"{ref.confidence:.2f}"

                table.add_row(
                    source_str,
                    ref.reference_type,
                    target_str,
                    confidence_str,
                    ref.resolution_method or "unknown",
                )

            console.print(table)

    except Exception as e:
        logger.error(f"Failed to query symbol references: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        raise typer.Exit(code=1)




@app.command("resolution-stats")
def resolution_stats_cmd(
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [PHASE 5] Display Phase 5 symbolic intelligence resolution statistics.

    Shows health metrics for import resolution, type tracking, and symbol references.
    Helps agents understand the quality and coverage of Phase 5 analysis.

    Examples:
      cerberus resolution-stats --json
      cerberus resolution-stats --index project.db --json
    """
    from cerberus.storage import open_index
    from cerberus.resolution import get_resolution_stats

    index_path = get_default_index(index_path)

    try:
        store = open_index(str(index_path))
        stats = get_resolution_stats(store)

        if CLIConfig.is_machine_mode() or json_output:
            typer.echo(json.dumps(stats, indent=2))
        else:
            from rich.panel import Panel
            from rich.table import Table

            # Create stats table
            table = Table.grid(padding=(0, 2))
            table.add_column(style="cyan", justify="right")
            table.add_column(style="bold white")

            # Import resolution stats
            resolution_rate = stats["resolution_rate"] * 100
            table.add_row("Import Resolution Rate:", f"[green]{resolution_rate:.1f}%[/green]")
            table.add_row("Total Import Links:", f"{stats['total_import_links']:,}")
            table.add_row("Resolved Imports:", f"[green]{stats['resolved_import_links']:,}[/green]")
            table.add_row("Unresolved Imports:", f"[yellow]{stats['unresolved_import_links']:,}[/yellow]")
            table.add_row("", "")

            # Method call stats
            table.add_row("Total Method Calls:", f"{stats['total_method_calls']:,}")
            table.add_row("Total Symbol References:", f"{stats['total_symbol_references']:,}")

            panel = Panel(
                table,
                title="[bold magenta]Phase 5: Symbolic Intelligence Statistics[/bold magenta]",
                border_style="magenta",
                padding=(1, 2),
            )

            console.print()
            console.print(panel)
            console.print()

    except Exception as e:
        logger.error(f"Failed to get resolution stats: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        raise typer.Exit(code=1)


# ===== Phase 2: Context Synthesis & Compaction Commands =====



@app.command("inherit-tree")
def inherit_tree_cmd(
    class_name: str = typer.Argument(..., help="Class name to show inheritance tree for."),
    file_path: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="File path to disambiguate (if multiple classes with same name).",
    ),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [PHASE 6] Show inheritance hierarchy (MRO) for a class.

    Displays the Method Resolution Order (MRO) showing which base classes
    are inherited and in what order methods are resolved.

    Examples:
      cerberus inherit-tree ParserError
      cerberus inherit-tree CodeSymbol --file src/cerberus/schemas.py
    """
    from cerberus.index import load_index
    from cerberus.resolution import compute_class_mro

    index_path = get_default_index(index_path)

    try:
        scan_result = load_index(index_path)
        store = scan_result._store  # Access SQLite store

        mro = compute_class_mro(store, class_name, str(file_path) if file_path else None)

        if not mro:
            console.print(f"[red]No inheritance found for class '{class_name}'[/red]")
            raise typer.Exit(code=1)

        if CLIConfig.is_machine_mode() or json_output:
            mro_data = [
                {
                    "class_name": node.class_name,
                    "file_path": node.file_path,
                    "base_classes": node.base_classes,
                    "depth": node.depth,
                    "confidence": node.confidence,
                }
                for node in mro
            ]
            typer.echo(json.dumps(mro_data, indent=2))
            return

        # Pretty print MRO
        console.print(f"\n[bold]Method Resolution Order for {class_name}:[/bold]\n")

        for i, node in enumerate(mro):
            indent = "  " * node.depth
            arrow = "↳ " if node.depth > 0 else ""
            confidence_color = "green" if node.confidence == 1.0 else "yellow" if node.confidence > 0.8 else "dim"

            console.print(f"{indent}{arrow}[{confidence_color}]{node.class_name}[/{confidence_color}]", end="")

            if node.file_path:
                console.print(f" [dim]({node.file_path})[/dim]", end="")

            if node.base_classes:
                console.print(f" [dim]extends: {', '.join(node.base_classes)}[/dim]")
            else:
                console.print()

        console.print(f"\n[dim]Total depth: {max(n.depth for n in mro)}[/dim]")

    except Exception as e:
        logger.error(f"Failed to compute inheritance tree: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)




@app.command("descendants")
def descendants_cmd(
    class_name: str = typer.Argument(..., help="Base class name to find descendants of."),
    file_path: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="File path to disambiguate (if multiple classes with same name).",
    ),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [PHASE 6] Show all classes that inherit from a base class.

    Finds all direct and indirect descendants (subclasses) of the given class.

    Examples:
      cerberus descendants CerberusError
      cerberus descendants BaseModel
    """
    from cerberus.index import load_index
    from cerberus.resolution import get_class_descendants

    index_path = get_default_index(index_path)

    try:
        scan_result = load_index(index_path)
        store = scan_result._store

        descendants = get_class_descendants(store, class_name, str(file_path) if file_path else None)

        if CLIConfig.is_machine_mode() or json_output:
            typer.echo(json.dumps({"base_class": class_name, "descendants": descendants}, indent=2))
            return

        if not descendants:
            console.print(f"[yellow]No descendants found for class '{class_name}'[/yellow]")
            return

        console.print(f"\n[bold]Descendants of {class_name}:[/bold] ({len(descendants)} classes)\n")

        for desc in sorted(descendants):
            console.print(f"  • {desc}")

        console.print()

    except Exception as e:
        logger.error(f"Failed to find descendants: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)




@app.command("overrides")
def overrides_cmd(
    class_name: str = typer.Argument(..., help="Class name to find overridden methods for."),
    file_path: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="File path to disambiguate (if multiple classes with same name).",
    ),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [PHASE 6] Show methods that override base class methods.

    Identifies which methods in the class override methods from base classes,
    helping understand polymorphism and method resolution.

    Examples:
      cerberus overrides ParserError
      cerberus overrides Skeletonizer
    """
    from cerberus.index import load_index
    from cerberus.resolution import get_overridden_methods

    index_path = get_default_index(index_path)

    try:
        scan_result = load_index(index_path)
        store = scan_result._store

        overrides = get_overridden_methods(store, class_name, str(file_path) if file_path else None)

        if CLIConfig.is_machine_mode() or json_output:
            typer.echo(json.dumps({"class": class_name, "overrides": overrides}, indent=2))
            return

        if not overrides:
            console.print(f"[yellow]No overridden methods found for class '{class_name}'[/yellow]")
            return

        console.print(f"\n[bold]Overridden methods in {class_name}:[/bold]\n")

        for method_name, override_info in overrides.items():
            console.print(f"  [cyan]{method_name}()[/cyan]")
            for info in override_info:
                confidence_color = "green" if info["confidence"] == 1.0 else "yellow"
                console.print(f"    ↳ overrides [{confidence_color}]{info['base_class']}[/{confidence_color}]", end="")
                if info["base_file"]:
                    console.print(f" [dim]({info['base_file']}:{info['base_line']})[/dim]")
                else:
                    console.print(f" [dim](external)[/dim]")

        console.print()

    except Exception as e:
        logger.error(f"Failed to find overrides: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)




@app.command("call-graph")
def call_graph_cmd(
    symbol_name: str = typer.Argument(..., help="Function/method name to analyze."),
    direction: str = typer.Option(
        "forward",
        "--direction",
        "-d",
        help="Graph direction: 'forward' (what does it call?) or 'reverse' (what calls it?)"
    ),
    file_path: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="File path to disambiguate (if multiple symbols with same name).",
    ),
    max_depth: int = typer.Option(
        5,
        "--depth",
        help="Maximum call depth to traverse."
    ),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [PHASE 6] Generate call graph showing execution paths.

    Shows what functions/methods are called (forward) or what calls them (reverse).

    Examples:
      cerberus call-graph build_index --direction forward
      cerberus call-graph parse_file --direction reverse --depth 3
    """
    from cerberus.index import load_index
    from cerberus.resolution import build_call_graph

    index_path = get_default_index(index_path)

    try:
        scan_result = load_index(index_path)
        store = scan_result._store

        graph = build_call_graph(
            store,
            symbol_name,
            str(file_path) if file_path else None,
            direction,
            max_depth
        )

        if CLIConfig.is_machine_mode() or json_output:
            import json as json_lib
            graph_data = {
                "root_symbol": graph.root_symbol,
                "root_file": graph.root_file,
                "nodes": [
                    {
                        "symbol": node.symbol_name,
                        "file": node.file_path,
                        "line": node.line,
                        "depth": node.depth,
                        "type": node.call_type
                    }
                    for node in graph.nodes
                ],
                "edges": [[caller, callee] for caller, callee in graph.edges],
                "max_depth": graph.max_depth_reached,
                "truncated": graph.truncated
            }
            typer.echo(json_lib.dumps(graph_data, indent=2))
            return

        # Pretty print call graph
        console.print(f"\n[bold]Call Graph for {symbol_name} ({direction}):[/bold]\n")

        if not graph.nodes:
            console.print(f"[yellow]No calls found for '{symbol_name}'[/yellow]")
            return

        # Group nodes by depth
        by_depth: Dict[int, List] = {}
        for node in graph.nodes:
            if node.depth not in by_depth:
                by_depth[node.depth] = []
            by_depth[node.depth].append(node)

        # Display by depth
        for depth in sorted(by_depth.keys()):
            nodes = by_depth[depth]
            indent = "  " * depth
            arrow = "→ " if depth > 0 else ""

            console.print(f"[dim]Depth {depth}:[/dim]")
            for node in nodes:
                console.print(f"{indent}{arrow}[cyan]{node.symbol_name}[/cyan] [dim]({node.file_path}:{node.line})[/dim]")

        console.print(f"\n[dim]Total nodes: {len(graph.nodes)}, edges: {len(graph.edges)}, max depth: {graph.max_depth_reached}[/dim]")
        if graph.truncated:
            console.print(f"[yellow]Graph truncated at depth {max_depth}[/yellow]")

    except Exception as e:
        logger.error(f"Failed to generate call graph: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)




@app.command("smart-context")
def smart_context_cmd(
    symbol_name: str = typer.Argument(..., help="Symbol name to get context for."),
    file_path: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="File path to disambiguate (if multiple symbols with same name).",
    ),
    include_bases: bool = typer.Option(
        True,
        "--include-bases/--no-bases",
        help="Include base class context for classes."
    ),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Write context to file instead of stdout."
    ),
):
    """
    [PHASE 6] Assemble smart context with inheritance awareness.

    Provides AI-optimized context including the symbol's code,
    skeletonized base classes, and related imports.

    Examples:
      cerberus smart-context Skeletonizer --include-bases
      cerberus smart-context build_index --output context.txt
    """
    from cerberus.index import load_index
    from cerberus.resolution import assemble_context

    index_path = get_default_index(index_path)

    try:
        scan_result = load_index(index_path)
        store = scan_result._store

        context = assemble_context(
            store,
            symbol_name,
            str(file_path) if file_path else None,
            include_bases
        )

        if not context:
            console.print(f"[red]Symbol '{symbol_name}' not found.[/red]")
            raise typer.Exit(code=1)

        # Format context
        from cerberus.resolution.context_assembler import ContextAssembler
        assembler = ContextAssembler(store)
        formatted = assembler.format_context(context)

        # Output
        if output_file:
            output_file.write_text(formatted)
            console.print(f"[green]Context written to {output_file}[/green]")
            console.print(f"[dim]Lines: {context.total_lines}, Compression: {context.compression_ratio:.1%}[/dim]")
        else:
            console.print(formatted)

    except Exception as e:
        logger.error(f"Failed to assemble context: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command("trace-path")
def trace_path_cmd(
    source: str = typer.Argument(..., help="Source symbol name (e.g., 'api_endpoint')"),
    target: str = typer.Argument(..., help="Target symbol name (e.g., 'db_save')"),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    max_depth: int = typer.Option(10, "--max-depth", "-d", help="Maximum path depth to search."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
):
    """
    [PHASE 8] Map execution path from source symbol to target symbol.

    Shows deterministic call chains showing how data flows through the system.
    Uses BFS to find shortest paths in the call graph.

    Examples:
      cerberus symbolic trace-path api_endpoint db_save
      cerberus symbolic trace-path handle_request send_response --max-depth 5
    """
    from collections import deque
    from cerberus.index import load_index
    from cerberus.resolution.call_graph_builder import CallGraphBuilder

    index_path = get_default_index(index_path)

    try:
        # Load index
        scan_result = load_index(index_path)

        # Find source and target symbols
        source_syms = [s for s in scan_result.symbols if s.name == source]
        target_syms = [s for s in scan_result.symbols if s.name == target]

        if not source_syms:
            console.print(f"[red]Source symbol '{source}' not found in index.[/red]")
            raise typer.Exit(code=1)

        if not target_syms:
            console.print(f"[red]Target symbol '{target}' not found in index.[/red]")
            raise typer.Exit(code=1)

        # Build call graph and find paths for each source symbol
        builder = CallGraphBuilder(scan_result._store)
        paths_found = []

        for source_sym in source_syms:
            # Build forward graph from this source
            call_graph = builder.build_forward_graph(source_sym.name, source_sym.file_path)
            source_key = f"{source_sym.file_path}:{source_sym.name}"

            # BFS
            queue = deque([(source_key, [source_key])])
            visited = set([source_key])

            while queue and len(paths_found) < 3:  # Find up to 3 paths
                current, path = queue.popleft()

                if len(path) > max_depth:
                    continue

                # Check if we reached target
                current_name = current.split(':')[-1]
                if current_name == target:
                    paths_found.append(path)
                    continue

                # Get callees
                if current in call_graph.nodes:
                    node = call_graph.nodes[current]
                    for callee_key in node.callees:
                        if callee_key not in visited:
                            visited.add(callee_key)
                            queue.append((callee_key, path + [callee_key]))

        if not paths_found:
            console.print(f"[yellow]No execution path found from '{source}' to '{target}' (within depth {max_depth}).[/yellow]")
            return

        # Format output
        if CLIConfig.is_machine_mode() or json_output:
            output = {
                'source': source,
                'target': target,
                'paths': []
            }
            for path in paths_found:
                path_data = []
                for key in path:
                    file_path, sym_name = key.rsplit(':', 1)
                    # Find symbol details
                    sym = next((s for s in scan_result.symbols if s.file_path == file_path and s.name == sym_name), None)
                    path_data.append({
                        'symbol': sym_name,
                        'file': file_path,
                        'line': sym.start_line if sym else 0
                    })
                output['paths'].append(path_data)

            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        console.print(f"\n[bold cyan]Execution paths from '{source}' to '{target}'[/bold cyan]")
        console.print(f"[dim]Found {len(paths_found)} path(s)[/dim]\n")

        for i, path in enumerate(paths_found, 1):
            console.print(f"[bold yellow]Path {i}:[/bold yellow] [dim](length: {len(path)})[/dim]")

            for j, key in enumerate(path):
                file_path, sym_name = key.rsplit(':', 1)

                # Find symbol details
                sym = next((s for s in scan_result.symbols if s.file_path == file_path and s.name == sym_name), None)

                # Format with arrows
                prefix = "  " if j > 0 else ""
                arrow = "  ↓ " if j < len(path) - 1 else ""

                if sym:
                    console.print(f"{prefix}[green]{sym_name}[/green] [dim]({file_path}:{sym.start_line})[/dim]")
                else:
                    console.print(f"{prefix}[green]{sym_name}[/green] [dim]({file_path})[/dim]")

                if arrow:
                    console.print(arrow)

            console.print()

    except Exception as e:
        logger.error(f"Trace-path failed: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


