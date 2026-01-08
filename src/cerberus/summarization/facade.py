"""
Facade for code summarization using local LLMs.
"""

import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

from ..schemas import CodeSummary, CodeSymbol, ScanResult
from .local_llm import LocalLLMClient, SummaryParser
from .config import SUMMARIZATION_CONFIG


class SummarizationFacade:
    """
    Main facade for code summarization operations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize summarization facade.

        Args:
            config: Optional configuration overrides
        """
        self.config = {**SUMMARIZATION_CONFIG, **(config or {})}
        self.llm_client = LocalLLMClient()
        self.parser = SummaryParser()
        logger.debug("SummarizationFacade initialized")

    def summarize_file(
        self,
        file_path: str,
        focus: Optional[str] = None
    ) -> Optional[CodeSummary]:
        """
        Summarize a source code file.

        Args:
            file_path: Path to the file
            focus: Optional focus area for summarization

        Returns:
            CodeSummary or None if LLM unavailable
        """
        if not self.llm_client.is_available():
            logger.warning("LLM not available, cannot summarize")
            return None

        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()

            # Check minimum lines
            line_count = len(code_content.splitlines())
            if line_count < self.config["min_lines_for_summary"]:
                logger.info(f"File {file_path} too small to summarize ({line_count} lines)")
                return self._create_simple_summary(file_path, code_content, "file")

            # Detect language
            language = self._detect_language(Path(file_path).suffix)

            # Format prompt
            prompt = self.parser.format_prompt(
                "file",
                file_path=file_path,
                language=language,
                code_content=code_content[:10000]  # Limit content size
            )

            # Generate summary
            logger.info(f"Summarizing file: {file_path}")
            response = self.llm_client.generate(prompt)

            if not response:
                return self._create_simple_summary(file_path, code_content, "file")

            # Parse response
            parsed = self.parser.parse_summary_response(response)

            return CodeSummary(
                target=file_path,
                summary_type="file",
                summary_text=parsed["purpose"],
                key_points=parsed["key_points"],
                dependencies=parsed["dependencies"],
                complexity_score=parsed["complexity"],
                generated_at=time.time(),
                model_used=self.llm_client.config["model"]
            )

        except Exception as e:
            logger.error(f"Failed to summarize file {file_path}: {e}")
            return None

    def summarize_symbol(
        self,
        symbol: CodeSymbol,
        scan_result: Optional[ScanResult] = None
    ) -> Optional[CodeSummary]:
        """
        Summarize a code symbol (function, class, etc.).

        Args:
            symbol: The symbol to summarize
            scan_result: Optional scan result for additional context

        Returns:
            CodeSummary or None if unavailable
        """
        if not self.llm_client.is_available():
            return None

        try:
            # Extract symbol code
            with open(symbol.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            symbol_code = "".join(lines[symbol.start_line - 1:symbol.end_line])

            # Format prompt
            prompt = self.parser.format_prompt(
                "symbol",
                symbol_name=symbol.name,
                symbol_type=symbol.type,
                file_path=symbol.file_path,
                code_content=symbol_code
            )

            # Generate
            logger.info(f"Summarizing symbol: {symbol.name}")
            response = self.llm_client.generate(prompt)

            if not response:
                return self._create_simple_summary(symbol.name, symbol_code, "symbol")

            parsed = self.parser.parse_summary_response(response)

            return CodeSummary(
                target=symbol.name,
                summary_type="symbol",
                summary_text=parsed["purpose"],
                key_points=parsed["key_points"],
                dependencies=parsed["dependencies"],
                complexity_score=parsed["complexity"],
                generated_at=time.time(),
                model_used=self.llm_client.config["model"]
            )

        except Exception as e:
            logger.error(f"Failed to summarize symbol {symbol.name}: {e}")
            return None

    def summarize_architecture(
        self,
        target: str,
        files: List[str],
        scan_result: Optional[ScanResult] = None
    ) -> Optional[CodeSummary]:
        """
        Summarize an architectural subsystem or layer.

        Args:
            target: Name of the subsystem/layer
            files: List of file paths in this subsystem
            scan_result: Optional scan result for context

        Returns:
            CodeSummary or None
        """
        if not self.llm_client.is_available():
            return None

        try:
            # Collect code from files
            code_snippets = []
            for file_path in files[:10]:  # Limit to first 10 files
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        code_snippets.append(f"### {file_path}\n{content[:500]}")  # Truncate
                except Exception as e:
                    logger.warning(f"Could not read {file_path}: {e}")

            code_overview = "\n\n".join(code_snippets)

            # Format prompt
            prompt = self.parser.format_prompt(
                "architecture",
                target=target,
                file_count=len(files),
                code_content=code_overview[:8000]  # Limit
            )

            # Generate
            logger.info(f"Summarizing architecture: {target}")
            response = self.llm_client.generate(prompt)

            if not response:
                return self._create_simple_summary(target, code_overview, "architecture")

            parsed = self.parser.parse_summary_response(response)

            return CodeSummary(
                target=target,
                summary_type="architecture",
                summary_text=parsed["purpose"],
                key_points=parsed["key_points"],
                dependencies=parsed["dependencies"],
                complexity_score=parsed["complexity"],
                generated_at=time.time(),
                model_used=self.llm_client.config["model"]
            )

        except Exception as e:
            logger.error(f"Failed to summarize architecture {target}: {e}")
            return None

    def _detect_language(self, extension: str) -> str:
        """Detect programming language from extension."""
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".go": "Go",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".rs": "Rust",
        }
        return ext_map.get(extension.lower(), "Unknown")

    def _create_simple_summary(
        self,
        target: str,
        code_content: str,
        summary_type: str
    ) -> CodeSummary:
        """
        Create a simple summary without LLM (fallback).

        Args:
            target: The target being summarized
            code_content: The code content
            summary_type: Type of summary

        Returns:
            Basic CodeSummary
        """
        lines = code_content.splitlines()
        line_count = len(lines)

        # Extract first comment or docstring as purpose
        purpose = f"Code file with {line_count} lines"
        for line in lines[:20]:
            if line.strip().startswith("#") or line.strip().startswith("//"):
                purpose = line.strip().lstrip("#/ ")
                break

        return CodeSummary(
            target=target,
            summary_type=summary_type,
            summary_text=purpose,
            key_points=[f"{line_count} lines of code"],
            dependencies=[],
            complexity_score=None,
            generated_at=time.time(),
            model_used="fallback"
        )


# Singleton
_facade: Optional[SummarizationFacade] = None


def get_summarization_facade(config: Optional[Dict[str, Any]] = None) -> SummarizationFacade:
    """
    Get or create summarization facade singleton.

    Args:
        config: Optional configuration

    Returns:
        SummarizationFacade instance
    """
    global _facade
    if _facade is None:
        _facade = SummarizationFacade(config=config)
    return _facade
