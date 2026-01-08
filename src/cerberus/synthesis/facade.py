"""
Facade for the synthesis module.
Provides a clean public API for context synthesis operations.
"""

from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger

from ..schemas import (
    ContextPayload,
    CodeSymbol,
    SkeletonizedCode,
    ScanResult
)
from .skeletonizer import Skeletonizer
from .payload import PayloadSynthesizer
from .config import SKELETONIZATION_CONFIG, PAYLOAD_CONFIG


class SynthesisFacade:
    """
    Main facade for context synthesis operations.
    Provides skeletonization and payload synthesis capabilities.
    """

    def __init__(
        self,
        skeleton_config: Optional[Dict[str, Any]] = None,
        payload_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize synthesis facade.

        Args:
            skeleton_config: Configuration for skeletonization
            payload_config: Configuration for payload synthesis
        """
        self.skeletonizer = Skeletonizer(config=skeleton_config)
        self.payload_synthesizer = PayloadSynthesizer(config=payload_config)
        logger.debug("SynthesisFacade initialized")

    def skeletonize_file(
        self,
        file_path: str,
        preserve_symbols: Optional[List[str]] = None
    ) -> SkeletonizedCode:
        """
        Skeletonize a source code file.

        Args:
            file_path: Path to the source file
            preserve_symbols: Symbol names to preserve fully (not skeletonize)

        Returns:
            SkeletonizedCode with pruned implementation
        """
        logger.info(f"Skeletonizing {file_path}")
        return self.skeletonizer.skeletonize_file(file_path, preserve_symbols)

    def skeletonize_directory(
        self,
        directory: str,
        pattern: str = "**/*.py",
        preserve_symbols: Optional[Dict[str, List[str]]] = None
    ) -> List[SkeletonizedCode]:
        """
        Skeletonize all files matching pattern in a directory.

        Args:
            directory: Directory to scan
            pattern: Glob pattern for files
            preserve_symbols: Dict mapping file paths to symbols to preserve

        Returns:
            List of SkeletonizedCode objects
        """
        preserve_symbols = preserve_symbols or {}
        dir_path = Path(directory)
        results = []

        logger.info(f"Skeletonizing directory {directory} with pattern {pattern}")

        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                preserve = preserve_symbols.get(str(file_path), [])
                try:
                    skeleton = self.skeletonize_file(str(file_path), preserve)
                    results.append(skeleton)
                except Exception as e:
                    logger.error(f"Failed to skeletonize {file_path}: {e}")

        logger.info(f"Skeletonized {len(results)} files")
        return results

    def build_context_payload(
        self,
        target_symbol: CodeSymbol,
        scan_result: ScanResult,
        include_callers: bool = True,
        max_depth: int = 2,
        max_tokens: Optional[int] = None
    ) -> ContextPayload:
        """
        Build a complete context payload for a target symbol.

        Args:
            target_symbol: The symbol to build context for
            scan_result: Scan result containing all project data
            include_callers: Include recursive call graph
            max_depth: Maximum call graph depth
            max_tokens: Token budget limit

        Returns:
            ContextPayload with synthesized context
        """
        logger.info(f"Building context payload for {target_symbol.name}")
        return self.payload_synthesizer.build_payload(
            target_symbol=target_symbol,
            scan_result=scan_result,
            include_callers=include_callers,
            max_depth=max_depth,
            max_tokens=max_tokens
        )

    def get_context_for_symbol(
        self,
        symbol_name: str,
        scan_result: ScanResult,
        include_callers: bool = True,
        max_depth: int = 2,
        max_tokens: Optional[int] = None
    ) -> Optional[ContextPayload]:
        """
        Convenience method to get context payload by symbol name.

        Args:
            symbol_name: Name of the symbol to get context for
            scan_result: Scan result containing all project data
            include_callers: Include recursive call graph
            max_depth: Maximum call graph depth
            max_tokens: Token budget limit

        Returns:
            ContextPayload if symbol found, None otherwise
        """
        # Find the symbol
        target_symbol = next(
            (s for s in scan_result.symbols if s.name == symbol_name),
            None
        )

        if not target_symbol:
            logger.warning(f"Symbol '{symbol_name}' not found")
            return None

        return self.build_context_payload(
            target_symbol=target_symbol,
            scan_result=scan_result,
            include_callers=include_callers,
            max_depth=max_depth,
            max_tokens=max_tokens
        )

    def format_payload_for_agent(self, payload: ContextPayload) -> str:
        """
        Format a context payload as readable text for an AI agent.

        Args:
            payload: The context payload to format

        Returns:
            Formatted string representation
        """
        parts = []

        # Header
        parts.append(f"# Context for: {payload.target_symbol.name}")
        parts.append(f"# File: {payload.target_symbol.file_path}")
        parts.append(f"# Type: {payload.target_symbol.type}")
        parts.append(f"# Lines: {payload.target_symbol.start_line}-{payload.target_symbol.end_line}")
        parts.append(f"# Estimated Tokens: ~{payload.estimated_tokens}")
        parts.append("")

        # Target implementation
        parts.append("## Target Implementation")
        parts.append("```")
        parts.append(payload.target_implementation.strip())
        parts.append("```")
        parts.append("")

        # Skeleton context
        if payload.skeleton_context:
            parts.append("## Skeleton Context")
            for skeleton in payload.skeleton_context:
                parts.append(f"### {skeleton.file_path} (compressed {skeleton.compression_ratio:.1%})")
                parts.append("```")
                parts.append(skeleton.content.strip())
                parts.append("```")
                parts.append("")

        # Resolved imports
        if payload.resolved_imports:
            parts.append("## Resolved Imports")
            for imp in payload.resolved_imports:
                parts.append(f"- {imp.name} ({imp.type}) from {imp.file_path}:{imp.start_line}")
            parts.append("")

        # Call graph
        if payload.call_graph and payload.call_graph.root_node:
            parts.append("## Call Graph")
            parts.append(self._format_call_graph_node(payload.call_graph.root_node))
            parts.append("")

        # Type context
        if payload.type_context:
            parts.append("## Type Context")
            for type_info in payload.type_context:
                parts.append(f"- {type_info.name}: {type_info.type_annotation or type_info.inferred_type}")
            parts.append("")

        return "\n".join(parts)

    def _format_call_graph_node(self, node, indent: int = 0) -> str:
        """Recursively format call graph node."""
        lines = []
        prefix = "  " * indent
        lines.append(f"{prefix}- {node.symbol_name} ({node.file_path}:{node.line})")

        for caller in node.callers:
            lines.append(self._format_call_graph_node(caller, indent + 1))

        return "\n".join(lines)


# Singleton instance for convenience
_facade: Optional[SynthesisFacade] = None


def get_synthesis_facade(
    skeleton_config: Optional[Dict[str, Any]] = None,
    payload_config: Optional[Dict[str, Any]] = None
) -> SynthesisFacade:
    """
    Get or create the synthesis facade singleton.

    Args:
        skeleton_config: Configuration for skeletonization
        payload_config: Configuration for payload synthesis

    Returns:
        SynthesisFacade instance
    """
    global _facade
    if _facade is None:
        _facade = SynthesisFacade(
            skeleton_config=skeleton_config,
            payload_config=payload_config
        )
    return _facade
