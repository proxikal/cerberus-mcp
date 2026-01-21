"""Structure and blueprint tools."""
from pathlib import Path

from cerberus.blueprint import BlueprintGenerator, BlueprintRequest, TreeRenderOptions
from ..index_manager import get_index_manager
from cerberus.mcp.tools.token_utils import (
    add_warning,
    estimate_tokens,
)


def register(mcp):
    @mcp.tool()
    def blueprint(
        path: str,
        show_deps: bool = False,
        show_meta: bool = False,
        format: str = "tree",
    ):
        """
        Generate structural blueprint of a file or directory.

        Provides a high-level view of code structure including classes,
        functions, and their relationships.

        TOKEN EFFICIENCY:

        Format costs (approx):
        - tree: ~350 tokens (recommended for LLM consumption; names only, no signatures)
        - json: ~1,800 tokens (≈5x more expensive; use only for programmatic parsing)
        - flat: ~200 tokens (symbol list)

        Metadata costs:
        - Basic (show_deps=False, show_meta=False): ~350 tokens
        - With deps/meta: up to ~1,500 tokens (≈4x increase)

        Best practices:
        - Prefer format="tree" for exploration (compact, names-only view).
        - Use format="json" or "json-compact" if you need full signatures.
        - Enable show_deps/show_meta only when necessary.

        Defaults that protect tokens:
        - max_depth=10 prevents deep trees
        - max_width=120 truncates long lines
        - show_signatures=False keeps tree format compact

        Args:
            path: File or directory path to analyze
            show_deps: Include dependency information (imports, calls); adds ~1k tokens
            show_meta: Include metadata (docstrings, line counts); adds ~1k tokens
            format: Output format - "tree" (efficient), "json" (verbose), "json-compact" (minified), "flat" (list)

        Returns:
            Formatted blueprint showing code structure. Format depends on 'format' parameter:
            - tree: ASCII tree visualization (bounded by max_depth/width)
            - json: Structured dict with symbols and metadata
            - flat: Simple list of symbols
        """
        manager = get_index_manager()
        index = manager.get_index()

        if not hasattr(index, "_store"):
            return {"error": "Blueprint requires SQLite index"}

        conn = index._store._get_connection()

        try:
            request = BlueprintRequest(
                file_path=str(Path(path).resolve()),
                show_deps=show_deps,
                show_meta=show_meta,
                output_format=format,
            )

            generator = BlueprintGenerator(conn)
            blueprint_obj = generator.generate(request)

            # Token-safe defaults: prevent unbounded tree output
            tree_options = TreeRenderOptions(
                max_depth=10,          # Captures most code, prevents pathological nesting
                max_width=120,         # Reasonable terminal width, truncates long lines
                show_signatures=False, # Show names only for compact output (~350 tokens)
            )

            output = generator.format_output(blueprint_obj, format, tree_options)

            # Build response with warnings and token info
            response = {}

            # For MCP clients, return parsed JSON for compact mode to avoid
            # an extra client-side parse step.
            if format == "json-compact" and isinstance(output, str):
                try:
                    import json
                    parsed = json.loads(output)
                    response = parsed if isinstance(parsed, dict) else {"result": parsed}
                except Exception:
                    # Fall back to raw string if parsing fails
                    response = {"result": output}
            elif isinstance(output, dict):
                response = output
            else:
                response = {"result": output}

            # Add warnings for expensive options
            if show_deps and show_meta:
                add_warning(
                    response,
                    "Using show_deps=true AND show_meta=true increases output by 2-3x. "
                    "Consider using only one if not both are needed."
                )
            elif show_deps:
                add_warning(
                    response,
                    "show_deps=true adds ~1,000 tokens. Disable if dependency info not needed."
                )
            elif show_meta:
                add_warning(
                    response,
                    "show_meta=true adds ~1,000 tokens. Disable if metadata not needed."
                )

            # Add token estimation
            output_str = str(output)
            tokens = estimate_tokens(output_str)
            response["_token_info"] = {
                "estimated_tokens": tokens,
                "format": format,
                "show_deps": show_deps,
                "show_meta": show_meta
            }

            # Warn if tree format exceeds expected token budget
            if format == "tree" and tokens > 2000 and not (show_deps or show_meta):
                add_warning(
                    response,
                    f"Blueprint output is larger than expected ({tokens} tokens). "
                    f"This usually happens with very large directories. "
                    f"Consider using a more specific path to reduce output size."
                )

            return response
        finally:
            conn.close()
