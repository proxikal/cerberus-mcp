"""Symbol retrieval tools."""
from pathlib import Path
from typing import List, Dict, Any

from cerberus.retrieval.utils import find_symbol_fts, read_range

from ..index_manager import get_index_manager
from cerberus.mcp.tools.token_utils import (
    estimate_tokens,
    estimate_file_tokens,
)


def register(mcp):
    @mcp.tool()
    def get_symbol(
        name: str,
        exact: bool = True,
        context_lines: int = 5,
    ) -> Dict[str, Any]:
        """
        Retrieve symbol by name with surrounding code context.

        TOKEN EFFICIENCY:
        - Single method: ~400 tokens with default context_lines=5.
        - context_lines controls cost:
          - 0: ~300 tokens
          - 5: ~400 tokens (recommended)
          - 10: ~500 tokens
          - 20: ~700 tokens
        - Increase context_lines only if more surrounding code is required.

        Args:
            name: Symbol name to find
            exact: If True, exact match only. If False, includes partial matches.
            context_lines: Lines of context before/after symbol

        Returns:
            List of matching symbols with code snippets
        """
        manager = get_index_manager()
        scan_result = manager.get_index()
        matches = find_symbol_fts(name, scan_result, exact=exact)

        results = []
        seen = set()
        total_tokens = 0

        for symbol in matches:
            key = (symbol.file_path, symbol.name, symbol.start_line, symbol.end_line, symbol.type)
            if key in seen:
                continue
            seen.add(key)

            snippet = read_range(
                Path(symbol.file_path),
                symbol.start_line,
                symbol.end_line,
                padding=context_lines,
            )

            # Estimate tokens for this symbol
            symbol_tokens = estimate_tokens(snippet.content)
            total_tokens += symbol_tokens

            results.append(
                {
                    "name": symbol.name,
                    "type": symbol.type,
                    "file": symbol.file_path,
                    "start_line": symbol.start_line,
                    "end_line": symbol.end_line,
                    "signature": symbol.signature,
                    "code": snippet.content,
                }
            )

        # Calculate token savings
        estimated_full_file_tokens = 0
        processed_files = set()

        for symbol in matches[:len(results)]:
            if symbol.file_path not in processed_files:
                processed_files.add(symbol.file_path)
                try:
                    file_path_obj = Path(symbol.file_path)
                    if file_path_obj.exists():
                        with open(file_path_obj) as f:
                            total_lines = sum(1 for _ in f)
                        estimated_full_file_tokens += estimate_file_tokens(symbol.file_path, total_lines)
                except:
                    pass

        # Build response with token metadata
        response = {"result": results}

        if estimated_full_file_tokens > 0:
            tokens_saved = estimated_full_file_tokens - total_tokens
            savings_percent = round((tokens_saved / estimated_full_file_tokens) * 100, 1) if estimated_full_file_tokens > 0 else 0

            response["_token_info"] = {
                "estimated_tokens": total_tokens,
                "alternative": "Read full file(s)",
                "alternative_tokens": estimated_full_file_tokens,
                "tokens_saved": tokens_saved,
                "savings_percent": savings_percent
            }

        return response
