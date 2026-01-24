"""Symbol retrieval tools."""
from pathlib import Path
from typing import List, Dict, Any, Optional

from cerberus.retrieval.utils import find_symbol_fts, read_range

from ..index_manager import get_index_manager
from cerberus.mcp.tools.token_utils import (
    estimate_tokens,
    estimate_file_tokens,
)


def register(mcp):
    @mcp.tool()
    def get_symbol(
        name: Optional[str] = None,
        context_lines: int = 5,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Retrieve symbol(s) by exact name with surrounding code context."""
        # Validate inputs
        if not name and not symbols:
            return {
                "result": [],
                "error": "Must provide either 'name' for single retrieval or 'symbols' for bulk retrieval"
            }

        # Handle bulk mode
        if symbols:
            manager = get_index_manager()
            scan_result = manager.get_index()

            all_results: list = []
            all_seen = set()
            total_tokens = 0
            processed_files = set()
            estimated_full_file_tokens = 0
            not_found: list = []

            for symbol_name in symbols:
                matches = find_symbol_fts(symbol_name, scan_result, exact=True)

                if not matches:
                    not_found.append(symbol_name)
                    continue

                for symbol in matches:
                    # Normalize path to relative for deduplication
                    try:
                        normalized_path = str(Path(symbol.file_path).relative_to(Path.cwd()))
                    except ValueError:
                        normalized_path = symbol.file_path

                    # Create deduplication key with normalized path
                    key = (normalized_path, symbol.name, symbol.start_line, symbol.end_line, symbol.type)
                    if key in all_seen:
                        continue
                    all_seen.add(key)

                    snippet = read_range(
                        Path(symbol.file_path),
                        symbol.start_line,
                        symbol.end_line,
                        padding=context_lines,
                    )

                    # Estimate tokens for this symbol
                    symbol_tokens = estimate_tokens(snippet.content)
                    total_tokens += symbol_tokens

                    all_results.append({
                        "name": symbol.name,
                        "type": symbol.type,
                        "file": normalized_path,
                        "start_line": symbol.start_line,
                        "end_line": symbol.end_line,
                        "signature": symbol.signature,
                        "code": snippet.content,
                    })

                    # Track files for token savings calculation
                    if symbol.file_path not in processed_files:
                        processed_files.add(symbol.file_path)
                        try:
                            file_path_obj = Path(symbol.file_path)
                            if file_path_obj.exists():
                                with open(file_path_obj) as f:
                                    total_lines = sum(1 for _ in f)
                                estimated_full_file_tokens += estimate_file_tokens(symbol.file_path, total_lines)
                        except Exception:
                            # Silently skip files we can't read for token estimation
                            pass

            # Build bulk response
            response = {
                "result": all_results,
                "bulk_mode": True,
                "requested_count": len(symbols),
                "found_count": len(all_results),
            }

            if not_found:
                response["not_found"] = not_found

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
            else:
                response["_token_info"] = {
                    "estimated_tokens": total_tokens,
                    "result_count": len(all_results)
                }

            return response

        # Single mode (original logic)
        manager = get_index_manager()
        scan_result = manager.get_index()
        matches = find_symbol_fts(name, scan_result, exact=True)

        results: list = []
        seen = set()
        total_tokens = 0

        for symbol in matches:
            # Normalize path to relative for deduplication
            try:
                normalized_path = str(Path(symbol.file_path).relative_to(Path.cwd()))
            except ValueError:
                # If can't make relative, use as-is
                normalized_path = symbol.file_path

            # Create deduplication key with normalized path
            key = (normalized_path, symbol.name, symbol.start_line, symbol.end_line, symbol.type)
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
                    "file": normalized_path,  # Use normalized path in output
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
                except Exception:
                    # Silently skip files we can't read for token estimation
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
        else:
            # Show token estimate
            response["_token_info"] = {
                "estimated_tokens": total_tokens,
                "result_count": len(results)
            }

        return response
