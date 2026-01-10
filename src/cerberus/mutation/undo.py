"""
UndoStack: Persistent undo system for mutation operations.

Phase 12.5: Infinite "Ctrl+Z" for AI agents by storing reverse patches
for every successful batch transaction.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from cerberus.logging_config import logger


class UndoStack:
    """
    Persistent undo stack for mutation operations.

    Phase 12.5: Stores every successful batch transaction with reverse patches,
    enabling unlimited undo capability for AI agents.
    """

    def __init__(self, history_dir: str = ".cerberus/history"):
        """
        Initialize undo stack.

        Args:
            history_dir: Directory to store undo history
        """
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"UndoStack initialized: {self.history_dir}")

    def record_transaction(
        self,
        operation_type: str,
        files: List[str],
        reverse_patches: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a transaction to the undo history.

        Args:
            operation_type: Type of operation (edit, delete, insert, batch)
            files: List of files affected
            reverse_patches: List of reverse patch dictionaries
            metadata: Optional metadata about the transaction

        Returns:
            Transaction ID (hash)
        """
        timestamp = datetime.now().isoformat()

        transaction = {
            "timestamp": timestamp,
            "operation_type": operation_type,
            "files": files,
            "reverse_patches": reverse_patches,
            "metadata": metadata or {}
        }

        # Generate transaction ID from content hash
        transaction_id = self._generate_transaction_id(transaction)

        # Write transaction to history
        history_file = self.history_dir / f"{transaction_id}.json"

        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(transaction, f, indent=2)

            logger.info(f"Recorded transaction {transaction_id} ({operation_type})")
            return transaction_id

        except Exception as e:
            logger.error(f"Failed to record transaction: {e}")
            raise

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get transaction history, most recent first.

        Args:
            limit: Maximum number of transactions to return

        Returns:
            List of transaction dictionaries with metadata
        """
        history_files = sorted(
            self.history_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        transactions = []

        for history_file in history_files[:limit]:
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    transaction = json.load(f)
                    transaction["transaction_id"] = history_file.stem
                    transactions.append(transaction)
            except Exception as e:
                logger.warning(f"Failed to read transaction {history_file}: {e}")

        return transactions

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific transaction by ID.

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction dictionary or None if not found
        """
        history_file = self.history_dir / f"{transaction_id}.json"

        if not history_file.exists():
            return None

        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                transaction = json.load(f)
                transaction["transaction_id"] = transaction_id
                return transaction
        except Exception as e:
            logger.error(f"Failed to read transaction {transaction_id}: {e}")
            return None

    def apply_reverse_patches(
        self,
        transaction_id: str
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Apply reverse patches from a transaction to undo it.

        Args:
            transaction_id: Transaction ID to undo

        Returns:
            Tuple of (success, applied_files, errors)
        """
        transaction = self.get_transaction(transaction_id)

        if not transaction:
            return False, [], [f"Transaction {transaction_id} not found"]

        applied_files = []
        errors = []

        logger.info(f"Applying reverse patches for transaction {transaction_id}")

        for patch in transaction["reverse_patches"]:
            file_path = patch.get("file_path")
            original_content = patch.get("original_content")

            if not file_path or original_content is None:
                errors.append(f"Invalid patch format: {patch}")
                continue

            try:
                # Write original content back to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)

                applied_files.append(file_path)
                logger.info(f"Reverted {file_path}")

            except Exception as e:
                error_msg = f"Failed to revert {file_path}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)

        success = len(errors) == 0
        return success, applied_files, errors

    def clear_history(self, keep_last: int = 0) -> int:
        """
        Clear transaction history.

        Args:
            keep_last: Number of recent transactions to keep

        Returns:
            Number of transactions deleted
        """
        history_files = sorted(
            self.history_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        deleted_count = 0

        for history_file in history_files[keep_last:]:
            try:
                history_file.unlink()
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {history_file}: {e}")

        logger.info(f"Cleared {deleted_count} transaction(s) from history")
        return deleted_count

    def _generate_transaction_id(self, transaction: Dict[str, Any]) -> str:
        """
        Generate a unique transaction ID from content hash.

        Args:
            transaction: Transaction dictionary

        Returns:
            Transaction ID (first 16 chars of SHA256 hash)
        """
        # Create deterministic string from transaction
        content = json.dumps(transaction, sort_keys=True)
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        return hash_obj.hexdigest()[:16]
