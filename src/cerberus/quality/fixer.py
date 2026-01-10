"""
StyleFixer - Phase 14.1: Style Issue Fixing

Applies style fixes with Symbol Guard integration and ledger logging.
"""

import os
import json
from typing import List, Tuple, Optional
from pathlib import Path

from cerberus.quality.style_guard import StyleGuardV2, StyleIssue, StyleFix
from cerberus.logging_config import logger


class StyleFixer:
    """
    Phase 14.1: Style issue fixer with Symbol Guard integration.

    This is the engine behind `cerberus quality style-fix`.

    Key Features:
    - Symbol Guard integration (blocks HIGH RISK files by default)
    - Ledger logging for all operations
    - Preview mode before applying changes
    - Verification support (--verify flag)
    """

    def __init__(self):
        """Initialize fixer."""
        self.style_guard = StyleGuardV2()
        logger.debug("StyleFixer initialized")

    def fix_file(
        self,
        file_path: str,
        preview: bool = False,
        force: bool = False,
    ) -> Tuple[bool, List[StyleFix]]:
        """
        Fix style issues in a single file.

        Phase 14.1: Symbol Guard integration - checks risk before fixing.

        Args:
            file_path: Path to file to fix
            preview: If True, only show what would be fixed (no changes)
            force: Force fix even if HIGH RISK (override Symbol Guard)

        Returns:
            Tuple of (success, fixes_applied)
        """
        try:
            # Check if file exists
            if not Path(file_path).exists():
                logger.error(f"File not found: {file_path}")
                return False, []

            # Phase 14.1: Symbol Guard integration
            if not force:
                risk_level = self._check_file_risk(file_path)
                if risk_level == "HIGH":
                    logger.warning(
                        f"⚠️  [Symbol Guard] HIGH RISK file: {file_path}\n"
                        "Style fixes disabled for safety.\n"
                        "Override with: --force"
                    )
                    return False, []

            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Detect and fix issues
            fixed_content, fixes = self.style_guard.apply_fixes(
                original_content,
                file_path
            )

            if not fixes:
                logger.info(f"✅ No style issues in {file_path}")
                return True, []

            # Preview mode - don't write changes
            if preview:
                logger.info(f"[Preview] Would apply {len(fixes)} fixes to {file_path}")
                return True, fixes

            # Write fixed content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)

            logger.info(f"✅ Applied {len(fixes)} fixes to {file_path}")

            # Phase 14.1: Ledger logging
            self._log_to_ledger(file_path, fixes, risk_level if not force else "HIGH (forced)")

            return True, fixes

        except Exception as e:
            logger.error(f"Failed to fix {file_path}: {e}")
            return False, []

    def fix_directory(
        self,
        directory: str,
        recursive: bool = False,
        preview: bool = False,
        force: bool = False,
        extensions: List[str] = None
    ) -> dict[str, Tuple[bool, List[StyleFix]]]:
        """
        Fix style issues in all files in a directory.

        Args:
            directory: Directory path
            recursive: Recursively fix subdirectories
            preview: If True, only show what would be fixed
            force: Force fix even for HIGH RISK files
            extensions: File extensions to fix (default: .py, .js, .ts)

        Returns:
            Dict mapping file paths to (success, fixes) tuples
        """
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.jsx', '.tsx']

        dir_path = Path(directory)
        results = {}

        if recursive:
            files = [
                f for f in dir_path.rglob('*')
                if f.is_file() and f.suffix in extensions
            ]
        else:
            files = [
                f for f in dir_path.glob('*')
                if f.is_file() and f.suffix in extensions
            ]

        for file_path in files:
            success, fixes = self.fix_file(
                str(file_path),
                preview=preview,
                force=force
            )
            results[str(file_path)] = (success, fixes)

        total_fixes = sum(len(fixes) for _, fixes in results.values())
        logger.info(f"Fixed {len(files)} files, applied {total_fixes} total fixes")

        return results

    def _check_file_risk(self, file_path: str) -> str:
        """
        Check file risk level using Symbol Guard integration.

        Phase 14.1: Integrates with Phase 13.2 stability scoring.

        Args:
            file_path: Path to file

        Returns:
            Risk level: "SAFE", "MEDIUM", or "HIGH"
        """
        try:
            # Phase 14.1: Import Symbol Guard for risk checking
            from cerberus.mutation.guard import SymbolGuard

            guard = SymbolGuard()

            # Get stability metrics for the file
            # This integrates with Phase 13.2 stability scoring
            # For now, we'll use a simple heuristic
            # TODO: Full integration with stability scoring system

            # Check if file is in critical paths
            critical_paths = [
                'core', 'mutation', 'index', 'storage',
                'security', 'auth', 'critical'
            ]

            file_path_lower = file_path.lower()
            for critical in critical_paths:
                if critical in file_path_lower:
                    return "HIGH"

            # Default to SAFE
            return "SAFE"

        except Exception as e:
            logger.debug(f"Could not determine risk for {file_path}: {e}")
            # On error, be conservative
            return "MEDIUM"

    def _log_to_ledger(
        self,
        file_path: str,
        fixes: List[StyleFix],
        risk_level: str
    ):
        """
        Log style fixes to ledger for auditing.

        Phase 14.1: All style operations are logged for transparency.

        Args:
            file_path: Path to file
            fixes: Fixes that were applied
            risk_level: Risk level of the file
        """
        try:
            # Phase 14.1: Import ledger for logging
            from cerberus.mutation.ledger import DiffLedger

            ledger = DiffLedger()

            # Create ledger entry
            entry = {
                "operation": "style_fix",
                "file": file_path,
                "fixes_count": len(fixes),
                "fixes": [fix.to_dict() for fix in fixes],
                "risk_level": risk_level,
            }

            # Log to ledger
            # Note: DiffLedger may need extension to support style operations
            # For now, we'll log to a separate style ledger file
            self._log_to_style_ledger(entry)

        except Exception as e:
            logger.debug(f"Could not log to ledger: {e}")

    def _log_to_style_ledger(self, entry: dict):
        """
        Log to style-specific ledger file.

        Phase 14.1: Temporary solution until DiffLedger supports style ops.

        Args:
            entry: Ledger entry to log
        """
        try:
            ledger_dir = Path.home() / '.cerberus'
            ledger_dir.mkdir(exist_ok=True)

            ledger_file = ledger_dir / 'style_ledger.jsonl'

            # Append to JSONL file
            with open(ledger_file, 'a', encoding='utf-8') as f:
                json.dump(entry, f)
                f.write('\n')

        except Exception as e:
            logger.debug(f"Could not write to style ledger: {e}")

    def format_fixes(
        self,
        fixes: List[StyleFix],
        file_path: str = None,
        mode: str = "text"
    ) -> str:
        """
        Format fixes for display.

        Args:
            fixes: List of fixes
            file_path: Optional file path for context
            mode: "text" or "json"

        Returns:
            Formatted string
        """
        if not fixes:
            return "✅ No fixes applied"

        if mode == "json":
            import json
            return json.dumps(
                {
                    "file": file_path,
                    "fixes": [fix.to_dict() for fix in fixes],
                    "count": len(fixes),
                },
                indent=2
            )

        # Text mode
        lines = []
        if file_path:
            lines.append(f"[File: {file_path}]")

        lines.append(f"✅ Applied {len(fixes)} fix(es):")
        lines.append("")

        for fix in fixes:
            if fix.line:
                lines.append(f"  Line {fix.line}: {fix.description}")
            elif fix.lines:
                start, end = fix.lines
                lines.append(f"  Lines {start}-{end}: {fix.description}")
            else:
                lines.append(f"  {fix.description}")

        return '\n'.join(lines)
