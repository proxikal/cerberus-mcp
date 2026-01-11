"""
Token savings tracking for Cerberus operations.
Tracks actual tokens used vs. baseline full-file reads.
Phase 16.2: Core infrastructure for verifiable context conservation.
"""
import time
from dataclasses import dataclass
from typing import Optional
from .session_manager import SessionManager
from .estimator import estimate_file_tokens


@dataclass
class TokenSavings:
    """Single operation savings record."""
    operation: str  # "get-symbol", "blueprint", etc.
    actual_tokens: int  # Tokens in actual output
    baseline_tokens: int  # Tokens if full file(s) read
    saved_tokens: int  # baseline - actual
    efficiency: float  # saved / baseline (0.0 - 1.0)
    timestamp: float


class TokenTracker:
    """Global token savings tracker."""

    def __init__(self):
        """Initialize token tracker."""
        self.session = SessionManager()
        self.current_operation = None
        self.current_task_tokens = 0
        self.current_task_baseline = 0

    def start_operation(self, operation_name: str) -> None:
        """
        Begin tracking an operation.

        Args:
            operation_name: Name of operation (e.g., "get-symbol")
        """
        self.current_operation = operation_name
        self.current_task_tokens = 0
        self.current_task_baseline = 0

    def record_output(self, output_text: str) -> None:
        """
        Record tokens in actual output.

        Args:
            output_text: Output text from command
        """
        # Rough estimation: 1 token ~= 4 characters
        self.current_task_tokens += len(output_text) // 4

    def record_baseline(self, file_path: str) -> None:
        """
        Record what tokens would be used for full file read.

        Args:
            file_path: Path to file that would be read
        """
        baseline = estimate_file_tokens(file_path)
        self.current_task_baseline += baseline

    def record_baseline_manual(self, token_count: int) -> None:
        """
        Manually specify baseline tokens.

        Args:
            token_count: Number of baseline tokens
        """
        self.current_task_baseline += token_count

    def finalize_operation(self) -> TokenSavings:
        """
        End operation and calculate savings.

        Returns:
            TokenSavings object with metrics
        """
        # Calculate saved tokens (never negative - 0 means no savings, not worse than baseline)
        saved = max(0, self.current_task_baseline - self.current_task_tokens)
        # Efficiency is 0.0-1.0 range (0% to 100% savings)
        efficiency = saved / self.current_task_baseline if self.current_task_baseline > 0 else 0.0

        savings = TokenSavings(
            operation=self.current_operation,
            actual_tokens=self.current_task_tokens,
            baseline_tokens=self.current_task_baseline,
            saved_tokens=saved,
            efficiency=efficiency,
            timestamp=time.time()
        )

        # Update session totals
        self.session.add_task_savings(savings)

        return savings

    def get_display_footer(self, savings: TokenSavings) -> str:
        """
        Generate footer for command output.

        Args:
            savings: TokenSavings from finalize_operation()

        Returns:
            Formatted footer string
        """
        # Task-level metrics
        task_saved_usd = savings.saved_tokens * 0.000003  # $3/1M tokens
        task_footer = (
            f"[Task] Saved: {savings.saved_tokens:,} tokens "
            f"(~${task_saved_usd:.4f}) | Efficiency: {savings.efficiency*100:.1f}%"
        )

        # Session-level metrics
        session_total = self.session.get_total_saved()
        session_usd = session_total * 0.000003
        session_efficiency = self.session.get_average_efficiency()
        session_footer = (
            f"[Session] Saved: {session_total:,} tokens "
            f"(~${session_usd:.2f}) | Efficiency: {session_efficiency*100:.1f}%"
        )

        return f"\n{task_footer}\n{session_footer}"


# Global singleton
_tracker = None


def get_tracker() -> TokenTracker:
    """
    Get global token tracker instance.

    Returns:
        TokenTracker singleton
    """
    global _tracker
    if _tracker is None:
        _tracker = TokenTracker()
    return _tracker
