"""
Configuration for the Cerberus Daemon (Cognitive Cortex).

Phase 9: Daemon-mode configuration for persistent server operation.
"""

from pathlib import Path
import platform
import tempfile

# Platform detection for socket strategy
SYSTEM_PLATFORM = platform.system()  # "Darwin", "Linux", "Windows"

# === Server Configuration ===
DAEMON_CONFIG = {
    "host": "127.0.0.1",  # Localhost only (security by default)
    "port": 9876,  # Default port for HTTP mode
    "socket_path": None,  # Will be set dynamically based on platform
    "mode": "unix_socket",  # "unix_socket" (Mac/Linux), "http" (fallback/Windows)
    "max_connections": 10,  # Max concurrent agent connections
    "startup_timeout": 30.0,  # Seconds to wait for daemon to become ready
    "shutdown_timeout": 5.0,  # Graceful shutdown timeout
    "health_check_interval": 1.0,  # Seconds between health checks
}

# === Unix Socket Configuration (Mac/Linux) ===
UNIX_SOCKET_CONFIG = {
    "socket_dir": Path(tempfile.gettempdir()) / "cerberus",
    "socket_name": "cerberus.sock",
    "permissions": 0o700,  # Owner read/write/execute only
}

# === PID and Runtime File Paths ===
def get_pid_file_path(project_path: Path = None) -> Path:
    """
    Get the PID file path for the daemon.

    Args:
        project_path: Optional project path (for multi-project support)

    Returns:
        Path to PID file
    """
    runtime_dir = UNIX_SOCKET_CONFIG["socket_dir"]
    runtime_dir.mkdir(parents=True, exist_ok=True)

    if project_path:
        # Hash project path for unique PID file
        project_hash = abs(hash(str(project_path.resolve())))
        return runtime_dir / f"cerberus_{project_hash}.pid"
    else:
        return runtime_dir / "cerberus.pid"


def get_log_file_path(project_path: Path = None) -> Path:
    """
    Get the log file path for the daemon.

    Args:
        project_path: Optional project path

    Returns:
        Path to log file
    """
    runtime_dir = UNIX_SOCKET_CONFIG["socket_dir"]
    runtime_dir.mkdir(parents=True, exist_ok=True)

    if project_path:
        project_hash = abs(hash(str(project_path.resolve())))
        return runtime_dir / f"cerberus_{project_hash}.log"
    else:
        return runtime_dir / "cerberus.log"

# Dynamically set socket path
if SYSTEM_PLATFORM in ("Darwin", "Linux"):
    DAEMON_CONFIG["socket_path"] = (
        UNIX_SOCKET_CONFIG["socket_dir"] / UNIX_SOCKET_CONFIG["socket_name"]
    )
elif SYSTEM_PLATFORM == "Windows":
    # Windows: Use Named Pipes or fallback to HTTP
    DAEMON_CONFIG["mode"] = "http"
    DAEMON_CONFIG["socket_path"] = r"\\.\pipe\cerberus"  # Named Pipe syntax

# === Session Management ===
SESSION_CONFIG = {
    "default_timeout": 3600.0,  # 1 hour idle timeout
    "max_sessions": 5,  # Support multi-agent swarms
    "seen_set_max_size": 10000,  # Max symbols tracked per session
    "enable_deduplication": True,  # Track "seen" symbols to reduce context bloat
}

# === Memory Tier Configuration (Phase 9.8) ===
MEMORY_TIER_CONFIG = {
    "skeleton_index_enabled": True,  # Tier 1: Always in RAM
    "hot_cache_enabled": True,  # Tier 2: LRU cache
    "hot_cache_max_size_mb": 256,  # Max RAM for hot working set
    "hot_cache_max_files": 100,  # Max files in hot cache
    "pin_recent_edits": True,  # Pin recently modified files in cache
    "pin_duration_seconds": 3600,  # 1 hour pin duration
    "prefetch_imports": True,  # Predictive prefetching
}

# === File Watcher Configuration (Phase 9.6) ===
WATCHER_CONFIG = {
    "enabled": True,  # Auto-start watcher with daemon
    "debounce_seconds": 0.5,  # Debounce rapid file changes
    "batch_updates": True,  # Batch multiple changes into single update
    "watch_patterns": ["*.py", "*.js", "*.ts", "*.go", "*.rs"],
    "ignore_patterns": [
        "*.pyc",
        "__pycache__",
        ".git",
        "node_modules",
        ".venv",
        "venv",
    ],
}

# === Proactive Notifications (Phase 9.9) ===
NOTIFICATION_CONFIG = {
    "enabled": True,  # Push notifications to agents
    "events": [
        "file_modified",
        "file_created",
        "file_deleted",
        "reference_break",  # Symbol reference invalidated
        "test_failure",  # Shadow workspace test failure
    ],
    "debounce_seconds": 1.0,  # Batch rapid events
    "max_queue_size": 100,  # Max pending notifications per session
}

# === System Monitoring (Phase 9.10) ===
MONITORING_CONFIG = {
    "enabled": True,  # Monitor agent process resources
    "check_interval_seconds": 5.0,  # Check every 5 seconds
    "memory_threshold_mb": 2048,  # Warn if agent > 2GB
    "cpu_threshold_percent": 80,  # Warn if agent CPU > 80%
    "warn_on_threshold": True,  # Send warning to agent
}

# === Shadow Workspace (Phase 9.11) ===
SHADOW_CONFIG = {
    "enabled": False,  # Disabled by default (Phase 9.11 feature)
    "shadow_dir": Path(tempfile.gettempdir()) / "cerberus_shadow",
    "auto_cleanup": True,  # Clean up after tests
    "max_shadow_workspaces": 3,  # Max concurrent shadow environments
}

# === Security Configuration (Phase 9.12) ===
SECURITY_CONFIG = {
    "read_only_default": True,  # Require explicit --allow-write flag
    "require_auth": False,  # Future: cryptographic session tokens
    "localhost_only": True,  # Never bind to 0.0.0.0
    "log_all_requests": True,  # Audit trail
    "max_request_size_mb": 10,  # Prevent DoS
}

# === RPC Protocol Configuration (Phase 9.3) ===
RPC_CONFIG = {
    "protocol": "json-rpc-2.0",
    "response_format": "json",  # Always JSON for agents
    "pretty_print_human": True,  # Pretty-print for human CLI users
    "include_metadata": True,  # Include timing/trace metadata
    "compression": "none",  # Future: gzip for large responses
}

# === Performance Targets (Success Metrics) ===
PERFORMANCE_TARGETS = {
    "symbol_lookup_ms": 50,  # Target: <50ms
    "file_read_ms": 100,  # Target: <100ms
    "search_query_ms": 200,  # Target: <200ms
    "cold_start_ms": 3000,  # One-time startup tax
    "memory_baseline_mb": 100,  # Daemon baseline memory
}
