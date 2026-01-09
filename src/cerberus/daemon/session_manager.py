"""
Phase 9.7: Session Management for Cerberus Daemon.

Manages agent sessions with state tracking and automatic cleanup.
"""

import time
import threading
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class Session:
    """
    Represents an agent session.

    Phase 9.7: Tracks session state and usage statistics.
    """
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    query_count: int = 0
    context: Dict[str, Any] = field(default_factory=dict)

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def increment_queries(self):
        """Increment query counter."""
        self.query_count += 1

    def age_seconds(self) -> float:
        """Get session age in seconds."""
        return time.time() - self.created_at

    def idle_seconds(self) -> float:
        """Get idle time in seconds."""
        return time.time() - self.last_activity

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "query_count": self.query_count,
            "age_seconds": self.age_seconds(),
            "idle_seconds": self.idle_seconds(),
        }


class SessionManager:
    """
    Manages agent sessions for the daemon.

    Phase 9.7: Session lifecycle and automatic cleanup.
    """

    def __init__(
        self,
        max_idle_seconds: float = 3600.0,  # 1 hour
        cleanup_interval: float = 300.0,   # 5 minutes
    ):
        """
        Initialize session manager.

        Args:
            max_idle_seconds: Maximum idle time before session expires
            cleanup_interval: How often to run cleanup (seconds)
        """
        self.sessions: Dict[str, Session] = {}
        self.max_idle_seconds = max_idle_seconds
        self.cleanup_interval = cleanup_interval
        self.lock = threading.Lock()

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
        )
        self.running = True
        self.cleanup_thread.start()

        logger.info(f"Phase 9.7: SessionManager initialized (max_idle={max_idle_seconds}s)")

    def create_session(self, session_id: str) -> Session:
        """
        Create a new session.

        Args:
            session_id: Unique session identifier

        Returns:
            Session object

        Phase 9.7: Session creation
        """
        with self.lock:
            if session_id in self.sessions:
                logger.debug(f"Session {session_id} already exists, reusing")
                return self.sessions[session_id]

            session = Session(session_id=session_id)
            self.sessions[session_id] = session
            logger.info(f"Phase 9.7: Created session {session_id}")
            return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get an existing session.

        Args:
            session_id: Session identifier

        Returns:
            Session object or None if not found

        Phase 9.7: Session retrieval
        """
        with self.lock:
            return self.sessions.get(session_id)

    def update_session(self, session_id: str):
        """
        Update session activity timestamp.

        Args:
            session_id: Session identifier

        Phase 9.7: Activity tracking
        """
        with self.lock:
            session = self.sessions.get(session_id)
            if session:
                session.update_activity()
                session.increment_queries()

    def close_session(self, session_id: str) -> bool:
        """
        Close and remove a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was closed

        Phase 9.7: Session cleanup
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Phase 9.7: Closed session {session_id}")
                return True
            return False

    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active sessions.

        Returns:
            Dictionary of session_id -> session data

        Phase 9.7: Session enumeration
        """
        with self.lock:
            return {
                sid: session.to_dict()
                for sid, session in self.sessions.items()
            }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get session statistics.

        Returns:
            Statistics dictionary

        Phase 9.7: Monitoring
        """
        with self.lock:
            total_queries = sum(s.query_count for s in self.sessions.values())
            return {
                "active_sessions": len(self.sessions),
                "total_queries": total_queries,
                "max_idle_seconds": self.max_idle_seconds,
            }

    def _cleanup_expired_sessions(self):
        """
        Remove expired sessions based on idle time.

        Phase 9.7: Automatic cleanup
        """
        with self.lock:
            now = time.time()
            expired = [
                sid for sid, session in self.sessions.items()
                if (now - session.last_activity) > self.max_idle_seconds
            ]

            for sid in expired:
                logger.info(f"Phase 9.7: Expiring idle session {sid}")
                del self.sessions[sid]

            if expired:
                logger.debug(f"Phase 9.7: Cleaned up {len(expired)} expired sessions")

    def _cleanup_loop(self):
        """
        Background cleanup loop.

        Phase 9.7: Periodic cleanup task
        """
        while self.running:
            time.sleep(self.cleanup_interval)
            try:
                self._cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"Phase 9.7: Cleanup error: {e}")

    def shutdown(self):
        """
        Shutdown session manager.

        Phase 9.7: Graceful shutdown
        """
        logger.info("Phase 9.7: Shutting down SessionManager")
        self.running = False
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=2.0)
