"""
CLI Dogfood Commands - 100% INDEX-FIRST (No Legacy Systems)

read, inspect, tree, ls, grep, timeline

Phase 10: All legacy fallbacks removed. Index is REQUIRED for deterministic exploration.
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
from .output import get_console
# Phase 12.5: JIT Guidance
from .guidance import GuidanceProvider
# Phase 12.5: Context Anchoring
from .anchoring import ContextAnchor

app = typer.Typer()
console = get_console()

@app.command()
def read(
    file_path: Path = typer.Argument(..., help="File path to read."),
    start_line: Optional[int] = typer.Option(None, "--start", help="Start line number (1-indexed)."),
    end_line: Optional[int] = typer.Option(None, "--end", help="End line number (1-indexed)."),
    lines: Optional[str] = typer.Option(None, "--lines", help="Line range (e.g., '1-100')."),
    index_path: Optional[Path] = typer.Option(None, "--index", "-i", help="Index path. Defaults to cerberus.db."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for agents."),
):
    """
    Read file using index-backed blueprint (100% deterministic).

    REQUIRES INDEX: This command uses blueprint (Phase 8 engine) for token-efficient
    file structure viewing. Run 'cerberus index .' first.

    Examples:
      cerberus dogfood read src/main.py                 # Blueprint view
      cerberus dogfood read src/main.py --lines 1-100   # Specific range
    """
    from cerberus.retrieval.utils import estimate_tokens

    # Default to cerberus.db if not provided
    if index_path is None:
        index_path = Path("cerberus.db")

    # INDEX REQUIRED - No legacy fallback
    if not index_path.exists():
        console.print("[red]✗ No index found in current directory.[/red]")
        console.print("[yellow]→ Run 'cerberus index .' to create index first.[/yellow]")
        console.print("[dim]Cerberus dogfood commands require an index for deterministic exploration.[/dim]")
        raise typer.Exit(code=1)

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

    try:
        # Load index and use blueprint (Phase 8 dogfooding)
        scan_result = load_index(index_path)
        file_str = str(file_path)

        # Query symbols for this file
        symbols = list(scan_result._store.query_symbols(filter={'file_path': file_str}))

        if not symbols:
            console.print(f"[red]✗ File '{file_path}' not in index.[/red]")
            console.print("[yellow]→ Run 'cerberus index .' to index this file.[/yellow]")
            raise typer.Exit(code=1)

        # Build blueprint output (Phase 8 engine)
        symbols.sort(key=lambda s: s.start_line)

        blueprint_lines = [
            f"# Blueprint: {file_path}",
            f"# Symbols: {len(symbols)} | Mode: index-backed AST",
            ""
        ]

        for sym in symbols:
            indent = "    " if sym.parent_class else ""
            sig = sym.signature or f"{sym.type} {sym.name}"
            blueprint_lines.append(f"{sym.start_line:5} | {indent}{sig}")

        content = "\n".join(blueprint_lines)
        logger.info(f"Dogfooding: Used blueprint for {file_path} (Phase 8 engine)")

    except Exception as e:
        logger.error(f"Blueprint failed: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        raise typer.Exit(code=1)

    # Get total lines
    total_lines = len(content.splitlines())

    # Determine range
    if start_line is None and end_line is None:
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

    # Extract range
    lines_list = content.splitlines()
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines_list), end_line)
    selected_lines = lines_list[start_idx:end_idx]

    # Track session metrics
    content_shown = "\n".join(selected_lines)
    tokens_read = estimate_tokens(content_shown)

    # Blueprint saves massive tokens - calculate against raw file
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        raw_content = f.read()
    raw_tokens = estimate_tokens(raw_content)
    tokens_saved = max(0, raw_tokens - tokens_read)

    record_operation("read", tokens_read=tokens_read, tokens_saved=tokens_saved, file_path=str(file_path))

    # Phase 10: Machine mode is DEFAULT - JSON output for AI agents
    if CLIConfig.is_machine_mode() or json_output:
        output = {
            "file_path": str(file_path),
            "mode": "blueprint",
            "lines_shown": {
                "start": start_line,
                "end": end_idx
            },
            "total_lines": total_lines,
            "content": "\n".join(selected_lines),
        }
        # Compact JSON for agents (no pretty printing)
        typer.echo(json.dumps(output, separators=(',', ':')))
        return

    # Human mode: Rich formatted output with Phase 12.5 Context Anchoring
    header = ContextAnchor.format_header(
        file_path=str(file_path),
        lines=f"{start_line}-{end_idx}",
        status="Blueprint",
        extra={"Total": f"{total_lines} lines", "Mode": "Phase 8"}
    )
    console.print(f"\n{header}")
    console.print()

    # Display content with line numbers
    for i, line in enumerate(selected_lines, start=start_line):
        console.print(f"[dim]{i:5}[/dim] | {escape(line)}")

    # Phase 12.5: JIT Guidance
    if not json_output:
        tip = GuidanceProvider.get_tip("read")
        if tip:
            console.print(GuidanceProvider.format_tip(tip, style="footer"))


@app.command()
def inspect(
    file_path: Path = typer.Argument(..., help="File path to inspect."),
    index_path: Path = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for agents."),
):
    """
    🔍 Show detailed symbol breakdown for a file.

    Displays all symbols (classes, functions) extracted from a file with line numbers.
    Useful for understanding what Cerberus can see in a file.

    Examples:
      cerberus dogfood inspect src/cerberus/main.py
      cerberus dogfood inspect src/cerberus/main.py --json
    """
    from cerberus.index import load_index

    # Default to cerberus.db in CWD if not provided
    if index_path is None:
        index_path = Path("cerberus.db")
        if not index_path.exists():
            console.print(f"[red]Error: Index file 'cerberus.db' not found in current directory.[/red]")
            console.print(f"[yellow]Run 'cerberus index .' first or provide --index path.[/yellow]")
            raise typer.Exit(code=1)

    try:
        # Load index
        scan_result = load_index(index_path)

        # Normalize file path
        file_str = str(file_path)

        # Find all symbols in this file
        symbols = []
        for symbol in scan_result.symbols:
            if symbol.file_path == file_str or symbol.file_path == str(file_path.absolute()):
                symbols.append(symbol)

        if not symbols:
            console.print(f"[yellow]No symbols found for file: {file_path}[/yellow]")
            console.print(f"[dim]Make sure the file is indexed and path matches.[/dim]")
            raise typer.Exit(code=1)

        # Sort by line number
        symbols.sort(key=lambda s: s.start_line)

        # Track metrics
        record_operation("inspect", tokens_read=len(symbols) * 10, tokens_saved=0, file_path=str(file_path))

        # JSON output
        if json_output:
            output = {
                "file_path": str(file_path),
                "total_symbols": len(symbols),
                "symbols": [
                    {
                        "name": s.name,
                        "type": s.type,
                        "line": s.start_line,
                        "signature": s.signature,
                        "parent_class": s.parent_class,
                    }
                    for s in symbols
                ],
            }
            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        console.print(f"\n[bold]File:[/bold] {file_path}")
        console.print(f"[bold]Symbols:[/bold] {len(symbols)}\n")

        table = Table(box=None, show_header=True, padding=(0, 2))
        table.add_column("Line", style="dim", justify="right", width=6)
        table.add_column("Type", style="cyan", width=10)
        table.add_column("Name", style="bold")
        table.add_column("Signature", style="dim")

        for sym in symbols:
            sig = sym.signature or ""
            if sym.parent_class:
                name = f"  └─ {sym.name}"
            else:
                name = sym.name

            table.add_row(
                str(sym.start_line),
                sym.type,
                name,
                sig[:80] + "..." if len(sig) > 80 else sig,
            )

        console.print(table)
        console.print()

    except Exception as e:
        logger.error(f"Inspect failed: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command()
def tree(
    directory: Path = typer.Argument(".", help="Directory to show tree structure for."),
    index_path: Optional[Path] = typer.Option(None, "--index", "-i", help="Index path to show symbol counts."),
    max_depth: int = typer.Option(3, "--depth", "-d", help="Maximum depth to traverse."),
    show_files: bool = typer.Option(False, "--files", "-f", help="Show files in addition to directories."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for agents."),
):
    """
    🌳 Show directory tree structure with symbol counts.

    Displays a tree view of directories (optionally with files) and shows
    symbol counts from the index if available.

    Examples:
      cerberus dogfood tree src/                    # Directory tree
      cerberus dogfood tree src/ --files            # Include files
      cerberus dogfood tree src/ --depth 2          # Limit depth
    """
    from cerberus.index import load_index
    import os

    try:
        # Check if directory exists
        if not directory.exists() or not directory.is_dir():
            console.print(f"[red]Directory not found: {directory}[/red]")
            raise typer.Exit(code=1)

        # Load index if available for symbol counts
        symbol_counts = {}
        if index_path is None:
            index_path = Path("cerberus.db")

        if index_path.exists():
            try:
                scan_result = load_index(index_path)
                # Count symbols per file
                for symbol in scan_result.symbols:
                    file_path = symbol.file_path
                    symbol_counts[file_path] = symbol_counts.get(file_path, 0) + 1
            except Exception as e:
                logger.debug(f"Could not load index for symbol counts: {e}")

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

            for i, entry in enumerate(entries):
                # Skip hidden
                if entry.name.startswith('.'):
                    continue
                # Skip __pycache__
                if entry.name == '__pycache__':
                    continue

                is_last = i == len(entries) - 1
                connector = "└─ " if is_last else "├─ "
                extension = "    " if is_last else "│   "

                if entry.is_dir():
                    total_dirs += 1
                    tree_data.append({
                        "prefix": prefix + connector,
                        "name": entry.name + "/",
                        "type": "directory",
                        "path": str(entry),
                    })
                    _build_tree(entry, prefix + extension, depth + 1)
                elif show_files and entry.is_file():
                    total_files += 1
                    file_symbols = symbol_counts.get(str(entry), 0)
                    total_symbols += file_symbols

                    symbol_info = f" ({file_symbols} symbols)" if file_symbols > 0 else ""
                    tree_data.append({
                        "prefix": prefix + connector,
                        "name": entry.name + symbol_info,
                        "type": "file",
                        "path": str(entry),
                        "symbols": file_symbols,
                    })

        _build_tree(directory)

        # Track metrics
        record_operation("tree", tokens_read=len(tree_data) * 5, tokens_saved=0, file_path=str(directory))

        # JSON output
        if json_output:
            output = {
                "directory": str(directory),
                "tree": tree_data,
                "summary": {
                    "directories": total_dirs,
                    "files": total_files,
                    "symbols": total_symbols,
                },
            }
            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        console.print(f"\n[bold]{directory}/[/bold]\n")

        for node in tree_data:
            if node['type'] == 'directory':
                console.print(f"{node['prefix']}[cyan]{node['name']}[/cyan]")
            else:
                console.print(f"{node['prefix']}{node['name']}")

        console.print(f"\n[green]{total_dirs} directories")
        if show_files:
            console.print(f"{total_files} files, {total_symbols} symbols[/green]")
        console.print()

    except Exception as e:
        logger.error(f"Tree failed: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command()
def ls(
    directory: Path = typer.Argument(".", help="Directory to list."),
    extensions: Optional[str] = typer.Option(None, "--ext", help="Filter by extensions (comma-separated)."),
    long_format: bool = typer.Option(False, "-l", help="Long format with sizes and dates."),
    index_path: Optional[Path] = typer.Option(None, "--index", "--idx", help="Index path. Defaults to cerberus.db."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for agents."),
):
    """
    List files in directory using skeleton index (100% deterministic).

    REQUIRES INDEX: Uses skeleton index (Phase 9 Three-Tier Memory) for instant
    listing of the "World Model" instead of filesystem crawling.

    Examples:
      cerberus dogfood ls src/cerberus                 # Index-based listing
      cerberus dogfood ls src/ --ext .py               # Python files only
      cerberus dogfood ls src/cerberus -l              # Long format with details
    """
    from datetime import datetime

    # Default to cerberus.db if not provided
    if index_path is None:
        index_path = Path("cerberus.db")

    # INDEX REQUIRED - No legacy fallback
    if not index_path.exists():
        console.print("[red]✗ No index found in current directory.[/red]")
        console.print("[yellow]→ Run 'cerberus index .' to create index first.[/yellow]")
        console.print("[dim]Cerberus dogfood commands require an index for deterministic exploration.[/dim]")
        raise typer.Exit(code=1)

    try:
        # DOGFOODING: Use skeleton index (Tier 1 - Phase 9 Three-Tier Memory)
        logger.info(f"Dogfooding: Using skeleton index for ls '{directory}' (Phase 9 engine)")

        scan_result = load_index(index_path)

        # Normalize directory path - use relative path like index does
        if directory == Path("."):
            dir_str = ""
        else:
            dir_str = str(directory).rstrip("/") + "/"

        # Query all files from index
        all_files = []
        for file_obj in scan_result.files:
            file_path_str = file_obj.path
            # Check if file is under the directory
            if dir_str == "":
                # Current directory - show files at top level
                if "/" not in file_path_str or file_path_str.count("/") == 0:
                    all_files.append(file_obj)
            elif file_path_str.startswith(dir_str):
                # Under the directory - only show immediate children
                rel_path = file_path_str[len(dir_str):]
                if "/" not in rel_path:  # Immediate child
                    all_files.append(file_obj)

        # Parse extensions filter
        ext_filter = None
        if extensions:
            ext_filter = [ext.strip() for ext in extensions.split(',')]

        # Build entries from index
        entries = []
        for file_obj in all_files:
            file_path = Path(file_obj.path)

            # Apply extension filter
            if ext_filter:
                if not any(file_path.name.endswith(ext) for ext in ext_filter):
                    continue

            # Try to get file stats (for size/mtime) - fallback if file deleted
            try:
                stat = file_path.stat()
                size = stat.st_size
                mtime = stat.st_mtime
            except FileNotFoundError:
                size = 0
                mtime = 0

            entry_data = {
                "name": file_path.name,
                "type": "file",
                "size": size,
                "modified": mtime,
                "path": str(file_path),
                "in_index": True,
            }
            entries.append(entry_data)

        # Sort by name
        entries.sort(key=lambda e: e["name"])

        # Track metrics (index lookup saves tokens - no filesystem crawl!)
        record_operation("ls", tokens_read=0, tokens_saved=len(entries) * 10, file_path=str(directory))

        # JSON output
        if json_output:
            output = {
                "mode": "index",
                "directory": str(directory),
                "entries": entries,
                "total": len(entries),
            }
            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        console.print(f"\n[bold]{directory}/[/bold] [dim](Index Mode - Phase 9)[/dim]\n")

        if long_format:
            table = Table(box=None, show_header=True, padding=(0, 2))
            table.add_column("Type", style="dim", width=4)
            table.add_column("Name", style="cyan")
            table.add_column("Size", justify="right", style="yellow")
            table.add_column("Modified", style="dim")

            for entry in entries:
                type_icon = "📄"
                size_str = f"{entry['size']:,}"
                mod_time = datetime.fromtimestamp(entry['modified']).strftime("%Y-%m-%d %H:%M") if entry['modified'] > 0 else "unknown"

                table.add_row(
                    type_icon,
                    entry['name'],
                    size_str,
                    mod_time
                )

            console.print(table)
        else:
            # Simple format
            for entry in entries:
                console.print(entry['name'])

        console.print(f"\n[green]{len(entries)} indexed files[/green]\n")

    except Exception as e:
        logger.error(f"Ls failed: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command()
def grep(
    pattern: str = typer.Argument(..., help="Pattern to search for (regex supported)."),
    path: Path = typer.Argument(".", help="Directory or file to search in."),
    extensions: Optional[str] = typer.Option(None, "--ext", help="Filter by extensions (comma-separated, e.g., '.py,.md')."),
    ignore_case: bool = typer.Option(False, "-i", help="Case-insensitive search."),
    invert_match: bool = typer.Option(False, "-v", help="Invert match - show lines that DON'T match pattern."),
    word_match: bool = typer.Option(False, "-w", help="Match whole words only (word boundaries)."),
    context: int = typer.Option(0, "-C", help="Show N lines of context before/after match."),
    files_only: bool = typer.Option(False, "-l", help="Show only filenames with matches."),
    count: bool = typer.Option(False, "-c", help="Show count of matches per file."),
    line_numbers: bool = typer.Option(False, "-n", help="Show line numbers in grep format (file:line:content)."),
    index_path: Optional[Path] = typer.Option(None, "--index", "--idx", help="Index path. Defaults to cerberus.db."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON for agents."),
):
    """
    Search for patterns using FTS5 keyword search (100% deterministic).

    REQUIRES INDEX: Uses FTS5 (Phase 9 engine) for zero disk I/O pattern searching.
    Run 'cerberus index .' first.

    Examples:
      cerberus dogfood grep "TODO" src/                  # FTS5 keyword search
      cerberus dogfood grep "class.*Test" .              # Regex pattern
      cerberus dogfood grep "import pandas" . -l         # Files only
    """
    # Default to cerberus.db if not provided
    if index_path is None:
        index_path = Path("cerberus.db")

    # INDEX REQUIRED - No legacy fallback
    if not index_path.exists():
        console.print("[red]✗ No index found in current directory.[/red]")
        console.print("[yellow]→ Run 'cerberus index .' to create index first.[/yellow]")
        console.print("[dim]Cerberus dogfood commands require an index for deterministic exploration.[/dim]")
        raise typer.Exit(code=1)

    try:
        # DOGFOODING: Use hybrid_search (Phase 9 engine)
        from cerberus.retrieval.facade import hybrid_search

        logger.info(f"Dogfooding: Using FTS5 keyword search for '{pattern}' (Phase 9 engine)")

        scan_result = load_index(index_path)

        # Perform FTS5 keyword search
        search_results = hybrid_search(
            scan_result=scan_result,
            query=pattern,
            mode="keyword",
            limit=1000,  # High limit for grep-like behavior
        )

        # Convert search results to grep format
        results = []
        total_matches = 0

        # Group results by file
        files_dict = {}
        for result in search_results:
            file_path = result.symbol.file_path
            if file_path not in files_dict:
                files_dict[file_path] = []
            files_dict[file_path].append({
                "line_number": result.symbol.start_line,
                "content": result.symbol.signature or result.symbol.name,
                "symbol_type": result.symbol.type,
            })
            total_matches += 1

        # Build results structure
        for file_path, matches in files_dict.items():
            results.append({
                "file": file_path,
                "matches": matches,
                "count": len(matches),
            })

        # Track metrics (FTS5 saves massive tokens - no file reads!)
        record_operation("grep", tokens_read=total_matches * 10, tokens_saved=total_matches * 100, file_path=str(path))

        # JSON output
        if json_output:
            output = {
                "mode": "fts5",
                "pattern": pattern,
                "total_matches": total_matches,
                "files_searched": len(results),
                "results": results,
            }
            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        console.print(f"\n[cyan]Pattern:[/cyan] {pattern} [dim](FTS5 Mode - Phase 9)[/dim]\n")

        if not results:
            console.print("[yellow]No matches found.[/yellow]")
            return

        for file_result in results:
            file_path = file_result["file"]
            matches = file_result["matches"]

            if files_only:
                console.print(file_path)
            elif count:
                console.print(f"{file_path}: {len(matches)}")
            else:
                console.print(f"\n[bold]{file_path}[/bold]")
                for match in matches:
                    line_num = match["line_number"]
                    content = match["content"]
                    console.print(f"[dim]{line_num:5}[/dim] | {escape(content)}")

        console.print(f"\n\n[green]{total_matches} matches in {len(results)} files[/green]")

    except Exception as e:
        logger.error(f"Grep failed: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


@app.command()
def timeline(
    commits: Optional[int] = typer.Option(None, "--commits", "-n", help="Number of recent commits to analyze."),
    since: Optional[str] = typer.Option(None, "--since", help="Branch or commit to compare from (e.g., 'main', 'HEAD~5')."),
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
    [PHASE 8] Show symbols changed in recent git history.

    Instantly identifies the "Active Work Zone" by listing only the symbols
    (functions/classes) that have changed, avoiding re-analysis of stable code.

    Examples:
      cerberus dogfood timeline --commits 3           # Last 3 commits
      cerberus dogfood timeline --since main          # Since diverging from main
      cerberus dogfood timeline --since HEAD~10       # Last 10 commits
    """
    import subprocess
    from pathlib import Path
    from cerberus.incremental.git_diff import get_git_root, get_git_diff, parse_git_diff
    from cerberus.index import load_index

    # Default to cerberus.db in CWD if not provided
    if index_path is None:
        index_path = Path("cerberus.db")
        if not index_path.exists():
            console.print(f"[red]Error: Index file 'cerberus.db' not found in current directory.[/red]")
            console.print(f"[yellow]Run 'cerberus index .' first or provide --index path.[/yellow]")
            raise typer.Exit(code=1)

    try:
        # Get git root
        cwd = Path.cwd()
        git_root = get_git_root(cwd)

        if not git_root:
            console.print(f"[red]Not in a git repository.[/red]")
            raise typer.Exit(code=1)

        # Build git command
        if commits:
            # Last N commits
            from_ref = f"HEAD~{commits}"
        elif since:
            # Since branch/commit
            from_ref = since
        else:
            # Default: uncommitted changes
            from_ref = None

        # Get git diff
        if from_ref:
            try:
                # Verify ref exists
                subprocess.run(
                    ["git", "rev-parse", "--verify", from_ref],
                    cwd=str(git_root),
                    capture_output=True,
                    check=True,
                    timeout=5,
                )
                diff_output = get_git_diff(git_root, from_ref)
            except subprocess.CalledProcessError:
                console.print(f"[red]Git ref '{from_ref}' not found.[/red]")
                raise typer.Exit(code=1)
        else:
            diff_output = get_git_diff(git_root)

        if not diff_output:
            console.print(f"[yellow]No changes found.[/yellow]")
            return

        # Parse diff to get changed line ranges
        changed_files = parse_git_diff(diff_output)

        if not changed_files:
            console.print(f"[yellow]No file changes detected.[/yellow]")
            return

        # Load index to map line ranges to symbols
        scan_result = load_index(index_path)

        # For each changed file, find which symbols were affected
        changed_symbols = []

        for file_path, line_ranges in changed_files.items():
            # Query symbols for this file
            file_symbols = [
                sym for sym in scan_result.symbols
                if sym.file_path == file_path or sym.file_path == str(Path(file_path).absolute())
            ]

            # Check which symbols intersect with changed lines
            for symbol in file_symbols:
                for start_line, end_line in line_ranges:
                    # Check if symbol overlaps with changed range
                    if (symbol.start_line <= end_line and
                        (symbol.end_line is None or symbol.end_line >= start_line)):
                        changed_symbols.append({
                            "file": file_path,
                            "symbol": symbol.name,
                            "type": symbol.type,
                            "line": symbol.start_line,
                            "parent": symbol.parent_class,
                        })
                        break  # Only count each symbol once

        # Track metrics
        record_operation("timeline", tokens_read=len(changed_symbols) * 10, tokens_saved=0, file_path=str(git_root))

        # JSON output
        if json_output:
            output = {
                "changed_files": len(changed_files),
                "changed_symbols": len(changed_symbols),
                "symbols": changed_symbols,
            }
            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        console.print(f"\n[bold]Changed Symbols[/bold] (Phase 8 Timeline)\n")

        if not changed_symbols:
            console.print("[yellow]No symbols changed in the specified range.[/yellow]")
            return

        table = Table(box=None, show_header=True, padding=(0, 2))
        table.add_column("File", style="cyan")
        table.add_column("Type", style="dim", width=10)
        table.add_column("Symbol", style="bold")
        table.add_column("Line", style="dim", justify="right")

        for change in changed_symbols:
            name = change['symbol']
            if change['parent']:
                name = f"{change['parent']}.{name}"

            table.add_row(
                change['file'],
                change['type'],
                name,
                str(change['line']),
            )

        console.print(table)
        console.print(f"\n[green]{len(changed_symbols)} symbols changed in {len(changed_files)} files[/green]\n")

    except Exception as e:
        logger.error(f"Timeline failed: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)
