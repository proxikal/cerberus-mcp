"""Structure and blueprint tools."""
from pathlib import Path
from typing import Literal

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
        format: Literal["tree", "json", "json-compact", "flat", "list"] = "tree",
    ):
        """Generate structural blueprint of file or directory."""
        # Handle simple list format (no index required)
        if format == "list":
            target_path = Path(path).resolve()

            if not target_path.exists():
                return {"error": f"Path not found: {path}"}

            if target_path.is_file():
                # Single file
                return {
                    "result": str(target_path),
                    "type": "file",
                    "_token_info": {
                        "estimated_tokens": 10,
                        "format": "list"
                    }
                }

            # Directory listing
            items: list = []
            try:
                for item in sorted(target_path.iterdir()):
                    # Skip hidden files and common ignore patterns
                    if item.name.startswith('.'):
                        continue
                    if item.name in ['__pycache__', 'node_modules', '.git']:
                        continue

                    item_type = "dir" if item.is_dir() else "file"
                    items.append({
                        "name": item.name,
                        "type": item_type,
                        "path": str(item.relative_to(target_path.parent))
                    })

                tokens = estimate_tokens(str(items))
                return {
                    "path": str(target_path),
                    "items": items,
                    "count": len(items),
                    "_token_info": {
                        "estimated_tokens": tokens,
                        "format": "list"
                    }
                }
            except PermissionError:
                return {"error": f"Permission denied: {path}"}

        # All other formats require index
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
            elif isinstance(output, dict):  # type: ignore[unreachable]
                response = output  # type: ignore[unreachable]
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
