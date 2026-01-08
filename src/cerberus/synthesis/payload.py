"""
Payload synthesis: Assembling complete context packages.
Combines target implementation with skeleton context and resolved imports.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

from ..schemas import (
    ContextPayload,
    CodeSymbol,
    SkeletonizedCode,
    CallGraphResult,
    TypeInfo,
    ScanResult
)
from ..graph import build_recursive_call_graph
from .skeletonizer import skeletonize_file
from .config import PAYLOAD_CONFIG, TOKEN_PRIORITY


class PayloadSynthesizer:
    """
    Synthesizes complete context payloads for target symbols.
    Intelligently combines target code, skeleton context, and dependencies.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize payload synthesizer.

        Args:
            config: Optional configuration overrides
        """
        self.config = {**PAYLOAD_CONFIG, **(config or {})}

    def build_payload(
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
            target_symbol: The target symbol to build context for
            scan_result: The scan result containing all symbols and dependencies
            include_callers: Whether to include call graph
            max_depth: Maximum depth for call graph traversal
            max_tokens: Maximum token budget (None = use default from config)

        Returns:
            ContextPayload with all context components
        """
        max_tokens = max_tokens or self.config["default_max_tokens"]

        logger.info(f"Building payload for {target_symbol.name} with max_tokens={max_tokens}")

        # 1. Extract target implementation
        target_impl = self._extract_target_implementation(target_symbol)

        # 2. Build call graph if requested
        call_graph = None
        if include_callers:
            call_graph = build_recursive_call_graph(
                target_symbol=target_symbol.name,
                scan_result=scan_result,
                max_depth=max_depth
            )

        # 3. Resolve imports used by target
        resolved_imports = self._resolve_imports(target_symbol, scan_result)

        # 4. Build skeleton context for containing file
        skeleton_context = self._build_skeleton_context(target_symbol, scan_result)

        # 5. Extract relevant type context
        type_context = self._extract_type_context(target_symbol, scan_result)

        # 6. Calculate metrics
        total_lines, estimated_tokens = self._calculate_metrics(
            target_impl, skeleton_context, resolved_imports, call_graph, type_context
        )

        # 7. Apply token budget if exceeded
        if estimated_tokens > max_tokens:
            logger.warning(
                f"Payload exceeds token budget ({estimated_tokens} > {max_tokens}), "
                "applying truncation"
            )
            skeleton_context, resolved_imports, type_context = self._truncate_to_budget(
                target_impl,
                skeleton_context,
                resolved_imports,
                type_context,
                call_graph,
                max_tokens
            )
            # Recalculate metrics
            total_lines, estimated_tokens = self._calculate_metrics(
                target_impl, skeleton_context, resolved_imports, call_graph, type_context
            )

        # 8. Assemble payload
        payload = ContextPayload(
            target_symbol=target_symbol,
            target_implementation=target_impl,
            skeleton_context=skeleton_context,
            resolved_imports=resolved_imports,
            call_graph=call_graph,
            type_context=type_context,
            total_lines=total_lines,
            estimated_tokens=estimated_tokens,
            metadata={
                "include_callers": include_callers,
                "max_depth": max_depth,
                "max_tokens": max_tokens,
                "truncated": estimated_tokens > max_tokens
            }
        )

        logger.info(
            f"Payload built: {total_lines} lines, ~{estimated_tokens} tokens, "
            f"{len(skeleton_context)} skeletons, {len(resolved_imports)} imports"
        )

        return payload

    def _extract_target_implementation(self, target_symbol: CodeSymbol) -> str:
        """Extract the full implementation of the target symbol."""
        try:
            with open(target_symbol.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Extract lines for the symbol (with padding)
            start_idx = max(0, target_symbol.start_line - 1 - self.config["default_padding_lines"])
            end_idx = min(len(lines), target_symbol.end_line + self.config["default_padding_lines"])

            implementation = "".join(lines[start_idx:end_idx])
            return implementation

        except Exception as e:
            logger.error(f"Failed to extract implementation for {target_symbol.name}: {e}")
            return f"# Error: Could not read {target_symbol.file_path}"

    def _resolve_imports(
        self,
        target_symbol: CodeSymbol,
        scan_result: ScanResult
    ) -> List[CodeSymbol]:
        """
        Resolve imported symbols that are used by the target.
        Returns CodeSymbol objects for internal imports.
        """
        resolved = []

        # Find import links for the target file
        target_imports = [
            link for link in scan_result.import_links
            if link.importer_file == target_symbol.file_path
        ]

        # For each imported symbol, try to find its definition
        for import_link in target_imports:
            for imported_symbol_name in import_link.imported_symbols:
                # Look for the symbol definition in the scan result
                symbol_def = next(
                    (s for s in scan_result.symbols
                     if s.name == imported_symbol_name
                     and s.file_path != target_symbol.file_path),
                    None
                )

                if symbol_def:
                    resolved.append(symbol_def)

        logger.debug(f"Resolved {len(resolved)} imports for {target_symbol.name}")
        return resolved

    def _build_skeleton_context(
        self,
        target_symbol: CodeSymbol,
        scan_result: ScanResult
    ) -> List[SkeletonizedCode]:
        """
        Build skeletonized context for the target's containing file.
        """
        skeletons = []

        # Skeletonize the containing file, preserving only the target symbol
        try:
            skeleton = skeletonize_file(
                file_path=target_symbol.file_path,
                preserve_symbols=[target_symbol.name]
            )
            skeletons.append(skeleton)

            # If configured, also skeletonize sibling classes in the same file
            if self.config["include_sibling_methods"] and target_symbol.parent_class:
                # Find other methods in the same class
                siblings = [
                    s for s in scan_result.symbols
                    if s.file_path == target_symbol.file_path
                    and s.parent_class == target_symbol.parent_class
                    and s.name != target_symbol.name
                ]
                logger.debug(f"Found {len(siblings)} sibling methods in class {target_symbol.parent_class}")

        except Exception as e:
            logger.error(f"Failed to skeletonize {target_symbol.file_path}: {e}")

        return skeletons

    def _extract_type_context(
        self,
        target_symbol: CodeSymbol,
        scan_result: ScanResult
    ) -> List[TypeInfo]:
        """
        Extract relevant type information for the target symbol.
        """
        if not self.config["include_type_definitions"]:
            return []

        # Get type info from the target's file
        type_context = [
            t for t in scan_result.type_infos
            if t.file_path == target_symbol.file_path
        ]

        logger.debug(f"Extracted {len(type_context)} type definitions")
        return type_context

    def _calculate_metrics(
        self,
        target_impl: str,
        skeleton_context: List[SkeletonizedCode],
        resolved_imports: List[CodeSymbol],
        call_graph: Optional[CallGraphResult],
        type_context: List[TypeInfo]
    ) -> tuple[int, int]:
        """
        Calculate total lines and estimated tokens for the payload.

        Returns:
            Tuple of (total_lines, estimated_tokens)
        """
        total_lines = 0

        # Count target lines
        total_lines += len(target_impl.splitlines())

        # Count skeleton lines
        for skeleton in skeleton_context:
            total_lines += skeleton.skeleton_lines

        # Count import lines (estimate)
        for imp in resolved_imports:
            total_lines += (imp.end_line - imp.start_line + 1)

        # Count type context lines (estimate)
        total_lines += len(type_context) * 2  # Rough estimate

        # Estimate tokens (very rough)
        estimated_tokens = total_lines * self.config["estimate_tokens_per_line"]

        return total_lines, estimated_tokens

    def _truncate_to_budget(
        self,
        target_impl: str,
        skeleton_context: List[SkeletonizedCode],
        resolved_imports: List[CodeSymbol],
        type_context: List[TypeInfo],
        call_graph: Optional[CallGraphResult],
        max_tokens: int
    ) -> tuple[List[SkeletonizedCode], List[CodeSymbol], List[TypeInfo]]:
        """
        Truncate components to fit within token budget.
        Prioritizes according to TOKEN_PRIORITY in config.

        Returns:
            Tuple of (truncated_skeletons, truncated_imports, truncated_types)
        """
        # Calculate target lines (non-negotiable)
        target_lines = len(target_impl.splitlines())
        target_tokens = target_lines * self.config["estimate_tokens_per_line"]

        # Remaining budget
        remaining_budget = max_tokens - target_tokens

        # Prioritize imports > call_graph > skeleton > types
        # Allocate budget proportionally

        # Allocate 40% to imports, 30% to skeleton, 30% to types
        import_budget = int(remaining_budget * 0.4)
        skeleton_budget = int(remaining_budget * 0.3)
        type_budget = int(remaining_budget * 0.3)

        # Truncate imports
        truncated_imports = resolved_imports[:import_budget // (self.config["estimate_tokens_per_line"] * 10)]

        # Truncate types
        truncated_types = type_context[:type_budget // (self.config["estimate_tokens_per_line"] * 2)]

        logger.info(
            f"Truncated: {len(resolved_imports)} → {len(truncated_imports)} imports, "
            f"{len(type_context)} → {len(truncated_types)} types"
        )

        return skeleton_context, truncated_imports, truncated_types


def build_payload(
    target_symbol: CodeSymbol,
    scan_result: ScanResult,
    include_callers: bool = True,
    max_depth: int = 2,
    max_tokens: Optional[int] = None,
    config: Optional[Dict[str, Any]] = None
) -> ContextPayload:
    """
    Convenience function to build a context payload.

    Args:
        target_symbol: The target symbol
        scan_result: Scan result with all symbols
        include_callers: Include call graph
        max_depth: Call graph max depth
        max_tokens: Token budget
        config: Optional config overrides

    Returns:
        ContextPayload
    """
    synthesizer = PayloadSynthesizer(config=config)
    return synthesizer.build_payload(
        target_symbol=target_symbol,
        scan_result=scan_result,
        include_callers=include_callers,
        max_depth=max_depth,
        max_tokens=max_tokens
    )
