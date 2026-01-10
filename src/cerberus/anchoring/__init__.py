"""
Anchoring Module - Phase 14.2: Context Anchors

GPS-like metadata to prevent agent hallucinations in long sessions.
"""

from cerberus.anchoring.anchor import ContextAnchorV2, AnchorConfig
from cerberus.anchoring.generator import AnchorGenerator
from cerberus.anchoring.schema import (
    AnchorMetadata,
    GPSLocation,
    DependencyInfo,
    RiskInfo,
    TemporalInfo,
    SafetyInfo,
)

__all__ = [
    "ContextAnchorV2",
    "AnchorConfig",
    "AnchorGenerator",
    "AnchorMetadata",
    "GPSLocation",
    "DependencyInfo",
    "RiskInfo",
    "TemporalInfo",
    "SafetyInfo",
]
