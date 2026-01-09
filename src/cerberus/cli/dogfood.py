"""
CLI Dogfood Commands

read, inspect, tree, ls, grep, timeline
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

app = typer.Typer()
console = Console()

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
            console.print(f"[dim]{i:5}[/dim] | {escape(line)}")

    except Exception as e:
        logger.error(f"Read failed: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
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
        console.print(f"[red]Error: {escape(str(e))}[/red]")
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
        console.print(f"[red]Error: {escape(str(e))}[/red]")
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
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)



@app.command()
def grep(
    pattern: str = typer.Argument(..., help="Pattern to search for (regex supported)."),
    path: Path = typer.Argument(".", help="Directory or file to search in."),
    extensions: Optional[str] = typer.Option(None, "--ext", help="Filter by file extensions (comma-separated)."),
    ignore_case: bool = typer.Option(False, "-i", help="Case-insensitive search."),
    invert_match: bool = typer.Option(False, "-v", help="Invert match - show lines that DON'T match pattern."),
    word_match: bool = typer.Option(False, "-w", help="Match whole words only (word boundaries)."),
    context: int = typer.Option(0, "-C", help="Show N lines of context before/after match."),
    files_only: bool = typer.Option(False, "-l", help="Show only filenames with matches."),
    count: bool = typer.Option(False, "-c", help="Show count of matches per file."),
    line_numbers: bool = typer.Option(False, "-n", help="Show line numbers in grep format (file:line:content)."),
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

        # Add word boundaries if -w flag
        if word_match:
            pattern = r'\b' + pattern + r'\b'

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
                    # Check if line matches (or doesn't match if -v is used)
                    line_matches = bool(regex.search(line))
                    if invert_match:
                        line_matches = not line_matches

                    if line_matches:
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
            elif line_numbers:
                # grep -n style: file:line:content
                for match in result["matches"]:
                    typer.echo(f"{result['file']}:{match['line_number']}:{match['content']}")
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
            console.print(f"[dim]Run 'cerberus index .' first or provide --index path.[/dim]")
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

        # Parse diff to get changed files and line ranges
        added_files, modified_files, deleted_files = parse_git_diff(diff_output, git_root)

        # Load index
        scan_result = load_index(index_path)

        # Track changed symbols
        changed_symbols = []

        # Process modified files
        for mod_file in modified_files:
            file_path = str(mod_file.path)

            # Get all symbols in this file
            file_symbols = list(scan_result._store.query_symbols(filter={'file_path': file_path}))

            # Check which symbols overlap with changed line ranges
            for sym in file_symbols:
                for line_range in mod_file.changed_lines:
                    # Check if symbol overlaps with changed lines
                    if not (sym.end_line < line_range.start or sym.start_line > line_range.end):
                        changed_symbols.append({
                            'file': file_path,
                            'symbol': sym.name,
                            'type': sym.type,
                            'line': sym.start_line,
                            'change_type': 'modified'
                        })
                        break  # Count symbol once even if multiple ranges overlap

        # Process added files
        for file_path in added_files:
            file_symbols = list(scan_result._store.query_symbols(filter={'file_path': str(file_path)}))
            for sym in file_symbols:
                changed_symbols.append({
                    'file': str(file_path),
                    'symbol': sym.name,
                    'type': sym.type,
                    'line': sym.start_line,
                    'change_type': 'added'
                })

        # Process deleted files
        for file_path in deleted_files:
            changed_symbols.append({
                'file': str(file_path),
                'symbol': '<entire file>',
                'type': 'file',
                'line': 0,
                'change_type': 'deleted'
            })

        # Deduplicate
        seen = set()
        unique_changes = []
        for item in changed_symbols:
            key = (item['file'], item['symbol'], item['line'])
            if key not in seen:
                seen.add(key)
                unique_changes.append(item)

        if json_output:
            output = {
                'ref': from_ref or 'working tree',
                'total_symbols': len(unique_changes),
                'changes': unique_changes
            }
            typer.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        ref_desc = f"since {from_ref}" if from_ref else "in working tree"
        console.print(f"\n[bold cyan]Timeline: Changed symbols {ref_desc}[/bold cyan]")
        console.print(f"[dim]{len(unique_changes)} symbols affected[/dim]\n")

        # Group by change type
        by_type = {'added': [], 'modified': [], 'deleted': []}
        for item in unique_changes:
            by_type[item['change_type']].append(item)

        # Display by type
        for change_type, items in by_type.items():
            if not items:
                continue

            if change_type == 'added':
                color = 'green'
                label = 'Added'
            elif change_type == 'modified':
                color = 'yellow'
                label = 'Modified'
            else:
                color = 'red'
                label = 'Deleted'

            console.print(f"[bold {color}]{label} ({len(items)}):[/bold {color}]")
            for item in items:
                sym_display = f"{item['type']} {item['symbol']}" if item['type'] != 'file' else item['symbol']
                console.print(f"  [{color}]{sym_display}[/{color}] [dim]- {item['file']}:{item['line']}[/dim]")
            console.print()

        # Record operation
        record_operation('timeline', tokens_read=0, tokens_saved=0, file_path=None)

    except Exception as e:
        logger.error(f"Timeline failed: {e}")
        console.print(f"[red]Error: {escape(str(e))}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


