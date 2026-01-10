"""
ContextAnchorV2 - Phase 14.2: Main Anchor System

Configurable anchor generation with machine-first output.
"""

import os
import json
from enum import Enum
from typing import Optional, Dict, Any

from cerberus.logging_config import logger
from cerberus.anchoring.generator import AnchorGenerator
from cerberus.anchoring.schema import AnchorMetadata


class AnchorMode(Enum):
    """Anchor output mode."""
    JSON = "json"      # Default: Structured JSON
    COMPACT = "compact"  # Compact JSON (<5% overhead)
    TEXT = "text"      # Human-readable box format
    OFF = "off"        # No anchors


class AnchorConfig:
    """
    Phase 14.2: Anchor configuration from environment.

    Environment Variables:
    - CERBERUS_ANCHORS: json|compact|text|off (default: json)
    - CERBERUS_ANCHOR_COMPACT: 1 for compact mode (deprecated, use CERBERUS_ANCHORS=compact)
    """

    @staticmethod
    def get_mode() -> AnchorMode:
        """
        Get anchor mode from environment.

        Returns:
            AnchorMode
        """
        # Check CERBERUS_ANCHORS first
        mode_str = os.environ.get("CERBERUS_ANCHORS", "").lower()

        if mode_str == "off":
            return AnchorMode.OFF
        elif mode_str == "text":
            return AnchorMode.TEXT
        elif mode_str == "compact":
            return AnchorMode.COMPACT
        elif mode_str == "json" or not mode_str:
            # Default to JSON
            # Check legacy CERBERUS_ANCHOR_COMPACT for backward compatibility
            if os.environ.get("CERBERUS_ANCHOR_COMPACT") == "1":
                return AnchorMode.COMPACT
            return AnchorMode.JSON

        # Unknown mode, default to JSON
        logger.warning(f"Unknown CERBERUS_ANCHORS mode: {mode_str}, using json")
        return AnchorMode.JSON

    @staticmethod
    def is_enabled() -> bool:
        """Check if anchors are enabled."""
        return AnchorConfig.get_mode() != AnchorMode.OFF


class ContextAnchorV2:
    """
    Phase 14.2: Context anchor system with GPS metadata.

    Usage:
        anchor_system = ContextAnchorV2(store)
        output = anchor_system.wrap_symbol_output(
            file_path="src/main.py",
            symbol_name="foo",
            body={"code": "def foo(): pass"},
        )
    """

    def __init__(self, store=None):
        """
        Initialize anchor system.

        Args:
            store: SQLiteIndexStore instance (optional)
        """
        self.generator = AnchorGenerator(store)
        self.mode = AnchorConfig.get_mode()
        logger.debug(f"ContextAnchorV2 initialized (mode: {self.mode.value})")

    def wrap_symbol_output(
        self,
        file_path: str,
        symbol_name: str,
        body: Optional[Dict[str, Any]] = None,
        include_dependencies: bool = True,
        include_risk: bool = True,
        include_temporal: bool = True,
        include_safety: bool = True,
    ) -> Dict[str, Any]:
        """
        Wrap symbol output with anchor metadata.

        Phase 14.2: Adds GPS + context to prevent hallucinations.

        Args:
            file_path: Path to file
            symbol_name: Symbol name
            body: Symbol body (code, docstring, etc.)
            include_dependencies: Include dependency context
            include_risk: Include risk info
            include_temporal: Include temporal context
            include_safety: Include safety context

        Returns:
            Dictionary with anchor + body
        """
        # If anchors disabled, return body only
        if self.mode == AnchorMode.OFF:
            return body or {}

        # Generate anchor
        anchor = self.generator.generate_anchor(
            file_path=file_path,
            symbol_name=symbol_name,
            include_dependencies=include_dependencies,
            include_risk=include_risk,
            include_temporal=include_temporal,
            include_safety=include_safety,
        )

        if not anchor:
            logger.warning(f"Could not generate anchor for {symbol_name}")
            return body or {}

        # Format based on mode
        if self.mode == AnchorMode.TEXT:
            # Human-readable box format
            result = {
                "anchor_text": anchor.to_human_string(),
            }
            if body:
                result["body"] = body
            return result

        elif self.mode == AnchorMode.COMPACT:
            # Compact JSON
            result = {
                "anchor": anchor.to_dict(compact=True),
            }
            if body:
                result["body"] = body
            return result

        else:  # JSON (default)
            # Full JSON
            result = {
                "anchor": anchor.to_dict(compact=False),
            }
            if body:
                result["body"] = body
            return result

    def format_for_cli(
        self,
        file_path: str,
        symbol_name: str,
        body: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Format anchor + body for CLI output.

        Args:
            file_path: Path to file
            symbol_name: Symbol name
            body: Body text (code, etc.)
            **kwargs: Additional args for wrap_symbol_output

        Returns:
            Formatted string
        """
        # If anchors disabled, return body only
        if self.mode == AnchorMode.OFF:
            return body or ""

        # Generate wrapped output
        wrapped = self.wrap_symbol_output(
            file_path=file_path,
            symbol_name=symbol_name,
            body={"code": body} if body else None,
            **kwargs
        )

        # Format based on mode
        if self.mode == AnchorMode.TEXT:
            # Human-readable
            parts = [wrapped.get("anchor_text", "")]
            if body:
                parts.append("")
                parts.append(body)
            return "\n".join(parts)

        else:  # JSON or COMPACT
            # Machine mode - return JSON
            return json.dumps(wrapped, indent=2 if self.mode == AnchorMode.JSON else None)

    def generate_mutation_anchor(
        self,
        file_path: str,
        symbol_name: str,
        operation: str,
    ) -> Optional[AnchorMetadata]:
        """
        Generate anchor for mutation operation.

        Args:
            file_path: Path to file
            symbol_name: Symbol name
            operation: Operation type (edit, delete, insert)

        Returns:
            AnchorMetadata or None
        """
        if self.mode == AnchorMode.OFF:
            return None

        return self.generator.generate_anchor_for_mutation(
            file_path=file_path,
            symbol_name=symbol_name,
            operation=operation,
        )

    def format_mutation_output(
        self,
        file_path: str,
        symbol_name: str,
        operation: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Format mutation result with anchor.

        Args:
            file_path: Path to file
            symbol_name: Symbol name
            operation: Operation type
            result: Mutation result dict

        Returns:
            Result with anchor metadata
        """
        if self.mode == AnchorMode.OFF:
            return result

        # Generate anchor
        anchor = self.generate_mutation_anchor(
            file_path=file_path,
            symbol_name=symbol_name,
            operation=operation,
        )

        if not anchor:
            return result

        # Add anchor to result
        result_copy = result.copy()

        if self.mode == AnchorMode.TEXT:
            result_copy["anchor_text"] = anchor.to_human_string()
        elif self.mode == AnchorMode.COMPACT:
            result_copy["anchor"] = anchor.to_dict(compact=True)
        else:  # JSON
            result_copy["anchor"] = anchor.to_dict(compact=False)

        return result_copy

    def validate_symbol_location(
        self,
        file_path: str,
        symbol_name: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that symbol exists in file (hallucination detection).

        Phase 14.2: Catches wrong-file errors before mutation.

        Args:
            file_path: Path to file
            symbol_name: Symbol name

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Try to generate GPS
            gps = self.generator._extract_gps(file_path, symbol_name)

            if not gps:
                return False, f"Symbol '{symbol_name}' not found in '{file_path}'"

            if gps.lines["start"] == 0 and gps.lines["end"] == 0:
                # GPS created but no line info (fallback mode)
                return False, f"Symbol '{symbol_name}' location uncertain in '{file_path}'"

            return True, None

        except Exception as e:
            return False, f"Validation failed: {e}"

    def get_correct_location(self, symbol_name: str) -> Optional[str]:
        """
        Find correct location for symbol (for hallucination correction).

        Args:
            symbol_name: Symbol name

        Returns:
            Correct file path or None
        """
        try:
            if self.generator.store:
                symbols = self.generator.store.find_symbol_by_name(symbol_name)
                if symbols:
                    return symbols[0].file_path
        except Exception as e:
            logger.debug(f"Could not find correct location: {e}")

        return None
