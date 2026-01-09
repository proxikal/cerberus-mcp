"""
CLI Retrieval Commands

get-symbol, search, skeleton-file, skeletonize, blueprint, get-context
"""

import json
import typer
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.markup import escape

from cerberus.logging_config import logger
from cerberus.agent_session import record_operation
from cerberus.index import (
    load_index,
    find_symbol,
    read_range,
    semantic_search,
)
# Phase 9.5: Thin Client Routing
from .retrieval_routing import get_symbol_with_routing

app = typer.Typer()
console = Console()

@app.command("get-symbol")
def get_symbol(
    name: Optional[str] = typer.Argument(None, help="Name of the symbol to retrieve."),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to a previously generated index file. Defaults to 'cerberus.db' in CWD.",
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
    fuzzy: bool = typer.Option(
        False, "--fuzzy", help="[PHASE 2.1] Enable fuzzy matching (substring search)."
    ),
    file: Optional[str] = typer.Option(
        None, "--file", help="[PHASE 2.1] Show all symbols in a specific file."
    ),
    symbol_type: Optional[str] = typer.Option(
        None, "--type", help="[PHASE 2.1] Filter by symbol type (function, class, method)."
    ),
    auto_hydrate: bool = typer.Option(
        False, "--auto-hydrate", help="[PHASE 8] Auto-fetch skeletons of referenced internal types."
    ),
):
    """
    [ENHANCED - PHASE 2.1] Retrieves code for a symbol from the index with minimal context.

    Now supports fuzzy matching for exploration!

    Examples:
      cerberus get-symbol MyClass                             # Exact match
      cerberus get-symbol "skeleto" --fuzzy                   # Fuzzy search
      cerberus get-symbol --file src/cerberus/main.py         # All symbols in file
    """
    # Default to cerberus.db in CWD if not provided
    if index_path is None:
        index_path = Path("cerberus.db")
        if not index_path.exists():
            console.print(f"[red]Error: Index file 'cerberus.db' not found in current directory.[/red]")
            console.print(f"[dim]Run 'cerberus index .' first or provide --index path.[/dim]")
            raise typer.Exit(code=1)

    # Phase 9.5: Only load index if needed (not for simple exact-match with daemon)
    # Simple exact-match case is handled by get_symbol_with_routing (which checks daemon first)
    scan_result = None
    if file or fuzzy or (name and not skeleton and not auto_hydrate):
        # Need full scan_result for complex queries
        if file or fuzzy:
            scan_result = load_index(index_path)

    # Phase 2.1: Enhanced symbol finding
    if file:
        # Show all symbols in a file
        matches = [sym for sym in scan_result.symbols
                  if sym.file_path.endswith(file) or file in sym.file_path]
        if symbol_type:
            matches = [sym for sym in matches if sym.type == symbol_type]
    elif fuzzy and name:
        # Fuzzy matching (substring)
        name_lower = name.lower()
        matches = [sym for sym in scan_result.symbols
                  if name_lower in sym.name.lower()]
        if symbol_type:
            matches = [sym for sym in matches if sym.type == symbol_type]
        # Sort by name length (shorter = better match)
        matches = sorted(matches, key=lambda s: len(s.name))
    elif name:
        # Exact matching with Phase 9.5 daemon routing
        matches = get_symbol_with_routing(name, index_path, use_daemon=True)
    else:
        console.print("[red]Error: Provide either a symbol name or use --file flag.[/red]")
        console.print("Examples:")
        console.print("  cerberus get-symbol MyClass")
        console.print("  cerberus get-symbol \"skeleto\" --fuzzy")
        console.print("  cerberus get-symbol --file src/cerberus/main.py")
        raise typer.Exit(code=1)

    if not matches:
        console.print(f"[red]No matches found for '{name or file}' in index '{index_path}'.[/red]")
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
                "hydrated_types": []
            }
        )

    # Phase 8: Auto-hydrate referenced types
    if auto_hydrate:
        import re
        for item in enriched:
            symbol = item["symbol"]
            hydrated = []

            # Extract type names from signature and return_type
            type_names = set()

            if symbol.get("return_type"):
                matches = re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b', symbol["return_type"])
                type_names.update(matches)

            if symbol.get("signature"):
                matches = re.findall(r':\s*([A-Z][a-zA-Z0-9_\[\]]+)', symbol["signature"])
                for match in matches:
                    inner_matches = re.findall(r'\b[A-Z][a-zA-Z0-9_]*\b', match)
                    type_names.update(inner_matches)

            # Filter out built-in types
            builtins = {'List', 'Dict', 'Set', 'Tuple', 'Optional', 'Union', 'Any', 'None', 'Callable'}
            type_names = type_names - builtins

            # Look up each type in the index
            for type_name in type_names:
                type_matches = [s for s in scan_result.symbols if s.name == type_name and s.type in ['class', 'interface']]

                for type_symbol in type_matches:
                    type_skeleton = read_range(
                        Path(type_symbol.file_path),
                        type_symbol.start_line,
                        type_symbol.end_line,
                        padding=0,
                        skeleton=True,
                    )
                    hydrated.append({
                        'type_name': type_name,
                        'file': type_symbol.file_path,
                        'line': type_symbol.start_line,
                        'skeleton': type_skeleton.content
                    })
                    break

            item["hydrated_types"] = hydrated

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

        if auto_hydrate and item.get("hydrated_types"):
            console.print(f"\n[bold magenta]Auto-Hydrated Types ({len(item['hydrated_types'])}):[/bold magenta]")
            for hydrated in item["hydrated_types"]:
                console.print(f"\n[bold cyan]{hydrated['type_name']}[/bold cyan] [dim]({hydrated['file']}:{hydrated['line']})[/dim]")
                console.print(f"[dim]{hydrated['skeleton']}[/dim]")



@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (keyword or natural language)."),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
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
    show_snippets: bool = typer.Option(False, "--show-snippets", help="Load and display code snippets for results."),
    auto_skeletonize: bool = typer.Option(True, "--auto-skeletonize/--no-auto-skeletonize", help="Auto-skeletonize large results to save tokens (Phase 4)."),
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
    """
    from cerberus.retrieval import hybrid_search, read_range
    from cerberus.retrieval.utils import estimate_tokens
    from cerberus.retrieval.config import AUTO_SKELETONIZE_CONFIG
    from cerberus.synthesis import get_synthesis_facade

    # Default to cerberus.db in CWD if not provided
    if index_path is None:
        index_path = Path("cerberus.db")
        if not index_path.exists():
            console.print(f"[red]Error: Index file 'cerberus.db' not found in current directory.[/red]")
            console.print(f"[dim]Run 'cerberus index .' first or provide --index path.[/dim]")
            raise typer.Exit(code=1)

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

        # Load snippets if requested (Phase 4: skeleton-first search)
        snippets_data = {}
        total_tokens_before = 0
        total_tokens_after = 0

        if show_snippets:
            # Load all snippets first
            for res in results:
                sym = res.symbol
                snippet = read_range(
                    file_path=Path(sym.file_path),
                    start_line=sym.start_line,
                    end_line=sym.end_line,
                    padding=padding,
                    skeleton=False,
                )
                snippets_data[res.rank] = {
                    "content": snippet.content,
                    "start_line": snippet.start_line,
                    "end_line": snippet.end_line,
                    "tokens": estimate_tokens(snippet.content),
                }
                total_tokens_before += snippets_data[res.rank]["tokens"]

            # Apply auto-skeletonization if enabled and threshold exceeded
            if auto_skeletonize and AUTO_SKELETONIZE_CONFIG["enabled"]:
                threshold = AUTO_SKELETONIZE_CONFIG["token_threshold"]
                per_result_threshold = AUTO_SKELETONIZE_CONFIG["per_result_threshold"]

                if total_tokens_before > threshold:
                    logger.info(f"Total tokens ({total_tokens_before}) exceeds threshold ({threshold}), applying auto-skeletonization")
                    synthesis_facade = get_synthesis_facade()

                    for res in results:
                        snippet_data = snippets_data[res.rank]
                        result_tokens = snippet_data["tokens"]

                        # Skeletonize large results
                        if result_tokens > per_result_threshold:
                            try:
                                skeleton = synthesis_facade.skeletonize_file(
                                    file_path=res.symbol.file_path,
                                    preserve_symbols=[res.symbol.name]
                                )
                                # Extract the relevant range from skeleton
                                skeleton_lines = skeleton.content.splitlines()
                                start_idx = max(0, res.symbol.start_line - 1 - padding)
                                end_idx = min(len(skeleton_lines), res.symbol.end_line + padding)
                                skeleton_snippet = "\n".join(skeleton_lines[start_idx:end_idx])

                                snippet_data["content"] = skeleton_snippet
                                snippet_data["tokens"] = estimate_tokens(skeleton_snippet)
                                snippet_data["skeletonized"] = True
                                logger.debug(f"Skeletonized {res.symbol.name}: {result_tokens} → {snippet_data['tokens']} tokens")
                            except Exception as e:
                                logger.warning(f"Failed to skeletonize {res.symbol.file_path}: {e}")
                                snippet_data["skeletonized"] = False
                        else:
                            snippet_data["skeletonized"] = False

                    # Recalculate total tokens
                    total_tokens_after = sum(s["tokens"] for s in snippets_data.values())
                    token_savings = total_tokens_before - total_tokens_after
                    if token_savings > 0:
                        console.print(f"[green]Token optimization:[/green] {total_tokens_before} → {total_tokens_after} tokens (saved {token_savings}, {100 * token_savings / total_tokens_before:.1f}%)")
                else:
                    total_tokens_after = total_tokens_before

        # Prepare response
        response = []
        for res in results:
            result_dict = {
                "rank": res.rank,
                "hybrid_score": res.hybrid_score,
                "bm25_score": res.bm25_score,
                "vector_score": res.vector_score,
                "match_type": res.match_type,
                "symbol": res.symbol.model_dump(),
            }

            # Add snippet if loaded
            if show_snippets and res.rank in snippets_data:
                result_dict["snippet"] = snippets_data[res.rank]

            response.append(result_dict)

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
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)



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
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        raise typer.Exit(code=1)



@app.command("blueprint")
def blueprint_cmd(
    file: Path = typer.Argument(..., help="File to generate blueprint for."),
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
    [PHASE 8] Whole-file AST blueprint from index (faster than disk read).
    Shows complete file structure (classes, signatures, docstrings) without function bodies.
    """
    from cerberus.index import load_index
    from collections import defaultdict

    # Default to cerberus.db in CWD if not provided
    if index_path is None:
        index_path = Path("cerberus.db")
        if not index_path.exists():
            console.print(f"[red]Error: Index file 'cerberus.db' not found in current directory.[/red]")
            console.print(f"[dim]Run 'cerberus index .' first or provide --index path.[/dim]")
            raise typer.Exit(code=1)

    try:
        # Load index
        scan_result = load_index(index_path)

        # Normalize file path
        file_str = str(file)

        # Query all symbols for the file from index
        symbols = list(scan_result._store.query_symbols(filter={'file_path': file_str}))

        if not symbols:
            console.print(f"[red]No symbols found for file '{file}' in index.[/red]")
            console.print(f"[dim]Make sure the file is indexed and the path matches.[/dim]")
            raise typer.Exit(code=1)

        # Deduplicate symbols (SQLite may have duplicates)
        seen = set()
        unique_symbols = []
        for sym in symbols:
            key = (sym.name, sym.type, sym.start_line, sym.parent_class or '')
            if key not in seen:
                seen.add(key)
                unique_symbols.append(sym)
        symbols = unique_symbols

        # Sort symbols by line number
        symbols.sort(key=lambda s: s.start_line)

        # Build blueprint structure
        blueprint_data = {
            'file': file_str,
            'symbols': [],
            'total_symbols': len(symbols),
        }

        # Group methods by parent class
        classes = defaultdict(list)
        top_level = []

        for sym in symbols:
            sym_data = {
                'name': sym.name,
                'type': sym.type,
                'line': sym.start_line,
                'signature': sym.signature or '',
            }

            if sym.parent_class:
                classes[sym.parent_class].append(sym_data)
            else:
                top_level.append(sym_data)

        # Build structured output
        for sym in top_level:
            if sym['type'] == 'class':
                # Add class with its methods
                class_entry = {
                    'name': sym['name'],
                    'type': 'class',
                    'line': sym['line'],
                    'signature': sym['signature'],
                    'methods': classes.get(sym['name'], [])
                }
                blueprint_data['symbols'].append(class_entry)
            else:
                # Top-level function/variable
                blueprint_data['symbols'].append(sym)

        if json_output:
            typer.echo(json.dumps(blueprint_data, indent=2))
            return

        # Human-readable output
        console.print(f"\n[bold cyan]Blueprint for {file}[/bold cyan]")
        console.print(f"[dim]Total symbols: {len(symbols)} (index-backed, no disk read)[/dim]\n")

        for sym in blueprint_data['symbols']:
            if sym['type'] == 'class':
                class_sig = sym.get('signature') or f"class {sym['name']}"
                console.print(f"\n[bold yellow]{class_sig}[/bold yellow] [dim](line {sym['line']})[/dim]")

                # Show methods
                for method in sym.get('methods', []):
                    method_sig = method.get('signature')
                    if not method_sig:
                        # Fallback: show as method name with parentheses
                        method_sig = f"def {method['name']}(...)" if method['type'] == 'function' else method['name']
                    console.print(f"    [green]{method_sig}[/green] [dim](line {method['line']})[/dim]")
            else:
                # Top-level function/variable
                sig = sym.get('signature')
                if not sig:
                    # Fallback: show with def keyword for functions
                    if sym['type'] == 'function':
                        sig = f"def {sym['name']}(...)"
                    else:
                        sig = sym['name']
                console.print(f"\n[bold green]{sig}[/bold green] [dim](line {sym['line']})[/dim]")

        console.print()

        # Record operation for dogfooding metrics
        record_operation('blueprint', tokens_read=0, tokens_saved=0, file_path=file_str)

    except Exception as e:
        logger.error(f"Failed to generate blueprint for {file}: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        raise typer.Exit(code=1)


@app.command("get-context")
def get_context(
    symbol_name: str = typer.Argument(..., help="Symbol name to get context for."),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
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

    # Default to cerberus.db in CWD if not provided
    if index_path is None:
        index_path = Path("cerberus.db")
        if not index_path.exists():
            console.print(f"[red]Error: Index file 'cerberus.db' not found in current directory.[/red]")
            console.print(f"[dim]Run 'cerberus index .' first or provide --index path.[/dim]")
            raise typer.Exit(code=1)

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
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        raise typer.Exit(code=1)


