"""
CLI Mutation Commands (Phase 11)

edit, delete, insert, stats
"""

import json
import typer
from pathlib import Path
from typing import Optional

from rich.table import Table

from cerberus.logging_config import logger
from cerberus.mutation import MutationFacade, DiffLedger
from cerberus.storage.sqlite_store import SQLiteIndexStore
from cerberus.quality import StyleDetector
from .output import get_console, structured_error
from .common import load_index_or_exit, get_default_index
from .config import CLIConfig
from .guidance import GuidanceProvider
from .anchoring import ContextAnchor
# Phase 19.2: Efficiency Hints
from .hints import EfficiencyHints

app = typer.Typer()
console = get_console()


@app.command("edit")
def edit_cmd(
    file: Path = typer.Argument(..., help="Path to file to edit", exists=True),
    symbol: str = typer.Option(..., "--symbol", "-s", help="Symbol name to edit"),
    code: Optional[str] = typer.Option(None, "--code", "-c", help="New code inline"),
    code_file: Optional[Path] = typer.Option(None, "--code-file", "-f", help="Path to file with new code"),
    symbol_type: Optional[str] = typer.Option(None, "--type", "-t", help="Symbol type filter (function, class, method)"),
    parent_class: Optional[str] = typer.Option(None, "--parent", "-p", help="Parent class for methods"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate but don't write"),
    no_format: bool = typer.Option(False, "--no-format", help="Skip auto-formatting"),
    no_imports: bool = typer.Option(False, "--no-imports", help="Skip import injection"),
    force: bool = typer.Option(False, "--force", help="Bypass Symbol Guard protection (Phase 13.2)"),
    check_corrections: bool = typer.Option(False, "--check-corrections", help="[PHASE 18] Check code against Session Memory corrections"),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    no_predict: bool = typer.Option(False, "--no-predict", help="Disable predictive suggestions (Phase 14.3)"),
):
    """
    Edit a code symbol by name using surgical AST-based replacement.

    Phase 14.3: Includes predictive editing suggestions for related changes.

    Phase 11: The Surgical Writer - replaces symbols without full-file rewrites.
    Phase 13.2: Symbol Guard protection with --force override.
    Phase 18: Session Memory correction checking with --check-corrections.
    """
    # Validate input
    if not code and not code_file:
        error_msg = "Must provide either --code or --code-file"
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="MISSING_ARGUMENT",
                message=error_msg,
                suggestions=["--code 'def foo(): pass'", "--code-file new_impl.py"]
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: {error_msg}[/red]")
        raise typer.Exit(code=1)

    # Read code from file if provided
    if code_file:
        try:
            code = code_file.read_text(encoding='utf-8')
        except Exception as e:
            if CLIConfig.is_machine_mode() or json_output:
                error = structured_error(
                    code="FILE_READ_ERROR",
                    message=f"Failed to read code file: {e}"
                )
                print(json.dumps(error, separators=(',', ':')))
            else:
                console.print(f"[red]Error: Failed to read {code_file}: {e}[/red]")
            raise typer.Exit(code=1)

    # Phase 18: Check code against Session Memory corrections
    correction_warnings = []
    if check_corrections and code:
        try:
            from cerberus.memory.corrections import CorrectionManager
            correction_mgr = CorrectionManager()
            corrections = correction_mgr.load_corrections()

            code_lower = code.lower()
            for c in corrections.corrections:
                # Check if the pattern (or keywords from it) appears in the new code
                pattern_keywords = [w for w in c.pattern.lower().split() if len(w) > 3]
                for keyword in pattern_keywords:
                    if keyword in code_lower:
                        correction_warnings.append({
                            "id": c.id,
                            "pattern": c.pattern,
                            "note": c.note or c.correction,
                            "frequency": c.frequency
                        })
                        break  # One match per correction is enough
        except Exception as e:
            logger.debug(f"Session Memory correction check failed: {e}")

    # Load index
    index_path = get_default_index(index_path)
    try:
        store = SQLiteIndexStore(str(index_path))
    except Exception as e:
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="INDEX_LOAD_ERROR",
                message=f"Failed to load index: {e}",
                actionable_fix="cerberus index ."
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: Failed to load index: {e}[/red]")
        raise typer.Exit(code=1)

    # Create facade
    facade = MutationFacade(store)

    # Perform edit
    result = facade.edit_symbol(
        file_path=str(file),
        symbol_name=symbol,
        new_code=code,
        symbol_type=symbol_type,
        parent_class=parent_class,
        dry_run=dry_run,
        auto_format=not no_format,
        auto_imports=not no_imports,
        force=force
    )

    # Output result
    if CLIConfig.is_machine_mode() or json_output:
        # Machine mode: pure JSON with predictions
        output_data = result.model_dump()

        # Phase 18: Add correction warnings to output
        if correction_warnings:
            output_data["correction_warnings"] = correction_warnings

        # Phase 14.4: Record action for accuracy tracking
        if result.success:
            try:
                ledger = DiffLedger()
                ledger.record_action(
                    action_type="edit",
                    target_symbol=symbol,
                    target_file=str(file),
                    command=f"cerberus mutations edit {file} --symbol {symbol}"
                )
            except Exception as e:
                logger.debug(f"Action tracking failed: {e}")

        # Phase 14.3: Add predictions if enabled
        if not no_predict and result.success:
            try:
                from cerberus.quality.predictor import PredictionEngine
                engine = PredictionEngine(str(index_path))
                predictions, stats = engine.predict_related_changes(
                    edited_symbol=symbol,
                    file_path=str(file),
                    symbol_type=symbol_type or "function"
                )
                prediction_output = engine.to_json(predictions, stats)
                output_data["predictions"] = prediction_output["predictions"]
                output_data["prediction_stats"] = prediction_output["prediction_stats"]

                # Log predictions to ledger (Phase 14.3 basic logging)
                if predictions:
                    if 'ledger' not in locals():
                        ledger = DiffLedger()
                    prediction_dicts = [
                        {"symbol": p.symbol, "confidence_score": p.confidence_score}
                        for p in predictions
                    ]
                    ledger.record_predictions(symbol, str(file), prediction_dicts)
            except Exception as e:
                logger.debug(f"Prediction engine failed: {e}")
                output_data["predictions"] = []

        print(json.dumps(output_data, separators=(',', ':')))
    else:
        # Human mode: rich output
        if result.success:
            # Phase 14.4: Record action for accuracy tracking
            try:
                ledger = DiffLedger()
                ledger.record_action(
                    action_type="edit",
                    target_symbol=symbol,
                    target_file=str(file),
                    command=f"cerberus mutations edit {file} --symbol {symbol}"
                )
            except Exception as e:
                logger.debug(f"Action tracking failed: {e}")

            # Phase 12.5: Context Anchoring (GPS)
            anchor_header = ContextAnchor.format_mutation_header(
                operation="edit",
                file_path=str(file),
                symbol=symbol,
                status="Modified"
            )
            console.print(f"[bold]{anchor_header}[/bold]\n")

            console.print(f"[green]✓[/green] Successfully edited '{symbol}' in {file}")
            console.print(f"  Lines changed: {result.lines_changed}/{result.lines_total}")
            console.print(f"  Write efficiency: {result.write_efficiency:.1%}")
            console.print(f"  Tokens saved: {result.tokens_saved}")
            if result.backup_path:
                console.print(f"  Backup: {result.backup_path}")
            if result.warnings:
                console.print("[yellow]Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  - {warning}")

            # Phase 18: Show Session Memory correction warnings
            if correction_warnings:
                console.print("[yellow]📝 Session Memory Correction Warnings:[/yellow]")
                for cw in correction_warnings:
                    console.print(f"  - {cw['note']} (corrected {cw['frequency']}x)")
                console.print("[dim]   Review these patterns to avoid past mistakes[/dim]")

            # Phase 14.1: Style detection (suggest fixes if issues found)
            try:
                detector = StyleDetector()
                issues = detector.check_file(str(file))
                if issues:
                    issue_types = list(set(issue.issue_type.value.replace('_', ' ') for issue in issues))
                    console.print(f"\n[yellow]⚠️  Style Issues Detected: {len(issues)} ({', '.join(issue_types[:3])})[/yellow]")
                    console.print(f"[dim]💡 Fix with: cerberus quality style-fix {file}[/dim]")
            except Exception as e:
                logger.debug(f"Style detection failed: {e}")

            # Phase 14.3: Predictive editing (suggest related changes)
            if not no_predict:
                try:
                    from cerberus.quality.predictor import PredictionEngine
                    engine = PredictionEngine(str(index_path))
                    predictions, stats = engine.predict_related_changes(
                        edited_symbol=symbol,
                        file_path=str(file),
                        symbol_type=symbol_type or "function"
                    )

                    # Log predictions to ledger (Phase 14.3 basic logging)
                    if predictions:
                        ledger = DiffLedger()
                        prediction_dicts = [
                            {"symbol": p.symbol, "confidence_score": p.confidence_score}
                            for p in predictions
                        ]
                        ledger.record_predictions(symbol, str(file), prediction_dicts)

                        console.print(f"\n[cyan]🔮 [Predictive] Related changes suggested ({len(predictions)} HIGH confidence):[/cyan]")
                        for i, pred in enumerate(predictions[:3], 1):  # Show top 3
                            console.print(f"  {i}. {pred.symbol} ({Path(pred.file).name}:{pred.line})")
                            console.print(f"     [dim]{pred.relationship}[/dim]")

                        if len(predictions) > 3:
                            console.print(f"  [dim]... and {len(predictions) - 3} more[/dim]")

                        console.print(f"[dim]💡 Review with: cerberus quality related-changes {symbol}[/dim]")
                except Exception as e:
                    logger.debug(f"Prediction engine failed: {e}")

            # Phase 19.2: Hint about corrections when not using --check-corrections
            if not check_corrections and not correction_warnings:
                correction_hint = EfficiencyHints.check_corrections_available(
                    file_path=str(file),
                    symbol_name=symbol,
                    used_check_corrections=check_corrections,
                )
                if correction_hint:
                    console.print(f"\n[cyan]{correction_hint.to_human()}[/cyan]")

            # Phase 12.5: JIT Guidance
            if GuidanceProvider.should_show_guidance(CLIConfig.is_machine_mode()):
                tip = GuidanceProvider.get_tip("edit")
                if tip:
                    console.print(f"[dim cyan]{GuidanceProvider.format_tip(tip)}[/dim cyan]")
        else:
            console.print(f"[red]✗[/red] Failed to edit '{symbol}'")
            for error in result.errors:
                console.print(f"  [red]Error:[/red] {error}")

    # Exit with appropriate code
    if not result.success:
        raise typer.Exit(code=1)


@app.command("delete")
def delete_cmd(
    file: Path = typer.Argument(..., help="Path to file", exists=True),
    symbol: str = typer.Option(..., "--symbol", "-s", help="Symbol name to delete"),
    symbol_type: Optional[str] = typer.Option(None, "--type", "-t", help="Symbol type filter"),
    parent_class: Optional[str] = typer.Option(None, "--parent", "-p", help="Parent class for methods"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate but don't write"),
    keep_decorators: bool = typer.Option(False, "--keep-decorators", help="Keep decorators when deleting"),
    force: bool = typer.Option(False, "--force", help="Bypass Symbol Guard protection (Phase 13.2)"),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Delete a code symbol by name.

    Phase 11: Safely remove symbols with backup and validation.
    Phase 13.2: Protected by Symbol Guard with stability-aware risk assessment.
    """
    # Load index
    index_path = get_default_index(index_path)
    try:
        store = SQLiteIndexStore(str(index_path))
    except Exception as e:
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="INDEX_LOAD_ERROR",
                message=f"Failed to load index: {e}",
                actionable_fix="cerberus index ."
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: Failed to load index: {e}[/red]")
        raise typer.Exit(code=1)

    # Create facade
    facade = MutationFacade(store)

    # Perform delete
    result = facade.delete_symbol(
        file_path=str(file),
        symbol_name=symbol,
        symbol_type=symbol_type,
        parent_class=parent_class,
        dry_run=dry_run,
        keep_decorators=keep_decorators,
        force=force
    )

    # Output result
    if CLIConfig.is_machine_mode() or json_output:
        print(json.dumps(result.model_dump(), separators=(',', ':')))
    else:
        if result.success:
            # Phase 12.5: Context Anchoring (GPS)
            anchor_header = ContextAnchor.format_mutation_header(
                operation="delete",
                file_path=str(file),
                symbol=symbol,
                status="Deleted"
            )
            console.print(f"[bold]{anchor_header}[/bold]\n")

            console.print(f"[green]✓[/green] Successfully deleted '{symbol}' from {file}")
            console.print(f"  Lines removed: {result.lines_changed}")
            console.print(f"  Backup: {result.backup_path}")

            # Phase 12.5: JIT Guidance
            if GuidanceProvider.should_show_guidance(CLIConfig.is_machine_mode()):
                tip = GuidanceProvider.get_tip("delete")
                if tip:
                    console.print(f"[dim cyan]{GuidanceProvider.format_tip(tip)}[/dim cyan]")
        else:
            console.print(f"[red]✗[/red] Failed to delete '{symbol}'")
            for error in result.errors:
                console.print(f"  [red]Error:[/red] {error}")

    if not result.success:
        raise typer.Exit(code=1)


@app.command("insert")
def insert_cmd(
    file: Path = typer.Argument(..., help="Path to file", exists=True),
    parent: str = typer.Option(..., "--parent", "-p", help="Parent symbol (class/module) to insert into"),
    code: Optional[str] = typer.Option(None, "--code", "-c", help="New code inline"),
    code_file: Optional[Path] = typer.Option(None, "--code-file", "-f", help="Path to file with new code"),
    after: Optional[str] = typer.Option(None, "--after", "-a", help="Insert after this symbol"),
    before: Optional[str] = typer.Option(None, "--before", "-b", help="Insert before this symbol"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate but don't write"),
    no_format: bool = typer.Option(False, "--no-format", help="Skip auto-formatting"),
    no_imports: bool = typer.Option(False, "--no-imports", help="Skip import injection"),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file. Defaults to 'cerberus.db' in CWD.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Insert new code into a file at a specific location.

    Phase 11: The Surgical Writer - insert new symbols without full-file rewrites.
    """
    # Validate input
    if not code and not code_file:
        error_msg = "Must provide either --code or --code-file"
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="MISSING_ARGUMENT",
                message=error_msg,
                suggestions=["--code 'def foo(): pass'", "--code-file new_impl.py"]
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: {error_msg}[/red]")
        raise typer.Exit(code=1)

    # Validate position arguments
    if after and before:
        error_msg = "Cannot specify both --after and --before"
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="INVALID_ARGUMENT",
                message=error_msg,
                suggestions=["Use --after OR --before, not both"]
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: {error_msg}[/red]")
        raise typer.Exit(code=1)

    # Read code from file if provided
    if code_file:
        try:
            code = code_file.read_text(encoding='utf-8')
        except Exception as e:
            if CLIConfig.is_machine_mode() or json_output:
                error = structured_error(
                    code="FILE_READ_ERROR",
                    message=f"Failed to read code file: {e}"
                )
                print(json.dumps(error, separators=(',', ':')))
            else:
                console.print(f"[red]Error: Failed to read {code_file}: {e}[/red]")
            raise typer.Exit(code=1)

    # Load index
    index_path = get_default_index(index_path)
    try:
        store = SQLiteIndexStore(str(index_path))
    except Exception as e:
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="INDEX_LOAD_ERROR",
                message=f"Failed to load index: {e}",
                actionable_fix="cerberus index ."
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: Failed to load index: {e}[/red]")
        raise typer.Exit(code=1)

    # Create facade
    facade = MutationFacade(store)

    # Perform insert
    result = facade.insert_symbol(
        file_path=str(file),
        parent_symbol=parent,
        new_code=code,
        after_symbol=after,
        before_symbol=before,
        dry_run=dry_run
    )

    # Output result
    if CLIConfig.is_machine_mode() or json_output:
        # Machine mode: pure JSON
        print(json.dumps(result.model_dump(), separators=(',', ':')))
    else:
        # Human mode: rich output
        if result.success:
            # Phase 12.5: Context Anchoring (GPS)
            anchor_header = ContextAnchor.format_mutation_header(
                operation="insert",
                file_path=str(file),
                symbol=parent,
                status="Inserted"
            )
            console.print(f"[bold]{anchor_header}[/bold]\n")

            console.print(f"[green]✓[/green] Successfully inserted code into '{parent}' in {file}")
            console.print(f"  Lines added: {result.lines_changed}")
            console.print(f"  Total lines: {result.lines_total}")
            if result.backup_path:
                console.print(f"  Backup: {result.backup_path}")
            if result.warnings:
                console.print("[yellow]Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  - {warning}")

            # Phase 12.5: JIT Guidance
            if GuidanceProvider.should_show_guidance(CLIConfig.is_machine_mode()):
                tip = GuidanceProvider.get_tip("insert")
                if tip:
                    console.print(f"[dim cyan]{GuidanceProvider.format_tip(tip)}[/dim cyan]")
        else:
            console.print(f"[red]✗[/red] Failed to insert code into '{parent}'")
            for error in result.errors:
                console.print(f"  [red]Error:[/red] {error}")

    # Exit with appropriate code
    if not result.success:
        raise typer.Exit(code=1)


@app.command("stats")
def stats_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Show write efficiency statistics from the diff ledger.

    Phase 11: Prove the value of surgical edits with metrics.
    """
    ledger = DiffLedger()
    stats = ledger.get_statistics()

    if CLIConfig.is_machine_mode() or json_output:
        print(json.dumps(stats, separators=(',', ':')))
    else:
        # Rich table output
        console.print("[bold]Phase 11: Mutation Statistics[/bold]\n")

        table = Table(title="Write Efficiency Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Operations", str(stats["total_operations"]))
        table.add_row(
            "Average Write Efficiency",
            f"{stats['average_write_efficiency']:.1%}"
        )
        table.add_row("Total Tokens Saved", f"{stats['total_tokens_saved']:,}")

        console.print(table)

        # Operations by type
        if stats["operations_by_type"]:
            console.print("\n[bold]Operations by Type:[/bold]")
            for op_type, count in stats["operations_by_type"].items():
                console.print(f"  {op_type}: {count}")


@app.command("batch-edit")
def batch_edit_cmd(
    operations_file: Path = typer.Argument(..., help="Path to JSON file with batch operations", exists=True),
    verify: Optional[str] = typer.Option(None, "--verify", help="Shell command to verify changes (e.g., 'pytest tests/')"),
    preview: bool = typer.Option(False, "--preview", help="Preview changes without writing (Phase 12.5)"),
    index_path: Optional[Path] = typer.Option(
        None,
        "--index",
        "-i",
        help="Path to index file.",
        dir_okay=False,
        readable=True,
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Execute multiple edit operations atomically with automatic rollback on failure.

    Phase 12: The Harmonized Writer - batch edits with verified transactions.
    Phase 12.5: --preview flag for dry-run visualization.

    OPERATIONS FILE FORMAT (JSON):
    [
      {
        "operation": "edit",
        "file_path": "src/file.py",
        "symbol_name": "my_function",
        "new_code": "def my_function(): pass",
        "symbol_type": "function",
        "auto_format": true
      },
      {
        "operation": "delete",
        "file_path": "src/file.py",
        "symbol_name": "old_function"
      }
    ]
    """
    # Load operations from JSON file
    try:
        with open(operations_file, 'r', encoding='utf-8') as f:
            operations_data = json.load(f)
    except Exception as e:
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="JSON_PARSE_ERROR",
                message=f"Failed to parse operations file: {e}",
                actionable_fix="Ensure the file is valid JSON"
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: Failed to parse operations file: {e}[/red]")
        raise typer.Exit(code=1)

    # Parse operations using EditOperation schema
    from cerberus.schemas import EditOperation
    try:
        operations = [EditOperation(**op) for op in operations_data]
    except Exception as e:
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="SCHEMA_VALIDATION_ERROR",
                message=f"Invalid operation format: {e}",
                actionable_fix="Check operation schema in documentation"
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: Invalid operation format: {e}[/red]")
        raise typer.Exit(code=1)

    # Load index
    index_path = get_default_index(index_path)
    try:
        store = SQLiteIndexStore(str(index_path))
    except Exception as e:
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="INDEX_LOAD_ERROR",
                message=f"Failed to load index: {e}",
                actionable_fix="cerberus index ."
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: Failed to load index: {e}[/red]")
        raise typer.Exit(code=1)

    # Create facade
    facade = MutationFacade(store)

    # Execute batch edit
    result = facade.batch_edit(
        operations=operations,
        verify_command=verify if not preview else None,
        preview=preview
    )

    # Output result
    if CLIConfig.is_machine_mode() or json_output:
        print(json.dumps(result.model_dump(), separators=(',', ':')))
    else:
        if result.success:
            console.print(f"[green]✓[/green] Batch edit completed successfully")
            console.print(f"  Operations: {result.operations_completed}/{result.operations_total}")

            # Show brief summary of each operation
            for idx, mutation_result in enumerate(result.results, 1):
                console.print(f"\n  {idx}. {mutation_result.operation.upper()} {mutation_result.symbol_name} in {mutation_result.file_path}")
                console.print(f"     Lines changed: {mutation_result.lines_changed}, Efficiency: {mutation_result.write_efficiency:.1%}")
                if mutation_result.diff:
                    console.print(f"[dim]{mutation_result.diff}[/dim]")

            # Phase 12.5: JIT Guidance
            if GuidanceProvider.should_show_guidance(CLIConfig.is_machine_mode()):
                tip = GuidanceProvider.get_tip("batch-edit")
                if tip:
                    console.print(f"[dim cyan]{GuidanceProvider.format_tip(tip)}[/dim cyan]")
        else:
            console.print(f"[red]✗[/red] Batch edit failed")
            console.print(f"  Operations completed: {result.operations_completed}/{result.operations_total}")
            console.print(f"  Rolled back: {result.rolled_back}")

            for error in result.errors:
                console.print(f"  [red]Error:[/red] {error}")

    if not result.success:
        raise typer.Exit(code=1)


@app.command("undo")
def undo_cmd(
    transaction_id: Optional[str] = typer.Argument(None, help="Transaction ID to undo (defaults to most recent)"),
    list_history: bool = typer.Option(False, "--list", "-l", help="List transaction history"),
    limit: int = typer.Option(50, "--limit", "-n", help="Number of transactions to show in history"),
    clear_history: bool = typer.Option(False, "--clear", help="Clear transaction history"),
    keep_last: int = typer.Option(0, "--keep-last", "-k", help="Number of transactions to keep when clearing"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Undo a previous mutation transaction.

    Phase 12.5: Persistent undo stack with infinite "Ctrl+Z" for AI agents.
    """
    from cerberus.mutation import UndoStack

    undo = UndoStack()

    # List history mode
    if list_history:
        history = undo.get_history(limit=limit)

        if CLIConfig.is_machine_mode() or json_output:
            print(json.dumps(history, separators=(',', ':'), default=str))
        else:
            console.print(f"[bold]Transaction History[/bold] (showing {len(history)} most recent)\n")

            for tx in history:
                timestamp = tx.get("timestamp", "unknown")
                tx_id = tx.get("transaction_id", "unknown")
                op_type = tx.get("operation_type", "unknown")
                files = tx.get("files", [])
                console.print(f"[cyan]{tx_id}[/cyan] - {timestamp}")
                console.print(f"  Type: {op_type}, Files: {len(files)}")
                if files:
                    console.print(f"  Affected: {', '.join(files[:3])}{' ...' if len(files) > 3 else ''}")
                console.print()

        return

    # Clear history mode
    if clear_history:
        deleted_count = undo.clear_history(keep_last=keep_last)

        if CLIConfig.is_machine_mode() or json_output:
            result = {"success": True, "deleted_count": deleted_count}
            print(json.dumps(result, separators=(',', ':')))
        else:
            console.print(f"[green]✓[/green] Cleared {deleted_count} transaction(s)")
            if keep_last > 0:
                console.print(f"  Kept last {keep_last} transaction(s)")

        return

    # Undo mode
    if not transaction_id:
        # Get most recent transaction
        history = undo.get_history(limit=1)
        if not history:
            if CLIConfig.is_machine_mode() or json_output:
                error = structured_error(
                    code="NO_HISTORY",
                    message="No transaction history found",
                    actionable_fix="Use 'cerberus mutations undo --list' to view history"
                )
                print(json.dumps(error, separators=(',', ':')))
            else:
                console.print("[red]Error: No transaction history found[/red]")
            raise typer.Exit(code=1)

        transaction_id = history[0]["transaction_id"]
        if not (CLIConfig.is_machine_mode() or json_output):
            console.print(f"Using most recent transaction: [cyan]{transaction_id}[/cyan]\n")

    # Apply undo
    success, applied_files, errors = undo.apply_reverse_patches(transaction_id)

    if CLIConfig.is_machine_mode() or json_output:
        result = {
            "success": success,
            "transaction_id": transaction_id,
            "applied_files": applied_files,
            "errors": errors
        }
        print(json.dumps(result, separators=(',', ':')))
    else:
        if success:
            console.print(f"[green]✓[/green] Successfully undid transaction {transaction_id}")
            console.print(f"  Reverted {len(applied_files)} file(s):")
            for file_path in applied_files:
                console.print(f"    - {file_path}")
        else:
            console.print(f"[red]✗[/red] Failed to undo transaction {transaction_id}")
            for error in errors:
                console.print(f"  [red]Error:[/red] {error}")

    if not success:
        raise typer.Exit(code=1)
