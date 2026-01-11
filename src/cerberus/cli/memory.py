"""
CLI Memory Commands (Phase 18)

Commands for Session Memory - capturing and injecting developer context.

Commands:
  learn     - Explicitly teach Session Memory something
  show      - Display stored memory
  context   - Generate injection context for a session
  extract   - Extract patterns from git history
  forget    - Remove a memory entry
  stats     - Show storage statistics
  edit      - Open a memory file in your editor
  export    - Export memory for backup or sharing
  import    - Import memory from backup file
"""

import json
import typer
from typing import Optional

from rich.markup import escape

from cerberus.memory.store import MemoryStore
from cerberus.memory.profile import ProfileManager
from cerberus.memory.context import ContextGenerator
from cerberus.memory.decisions import DecisionManager
from cerberus.memory.corrections import CorrectionManager
from cerberus.memory.prompts import PromptManager
from cerberus.memory.extract import GitExtractor
from cerberus.cli.output import get_console

app = typer.Typer()
console = get_console()


@app.command()
def learn(
    text: str = typer.Argument(
        ...,
        help="The preference, decision, correction, or prompt name to learn"
    ),
    decision: bool = typer.Option(
        False,
        "--decision",
        "-d",
        help="Learn as a project decision"
    ),
    correction: bool = typer.Option(
        False,
        "--correction",
        "-c",
        help="Learn as a correction pattern"
    ),
    prompt: bool = typer.Option(
        False,
        "--prompt",
        help="Learn as an effective prompt"
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project name for decisions (auto-detected from git if not provided)"
    ),
    rationale: Optional[str] = typer.Option(
        None,
        "--rationale",
        "-r",
        help="Rationale for a decision"
    ),
    note: Optional[str] = typer.Option(
        None,
        "--note",
        "-n",
        help="Note for a correction"
    ),
    task_type: Optional[str] = typer.Option(
        None,
        "--task",
        "-t",
        help="Task type for a prompt (e.g., code-review, refactor, testing)"
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        help="Full template for a prompt (use {{variable}} for placeholders)"
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        help="Description for a prompt"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON"
    ),
):
    """
    Explicitly teach Session Memory something.

    Preferences (default):
      cerberus memory learn "prefer early returns"
      cerberus memory learn "always use async/await"
      cerberus memory learn "max line length 100"

    Decisions (--decision):
      cerberus memory learn --decision "chose SQLite for portability"
      cerberus memory learn -d "Parser: Use native ast" -r "accuracy"

    Corrections (--correction):
      cerberus memory learn --correction "AI keeps forgetting to log errors"
      cerberus memory learn -c "catch -> catch with logging" -n "Always log"

    Prompts (--prompt):
      cerberus memory learn --prompt "security-audit" --task code-review
      cerberus memory learn --prompt "owasp-check" -t security-audit --template "Review for OWASP..."
    """
    # Handle prompts
    if prompt:
        if not task_type:
            console.print("[red]Error: --task is required for prompts[/red]")
            console.print("[dim]Example: cerberus memory learn --prompt \"name\" --task code-review[/dim]")
            raise typer.Exit(code=1)

        manager = PromptManager()
        result = manager.learn_prompt(
            name=text,
            task_type=task_type,
            template=template,
            description=description,
            notes=note,
        )

        if json_output:
            typer.echo(json.dumps(result, indent=2))
        else:
            if result["success"]:
                typer.echo(f"Learned prompt '{text}' for {result['task_type']}")
            else:
                console.print(f"[red]Failed: {result['message']}[/red]")
                raise typer.Exit(code=1)
        return

    # Handle decisions
    if decision:
        manager = DecisionManager()
        result = manager.learn_decision(text, project=project, rationale=rationale)

        if json_output:
            typer.echo(json.dumps(result, indent=2))
        else:
            if result["success"]:
                typer.echo(f"Learned decision for {result['project']}: {result['decision']['topic']}")
            else:
                console.print(f"[red]Failed: {result['message']}[/red]")
                raise typer.Exit(code=1)
        return

    # Handle corrections
    if correction:
        manager = CorrectionManager()
        result = manager.learn_correction(text, note=note)

        if json_output:
            typer.echo(json.dumps(result, indent=2))
        else:
            if result["success"]:
                if result.get("is_new"):
                    typer.echo(f"Learned new correction: {result['message']}")
                else:
                    typer.echo(f"Updated correction: {result['message']}")
            else:
                console.print(f"[red]Failed: {result['message']}[/red]")
                raise typer.Exit(code=1)
        return

    # Default: learn as preference
    manager = ProfileManager()
    result = manager.learn(text)

    if json_output:
        typer.echo(json.dumps(result, indent=2))
    else:
        if result["success"]:
            typer.echo(result["message"])
            if result.get("category"):
                typer.echo(f"Category: {result['category']}")
        else:
            console.print(f"[red]Failed: {result['message']}[/red]")
            raise typer.Exit(code=1)


@app.command()
def show(
    section: Optional[str] = typer.Argument(
        None,
        help="Section to show: profile, decisions, corrections, prompts (default: all)"
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project name for decisions (auto-detected if not provided)"
    ),
    task_type: Optional[str] = typer.Option(
        None,
        "--task",
        "-t",
        help="Task type for prompts"
    ),
    top: int = typer.Option(
        10,
        "--top",
        help="Number of items to show for ranked lists"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON"
    ),
):
    """
    Display stored memory.

    Examples:
      cerberus memory show                       # Show all
      cerberus memory show profile               # Show profile only
      cerberus memory show decisions             # Show decisions
      cerberus memory show corrections --top 5   # Show top 5 corrections
      cerberus memory show prompts               # Show all prompts
      cerberus memory show prompts -t refactor   # Show prompts for refactor tasks
    """
    store = MemoryStore()
    section_lower = section.lower() if section else None

    # Handle JSON output for all sections
    if json_output:
        output = {}

        if section_lower is None or section_lower in ["all", "profile"]:
            profile_manager = ProfileManager(store)
            output["profile"] = profile_manager.load_profile().to_dict()

        if section_lower is None or section_lower in ["all", "decisions"]:
            decision_manager = DecisionManager(store)
            proj = project or decision_manager.detect_project_name()
            if proj:
                decisions = decision_manager.load_decisions(proj)
                output["decisions"] = {
                    "project": proj,
                    "decisions": [d.to_dict() for d in decisions.decisions]
                }
            output["available_projects"] = decision_manager.list_projects()

        if section_lower is None or section_lower in ["all", "corrections"]:
            correction_manager = CorrectionManager(store)
            corrections = correction_manager.load_corrections()
            output["corrections"] = [c.to_dict() for c in corrections.get_by_frequency(top)]

        if section_lower is None or section_lower in ["all", "prompts"]:
            prompt_manager = PromptManager(store)
            if task_type:
                library = prompt_manager.load_library(task_type)
                output["prompts"] = {task_type: [p.to_dict() for p in library.prompts]}
            else:
                output["prompts"] = {}
                for tt in prompt_manager.list_task_types():
                    library = prompt_manager.load_library(tt)
                    output["prompts"][tt] = [p.to_dict() for p in library.prompts]

        output["stats"] = store.get_storage_stats()
        typer.echo(json.dumps(output, indent=2))
        return

    # Validate section
    valid_sections = ["profile", "decisions", "corrections", "prompts", "all", None]
    if section_lower not in valid_sections:
        console.print(f"[red]Unknown section: {section}[/red]")
        console.print("[dim]Valid sections: profile, decisions, corrections, prompts[/dim]")
        raise typer.Exit(code=1)

    # Show profile
    if section_lower in [None, "all", "profile"]:
        _show_profile(store)

    # Show decisions
    if section_lower in [None, "all", "decisions"]:
        _show_decisions(store, project)

    # Show corrections
    if section_lower in [None, "all", "corrections"]:
        _show_corrections(store, top)

    # Show prompts
    if section_lower in [None, "all", "prompts"]:
        _show_prompts(store, task_type)


def _show_profile(store: MemoryStore) -> None:
    """Display profile section."""
    manager = ProfileManager(store)
    profile = manager.load_profile()

    if profile.is_empty():
        typer.echo("Profile: (empty)")
        typer.echo("  Learn preferences with: cerberus memory learn \"prefer early returns\"")
        typer.echo("")
        return

    typer.echo("Profile:")
    typer.echo(f"  Updated: {profile.updated_at or 'never'}")

    if profile.coding_style:
        typer.echo("  Coding Style:")
        for key, value in profile.coding_style.items():
            display_key = key.replace("_", " ").title()
            typer.echo(f"    {display_key}: {value}")

    if profile.naming_conventions:
        typer.echo("  Naming Conventions:")
        for key, value in profile.naming_conventions.items():
            display_key = key.replace("_", " ").title()
            typer.echo(f"    {display_key}: {value}")

    if profile.anti_patterns:
        typer.echo("  Anti-patterns:")
        for ap in profile.anti_patterns:
            typer.echo(f"    - {ap}")

    if profile.general:
        typer.echo("  General:")
        for pref in profile.general:
            typer.echo(f"    - {pref}")

    typer.echo("")


def _show_decisions(store: MemoryStore, project: Optional[str]) -> None:
    """Display decisions section."""
    manager = DecisionManager(store)

    proj = project or manager.detect_project_name()
    if proj is None:
        available = manager.list_projects()
        if available:
            typer.echo(f"Decisions: (no project detected)")
            typer.echo(f"  Available projects: {', '.join(available)}")
            typer.echo("  Use --project to specify")
        else:
            typer.echo("Decisions: (none)")
            typer.echo("  Learn decisions with: cerberus memory learn -d \"chose X for Y\"")
        typer.echo("")
        return

    decisions = manager.load_decisions(proj)
    if not decisions.decisions:
        typer.echo(f"Decisions ({proj}): (none)")
        typer.echo("  Learn decisions with: cerberus memory learn -d \"chose X for Y\"")
        typer.echo("")
        return

    typer.echo(f"Decisions ({proj}):")
    for d in decisions.decisions:
        typer.echo(f"  [{d.id}] {d.topic}: {d.decision}")
        if d.rationale:
            typer.echo(f"         Rationale: {d.rationale}")
    typer.echo("")


def _show_corrections(store: MemoryStore, top: int) -> None:
    """Display corrections section."""
    manager = CorrectionManager(store)
    corrections = manager.load_corrections()

    if not corrections.corrections:
        typer.echo("Corrections: (none)")
        typer.echo("  Learn corrections with: cerberus memory learn -c \"AI keeps doing X\"")
        typer.echo("")
        return

    typer.echo(f"Corrections (top {top} by frequency):")
    for c in corrections.get_by_frequency(top):
        note_or_pattern = c.note if c.note else c.pattern[:50]
        typer.echo(f"  [{c.id}] {note_or_pattern} ({c.frequency}x)")
    typer.echo("")


def _show_prompts(store: MemoryStore, task_type: Optional[str]) -> None:
    """Display prompts section."""
    manager = PromptManager(store)

    task_types = [task_type] if task_type else manager.list_task_types()

    if not task_types:
        typer.echo("Prompts: (none)")
        typer.echo("  Learn prompts with: cerberus memory learn --prompt \"name\" --task code-review")
        typer.echo("")
        return

    typer.echo("Prompts:")
    for tt in task_types:
        library = manager.load_library(tt)
        if library.prompts:
            typer.echo(f"  {tt}:")
            for p in library.prompts:
                eff_pct = int(p.effectiveness * 100)
                typer.echo(f"    [{p.id}] {p.name} ({eff_pct}% effective, {p.use_count} uses)")
                if p.description:
                    typer.echo(f"           {p.description}")
    typer.echo("")


@app.command()
def context(
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Include project-specific decisions (auto-detected if not provided)"
    ),
    task: Optional[str] = typer.Option(
        None,
        "--task",
        "-t",
        help="Include task-specific prompts (e.g., code-review, refactor)"
    ),
    compact: bool = typer.Option(
        False,
        "--compact",
        "-c",
        help="Generate minimal context (fewer sections)"
    ),
    stats: bool = typer.Option(
        False,
        "--stats",
        help="Show context statistics"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON (includes both context and stats)"
    ),
):
    """
    Generate injection context for a session.

    This generates AI-optimized markdown that should be injected
    at the start of an AI session for instant developer context.

    Examples:
      cerberus memory context                    # Generate full context
      cerberus memory context --project foo      # Include project decisions
      cerberus memory context --task code-review # Include prompts for code review
      cerberus memory context --compact          # Minimal version
      cerberus memory context --stats            # Show compression metrics

    Output is optimized for AI comprehension and token efficiency.
    Target: <150 lines / 4KB.
    """
    generator = ContextGenerator()

    # Generate context
    ctx = generator.generate_context(
        project=project,
        task=task,
        compact=compact,
    )

    if json_output:
        output = {
            "context": ctx,
            "stats": generator.get_context_stats(),
        }
        typer.echo(json.dumps(output, indent=2))
        return

    # Output the context
    typer.echo(ctx)

    # Show stats if requested
    if stats:
        ctx_stats = generator.get_context_stats()
        typer.echo("")
        typer.echo("--- Context Stats ---")
        typer.echo(f"Lines: {ctx_stats['context_lines']}")
        typer.echo(f"Bytes: {ctx_stats['context_bytes']}")
        typer.echo(f"Compression: {ctx_stats['compression_ratio']}%")
        typer.echo(f"Under limit: {ctx_stats['under_limit']}")


@app.command()
def extract(
    from_git: bool = typer.Option(
        True,
        "--from-git",
        help="Extract patterns from git history"
    ),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        "-s",
        help="Git date string (e.g., '1 week ago', '2024-01-01')"
    ),
    max_commits: int = typer.Option(
        100,
        "--max-commits",
        "-m",
        help="Maximum number of commits to analyze"
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project name (auto-detected from git if not provided)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be extracted without saving"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON"
    ),
):
    """
    Extract patterns from git history.

    Analyzes commit messages for:
    - Decisions (keywords: chose, decided, using, prefer)
    - Corrections (keywords: fix, correct, always, never)

    Examples:
      cerberus memory extract                    # Extract from last 100 commits
      cerberus memory extract --since "1 week ago"
      cerberus memory extract --dry-run          # Preview without saving
      cerberus memory extract --max-commits 500  # Analyze more commits
    """
    extractor = GitExtractor()

    if dry_run:
        result = extractor.extract_from_git(
            since=since,
            max_commits=max_commits,
            project=project,
        )
    else:
        result = extractor.learn_from_git(
            since=since,
            max_commits=max_commits,
            project=project,
            dry_run=False,
        )

    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return

    if not result["success"]:
        console.print(f"[red]Error: {result['message']}[/red]")
        raise typer.Exit(code=1)

    summary = result.get("summary", {})
    typer.echo(f"Analyzed {summary.get('commits_analyzed', 0)} commits from {result.get('project', 'unknown')}")
    typer.echo("")

    if dry_run:
        decisions = result.get("decisions", [])
        corrections = result.get("corrections", [])

        if decisions:
            typer.echo("Decisions found:")
            for d in decisions[:10]:
                typer.echo(f"  - {d['content'][:60]}...")
            typer.echo("")

        if corrections:
            typer.echo("Corrections found:")
            for c in corrections[:10]:
                typer.echo(f"  - {c['content'][:60]}...")
            typer.echo("")

        typer.echo(f"Total: {len(decisions)} decisions, {len(corrections)} corrections")
        typer.echo("[dim]Run without --dry-run to save these patterns[/dim]")
    else:
        typer.echo(f"Learned {summary.get('decisions_learned', 0)} decisions")
        typer.echo(f"Learned {summary.get('corrections_learned', 0)} corrections")


@app.command()
def forget(
    item: str = typer.Argument(
        ...,
        help="The item to remove (preference text, decision ID, correction ID, or prompt name)"
    ),
    decision: bool = typer.Option(
        False,
        "--decision",
        "-d",
        help="Remove a decision by ID"
    ),
    correction: bool = typer.Option(
        False,
        "--correction",
        "-c",
        help="Remove a correction by ID"
    ),
    prompt: bool = typer.Option(
        False,
        "--prompt",
        help="Remove a prompt by name"
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project name for decisions"
    ),
    task_type: Optional[str] = typer.Option(
        None,
        "--task",
        "-t",
        help="Task type for prompts"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON"
    ),
):
    """
    Remove a memory entry.

    Examples:
      cerberus memory forget "early_returns"              # Remove preference
      cerberus memory forget dec-001 --decision           # Remove decision
      cerberus memory forget cor-002 --correction         # Remove correction
      cerberus memory forget "security-audit" --prompt    # Remove prompt
    """
    # Handle prompt removal
    if prompt:
        manager = PromptManager()
        result = manager.forget_prompt(item, task_type=task_type)

        if json_output:
            typer.echo(json.dumps(result, indent=2))
        else:
            if result["success"]:
                typer.echo(result["message"])
            else:
                console.print(f"[yellow]{result['message']}[/yellow]")
                raise typer.Exit(code=1)
        return

    # Handle decision removal
    if decision:
        manager = DecisionManager()
        result = manager.forget_decision(item, project=project)

        if json_output:
            typer.echo(json.dumps(result, indent=2))
        else:
            if result["success"]:
                typer.echo(result["message"])
            else:
                console.print(f"[yellow]{result['message']}[/yellow]")
                raise typer.Exit(code=1)
        return

    # Handle correction removal
    if correction:
        manager = CorrectionManager()
        result = manager.forget_correction(item)

        if json_output:
            typer.echo(json.dumps(result, indent=2))
        else:
            if result["success"]:
                typer.echo(result["message"])
            else:
                console.print(f"[yellow]{result['message']}[/yellow]")
                raise typer.Exit(code=1)
        return

    # Default: remove preference
    manager = ProfileManager()
    result = manager.forget(item)

    if json_output:
        typer.echo(json.dumps(result, indent=2))
    else:
        if result["success"]:
            typer.echo(result["message"])
        else:
            console.print(f"[yellow]{result['message']}[/yellow]")
            raise typer.Exit(code=1)


@app.command()
def stats(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON"
    ),
):
    """
    Show Session Memory statistics.

    Displays storage usage, compression metrics, and limits.
    """
    store = MemoryStore()
    generator = ContextGenerator(store)
    correction_manager = CorrectionManager(store)
    decision_manager = DecisionManager(store)
    prompt_manager = PromptManager(store)

    storage_stats = store.get_storage_stats()
    context_stats = generator.get_context_stats()
    correction_summary = correction_manager.get_summary()
    prompt_summary = prompt_manager.get_summary()

    if json_output:
        output = {
            "storage": storage_stats,
            "context": context_stats,
            "corrections": correction_summary,
            "prompts": prompt_summary,
            "projects": decision_manager.list_projects(),
            "limits": {
                "max_profile_bytes": MemoryStore.MAX_PROFILE_SIZE,
                "max_context_bytes": MemoryStore.MAX_CONTEXT_SIZE,
            }
        }
        typer.echo(json.dumps(output, indent=2))
        return

    typer.echo("Session Memory Statistics")
    typer.echo("")

    # Storage info
    typer.echo("Storage:")
    typer.echo(f"  Location: {storage_stats['base_path']}")
    typer.echo(f"  Total size: {storage_stats['total_size_bytes']} bytes")
    typer.echo(f"  Profile exists: {storage_stats['profile_exists']}")
    typer.echo(f"  Corrections exist: {storage_stats['corrections_exists']}")
    typer.echo(f"  Projects: {storage_stats['project_count']}")
    typer.echo(f"  Prompt types: {storage_stats['prompt_count']}")
    typer.echo("")

    # Corrections summary
    typer.echo("Corrections:")
    typer.echo(f"  Total patterns: {correction_summary['total_count']}")
    typer.echo(f"  Total frequency: {correction_summary['total_frequency']}")
    typer.echo("")

    # Prompts summary
    typer.echo("Prompts:")
    typer.echo(f"  Total prompts: {prompt_summary['total_prompts']}")
    typer.echo(f"  Task types: {prompt_summary['task_types']}")
    typer.echo("")

    # Context info
    typer.echo("Context Generation:")
    typer.echo(f"  Output lines: {context_stats['context_lines']}")
    typer.echo(f"  Output bytes: {context_stats['context_bytes']}")
    typer.echo(f"  Under 4KB limit: {context_stats['under_limit']}")
    typer.echo("")

    # Limits
    typer.echo("Limits:")
    typer.echo(f"  Max profile: {MemoryStore.MAX_PROFILE_SIZE} bytes (1KB)")
    typer.echo(f"  Max context: {MemoryStore.MAX_CONTEXT_SIZE} bytes (4KB)")


@app.command()
def edit(
    section: str = typer.Argument(
        ...,
        help="Section to edit: profile, corrections, decisions, prompts"
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project name (for decisions)"
    ),
    task_type: Optional[str] = typer.Option(
        None,
        "--task",
        "-t",
        help="Task type (for prompts)"
    ),
    editor: Optional[str] = typer.Option(
        None,
        "--editor",
        "-e",
        help="Editor to use (default: $EDITOR or vi)"
    ),
):
    """
    Open a memory file in your editor.

    Examples:
      cerberus memory edit profile                    # Edit preferences
      cerberus memory edit corrections                # Edit corrections
      cerberus memory edit decisions --project foo   # Edit project decisions
      cerberus memory edit prompts --task code-review  # Edit prompts
    """
    import os
    import subprocess

    store = MemoryStore()
    section_lower = section.lower()

    # Determine file path
    if section_lower == "profile":
        file_path = store.profile_path
    elif section_lower == "corrections":
        file_path = store.corrections_path
    elif section_lower == "decisions":
        if not project:
            # Try to auto-detect project
            manager = DecisionManager(store)
            project = manager.detect_project_name()
            if not project:
                console.print("[red]Error: --project required for decisions[/red]")
                console.print("[dim]Use: cerberus memory edit decisions --project <name>[/dim]")
                raise typer.Exit(code=1)
        file_path = store.project_path(project)
    elif section_lower == "prompts":
        if not task_type:
            console.print("[red]Error: --task required for prompts[/red]")
            console.print("[dim]Use: cerberus memory edit prompts --task <type>[/dim]")
            raise typer.Exit(code=1)
        file_path = store.prompt_path(task_type)
    else:
        console.print(f"[red]Unknown section: {section}[/red]")
        console.print("[dim]Valid sections: profile, corrections, decisions, prompts[/dim]")
        raise typer.Exit(code=1)

    # Create file with empty structure if it doesn't exist
    if not file_path.exists():
        if section_lower == "profile":
            store.write_json(file_path, {"$schema": "profile-v1", "coding_style": {}, "naming_conventions": {}, "anti_patterns": [], "languages": {}, "general": []})
        elif section_lower == "corrections":
            store.write_json(file_path, {"$schema": "corrections-v1", "corrections": []})
        elif section_lower == "decisions":
            store.write_json(file_path, {"$schema": "decisions-v1", "project": project, "decisions": []})
        elif section_lower == "prompts":
            store.write_json(file_path, {"$schema": "prompt-library-v1", "task_type": task_type, "prompts": []})

    # Determine editor
    editor_cmd = editor or os.environ.get('EDITOR') or os.environ.get('VISUAL') or 'vi'

    typer.echo(f"Opening {file_path} in {editor_cmd}...")

    try:
        subprocess.run([editor_cmd, str(file_path)], check=True)
        typer.echo("File saved.")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Editor exited with error: {e.returncode}[/red]")
        raise typer.Exit(code=1)
    except FileNotFoundError:
        console.print(f"[red]Editor not found: {editor_cmd}[/red]")
        console.print("[dim]Set $EDITOR environment variable or use --editor[/dim]")
        raise typer.Exit(code=1)


@app.command(name="export")
def export_memory(
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (default: stdout)"
    ),
    section: Optional[str] = typer.Option(
        None,
        "--section",
        "-s",
        help="Export specific section: profile, corrections, decisions, prompts (default: all)"
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project name for decisions export"
    ),
    compact: bool = typer.Option(
        False,
        "--compact",
        help="Compact JSON output (no indentation)"
    ),
):
    """
    Export Session Memory for backup or sharing.

    Examples:
      cerberus memory export                          # Export all to stdout
      cerberus memory export -o backup.json           # Export all to file
      cerberus memory export --section profile        # Export profile only
      cerberus memory export --section decisions -p cerberus  # Export project decisions
    """
    store = MemoryStore()
    profile_manager = ProfileManager(store)
    correction_manager = CorrectionManager(store)
    decision_manager = DecisionManager(store)
    prompt_manager = PromptManager(store)

    export_data = {
        "$schema": "session-memory-export-v1",
        "exported_at": store.timestamp(),
        "version": "18.4",
    }

    section_lower = section.lower() if section else None

    # Export profile
    if section_lower is None or section_lower == "profile":
        profile = profile_manager.load_profile()
        export_data["profile"] = profile.to_dict()

    # Export corrections
    if section_lower is None or section_lower == "corrections":
        corrections = correction_manager.load_corrections()
        export_data["corrections"] = {
            "$schema": "corrections-v1",
            "corrections": [c.to_dict() for c in corrections.corrections]
        }

    # Export decisions
    if section_lower is None or section_lower == "decisions":
        if project:
            # Export specific project
            decisions = decision_manager.load_decisions(project)
            export_data["decisions"] = {
                project: {
                    "$schema": "decisions-v1",
                    "project": project,
                    "decisions": [d.to_dict() for d in decisions.decisions]
                }
            }
        else:
            # Export all projects
            export_data["decisions"] = {}
            for proj in decision_manager.list_projects():
                decisions = decision_manager.load_decisions(proj)
                export_data["decisions"][proj] = {
                    "$schema": "decisions-v1",
                    "project": proj,
                    "decisions": [d.to_dict() for d in decisions.decisions]
                }

    # Export prompts
    if section_lower is None or section_lower == "prompts":
        export_data["prompts"] = {}
        for task_type in prompt_manager.list_task_types():
            library = prompt_manager.load_library(task_type)
            export_data["prompts"][task_type] = {
                "$schema": "prompt-library-v1",
                "task_type": task_type,
                "prompts": [p.to_dict() for p in library.prompts]
            }

    # Format output
    indent = None if compact else 2
    json_output = json.dumps(export_data, indent=indent, ensure_ascii=False)

    if output:
        try:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            typer.echo(f"Exported to {output}")
        except Exception as e:
            console.print(f"[red]Error writing file: {e}[/red]")
            raise typer.Exit(code=1)
    else:
        typer.echo(json_output)


@app.command(name="import")
def import_memory(
    input_file: str = typer.Argument(
        ...,
        help="Path to the export file to import"
    ),
    section: Optional[str] = typer.Option(
        None,
        "--section",
        "-s",
        help="Import specific section: profile, corrections, decisions, prompts (default: all)"
    ),
    merge: bool = typer.Option(
        True,
        "--merge/--replace",
        help="Merge with existing data (default) or replace entirely"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be imported without making changes"
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON"
    ),
):
    """
    Import Session Memory from a backup or shared file.

    Examples:
      cerberus memory import backup.json              # Import all sections
      cerberus memory import backup.json --dry-run   # Preview import
      cerberus memory import backup.json --section profile  # Import profile only
      cerberus memory import backup.json --replace   # Replace instead of merge
    """
    from pathlib import Path

    # Read import file
    input_path = Path(input_file)
    if not input_path.exists():
        console.print(f"[red]File not found: {input_file}[/red]")
        raise typer.Exit(code=1)

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(code=1)

    # Validate schema
    if "$schema" not in import_data or not import_data.get("$schema", "").startswith("session-memory-export"):
        console.print("[yellow]Warning: File may not be a valid Session Memory export[/yellow]")

    store = MemoryStore()
    profile_manager = ProfileManager(store)
    correction_manager = CorrectionManager(store)
    decision_manager = DecisionManager(store)
    prompt_manager = PromptManager(store)

    section_lower = section.lower() if section else None
    result = {
        "success": True,
        "dry_run": dry_run,
        "imported": {},
    }

    # Import profile
    if (section_lower is None or section_lower == "profile") and "profile" in import_data:
        profile_data = import_data["profile"]
        if dry_run:
            result["imported"]["profile"] = {"would_import": True, "entries": len(profile_data.get("coding_style", {})) + len(profile_data.get("anti_patterns", []))}
        else:
            if merge:
                existing = profile_manager.load_profile()
                # Merge coding style
                existing.coding_style.update(profile_data.get("coding_style", {}))
                existing.naming_conventions.update(profile_data.get("naming_conventions", {}))
                # Merge lists (avoid duplicates)
                for ap in profile_data.get("anti_patterns", []):
                    if ap not in existing.anti_patterns:
                        existing.anti_patterns.append(ap)
                for gen in profile_data.get("general", []):
                    if gen not in existing.general:
                        existing.general.append(gen)
                existing.languages.update(profile_data.get("languages", {}))
                profile_manager.save_profile(existing)
            else:
                from cerberus.memory.profile import Profile
                new_profile = Profile.from_dict(profile_data)
                profile_manager.save_profile(new_profile)
            result["imported"]["profile"] = {"success": True}

    # Import corrections
    if (section_lower is None or section_lower == "corrections") and "corrections" in import_data:
        corrections_data = import_data["corrections"]
        corrections_list = corrections_data.get("corrections", [])
        if dry_run:
            result["imported"]["corrections"] = {"would_import": True, "count": len(corrections_list)}
        else:
            from cerberus.memory.corrections import Correction
            existing = correction_manager.load_corrections()
            for c_data in corrections_list:
                new_correction = Correction.from_dict(c_data)
                # Find existing by pattern similarity
                found = existing.find_similar(new_correction.pattern)
                if found and merge:
                    # Merge: add frequencies
                    found.frequency += new_correction.frequency
                    if new_correction.note:
                        found.note = new_correction.note
                elif not found:
                    # Append to corrections list directly
                    existing.corrections.append(new_correction)
                elif not merge:
                    # Replace: remove existing, add new
                    existing.corrections = [c for c in existing.corrections if c.id != found.id]
                    existing.corrections.append(new_correction)
            correction_manager.save_corrections(existing)
            result["imported"]["corrections"] = {"success": True, "count": len(corrections_list)}

    # Import decisions
    if (section_lower is None or section_lower == "decisions") and "decisions" in import_data:
        decisions_data = import_data["decisions"]
        total_decisions = 0
        for proj, proj_data in decisions_data.items():
            decisions_list = proj_data.get("decisions", [])
            total_decisions += len(decisions_list)
            if not dry_run:
                from cerberus.memory.decisions import Decision
                existing = decision_manager.load_decisions(proj)
                for d_data in decisions_list:
                    new_decision = Decision.from_dict(d_data)
                    if merge:
                        # Check if decision with same topic exists
                        found = None
                        for d in existing.decisions:
                            if d.topic == new_decision.topic:
                                found = d
                                break
                        if found:
                            # Update existing
                            found.decision = new_decision.decision
                            found.rationale = new_decision.rationale or found.rationale
                        else:
                            existing.add_decision(new_decision)
                    else:
                        existing.add_decision(new_decision)
                decision_manager.save_decisions(proj, existing)

        if dry_run:
            result["imported"]["decisions"] = {"would_import": True, "projects": len(decisions_data), "total_decisions": total_decisions}
        else:
            result["imported"]["decisions"] = {"success": True, "projects": len(decisions_data), "total_decisions": total_decisions}

    # Import prompts
    if (section_lower is None or section_lower == "prompts") and "prompts" in import_data:
        prompts_data = import_data["prompts"]
        total_prompts = 0
        for task_type, lib_data in prompts_data.items():
            prompts_list = lib_data.get("prompts", [])
            total_prompts += len(prompts_list)
            if not dry_run:
                from cerberus.memory.prompts import Prompt
                existing = prompt_manager.load_library(task_type)
                for p_data in prompts_list:
                    new_prompt = Prompt.from_dict(p_data)
                    if merge:
                        # Check if prompt with same name exists
                        found = existing.find_by_name(new_prompt.name)
                        if found:
                            # Update existing
                            found.template = new_prompt.template or found.template
                            found.description = new_prompt.description or found.description
                            found.use_count += new_prompt.use_count
                        else:
                            existing.add_prompt(new_prompt)
                    else:
                        existing.add_prompt(new_prompt)
                prompt_manager.save_library(task_type, existing)

        if dry_run:
            result["imported"]["prompts"] = {"would_import": True, "task_types": len(prompts_data), "total_prompts": total_prompts}
        else:
            result["imported"]["prompts"] = {"success": True, "task_types": len(prompts_data), "total_prompts": total_prompts}

    if json_output:
        typer.echo(json.dumps(result, indent=2))
    else:
        if dry_run:
            typer.echo("Dry run - no changes made:")
        else:
            typer.echo("Import complete:")

        for section_name, section_result in result["imported"].items():
            if dry_run:
                if section_name == "profile":
                    typer.echo(f"  Profile: {section_result.get('entries', 0)} entries would be imported")
                elif section_name == "corrections":
                    typer.echo(f"  Corrections: {section_result.get('count', 0)} would be imported")
                elif section_name == "decisions":
                    typer.echo(f"  Decisions: {section_result.get('total_decisions', 0)} from {section_result.get('projects', 0)} projects would be imported")
                elif section_name == "prompts":
                    typer.echo(f"  Prompts: {section_result.get('total_prompts', 0)} from {section_result.get('task_types', 0)} task types would be imported")
            else:
                if section_name == "profile":
                    typer.echo(f"  Profile: imported")
                elif section_name == "corrections":
                    typer.echo(f"  Corrections: {section_result.get('count', 0)} imported")
                elif section_name == "decisions":
                    typer.echo(f"  Decisions: {section_result.get('total_decisions', 0)} from {section_result.get('projects', 0)} projects imported")
                elif section_name == "prompts":
                    typer.echo(f"  Prompts: {section_result.get('total_prompts', 0)} from {section_result.get('task_types', 0)} task types imported")
