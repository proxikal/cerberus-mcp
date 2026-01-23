"""
Phase 6: Smart Context Assembler.

Automatically assembles relevant context for a symbol including:
- The symbol's full implementation
- Base class definitions (skeletonized)
- Inherited methods that are overridden
- Related imports and dependencies
"""

import json
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from cerberus.logging_config import logger
from cerberus.storage.sqlite_store import SQLiteIndexStore
from cerberus.schemas import CodeSymbol
from .mro_calculator import MROCalculator
from .config import CONTEXT_ASSEMBLY_CONFIG


@dataclass
class AssembledContext:
    """Represents assembled context for a symbol."""
    target_symbol: str
    target_file: str
    target_code: str
    base_classes: List[Dict[str, any]]  # List of base class info with code
    related_symbols: List[Dict[str, any]]  # Related functions, imports, etc.
    total_lines: int
    compression_ratio: float  # Compared to full file
    includes_inheritance: bool


class ContextAssembler:
    """
    Intelligently assembles code context with inheritance awareness.

    Provides AI agents with precisely the context they need, including:
    - Full implementation of target symbol
    - Skeletonized base classes
    - Overridden methods from base classes
    - Relevant imports and type definitions
    """

    def __init__(self, store: SQLiteIndexStore):
        """
        Initialize context assembler.

        Args:
            store: SQLite index store
        """
        self.store = store
        self.config = CONTEXT_ASSEMBLY_CONFIG
        self.mro_calculator = MROCalculator(store)

    def assemble_context(
        self,
        symbol_name: str,
        file_path: Optional[str] = None,
        include_bases: Optional[bool] = None,
        max_inheritance_depth: Optional[int] = None
    ) -> Optional[AssembledContext]:
        """
        Assemble smart context for a symbol.

        Args:
            symbol_name: Name of the symbol (function, class, method)
            file_path: Optional file path to disambiguate
            include_bases: Whether to include base classes (default from config)
            max_inheritance_depth: How many levels up to include (default from config)

        Returns:
            AssembledContext or None if symbol not found
        """
        include_bases = include_bases if include_bases is not None else self.config["include_base_classes"]
        max_depth = max_inheritance_depth or self.config["max_inheritance_depth"]

        logger.debug(f"Assembling context for {symbol_name} (include_bases={include_bases})")

        # Get the target symbol
        symbol = self._get_symbol(symbol_name, file_path)
        if not symbol:
            logger.warning(f"Symbol {symbol_name} not found")
            return None

        # Get the symbol's code
        target_code = self._get_symbol_code(symbol)

        # Assemble base classes if applicable and requested
        base_classes = []
        includes_inheritance = False

        if include_bases and symbol.type == "class":
            base_classes = self._assemble_base_classes(symbol_name, symbol.file_path, max_depth)
            includes_inheritance = len(base_classes) > 0

        # Get related symbols (imports, dependencies)
        related_symbols = self._get_related_symbols(symbol)

        # Calculate total lines
        total_lines = target_code.count('\n') + 1
        for base in base_classes:
            if 'code' in base:
                total_lines += base['code'].count('\n') + 1

        # Estimate compression ratio (compared to full file)
        original_file_lines = self._get_file_line_count(symbol.file_path)
        compression_ratio = total_lines / original_file_lines if original_file_lines > 0 else 1.0

        logger.debug(f"Context assembled: {total_lines} lines, {len(base_classes)} base classes")

        return AssembledContext(
            target_symbol=symbol_name,
            target_file=symbol.file_path,
            target_code=target_code,
            base_classes=base_classes,
            related_symbols=related_symbols,
            total_lines=total_lines,
            compression_ratio=compression_ratio,
            includes_inheritance=includes_inheritance
        )

    def _get_symbol(
        self,
        symbol_name: str,
        file_path: Optional[str]
    ) -> Optional[CodeSymbol]:
        """
        Get symbol from database with smart ranking.

        When multiple symbols share the same name, ranks them by:
        1. Current working directory (highest priority)
        2. Shallower path depth (likely main implementation)
        3. File name matches symbol name (e.g., Config.ts for Config class)
        4. Root-level directories (src/, lib/, pkg/, internal/)
        """
        conn = self.store._get_connection()
        try:
            if file_path:
                # Exact match requested - no ambiguity
                cursor = conn.execute("""
                    SELECT name, type, file_path, start_line, end_line,
                           signature, return_type, parameters, parent_class
                    FROM symbols
                    WHERE name = ? AND file_path = ?
                    LIMIT 1
                """, (symbol_name, file_path))
                result = cursor.fetchone()
            else:
                # Fetch ALL matches and rank them
                cursor = conn.execute("""
                    SELECT name, type, file_path, start_line, end_line,
                           signature, return_type, parameters, parent_class
                    FROM symbols
                    WHERE name = ?
                """, (symbol_name,))

                all_results = cursor.fetchall()
                if not all_results:
                    return None

                # If only one match, return it immediately
                if len(all_results) == 1:
                    result = all_results[0]
                else:
                    # Multiple matches - rank them
                    ranked = self._rank_symbols(symbol_name, all_results)
                    result = ranked[0]  # Best match

                    # Log disambiguation for transparency
                    other_locations = [r[2] for r in ranked[1:4]]  # Show up to 3 alternatives
                    logger.info(
                        f"Multiple matches for '{symbol_name}' - selected {result[2]}. "
                        f"Alternatives: {', '.join(other_locations)}"
                    )

            if result:
                return CodeSymbol(
                    name=result[0],
                    type=result[1],
                    file_path=result[2],
                    start_line=result[3],
                    end_line=result[4],
                    signature=result[5],
                    return_type=result[6],
                    parameters=json.loads(result[7]) if result[7] else None,
                    parent_class=result[8]
                )
            return None
        finally:
            conn.close()

    def _rank_symbols(self, symbol_name: str, results: list) -> list:
        """
        Rank symbol matches by relevance.

        Scoring criteria (higher = better):
        - In current working directory: +100
        - Shallower path: +(50 - path_depth)
        - File name contains symbol name: +30
        - Root-level files (src/, lib/, pkg/, internal/): +20
        """
        from pathlib import Path

        cwd = Path.cwd()
        ranked = []

        for result in results:
            file_path = result[2]
            score = 0
            path = Path(file_path)

            # 1. Prioritize files in current working directory
            try:
                path.relative_to(cwd)
                score += 100
            except ValueError:
                pass  # Not in cwd

            # 2. Prefer shallower paths (likely main implementation)
            depth = len(Path(file_path).parts)
            score += max(0, 50 - depth)

            # 3. File name matches symbol name
            file_stem = path.stem.lower()
            if symbol_name.lower() in file_stem or file_stem in symbol_name.lower():
                score += 30

            # 4. Prefer root-level directories (src, lib, pkg, internal)
            parts = Path(file_path).parts
            if len(parts) > 0 and parts[0] in ('src', 'lib', 'pkg', 'internal'):
                score += 20

            ranked.append((result, score))

        # Sort by score descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in ranked]  # Return just the results, sorted

    def _get_symbol_code(self, symbol: CodeSymbol) -> str:
        """Extract the code for a symbol from its file."""
        try:
            from pathlib import Path
            file_path = Path(symbol.file_path)

            if not file_path.exists():
                # Try relative to project root
                # For now, return placeholder
                return f"# Code for {symbol.name} at {symbol.file_path}:{symbol.start_line}-{symbol.end_line}\n"

            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Extract lines for this symbol
            start_idx = symbol.start_line - 1
            end_idx = symbol.end_line

            if start_idx < len(lines):
                symbol_lines = lines[start_idx:end_idx]
                return ''.join(symbol_lines)

            return f"# Code not found for {symbol.name}\n"

        except Exception as e:
            logger.error(f"Failed to extract code for {symbol.name}: {e}")
            return f"# Error extracting code: {e}\n"

    def _assemble_base_classes(
        self,
        class_name: str,
        file_path: str,
        max_depth: int
    ) -> List[Dict[str, any]]:
        """
        Assemble base class contexts (skeletonized if configured).

        Returns:
            List of dicts with base class info and code
        """
        base_classes = []

        # Get MRO
        mro = self.mro_calculator.compute_mro(class_name, file_path)

        # Skip first (the class itself) and limit depth
        for node in mro[1:max_depth + 1]:
            base_symbol = self._get_symbol(node.class_name, node.file_path)

            if base_symbol:
                # Get code (skeletonize if configured)
                if self.config["skeletonize_bases"]:
                    code = self._skeletonize_class(base_symbol)
                else:
                    code = self._get_symbol_code(base_symbol)

                base_classes.append({
                    "name": node.class_name,
                    "file": node.file_path,
                    "depth": node.depth,
                    "confidence": node.confidence,
                    "code": code,
                    "skeletonized": self.config["skeletonize_bases"]
                })

        return base_classes

    def _skeletonize_class(self, symbol: CodeSymbol) -> str:
        """
        Skeletonize a class (keep signatures, remove bodies).

        For now, return a simplified version.
        In production, this would use the synthesis package.
        """
        try:
            # Try to use the synthesis package
            from cerberus.synthesis import Skeletonizer

            skel = Skeletonizer()
            result = skel.skeletonize_file(symbol.file_path, preserve_symbols=[])

            # Extract just this class from the skeletonized content
            # For simplicity, return the full skeletonized file
            return result.content

        except Exception as e:
            logger.debug(f"Skeletonization not available: {e}")
            # Fallback: just return signature
            return f"class {symbol.name}:\n    # ... (skeletonized)\n    pass\n"

    def _get_related_symbols(self, symbol: CodeSymbol) -> List[Dict[str, any]]:
        """
        Get related symbols (imports, type dependencies, etc.).

        Returns:
            List of related symbol info
        """
        related = []

        # Get imports for this file
        conn = self.store._get_connection()
        try:
            cursor = conn.execute("""
                SELECT DISTINCT module, line
                FROM imports
                WHERE file_path = ?
                ORDER BY line
                LIMIT 20
            """, (symbol.file_path,))

            imports = cursor.fetchall()

            for module, line in imports:
                related.append({
                    "type": "import",
                    "name": module,
                    "line": line
                })

            return related
        finally:
            conn.close()

    def _get_file_line_count(self, file_path: str) -> int:
        """Get total line count of a file."""
        try:
            from pathlib import Path
            path = Path(file_path)

            if not path.exists():
                return 0

            with open(path, 'r', encoding='utf-8') as f:
                return sum(1 for _ in f)

        except Exception:
            return 0

    def format_context(self, context: AssembledContext) -> str:
        """
        Format assembled context as a string suitable for AI consumption.

        Args:
            context: AssembledContext to format

        Returns:
            Formatted string with all context
        """
        lines = []

        # Header
        lines.append(f"# Context for: {context.target_symbol}")
        lines.append(f"# File: {context.target_file}")
        lines.append(f"# Total lines: {context.total_lines}")
        lines.append(f"# Compression: {context.compression_ratio:.1%} of original file")
        lines.append("")

        # Related imports
        if context.related_symbols:
            lines.append("# Related imports:")
            for related in context.related_symbols[:10]:
                if related['type'] == 'import':
                    lines.append(f"# - {related['name']}")
            lines.append("")

        # Base classes (if any)
        if context.base_classes:
            lines.append(f"# Inheritance chain ({len(context.base_classes)} base classes):")
            for base in context.base_classes:
                marker = " (skeletonized)" if base['skeletonized'] else ""
                lines.append(f"# - {base['name']} at depth {base['depth']}{marker}")
            lines.append("")

            # Include base class code
            for base in context.base_classes:
                lines.append(f"# Base class: {base['name']} ({base['file']})")
                lines.append(base['code'])
                lines.append("")

        # Target symbol code
        lines.append(f"# Target: {context.target_symbol}")
        lines.append(context.target_code)

        return '\n'.join(lines)
