"""
Thin Client for Cerberus Daemon (Phase 9.5).

Provides automatic routing of commands through the daemon when available,
with transparent fallback to direct execution.

Mission: Eliminate the 3-second Python startup tax by routing to a hot daemon.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Callable, TypeVar
import requests
from loguru import logger

from .config import DAEMON_CONFIG
from .pid_manager import is_daemon_running_pid, get_daemon_pid_from_file
from .facade import get_pid_file_path

T = TypeVar('T')


def is_daemon_available(timeout_ms: int = 50) -> bool:
    """
    Fast check if daemon is available.

    Args:
        timeout_ms: Timeout in milliseconds (default: 50ms)

    Returns:
        True if daemon is running and responsive

    Phase 9.5: Fast availability check (<50ms)
    """
    # Quick PID check first (no network)
    pid_file = get_pid_file_path()
    if not is_daemon_running_pid(pid_file):
        return False

    # Verify daemon is actually responsive
    try:
        url = f"http://{DAEMON_CONFIG['host']}:{DAEMON_CONFIG['port']}/health"
        response = requests.get(url, timeout=timeout_ms / 1000.0)
        return response.status_code == 200 and response.json().get("healthy", False)
    except (requests.RequestException, Exception):
        return False


def send_rpc_call(
    method: str,
    params: Optional[Dict[str, Any]] = None,
    timeout_ms: int = 5000,
) -> Dict[str, Any]:
    """
    Send JSON-RPC call to daemon.

    Args:
        method: RPC method name
        params: Method parameters
        timeout_ms: Request timeout in milliseconds

    Returns:
        RPC response (result or error)

    Raises:
        Exception: If RPC call fails or daemon is unavailable

    Phase 9.5: Direct RPC communication
    """
    url = f"http://{DAEMON_CONFIG['host']}:{DAEMON_CONFIG['port']}/rpc"

    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1,
    }

    try:
        response = requests.post(url, json=payload, timeout=timeout_ms / 1000.0)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            error = data["error"]
            raise Exception(f"RPC error: {error.get('message', 'Unknown error')}")

        return data.get("result", {})

    except requests.RequestException as e:
        raise Exception(f"Failed to connect to daemon: {e}")


def auto_route(
    method: str,
    params: Optional[Dict[str, Any]],
    fallback_fn: Callable[[], T],
    enable_routing: bool = True,
) -> T:
    """
    Automatically route command to daemon or execute fallback.

    Args:
        method: RPC method name
        params: Method parameters
        fallback_fn: Function to call if daemon unavailable
        enable_routing: Set to False to force fallback (testing/debugging)

    Returns:
        Result from daemon or fallback function

    Phase 9.5: Smart routing with transparent fallback

    Usage:
        result = auto_route(
            method="get_symbol",
            params={"name": "MyClass"},
            fallback_fn=lambda: direct_get_symbol("MyClass"),
        )
    """
    # Allow disabling routing for testing
    if not enable_routing:
        logger.debug(f"Routing disabled, executing fallback for {method}")
        return fallback_fn()

    # Check daemon availability
    if not is_daemon_available():
        logger.debug(f"Daemon unavailable, executing fallback for {method}")
        return fallback_fn()

    # Route through daemon
    try:
        logger.debug(f"Routing {method} to daemon")
        result = send_rpc_call(method, params)
        return result

    except Exception as e:
        logger.warning(f"Daemon routing failed for {method}: {e}, falling back to direct execution")
        return fallback_fn()


def route_get_symbol(
    name: str,
    index_path: Path,
    file_filter: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Route get_symbol command to daemon or execute directly.

    Args:
        name: Symbol name
        index_path: Path to index
        file_filter: Optional file filter

    Returns:
        Symbol data or None

    Phase 9.5: Specialized routing for get_symbol
    """
    from ..index import load_index
    from ..retrieval.utils import find_symbol

    def fallback():
        scan_result = load_index(index_path)
        results = find_symbol(name=name, scan_result=scan_result)

        if file_filter and results:
            results = [r for r in results if file_filter in r.file_path]

        if not results:
            return None

        # Convert to dict format matching daemon response
        result_dicts = [r.model_dump() if hasattr(r, 'model_dump') else r.dict() for r in results]
        return {
            "found": True,
            "symbol": name,
            "primary": result_dicts[0],
            "matches": result_dicts,
            "count": len(results),
        }

    params = {"name": name}
    if file_filter:
        params["file"] = file_filter

    return auto_route(
        method="get_symbol",
        params=params,
        fallback_fn=fallback,
    )


def route_search(
    query: str,
    index_path: Path,
    mode: str = "auto",
    top_k: int = 10,
) -> Dict[str, Any]:
    """
    Route search command to daemon or execute directly.

    Args:
        query: Search query
        index_path: Path to index
        mode: Search mode
        top_k: Number of results

    Returns:
        Search results

    Phase 9.5: Specialized routing for search
    """
    from ..retrieval.facade import hybrid_search

    def fallback():
        results = hybrid_search(
            query=query,
            index_path=index_path,
            mode=mode,
            top_k=top_k,
        )

        # Convert to dict format
        return {
            "query": query,
            "mode": mode,
            "count": len(results),
            "results": [
                {
                    "symbol": r.symbol,
                    "file": r.file,
                    "snippet": r.snippet,
                    "score": r.score,
                }
                for r in results
            ],
        }

    return auto_route(
        method="search",
        params={"query": query, "mode": mode, "top_k": top_k},
        fallback_fn=fallback,
    )


def route_read_file(
    file_path: str,
    line_range: Optional[tuple] = None,
) -> Dict[str, Any]:
    """
    Route read_file command to daemon or execute directly.

    Args:
        file_path: Path to file
        line_range: Optional (start, end) line range

    Returns:
        File content

    Phase 9.5: Specialized routing for read_file
    """
    from ..index import read_range

    def fallback():
        if line_range:
            content = read_range(
                file_path=Path(file_path),
                start_line=line_range[0],
                end_line=line_range[1],
            )
        else:
            with open(file_path, 'r') as f:
                content = f.read()

        return {
            "file": file_path,
            "content": content,
            "lines": line_range,
        }

    params = {"file": file_path}
    if line_range:
        params["lines"] = list(line_range)

    return auto_route(
        method="read_file",
        params=params,
        fallback_fn=fallback,
    )


def get_routing_stats() -> Dict[str, Any]:
    """
    Get routing statistics and daemon info.

    Returns:
        Routing statistics

    Phase 9.5: Debugging and monitoring
    """
    daemon_available = is_daemon_available()

    stats = {
        "daemon_available": daemon_available,
        "routing_enabled": True,
    }

    if daemon_available:
        try:
            url = f"http://{DAEMON_CONFIG['host']}:{DAEMON_CONFIG['port']}/status"
            response = requests.get(url, timeout=1.0)
            if response.status_code == 200:
                stats["daemon_status"] = response.json()
        except:
            pass

    return stats
