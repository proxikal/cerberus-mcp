"""
JSON-RPC 2.0 Protocol Implementation for Cerberus Daemon.

Phase 9.3: Structured agent-native communication protocol.

Implements JSON-RPC 2.0 specification:
https://www.jsonrpc.org/specification
"""

from typing import Any, Dict, Optional, Union, List
from pydantic import BaseModel, Field
from loguru import logger


# === JSON-RPC 2.0 Schemas ===

class JSONRPCRequest(BaseModel):
    """
    JSON-RPC 2.0 Request.

    Example:
        {"jsonrpc": "2.0", "method": "get_symbol", "params": {"name": "MyClass"}, "id": 1}
    """
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name to invoke")
    params: Optional[Union[Dict[str, Any], List[Any]]] = Field(
        default=None,
        description="Method parameters (object or array)"
    )
    id: Optional[Union[str, int]] = Field(
        default=None,
        description="Request ID (null for notifications)"
    )


class JSONRPCError(BaseModel):
    """
    JSON-RPC 2.0 Error object.

    Standard error codes:
        -32700: Parse error
        -32600: Invalid Request
        -32601: Method not found
        -32602: Invalid params
        -32603: Internal error
        -32000 to -32099: Server error (custom)
    """
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Any] = Field(default=None, description="Additional error data")


class JSONRPCResponse(BaseModel):
    """
    JSON-RPC 2.0 Response.

    Success example:
        {"jsonrpc": "2.0", "result": {...}, "id": 1}

    Error example:
        {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 1}
    """
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    result: Optional[Any] = Field(default=None, description="Result (on success)")
    error: Optional[JSONRPCError] = Field(default=None, description="Error (on failure)")
    id: Optional[Union[str, int]] = Field(default=None, description="Request ID")


# === Error Code Constants ===

class RPCErrorCode:
    """Standard JSON-RPC 2.0 error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Custom Cerberus error codes (server-defined)
    INDEX_ERROR = -32000
    SYMBOL_NOT_FOUND = -32001
    FILE_NOT_FOUND = -32002
    PERMISSION_DENIED = -32003


# === Helper Functions ===

def create_success_response(result: Any, request_id: Optional[Union[str, int]]) -> JSONRPCResponse:
    """
    Create a successful JSON-RPC response.

    Args:
        result: Result data
        request_id: Original request ID

    Returns:
        JSONRPCResponse with result
    """
    return JSONRPCResponse(
        jsonrpc="2.0",
        result=result,
        id=request_id,
    )


def create_error_response(
    code: int,
    message: str,
    request_id: Optional[Union[str, int]] = None,
    data: Optional[Any] = None,
) -> JSONRPCResponse:
    """
    Create an error JSON-RPC response.

    Args:
        code: Error code
        message: Error message
        request_id: Original request ID
        data: Additional error data

    Returns:
        JSONRPCResponse with error
    """
    return JSONRPCResponse(
        jsonrpc="2.0",
        error=JSONRPCError(
            code=code,
            message=message,
            data=data,
        ),
        id=request_id,
    )


def parse_rpc_request(data: Dict[str, Any]) -> Union[JSONRPCRequest, JSONRPCResponse]:
    """
    Parse raw JSON data into a JSON-RPC request.

    Args:
        data: Raw JSON dictionary

    Returns:
        JSONRPCRequest on success, or JSONRPCResponse with error on failure
    """
    try:
        return JSONRPCRequest(**data)
    except Exception as e:
        logger.error(f"Failed to parse JSON-RPC request: {e}")
        return create_error_response(
            code=RPCErrorCode.INVALID_REQUEST,
            message="Invalid Request",
            data=str(e),
        )


def validate_params(
    params: Optional[Union[Dict[str, Any], List[Any]]],
    expected_keys: Optional[List[str]] = None,
) -> Optional[JSONRPCResponse]:
    """
    Validate RPC method parameters.

    Args:
        params: Method parameters
        expected_keys: Expected parameter keys (for dict params)

    Returns:
        None if valid, JSONRPCResponse with error if invalid
    """
    if params is None:
        return None

    if expected_keys and isinstance(params, dict):
        missing = [key for key in expected_keys if key not in params]
        if missing:
            return create_error_response(
                code=RPCErrorCode.INVALID_PARAMS,
                message="Invalid params",
                data=f"Missing required parameters: {missing}",
            )

    return None


# === Response Formatting ===

def format_symbol_result(symbol_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format symbol data for agent consumption.

    Args:
        symbol_data: Raw symbol data from index (CodeSymbol dict)

    Returns:
        Agent-friendly structured data
    """
    return {
        "name": symbol_data.get("name"),
        "type": symbol_data.get("type") or symbol_data.get("symbol_type"),  # Handle both field names
        "file": symbol_data.get("file_path"),
        "line_start": symbol_data.get("start_line") or symbol_data.get("line_start"),  # Handle both
        "line_end": symbol_data.get("end_line") or symbol_data.get("line_end"),  # Handle both
        "docstring": symbol_data.get("docstring"),
        "signature": symbol_data.get("signature"),
        "complexity": symbol_data.get("complexity"),
        "parent_class": symbol_data.get("parent_class"),
        "return_type": symbol_data.get("return_type"),  # Phase 1.2: Type-aware
        "parameters": symbol_data.get("parameters"),  # Phase 1.2: Type-aware
    }


def format_search_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format search results for agent consumption.

    Args:
        results: Raw search results from index

    Returns:
        Agent-friendly list of results
    """
    return [
        {
            "rank": idx + 1,
            "score": result.get("score", 0.0),
            "symbol": result.get("name"),
            "type": result.get("symbol_type"),
            "file": result.get("file_path"),
            "line_start": result.get("line_start"),
            "line_end": result.get("line_end"),
            "match_type": result.get("match_type", "keyword"),
        }
        for idx, result in enumerate(results)
    ]


def format_file_content(content: str, file_path: str, lines: Optional[tuple] = None) -> Dict[str, Any]:
    """
    Format file content for agent consumption.

    Args:
        content: File content
        file_path: Path to file
        lines: Optional (start, end) line range

    Returns:
        Agent-friendly file data
    """
    return {
        "file": file_path,
        "content": content,
        "lines": {
            "start": lines[0] if lines else 1,
            "end": lines[1] if lines else len(content.splitlines()),
        },
        "total_lines": len(content.splitlines()),
    }


# === Batch Request Support ===

def is_batch_request(data: Any) -> bool:
    """
    Check if request is a batch request (array of requests).

    Args:
        data: Raw request data

    Returns:
        True if batch request
    """
    return isinstance(data, list)


def parse_batch_request(data: List[Dict[str, Any]]) -> List[Union[JSONRPCRequest, JSONRPCResponse]]:
    """
    Parse batch JSON-RPC request.

    Args:
        data: List of request dictionaries

    Returns:
        List of JSONRPCRequest or JSONRPCResponse (with errors)
    """
    if not data:
        return [create_error_response(
            code=RPCErrorCode.INVALID_REQUEST,
            message="Invalid Request: empty batch",
        )]

    return [parse_rpc_request(req) for req in data]
