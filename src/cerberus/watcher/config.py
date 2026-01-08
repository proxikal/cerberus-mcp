"""
Configuration for the background watcher daemon.
"""

import tempfile
from pathlib import Path

WATCHER_CONFIG = {
    "auto_start": True,  # Auto-start watcher on CLI commands
    "debounce_delay": 2.0,  # Seconds to wait after last change before updating
    "event_batch_size": 10,  # Process events in batches
    "max_events_per_update": 100,  # Limit events per update cycle
    "shutdown_idle_timeout": 0,  # Shutdown after N seconds of inactivity (0 = never)
    "log_to_file": True,  # Log daemon output to file
}

MONITORING_CONFIG = {
    "watch_patterns": ["**/*.py", "**/*.ts", "**/*.js", "**/*.go"],
    "ignore_patterns": [
        "**/__pycache__/**",
        "**/node_modules/**",
        "**/.venv/**",
        "**/venv/**",
        "**/env/**",
        "**/build/**",
        "**/dist/**",
        "**/.git/**",
        "**/.cerberus/**",
    ],
    "recursive": True,
}

IPC_CONFIG = {
    "socket_dir": Path(tempfile.gettempdir()) / "cerberus",
    "pid_file_pattern": "cerberus_watcher_{project_hash}.pid",
    "socket_file_pattern": "cerberus_watcher_{project_hash}.sock",
    "log_file_pattern": ".cerberus/watcher.log",  # Relative to project root
}


def get_project_hash(project_path: Path) -> str:
    """
    Generate a hash for a project path to use in filenames.

    Args:
        project_path: Path to project

    Returns:
        Hash string (first 8 chars of SHA256)
    """
    import hashlib
    path_str = str(project_path.resolve())
    return hashlib.sha256(path_str.encode()).hexdigest()[:8]


def get_pid_file_path(project_path: Path) -> Path:
    """Get PID file path for a project."""
    project_hash = get_project_hash(project_path)
    filename = IPC_CONFIG["pid_file_pattern"].format(project_hash=project_hash)
    IPC_CONFIG["socket_dir"].mkdir(parents=True, exist_ok=True)
    return IPC_CONFIG["socket_dir"] / filename


def get_socket_file_path(project_path: Path) -> Path:
    """Get socket file path for a project."""
    project_hash = get_project_hash(project_path)
    filename = IPC_CONFIG["socket_file_pattern"].format(project_hash=project_hash)
    IPC_CONFIG["socket_dir"].mkdir(parents=True, exist_ok=True)
    return IPC_CONFIG["socket_dir"] / filename


def get_log_file_path(project_path: Path) -> Path:
    """Get log file path for a project."""
    log_dir = project_path / ".cerberus"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "watcher.log"
