"""
Decorator for automatic MCP tool tracking.

Wraps MCP tools to automatically track usage, token costs, and efficiency.
"""

from functools import wraps
from typing import Any, Callable, Dict, Optional
import inspect

from cerberus.metrics.mcp_tracker import get_mcp_tracker


def extract_token_info(response: Any) -> tuple:
    """
    Extract token information from tool response.

    Args:
        response: Tool response (dict, list, or other)

    Returns:
        Tuple of (tokens_used, tokens_saved, alternative_approach, warnings, hints)
    """
    tokens_used = None
    tokens_saved = None
    alternative_approach = None
    warnings = []
    hints = []

    if isinstance(response, dict):
        # Extract _token_info if present
        if "_token_info" in response:
            token_info = response["_token_info"]
            tokens_used = token_info.get("estimated_tokens")
            tokens_saved = token_info.get("tokens_saved")
            alternative_approach = token_info.get("alternative")

        # Extract warnings if present
        if "_warnings" in response:
            warnings = [w if isinstance(w, str) else w.get("message", "") for w in response["_warnings"]]
        elif "_hints" in response:
            hints_data = response["_hints"]
            for hint in hints_data:
                if isinstance(hint, dict):
                    if hint.get("type") == "warning":
                        warnings.append(hint.get("message", ""))
                    else:
                        hints.append(hint.get("message", ""))

    return tokens_used, tokens_saved, alternative_approach, warnings, hints


def track_mcp_tool(func: Callable) -> Callable:
    """
    Decorator to automatically track MCP tool usage.

    Extracts tool name, parameters, and token info from responses,
    then records to MCP metrics tracker.

    Usage:
        @mcp.tool()
        @track_mcp_tool
        def my_tool(arg1: str, arg2: int) -> dict:
            return {"result": "..."}
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        tracker = get_mcp_tracker()

        # Capture parameters (excluding 'self' if present)
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()

        # Remove 'self' if present (for methods)
        params = {k: v for k, v in bound_args.arguments.items() if k != 'self'}

        # Sanitize parameters (convert to JSON-serializable types)
        safe_params = {}
        for key, value in params.items():
            try:
                if isinstance(value, (str, int, float, bool, type(None))):
                    safe_params[key] = value
                elif isinstance(value, (list, tuple)):
                    safe_params[key] = list(value)
                elif isinstance(value, dict):
                    safe_params[key] = dict(value)
                else:
                    safe_params[key] = str(value)
            except:
                safe_params[key] = "<not serializable>"

        # Execute the tool
        try:
            response = func(*args, **kwargs)
            success = True
            error_message = None
        except Exception as e:
            response = None
            success = False
            error_message = str(e)
            # Re-raise the exception after tracking
            tracker.track_tool_call(
                tool_name=tool_name,
                parameters=safe_params,
                success=False,
                error_message=error_message,
            )
            raise

        # Extract token information from response
        tokens_used, tokens_saved, alternative, warnings, hints = extract_token_info(response)

        # Track the call
        tracker.track_tool_call(
            tool_name=tool_name,
            parameters=safe_params,
            tokens_used=tokens_used,
            tokens_saved=tokens_saved,
            alternative_approach=alternative,
            warnings=warnings,
            hints=hints,
            success=success,
        )

        return response

    return wrapper


def track_tool_manually(
    tool_name: str,
    parameters: Dict[str, Any],
    response: Any,
    success: bool = True,
    error_message: Optional[str] = None,
) -> None:
    """
    Manually track a tool call without using the decorator.

    Useful for cases where the decorator can't be used.

    Args:
        tool_name: Name of the tool
        parameters: Tool parameters
        response: Tool response
        success: Whether the call succeeded
        error_message: Error message if failed
    """
    tracker = get_mcp_tracker()

    tokens_used, tokens_saved, alternative, warnings, hints = extract_token_info(response)

    tracker.track_tool_call(
        tool_name=tool_name,
        parameters=parameters,
        tokens_used=tokens_used,
        tokens_saved=tokens_saved,
        alternative_approach=alternative,
        warnings=warnings,
        hints=hints,
        success=success,
        error_message=error_message,
    )
