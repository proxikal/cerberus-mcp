"""
SymbolGuard: Reference protection for mutation operations.

Phase 12.5: Prevent accidental "Mass Extinction" events by checking
symbol references before destructive operations.
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
        force: bool = False
    ) -> Tuple[bool, Optional[str], List[Dict[str, Any]]]:
        """
        Check if a symbol has references before destructive operations.

        Args:
            symbol_name: Symbol to check
            file_path: File containing the symbol
            force: If True, bypass the reference check

        Returns:
            Tuple of (allowed, error_message, references_list)
            - allowed: True if operation can proceed
            - error_message: Error message if blocked, None otherwise
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

        # Block the operation
        ref_count = len(external_refs)
        error_msg = (
            f"[SAFETY BLOCK] Symbol '{symbol_name}' is referenced in {ref_count} "
            f"location(s). Use --force to override.\n"
            f"References:\n"
        )

        # Add top 5 reference locations to error message
        for i, ref in enumerate(external_refs[:5], 1):
            source_file = ref.get("source_file", "unknown")
            error_msg += f"  {i}. {source_file}\n"

        if ref_count > 5:
            error_msg += f"  ... and {ref_count - 5} more location(s)\n"

        logger.warning(error_msg)
        return False, error_msg, external_refs

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
