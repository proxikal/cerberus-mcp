"""File reading tools."""
from pathlib import Path
from typing import List, Dict, Any

from cerberus.retrieval.utils import read_range as core_read_range
from cerberus.mcp.tools.token_utils import (
    add_token_metadata,
    add_usage_hint,
    estimate_file_tokens,
    estimate_tokens,
)


def register(mcp):
    @mcp.tool()
    def read_range(
        file_path: str = None,
        start_line: int = None,
        end_line: int = None,
        context_lines: int = 0,
        ranges: List[Dict[str, Any]] = None,
    ) -> dict:
        """
        Read line ranges or entire files with Cerberus metadata.

        Supports single, bulk, and full-file modes:
        - Single range: Provide file_path, start_line, end_line
        - Full file: Provide file_path only (omit start_line/end_line)
        - Bulk: Provide ranges list

        Args:
            file_path: Path to file (single mode)
            start_line: Starting line number, 1-indexed (optional - omit for full file)
            end_line: Ending line number, 1-indexed (optional - omit for full file)
            context_lines: Additional context lines before/after (default: 0)
            ranges: List of range dicts for bulk reading (each with file_path, optional start_line/end_line)

        Returns:
            Dict with result(s) and token info

        Examples:
            # Full file (NEW - entire file with metadata)
            read_range(file_path="src/config.py")

            # Single range
            read_range(file_path="src/main.py", start_line=10, end_line=20)

            # Bulk ranges (multiple ranges from same or different files)
            read_range(ranges=[
                {"file_path": "src/config.py", "start_line": 10, "end_line": 30},
                {"file_path": "src/utils.py"},  # Full file in bulk
                {"file_path": "src/models.py", "start_line": 100, "end_line": 120}
            ])
        """
        # Validate inputs
        if not file_path and not ranges:
            return {
                "error": "Must provide either file_path/start_line/end_line for single read or ranges for bulk read"
            }

        # Handle bulk mode
        if ranges:
            all_results = []
            errors = []
            total_tokens = 0
            processed_files = set()
            estimated_full_file_tokens = 0

            for idx, range_spec in enumerate(ranges):
                try:
                    r_file_path = range_spec.get("file_path")
                    r_start_line = range_spec.get("start_line")
                    r_end_line = range_spec.get("end_line")
                    r_context_lines = range_spec.get("context_lines", 0)

                    if not r_file_path:
                        errors.append(f"Range {idx}: Missing file_path")
                        continue

                    # If start/end not provided, read entire file
                    if r_start_line is None or r_end_line is None:
                        file_path_obj = Path(r_file_path)
                        if not file_path_obj.exists():
                            errors.append(f"Range {idx}: File not found: {r_file_path}")
                            continue

                        with open(file_path_obj) as f:
                            total_lines = sum(1 for _ in f)
                        r_start_line = 1
                        r_end_line = total_lines

                    snippet = core_read_range(
                        Path(r_file_path),
                        r_start_line,
                        r_end_line,
                        padding=r_context_lines,
                    )

                    # Estimate tokens for this snippet
                    snippet_tokens = estimate_tokens(snippet.content)
                    total_tokens += snippet_tokens

                    all_results.append({
                        "file": snippet.file_path,
                        "start_line": snippet.start_line,
                        "end_line": snippet.end_line,
                        "content": snippet.content,
                        "tokens": snippet_tokens
                    })

                    # Track files for token savings calculation
                    if r_file_path not in processed_files:
                        processed_files.add(r_file_path)
                        try:
                            file_path_obj = Path(r_file_path)
                            if file_path_obj.exists():
                                with open(file_path_obj) as f:
                                    total_lines = sum(1 for _ in f)
                                estimated_full_file_tokens += estimate_file_tokens(r_file_path, total_lines)
                        except:
                            pass

                except Exception as e:
                    errors.append(f"Range {idx}: {str(e)}")

            # Build bulk response
            response = {
                "result": all_results,
                "bulk_mode": True,
                "requested_count": len(ranges),
                "success_count": len(all_results),
                "error_count": len(errors),
            }

            if errors:
                response["errors"] = errors

            # Token info
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

        # Single mode
        # If start/end not provided, read entire file
        if start_line is None or end_line is None:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {
                    "error": f"File not found: {file_path}"
                }

            with open(file_path_obj) as f:
                total_lines = sum(1 for _ in f)
            start_line = 1
            end_line = total_lines

        snippet = core_read_range(
            Path(file_path),
            start_line,
            end_line,
            padding=context_lines,
        )

        # Calculate token metadata
        try:
            # Estimate full file tokens (assuming average file size)
            file_path_obj = Path(file_path)
            if file_path_obj.exists():
                with open(file_path_obj) as f:
                    total_lines = sum(1 for _ in f)
                estimated_full_file_tokens = estimate_file_tokens(file_path, total_lines)
            else:
                estimated_full_file_tokens = None
        except:
            estimated_full_file_tokens = None

        response = {
            "file": snippet.file_path,
            "start_line": snippet.start_line,
            "end_line": snippet.end_line,
            "content": snippet.content,
        }

        # Add token info
        if estimated_full_file_tokens:
            add_token_metadata(
                response,
                snippet.content,
                alternative_approach="Read full file",
                estimated_alternative_tokens=estimated_full_file_tokens
            )

        return response
