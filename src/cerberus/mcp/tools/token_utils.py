"""
Token estimation utilities for MCP tool responses.

Provides approximate token counts and savings calculations to help
users make informed optimization decisions.
"""

from typing import Dict, Any, Optional
import json


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.

    Uses simple approximation: ~4 characters per token for code,
    ~5 characters per token for prose. This is a conservative estimate.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Use 4 chars per token as conservative estimate for code
    return len(text) // 4


def estimate_json_tokens(data: Any) -> int:
    """
    Estimate tokens for JSON data.

    Args:
        data: JSON-serializable data

    Returns:
        Estimated token count
    """
    try:
        json_str = json.dumps(data)
        return estimate_tokens(json_str)
    except:
        return 0


def add_token_metadata(
    response: Dict[str, Any],
    content: str,
    alternative_approach: Optional[str] = None,
    estimated_alternative_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Add token cost metadata to MCP response.

    Args:
        response: Original response dict
        content: Content to estimate tokens for
        alternative_approach: Description of alternative approach (e.g., "Read full file")
        estimated_alternative_tokens: Estimated tokens for alternative approach

    Returns:
        Response with token metadata added
    """
    tokens_used = estimate_tokens(content)

    response["_token_info"] = {
        "estimated_tokens": tokens_used,
    }

    if alternative_approach and estimated_alternative_tokens:
        tokens_saved = estimated_alternative_tokens - tokens_used
        savings_percent = round((tokens_saved / estimated_alternative_tokens) * 100, 1)

        response["_token_info"]["alternative"] = alternative_approach
        response["_token_info"]["alternative_tokens"] = estimated_alternative_tokens
        response["_token_info"]["tokens_saved"] = tokens_saved
        response["_token_info"]["savings_percent"] = savings_percent

    return response


def add_usage_hint(
    response: Dict[str, Any],
    hint: str,
    hint_type: str = "optimization"
) -> Dict[str, Any]:
    """
    Add usage hint to MCP response.

    Args:
        response: Original response dict
        hint: Hint message
        hint_type: Type of hint ("optimization", "warning", "suggestion")

    Returns:
        Response with hint added
    """
    if "_hints" not in response:
        response["_hints"] = []

    response["_hints"].append({
        "type": hint_type,
        "message": hint
    })

    return response


def add_warning(
    response: Dict[str, Any],
    warning: str
) -> Dict[str, Any]:
    """
    Add warning to MCP response.

    Args:
        response: Original response dict
        warning: Warning message

    Returns:
        Response with warning added
    """
    return add_usage_hint(response, warning, hint_type="warning")


def add_recommendation(
    response: Dict[str, Any],
    tool: str,
    reason: str
) -> Dict[str, Any]:
    """
    Add tool recommendation to MCP response.

    Args:
        response: Original response dict
        tool: Recommended tool name
        reason: Reason for recommendation

    Returns:
        Response with recommendation added
    """
    if "_recommendations" not in response:
        response["_recommendations"] = []

    response["_recommendations"].append({
        "tool": tool,
        "reason": reason
    })

    return response


def estimate_file_tokens(file_path: str, line_count: int) -> int:
    """
    Estimate tokens for reading a full file.

    Args:
        file_path: Path to file
        line_count: Number of lines in file

    Returns:
        Estimated token count
    """
    # Approximate: ~60 characters per line for code (conservative)
    # ~15 tokens per line
    return line_count * 15


def calculate_skeleton_savings(
    original_lines: int,
    skeleton_lines: int
) -> Dict[str, Any]:
    """
    Calculate token savings from skeletonization.

    Args:
        original_lines: Original file line count
        skeleton_lines: Skeleton line count

    Returns:
        Dict with savings information
    """
    compression_ratio = skeleton_lines / original_lines if original_lines > 0 else 0

    # Estimate tokens (~15 tokens per line for code)
    original_tokens = original_lines * 15
    skeleton_tokens = skeleton_lines * 15
    tokens_saved = original_tokens - skeleton_tokens
    savings_percent = round((1 - compression_ratio) * 100, 1)

    return {
        "original_tokens": original_tokens,
        "skeleton_tokens": skeleton_tokens,
        "tokens_saved": tokens_saved,
        "savings_percent": savings_percent,
        "compression_ratio": round(compression_ratio, 3)
    }
