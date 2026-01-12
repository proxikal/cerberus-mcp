"""
Daemon module for Cerberus Cognitive Cortex.

Phase 9: Persistent background server for zero-latency AI symbiosis.

This module provides:
- Daemon lifecycle management (start, stop, status)
- Session management for stateful agent interactions
- JSON-RPC protocol for structured agent communication
- Real-time file watching and proactive notifications
- Tiered memory management (skeleton index + hot cache + cold storage)

Public API exported from facade.py following self-similar architecture.
"""

from .facade import (
    start_daemon,
    stop_daemon,
    daemon_status,
    health_check,
    is_daemon_running,
    send_rpc_request,
    get_socket_path,
    get_daemon_pid,
)

# Phase 9.5: Thin Client Routing
from .thin_client import (
    is_daemon_available,
    auto_route,
    route_get_symbol,
    route_search,
    route_read_file,
    get_routing_stats,
)

__all__ = [
    "start_daemon",
    "stop_daemon",
    "daemon_status",
    "health_check",
    "is_daemon_running",
    "send_rpc_request",
    "get_socket_path",
    "get_daemon_pid",
    # Phase 9.5
    "is_daemon_available",
    "auto_route",
    "route_get_symbol",
    "route_search",
    "route_read_file",
    "get_routing_stats",
]
