"""
Agent session tracking for dogfooding metrics.

Tracks token usage and savings when AI agents use Cerberus CLI to explore/maintain codebases.
Shows beautiful summary of efficiency gains from using deterministic tools.

Features:
- Per-task token tracking (resets after each summary display)
- Session-level cumulative tracking
- Auto-reset after inactivity (1 hour by default)
- Token-to-dollar cost savings conversion
- Default display after task completion
"""

import os
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SessionMetrics:
    """Metrics for a Cerberus CLI session."""

    # Session-level token tracking (cumulative)
    tokens_read: int = 0  # Total tokens read via Cerberus (session)
    tokens_saved: int = 0  # Tokens saved via skeleton/range limits (session)

    # Per-task token tracking (resets after display)
    task_tokens_read: int = 0  # Tokens read in current task
    task_tokens_saved: int = 0  # Tokens saved in current task

    # Operation counts
    commands_used: Dict[str, int] = field(default_factory=dict)
    files_accessed: List[str] = field(default_factory=list)

    # Session info
    session_start: Optional[float] = None
    session_end: Optional[float] = None
    last_operation_time: Optional[float] = None  # For inactivity detection

    def record_command(self, command: str, tokens_read: int = 0, tokens_saved: int = 0, file_path: Optional[str] = None):
        """Record a command execution."""
        self.commands_used[command] = self.commands_used.get(command, 0) + 1

        # Update session-level counters
        self.tokens_read += tokens_read
        self.tokens_saved += tokens_saved

        # Update per-task counters
        self.task_tokens_read += tokens_read
        self.task_tokens_saved += tokens_saved

        # Update last operation timestamp
        self.last_operation_time = time.time()

        if file_path and file_path not in self.files_accessed:
            self.files_accessed.append(file_path)

    def reset_task_metrics(self):
        """Reset per-task metrics after displaying summary."""
        self.task_tokens_read = 0
        self.task_tokens_saved = 0

    def get_total_tokens(self) -> int:
        """Get total tokens that would have been used without Cerberus (session)."""
        return self.tokens_read + self.tokens_saved

    def get_task_total_tokens(self) -> int:
        """Get total tokens for current task."""
        return self.task_tokens_read + self.task_tokens_saved

    def get_efficiency_percent(self) -> float:
        """Calculate efficiency percentage (session)."""
        total = self.get_total_tokens()
        if total == 0:
            return 0.0
        return (self.tokens_saved / total) * 100

    def get_task_efficiency_percent(self) -> float:
        """Calculate efficiency percentage (current task)."""
        total = self.get_task_total_tokens()
        if total == 0:
            return 0.0
        return (self.task_tokens_saved / total) * 100

    def get_duration_seconds(self) -> float:
        """Get session duration in seconds."""
        if self.session_start and self.session_end:
            return self.session_end - self.session_start
        return 0.0

    @staticmethod
    def tokens_to_dollars(tokens: int, is_output: bool = False) -> float:
        """
        Convert tokens to dollar cost savings.

        Uses Claude Sonnet 4.5 pricing (as of Jan 2026):
        - Input: $3.00 per 1M tokens
        - Output: $15.00 per 1M tokens

        Args:
            tokens: Number of tokens
            is_output: Whether these are output tokens (more expensive)

        Returns:
            Dollar amount
        """
        if tokens == 0:
            return 0.0

        # Claude Sonnet 4.5 pricing
        price_per_million = 15.0 if is_output else 3.0

        return (tokens / 1_000_000) * price_per_million


class SessionTracker:
    """Global session tracker for agent usage."""

    # Session timeout: reset after 1 hour of inactivity (configurable via env)
    DEFAULT_SESSION_TIMEOUT = 3600  # 1 hour in seconds

    def __init__(self):
        self.metrics = SessionMetrics()

        # Get session timeout from environment or use default
        timeout_str = os.environ.get("CERBERUS_SESSION_TIMEOUT", str(self.DEFAULT_SESSION_TIMEOUT))
        try:
            self.session_timeout = int(timeout_str)
        except ValueError:
            self.session_timeout = self.DEFAULT_SESSION_TIMEOUT

        # Enable tracking by default unless CERBERUS_NO_TRACK is set
        no_track = os.environ.get("CERBERUS_NO_TRACK", "false").lower() == "true"
        # Legacy support: also check CERBERUS_TRACK_SESSION
        track_session = os.environ.get("CERBERUS_TRACK_SESSION", "true").lower() == "true"

        self.enabled = not no_track and track_session

        # Use centralized paths for session file location
        from cerberus.paths import get_paths
        paths = get_paths()
        # Ensure .cerberus directory exists
        paths.ensure_dirs()
        # Get appropriate session file based on dev mode
        self.session_file = str(paths.get_session_file())

        if self.enabled:
            # Load existing session or create new one
            if os.path.exists(self.session_file):
                self._load_session()
                # Check if session has timed out due to inactivity
                if self._is_session_expired():
                    self._reset_session()
            else:
                self.metrics.session_start = time.time()
                self.metrics.last_operation_time = time.time()
                self._save_session()

    def _is_session_expired(self) -> bool:
        """Check if session has expired due to inactivity."""
        if not self.metrics.last_operation_time:
            return False

        elapsed = time.time() - self.metrics.last_operation_time
        return elapsed > self.session_timeout

    def _reset_session(self):
        """Reset session metrics (called after timeout)."""
        self.metrics = SessionMetrics()
        self.metrics.session_start = time.time()
        self.metrics.last_operation_time = time.time()
        self._save_session()

    def _load_session(self):
        """Load session from file."""
        try:
            with open(self.session_file, 'r') as f:
                data = json.load(f)
                self.metrics.tokens_read = data.get("tokens_read", 0)
                self.metrics.tokens_saved = data.get("tokens_saved", 0)
                self.metrics.task_tokens_read = data.get("task_tokens_read", 0)
                self.metrics.task_tokens_saved = data.get("task_tokens_saved", 0)
                self.metrics.commands_used = data.get("commands_used", {})
                self.metrics.files_accessed = data.get("files_accessed", [])
                self.metrics.session_start = data.get("session_start")
                self.metrics.last_operation_time = data.get("last_operation_time")
        except Exception:
            # If load fails, start fresh
            self.metrics.session_start = time.time()
            self.metrics.last_operation_time = time.time()

    def _save_session(self):
        """Save session to file."""
        try:
            data = {
                "tokens_read": self.metrics.tokens_read,
                "tokens_saved": self.metrics.tokens_saved,
                "task_tokens_read": self.metrics.task_tokens_read,
                "task_tokens_saved": self.metrics.task_tokens_saved,
                "commands_used": self.metrics.commands_used,
                "files_accessed": self.metrics.files_accessed,
                "session_start": self.metrics.session_start,
                "last_operation_time": self.metrics.last_operation_time,
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

    def display_summary(self, show_task_summary: bool = True):
        """
        Display task and session summary with token savings and cost calculations.

        Args:
            show_task_summary: If True, show per-task metrics. If False, only show session.
        """
        if not self.enabled:
            return

        # Skip if no operations recorded
        if self.metrics.tokens_read == 0 and self.metrics.tokens_saved == 0:
            return

        # Import config to check machine mode and metric settings
        from cerberus.cli.config import CLIConfig

        # Check if metrics should be suppressed
        if CLIConfig.is_silent_metrics():
            return

        # Calculate task metrics
        task_total = self.metrics.get_task_total_tokens()
        task_efficiency = self.metrics.get_task_efficiency_percent()
        task_dollars = SessionMetrics.tokens_to_dollars(self.metrics.task_tokens_saved, is_output=False)

        # Calculate session metrics
        session_total = self.metrics.get_total_tokens()
        session_efficiency = self.metrics.get_efficiency_percent()
        session_dollars = SessionMetrics.tokens_to_dollars(self.metrics.tokens_saved, is_output=False)

        # Machine mode: compact default output
        if CLIConfig.is_machine_mode():
            # Only display when showing task summary (at task completion)
            # This prevents session summary from appearing after every single command
            if not show_task_summary:
                return

            # Skip if no task data to show
            if task_total == 0:
                return

            print()  # Newline for readability

            # Show task summary
            print(f"[Task] Saved: {self.metrics.task_tokens_saved:,} tokens (~${task_dollars:.4f}) | Efficiency: {task_efficiency:.1f}%")

            # Show session summary (only at task completion)
            print(f"[Session] Saved: {self.metrics.tokens_saved:,} tokens (~${session_dollars:.2f}) | Efficiency: {session_efficiency:.1f}%")
            print()  # Newline for readability

            # Reset task metrics after displaying
            self.metrics.reset_task_metrics()
            self._save_session()

            return

        # Human mode: rich output
        # Only display when showing task summary (at task completion)
        if not show_task_summary:
            return

        # Skip if no task data to show
        if task_total == 0:
            return

        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        console = Console()

        # Create main stats table
        stats_table = Table.grid(padding=(0, 2))
        stats_table.add_column(style="cyan", justify="right")
        stats_table.add_column(style="bold white")

        # Task metrics
        if task_total > 0:
            stats_table.add_row("[bold]This Task:", "")
            stats_table.add_row("  Tokens Saved:", f"[green]{self.metrics.task_tokens_saved:,}[/green]")
            stats_table.add_row("  Cost Savings:", f"[green]${task_dollars:.4f}[/green]")
            stats_table.add_row("  Efficiency:", f"[bold green]{task_efficiency:.1f}%[/bold green]")
            stats_table.add_row("", "")

        # Session metrics
        stats_table.add_row("[bold]This Session:", "")
        stats_table.add_row("  Tokens Saved:", f"[green]{self.metrics.tokens_saved:,}[/green]")
        stats_table.add_row("  Cost Savings:", f"[green]${session_dollars:.2f}[/green]")
        stats_table.add_row("  Efficiency:", f"[bold green]{session_efficiency:.1f}%[/bold green]")
        stats_table.add_row("  Operations:", f"{sum(self.metrics.commands_used.values())}")

        # Create the panel
        title = Text()
        title.append("💰 Token Savings Report", style="bold green")

        panel = Panel(
            stats_table,
            title=title,
            border_style="green",
            padding=(1, 2),
        )

        console.print()
        console.print(panel)
        console.print()

        # Reset task metrics after displaying
        self.metrics.reset_task_metrics()
        self._save_session()


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


def display_session_summary(show_task_summary: bool = True):
    """
    Display the session summary if tracking is enabled.

    Args:
        show_task_summary: If True, show per-task savings. If False, only session.
    """
    tracker = get_session_tracker()
    tracker.finalize()
    tracker.display_summary(show_task_summary=show_task_summary)


def display_task_completion():
    """
    Display task completion summary (both task and session savings).

    This is the default function to call after completing a task.
    Shows token savings for this task + cumulative session savings.
    """
    tracker = get_session_tracker()
    tracker.display_summary(show_task_summary=True)


def clear_session():
    """Clear the session file and reset all metrics."""
    tracker = get_session_tracker()
    if tracker.enabled:
        # Reset metrics
        tracker._reset_session()
        # Delete file
        if os.path.exists(tracker.session_file):
            try:
                os.remove(tracker.session_file)
            except Exception:
                pass
