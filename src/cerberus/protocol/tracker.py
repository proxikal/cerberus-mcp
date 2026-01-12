"""
Protocol State Tracker (Phase 19.7)

Tracks cerberus command usage and protocol refresh state.
Determines when to suggest protocol refresh to AI agents.

Session-based tracking:
- Commands since last refresh
- Time since last refresh
- Total cerberus commands in session
"""

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from cerberus.logging_config import logger


# Thresholds for suggesting refresh
COMMAND_THRESHOLD = 20  # Suggest after N cerberus commands without refresh
TIME_THRESHOLD_SECONDS = 600  # Suggest after N seconds without refresh (10 min)
STALE_THRESHOLD_SECONDS = 1800  # Consider protocol stale after 30 min


@dataclass
class ProtocolState:
    """Current protocol tracking state."""

    session_start: float = field(default_factory=time.time)
    last_refresh: Optional[float] = None
    commands_since_refresh: int = 0
    total_commands: int = 0
    refresh_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ProtocolState":
        return cls(**data)


class ProtocolTracker:
    """
    Tracks protocol state and determines when refresh is needed.

    State persists in session file for cross-command tracking.
    """

    def __init__(self, session_file: Optional[Path] = None):
        """
        Initialize tracker.

        Args:
            session_file: Path to session state file (default: .cerberus_protocol.json)
        """
        if session_file is None:
            session_file = Path.cwd() / ".cerberus_protocol.json"
        self.session_file = session_file
        self._state: Optional[ProtocolState] = None

    @property
    def state(self) -> ProtocolState:
        """Get current state, loading from file if needed."""
        if self._state is None:
            self._state = self._load_state()
        return self._state

    def _load_state(self) -> ProtocolState:
        """Load state from file or create new."""
        if self.session_file.exists():
            try:
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                state = ProtocolState.from_dict(data)

                # Check if session is stale (>1 hour inactive)
                if time.time() - state.session_start > 3600:
                    logger.debug("Protocol session expired, starting fresh")
                    return ProtocolState()

                return state
            except Exception as e:
                logger.debug(f"Could not load protocol state: {e}")

        return ProtocolState()

    def _save_state(self) -> None:
        """Persist state to file."""
        try:
            with open(self.session_file, "w") as f:
                json.dump(self.state.to_dict(), f)
        except Exception as e:
            logger.debug(f"Could not save protocol state: {e}")

    def record_command(self, command_name: str) -> None:
        """
        Record a cerberus command execution.

        Args:
            command_name: Name of the command (e.g., "blueprint", "search")
        """
        self.state.commands_since_refresh += 1
        self.state.total_commands += 1
        self._save_state()
        logger.debug(
            f"Protocol tracker: {command_name} "
            f"(cmds since refresh: {self.state.commands_since_refresh})"
        )

    def record_refresh(self) -> None:
        """Record a protocol refresh."""
        self.state.last_refresh = time.time()
        self.state.commands_since_refresh = 0
        self.state.refresh_count += 1
        self._save_state()
        logger.debug(f"Protocol refreshed (total refreshes: {self.state.refresh_count})")

    def should_suggest_refresh(self) -> bool:
        """
        Check if protocol refresh should be suggested.

        Returns True if:
        - Never refreshed AND (commands > threshold OR time > threshold)
        - OR last refresh was > threshold ago
        """
        state = self.state

        # If never refreshed
        if state.last_refresh is None:
            # Check command count
            if state.commands_since_refresh >= COMMAND_THRESHOLD:
                return True

            # Check time since session start
            time_since_start = time.time() - state.session_start
            if time_since_start >= TIME_THRESHOLD_SECONDS:
                return True

            return False

        # If previously refreshed, check staleness
        time_since_refresh = time.time() - state.last_refresh

        # Stale if too much time has passed
        if time_since_refresh >= STALE_THRESHOLD_SECONDS:
            return True

        # Or if too many commands since last refresh
        if state.commands_since_refresh >= COMMAND_THRESHOLD:
            return True

        return False

    def get_refresh_reason(self) -> Optional[str]:
        """Get human-readable reason for suggesting refresh."""
        if not self.should_suggest_refresh():
            return None

        state = self.state

        if state.last_refresh is None:
            if state.commands_since_refresh >= COMMAND_THRESHOLD:
                return f"{state.commands_since_refresh} commands without protocol refresh"
            else:
                minutes = int((time.time() - state.session_start) / 60)
                return f"Session active {minutes}+ minutes without protocol refresh"

        time_since = time.time() - state.last_refresh
        if time_since >= STALE_THRESHOLD_SECONDS:
            minutes = int(time_since / 60)
            return f"Protocol last refreshed {minutes} minutes ago"

        return f"{state.commands_since_refresh} commands since last refresh"

    def get_status(self) -> dict:
        """Get current protocol status for display."""
        state = self.state
        now = time.time()

        return {
            "session_age_minutes": int((now - state.session_start) / 60),
            "last_refresh_minutes": (
                int((now - state.last_refresh) / 60)
                if state.last_refresh
                else None
            ),
            "commands_since_refresh": state.commands_since_refresh,
            "total_commands": state.total_commands,
            "refresh_count": state.refresh_count,
            "needs_refresh": self.should_suggest_refresh(),
            "refresh_reason": self.get_refresh_reason(),
        }

    def reset(self) -> None:
        """Reset protocol state (new session)."""
        self._state = ProtocolState()
        self._save_state()


# Singleton instance
_tracker: Optional[ProtocolTracker] = None


def get_protocol_tracker() -> ProtocolTracker:
    """Get the global protocol tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = ProtocolTracker()
    return _tracker


def reset_protocol_tracker() -> None:
    """Reset the global protocol tracker."""
    global _tracker
    if _tracker is not None:
        _tracker.reset()
    _tracker = None
