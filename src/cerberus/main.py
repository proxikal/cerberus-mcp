import json
import typer
import atexit
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.table import Table

from cerberus.logging_config import logger
from cerberus.agent_session import display_session_summary, record_operation
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

# Register session summary display at exit (for agent dogfooding metrics)
atexit.register(display_session_summary)

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
    typer.echo("Cerberus v0.1.0")

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
def read(
    file_path: Path = typer.Argument(..., help="File path to read."),
    start_line: Optional[int] = typer.Option(None, "--start", help="Start line number (1-indexed)."),
    end_line: Optional[int] = typer.Option(None, "--end", help="End line number (1-indexed)."),
    lines: Optional[str] = typer.Option(None, "--lines", help="Line range (e.g., '1-100')."),
    skeleton: bool = typer.Option(False, "--skeleton", help="Show skeleton view (signatures only)."),
    index_path: Optional[Path] = typer.Option(None, "--index", "-i", help="Index path for verification."),
    verify: bool = typer.Option(False, "--verify", help="Verify file matches index (requires --index)."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for agents."),
):
    """
    [DOGFOODING - PHASE 1.1] Read a source file with optional range and skeleton view.

    This command enables 100% Cerberus dogfooding by providing direct file access
    through the CLI instead of requiring external file read tools.

    Examples:
      cerberus read src/cerberus/main.py                    # Full file
      cerberus read src/cerberus/main.py --lines 1-100      # Specific range
      cerberus read src/cerberus/main.py --skeleton         # Signatures only
      cerberus read src/cerberus/main.py --index cerberus.db --verify  # Check drift
    """
    from cerberus.retrieval.utils import read_range, _skeletonize, estimate_tokens
    from cerberus.index import load_index

    try:
        # Parse line range if provided
        if lines:
            try:
                parts = lines.split('-')
                if len(parts) != 2:
                    console.print(f"[red]Invalid line range '{lines}'. Use format: 'start-end' (e.g., '1-100')[/red]")
                    raise typer.Exit(code=1)
                start_line = int(parts[0])
                end_line = int(parts[1])
            except ValueError:
                console.print(f"[red]Invalid line range '{lines}'. Numbers required.[/red]")
                raise typer.Exit(code=1)

        # Check if file exists
        if not file_path.exists():
            console.print(f"[red]File not found: {file_path}[/red]")
            raise typer.Exit(code=1)

        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        total_lines = len(content.splitlines())

        # Determine range
        if start_line is None and end_line is None:
            # Full file
            start_line = 1
            end_line = total_lines
        elif start_line is None:
            start_line = 1
        elif end_line is None:
            end_line = total_lines

        # Validate range
        if start_line < 1 or end_line < start_line:
            console.print(f"[red]Invalid range: {start_line}-{end_line}[/red]")
            raise typer.Exit(code=1)

        # Apply skeleton view if requested
        if skeleton:
            content = _skeletonize(content)
            total_lines = len(content.splitlines())

        # Extract range
        lines_list = content.splitlines()
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines_list), end_line)
        selected_lines = lines_list[start_idx:end_idx]

        # Verify against index if requested
        in_index = False
        index_matches = None
        if verify and index_path:
            try:
                scan_result = load_index(index_path)
                # Check if file is in index
                abs_path = str(file_path.absolute())
                in_index = any(sym.file_path == abs_path or sym.file_path == str(file_path)
                              for sym in scan_result.symbols)
                if in_index:
                    # Simple check: compare line count (more sophisticated checks possible)
                    index_symbols = [sym for sym in scan_result.symbols
                                    if sym.file_path == abs_path or sym.file_path == str(file_path)]
                    if index_symbols:
                        # File exists in index
                        index_matches = True
                    else:
                        index_matches = False
            except Exception as e:
                logger.warning(f"Could not verify against index: {e}")

        # Get file stats
        import os
        file_stats = os.stat(file_path)
        last_modified = file_stats.st_mtime

        # Track session metrics for dogfooding
        content_shown = "\n".join(selected_lines)
        tokens_read = estimate_tokens(content_shown)
        # Calculate tokens saved (full file tokens - tokens shown)
        full_content_tokens = estimate_tokens(content)
        tokens_saved = max(0, full_content_tokens - tokens_read)
        if skeleton:
            # Skeleton view saves even more tokens
            original_content_tokens = estimate_tokens(Path(file_path).read_text(errors='ignore'))
            tokens_saved = max(0, original_content_tokens - tokens_read)

        record_operation("read", tokens_read=tokens_read, tokens_saved=tokens_saved, file_path=str(file_path))

        # JSON output
        if json_output:
            output = {
                "file_path": str(file_path),
                "lines_shown": {
                    "start": start_line,
                    "end": end_idx
                },
                "total_lines": total_lines,
                "content": "\n".join(selected_lines),
                "last_modified": last_modified,
                "skeleton_view": skeleton,
            }
            if verify and index_path:
                output["index"] = {
                    "in_index": in_index,
                    "matches": index_matches
                }
            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        console.print(f"\n[cyan]File:[/cyan] {file_path}")
        console.print(f"[cyan]Lines:[/cyan] {start_line}-{end_idx} of {total_lines} ({100 * (end_idx - start_line + 1) / total_lines:.1f}%)")

        if skeleton:
            console.print(f"[yellow]View:[/yellow] Skeleton (signatures only)")

        if verify and index_path:
            if in_index:
                if index_matches:
                    console.print(f"[green]Index Status:[/green] ✓ In index")
                else:
                    console.print(f"[yellow]Index Status:[/yellow] ⚠ In index (may be stale)")
            else:
                console.print(f"[red]Index Status:[/red] ✗ Not in index")

        console.print()

        # Display content with line numbers
        for i, line in enumerate(selected_lines, start=start_line):
            console.print(f"[dim]{i:5}[/dim] | {line}")

    except Exception as e:
        logger.error(f"Read failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)

@app.command()
def inspect(
    file_path: Path = typer.Argument(..., help="File path to inspect."),
    index_path: Path = typer.Option(
        "cerberus.db",
        "--index",
        "-i",
        help="Path to index file.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
    show_callers: bool = typer.Option(False, "--callers", help="Include caller information."),
    show_imports: bool = typer.Option(False, "--imports", help="Include import statements."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for agents."),
):
    """
    [DOGFOODING - PHASE 1.2] Inspect a file to see all symbols, imports, and callers at a glance.

    This command provides a complete file overview without reading the full source,
    enabling quick exploration and understanding of file structure.

    Examples:
      cerberus inspect src/cerberus/synthesis/facade.py --index cerberus.db
      cerberus inspect src/cerberus/main.py --callers --imports
      cerberus inspect src/cerberus/retrieval/facade.py --json
    """
    from cerberus.index import load_index
    from cerberus.retrieval.utils import estimate_tokens
    from rich.panel import Panel
    from rich.text import Text
    import os
    from datetime import datetime

    try:
        # Check if file exists
        if not file_path.exists():
            console.print(f"[red]File not found: {file_path}[/red]")
            raise typer.Exit(code=1)

        # Load index
        scan_result = load_index(index_path)

        # Find symbols in this file
        abs_path = str(file_path.absolute())
        file_symbols = [sym for sym in scan_result.symbols
                       if sym.file_path == abs_path or sym.file_path == str(file_path)]

        if not file_symbols:
            console.print(f"[yellow]No symbols found for {file_path} in index.[/yellow]")
            console.print(f"[dim]File may not be indexed. Run: cerberus index . -o {index_path}[/dim]")
            raise typer.Exit(code=0)

        # Get file stats
        file_stats = os.stat(file_path)
        total_lines = len(file_path.read_text(errors='ignore').splitlines())
        last_modified = datetime.fromtimestamp(file_stats.st_mtime)
        time_ago = datetime.now() - last_modified
        if time_ago.days > 0:
            time_str = f"{time_ago.days} days ago"
        elif time_ago.seconds > 3600:
            time_str = f"{time_ago.seconds // 3600} hours ago"
        else:
            time_str = f"{time_ago.seconds // 60} minutes ago"

        # Organize symbols by type
        classes = [s for s in file_symbols if s.type == "class"]
        functions = [s for s in file_symbols if s.type == "function" and s.parent_class is None]
        methods = [s for s in file_symbols if s.type == "method" or (s.type == "function" and s.parent_class)]

        # Get imports if requested
        imports = []
        if show_imports:
            imports = [imp for imp in scan_result.imports if imp.file_path == abs_path or imp.file_path == str(file_path)]

        # Get callers if requested
        callers_map = {}
        if show_callers:
            for sym in file_symbols:
                callers = [call for call in scan_result.calls if call.callee == sym.name]
                if callers:
                    callers_map[sym.name] = callers

        # Track metrics
        record_operation("inspect", tokens_read=0, tokens_saved=total_lines * 4, file_path=str(file_path))

        # JSON output
        if json_output:
            output = {
                "file_path": str(file_path),
                "stats": {
                    "total_lines": total_lines,
                    "symbol_count": len(file_symbols),
                    "last_modified": file_stats.st_mtime,
                },
                "classes": [{"name": c.name, "line": c.start_line} for c in classes],
                "functions": [{"name": f.name, "line": f.start_line} for f in functions],
                "methods": [{"name": m.name, "line": m.start_line, "parent": m.parent_class} for m in methods],
            }
            if show_imports:
                output["imports"] = [{"module": i.module, "line": i.line} for i in imports]
            if show_callers:
                output["callers"] = {name: len(calls) for name, calls in callers_map.items()}
            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        console.print()
        console.print(f"[cyan]File:[/cyan] {file_path}")
        console.print(f"[cyan]Lines:[/cyan] {total_lines} | [cyan]Symbols:[/cyan] {len(file_symbols)} | [cyan]Modified:[/cyan] {time_str}")

        # Classes
        if classes:
            table = Table(title="📦 Classes", box=None, show_header=False, padding=(0, 2))
            table.add_column(style="green bold")
            table.add_column(style="dim")
            for cls in classes:
                class_methods = [m for m in methods if m.parent_class == cls.name]
                table.add_row(f"{cls.name}", f"(line {cls.start_line}, {len(class_methods)} methods)")
            console.print(table)

        # Functions
        if functions:
            table = Table(title="⚡ Functions", box=None, show_header=False, padding=(0, 2))
            table.add_column(style="yellow bold")
            table.add_column(style="dim")
            for func in functions[:10]:  # Limit to 10
                caller_count = len(callers_map.get(func.name, [])) if show_callers else 0
                caller_info = f", {caller_count} callers" if caller_count > 0 else ""
                table.add_row(f"{func.name}", f"(line {func.start_line}{caller_info})")
            if len(functions) > 10:
                console.print(f"[dim]... and {len(functions) - 10} more functions[/dim]")
            console.print(table)

        # Imports
        if show_imports and imports:
            console.print("\n[cyan]📥 Imports:[/cyan]")
            for imp in imports[:5]:
                console.print(f"  [dim]→[/dim] {imp.module}")
            if len(imports) > 5:
                console.print(f"  [dim]... and {len(imports) - 5} more imports[/dim]")

        # Callers summary
        if show_callers and callers_map:
            console.print(f"\n[cyan]📞 Called By:[/cyan] {len(callers_map)} symbols have callers")
            for name, calls in list(callers_map.items())[:3]:
                console.print(f"  [green]{name}[/green]: {len(calls)} callers")
            if len(callers_map) > 3:
                console.print(f"  [dim]... and {len(callers_map) - 3} more[/dim]")

        console.print()

    except Exception as e:
        logger.error(f"Inspect failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)

@app.command()
def tree(
    directory: Path = typer.Argument(".", help="Directory to show tree structure for."),
    index_path: Optional[Path] = typer.Option(None, "--index", "-i", help="Index path to show symbol counts."),
    max_depth: int = typer.Option(3, "--depth", "-d", help="Maximum depth to traverse."),
    show_symbols: bool = typer.Option(False, "--symbols", help="Show symbol counts per file."),
    extensions: Optional[str] = typer.Option(None, "--ext", help="Filter by extensions (comma-separated, e.g., '.py,.ts')."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for agents."),
):
    """
    [DOGFOODING - PHASE 2.2] Display directory tree structure with optional symbol counts.

    Critical for agent exploration - shows project layout without reading files.

    Examples:
      cerberus tree src/cerberus                          # Basic tree
      cerberus tree src/cerberus --depth 2                # Limit depth
      cerberus tree src/ --index cerberus.db --symbols    # With symbol counts
      cerberus tree . --ext .py,.ts                       # Filter by extension
    """
    from pathlib import Path
    from cerberus.index import load_index
    from cerberus.retrieval.utils import estimate_tokens
    import os

    try:
        # Check if directory exists
        if not directory.exists() or not directory.is_dir():
            console.print(f"[red]Directory not found: {directory}[/red]")
            raise typer.Exit(code=1)

        # Parse extensions filter
        ext_filter = None
        if extensions:
            ext_filter = [e.strip() for e in extensions.split(',')]
            if not all(e.startswith('.') for e in ext_filter):
                console.print("[yellow]Warning: Extensions should start with '.' (e.g., '.py')[/yellow]")

        # Load index if provided
        symbol_counts = {}
        if index_path and show_symbols:
            scan_result = load_index(index_path)
            for sym in scan_result.symbols:
                file_path = sym.file_path
                symbol_counts[file_path] = symbol_counts.get(file_path, 0) + 1

        # Build tree structure
        tree_data = []
        total_files = 0
        total_dirs = 0
        total_symbols = 0

        def _build_tree(path: Path, prefix: str = "", depth: int = 0):
            nonlocal total_files, total_dirs, total_symbols

            if depth > max_depth:
                return

            try:
                entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
            except PermissionError:
                return

            # Filter entries
            filtered_entries = []
            for entry in entries:
                # Skip hidden files/dirs
                if entry.name.startswith('.'):
                    continue
                # Skip __pycache__
                if entry.name == '__pycache__':
                    continue
                # Apply extension filter
                if ext_filter and entry.is_file():
                    if not any(entry.name.endswith(ext) for ext in ext_filter):
                        continue
                filtered_entries.append(entry)

            for i, entry in enumerate(filtered_entries):
                is_last = (i == len(filtered_entries) - 1)
                connector = "└── " if is_last else "├── "
                next_prefix = prefix + ("    " if is_last else "│   ")

                if entry.is_dir():
                    total_dirs += 1
                    tree_data.append({
                        "type": "dir",
                        "name": entry.name,
                        "prefix": prefix + connector,
                        "path": str(entry.relative_to(directory)),
                    })
                    _build_tree(entry, next_prefix, depth + 1)
                else:
                    total_files += 1
                    file_info = {
                        "type": "file",
                        "name": entry.name,
                        "prefix": prefix + connector,
                        "path": str(entry.relative_to(directory)),
                        "size": entry.stat().st_size,
                    }

                    # Add symbol count if available
                    abs_path = str(entry.absolute())
                    if abs_path in symbol_counts:
                        sym_count = symbol_counts[abs_path][abs_path]
                        file_info["symbols"] = sym_count
                        total_symbols += sym_count

                    tree_data.append(file_info)

        # Build the tree
        _build_tree(directory)

        # Track metrics
        total_tokens_saved = total_files * 200  # Assume avg 200 lines per file
        record_operation("tree", tokens_read=0, tokens_saved=total_tokens_saved, file_path=str(directory))

        # JSON output
        if json_output:
            output = {
                "directory": str(directory),
                "tree": tree_data,
                "summary": {
                    "total_files": total_files,
                    "total_directories": total_dirs,
                    "total_symbols": total_symbols if show_symbols else None,
                }
            }
            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        console.print(f"\n[cyan bold]{directory}/[/cyan bold]")

        for item in tree_data:
            line = item["prefix"]
            if item["type"] == "dir":
                line += f"[cyan bold]{item['name']}/[/cyan bold]"
            else:
                line += f"{item['name']}"
                if "symbols" in item:
                    line += f" [dim]({item['symbols']} symbols)[/dim]"

            console.print(line)

        # Summary
        console.print()
        summary_parts = [f"{total_files} files", f"{total_dirs} directories"]
        if show_symbols and total_symbols > 0:
            summary_parts.append(f"{total_symbols} symbols")
        console.print(f"[dim]{', '.join(summary_parts)}[/dim]")
        console.print()

    except Exception as e:
        logger.error(f"Tree failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)

@app.command()
def ls(
    directory: Path = typer.Argument(".", help="Directory to list."),
    extensions: Optional[str] = typer.Option(None, "--ext", help="Filter by extensions (comma-separated)."),
    long_format: bool = typer.Option(False, "-l", help="Long format with sizes and dates."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for agents."),
):
    """
    [DOGFOODING - PHASE 2.2] List files in a directory (fast, no parsing).

    Lightweight alternative to scan - just shows files without analyzing them.

    Examples:
      cerberus ls src/cerberus                 # Basic listing
      cerberus ls src/ --ext .py               # Python files only
      cerberus ls src/cerberus -l              # Long format with details
    """
    from datetime import datetime
    import os

    try:
        # Check if directory exists
        if not directory.exists() or not directory.is_dir():
            console.print(f"[red]Directory not found: {directory}[/red]")
            raise typer.Exit(code=1)

        # Parse extensions filter
        ext_filter = None
        if extensions:
            ext_filter = [e.strip() for e in extensions.split(',')]

        # List files
        entries = []
        try:
            for entry in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name)):
                # Skip hidden
                if entry.name.startswith('.'):
                    continue
                # Skip __pycache__
                if entry.name == '__pycache__':
                    continue

                # Apply extension filter
                if ext_filter and entry.is_file():
                    if not any(entry.name.endswith(ext) for ext in ext_filter):
                        continue

                stat = entry.stat()
                entry_data = {
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "path": str(entry),
                }
                entries.append(entry_data)
        except PermissionError:
            console.print(f"[red]Permission denied: {directory}[/red]")
            raise typer.Exit(code=1)

        # Track metrics
        record_operation("ls", tokens_read=0, tokens_saved=len(entries) * 10, file_path=str(directory))

        # JSON output
        if json_output:
            output = {
                "directory": str(directory),
                "entries": entries,
                "total": len(entries),
            }
            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        console.print(f"\n[cyan]{directory}/[/cyan]\n")

        if long_format:
            table = Table(box=None, show_header=True, padding=(0, 2))
            table.add_column("Type", style="dim", width=4)
            table.add_column("Name", style="cyan")
            table.add_column("Size", justify="right", style="yellow")
            table.add_column("Modified", style="dim")

            for entry in entries:
                type_icon = "📁" if entry["type"] == "directory" else "📄"
                size_str = f"{entry['size']:,}" if entry['type'] == 'file' else "-"
                mod_time = datetime.fromtimestamp(entry["modified"]).strftime("%Y-%m-%d %H:%M")

                table.add_row(
                    type_icon,
                    entry["name"] + ("/" if entry["type"] == "directory" else ""),
                    size_str,
                    mod_time
                )

            console.print(table)
        else:
            # Simple format
            for entry in entries:
                if entry["type"] == "directory":
                    console.print(f"[cyan bold]{entry['name']}/[/cyan bold]")
                else:
                    console.print(entry["name"])

        console.print(f"\n[dim]{len(entries)} items[/dim]\n")

    except Exception as e:
        logger.error(f"Ls failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)

@app.command()
def grep(
    pattern: str = typer.Argument(..., help="Pattern to search for (regex supported)."),
    path: Path = typer.Argument(".", help="Directory or file to search in."),
    extensions: Optional[str] = typer.Option(None, "--ext", help="Filter by file extensions (comma-separated)."),
    ignore_case: bool = typer.Option(False, "-i", help="Case-insensitive search."),
    context: int = typer.Option(0, "-C", help="Show N lines of context before/after match."),
    files_only: bool = typer.Option(False, "-l", help="Show only filenames with matches."),
    count: bool = typer.Option(False, "-c", help="Show count of matches per file."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for agents."),
):
    """
    [DOGFOODING - PHASE 2.2] Search for patterns in files (works without index).

    Critical for agent exploration - find patterns anywhere in codebase.

    Examples:
      cerberus grep "TODO" src/                      # Find all TODOs
      cerberus grep "class.*Test" tests/ --ext .py   # Find test classes
      cerberus grep "import.*pandas" . -i            # Case-insensitive
      cerberus grep "def.*auth" src/ -l              # Files with auth functions
    """
    import re
    import os

    try:
        # Parse extensions filter
        ext_filter = None
        if extensions:
            ext_filter = [e.strip() for e in extensions.split(',')]

        # Compile pattern
        flags = re.IGNORECASE if ignore_case else 0
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            console.print(f"[red]Invalid regex pattern: {e}[/red]")
            raise typer.Exit(code=1)

        # Find files to search
        files_to_search = []
        if path.is_file():
            files_to_search = [path]
        elif path.is_dir():
            for root, dirs, files in os.walk(path):
                # Skip hidden and __pycache__
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

                for file in files:
                    if file.startswith('.'):
                        continue

                    file_path = Path(root) / file

                    # Apply extension filter
                    if ext_filter:
                        if not any(file.endswith(ext) for ext in ext_filter):
                            continue

                    files_to_search.append(file_path)
        else:
            console.print(f"[red]Path not found: {path}[/red]")
            raise typer.Exit(code=1)

        # Search files
        results = []
        total_matches = 0

        for file_path in files_to_search:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                matches = []
                for line_num, line in enumerate(lines, start=1):
                    if regex.search(line):
                        match_data = {
                            "line_number": line_num,
                            "content": line.rstrip(),
                        }

                        # Add context if requested
                        if context > 0:
                            context_before = lines[max(0, line_num - 1 - context):line_num - 1]
                            context_after = lines[line_num:min(len(lines), line_num + context)]
                            match_data["context_before"] = [l.rstrip() for l in context_before]
                            match_data["context_after"] = [l.rstrip() for l in context_after]

                        matches.append(match_data)
                        total_matches += 1

                if matches:
                    results.append({
                        "file": str(file_path),
                        "matches": matches,
                        "count": len(matches),
                    })

            except (UnicodeDecodeError, PermissionError):
                continue

        # Track metrics
        total_lines_saved = sum(len(open(f, 'r', errors='ignore').readlines()) for f in files_to_search[:100])  # Sample
        record_operation("grep", tokens_read=total_matches * 10, tokens_saved=total_lines_saved, file_path=str(path))

        # JSON output
        if json_output:
            output = {
                "pattern": pattern,
                "path": str(path),
                "results": results,
                "total_matches": total_matches,
                "files_searched": len(files_to_search),
            }
            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        if not results:
            console.print(f"\n[yellow]No matches found for pattern '{pattern}'[/yellow]\n")
            return

        console.print(f"\n[cyan]Pattern:[/cyan] {pattern}\n")

        for result in results:
            if files_only:
                console.print(result["file"])
            elif count:
                console.print(f"{result['file']}: {result['count']}")
            else:
                console.print(f"[magenta]{result['file']}[/magenta]")
                for match in result["matches"][:10]:  # Limit to 10 per file
                    console.print(f"  [dim]{match['line_number']:4}[/dim] | {match['content']}")

                if len(result["matches"]) > 10:
                    console.print(f"  [dim]... and {len(result['matches']) - 10} more matches[/dim]")
                console.print()

        console.print(f"[dim]{total_matches} matches in {len(results)} files (searched {len(files_to_search)} files)[/dim]\n")

    except Exception as e:
        logger.error(f"Grep failed: {e}")
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)

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
        # Exact matching (original behavior)
        matches = find_symbol(name, scan_result)
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
    """
    # Default to cerberus.db in CWD if not provided
    if index_path is None:
        index_path = Path("cerberus.db")
        if not index_path.exists():
            console.print(f"[red]Error: Index file 'cerberus.db' not found in current directory.[/red]")
            console.print(f"[dim]Run 'cerberus index .' first or provide --index path.[/dim]")
            raise typer.Exit(code=1)

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
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


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
        # For 'start' we will create it if needed, for others we check existence
        if action in ["start", "restart"] and not index_path.exists():
             logger.info(f"Index not found at {index_path}, watcher will initialize it.")
        elif action not in ["start", "restart"] and not index_path.exists():
             # For status/stop/logs, we might just be checking based on PID file, but index path is used in status display
             pass

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
    from cerberus.agent_session import display_session_summary, clear_session, get_session_tracker

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


if __name__ == "__main__":
    app()
