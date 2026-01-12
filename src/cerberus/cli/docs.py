"""
Documentation Access Command

Provides access to Cerberus documentation files without hardcoded paths.
Works for any Cerberus installation (local dev, pip install, system install).
"""

import typer
from pathlib import Path
from typing import Optional

from cerberus.cli.output import get_console
from cerberus.logging_config import logger

app = typer.Typer()
console = get_console()


def get_docs_dir() -> Optional[Path]:
    """
    Auto-discover Cerberus documentation directory.

    Tries multiple locations:
    1. Development: ~/Desktop/Dev/Cerberus/
    2. Config: ~/.config/cerberus/docs/
    3. Package: Relative to this module
    """
    # Try development location first
    dev_path = Path.home() / "Desktop" / "Dev" / "Cerberus"
    if dev_path.exists() and (dev_path / "CERBERUS.md").exists():
        return dev_path

    # Try config location
    config_path = Path.home() / ".config" / "cerberus" / "docs"
    if config_path.exists() and (config_path / "CERBERUS.md").exists():
        return config_path

    # Try package location (relative to this file)
    # src/cerberus/cli/docs.py -> go up 3 levels to repo root
    package_path = Path(__file__).parent.parent.parent.parent
    if package_path.exists() and (package_path / "CERBERUS.md").exists():
        return package_path

    return None


@app.command("commands")
def show_commands(
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Display CERBERUS-COMMANDS.md (full command reference).

    Usage:
        cerberus docs commands
        cerberus docs commands --json
    """
    docs_dir = get_docs_dir()

    if not docs_dir:
        console.print("[red]Error: Could not locate Cerberus documentation.[/red]")
        console.print("Tried:")
        console.print("  - ~/Desktop/Dev/Cerberus/")
        console.print("  - ~/.config/cerberus/docs/")
        console.print("  - Package installation")
        raise typer.Exit(1)

    commands_file = docs_dir / "CERBERUS-COMMANDS.md"

    if not commands_file.exists():
        console.print(f"[red]Error: CERBERUS-COMMANDS.md not found at {docs_dir}[/red]")
        raise typer.Exit(1)

    content = commands_file.read_text(encoding="utf-8")

    if json:
        import json as json_module
        output = {
            "file": "CERBERUS-COMMANDS.md",
            "path": str(commands_file),
            "content": content
        }
        console.print(json_module.dumps(output, indent=2))
    else:
        console.print(content)


@app.command("architecture")
def show_architecture(
    json: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Display CERBERUS-ARCHITECTURE.md (internals & configuration).

    Usage:
        cerberus docs architecture
        cerberus docs architecture --json
    """
    docs_dir = get_docs_dir()

    if not docs_dir:
        console.print("[red]Error: Could not locate Cerberus documentation.[/red]")
        raise typer.Exit(1)

    arch_file = docs_dir / "CERBERUS-ARCHITECTURE.md"

    if not arch_file.exists():
        console.print(f"[red]Error: CERBERUS-ARCHITECTURE.md not found at {docs_dir}[/red]")
        raise typer.Exit(1)

    content = arch_file.read_text(encoding="utf-8")

    if json:
        import json as json_module
        output = {
            "file": "CERBERUS-ARCHITECTURE.md",
            "path": str(arch_file),
            "content": content
        }
        console.print(json_module.dumps(output, indent=2))
    else:
        console.print(content)


@app.command("path")
def show_path():
    """
    Display the path to Cerberus documentation directory.

    Useful for agents to discover where docs are installed.

    Usage:
        cerberus docs path
    """
    docs_dir = get_docs_dir()

    if not docs_dir:
        console.print("[red]Error: Could not locate Cerberus documentation.[/red]")
        raise typer.Exit(1)

    console.print(str(docs_dir))


@app.command("quick")
def show_quick():
    """
    Display quick reference (common commands only).

    AI Agent-friendly: Essential commands without full reference.

    Usage:
        cerberus docs quick
    """
    quick_ref = """
CERBERUS QUICK REFERENCE

CRITICAL: Always load memory first
  cerberus memory context --compact --json

Common Commands:
  cerberus orient <dir>                    - Directory overview
  cerberus go <file>                       - File symbols with line numbers
  cerberus retrieval search "query"        - Find symbols (NOT 'cerberus search')
  cerberus retrieval get-symbol <name>     - Symbol details with snippet
  cerberus retrieval blueprint <dir>       - Architecture overview

After Exploration (Use Direct Tools):
  Read <file> lines X-Y                    - Get actual code for editing
  Edit <file>                              - Make changes

Full Reference:
  cerberus docs commands                   - All commands
  cerberus docs architecture               - Internals & config

Memory Commands:
  cerberus memory learn --correction "..."  - Record mistake to avoid
  cerberus memory learn --decision "..."    - Record architectural decision
  cerberus memory context --compact --json  - Get all patterns/corrections
"""
    console.print(quick_ref)


@app.command("list")
def list_docs():
    """
    List all available documentation files.

    Usage:
        cerberus docs list
    """
    docs_dir = get_docs_dir()

    if not docs_dir:
        console.print("[red]Error: Could not locate Cerberus documentation.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Cerberus Documentation Location:[/bold] {docs_dir}\n")

    doc_files = [
        ("CERBERUS.md", "Core guide (always load)"),
        ("CERBERUS-COMMANDS.md", "Full command reference"),
        ("CERBERUS-ARCHITECTURE.md", "Internals & configuration"),
        ("CERBERUS-DEVELOPMENT.md", "Contributing guide"),
        ("CERBERUS-LEADERSHIP.md", "Agent pushback playbook"),
        ("HANDOFF.md", "Development state tracking"),
    ]

    for filename, description in doc_files:
        filepath = docs_dir / filename
        if filepath.exists():
            console.print(f"  ✓ {filename:30s} - {description}")
        else:
            console.print(f"  ✗ {filename:30s} - {description} [dim](not found)[/dim]")
