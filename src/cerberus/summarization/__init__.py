"""
Cerberus Summarization Module

Provides code summarization using local LLMs.
Follows the self-similarity mandate: clean facade, modular structure.
"""

from .facade import SummarizationFacade, get_summarization_facade
from .local_llm import LocalLLMClient, SummaryParser
from .config import (
    LLM_CONFIG,
    SUMMARIZATION_CONFIG,
    PROMPT_TEMPLATES,
    RESPONSE_PATTERNS
)

__all__ = [
    # Main facade
    "SummarizationFacade",
    "get_summarization_facade",

    # LLM client
    "LocalLLMClient",
    "SummaryParser",

    # Configuration
    "LLM_CONFIG",
    "SUMMARIZATION_CONFIG",
    "PROMPT_TEMPLATES",
    "RESPONSE_PATTERNS",
]
