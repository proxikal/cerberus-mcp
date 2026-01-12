"""
Session persistence for token savings tracking.
Manages session file in .cerberus/ directory.
Phase 16.2: Session state persistence for token tracking.
"""
import json
import os
import time
from pathlib import Path
from typing import Dict, Any

from cerberus.paths import get_paths


SESSION_TIMEOUT = 3600  # 1 hour (configurable via env)


class SessionManager:
    """Manages persistent session state for token tracking."""

    def __init__(self):
        """Initialize session manager."""
        paths = get_paths()
        paths.ensure_dirs()  # Ensure .cerberus directory exists
        self.session_file = paths.get_session_file()
        self.data = self._load_or_create()

    def _load_or_create(self) -> Dict[str, Any]:
        """
        Load existing session or create new one.

        Returns:
            Session data dictionary
        """
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)

                # Check if session timed out
                timeout = int(os.getenv('CERBERUS_SESSION_TIMEOUT', SESSION_TIMEOUT))
                if time.time() - data.get('last_activity', 0) > timeout:
                    return self._create_new_session()

                return data
            except (json.JSONDecodeError, IOError):
                return self._create_new_session()
        else:
            return self._create_new_session()

    def _create_new_session(self) -> Dict[str, Any]:
        """
        Create new session data structure.

        Returns:
            New session dictionary
        """
        return {
            'started_at': time.time(),
            'last_activity': time.time(),
            'total_saved_tokens': 0,
            'total_baseline_tokens': 0,
            'operation_count': 0,
            'operations': []
        }

    def add_task_savings(self, savings) -> None:
        """
        Add task savings to session totals.

        Args:
            savings: TokenSavings object
        """
        self.data['total_saved_tokens'] += savings.saved_tokens
        self.data['total_baseline_tokens'] += savings.baseline_tokens
        self.data['operation_count'] += 1
        self.data['last_activity'] = time.time()

        # Store last 100 operations
        self.data['operations'].append({
            'operation': savings.operation,
            'saved': savings.saved_tokens,
            'baseline': savings.baseline_tokens,
            'efficiency': savings.efficiency,
            'timestamp': savings.timestamp
        })
        if len(self.data['operations']) > 100:
            self.data['operations'] = self.data['operations'][-100:]

        self._persist()

    def get_total_saved(self) -> int:
        """
        Get total tokens saved in session.

        Returns:
            Total saved tokens
        """
        return self.data['total_saved_tokens']

    def get_average_efficiency(self) -> float:
        """
        Get average efficiency across session.

        Returns:
            Average efficiency (0.0 - 1.0)
        """
        baseline = self.data['total_baseline_tokens']
        if baseline == 0:
            return 0.0
        saved = self.data['total_saved_tokens']
        return saved / baseline

    def _persist(self) -> None:
        """Write session data to disk."""
        try:
            with open(self.session_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError:
            # Don't crash on persistence failure
            pass
