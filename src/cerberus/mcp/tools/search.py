"""Search tool - hybrid keyword + semantic search."""
from typing import Dict, Any, List, Set, Tuple
from pathlib import Path
import re

from cerberus.retrieval import hybrid_search

from ..index_manager import get_index_manager
from cerberus.mcp.tools.token_utils import (
    add_warning,
    estimate_json_tokens,
)


# Common words to ignore when extracting keywords
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "should",
    "could", "may", "might", "can", "this", "that", "these", "those",
    "where", "what", "when", "how", "why", "find", "get", "show", "list",
    "all", "any", "some", "for", "with", "from", "to", "of", "in", "on", "at"
}


def extract_keywords(query: str) -> List[str]:
    """
    Extract meaningful keywords from a natural language query.

    Args:
        query: Search query

    Returns:
        List of keywords (excluding stop words)
    """
    # Lowercase and split on non-word characters
    words = re.findall(r'\w+', query.lower())

    # Filter out stop words and very short words
    keywords = [w for w in words if w not in STOP_WORDS and len(w) > 2]

    return keywords


def generate_suggestions(query: str, index_path: Path, limit: int = 5) -> List[str]:
    """
    Generate query suggestions when search returns empty results.

    Extracts keywords from query and searches for each individually,
    returning the most relevant filenames and symbols.

    Args:
        query: Original search query
        index_path: Path to index
        limit: Max suggestions to return

    Returns:
        List of suggested search terms
    """
    keywords = extract_keywords(query)

    if not keywords:
        return []

    # Try searching for each keyword
    suggestions = set()
    for keyword in keywords[:3]:  # Limit to first 3 keywords to avoid too many searches
        try:
            results = hybrid_search(
                query=keyword,
                index_path=index_path,
                mode="keyword",
                top_k=3,  # Only need a few results per keyword
            )

            for r in results[:2]:  # Top 2 results per keyword
                # Add filename if it looks relevant
                filename = Path(r.symbol.file_path).name
                if keyword.lower() in filename.lower():
                    suggestions.add(filename)

                # Add symbol name if it looks relevant
                if keyword.lower() in r.symbol.name.lower():
                    suggestions.add(r.symbol.name)
        except Exception:
            # If keyword search fails, skip it (intentionally broad catch)
            pass

    return sorted(list(suggestions))[:limit]


def register(mcp):
    @mcp.tool()
    def search(
        query: str,
        limit: int = 5,  # SAFEGUARD: Reduced from 10 to 5 for safer default
        mode: str = "auto",
        filter_type: str = "symbols",
    ) -> Dict[str, Any]:
        """Search codebase for symbols, imports, or relationships."""
        # SAFEGUARD: Hard limit enforcement
        MAX_LIMIT = 20
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT

        manager = get_index_manager()
        manager.get_index()  # Ensure index is loaded and cached
        index_path = manager._index_path or manager._discover_index_path()

        # Handle import search separately
        if filter_type == "imports":
            import sqlite3
            conn = sqlite3.connect(str(index_path))
            conn.row_factory = sqlite3.Row

            try:
                # Search for files that import the specified module
                # Support partial matching (e.g., "pathlib" matches "pathlib.Path")
                cursor = conn.execute(
                    """
                    SELECT module, file_path, line
                    FROM imports
                    WHERE module LIKE ? OR module LIKE ?
                    ORDER BY file_path, line
                    LIMIT ?
                    """,
                    (f"%{query}%", query, limit)
                )

                import_results: List[Dict[str, Any]] = []
                seen: Set[Tuple[str, str]] = set()

                for row in cursor.fetchall():
                    # Normalize path to relative
                    try:
                        normalized_path = str(Path(row["file_path"]).relative_to(Path.cwd()))
                    except ValueError:
                        normalized_path = row["file_path"]

                    # Deduplicate by file + module
                    key = (normalized_path, row["module"])
                    if key in seen:
                        continue
                    seen.add(key)

                    import_results.append({
                        "module": row["module"],
                        "file": normalized_path,
                        "line": row["line"],
                        "type": "import"
                    })

                response: Dict[str, Any] = {
                    "result": import_results,
                    "filter_type": "imports",
                    "query": query
                }

                # Token estimation
                estimated_tokens = len(import_results) * 60  # Imports are simpler than symbols
                response["_token_info"] = {
                    "estimated_tokens": estimated_tokens,
                    "result_count": len(import_results),
                    "tokens_per_result": 60,
                    "filter_type": "imports"
                }

                if not import_results:
                    add_warning(
                        response,
                        f"No files found importing '{query}'. Try searching for: module name, package path"
                    )

                return response

            finally:
                conn.close()

        # Default: symbol search
        results = hybrid_search(
            query=query,
            index_path=index_path,
            mode=mode,
            top_k=limit,
        )

        # Deduplicate results by normalizing paths to relative
        seen = set()
        result_list: List[Dict[str, Any]] = []

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

        # If no results, generate query suggestions
        if not result_list:
            suggestions = generate_suggestions(query, index_path, limit=5)
            if suggestions:
                response["suggestions"] = suggestions
                add_warning(
                    response,
                    f"No results found for '{query}'. Try searching for: {', '.join(suggestions[:3])}"
                )

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
