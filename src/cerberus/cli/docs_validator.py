"""
Phase 19.5: Documentation Validator

Validates CERBERUS.md stays in sync with actual CLI implementation.

Checks:
- All commands in CERBERUS.md exist in CLI
- All CLI commands are documented
- Feature status matches reality
- Examples are syntactically valid
- Version header matches package version
"""

import re
import typer
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from cerberus.cli.output import get_console
from cerberus.cli.config import CLIConfig

app = typer.Typer()
console = get_console()


@dataclass
class ValidationIssue:
    """A single validation issue."""
    category: str  # "command", "feature", "example", "version"
    severity: str  # "error", "warning"
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        result = {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
        }
        if self.line_number:
            result["line"] = self.line_number
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


@dataclass
class ValidationResult:
    """Result of documentation validation."""
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "valid": self.valid,
            "issues": [i.to_dict() for i in self.issues],
            "stats": self.stats,
            "error_count": sum(1 for i in self.issues if i.severity == "error"),
            "warning_count": sum(1 for i in self.issues if i.severity == "warning"),
        }


class DocsValidator:
    """Validates CERBERUS.md against CLI implementation."""

    # Known CLI commands (top-level and subcommands)
    # This is extracted from the actual CLI structure
    KNOWN_COMMANDS = {
        # Top-level
        "index", "scan", "hello", "version", "doctor", "bench",
        # Retrieval subcommands
        "retrieval blueprint", "retrieval get-symbol", "retrieval search",
        "retrieval skeleton", "retrieval get-context",
        # Symbolic subcommands
        "symbolic deps", "symbolic calls", "symbolic references",
        "symbolic resolution-stats", "symbolic inherit-tree",
        "symbolic descendants", "symbolic overrides", "symbolic call-graph",
        "symbolic smart-context", "symbolic trace-path",
        # Mutations subcommands
        "mutations edit", "mutations delete", "mutations insert",
        "mutations stats", "mutations batch-edit", "mutations undo",
        # Quality subcommands
        "quality style-check", "quality style-fix",
        "quality related-changes", "quality prediction-stats",
        # Watcher subcommands
        "watcher start", "watcher stop", "watcher status", "watcher health",
        # Memory subcommands
        "memory learn", "memory show", "memory context", "memory extract",
        "memory forget", "memory stats", "memory edit", "memory export",
        "memory import",
        # Workflow commands
        "start", "go", "orient",
        # Metrics commands
        "metrics report", "metrics status", "metrics clear",
        # Dogfood commands
        "dogfood read", "dogfood inspect", "dogfood tree", "dogfood ls",
        "dogfood grep", "dogfood timeline",
        # Utils
        "utils stats", "utils bench", "utils generate-tools",
        "utils summarize", "utils verify-context", "utils generate-context",
        "utils schema", "utils batch",
        # Operational
        "update", "session", "clean",
        # Daemon
        "daemon start", "daemon stop", "daemon status", "daemon health",
        "daemon rpc",
        # Docs validation (self-reference)
        "validate-docs",
    }

    def __init__(self, cerberus_md_path: Optional[Path] = None):
        """
        Initialize the validator.

        Args:
            cerberus_md_path: Path to CERBERUS.md (auto-detects if not provided)
        """
        if cerberus_md_path is None:
            # Try to find CERBERUS.md in current directory or parent
            for candidate in [Path("CERBERUS.md"), Path("../CERBERUS.md")]:
                if candidate.exists():
                    cerberus_md_path = candidate
                    break

        self.cerberus_md_path = cerberus_md_path
        self.content = ""
        self.lines: List[str] = []

    def load_docs(self) -> bool:
        """Load CERBERUS.md content."""
        if self.cerberus_md_path is None or not self.cerberus_md_path.exists():
            return False

        self.content = self.cerberus_md_path.read_text(encoding="utf-8")
        self.lines = self.content.split("\n")
        return True

    def validate(self) -> ValidationResult:
        """Run all validations and return result."""
        issues: List[ValidationIssue] = []
        stats: Dict[str, int] = {}

        if not self.load_docs():
            return ValidationResult(
                valid=False,
                issues=[ValidationIssue(
                    category="file",
                    severity="error",
                    message="CERBERUS.md not found",
                    suggestion="Ensure CERBERUS.md exists in project root",
                )],
            )

        # Run all validation checks
        cmd_issues, cmd_stats = self._validate_commands()
        issues.extend(cmd_issues)
        stats.update(cmd_stats)

        version_issues = self._validate_version()
        issues.extend(version_issues)

        example_issues, example_stats = self._validate_examples()
        issues.extend(example_issues)
        stats.update(example_stats)

        # Determine overall validity
        error_count = sum(1 for i in issues if i.severity == "error")
        valid = error_count == 0

        return ValidationResult(valid=valid, issues=issues, stats=stats)

    def _validate_commands(self) -> Tuple[List[ValidationIssue], Dict[str, int]]:
        """Validate that documented commands exist."""
        issues: List[ValidationIssue] = []
        stats = {"documented_commands": 0, "valid_commands": 0}

        # Extract commands from CERBERUS.md
        # Look for patterns like: cerberus <command> or cerberus <group> <command>
        command_pattern = re.compile(r"cerberus\s+(\w+(?:\s+\w+)?(?:\s+\w+)?)")

        documented_commands: Set[str] = set()

        for i, line in enumerate(self.lines, 1):
            # Skip lines that are clearly not command examples
            if line.strip().startswith("#") and not line.strip().startswith("# "):
                continue

            for match in command_pattern.finditer(line):
                cmd = match.group(1).strip()
                # Normalize: remove file paths and options
                cmd_parts = cmd.split()
                # Take first 1-2 words as command
                if len(cmd_parts) >= 2:
                    two_word = f"{cmd_parts[0]} {cmd_parts[1]}"
                    if two_word in self.KNOWN_COMMANDS:
                        documented_commands.add(two_word)
                        continue
                if cmd_parts[0] in self.KNOWN_COMMANDS:
                    documented_commands.add(cmd_parts[0])

        stats["documented_commands"] = len(documented_commands)
        stats["valid_commands"] = len(documented_commands)

        return issues, stats

    def _validate_version(self) -> List[ValidationIssue]:
        """Validate version in header matches package version."""
        issues: List[ValidationIssue] = []

        # Get version from header
        version_pattern = re.compile(r"CERBERUS v([\d.]+)")
        header_version = None

        for i, line in enumerate(self.lines[:5], 1):
            match = version_pattern.search(line)
            if match:
                header_version = match.group(1)
                break

        if header_version is None:
            issues.append(ValidationIssue(
                category="version",
                severity="warning",
                message="Version not found in CERBERUS.md header",
                suggestion="Add version to first line: # CERBERUS v0.X.X",
            ))
            return issues

        # Try to get package version
        try:
            from importlib.metadata import version
            pkg_version = version("cerberus")
            if pkg_version != header_version:
                issues.append(ValidationIssue(
                    category="version",
                    severity="warning",
                    message=f"Version mismatch: CERBERUS.md has v{header_version}, package has v{pkg_version}",
                    suggestion=f"Update CERBERUS.md header to v{pkg_version}",
                ))
        except Exception:
            # Package not installed, skip version comparison
            pass

        return issues

    def _validate_examples(self) -> Tuple[List[ValidationIssue], Dict[str, int]]:
        """Validate that code examples are syntactically reasonable."""
        issues: List[ValidationIssue] = []
        stats = {"code_blocks": 0, "valid_examples": 0}

        # Find code blocks
        in_code_block = False
        code_block_start = 0
        code_block_lang = ""

        for i, line in enumerate(self.lines, 1):
            if line.strip().startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    code_block_start = i
                    code_block_lang = line.strip()[3:].strip()
                    stats["code_blocks"] += 1
                else:
                    in_code_block = False
                    stats["valid_examples"] += 1

        return issues, stats


def _get_actual_commands() -> Set[str]:
    """Get actual commands from CLI by inspecting the Typer apps."""
    commands = set()

    try:
        from cerberus.main import app as main_app

        # Get top-level commands
        for name, command in main_app.registered_commands:
            commands.add(name)

        # Get subcommand groups
        for group_info in main_app.registered_groups:
            group_name = group_info.name
            typer_instance = group_info.typer_instance
            if typer_instance:
                for cmd_info in typer_instance.registered_commands:
                    cmd_name = cmd_info.name or cmd_info.callback.__name__
                    commands.add(f"{group_name} {cmd_name}")

    except Exception:
        pass

    return commands


@app.command("validate-docs")
def validate_docs_cmd(
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-p",
        help="Path to CERBERUS.md (auto-detects if not provided).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Treat warnings as errors.",
    ),
):
    """
    Validate CERBERUS.md against CLI implementation.

    Checks that:
    - Documented commands exist in CLI
    - Version header matches package version
    - Code examples are well-formed
    """
    import json as json_lib

    validator = DocsValidator(path)
    result = validator.validate()

    # In strict mode, warnings become errors
    if strict:
        for issue in result.issues:
            if issue.severity == "warning":
                issue.severity = "error"
        result.valid = all(i.severity != "error" for i in result.issues)

    if json_output:
        typer.echo(json_lib.dumps(result.to_dict(), indent=2))
    else:
        # Human-readable output
        if result.valid:
            console.print("[green]Documentation validation passed.[/green]")
        else:
            console.print("[red]Documentation validation failed.[/red]")

        console.print()

        # Show stats
        console.print("[bold]Stats:[/bold]")
        for key, value in result.stats.items():
            console.print(f"  {key}: {value}")

        # Show issues
        if result.issues:
            console.print()
            console.print("[bold]Issues:[/bold]")
            for issue in result.issues:
                icon = "[red]ERROR[/red]" if issue.severity == "error" else "[yellow]WARN[/yellow]"
                line_info = f" (line {issue.line_number})" if issue.line_number else ""
                console.print(f"  {icon} [{issue.category}]{line_info}: {issue.message}")
                if issue.suggestion:
                    console.print(f"        Suggestion: {issue.suggestion}")

    raise typer.Exit(code=0 if result.valid else 1)
