"""
Cerberus Synthesis Module

Provides context synthesis and skeletonization capabilities.
Follows the self-similarity mandate: clean facade, modular structure.
"""

from .facade import SynthesisFacade, get_synthesis_facade
from .skeletonizer import Skeletonizer, skeletonize_file
from .payload import PayloadSynthesizer, build_payload
from .config import (
    SKELETONIZATION_CONFIG,
    PAYLOAD_CONFIG,
    BODY_REPLACEMENTS,
    TOKEN_PRIORITY
)

__all__ = [
    # Main facade
    "SynthesisFacade",
    "get_synthesis_facade",

    # Skeletonization
    "Skeletonizer",
    "skeletonize_file",

    # Payload synthesis
    "PayloadSynthesizer",
    "build_payload",

    # Configuration
    "SKELETONIZATION_CONFIG",
    "PAYLOAD_CONFIG",
    "BODY_REPLACEMENTS",
    "TOKEN_PRIORITY",
]
