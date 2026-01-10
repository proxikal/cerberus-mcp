"""
Anchor Schema - Phase 14.2: Data Models

Structured metadata for grounding agents in codebase reality.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum


class RiskLevel(Enum):
    """Risk level for Symbol Guard integration."""
    SAFE = "SAFE"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class GuardStatus(Enum):
    """Symbol Guard status."""
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass
class GPSLocation:
    """
    GPS-like location metadata.

    Phase 14.2: Prevents "where is this symbol?" confusion.
    """
    file: str
    symbol: str
    lines: Dict[str, int]  # {"start": 234, "end": 289}
    symbol_type: Optional[str] = None  # function, class, method, etc.
    parent_class: Optional[str] = None  # For methods

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "file": self.file,
            "symbol": self.symbol,
            "lines": self.lines,
            "symbol_type": self.symbol_type,
            "parent_class": self.parent_class,
        }

    def to_compact_dict(self) -> Dict[str, Any]:
        """Compact representation (<5% overhead)."""
        result = {
            "f": self.file,
            "s": self.symbol,
            "l": self.lines,
        }
        if self.symbol_type:
            result["t"] = self.symbol_type
        return result


@dataclass
class DependencyInfo:
    """
    Dependency context with confidence scores.

    Phase 14.2: Prevents "what does this call?" questions.
    """
    name: str
    confidence: float
    type: str  # "call", "import", "inheritance", etc.
    file: Optional[str] = None
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            "confidence": self.confidence,
            "type": self.type,
            "file": self.file,
            "line": self.line,
        }

    def to_compact_dict(self) -> Dict[str, Any]:
        """Compact representation."""
        result = {"n": self.name, "c": self.confidence, "t": self.type}
        if self.file:
            result["f"] = self.file
        return result


@dataclass
class RiskInfo:
    """
    Risk and stability metadata.

    Phase 14.2: Prevents "is this safe to edit?" uncertainty.
    Integrates with Phase 13.2 stability scoring.
    """
    level: RiskLevel
    score: float  # 0.0-1.0
    factors: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "level": self.level.value,
            "score": self.score,
            "factors": self.factors,
        }

    def to_compact_dict(self) -> Dict[str, Any]:
        """Compact representation."""
        return {
            "l": self.level.value[0],  # S/M/H
            "s": round(self.score, 2),
        }


@dataclass
class TemporalInfo:
    """
    Temporal context from git history.

    Phase 14.2: Prevents stale assumptions.
    """
    last_modified: Optional[str] = None  # ISO 8601 timestamp
    last_modified_by: Optional[str] = None
    created: Optional[str] = None
    days_since_last_edit: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "last_modified": self.last_modified,
            "last_modified_by": self.last_modified_by,
            "created": self.created,
            "days_since_last_edit": self.days_since_last_edit,
        }

    def to_compact_dict(self) -> Dict[str, Any]:
        """Compact representation."""
        result = {}
        if self.last_modified:
            result["m"] = self.last_modified
        if self.days_since_last_edit is not None:
            result["d"] = self.days_since_last_edit
        return result


@dataclass
class SafetyInfo:
    """
    Safety system integration status.

    Phase 14.2: Shows available safety features.
    """
    symbol_guard: GuardStatus
    verifiable: bool  # Has tests, can use --verify
    undo_available: bool
    recent_undo: bool = False  # Was recently undone

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "symbol_guard": self.symbol_guard.value,
            "verifiable": self.verifiable,
            "undo_available": self.undo_available,
            "recent_undo": self.recent_undo,
        }

    def to_compact_dict(self) -> Dict[str, Any]:
        """Compact representation."""
        return {
            "g": self.symbol_guard.value[0],  # A/W/B
            "v": self.verifiable,
            "u": self.undo_available,
        }


@dataclass
class AnchorMetadata:
    """
    Complete anchor metadata structure.

    Phase 14.2: GPS + Dependencies + Risk + Temporal + Safety.
    """
    gps: GPSLocation
    dependencies: List[DependencyInfo] = field(default_factory=list)
    risk: Optional[RiskInfo] = None
    temporal: Optional[TemporalInfo] = None
    safety: Optional[SafetyInfo] = None

    def to_dict(self, compact: bool = False) -> Dict[str, Any]:
        """
        Convert to JSON-serializable dict.

        Args:
            compact: Use compact keys for <5% token overhead

        Returns:
            Dictionary representation
        """
        if compact:
            result = {"gps": self.gps.to_compact_dict()}
            if self.dependencies:
                result["deps"] = [d.to_compact_dict() for d in self.dependencies]
            if self.risk:
                result["risk"] = self.risk.to_compact_dict()
            if self.temporal:
                result["time"] = self.temporal.to_compact_dict()
            if self.safety:
                result["safe"] = self.safety.to_compact_dict()
            return result

        # Full format
        result = {"gps": self.gps.to_dict()}
        if self.dependencies:
            result["dependencies"] = [d.to_dict() for d in self.dependencies]
        if self.risk:
            result["risk"] = self.risk.to_dict()
        if self.temporal:
            result["temporal"] = self.temporal.to_dict()
        if self.safety:
            result["safety"] = self.safety.to_dict()
        return result

    def to_human_string(self) -> str:
        """
        Convert to human-readable box format.

        Returns:
            Formatted string with box-drawing characters
        """
        lines = []
        lines.append("╭─ GPS ──────────────────────────────────────────────╮")
        lines.append(f"│ File: {self.gps.file:<45} │")
        lines.append(f"│ Symbol: {self.gps.symbol:<43} │")
        lines.append(f"│ Lines: {self.gps.lines['start']}-{self.gps.lines['end']:<41} │")

        if self.dependencies:
            lines.append("├─ Dependencies ──────────────────────────────────────┤")
            dep_str = ", ".join(
                f"{d.name} ✓{d.confidence}"
                for d in self.dependencies[:5]
            )
            lines.append(f"│ Calls: {dep_str:<44} │")

        if self.risk:
            lines.append("├─ Safety ────────────────────────────────────────────┤")
            emoji = {"SAFE": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}[self.risk.level.value]
            risk_str = f"{emoji} {self.risk.level.value}"
            if "churn_per_week" in self.risk.factors:
                risk_str += f" (churn: {self.risk.factors['churn_per_week']:.1f}/wk"
            if "test_coverage" in self.risk.factors:
                risk_str += f", coverage: {self.risk.factors['test_coverage']*100:.0f}%)"
            lines.append(f"│ Risk: {risk_str:<45} │")

            if self.safety:
                guard_status = self.safety.symbol_guard.value
                verifiable = "Yes" if self.safety.verifiable else "No"
                undo = "Available" if self.safety.undo_available else "No"
                lines.append(f"│ Guard: {guard_status} | Verifiable: {verifiable} | Undo: {undo:<10} │")

        if self.temporal:
            lines.append("├─ Temporal ──────────────────────────────────────────┤")
            if self.temporal.last_modified and self.temporal.last_modified_by:
                # Shorten timestamp
                timestamp = self.temporal.last_modified.split('T')[0]
                lines.append(f"│ Modified: {timestamp} by {self.temporal.last_modified_by:<25} │")

        lines.append("╰─────────────────────────────────────────────────────╯")
        return "\n".join(lines)
