"""
CLI Quality Commands - Phase 14.1: Style Guard

style-check: Preview style issues without changes
style-fix: Apply style fixes with Symbol Guard integration
"""

import json
import typer
from pathlib import Path
from typing import Optional

from rich.table import Table

from cerberus.logging_config import logger
from cerberus.quality import StyleDetector, StyleFixer
from .output import get_console, structured_error
from .config import CLIConfig

app = typer.Typer()
console = get_console()


@app.command("style-check")
def style_check_cmd(
    path: Path = typer.Argument(..., help="File or directory to check", exists=True),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Recursively check subdirectories"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Check for style issues without making changes.

    Phase 14.1: Preview mode - shows what would be fixed without modifying files.

    Examples:
        cerberus quality style-check src/main.py
        cerberus quality style-check src/ --recursive
        cerberus quality style-check src/core.py --json
    """
    detector = StyleDetector()

    try:
        # Check if path is file or directory
        if path.is_file():
            issues = detector.check_file(str(path))

            if CLIConfig.is_machine_mode() or json_output:
                # Machine mode - JSON output
                output = {
                    "command": "quality.style-check",
                    "status": "success",
                    "file": str(path),
                    "issues": [issue.to_dict() for issue in issues],
                    "count": len(issues),
                }
                print(json.dumps(output, indent=2 if not CLIConfig.is_machine_mode() else None))
            else:
                # Human mode - pretty output
                if not issues:
                    console.print(f"✅ No style issues detected in [cyan]{path}[/cyan]")
                else:
                    console.print(f"⚠️  [yellow]{len(issues)} style issue(s) detected in {path}[/yellow]")
                    console.print()

                    for issue in issues:
                        if issue.line:
                            console.print(f"  Line {issue.line}: {issue.description}")
                        elif issue.lines:
                            start, end = issue.lines
                            console.print(f"  Lines {start}-{end}: {issue.description}")
                        else:
                            console.print(f"  {issue.description}")

                        if issue.suggestion:
                            console.print(f"    [dim]→ {issue.suggestion}[/dim]")

                    console.print()
                    console.print(f"[dim]💡 Fix with: cerberus quality style-fix {path}[/dim]")

        elif path.is_dir():
            results = detector.check_directory(str(path), recursive=recursive)

            if CLIConfig.is_machine_mode() or json_output:
                # Machine mode - JSON output
                output = {
                    "command": "quality.style-check",
                    "status": "success",
                    "directory": str(path),
                    "files_checked": len(results),
                    "files_with_issues": len([r for r in results.values() if r]),
                    "results": {
                        file: [issue.to_dict() for issue in issues]
                        for file, issues in results.items()
                    },
                }
                print(json.dumps(output, indent=2 if not CLIConfig.is_machine_mode() else None))
            else:
                # Human mode - pretty output
                if not results:
                    console.print(f"✅ No style issues detected in [cyan]{path}[/cyan]")
                else:
                    total_issues = sum(len(issues) for issues in results.values())
                    console.print(
                        f"⚠️  [yellow]{total_issues} style issue(s) in {len(results)} file(s)[/yellow]"
                    )
                    console.print()

                    for file_path, issues in results.items():
                        console.print(f"[cyan]{file_path}[/cyan]: {len(issues)} issue(s)")
                        for issue in issues[:3]:  # Show first 3 issues per file
                            if issue.line:
                                console.print(f"  Line {issue.line}: {issue.description}")
                            elif issue.lines:
                                start, end = issue.lines
                                console.print(f"  Lines {start}-{end}: {issue.description}")

                        if len(issues) > 3:
                            console.print(f"  [dim]... and {len(issues) - 3} more[/dim]")
                        console.print()

                    console.print(f"[dim]💡 Fix with: cerberus quality style-fix {path} --recursive[/dim]")

    except Exception as e:
        logger.error(f"Style check failed: {e}")
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="STYLE_CHECK_ERROR",
                message=f"Style check failed: {e}",
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: Style check failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("style-fix")
def style_fix_cmd(
    path: Path = typer.Argument(..., help="File or directory to fix", exists=True),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Recursively fix subdirectories"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Preview changes without applying"),
    force: bool = typer.Option(False, "--force", help="Force fix HIGH RISK files (override Symbol Guard)"),
    verify: Optional[str] = typer.Option(None, "--verify", "-v", help="Run command after fixing (e.g., 'pytest tests/')"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Apply style fixes to files.

    Phase 14.1: Explicit style fixing with Symbol Guard integration.

    Symbol Guard Protection:
        - HIGH RISK files are blocked by default (require --force)
        - MEDIUM/SAFE files are fixed automatically
        - Risk scoring integrates with Phase 13.2 stability metrics

    Examples:
        cerberus quality style-fix src/main.py
        cerberus quality style-fix src/ --recursive
        cerberus quality style-fix src/core.py --preview
        cerberus quality style-fix src/critical.py --force  # Override Symbol Guard
        cerberus quality style-fix src/ --verify "pytest tests/"  # Fix + verify
    """
    fixer = StyleFixer()

    try:
        # Check if path is file or directory
        if path.is_file():
            success, fixes = fixer.fix_file(str(path), preview=preview, force=force)

            if CLIConfig.is_machine_mode() or json_output:
                # Machine mode - JSON output
                output = {
                    "command": "quality.style-fix",
                    "status": "success" if success else "failed",
                    "file": str(path),
                    "preview": preview,
                    "fixes": [fix.to_dict() for fix in fixes],
                    "count": len(fixes),
                }
                print(json.dumps(output, indent=2 if not CLIConfig.is_machine_mode() else None))
            else:
                # Human mode - pretty output
                if not success:
                    console.print(f"[red]❌ Failed to fix {path}[/red]")
                    raise typer.Exit(code=1)

                if not fixes:
                    console.print(f"✅ No style issues in [cyan]{path}[/cyan]")
                else:
                    if preview:
                        console.print(f"[yellow]Preview: Would apply {len(fixes)} fix(es) to {path}[/yellow]")
                    else:
                        console.print(f"✅ Applied {len(fixes)} fix(es) to [cyan]{path}[/cyan]")

                    console.print()
                    for fix in fixes:
                        if fix.line:
                            console.print(f"  Line {fix.line}: {fix.description}")
                        elif fix.lines:
                            start, end = fix.lines
                            console.print(f"  Lines {start}-{end}: {fix.description}")
                        else:
                            console.print(f"  {fix.description}")

            # Run verification if requested
            if verify and not preview and fixes:
                console.print()
                console.print(f"[dim]Running verification: {verify}[/dim]")
                import subprocess
                result = subprocess.run(verify, shell=True, capture_output=True, text=True)

                if result.returncode != 0:
                    console.print("[red]❌ Verification failed![/red]")
                    console.print(result.stdout)
                    console.print(result.stderr)
                    raise typer.Exit(code=1)
                else:
                    console.print("[green]✅ Verification passed[/green]")

        elif path.is_dir():
            results = fixer.fix_directory(str(path), recursive=recursive, preview=preview, force=force)

            if CLIConfig.is_machine_mode() or json_output:
                # Machine mode - JSON output
                output = {
                    "command": "quality.style-fix",
                    "status": "success",
                    "directory": str(path),
                    "preview": preview,
                    "files_processed": len(results),
                    "files_fixed": len([r for r in results.values() if r[0] and r[1]]),
                    "results": {
                        file: {
                            "success": success,
                            "fixes": [fix.to_dict() for fix in fixes],
                            "count": len(fixes),
                        }
                        for file, (success, fixes) in results.items()
                    },
                }
                print(json.dumps(output, indent=2 if not CLIConfig.is_machine_mode() else None))
            else:
                # Human mode - pretty output
                total_fixes = sum(len(fixes) for _, fixes in results.values())
                fixed_files = len([r for r in results.values() if r[0] and r[1]])

                if preview:
                    console.print(
                        f"[yellow]Preview: Would apply {total_fixes} fix(es) to {fixed_files} file(s)[/yellow]"
                    )
                else:
                    console.print(f"✅ Applied {total_fixes} fix(es) to {fixed_files} file(s)")

                console.print()
                for file_path, (success, fixes) in results.items():
                    if fixes:
                        console.print(f"[cyan]{file_path}[/cyan]: {len(fixes)} fix(es)")

            # Run verification if requested
            if verify and not preview and total_fixes > 0:
                console.print()
                console.print(f"[dim]Running verification: {verify}[/dim]")
                import subprocess
                result = subprocess.run(verify, shell=True, capture_output=True, text=True)

                if result.returncode != 0:
                    console.print("[red]❌ Verification failed![/red]")
                    console.print(result.stdout)
                    console.print(result.stderr)
                    raise typer.Exit(code=1)
                else:
                    console.print("[green]✅ Verification passed[/green]")

    except Exception as e:
        logger.error(f"Style fix failed: {e}")
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="STYLE_FIX_ERROR",
                message=f"Style fix failed: {e}",
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: Style fix failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("related-changes")
def related_changes_cmd(
    symbol: str = typer.Argument(..., help="Symbol name to analyze"),
    file_path: Optional[Path] = typer.Option(None, "--file", "-f", help="File containing the symbol", exists=True),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed prediction reasoning"),
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
    Show predicted related changes for a symbol (Phase 14.3).

    Uses deterministic AST relationships to suggest files/symbols that may need
    updates when the given symbol changes.

    Examples:
        cerberus quality related-changes validate_ops
        cerberus quality related-changes batch_edit --file src/mutations.py
        cerberus quality related-changes AuthConfig --verbose
        cerberus quality related-changes process_request --json
    """
    from cerberus.quality.predictor import PredictionEngine
    from .common import get_default_index

    # Get index path
    index_path = get_default_index(index_path)

    try:
        # Initialize prediction engine
        engine = PredictionEngine(str(index_path))

        # If file_path provided, use it; otherwise try to find the symbol
        if not file_path:
            # Query index to find the symbol's file
            import sqlite3
            conn = sqlite3.connect(str(index_path))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_path FROM symbols
                WHERE name = ?
                LIMIT 1
            """, (symbol,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                error_msg = f"Symbol '{symbol}' not found in index. Provide --file explicitly."
                if CLIConfig.is_machine_mode() or json_output:
                    error = structured_error(
                        code="SYMBOL_NOT_FOUND",
                        message=error_msg,
                        suggestions=[f"cerberus retrieval get-symbol {symbol}"]
                    )
                    print(json.dumps(error, separators=(',', ':')))
                else:
                    console.print(f"[red]Error: {error_msg}[/red]")
                raise typer.Exit(code=1)

            file_path = Path(row[0])

        # Get predictions
        predictions, stats = engine.predict_related_changes(
            edited_symbol=symbol,
            file_path=str(file_path)
        )

        # Output
        if CLIConfig.is_machine_mode() or json_output:
            # Machine mode - JSON
            output = engine.to_json(predictions, stats)
            print(json.dumps(output, separators=(',', ':')))
        else:
            # Human mode - rich output
            if not predictions:
                console.print(f"[yellow]No high-confidence related changes found for '{symbol}'[/yellow]")
                console.print(f"[dim]This means no direct callers, dependencies, or test files were detected.[/dim]")
            else:
                console.print(f"[cyan]🔮 Predicted Related Changes for '{symbol}'[/cyan]")
                console.print(f"[dim]File: {file_path}[/dim]\n")

                for i, pred in enumerate(predictions, 1):
                    confidence_emoji = "🔮" if pred.confidence == "HIGH" else "⚠️"
                    console.print(f"{i}. {confidence_emoji} [bold]{pred.symbol}[/bold]")
                    console.print(f"   File: {pred.file}:{pred.line}")
                    console.print(f"   Relationship: {pred.relationship}")

                    if verbose:
                        console.print(f"   Confidence: {pred.confidence_score:.2f}")
                        console.print(f"   Reason: {pred.reason}")
                        if pred.command:
                            console.print(f"   Command: [dim]{pred.command}[/dim]")

                    console.print()  # Blank line

                # Show stats
                console.print(f"[dim]Stats: {stats.high_confidence} high-confidence predictions " +
                             f"({stats.filtered} filtered out)[/dim]")

    except Exception as e:
        logger.error(f"Related changes analysis failed: {e}")
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="PREDICTION_ERROR",
                message=f"Related changes analysis failed: {e}",
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: Related changes analysis failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command("prediction-stats")
def prediction_stats_cmd(
    time_window: int = typer.Option(900, "--window", "-w", help="Time window in seconds to correlate actions (default: 900 = 15 min)"),
    limit: int = typer.Option(100, "--limit", "-l", help="Number of recent predictions to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
):
    """
    Phase 14.4: Show prediction accuracy statistics.

    Correlates predictions with agent actions to calculate accuracy metrics.

    Examples:
      cerberus quality prediction-stats
      cerberus quality prediction-stats --window 600 --limit 50
      cerberus quality prediction-stats --json
    """
    try:
        from cerberus.mutation.ledger import DiffLedger

        ledger = DiffLedger()

        # Get accuracy metrics
        accuracy = ledger.get_prediction_accuracy(
            time_window=float(time_window),
            limit=limit
        )

        # Get basic prediction stats
        basic_stats = ledger.get_prediction_stats(limit=limit)

        if CLIConfig.is_machine_mode() or json_output:
            # Machine mode: JSON output
            output = {
                "accuracy": accuracy,
                "basic_stats": basic_stats
            }
            print(json.dumps(output, separators=(',', ':')))
        else:
            # Human mode: Rich formatted output
            console.print("[bold cyan]Prediction Accuracy Statistics (Phase 14.4)[/bold cyan]\n")

            # Accuracy metrics
            console.print("[bold]Accuracy Metrics:[/bold]")
            console.print(f"  Total Predictions: {accuracy['total_predictions']}")
            console.print(f"  Predictions Followed: [green]{accuracy['predictions_followed']}[/green]")
            console.print(f"  Predictions Ignored: [yellow]{accuracy['predictions_ignored']}[/yellow]")
            console.print(f"  Accuracy Rate: [bold]{accuracy['accuracy_rate']:.1%}[/bold]")

            if accuracy['predictions_followed'] > 0:
                console.print(f"  Avg Time to Action: {accuracy['avg_time_to_action_seconds']:.1f}s")

            console.print(f"  Time Window: {accuracy['time_window_seconds']}s ({accuracy['time_window_seconds']/60:.1f} min)")
            console.print(f"  Sample Size: {accuracy['sample_size']} prediction logs\n")

            # Basic stats
            console.print("[bold]Prediction Stats:[/bold]")
            console.print(f"  Total Prediction Logs: {basic_stats['total_prediction_logs']}")
            console.print(f"  Avg Predictions Per Edit: {basic_stats['average_predictions_per_edit']:.1f}")

            if basic_stats['top_predicted_symbols']:
                console.print(f"\n[bold]Most Frequently Predicted Symbols:[/bold]")
                for symbol, count in list(basic_stats['top_predicted_symbols'].items())[:5]:
                    console.print(f"    {symbol}: {count} times")

            # Interpretation
            console.print(f"\n[dim]Interpretation:[/dim]")
            accuracy_rate = accuracy['accuracy_rate']
            if accuracy_rate >= 0.9:
                console.print(f"[dim]  🟢 Excellent: {accuracy_rate:.1%} of predictions are followed by agents[/dim]")
            elif accuracy_rate >= 0.7:
                console.print(f"[dim]  🟡 Good: {accuracy_rate:.1%} of predictions are useful[/dim]")
            elif accuracy_rate >= 0.5:
                console.print(f"[dim]  🟠 Fair: {accuracy_rate:.1%} accuracy, room for improvement[/dim]")
            else:
                console.print(f"[dim]  🔴 Low: {accuracy_rate:.1%} accuracy, predictions may need tuning[/dim]")

    except Exception as e:
        logger.error(f"Failed to get prediction stats: {e}")
        if CLIConfig.is_machine_mode() or json_output:
            error = structured_error(
                code="STATS_ERROR",
                message=f"Failed to get prediction stats: {e}",
            )
            print(json.dumps(error, separators=(',', ':')))
        else:
            console.print(f"[red]Error: Failed to get prediction stats: {e}[/red]")
        raise typer.Exit(code=1)
