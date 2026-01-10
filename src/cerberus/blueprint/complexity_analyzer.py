"""Complexity analysis for code symbols.

Phase 13.1: Calculate cyclomatic complexity, line count, nesting depth, and branch count.
"""

import re
from pathlib import Path
from typing import Optional

from cerberus.logging_config import logger
from cerberus.schemas import CodeSymbol
from .schemas import ComplexityMetrics


class ComplexityAnalyzer:
    """Calculates code complexity metrics."""

    # Regex patterns for complexity analysis
    BRANCH_PATTERNS = [
        r'\bif\s+',          # if statements
        r'\belif\s+',        # elif statements
        r'\belse\s*:',       # else statements
        r'\bfor\s+',         # for loops
        r'\bwhile\s+',       # while loops
        r'\bexcept\s+',      # except blocks
        r'\btry\s*:',        # try blocks
        r'\band\b',          # logical and (adds branch)
        r'\bor\b',           # logical or (adds branch)
        r'\?.*:',            # ternary operator (for other languages)
        r'case\s+',          # case statements (for other languages)
    ]

    def __init__(self):
        """Initialize complexity analyzer."""
        self.branch_regex = re.compile('|'.join(self.BRANCH_PATTERNS))

    def analyze(self, symbol: CodeSymbol, source_code: Optional[str] = None) -> ComplexityMetrics:
        """
        Calculate complexity metrics for a symbol.

        Args:
            symbol: CodeSymbol to analyze
            source_code: Optional source code snippet. If not provided, will read from file.

        Returns:
            ComplexityMetrics with all metrics calculated
        """
        # Get source code if not provided
        if source_code is None:
            source_code = self._read_symbol_source(symbol)

        if not source_code:
            # Return minimal metrics if source unavailable
            lines = symbol.end_line - symbol.start_line + 1
            return ComplexityMetrics(
                lines=lines,
                complexity=0,
                branches=0,
                nesting=0,
                level=ComplexityMetrics.calculate_level(0, lines)
            )

        # Calculate metrics
        lines = self._count_lines(source_code)
        branches = self._count_branches(source_code)
        complexity = self._calculate_cyclomatic_complexity(branches)
        nesting = self._calculate_max_nesting(source_code)

        # Determine level
        level = ComplexityMetrics.calculate_level(complexity, lines)

        return ComplexityMetrics(
            lines=lines,
            complexity=complexity,
            branches=branches,
            nesting=nesting,
            level=level
        )

    def _read_symbol_source(self, symbol: CodeSymbol) -> Optional[str]:
        """
        Read source code for a symbol from its file.

        Args:
            symbol: CodeSymbol with file_path and line range

        Returns:
            Source code string or None if error
        """
        try:
            file_path = Path(symbol.file_path)
            if not file_path.exists():
                logger.warning(f"File not found for complexity analysis: {symbol.file_path}")
                return None

            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Extract lines for symbol (1-indexed to 0-indexed)
            start_idx = symbol.start_line - 1
            end_idx = symbol.end_line  # end_line is inclusive

            if start_idx < 0 or end_idx > len(lines):
                logger.warning(
                    f"Invalid line range for {symbol.name}: "
                    f"{symbol.start_line}-{symbol.end_line}"
                )
                return None

            source = ''.join(lines[start_idx:end_idx])
            return source

        except Exception as e:
            logger.warning(f"Error reading source for complexity analysis: {e}")
            return None

    def _count_lines(self, source_code: str) -> int:
        """
        Count non-empty, non-comment lines.

        Args:
            source_code: Source code string

        Returns:
            Number of lines
        """
        lines = source_code.split('\n')
        non_empty = 0

        for line in lines:
            stripped = line.strip()
            # Skip empty lines and comment-only lines
            if stripped and not stripped.startswith('#'):
                non_empty += 1

        return non_empty

    def _count_branches(self, source_code: str) -> int:
        """
        Count branching statements.

        Args:
            source_code: Source code string

        Returns:
            Number of branches
        """
        # Find all matches
        matches = self.branch_regex.findall(source_code)
        return len(matches)

    def _calculate_cyclomatic_complexity(self, branches: int) -> int:
        """
        Calculate cyclomatic complexity from branch count.

        Cyclomatic complexity = branches + 1 (base complexity)

        Args:
            branches: Number of branching statements

        Returns:
            Cyclomatic complexity score
        """
        return branches + 1

    def _calculate_max_nesting(self, source_code: str) -> int:
        """
        Calculate maximum nesting depth.

        Args:
            source_code: Source code string

        Returns:
            Maximum nesting level
        """
        lines = source_code.split('\n')
        max_depth = 0
        current_depth = 0
        base_indent = None

        for line in lines:
            if not line.strip():
                continue

            # Calculate indentation (spaces/tabs)
            indent = len(line) - len(line.lstrip())

            # Set base indent from first line
            if base_indent is None and line.strip():
                base_indent = indent
                current_depth = 0
                continue

            if base_indent is None:
                continue

            # Calculate depth relative to base
            relative_indent = indent - base_indent
            if relative_indent >= 0:
                # Assuming 4-space indents (adjust for tabs or 2-space)
                current_depth = relative_indent // 4
                max_depth = max(max_depth, current_depth)

        return max_depth

    def analyze_bulk(self, symbols: list[CodeSymbol]) -> dict[str, ComplexityMetrics]:
        """
        Analyze complexity for multiple symbols from same file efficiently.

        Args:
            symbols: List of CodeSymbol objects (should be from same file)

        Returns:
            Dictionary mapping symbol names to ComplexityMetrics
        """
        if not symbols:
            return {}

        result = {}

        # Group by file for efficient reading
        by_file = {}
        for symbol in symbols:
            if symbol.file_path not in by_file:
                by_file[symbol.file_path] = []
            by_file[symbol.file_path].append(symbol)

        # Analyze each file's symbols
        for file_path, file_symbols in by_file.items():
            try:
                # Read entire file once
                path = Path(file_path)
                if not path.exists():
                    continue

                with open(path, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()

                # Analyze each symbol
                for symbol in file_symbols:
                    start_idx = symbol.start_line - 1
                    end_idx = symbol.end_line

                    if start_idx >= 0 and end_idx <= len(all_lines):
                        source = ''.join(all_lines[start_idx:end_idx])
                        result[symbol.name] = self.analyze(symbol, source)

            except Exception as e:
                logger.warning(f"Error in bulk complexity analysis for {file_path}: {e}")

        return result
