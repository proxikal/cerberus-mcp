"""
SymbolGuard: Reference protection for mutation operations.

Phase 12.5: Prevent accidental "Mass Extinction" events by checking
symbol references before destructive operations.

Phase 13.2+: Integration with stability scoring for risk-aware validation.
Blocks HIGH RISK operations, warns on MEDIUM, allows LOW.
"""

import json
import subprocess
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

from cerberus.logging_config import logger
from cerberus.storage.sqlite_store import SQLiteIndexStore


class SymbolGuard:
    """
    Guard against destructive operations on referenced symbols.

    Phase 12.5: Safety mechanism to prevent accidental deletion or
    renaming of symbols that are referenced elsewhere in the codebase.
    """

    def __init__(self, store: SQLiteIndexStore, index_path: str = "cerberus.db"):
        """
        Initialize symbol guard.

        Args:
            store: SQLite index store for reference lookups
            index_path: Path to cerberus index database
        """
        self.store = store
        self.index_path = index_path
        logger.debug("SymbolGuard initialized")

    def check_references(
        self,
        symbol_name: str,
        file_path: str,
        force: bool = False,
        enable_stability_check: bool = True
    ) -> Tuple[bool, Optional[str], List[Dict[str, Any]]]:
        """
        Check if a symbol has references before destructive operations.

        Phase 13.2+: Integrates stability scoring for risk-aware validation:
        - 🔴 HIGH RISK (score < 0.50): BLOCK without --force
        - 🟡 MEDIUM (0.50-0.75): WARN but allow
        - 🟢 SAFE (> 0.75): Allow with info message

        Args:
            symbol_name: Symbol to check
            file_path: File containing the symbol
            force: If True, bypass all checks
            enable_stability_check: If True, use Phase 13.2 stability scores

        Returns:
            Tuple of (allowed, error_message, references_list)
            - allowed: True if operation can proceed
            - error_message: Error message if blocked, warning if risky, None otherwise
            - references_list: List of reference details
        """
        if force:
            logger.info(f"Symbol Guard bypassed with --force for '{symbol_name}'")
            return True, None, []

        logger.info(f"Symbol Guard: Checking references for '{symbol_name}' in {file_path}")

        # Query references using cerberus symbolic references command
        references = self._query_references(symbol_name)

        if not references:
            logger.info(f"Symbol Guard: No references found for '{symbol_name}'")
            return True, None, []

        # Filter out self-references (references from the same file)
        external_refs = [
            ref for ref in references
            if ref.get("source_file") != file_path
        ]

        if not external_refs:
            logger.info(f"Symbol Guard: Only self-references found for '{symbol_name}'")
            return True, None, references

        ref_count = len(external_refs)

        # Phase 13.2: Query stability score for risk-aware validation
        stability_info = None
        if enable_stability_check:
            stability_info = self._query_stability(symbol_name, file_path)

        # Determine risk level and blocking behavior
        risk_level = stability_info.get("level", "UNKNOWN") if stability_info else "UNKNOWN"
        stability_score = stability_info.get("score", None) if stability_info else None

        # Build error/warning message
        if risk_level == "🔴 HIGH RISK":
            # HIGH RISK: Block without --force
            error_msg = self._format_high_risk_message(
                symbol_name, ref_count, external_refs, stability_score
            )
            logger.error(error_msg)
            return False, error_msg, external_refs

        elif risk_level == "🟡 MEDIUM":
            # MEDIUM RISK: Warn but allow
            warning_msg = self._format_medium_risk_message(
                symbol_name, ref_count, external_refs, stability_score
            )
            logger.warning(warning_msg)
            return True, warning_msg, external_refs

        elif risk_level == "🟢 SAFE":
            # SAFE: Allow with info
            info_msg = f"[INFO] Symbol '{symbol_name}' is safe to modify ({risk_level}, score: {stability_score:.2f}). {ref_count} reference(s) found."
            logger.info(info_msg)
            return True, info_msg, external_refs

        else:
            # UNKNOWN: Fall back to basic reference check (original behavior)
            error_msg = self._format_basic_block_message(symbol_name, ref_count, external_refs)
            logger.warning(error_msg)
            return False, error_msg, external_refs

    def _format_high_risk_message(
        self,
        symbol_name: str,
        ref_count: int,
        references: List[Dict[str, Any]],
        score: Optional[float]
    ) -> str:
        """Format HIGH RISK blocking message."""
        score_str = f"{score:.2f}" if score is not None else "N/A"
        msg = (
            f"[🔴 HIGH RISK - BLOCKED] Symbol '{symbol_name}' has {ref_count} reference(s) "
            f"and stability score {score_str} < 0.50.\n"
            f"This symbol is HIGH RISK to modify/delete:\n"
            f"  - Low test coverage or high complexity\n"
            f"  - Recent churn or many dependencies\n"
            f"  - {ref_count} file(s) depend on this symbol\n\n"
            f"Use --force to override (NOT RECOMMENDED).\n\n"
            f"Top references:\n"
        )

        for i, ref in enumerate(references[:5], 1):
            source_file = ref.get("source_file", "unknown")
            msg += f"  {i}. {source_file}\n"

        if ref_count > 5:
            msg += f"  ... and {ref_count - 5} more\n"

        return msg

    def _format_medium_risk_message(
        self,
        symbol_name: str,
        ref_count: int,
        references: List[Dict[str, Any]],
        score: Optional[float]
    ) -> str:
        """Format MEDIUM RISK warning message."""
        score_str = f"{score:.2f}" if score is not None else "N/A"
        msg = (
            f"[🟡 MEDIUM RISK - WARNING] Symbol '{symbol_name}' has {ref_count} reference(s) "
            f"and stability score {score_str} (0.50-0.75).\n"
            f"Proceeding with caution. Consider:\n"
            f"  - Adding tests before modification\n"
            f"  - Reviewing {ref_count} dependent file(s)\n"
            f"  - Using --verify flag for validation\n\n"
            f"Top references:\n"
        )

        for i, ref in enumerate(references[:3], 1):
            source_file = ref.get("source_file", "unknown")
            msg += f"  {i}. {source_file}\n"

        if ref_count > 3:
            msg += f"  ... and {ref_count - 3} more\n"

        return msg

    def _format_basic_block_message(
        self,
        symbol_name: str,
        ref_count: int,
        references: List[Dict[str, Any]]
    ) -> str:
        """Format basic blocking message (fallback when stability unavailable)."""
        msg = (
            f"[SAFETY BLOCK] Symbol '{symbol_name}' is referenced in {ref_count} "
            f"location(s). Use --force to override.\n"
            f"References:\n"
        )

        for i, ref in enumerate(references[:5], 1):
            source_file = ref.get("source_file", "unknown")
            msg += f"  {i}. {source_file}\n"

        if ref_count > 5:
            msg += f"  ... and {ref_count - 5} more location(s)\n"

        return msg

    def _query_stability(self, symbol_name: str, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Query stability score using cerberus blueprint command.

        Args:
            symbol_name: Symbol to query
            file_path: File containing the symbol

        Returns:
            Dict with 'score' and 'level' keys, or None if unavailable
        """
        try:
            # Use cerberus blueprint with stability overlay
            cmd = [
                "cerberus",
                "retrieval",
                "blueprint",
                file_path,
                "--stability",
                "--format", "json",
                "--index", self.index_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.debug(f"Failed to query stability: {result.stderr}")
                return None

            # Parse JSON output
            data = json.loads(result.stdout)

            # Find the symbol in the blueprint output
            symbol_info = self._find_symbol_in_blueprint(data, symbol_name)
            if not symbol_info:
                logger.debug(f"Symbol '{symbol_name}' not found in blueprint output")
                return None

            # Extract stability information
            stability = symbol_info.get("stability")
            if not stability:
                logger.debug(f"No stability data for symbol '{symbol_name}'")
                return None

            return {
                "score": stability.get("score"),
                "level": stability.get("level"),
                "factors": stability.get("factors", {})
            }

        except subprocess.TimeoutExpired:
            logger.warning(f"Stability query timed out for symbol '{symbol_name}'")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse stability query response: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error querying stability: {e}")
            return None

    def _find_symbol_in_blueprint(self, blueprint_data: Any, symbol_name: str) -> Optional[Dict[str, Any]]:
        """
        Recursively search blueprint output for a symbol by name.

        Args:
            blueprint_data: Blueprint JSON data (dict or list)
            symbol_name: Name of symbol to find

        Returns:
            Symbol dictionary if found, None otherwise
        """
        if isinstance(blueprint_data, dict):
            # Check if this node matches
            if blueprint_data.get("name") == symbol_name:
                return blueprint_data
            # Recursively search children
            for child in blueprint_data.get("children", []):
                result = self._find_symbol_in_blueprint(child, symbol_name)
                if result:
                    return result
        elif isinstance(blueprint_data, list):
            # Search all items in the list
            for item in blueprint_data:
                result = self._find_symbol_in_blueprint(item, symbol_name)
                if result:
                    return result
        return None

    def _query_references(self, symbol_name: str) -> List[Dict[str, Any]]:
        """
        Query references using cerberus symbolic references command.

        Args:
            symbol_name: Symbol to query

        Returns:
            List of reference dictionaries
        """
        try:
            # Use cerberus symbolic references --target with JSON output
            cmd = [
                "cerberus",
                "symbolic",
                "references",
                "--target", symbol_name,
                "--index", self.index_path,
                "--json"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning(f"Failed to query references: {result.stderr}")
                return []

            # Parse JSON output
            data = json.loads(result.stdout)

            # Extract references from the response
            # The format may vary, handle both list and dict responses
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "references" in data:
                return data["references"]
            else:
                logger.warning(f"Unexpected reference query response format: {type(data)}")
                return []

        except subprocess.TimeoutExpired:
            logger.error(f"Reference query timed out for symbol '{symbol_name}'")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse reference query response: {e}")
            return []
        except Exception as e:
            logger.error(f"Error querying references: {e}")
            return []
