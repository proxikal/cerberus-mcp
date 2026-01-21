"""Search tool - hybrid keyword + semantic search."""
from typing import Dict, Any
from pathlib import Path

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
        limit: int = 5,  # SAFEGUARD: Reduced from 10 to 5 for safer default
        mode: str = "auto",
    ) -> Dict[str, Any]:
        """
        Search codebase for symbols matching query.

        TOKEN EFFICIENCY:
        - Each result: ~80-100 tokens.
        - Recommended limit: 5-10 results (~400-1,000 tokens).
        - limit directly scales tokens: limit=5 (~500), limit=10 (~1,000), limit=20 (~2,000).
        - Avoid high limits unless necessary.

        SAFEGUARDS:
        - Default limit reduced to 5 (from 10) for token safety
        - Maximum limit: 50 results
        - Warnings when estimated tokens > 2000

        Args:
            query: Search query (keyword or natural language)
            limit: Maximum results to return (default: 5, max: 50)
            mode: Search mode - "auto", "keyword", "semantic", "balanced"

        Returns:
            List of matching symbols with file paths and line numbers
        """
        # SAFEGUARD: Hard limit enforcement
        MAX_LIMIT = 50
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT

        manager = get_index_manager()
        manager.get_index()  # Ensure index is loaded and cached
        index_path = manager._index_path or manager._discover_index_path()

        results = hybrid_search(
            query=query,
            index_path=index_path,
            mode=mode,
            top_k=limit,
        )

        # Deduplicate results by normalizing paths to relative
        seen = set()
        result_list = []

        for r in results:
            # Normalize path to relative for deduplication
            try:
                normalized_path = str(Path(r.symbol.file_path).relative_to(Path.cwd()))
            except ValueError:
                # If can't make relative, use as-is
                normalized_path = r.symbol.file_path

            # Create deduplication key
            key = (normalized_path, r.symbol.name, r.symbol.start_line, r.symbol.end_line, r.symbol.type)

            if key in seen:
                continue
            seen.add(key)

            result_list.append({
                "name": r.symbol.name,
                "type": r.symbol.type,
                "file": normalized_path,  # Use normalized path in output
                "start_line": r.symbol.start_line,
                "end_line": r.symbol.end_line,
                "score": r.hybrid_score,
                "match_type": r.match_type,
            })

        response = {"result": result_list}

        # Check if fallback happened (semantic/balanced mode with no embeddings)
        fallback_used = result_list and result_list[0].get("match_type") == "keyword_fallback"

        if fallback_used:
            response["fallback_used"] = True
            response["fallback_reason"] = "No embeddings available in index"

        # Add token estimation (~90 tokens per result average)
        estimated_tokens = len(result_list) * 90
        response["_token_info"] = {
            "estimated_tokens": estimated_tokens,
            "result_count": len(result_list),
            "tokens_per_result": 90,
            "mode": mode,
            "limit": limit
        }

        # Add warning if fallback occurred
        if fallback_used:
            add_warning(
                response,
                f"Semantic search requested but no embeddings available. "
                f"Falling back to keyword search. To enable semantic search, rebuild index with embeddings: "
                f"index_build(..., store_embeddings=True)"
            )

        # SAFEGUARD: Add warnings for high limits or large responses
        if limit > 20:
            add_warning(
                response,
                f"Using limit={limit} may return excessive results. "
                "Consider limit=5-10 for most use cases."
            )

        if estimated_tokens > 2000:
            add_warning(
                response,
                f"Large response (~{estimated_tokens} tokens). "
                f"Consider reducing limit (currently {limit}) for more focused results."
            )

        return response
