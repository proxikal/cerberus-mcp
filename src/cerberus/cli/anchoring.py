"""
Context Anchoring (GPS): Standardized headers for output blocks.

Phase 12.5: Provides permanent "anchor points" for LLM attention mechanism,
preventing context confusion in massive-context models (1M+ tokens).
"""

from typing import Optional, Dict, Any
from pathlib import Path


class ContextAnchor:
    """
    Provides standardized context headers for outputs.

    Phase 12.5: The "GPS" - rigid, consistent headers that help AI models
    maintain file/symbol identity across long conversations.
    """

    @staticmethod
    def format_header(
        file_path: Optional[str] = None,
        symbol: Optional[str] = None,
        lines: Optional[str] = None,
        status: str = "Read-Only",
        extra: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a standardized context anchor header.

        Args:
            file_path: File path
            symbol: Symbol name
            lines: Line range (e.g., "10-45")
            status: Status indicator (Read-Only, Editable, Modified, etc.)
            extra: Extra metadata to include

        Returns:
            Formatted header string

        Example:
            [File: src/auth.py] [Symbol: AuthConfig] [Lines: 10-45] [Status: Read-Only]
        """
        parts = []

        if file_path:
            # Normalize path for consistency
            normalized = str(Path(file_path))
            parts.append(f"File: {normalized}")

        if symbol:
            parts.append(f"Symbol: {symbol}")

        if lines:
            parts.append(f"Lines: {lines}")

        parts.append(f"Status: {status}")

        if extra:
            for key, value in extra.items():
                parts.append(f"{key}: {value}")

        # Format as rigid blocks
        header = " ".join(f"[{part}]" for part in parts)
        return header

    @staticmethod
    def format_mutation_header(
        operation: str,
        file_path: str,
        symbol: str,
        status: str = "Modified"
    ) -> str:
        """
        Generate header for mutation operations.

        Args:
            operation: Operation type (edit, delete, insert)
            file_path: File path
            symbol: Symbol name
            status: Status (Modified, Deleted, etc.)

        Returns:
            Formatted mutation header
        """
        return ContextAnchor.format_header(
            file_path=file_path,
            symbol=symbol,
            status=status,
            extra={"Operation": operation.upper()}
        )

    @staticmethod
    def format_result_header(
        file_path: str,
        symbol: str,
        lines_changed: int,
        lines_total: int,
        status: str = "Completed"
    ) -> str:
        """
        Generate header for result outputs.

        Args:
            file_path: File path
            symbol: Symbol name
            lines_changed: Number of lines changed
            lines_total: Total lines in file
            status: Status indicator

        Returns:
            Formatted result header
        """
        return ContextAnchor.format_header(
            file_path=file_path,
            symbol=symbol,
            lines=f"{lines_changed}/{lines_total}",
            status=status
        )

    @staticmethod
    def wrap_output(content: str, header: str, footer: Optional[str] = None) -> str:
        """
        Wrap content with header and optional footer.

        Args:
            content: Output content
            header: Context anchor header
            footer: Optional footer

        Returns:
            Wrapped output
        """
        separator = "─" * 80

        parts = [
            separator,
            header,
            separator,
            content
        ]

        if footer:
            parts.extend([separator, footer])

        parts.append(separator)

        return "\n".join(parts)

    @staticmethod
    def format_search_result_header(
        file_path: str,
        match_count: int,
        status: str = "Search Result"
    ) -> str:
        """
        Generate header for search results.

        Args:
            file_path: File path
            match_count: Number of matches
            status: Status indicator

        Returns:
            Formatted search header
        """
        return ContextAnchor.format_header(
            file_path=file_path,
            status=status,
            extra={"Matches": str(match_count)}
        )
