"""File reading tools."""
from pathlib import Path

from cerberus.retrieval.utils import read_range as core_read_range
from cerberus.mcp.tools.token_utils import (
    add_token_metadata,
    add_usage_hint,
    estimate_file_tokens,
)


def register(mcp):
    @mcp.tool()
    def read_range(
        file_path: str,
        start_line: int,
        end_line: int,
        context_lines: int = 0,
    ) -> dict:
        """
        Read specific lines from a file.

        Args:
            file_path: Path to file
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed)
            context_lines: Additional context lines before/after

        Returns:
            File content with metadata
        """
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
