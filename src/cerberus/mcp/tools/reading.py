"""File reading tools."""
from pathlib import Path
from typing import List, Dict, Any
import os
import subprocess
from datetime import datetime

from cerberus.retrieval.utils import read_range as core_read_range
from cerberus.mcp.tools.token_utils import (
    add_token_metadata,
    add_usage_hint,
    estimate_file_tokens,
    estimate_tokens,
)
from cerberus.mcp.config import get_config_value


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

                        # Check line limit for full file reads
                        max_lines = get_config_value("limits.full_file_read_max_lines", 200)
                        if total_lines > max_lines:
                            errors.append(
                                f"Range {idx}: File has {total_lines} lines, exceeds full file read limit of {max_lines}. "
                                f"Use start_line/end_line parameters to read specific ranges."
                            )
                            continue

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

            # Check line limit for full file reads
            max_lines = get_config_value("limits.full_file_read_max_lines", 200)
            if total_lines > max_lines:
                return {
                    "error": f"File has {total_lines} lines, exceeds full file read limit of {max_lines}. "
                            f"Use start_line/end_line parameters to read specific ranges, or adjust "
                            f"'limits.full_file_read_max_lines' in config (./cerberus.toml or ~/.config/cerberus/config.toml)."
                }

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

    @mcp.tool()
    def file_info(
        path: str = None,
        paths: List[str] = None,
    ) -> dict:
        """
        Get file metadata without reading content.

        Provides lightweight file information for quick checks:
        - File size (bytes and human-readable)
        - Line count (for text files)
        - File type/extension
        - Last modified time
        - Git tracking status
        - Permissions

        Token cost: ~50-100 tokens per file (vs 1000s for reading content)

        Supports single and bulk modes:
        - Single: Provide path parameter
        - Bulk: Provide paths list

        Args:
            path: File path (single mode)
            paths: List of file paths (bulk mode)

        Returns:
            File metadata dict or list of metadata dicts

        Examples:
            # Single file
            file_info(path="src/main.py")

            # Bulk files
            file_info(paths=["src/config.py", "src/utils.py", "README.md"])
        """
        def _get_file_info(file_path_str: str) -> Dict[str, Any]:
            """Helper to get info for a single file."""
            file_path = Path(file_path_str).resolve()

            if not file_path.exists():
                return {"error": f"File not found: {file_path_str}"}

            if not file_path.is_file():
                return {"error": f"Path is not a file: {file_path_str}"}

            try:
                # Basic file stats
                stat = file_path.stat()
                size_bytes = stat.st_size

                # Human-readable size
                if size_bytes < 1024:
                    size_human = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_human = f"{size_bytes / 1024:.1f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    size_human = f"{size_bytes / (1024 * 1024):.1f} MB"
                else:
                    size_human = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

                # Last modified
                mtime = datetime.fromtimestamp(stat.st_mtime)
                modified_str = mtime.strftime("%Y-%m-%d %H:%M:%S")

                # Line count for text files
                line_count = None
                is_text = True
                try:
                    with open(file_path, 'r') as f:
                        line_count = sum(1 for _ in f)
                except (UnicodeDecodeError, PermissionError):
                    is_text = False

                # Git status
                git_tracked = False
                git_status = "untracked"
                try:
                    # Check if file is in a git repo
                    result = subprocess.run(
                        ["git", "ls-files", "--error-unmatch", str(file_path)],
                        cwd=file_path.parent,
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0:
                        git_tracked = True
                        # Check if modified
                        status_result = subprocess.run(
                            ["git", "status", "--porcelain", str(file_path)],
                            cwd=file_path.parent,
                            capture_output=True,
                            text=True,
                            timeout=2
                        )
                        if status_result.stdout.strip():
                            git_status = "modified"
                        else:
                            git_status = "tracked"
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass

                # Permissions (Unix-style)
                mode = stat.st_mode
                perms = oct(mode)[-3:]

                info = {
                    "path": str(file_path),
                    "name": file_path.name,
                    "extension": file_path.suffix or "none",
                    "size_bytes": size_bytes,
                    "size_human": size_human,
                    "modified": modified_str,
                    "is_text": is_text,
                    "permissions": perms,
                    "git_tracked": git_tracked,
                    "git_status": git_status,
                }

                if line_count is not None:
                    info["line_count"] = line_count

                return info

            except Exception as e:
                return {"error": str(e), "path": file_path_str}

        # Validate inputs
        if not path and not paths:
            return {"error": "Must provide either path for single file or paths for bulk mode"}

        # Handle bulk mode
        if paths:
            # Check bulk limit
            max_files = get_config_value("limits.bulk_file_info_max_files", 50)
            if len(paths) > max_files:
                return {
                    "error": f"Requested {len(paths)} files, exceeds bulk limit of {max_files}. "
                            f"Reduce request size or adjust 'limits.bulk_file_info_max_files' in config."
                }

            results = []
            errors = []

            for file_path_str in paths:
                info = _get_file_info(file_path_str)
                if "error" in info:
                    errors.append(info)
                else:
                    results.append(info)

            response = {
                "bulk_mode": True,
                "requested_count": len(paths),
                "success_count": len(results),
                "error_count": len(errors),
                "results": results,
            }

            if errors:
                response["errors"] = errors

            # Token info (metadata is lightweight)
            estimated_tokens = len(results) * 60  # ~60 tokens per file metadata
            response["_token_info"] = {
                "estimated_tokens": estimated_tokens,
                "tokens_per_file": 60,
                "alternative": "Read file content",
                "alternative_tokens_per_file": 1000,  # Rough estimate
            }

            return response

        # Single mode
        info = _get_file_info(path)

        if "error" in info:
            return info

        # Add token info
        info["_token_info"] = {
            "estimated_tokens": 60,
            "alternative": "Read file content",
            "alternative_tokens": estimate_file_tokens(path, info.get("line_count", 100)),
        }

        return info
