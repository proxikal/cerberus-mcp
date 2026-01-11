"""
CLI Workflow Commands (Phase 19.1)

Streamlined entry points for efficient Cerberus workflows.

Commands:
  start  - Single command to initialize an efficient session
  go     - Blueprint + actionable read suggestions for a file
  orient - Full situational awareness for a directory/project
"""

import json
import typer
from pathlib import Path
from typing import Optional
from datetime import datetime

from rich.markup import escape

from cerberus.cli.output import get_console
from cerberus.cli.config import CLIConfig
from cerberus.logging_config import logger
# Phase 19.3: Efficiency tracking
from cerberus.metrics.efficiency import get_efficiency_tracker
# Phase 19.7: Protocol tracking
from cerberus.protocol import get_protocol_tracker
from cerberus.cli.hints import EfficiencyHints, HintCollector

app = typer.Typer()
console = get_console()


def _format_number(n: int) -> str:
    """Format number with thousands separator."""
    return f"{n:,}"


def _get_index_health(index_path: Path) -> dict:
    """Check index health and return status info."""
    if not index_path.exists():
        return {
            "healthy": False,
            "exists": False,
            "message": "No index found",
            "symbol_count": 0,
            "file_count": 0,
        }

    try:
        from cerberus.index import load_index

        scan_result = load_index(index_path)
        symbol_count = len(scan_result.symbols)
        file_count = len(scan_result.files)

        return {
            "healthy": True,
            "exists": True,
            "message": f"healthy, {_format_number(symbol_count)} symbols",
            "symbol_count": symbol_count,
            "file_count": file_count,
        }
    except Exception as e:
        return {
            "healthy": False,
            "exists": True,
            "message": f"Error: {str(e)[:50]}",
            "symbol_count": 0,
            "file_count": 0,
        }


def _get_watcher_status(project_path: Path) -> dict:
    """Check watcher status and return info."""
    try:
        from cerberus.watcher import watcher_status

        status = watcher_status(project_path)
        if status.running:
            return {
                "running": True,
                "pid": status.pid,
                "message": f"Running (PID {status.pid})",
            }
        else:
            return {
                "running": False,
                "pid": None,
                "message": "Not running",
            }
    except Exception as e:
        return {
            "running": False,
            "pid": None,
            "message": f"Error checking: {str(e)[:30]}",
        }


def _get_memory_summary() -> dict:
    """Get Session Memory summary."""
    try:
        from cerberus.memory.store import MemoryStore
        from cerberus.memory.profile import ProfileManager
        from cerberus.memory.decisions import DecisionManager
        from cerberus.memory.corrections import CorrectionManager

        store = MemoryStore()
        profile_manager = ProfileManager(store)
        decision_manager = DecisionManager(store)
        correction_manager = CorrectionManager(store)

        profile = profile_manager.load_profile()

        # Count preferences
        pref_count = 0
        if profile.coding_style:
            pref_count += len(profile.coding_style)
        if profile.naming_conventions:
            pref_count += len(profile.naming_conventions)
        if profile.anti_patterns:
            pref_count += len(profile.anti_patterns)
        if profile.general:
            pref_count += len(profile.general)

        # Get project decisions
        detected_project = decision_manager.detect_project_name()
        decision_count = 0
        if detected_project:
            decisions = decision_manager.load_decisions(detected_project)
            decision_count = len(decisions.decisions)

        # Get corrections
        corrections = correction_manager.load_corrections()
        correction_count = len(corrections.corrections)

        return {
            "preferences": pref_count,
            "decisions": decision_count,
            "corrections": correction_count,
            "project": detected_project,
            "has_content": pref_count > 0 or decision_count > 0 or correction_count > 0,
        }
    except Exception as e:
        logger.debug(f"Error getting memory summary: {e}")
        return {
            "preferences": 0,
            "decisions": 0,
            "corrections": 0,
            "project": None,
            "has_content": False,
        }


def _get_developer_context() -> list:
    """Get formatted developer context from Session Memory."""
    try:
        from cerberus.memory.profile import ProfileManager

        manager = ProfileManager()
        profile = manager.load_profile()

        context_items = []

        # Add coding style preferences
        if profile.coding_style:
            if profile.coding_style.get("prefer_early_returns"):
                context_items.append("Prefer early returns")
            if profile.coding_style.get("async_style") == "async_await":
                context_items.append("Use async/await over callbacks")
            if profile.coding_style.get("quotes") == "single":
                context_items.append("Single quotes for strings")
            elif profile.coding_style.get("quotes") == "double":
                context_items.append("Double quotes for strings")

        # Add general preferences
        if profile.general:
            for pref in profile.general[:3]:  # Limit to 3
                context_items.append(pref)

        return context_items[:5]  # Max 5 items
    except Exception:
        return []


@app.command()
def start(
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
    ),
    project_path: Optional[Path] = typer.Option(
        None,
        "--project",
        "-p",
        help="Path to project (default: current directory).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON for agents.",
    ),
):
    """
    Initialize a Cerberus session with health checks and context.

    Single command that:
    - Checks index health (cerberus.db)
    - Checks watcher status
    - Loads and displays Session Memory summary

    Examples:
      cerberus start                    # Start session in current directory
      cerberus start --project ~/code   # Start for specific project
    """
    if project_path is None:
        project_path = Path.cwd()

    if index_path is None:
        index_path = Path("cerberus.db")

    # Gather status info
    index_status = _get_index_health(index_path)
    watcher_status = _get_watcher_status(project_path)
    memory_summary = _get_memory_summary()
    dev_context = _get_developer_context()

    if json_output or CLIConfig.is_machine_mode():
        output = {
            "status": "initialized",
            "index": {
                "path": str(index_path),
                "healthy": index_status["healthy"],
                "exists": index_status["exists"],
                "symbol_count": index_status["symbol_count"],
                "file_count": index_status["file_count"],
            },
            "watcher": {
                "running": watcher_status["running"],
                "pid": watcher_status["pid"],
            },
            "memory": {
                "preferences": memory_summary["preferences"],
                "decisions": memory_summary["decisions"],
                "corrections": memory_summary["corrections"],
                "project": memory_summary["project"],
            },
            "context": dev_context,
            "next_command": "cerberus go <file>",
        }
        typer.echo(json.dumps(output, separators=(",", ":")))
        return

    # Human mode output
    console.print("\n[bold]Cerberus Session Initialized[/bold]")
    console.print("-" * 30)

    # Index status
    if index_status["healthy"]:
        console.print(f"Index: {index_path} ([green]{index_status['message']}[/green])")
    elif index_status["exists"]:
        console.print(f"Index: {index_path} ([yellow]{index_status['message']}[/yellow])")
    else:
        console.print(f"Index: [yellow]{index_status['message']}[/yellow]")
        console.print("  [dim]Run 'cerberus index .' to create index[/dim]")

    # Watcher status
    if watcher_status["running"]:
        console.print(f"Watcher: [green]{watcher_status['message']}[/green]")
    else:
        console.print(f"Watcher: [yellow]{watcher_status['message']}[/yellow]")

    # Memory summary
    mem_parts = []
    if memory_summary["preferences"] > 0:
        mem_parts.append(f"{memory_summary['preferences']} preferences")
    if memory_summary["decisions"] > 0:
        mem_parts.append(f"{memory_summary['decisions']} decisions")
    if memory_summary["corrections"] > 0:
        mem_parts.append(f"{memory_summary['corrections']} corrections")

    if mem_parts:
        console.print(f"Memory: {', '.join(mem_parts)} loaded")
    else:
        console.print("Memory: [dim](empty)[/dim]")

    # Developer context
    if dev_context:
        console.print("\n[cyan]Developer Context:[/cyan]")
        for item in dev_context:
            console.print(f"  - {item}")

    console.print(f"\n[dim]Ready. Use `cerberus go <file>` to begin exploration.[/dim]")

    # Phase 19.3: Track metrics
    try:
        tracker = get_efficiency_tracker()
        flags = []
        if memory_summary["has_content"]:
            flags.append("--with-memory-context")
        tracker.record_command("start", flags)
    except Exception:
        pass  # Don't fail command if metrics fail

    # Phase 19.7: Track protocol usage and check for refresh hint
    try:
        protocol_tracker = get_protocol_tracker()
        protocol_tracker.record_command("start")

        # Check if refresh hint should be shown
        hint = EfficiencyHints.check_protocol_refresh()
        if hint and not json_output:
            console.print(f"\n[dim]{hint.to_human()}[/dim]")
    except Exception:
        pass  # Don't fail command if protocol tracking fails


@app.command()
def go(
    file_path: Path = typer.Argument(
        ...,
        help="File to analyze with blueprint.",
    ),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
    ),
    threshold: int = typer.Option(
        30,
        "--threshold",
        "-t",
        help="Line threshold for 'heavy' symbols.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON for agents.",
    ),
):
    """
    Blueprint + actionable read suggestions for a file.

    Runs blueprint on a file and identifies heavy symbols (>30 lines by default),
    generating copy-pasteable read commands for quick exploration.

    Examples:
      cerberus go src/auth/service.py           # Analyze file
      cerberus go src/main.py --threshold 50    # Custom threshold
    """
    from cerberus.index import load_index

    if index_path is None:
        index_path = Path("cerberus.db")

    # Check file exists
    if not file_path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(code=1)

    # Check index exists
    if not index_path.exists():
        console.print("[red]No index found. Run 'cerberus index .' first.[/red]")
        raise typer.Exit(code=1)

    scan_result = load_index(index_path)

    # Get file absolute path for matching
    file_absolute = file_path.resolve()
    file_str = str(file_absolute)

    # Query symbols for this file
    symbols = []
    for sym in scan_result.symbols:
        if sym.file_path == file_str or sym.file_path == str(file_path):
            symbols.append(sym)

    if not symbols:
        console.print(f"[yellow]File '{file_path}' not in index.[/yellow]")
        console.print("[dim]Run 'cerberus index .' to index this file.[/dim]")
        raise typer.Exit(code=1)

    # Sort by line number
    symbols.sort(key=lambda s: s.start_line)

    # Read file to get total lines
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        total_lines = len(f.readlines())

    # Build symbol tree and identify heavy symbols
    heavy_symbols = []
    symbol_data = []

    for sym in symbols:
        # Calculate symbol size
        end_line = sym.end_line if sym.end_line else sym.start_line
        size = end_line - sym.start_line + 1

        sym_info = {
            "name": sym.name,
            "type": sym.type,
            "start_line": sym.start_line,
            "end_line": end_line,
            "size": size,
            "parent_class": sym.parent_class,
            "signature": sym.signature,
            "is_heavy": size > threshold,
        }
        symbol_data.append(sym_info)

        if size > threshold:
            heavy_symbols.append(sym_info)

    # Generate quick read commands
    quick_reads = []

    # Sort heavy symbols by size (largest first)
    heavy_symbols.sort(key=lambda s: s["size"], reverse=True)

    for sym in heavy_symbols[:5]:  # Top 5 heavy symbols
        name = sym["name"]
        if sym["parent_class"]:
            name = f"{sym['parent_class']}.{name}"

        quick_reads.append({
            "command": f"read {file_path} lines {sym['start_line']}-{sym['end_line']}",
            "description": f"{name} ({sym['type']}, {sym['size']} lines)",
        })

    # Add class + init if there's a class
    for sym in symbol_data:
        if sym["type"] == "class" and not sym["is_heavy"]:
            # Find __init__ for this class
            init_sym = None
            for s in symbol_data:
                if s["name"] == "__init__" and s["parent_class"] == sym["name"]:
                    init_sym = s
                    break

            if init_sym:
                end = init_sym["end_line"]
            else:
                # Just show class header (first 15 lines or until first method)
                end = min(sym["start_line"] + 15, sym["end_line"])

            quick_reads.append({
                "command": f"read {file_path} lines {sym['start_line']}-{end}",
                "description": f"{sym['name']} class + init",
            })
            break

    if json_output or CLIConfig.is_machine_mode():
        output = {
            "file": str(file_path),
            "total_lines": total_lines,
            "symbol_count": len(symbols),
            "heavy_symbol_count": len(heavy_symbols),
            "threshold": threshold,
            "symbols": symbol_data,
            "quick_reads": quick_reads,
        }
        typer.echo(json.dumps(output, separators=(",", ":")))
        return

    # Human mode output - tree view
    console.print(f"\n[bold]{file_path}[/bold] ({total_lines} lines, {len(symbols)} symbols)")

    # Build tree structure
    classes = {}
    top_level = []

    for sym in symbol_data:
        if sym["parent_class"]:
            if sym["parent_class"] not in classes:
                classes[sym["parent_class"]] = []
            classes[sym["parent_class"]].append(sym)
        elif sym["type"] == "class":
            classes[sym["name"]] = classes.get(sym["name"], [])
            top_level.append(sym)
        else:
            top_level.append(sym)

    # Print tree
    for i, sym in enumerate(top_level):
        is_last_top = i == len(top_level) - 1
        prefix = "└── " if is_last_top else "├── "

        line_range = f"lines {sym['start_line']}-{sym['end_line']}"
        heavy_marker = " [yellow]<- Heavy ({} lines)[/yellow]".format(sym["size"]) if sym["is_heavy"] else ""

        if sym["type"] == "class":
            console.print(f"{prefix}[cyan]{sym['name']}[/cyan] [class] {'─' * 10} {line_range}{heavy_marker}")

            # Print class members
            members = classes.get(sym["name"], [])
            for j, member in enumerate(members):
                is_last_member = j == len(members) - 1
                member_prefix = "    └── " if is_last_member else "    ├── "
                if is_last_top:
                    member_prefix = "    " + member_prefix[4:]

                m_line_range = f"lines {member['start_line']}-{member['end_line']}"
                m_heavy = " [yellow]<- Heavy ({} lines)[/yellow]".format(member["size"]) if member["is_heavy"] else ""
                dots = "." * max(1, 25 - len(member["name"]))
                console.print(f"{member_prefix}{member['name']} [{member['type']}] {dots} {m_line_range}{m_heavy}")
        else:
            dots = "─" * max(1, 20 - len(sym["name"]))
            console.print(f"{prefix}[green]{sym['name']}[/green] [{sym['type']}] {dots} {line_range}{heavy_marker}")

    # Print quick reads
    if quick_reads:
        console.print("\n[cyan]Quick reads:[/cyan]")
        for qr in quick_reads[:5]:
            console.print(f"  {qr['command']}    [dim]# {qr['description']}[/dim]")

    # Phase 19.3: Track metrics
    try:
        tracker = get_efficiency_tracker()
        flags = [f"--threshold={threshold}"]
        if json_output:
            flags.append("--json")
        tracker.record_command("go", flags, lines_returned=total_lines)
    except Exception:
        pass  # Don't fail command if metrics fail

    # Phase 19.7: Track protocol usage and check for refresh hint
    try:
        protocol_tracker = get_protocol_tracker()
        protocol_tracker.record_command("go")

        # Check if refresh hint should be shown (append to output)
        hint = EfficiencyHints.check_protocol_refresh()
        if hint:
            if json_output or CLIConfig.is_machine_mode():
                # For JSON, append as hint
                pass  # Already handled by HintCollector in JSON output
            else:
                console.print(f"\n[dim]{hint.to_human()}[/dim]")
    except Exception:
        pass  # Don't fail command if protocol tracking fails


@app.command()
def orient(
    directory: Path = typer.Argument(
        ".",
        help="Directory to analyze (default: current directory).",
    ),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON for agents.",
    ),
):
    """
    Full situational awareness for a directory/project.

    Shows:
    - File counts and line totals
    - Index freshness
    - Hot spots (most complex files)
    - Recent git changes
    - Session Memory summary

    Examples:
      cerberus orient              # Analyze current directory
      cerberus orient src/         # Analyze specific directory
    """
    import subprocess

    if index_path is None:
        index_path = Path("cerberus.db")

    if not directory.exists():
        console.print(f"[red]Directory not found: {directory}[/red]")
        raise typer.Exit(code=1)

    # Get project name from git or directory
    project_name = directory.resolve().name
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            cwd=str(directory),
            timeout=5,
        )
        if result.returncode == 0:
            project_name = Path(result.stdout.strip()).name
    except Exception:
        pass

    # Count files and lines
    file_stats = {"py": 0, "js": 0, "ts": 0, "other": 0}
    total_lines = 0
    file_line_counts = []

    try:
        for file in directory.rglob("*"):
            if file.is_file() and not any(
                part.startswith(".") or part == "__pycache__" or part == "node_modules"
                for part in file.parts
            ):
                suffix = file.suffix.lower()
                if suffix == ".py":
                    file_stats["py"] += 1
                elif suffix == ".js":
                    file_stats["js"] += 1
                elif suffix in [".ts", ".tsx"]:
                    file_stats["ts"] += 1
                else:
                    file_stats["other"] += 1

                # Count lines for supported files
                if suffix in [".py", ".js", ".ts", ".tsx"]:
                    try:
                        with open(file, "r", encoding="utf-8", errors="ignore") as f:
                            lines = len(f.readlines())
                            total_lines += lines
                            file_line_counts.append((str(file), lines))
                    except Exception:
                        pass
    except Exception as e:
        logger.debug(f"Error counting files: {e}")

    # Get index info
    index_info = {"exists": False, "age_minutes": None, "stale": True}
    if index_path.exists():
        index_info["exists"] = True
        mtime = datetime.fromtimestamp(index_path.stat().st_mtime)
        age_seconds = (datetime.now() - mtime).total_seconds()
        index_info["age_minutes"] = int(age_seconds / 60)
        index_info["stale"] = age_seconds > 3600  # Consider stale after 1 hour

    # Get hot spots (files with most lines - proxy for complexity)
    hot_spots = []
    if index_path.exists():
        try:
            from cerberus.index import load_index

            scan_result = load_index(index_path)

            # Count symbols per file and use that + lines as complexity proxy
            file_complexity = {}
            for sym in scan_result.symbols:
                fp = sym.file_path
                if fp not in file_complexity:
                    file_complexity[fp] = {"symbols": 0, "lines": 0}
                file_complexity[fp]["symbols"] += 1

            # Get line counts for indexed files
            for fp, data in file_complexity.items():
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                        data["lines"] = len(f.readlines())
                except Exception:
                    pass

            # Sort by symbol count * lines as complexity score
            sorted_files = sorted(
                file_complexity.items(),
                key=lambda x: x[1]["symbols"] * (x[1]["lines"] / 100),
                reverse=True,
            )

            for fp, data in sorted_files[:5]:
                # Make path relative if possible
                try:
                    rel_path = Path(fp).relative_to(Path.cwd())
                except ValueError:
                    rel_path = Path(fp)

                hot_spots.append({
                    "file": str(rel_path),
                    "symbols": data["symbols"],
                    "lines": data["lines"],
                })
        except Exception as e:
            logger.debug(f"Error getting hot spots: {e}")

    # Get recent git changes
    recent_changes = []
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--name-only", "-n", "10", "--pretty=format:%h|%ar"],
            capture_output=True,
            text=True,
            cwd=str(directory),
            timeout=10,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            current_time = None
            seen_files = set()
            for line in lines:
                if "|" in line:
                    _, time_ago = line.split("|", 1)
                    current_time = time_ago
                elif line.strip() and current_time and line not in seen_files:
                    # Get line changes
                    try:
                        diff_result = subprocess.run(
                            ["git", "diff", "--shortstat", "HEAD~1", "--", line],
                            capture_output=True,
                            text=True,
                            cwd=str(directory),
                            timeout=5,
                        )
                        change_info = ""
                        if diff_result.returncode == 0 and diff_result.stdout.strip():
                            parts = diff_result.stdout.strip().split(",")
                            for part in parts:
                                if "insertion" in part:
                                    num = part.strip().split()[0]
                                    change_info = f"+{num} lines"
                                    break
                    except Exception:
                        change_info = ""

                    recent_changes.append({
                        "file": line,
                        "when": current_time,
                        "change": change_info,
                    })
                    seen_files.add(line)

                    if len(recent_changes) >= 5:
                        break
    except Exception as e:
        logger.debug(f"Error getting git changes: {e}")

    # Get memory summary
    memory_summary = _get_memory_summary()

    if json_output or CLIConfig.is_machine_mode():
        output = {
            "project": project_name,
            "directory": str(directory),
            "files": {
                "python": file_stats["py"],
                "javascript": file_stats["js"],
                "typescript": file_stats["ts"],
                "other": file_stats["other"],
                "total": sum(file_stats.values()),
            },
            "total_lines": total_lines,
            "index": index_info,
            "hot_spots": hot_spots,
            "recent_changes": recent_changes,
            "memory": {
                "preferences": memory_summary["preferences"],
                "decisions": memory_summary["decisions"],
                "corrections": memory_summary["corrections"],
            },
        }
        typer.echo(json.dumps(output, separators=(",", ":")))
        return

    # Human mode output
    console.print(f"\n[bold]Project: {project_name}[/bold] ({directory}/)")
    console.print("-" * (len(project_name) + 20))

    # File stats
    file_parts = []
    if file_stats["py"] > 0:
        file_parts.append(f"{file_stats['py']} Python files")
    if file_stats["js"] > 0:
        file_parts.append(f"{file_stats['js']} JavaScript files")
    if file_stats["ts"] > 0:
        file_parts.append(f"{file_stats['ts']} TypeScript files")

    if file_parts:
        console.print(f"Files: {', '.join(file_parts)}, {_format_number(total_lines)} lines")
    else:
        console.print(f"Files: {sum(file_stats.values())} total")

    # Index status
    if index_info["exists"]:
        if index_info["stale"]:
            console.print(f"Index: [yellow]Stale (last indexed {index_info['age_minutes']} minutes ago)[/yellow]")
        else:
            console.print(f"Index: [green]Current (last indexed {index_info['age_minutes']} minutes ago)[/green]")
    else:
        console.print("Index: [yellow]Not found - run 'cerberus index .'[/yellow]")

    # Hot spots
    if hot_spots:
        console.print("\n[cyan]Hot spots (most complex):[/cyan]")
        for i, hs in enumerate(hot_spots, 1):
            console.print(f"  {i}. {hs['file']}    Symbols:{hs['symbols']}  Lines:{hs['lines']}")

    # Recent changes
    if recent_changes:
        console.print("\n[cyan]Recent changes (git):[/cyan]")
        for change in recent_changes:
            change_str = f" ({change['change']})" if change["change"] else ""
            console.print(f"  - {change['file']} ({change['when']}{change_str})")

    # Memory summary
    mem_parts = []
    if memory_summary["preferences"] > 0:
        mem_parts.append(f"{memory_summary['preferences']} preferences")
    if memory_summary["decisions"] > 0:
        mem_parts.append(f"{memory_summary['decisions']} project decisions")

    if mem_parts:
        console.print(f"\nSession Memory loaded: {', '.join(mem_parts)}")
    console.print()

    # Phase 19.7: Track protocol usage and check for refresh hint
    try:
        protocol_tracker = get_protocol_tracker()
        protocol_tracker.record_command("orient")

        hint = EfficiencyHints.check_protocol_refresh()
        if hint and not json_output:
            console.print(f"[dim]{hint.to_human()}[/dim]")
    except Exception:
        pass  # Don't fail command if protocol tracking fails
