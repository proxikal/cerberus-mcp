"""
JSON-RPC Method Implementations for Cerberus Daemon.

Phase 9.3: Method routing and execution.

Maps RPC method names to Cerberus index operations.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Callable
from loguru import logger

from ..retrieval import hybrid_search, find_symbol, read_range
from ..index.index_loader import load_index
from .rpc_protocol import (
    JSONRPCResponse,
    create_success_response,
    create_error_response,
    RPCErrorCode,
    format_symbol_result,
    format_search_results,
    format_file_content,
)


class RPCMethodRegistry:
    """
    Registry of available RPC methods.

    Phase 9.3: Core method implementations.
    """

    def __init__(self, index_path: Path):
        """
        Initialize method registry.

        Args:
            index_path: Path to SQLite index
        """
        self.index_path = index_path
        self.index_store = None

        # Method registry: method_name -> handler_function
        self.methods: Dict[str, Callable] = {
            # Symbol retrieval
            "get_symbol": self.get_symbol,
            "find_symbol": self.get_symbol,  # Alias

            # Search
            "search": self.search,
            "hybrid_search": self.search,  # Alias

            # File operations
            "read_file": self.read_file,
            "read_range": self.read_range,

            # Index info
            "index_stats": self.index_stats,

            # Session management (Phase 9.7 placeholders)
            "create_session": self.create_session,
            "close_session": self.close_session,

            # Meta
            "list_methods": self.list_methods,
        }

    def _ensure_index_loaded(self) -> bool:
        """
        Ensure index is loaded.

        Returns:
            True if loaded successfully
        """
        if self.index_store is None:
            try:
                self.index_store = load_index(self.index_path)
                return True
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
                return False
        return True

    def invoke(self, method: str, params: Optional[Dict[str, Any]], request_id: Optional[Any]) -> JSONRPCResponse:
        """
        Invoke an RPC method.

        Args:
            method: Method name
            params: Method parameters
            request_id: Request ID

        Returns:
            JSONRPCResponse with result or error
        """
        # Check if method exists
        if method not in self.methods:
            return create_error_response(
                code=RPCErrorCode.METHOD_NOT_FOUND,
                message=f"Method not found: {method}",
                request_id=request_id,
            )

        # Ensure index is loaded
        if not self._ensure_index_loaded():
            return create_error_response(
                code=RPCErrorCode.INDEX_ERROR,
                message="Index not loaded",
                request_id=request_id,
            )

        # Invoke method
        try:
            handler = self.methods[method]
            result = handler(params or {})
            return create_success_response(result, request_id)

        except Exception as e:
            logger.error(f"Error executing method {method}: {e}")
            return create_error_response(
                code=RPCErrorCode.INTERNAL_ERROR,
                message=f"Internal error: {str(e)}",
                request_id=request_id,
                data={"method": method, "error": str(e)},
            )

    # === Method Implementations ===

    def get_symbol(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get symbol definition.

        Params:
            name: Symbol name (required)
            file: Optional file path filter

        Returns:
            Symbol data or None
        """
        name = params.get("name")
        if not name:
            raise ValueError("Missing required parameter: name")

        file_filter = params.get("file")

        # Use find_symbol from retrieval module (requires scan_result, not index_path)
        results = find_symbol(name=name, scan_result=self.index_store)

        # Apply file filter if specified
        if file_filter and results:
            results = [r for r in results if file_filter in r.file_path]

        if not results:
            return {
                "found": False,
                "symbol": name,
                "matches": [],
            }

        # Convert CodeSymbol objects to dicts for formatting
        # CodeSymbol objects have .dict() or .model_dump() methods (Pydantic)
        try:
            # Try Pydantic v2 method first
            result_dicts = [r.model_dump() if hasattr(r, 'model_dump') else r.dict() for r in results]
        except AttributeError:
            # Fallback to dict conversion via __dict__
            result_dicts = [vars(r) for r in results]

        # Return first match with all matches list
        return {
            "found": True,
            "symbol": name,
            "primary": format_symbol_result(result_dicts[0]),
            "matches": [format_symbol_result(r) for r in result_dicts],
            "count": len(results),
        }

    def search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for symbols.

        Params:
            query: Search query (required)
            mode: Search mode (keyword, semantic, balanced, auto)
            top_k: Number of results to return

        Returns:
            Search results
        """
        query = params.get("query")
        if not query:
            raise ValueError("Missing required parameter: query")

        mode = params.get("mode", "auto")
        top_k = params.get("top_k", 10)

        # Use hybrid_search from retrieval module
        results = hybrid_search(
            query=query,
            index_path=self.index_path,
            mode=mode,
            top_k=top_k,
        )

        return {
            "query": query,
            "mode": mode,
            "count": len(results),
            "results": format_search_results(results),
        }

    def read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read file content.

        Params:
            file: File path (required)
            lines: Optional [start, end] line range

        Returns:
            File content
        """
        file_path = params.get("file")
        if not file_path:
            raise ValueError("Missing required parameter: file")

        lines = params.get("lines")
        line_range = None
        if lines:
            if not isinstance(lines, list) or len(lines) != 2:
                raise ValueError("Invalid lines parameter: must be [start, end]")
            line_range = (lines[0], lines[1])

        # Read file content
        path = Path(file_path)
        if not path.exists():
            return {
                "found": False,
                "file": file_path,
                "error": "File not found",
            }

        try:
            if line_range:
                # Use read_range from retrieval module
                content_lines = read_range(
                    file_path=path,
                    start_line=line_range[0],
                    end_line=line_range[1],
                )
                content = "\n".join(content_lines)
            else:
                content = path.read_text()

            return {
                "found": True,
                **format_file_content(content, file_path, line_range),
            }

        except Exception as e:
            return {
                "found": False,
                "file": file_path,
                "error": str(e),
            }

    def read_range(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read file content with line range.

        Params:
            file: File path (required)
            start: Start line (required)
            end: End line (required)

        Returns:
            File content in range
        """
        file_path = params.get("file")
        start = params.get("start")
        end = params.get("end")

        if not all([file_path, start, end]):
            raise ValueError("Missing required parameters: file, start, end")

        return self.read_file({"file": file_path, "lines": [start, end]})

    def index_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get index statistics.

        Returns:
            Index stats
        """
        if not self.index_store:
            return {"error": "Index not loaded"}

        stats = self.index_store.get_stats()
        return {
            "index_path": str(self.index_path),
            "total_files": stats.get("total_files", 0),
            "total_symbols": stats.get("total_symbols", 0),
            "total_imports": stats.get("total_imports", 0),
            "total_calls": stats.get("total_calls", 0),
        }

    def create_session(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create agent session (Phase 9.7 placeholder).

        Params:
            agent_id: Optional agent identifier

        Returns:
            Session info
        """
        # TODO Phase 9.7: Implement session management
        return {
            "session_id": "placeholder",
            "agent_id": params.get("agent_id", "default"),
            "created_at": 0,
            "note": "Phase 9.7: Session management not yet implemented",
        }

    def close_session(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Close agent session (Phase 9.7 placeholder).

        Params:
            session_id: Session identifier

        Returns:
            Session closure info
        """
        # TODO Phase 9.7: Implement session management
        return {
            "status": "placeholder",
            "note": "Phase 9.7: Session management not yet implemented",
        }

    def list_methods(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        List available RPC methods.

        Returns:
            List of method names
        """
        return {
            "methods": sorted(self.methods.keys()),
            "count": len(self.methods),
        }
