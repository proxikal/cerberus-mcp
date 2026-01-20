"""Search tool - hybrid keyword + semantic search."""
from typing import Dict, Any

from cerberus.retrieval import hybrid_search

from ..index_manager import get_index_manager
from cerberus.mcp.tools.token_utils import (
    add_warning,
    estimate_json_tokens,
)


def register(mcp):
    @mcp.tool()
    def search(
        query: str,
        limit: int = 10,
        mode: str = "auto",
    ) -> Dict[str, Any]:
        """
        Search codebase for symbols matching query.

        TOKEN EFFICIENCY:
        - Each result: ~80-100 tokens.
        - Recommended limit: 5-10 results (~400-1,000 tokens).
        - limit directly scales tokens: limit=5 (~500), limit=10 (~1,000), limit=20 (~2,000).
        - Avoid high limits unless necessary.

        Args:
            query: Search query (keyword or natural language)
            limit: Maximum results to return
            mode: Search mode - "auto", "keyword", "semantic", "balanced"

        Returns:
            List of matching symbols with file paths and line numbers
        """
        manager = get_index_manager()
        manager.get_index()  # Ensure index is loaded and cached
        index_path = manager._index_path or manager._discover_index_path()

        results = hybrid_search(
            query=query,
            index_path=index_path,
            mode=mode,
            top_k=limit,
        )

        result_list = [
            {
                "name": r.symbol.name,
                "type": r.symbol.type,
                "file": r.symbol.file_path,
                "start_line": r.symbol.start_line,
                "end_line": r.symbol.end_line,
                "score": r.hybrid_score,
                "match_type": r.match_type,
            }
            for r in results
        ]

        response = {"result": result_list}

        # Add warning for high limits
        if limit > 20:
            add_warning(
                response,
                f"Using limit={limit} may return excessive results. "
                "Consider limit=5-10 for most use cases."
            )

        # Add token estimation (~90 tokens per result average)
        estimated_tokens = len(result_list) * 90
        response["_token_info"] = {
            "estimated_tokens": estimated_tokens,
            "result_count": len(result_list),
            "tokens_per_result": 90,
            "mode": mode,
            "limit": limit
        }

        return response
