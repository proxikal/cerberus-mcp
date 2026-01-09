"""
Agent session tracking for dogfooding metrics.

Tracks token usage and savings when AI agents use Cerberus CLI to explore/maintain codebases.
Shows beautiful summary of efficiency gains from using deterministic tools.
"""

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SessionMetrics:
    """Metrics for a Cerberus CLI session."""

    # Token tracking
    tokens_read: int = 0  # Total tokens read via Cerberus
    tokens_saved: int = 0  # Tokens saved via skeleton/range limits

    # Operation counts
    commands_used: Dict[str, int] = field(default_factory=dict)
    files_accessed: List[str] = field(default_factory=list)

    # Session info
    session_start: Optional[float] = None
    session_end: Optional[float] = None

    def record_command(self, command: str, tokens_read: int = 0, tokens_saved: int = 0, file_path: Optional[str] = None):
        """Record a command execution."""
        self.commands_used[command] = self.commands_used.get(command, 0) + 1
        self.tokens_read += tokens_read
        self.tokens_saved += tokens_saved

        if file_path and file_path not in self.files_accessed:
            self.files_accessed.append(file_path)

    def get_total_tokens(self) -> int:
        """Get total tokens that would have been used without Cerberus."""
        return self.tokens_read + self.tokens_saved

    def get_efficiency_percent(self) -> float:
        """Calculate efficiency percentage."""
        total = self.get_total_tokens()
        if total == 0:
            return 0.0
        return (self.tokens_saved / total) * 100

    def get_duration_seconds(self) -> float:
        """Get session duration in seconds."""
        if self.session_start and self.session_end:
            return self.session_end - self.session_start
        return 0.0


class SessionTracker:
    """Global session tracker for agent usage."""

    def __init__(self):
        self.metrics = SessionMetrics()
        
        # Enable tracking by default unless CERBERUS_NO_TRACK is set
        no_track = os.environ.get("CERBERUS_NO_TRACK", "false").lower() == "true"
        # Legacy support: also check CERBERUS_TRACK_SESSION
        track_session = os.environ.get("CERBERUS_TRACK_SESSION", "true").lower() == "true"
        
        self.enabled = not no_track and track_session
        
        # Dogfooding safeguard: if we are in the Cerberus repo itself, use a separate session file
        # to avoid polluting user sessions.
        is_dev = os.path.exists(os.path.join(os.getcwd(), ".git")) and "Cerberus" in os.getcwd()
        if is_dev:
            self.session_file = os.path.join(os.getcwd(), ".cerberus_dev_session.json")
        else:
            self.session_file = os.path.join(os.getcwd(), ".cerberus_session.json")

        if self.enabled:
            # Load existing session or create new one
            if os.path.exists(self.session_file):
                self._load_session()
            else:
                self.metrics.session_start = datetime.now().timestamp()
                self._save_session()

    def _load_session(self):
        """Load session from file."""
        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)
                self.metrics.tokens_read = data.get("tokens_read", 0)
                self.metrics.tokens_saved = data.get("tokens_saved", 0)
                self.metrics.commands_used = data.get("commands_used", {})
                self.metrics.files_accessed = data.get("files_accessed", [])
                self.metrics.session_start = data.get("session_start")
        except Exception:
            # If load fails, start fresh
            self.metrics.session_start = datetime.now().timestamp()

    def _save_session(self):
        """Save session to file."""
        try:
            data = {
                "tokens_read": self.metrics.tokens_read,
                "tokens_saved": self.metrics.tokens_saved,
                "commands_used": self.metrics.commands_used,
                "files_accessed": self.metrics.files_accessed,
                "session_start": self.metrics.session_start,
            }
            with open(self.session_file, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass  # Silently fail if can't save

    def record(self, command: str, tokens_read: int = 0, tokens_saved: int = 0, file_path: Optional[str] = None):
        """Record command usage."""
        if self.enabled:
            self.metrics.record_command(command, tokens_read, tokens_saved, file_path)
            self._save_session()  # Save after each command

    def finalize(self):
        """Finalize session and display summary."""
        if self.enabled and self.metrics.session_start:
            self.metrics.session_end = datetime.now().timestamp()

    def display_summary(self):
        """Display session summary respecting machine mode and metric configuration."""
        if not self.enabled:
            return

        # Skip if no commands were used
        if not self.metrics.commands_used:
            return

        # Import config to check machine mode and metric settings
        from cerberus.cli.config import CLIConfig

        # Protocol Enforcement (Phase 10 - Symbiosis Check)
        # Warn if human mode is being used during an agent session
        if not CLIConfig.is_machine_mode():
            print("\n[PROTOCOL] Warning: Human mode active. This burns tokens.")
            print("[PROTOCOL] Machine mode is default. Remove --human flag or set CERBERUS_HUMAN_MODE=0\n")

        # Check if metrics should be suppressed
        if CLIConfig.is_silent_metrics():
            return

        total_tokens = self.metrics.get_total_tokens()
        efficiency = self.metrics.get_efficiency_percent()

        # Machine mode: minimal text output
        if CLIConfig.is_machine_mode():
            # Only show what's requested
            if CLIConfig.show_session_savings():
                print(f"[Meta] Session Saved: {self.metrics.tokens_saved:,} tokens")
            if CLIConfig.show_turn_savings():
                # Show turn-level savings if requested
                pass  # Turn-level tracking would require per-command tracking
            return

        # Human mode: rich output
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = Console()

        # Create main stats table
        stats_table = Table.grid(padding=(0, 2))
        stats_table.add_column(style="cyan", justify="right")
        stats_table.add_column(style="bold white")

        # Tokens
        stats_table.add_row("Tokens Read:", f"{self.metrics.tokens_read:,}")
        stats_table.add_row("Tokens Saved:", f"[green]{self.metrics.tokens_saved:,}[/green]")
        stats_table.add_row("Total Tokens (without Cerberus):", f"[dim]{total_tokens:,}[/dim]")
        stats_table.add_row("Efficiency:", f"[bold green]{efficiency:.1f}%[/bold green]" if efficiency > 0 else "0%")

        # Commands
        commands_str = ", ".join(f"{cmd}({count})" for cmd, count in sorted(self.metrics.commands_used.items()))
        stats_table.add_row("", "")
        stats_table.add_row("Commands Used:", f"[yellow]{commands_str}[/yellow]")
        stats_table.add_row("Files Accessed:", f"{len(self.metrics.files_accessed)}")

        # Duration
        duration = self.metrics.get_duration_seconds()
        if duration > 0:
            stats_table.add_row("Session Duration:", f"{duration:.1f}s")

        # Create the panel
        title = Text()
        title.append("🤖 Agent Session Summary ", style="bold magenta")
        title.append("• Cerberus Dogfooding Metrics", style="dim")

        panel = Panel(
            stats_table,
            title=title,
            border_style="magenta",
            padding=(1, 2),
        )

        console.print()
        console.print(panel)

        # Show savings message if significant
        if self.metrics.tokens_saved > 1000:
            savings_msg = Text()
            savings_msg.append("💰 ", style="yellow")
            savings_msg.append(f"Saved {self.metrics.tokens_saved:,} tokens ", style="bold green")
            savings_msg.append("using deterministic context management!", style="dim")
            console.print(savings_msg, justify="center")
            console.print()


# Global session tracker instance
_session_tracker: Optional[SessionTracker] = None


def get_session_tracker() -> SessionTracker:
    """Get or create the global session tracker."""
    global _session_tracker
    if _session_tracker is None:
        _session_tracker = SessionTracker()
    return _session_tracker


def record_operation(command: str, tokens_read: int = 0, tokens_saved: int = 0, file_path: Optional[str] = None):
    """Record an operation in the session tracker."""
    tracker = get_session_tracker()
    tracker.record(command, tokens_read, tokens_saved, file_path)


def display_session_summary():
    """Display the session summary if tracking is enabled."""
    tracker = get_session_tracker()
    tracker.finalize()
    tracker.display_summary()


def clear_session():
    """Clear the session file."""
    tracker = get_session_tracker()
    if tracker.enabled and os.path.exists(tracker.session_file):
        try:
            os.remove(tracker.session_file)
        except Exception:
            pass
