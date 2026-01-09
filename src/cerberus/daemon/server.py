"""
Cerberus Daemon Server Implementation.

Phase 9.2: Lightweight HTTP server with health endpoint.
Phase 9.3: JSON-RPC 2.0 protocol support.

Uses Python's built-in http.server for zero dependencies.
"""

import os
import sys
import json
import time
import signal
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Optional
from loguru import logger

from ..index.index_loader import load_index
from .config import DAEMON_CONFIG, get_pid_file_path, get_log_file_path
from .pid_manager import write_pid_file, remove_pid_file
from .rpc_protocol import (
    parse_rpc_request,
    is_batch_request,
    parse_batch_request,
    create_error_response,
    RPCErrorCode,
    JSONRPCRequest,
    JSONRPCResponse,
)
from .rpc_methods import RPCMethodRegistry


class CerberusDaemonHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for the Cerberus Daemon.

    Phase 9.2: Implements basic health check endpoint.
    Phase 9.3: Implements JSON-RPC 2.0 protocol.
    """

    # Class-level state
    index_path: Optional[Path] = None
    index_store = None
    start_time: float = time.time()
    rpc_registry: Optional[RPCMethodRegistry] = None

    def log_message(self, format, *args):
        """Override to use loguru instead of stderr."""
        logger.debug(f"{self.address_string()} - {format % args}")

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/status":
            self._handle_status()
        else:
            self._send_response(404, {"error": "Not found"})

    def do_POST(self):
        """Handle POST requests (future: JSON-RPC)."""
        if self.path == "/rpc":
            self._handle_rpc()
        else:
            self._send_response(404, {"error": "Not found"})

    def _handle_health(self):
        """
        Health check endpoint.

        Returns:
            200 OK with health status
        """
        try:
            # Check if index is accessible
            index_accessible = self.index_store is not None

            health_data = {
                "healthy": True,
                "status": "running",
                "index_loaded": index_accessible,
                "uptime_seconds": time.time() - self.start_time,
                "timestamp": time.time(),
            }

            self._send_response(200, health_data)

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self._send_response(500, {"healthy": False, "error": str(e)})

    def _handle_status(self):
        """
        Status endpoint with detailed metrics.

        Returns:
            200 OK with daemon status
        """
        try:
            # Phase 9.6: Get watcher stats if available
            watcher_stats = None
            if self.watcher:
                try:
                    watcher_stats = self.watcher.get_stats()
                except Exception:
                    pass

            # Phase 9.7: Get session stats if available
            session_stats = None
            active_sessions = 0
            if self.session_manager:
                try:
                    session_stats = self.session_manager.get_stats()
                    active_sessions = session_stats.get("active_sessions", 0)
                except Exception:
                    pass

            status_data = {
                "running": True,
                "pid": os.getpid(),
                "uptime_seconds": time.time() - self.start_time,
                "index_loaded": self.index_store is not None,
                "index_path": str(self.index_path) if self.index_path else None,
                "active_sessions": active_sessions,  # Phase 9.7
                "memory_mb": 0,  # TODO Phase 9.10
                "watcher": watcher_stats,  # Phase 9.6
                "sessions": session_stats,  # Phase 9.7
            }

            self._send_response(200, status_data)

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            self._send_response(500, {"error": str(e)})

    def _handle_rpc(self):
        """
        JSON-RPC 2.0 endpoint.

        Handles single and batch requests.

        Phase 9.3: Implementation complete.
        """
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                response = create_error_response(
                    code=RPCErrorCode.INVALID_REQUEST,
                    message="Empty request body",
                )
                self._send_json_rpc_response(response)
                return

            body = self.rfile.read(content_length)

            # Parse JSON
            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                response = create_error_response(
                    code=RPCErrorCode.PARSE_ERROR,
                    message="Parse error",
                    data=str(e),
                )
                self._send_json_rpc_response(response)
                return

            # Handle batch vs single request
            if is_batch_request(data):
                responses = self._handle_batch_rpc(data)
                self._send_json_rpc_responses(responses)
            else:
                response = self._handle_single_rpc(data)
                self._send_json_rpc_response(response)

        except Exception as e:
            logger.error(f"RPC handler error: {e}")
            response = create_error_response(
                code=RPCErrorCode.INTERNAL_ERROR,
                message="Internal error",
                data=str(e),
            )
            self._send_json_rpc_response(response)

    def _handle_single_rpc(self, data: dict) -> JSONRPCResponse:
        """
        Handle single JSON-RPC request.

        Args:
            data: Request data

        Returns:
            JSONRPCResponse
        """
        # Parse request
        request = parse_rpc_request(data)
        if isinstance(request, JSONRPCResponse):
            # Parse error
            return request

        # Ensure RPC registry is initialized
        if self.rpc_registry is None:
            return create_error_response(
                code=RPCErrorCode.INTERNAL_ERROR,
                message="RPC registry not initialized",
                request_id=request.id,
            )

        # Invoke method
        return self.rpc_registry.invoke(
            method=request.method,
            params=request.params,
            request_id=request.id,
        )

    def _handle_batch_rpc(self, data: list) -> list:
        """
        Handle batch JSON-RPC request.

        Args:
            data: List of request data

        Returns:
            List of JSONRPCResponse
        """
        requests = parse_batch_request(data)
        responses = []

        for request in requests:
            if isinstance(request, JSONRPCResponse):
                # Parse error
                responses.append(request)
            else:
                # Valid request
                response = self._handle_single_rpc(request.model_dump())
                responses.append(response)

        return responses

    def _send_json_rpc_response(self, response: JSONRPCResponse):
        """
        Send single JSON-RPC response.

        Args:
            response: JSONRPCResponse object
        """
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        response_json = response.model_dump(exclude_none=True)
        response_bytes = json.dumps(response_json, indent=2).encode("utf-8")
        self.wfile.write(response_bytes)

    def _send_json_rpc_responses(self, responses: list):
        """
        Send batch JSON-RPC responses.

        Args:
            responses: List of JSONRPCResponse objects
        """
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        response_list = [r.model_dump(exclude_none=True) for r in responses]
        response_bytes = json.dumps(response_list, indent=2).encode("utf-8")
        self.wfile.write(response_bytes)

    def _send_response(self, status_code: int, data: dict):
        """
        Send JSON response.

        Args:
            status_code: HTTP status code
            data: Response data (will be JSON-encoded)
        """
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.wfile.write(response_bytes)


class CerberusDaemonServer:
    """
    Cerberus Daemon Server.

    Phase 9.2: Persistent background server for zero-latency queries.
    """

    def __init__(
        self,
        index_path: Path,
        host: str = "127.0.0.1",
        port: int = 9876,
        project_path: Optional[Path] = None,
        enable_watcher: bool = True,
    ):
        """
        Initialize daemon server.

        Args:
            index_path: Path to SQLite index
            host: Host to bind to (default: localhost)
            port: Port to bind to
            project_path: Optional project path (for multi-project support)
            enable_watcher: Enable filesystem watcher (Phase 9.6)
        """
        self.index_path = index_path.resolve()
        self.host = host
        self.port = port
        self.project_path = project_path
        self.enable_watcher = enable_watcher
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.watcher: Optional[Any] = None  # Phase 9.6: Filesystem watcher
        self.session_manager: Optional[Any] = None  # Phase 9.7: Session management

        # PID file management
        self.pid_file = get_pid_file_path(project_path)
        self.log_file = get_log_file_path(project_path)

        # Set class-level state for handlers
        CerberusDaemonHandler.index_path = self.index_path
        CerberusDaemonHandler.start_time = time.time()
        CerberusDaemonHandler.watcher = None  # Phase 9.6: Will be set when watcher starts
        CerberusDaemonHandler.session_manager = None  # Phase 9.7: Will be set when sessions enabled

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
        signal.signal(signal.SIGINT, self._handle_shutdown_signal)

    def _load_index(self) -> bool:
        """
        Load the index into memory and initialize RPC registry.

        Returns:
            True if loaded successfully
        """
        try:
            logger.info(f"Loading index from {self.index_path}")
            index_store = load_index(self.index_path)

            # Set class-level state for handlers
            CerberusDaemonHandler.index_store = index_store

            # Initialize RPC method registry (Phase 9.3)
            logger.info("Initializing RPC method registry")
            rpc_registry = RPCMethodRegistry(self.index_path)
            CerberusDaemonHandler.rpc_registry = rpc_registry

            logger.info("Index and RPC registry loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False

    def start(self, background: bool = True) -> int:
        """
        Start the daemon server.

        Args:
            background: Run as background daemon (default: True)

        Returns:
            PID of the daemon process

        Raises:
            RuntimeError: If server fails to start
        """
        # Load index into memory
        if not self._load_index():
            raise RuntimeError("Failed to load index")

        # Phase 9.7: Initialize session manager
        try:
            from .session_manager import SessionManager
            self.session_manager = SessionManager(
                max_idle_seconds=3600.0,  # 1 hour idle timeout
                cleanup_interval=300.0,   # Cleanup every 5 minutes
            )
            CerberusDaemonHandler.session_manager = self.session_manager
            logger.info("Phase 9.7: Session manager initialized")
        except Exception as e:
            logger.warning(f"Phase 9.7: Session manager initialization failed: {e}")
            self.session_manager = None

        if background:
            # Fork to background
            pid = os.fork()
            if pid > 0:
                # Parent process: write PID and exit
                write_pid_file(self.pid_file, pid)
                logger.info(f"Daemon started in background (PID: {pid})")
                return pid

            # Child process: continue as daemon
            os.setsid()  # Detach from terminal

        # Write PID file (either child process or foreground)
        write_pid_file(self.pid_file, os.getpid())

        # Redirect stdout/stderr to log file if in background
        if background:
            log_fd = os.open(str(self.log_file), os.O_WRONLY | os.O_CREAT | os.O_APPEND)
            os.dup2(log_fd, sys.stdout.fileno())
            os.dup2(log_fd, sys.stderr.fileno())
            os.close(log_fd)

        # Phase 9.6: Start filesystem watcher if enabled
        if self.enable_watcher and self.project_path:
            try:
                from .watcher_integration import create_daemon_watcher
                self.watcher = create_daemon_watcher(
                    project_path=self.project_path,
                    index_path=self.index_path,
                    auto_start=True,
                )
                if self.watcher:
                    CerberusDaemonHandler.watcher = self.watcher  # Make accessible to handlers
                    logger.info(f"Phase 9.6: Filesystem watcher enabled")
                else:
                    logger.warning(f"Phase 9.6: Failed to start watcher, continuing without it")
            except Exception as e:
                logger.warning(f"Phase 9.6: Watcher initialization failed: {e}, continuing without watcher")
                self.watcher = None

        # Start HTTP server
        try:
            self.server = HTTPServer((self.host, self.port), CerberusDaemonHandler)
            logger.info(f"Daemon listening on {self.host}:{self.port}")

            # Serve forever
            self.server.serve_forever()

        except Exception as e:
            logger.error(f"Server failed: {e}")
            # Phase 9.6: Stop watcher on error
            if self.watcher:
                try:
                    self.watcher.stop()
                except:
                    pass
            remove_pid_file(self.pid_file)
            raise RuntimeError(f"Failed to start server: {e}")

        return os.getpid()

    def stop(self, timeout: float = 5.0) -> bool:
        """
        Stop the daemon server.

        Args:
            timeout: Graceful shutdown timeout

        Returns:
            True if stopped successfully
        """
        logger.info("Stopping daemon server")

        # Phase 9.7: Shutdown session manager
        if self.session_manager:
            try:
                self.session_manager.shutdown()
                logger.info("Phase 9.7: Session manager stopped")
            except Exception as e:
                logger.warning(f"Phase 9.7: Error stopping session manager: {e}")

        # Phase 9.6: Stop watcher
        if self.watcher:
            try:
                self.watcher.stop(timeout=timeout)
                logger.info("Phase 9.6: Watcher stopped")
            except Exception as e:
                logger.warning(f"Phase 9.6: Error stopping watcher: {e}")

        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Server shut down")

        # Clean up PID file
        remove_pid_file(self.pid_file)

        return True

    def _handle_shutdown_signal(self, signum, frame):
        """Handle shutdown signals (SIGTERM, SIGINT)."""
        logger.info(f"Received signal {signum}, shutting down")
        self.stop()
        sys.exit(0)


def run_daemon_server(
    index_path: Path,
    host: str = None,
    port: int = None,
    background: bool = True,
    project_path: Optional[Path] = None,
) -> int:
    """
    Run the Cerberus Daemon server.

    Args:
        index_path: Path to SQLite index
        host: Host to bind to (default: from config)
        port: Port to bind to (default: from config)
        background: Run as background daemon
        project_path: Optional project path

    Returns:
        PID of the daemon process
    """
    host = host or DAEMON_CONFIG["host"]
    port = port or DAEMON_CONFIG["port"]

    server = CerberusDaemonServer(
        index_path=index_path,
        host=host,
        port=port,
        project_path=project_path,
    )

    return server.start(background=background)
