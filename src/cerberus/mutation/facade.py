"""
MutationFacade: Orchestrate surgical editing operations.

Phase 11: Main entry point for edit/insert/delete operations.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List

from cerberus.logging_config import logger
from cerberus.storage.sqlite_store import SQLiteIndexStore
from cerberus.schemas import MutationResult, SymbolLocation, EditOperation, BatchEditResult

from .locator import SymbolLocator
from .editor import CodeEditor
from .formatter import CodeFormatter
from .validator import CodeValidator
from .import_manager import ImportManager
from .ledger import DiffLedger
from .guard import SymbolGuard
from .undo import UndoStack
from .style_guard import StyleGuard
from .config import MUTATION_CONFIG


class MutationFacade:
    """
    Main facade for code mutation operations.

    Orchestrates the complete pipeline:
    1. Locate symbol (SymbolLocator)
    2. Format code (CodeFormatter)
    3. Analyze dependencies (ImportManager)
    4. Create backup (CodeEditor)
    5. Replace/insert/delete (CodeEditor)
    6. Inject imports (ImportManager)
    7. Format file (CodeFormatter)
    8. Validate (CodeValidator)
    9. Write if valid (CodeEditor)
    10. Record metrics (DiffLedger)
    """

    def __init__(
        self,
        store: SQLiteIndexStore,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize mutation facade.

        Args:
            store: SQLite index store for symbol lookups
            config: Optional config overrides
        """
        self.store = store
        self.config = {**MUTATION_CONFIG, **(config or {})}

        # Initialize components
        self.locator = SymbolLocator(store)
        self.editor = CodeEditor(self.config)
        self.formatter = CodeFormatter(self.config)
        self.validator = CodeValidator(store)
        self.import_manager = ImportManager(store)
        self.ledger = DiffLedger(self.config.get("ledger_path"))
        self.guard = SymbolGuard(store, self.config.get("index_path", "cerberus.db"))
        self.undo = UndoStack(self.config.get("undo_history_dir", ".cerberus/history"))
        self.style_guard = StyleGuard()

        logger.debug("MutationFacade initialized")

    def edit_symbol(
        self,
        file_path: str,
        symbol_name: str,
        new_code: str,
        symbol_type: Optional[str] = None,
        parent_class: Optional[str] = None,
        dry_run: bool = False,
        auto_format: bool = True,
        auto_imports: bool = True,
        force: bool = False
    ) -> MutationResult:
        """
        Edit a symbol by name.

        Args:
            file_path: Path to source file
            symbol_name: Symbol name to edit
            new_code: New code implementation
            symbol_type: Optional symbol type filter
            parent_class: Optional parent class for methods
            dry_run: If True, validate but don't write
            auto_format: If True, auto-format after edit
            auto_imports: If True, auto-inject missing imports
            force: If True, bypass reference protection (Phase 13.2)

        Returns:
            MutationResult with status and metrics
        """
        logger.info(f"Editing symbol '{symbol_name}' in {file_path}")

        # Phase 12: Read original content for diff generation
        original_content = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            logger.warning(f"Failed to read original content for diff: {e}")

        # 1. Locate symbol
        location = self.locator.locate_symbol(
            file_path,
            symbol_name,
            symbol_type,
            parent_class
        )

        if not location:
            return MutationResult(
                success=False,
                operation="edit",
                file_path=file_path,
                symbol_name=symbol_name,
                lines_changed=0,
                lines_total=0,
                write_efficiency=0.0,
                tokens_saved=0,
                validation_passed=False,
                errors=[f"Symbol '{symbol_name}' not found in {file_path}"]
            )

        # Phase 13.2: Symbol Guard - Check references and stability before edit
        if not dry_run:
            allowed, guard_message, references = self.guard.check_references(
                symbol_name,
                file_path,
                force
            )

            # Collect warnings if MEDIUM risk
            guard_warnings = []
            if guard_message and "MEDIUM" in guard_message:
                guard_warnings.append(guard_message)

            # Block if HIGH RISK without --force
            if not allowed:
                return MutationResult(
                    success=False,
                    operation="edit",
                    file_path=file_path,
                    symbol_name=symbol_name,
                    lines_changed=0,
                    lines_total=0,
                    write_efficiency=0.0,
                    tokens_saved=0,
                    validation_passed=False,
                    errors=[guard_message or "Operation blocked by Symbol Guard"],
                    warnings=[f"Found {len(references)} reference(s) to this symbol"] if references else []
                )

        # 2. Format new code to match indentation
        if auto_format:
            new_code = self.formatter.format_code_block(
                new_code,
                location.indentation_level,
                file_path
            )

        # 3. Analyze dependencies (placeholder for now)
        required_imports = []
        if auto_imports:
            required_imports = self.import_manager.analyze_dependencies(
                new_code,
                location.language
            )

        # 4-5. Replace symbol (includes backup) - skip if dry_run
        if dry_run:
            # Dry run: just validate syntax and return
            validation_passed, errors, warnings = self.validator.dry_run_validation(
                file_path,
                new_code,
                location.language
            )
            return MutationResult(
                success=validation_passed,
                operation="edit",
                file_path=file_path,
                symbol_name=symbol_name,
                lines_changed=0,
                lines_total=0,
                write_efficiency=0.0,
                tokens_saved=0,
                validation_passed=validation_passed,
                errors=errors,
                warnings=warnings,
                backup_path=None
            )

        # Normal mode: perform the edit
        success, backup_path = self.editor.replace_symbol(location, new_code)

        if not success:
            return MutationResult(
                success=False,
                operation="edit",
                file_path=file_path,
                symbol_name=symbol_name,
                lines_changed=0,
                lines_total=0,
                write_efficiency=0.0,
                tokens_saved=0,
                validation_passed=False,
                errors=["Failed to write changes"],
                backup_path=backup_path
            )

        # Read modified content for validation
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                modified_content = f.read()
        except Exception as e:
            return MutationResult(
                success=False,
                operation="edit",
                file_path=file_path,
                symbol_name=symbol_name,
                lines_changed=0,
                lines_total=0,
                write_efficiency=0.0,
                tokens_saved=0,
                validation_passed=False,
                errors=[f"Failed to read modified file: {e}"],
                backup_path=backup_path
            )

        # 6. Inject imports if needed
        if auto_imports and required_imports:
            modified_content = self.import_manager.inject_imports(
                file_path,
                modified_content,
                required_imports,
                location.language
            )

        # Phase 12.5: Apply Style Guard auto-fixes
        if not dry_run:
            # Calculate changed line numbers
            changed_lines = set(range(location.start_line - 1, location.end_line))

            # Apply style fixes
            fixed_content, fixes_applied = self.style_guard.auto_fix(
                modified_content,
                file_path,
                changed_lines
            )

            # Write fixed content back if changes were made
            if fixes_applied:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    modified_content = fixed_content
                    logger.info(f"StyleGuard applied {len(fixes_applied)} fixes")
                except Exception as e:
                    logger.warning(f"Failed to apply style fixes: {e}")

        # 7. Format file (optional)
        if auto_format and not dry_run:
            self.formatter.format_file(file_path, location.language)

        # 8. Validate
        validation_passed, errors, warnings = self.validator.dry_run_validation(
            file_path,
            modified_content,
            location.language
        )

        # Calculate metrics
        lines_total = len(modified_content.split('\n'))
        lines_changed = location.end_line - location.start_line + 1
        write_efficiency = lines_changed / lines_total if lines_total > 0 else 0.0
        tokens_saved = (lines_total - lines_changed) * 4

        # 10. Record metrics
        if self.config.get("ledger_enabled") and not dry_run:
            self.ledger.record_mutation(
                "edit",
                file_path,
                lines_changed,
                lines_total
            )

        # Phase 12: Generate unified diff
        diff = None
        if original_content and not dry_run:
            try:
                diff = self.editor.generate_unified_diff(
                    file_path,
                    original_content,
                    modified_content
                )
            except Exception as e:
                logger.warning(f"Failed to generate diff: {e}")

        return MutationResult(
            success=validation_passed and success,
            operation="edit",
            file_path=file_path,
            symbol_name=symbol_name,
            lines_changed=lines_changed,
            lines_total=lines_total,
            write_efficiency=write_efficiency,
            tokens_saved=tokens_saved,
            validation_passed=validation_passed,
            errors=errors,
            warnings=warnings,
            backup_path=backup_path,
            diff=diff
        )

    def insert_symbol(
        self,
        file_path: str,
        parent_symbol: str,
        new_code: str,
        after_symbol: Optional[str] = None,
        before_symbol: Optional[str] = None,
        dry_run: bool = False
    ) -> MutationResult:
        """
        Insert new code into a file.
        Phase 12: Complete CRUD implementation.

        Args:
            file_path: Path to file
            parent_symbol: Parent symbol (class) to insert into
            new_code: Code to insert
            after_symbol: Insert after this symbol
            before_symbol: Insert before this symbol
            dry_run: If True, validate but don't write

        Returns:
            MutationResult with status and metrics
        """
        logger.info(f"Inserting code into '{parent_symbol}' in {file_path}")

        # Phase 12: Read original content for diff generation
        original_content = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            logger.warning(f"Failed to read original content for diff: {e}")

        # Locate parent symbol
        parent_location = self.locator.locate_symbol(
            file_path,
            parent_symbol,
            symbol_type="class"  # Most common case
        )

        if not parent_location:
            return MutationResult(
                success=False,
                operation="insert",
                file_path=file_path,
                symbol_name=parent_symbol,
                lines_changed=0,
                lines_total=0,
                write_efficiency=0.0,
                tokens_saved=0,
                validation_passed=False,
                errors=[f"Parent symbol '{parent_symbol}' not found in {file_path}"]
            )

        # Determine insertion point
        byte_offset = parent_location.end_byte  # Default: end of parent

        if after_symbol:
            after_location = self.locator.locate_symbol(
                file_path,
                after_symbol,
                parent_class=parent_symbol
            )
            if after_location:
                byte_offset = after_location.end_byte
            else:
                logger.warning(f"after_symbol '{after_symbol}' not found, using default position")

        elif before_symbol:
            before_location = self.locator.locate_symbol(
                file_path,
                before_symbol,
                parent_class=parent_symbol
            )
            if before_location:
                byte_offset = before_location.start_byte
            else:
                logger.warning(f"before_symbol '{before_symbol}' not found, using default position")

        # Format new code with proper indentation
        indentation_level = parent_location.indentation_level + 1  # One level deeper than parent
        new_code_formatted = self.formatter.format_code_block(
            new_code,
            indentation_level,
            file_path
        )

        # Add newlines around the insertion
        new_code_formatted = "\n" + new_code_formatted + "\n"

        # Perform insertion if not dry run
        if not dry_run:
            success, backup_path = self.editor.insert_symbol(
                file_path,
                byte_offset,
                new_code_formatted
            )
        else:
            success, backup_path = True, None

        if not success and not dry_run:
            return MutationResult(
                success=False,
                operation="insert",
                file_path=file_path,
                symbol_name=parent_symbol,
                lines_changed=0,
                lines_total=0,
                write_efficiency=0.0,
                tokens_saved=0,
                validation_passed=False,
                errors=["Failed to insert code"],
                backup_path=backup_path
            )

        # Read modified content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                modified_content = f.read()
        except Exception as e:
            return MutationResult(
                success=False,
                operation="insert",
                file_path=file_path,
                symbol_name=parent_symbol,
                lines_changed=0,
                lines_total=0,
                write_efficiency=0.0,
                tokens_saved=0,
                validation_passed=False,
                errors=[f"Failed to read modified file: {e}"],
                backup_path=backup_path if not dry_run else None
            )

        # Validate
        validation_passed, errors, warnings = self.validator.dry_run_validation(
            file_path,
            modified_content if not dry_run else original_content + new_code_formatted,
            parent_location.language
        )

        # Calculate metrics
        lines_total = len(modified_content.split('\n'))
        lines_changed = len(new_code_formatted.split('\n'))
        write_efficiency = lines_changed / lines_total if lines_total > 0 else 0.0
        tokens_saved = (lines_total - lines_changed) * 4

        # Record metrics
        if self.config.get("ledger_enabled") and not dry_run:
            self.ledger.record_mutation(
                "insert",
                file_path,
                lines_changed,
                lines_total
            )

        # Phase 12: Generate unified diff
        diff = None
        if original_content and not dry_run:
            try:
                diff = self.editor.generate_unified_diff(
                    file_path,
                    original_content,
                    modified_content
                )
            except Exception as e:
                logger.warning(f"Failed to generate diff: {e}")

        return MutationResult(
            success=validation_passed and success,
            operation="insert",
            file_path=file_path,
            symbol_name=parent_symbol,
            lines_changed=lines_changed,
            lines_total=lines_total,
            write_efficiency=write_efficiency,
            tokens_saved=tokens_saved,
            validation_passed=validation_passed,
            errors=errors,
            warnings=warnings,
            backup_path=backup_path if not dry_run else None,
            diff=diff
        )

    def delete_symbol(
        self,
        file_path: str,
        symbol_name: str,
        symbol_type: Optional[str] = None,
        parent_class: Optional[str] = None,
        dry_run: bool = False,
        keep_decorators: bool = False,
        force: bool = False
    ) -> MutationResult:
        """
        Delete a symbol from file.

        Args:
            file_path: Path to file
            symbol_name: Symbol to delete
            symbol_type: Optional symbol type filter
            parent_class: Optional parent class for methods
            dry_run: If True, validate but don't write
            keep_decorators: If True, keep decorators
            force: If True, bypass reference protection (Phase 12.5)

        Returns:
            MutationResult with status and metrics
        """
        logger.info(f"Deleting symbol '{symbol_name}' from {file_path}")

        # Phase 12: Read original content for diff generation
        original_content = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            logger.warning(f"Failed to read original content for diff: {e}")

        # Locate symbol
        location = self.locator.locate_symbol(
            file_path,
            symbol_name,
            symbol_type,
            parent_class
        )

        if not location:
            return MutationResult(
                success=False,
                operation="delete",
                file_path=file_path,
                symbol_name=symbol_name,
                lines_changed=0,
                lines_total=0,
                write_efficiency=0.0,
                tokens_saved=0,
                validation_passed=False,
                errors=[f"Symbol '{symbol_name}' not found"]
            )

        # Phase 12.5: Symbol Guard - Check for references before deletion
        if not dry_run:
            allowed, guard_error, references = self.guard.check_references(
                symbol_name,
                file_path,
                force
            )

            if not allowed:
                return MutationResult(
                    success=False,
                    operation="delete",
                    file_path=file_path,
                    symbol_name=symbol_name,
                    lines_changed=0,
                    lines_total=0,
                    write_efficiency=0.0,
                    tokens_saved=0,
                    validation_passed=False,
                    errors=[guard_error],
                    warnings=[f"Found {len(references)} reference(s) to this symbol"]
                )

        # Delete symbol
        if not dry_run:
            success, backup_path = self.editor.delete_symbol(location, keep_decorators)
        else:
            success, backup_path = True, None

        # Read modified content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                modified_content = f.read()
        except Exception as e:
            return MutationResult(
                success=False,
                operation="delete",
                file_path=file_path,
                symbol_name=symbol_name,
                lines_changed=0,
                lines_total=0,
                write_efficiency=0.0,
                tokens_saved=0,
                validation_passed=False,
                errors=[f"Failed to read file: {e}"]
            )

        # Validate
        validation_passed, errors, warnings = self.validator.dry_run_validation(
            file_path,
            modified_content,
            location.language
        )

        # Calculate metrics
        lines_total = len(modified_content.split('\n'))
        lines_changed = location.end_line - location.start_line + 1
        write_efficiency = lines_changed / lines_total if lines_total > 0 else 0.0
        tokens_saved = (lines_total - lines_changed) * 4

        # Record metrics
        if self.config.get("ledger_enabled") and not dry_run:
            self.ledger.record_mutation(
                "delete",
                file_path,
                lines_changed,
                lines_total
            )

        # Phase 12: Generate unified diff
        diff = None
        if original_content and not dry_run:
            try:
                diff = self.editor.generate_unified_diff(
                    file_path,
                    original_content,
                    modified_content
                )
            except Exception as e:
                logger.warning(f"Failed to generate diff: {e}")

        return MutationResult(
            success=validation_passed and success,
            operation="delete",
            file_path=file_path,
            symbol_name=symbol_name,
            lines_changed=lines_changed,
            lines_total=lines_total,
            write_efficiency=write_efficiency,
            tokens_saved=tokens_saved,
            validation_passed=validation_passed,
            errors=errors,
            warnings=warnings,
            backup_path=backup_path,
            diff=diff
        )

    def batch_edit(
        self,
        operations: List[EditOperation],
        verify_command: Optional[str] = None,
        preview: bool = False
    ) -> BatchEditResult:
        """
        Execute multiple edit operations atomically.
        Phase 12: Atomic multi-file transactions with rollback on failure.
        Phase 12.5: Preview mode for dry-run visualization.

        Args:
            operations: List of edit operations to perform
            verify_command: Optional shell command to verify changes (e.g., "pytest")
            preview: If True, run in dry-run mode without writing files

        Returns:
            BatchEditResult with all mutation results and rollback status
        """
        logger.info(f"Starting batch edit with {len(operations)} operations")

        results: List[MutationResult] = []
        backup_paths: List[str] = []
        operations_completed = 0
        all_errors: List[str] = []

        # Phase 12.5: Capture original file content for undo
        original_contents: Dict[str, str] = {}
        affected_files = set(op.file_path for op in operations)

        for file_path in affected_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_contents[file_path] = f.read()
            except Exception as e:
                logger.warning(f"Could not capture original content for {file_path}: {e}")

        # Group operations by file to process them in sequence per file
        from collections import defaultdict
        ops_by_file: Dict[str, List[EditOperation]] = defaultdict(list)
        for op in operations:
            ops_by_file[op.file_path].append(op)

        try:
            # Process each file's operations
            for file_path, file_ops in ops_by_file.items():
                logger.info(f"Processing {len(file_ops)} operations for {file_path}")

                # Execute operations for this file
                for op in file_ops:
                    if op.operation == "edit":
                        result = self.edit_symbol(
                            file_path=op.file_path,
                            symbol_name=op.symbol_name,
                            new_code=op.new_code or "",
                            symbol_type=op.symbol_type,
                            parent_class=op.parent_class,
                            dry_run=preview,
                            auto_format=op.auto_format,
                            auto_imports=op.auto_imports,
                            force=op.force
                        )
                    elif op.operation == "insert":
                        result = self.insert_symbol(
                            file_path=op.file_path,
                            parent_symbol=op.parent_symbol or op.symbol_name,
                            new_code=op.new_code or "",
                            after_symbol=op.after_symbol,
                            before_symbol=op.before_symbol,
                            dry_run=preview
                        )
                    elif op.operation == "delete":
                        result = self.delete_symbol(
                            file_path=op.file_path,
                            symbol_name=op.symbol_name,
                            symbol_type=op.symbol_type,
                            parent_class=op.parent_class,
                            dry_run=preview,
                            force=op.force
                        )
                    else:
                        result = MutationResult(
                            success=False,
                            operation=op.operation,
                            file_path=op.file_path,
                            symbol_name=op.symbol_name,
                            lines_changed=0,
                            lines_total=0,
                            write_efficiency=0.0,
                            tokens_saved=0,
                            validation_passed=False,
                            errors=[f"Unknown operation: {op.operation}"]
                        )

                    results.append(result)

                    if not result.success:
                        error_msg = f"Operation failed: {op.operation} on {op.symbol_name} in {op.file_path}"
                        all_errors.append(error_msg)
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)

                    # Track backups for rollback
                    if result.backup_path:
                        backup_paths.append(result.backup_path)

                    operations_completed += 1

            # Phase 12: Run verify command if provided
            if verify_command:
                logger.info(f"Running verification command: {verify_command}")
                import subprocess
                result_code = subprocess.run(
                    verify_command,
                    shell=True,
                    capture_output=True,
                    text=True
                )

                if result_code.returncode != 0:
                    error_msg = f"Verification failed (exit code {result_code.returncode})"
                    all_errors.append(error_msg)
                    all_errors.append(f"Stdout: {result_code.stdout}")
                    all_errors.append(f"Stderr: {result_code.stderr}")
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

            # Phase 12.5: Record transaction for undo (skip in preview mode)
            if not preview:
                reverse_patches = []
                for file_path, original_content in original_contents.items():
                    reverse_patches.append({
                        "file_path": file_path,
                        "original_content": original_content
                    })

                if reverse_patches:
                    try:
                        operation_types = list(set(op.operation for op in operations))
                        operation_type = operation_types[0] if len(operation_types) == 1 else "batch"

                        transaction_id = self.undo.record_transaction(
                            operation_type=operation_type,
                            files=list(affected_files),
                            reverse_patches=reverse_patches,
                            metadata={
                                "operations_count": len(operations),
                                "verify_command": verify_command
                            }
                        )
                        logger.info(f"Recorded undo transaction: {transaction_id}")
                    except Exception as e:
                        logger.warning(f"Failed to record undo transaction: {e}")

            # Success!
            logger.info(f"Batch edit completed successfully: {operations_completed}/{len(operations)}")
            return BatchEditResult(
                success=True,
                operations_completed=operations_completed,
                operations_total=len(operations),
                results=results,
                errors=[],
                rolled_back=False
            )

        except Exception as e:
            # Rollback all changes
            logger.error(f"Batch edit failed, rolling back changes: {e}")
            rollback_success = True

            for backup_path in backup_paths:
                try:
                    # Extract original file path from backup path
                    # Backup format: .cerberus_backups/filename.timestamp.backup
                    import re
                    from pathlib import Path

                    backup_name = Path(backup_path).name
                    # Remove timestamp and .backup extension
                    match = re.match(r"(.+)\.\d{8}_\d{6}\.backup$", backup_name)
                    if match:
                        original_name = match.group(1)
                        # Find the file in the results to get full path
                        for mutation_result in results:
                            if Path(mutation_result.file_path).name == original_name:
                                target_path = mutation_result.file_path
                                success = self.editor._restore_backup(backup_path, target_path)
                                if not success:
                                    rollback_success = False
                                    logger.error(f"Failed to restore backup: {backup_path}")
                                break
                except Exception as rollback_error:
                    rollback_success = False
                    logger.error(f"Failed to rollback {backup_path}: {rollback_error}")

            return BatchEditResult(
                success=False,
                operations_completed=operations_completed,
                operations_total=len(operations),
                results=results,
                errors=all_errors,
                rolled_back=rollback_success
            )
