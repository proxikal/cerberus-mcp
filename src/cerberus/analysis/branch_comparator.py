"""
Cross-branch comparison at symbol granularity.

Maps git diff line ranges to indexed symbols to report which functions,
classes, and methods changed between two branches.
"""

from __future__ import annotations

import ast
import copy
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from cerberus.incremental.git_diff import get_git_root, parse_line_ranges
from cerberus.schemas import CodeSymbol, LineRange
from cerberus.storage import ScanResultAdapter


@dataclass
class SymbolChange:
    """Represents a symbol-level change within a file."""

    name: str
    type: str  # function, class, method
    change_type: str  # modified, added, deleted, renamed
    lines_added: int
    lines_removed: int
    file: str
    line_number: int
    parent_class: Optional[str] = None
    semantically_equivalent: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "name": self.name,
            "type": self.type,
            "change_type": self.change_type,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "file": self.file,
            "line_number": self.line_number,
        }
        if self.parent_class is not None:
            data["parent_class"] = self.parent_class
        if self.semantically_equivalent is not None:
            data["semantically_equivalent"] = self.semantically_equivalent
        return data


@dataclass
class FileChange:
    """Represents a file that changed between branches."""

    file: str
    change_type: str  # modified, added, deleted, renamed
    symbols_changed: List[SymbolChange] = field(default_factory=list)
    old_path: Optional[str] = None
    binary: bool = False

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "file": self.file,
            "change_type": self.change_type,
            "symbols_changed": [s.to_dict() for s in self.symbols_changed],
        }
        if self.old_path:
            data["old_path"] = self.old_path
        if self.binary:
            data["binary"] = True
        return data


@dataclass
class BranchComparisonResult:
    """Result of comparing two branches."""

    status: str
    branch_a: str
    branch_b: str
    focus: Optional[str]
    files_changed: int
    symbols_changed: int
    changes: List[Dict[str, Any]]
    conflicts: List[Dict[str, Any]]
    risk_assessment: str
    token_cost: int
    truncated: bool = False
    warnings: List[str] = field(default_factory=list)
    available_symbols: Optional[int] = None
    available_files: Optional[int] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "status": self.status,
            "branch_a": self.branch_a,
            "branch_b": self.branch_b,
            "focus": self.focus,
            "files_changed": self.files_changed,
            "symbols_changed": self.symbols_changed,
            "changes": self.changes,
            "conflicts": self.conflicts,
            "risk_assessment": self.risk_assessment,
            "token_cost": self.token_cost,
        }
        if self.truncated:
            data["truncated"] = True
        if self.warnings:
            data["warnings"] = self.warnings
        if self.available_symbols is not None:
            data["available_symbols"] = self.available_symbols
        if self.available_files is not None:
            data["available_files"] = self.available_files
        if self.error:
            data["error"] = self.error
        return data


@dataclass
class MultiBranchComparisonResult:
    """Aggregated result for comparing multiple branches to a base branch."""

    status: str
    base_branch: str
    branches: List[str]
    results: List[BranchComparisonResult]
    aggregate_files_changed: int
    aggregate_symbols_changed: int
    branches_with_conflicts: List[str] = field(default_factory=list)
    truncated: bool = False
    token_cost: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "base_branch": self.base_branch,
            "branches": self.branches,
            "aggregate_files_changed": self.aggregate_files_changed,
            "aggregate_symbols_changed": self.aggregate_symbols_changed,
            "branches_with_conflicts": self.branches_with_conflicts,
            "truncated": self.truncated,
            "token_cost": self.token_cost,
            "errors": self.errors,
            "results": [r.to_dict() for r in self.results],
        }


class BranchComparator:
    """
    Compare two git branches and map diff ranges to symbols.

    Relies on an up-to-date Cerberus index for branch_b to map line ranges
    to symbol definitions.
    """

    def __init__(self, project_root: Path, index: Any):
        self.project_root = project_root
        self.index = index
        self.git_root = get_git_root(project_root) or project_root
        self._symbol_cache = self._build_symbol_cache()
        self._last_compare_branches: Tuple[Optional[str], Optional[str]] = (None, None)

    def compare(
        self,
        branch_a: str,
        branch_b: str,
        focus: Optional[str] = None,
        include_conflicts: bool = True,
    ) -> BranchComparisonResult:
        """
        Compare two branches at the symbol level.

        Args:
            branch_a: Base branch (e.g., main)
            branch_b: Compare branch (e.g., feature/auth)
            focus: Optional substring filter across paths and symbols
            include_conflicts: Whether to detect potential conflicts
        """
        if not self.git_root:
            return BranchComparisonResult(
                status="error",
                branch_a=branch_a,
                branch_b=branch_b,
                focus=focus,
                files_changed=0,
                symbols_changed=0,
                changes=[],
                conflicts=[],
                risk_assessment="unknown",
                token_cost=0,
                error="Not a git repository",
            )

        if not self._branch_exists(branch_a) or not self._branch_exists(branch_b):
            return BranchComparisonResult(
                status="error",
                branch_a=branch_a,
                branch_b=branch_b,
                focus=focus,
                files_changed=0,
                symbols_changed=0,
                changes=[],
                conflicts=[],
                risk_assessment="unknown",
                token_cost=0,
                error="One or both branches do not exist",
            )

        warnings: List[str] = []

        base = self._get_merge_base(branch_a, branch_b)
        if not base:
            warnings.append("Could not determine merge-base; diff may be inaccurate.")

        self._check_index_sync(branch_b, warnings)

        diff_stats = self._get_diff_stats(branch_a, branch_b)
        if diff_stats is None:
            return BranchComparisonResult(
                status="error",
                branch_a=branch_a,
                branch_b=branch_b,
                focus=focus,
                files_changed=0,
                symbols_changed=0,
                changes=[],
                conflicts=[],
                risk_assessment="unknown",
                token_cost=0,
                error="Failed to compute git diff",
                warnings=warnings,
            )

        changed_files = self._get_changed_files_with_ranges(branch_a, branch_b, diff_stats)
        if not changed_files:
            return BranchComparisonResult(
                status="success",
                branch_a=branch_a,
                branch_b=branch_b,
                focus=focus,
                files_changed=0,
                symbols_changed=0,
                changes=[],
                conflicts=[],
                risk_assessment="low",
                token_cost=0,
                warnings=warnings,
            )

        self._last_compare_branches = (branch_a, branch_b)

        mapped_changes = self._map_changes_to_symbols(changed_files, branch_a, branch_b)

        available_symbols = sum(len(fc.symbols_changed) for fc in mapped_changes)
        available_files = len(mapped_changes)

        if focus:
            mapped_changes = self._apply_focus_filter(mapped_changes, focus)

        mapped_changes, truncated = self._truncate_changes(mapped_changes, limit=50)

        conflicts = self._detect_conflicts(branch_a, branch_b) if include_conflicts else []
        risk = self._assess_risk(mapped_changes)

        token_cost = self._estimate_token_cost([fc.to_dict() for fc in mapped_changes])

        return BranchComparisonResult(
            status="success",
            branch_a=branch_a,
            branch_b=branch_b,
            focus=focus,
            files_changed=len(mapped_changes),
            symbols_changed=sum(len(fc.symbols_changed) for fc in mapped_changes),
            changes=[fc.to_dict() for fc in mapped_changes],
            conflicts=conflicts,
            risk_assessment=risk,
            token_cost=token_cost,
            truncated=truncated,
            warnings=warnings,
            available_symbols=available_symbols,
            available_files=available_files,
        )

    # ------------------------------------------------------------------
    # Git helpers
    # ------------------------------------------------------------------
    def _run_git(self, args: List[str]) -> Tuple[int, str, str]:
        """Run a git command in the repo."""
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=str(self.git_root),
                capture_output=True,
                text=True,
                timeout=20,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"Git command timed out: git {' '.join(args)}")
            return 1, "", "timeout"
        except Exception as exc:
            logger.error(f"Git command failed: git {' '.join(args)} ({exc})")
            return 1, "", str(exc)

    def _branch_exists(self, branch: str) -> bool:
        """Check whether a branch exists locally or remotely."""
        code, _, _ = self._run_git(["rev-parse", "--verify", branch])
        return code == 0

    def _get_merge_base(self, branch_a: str, branch_b: str) -> Optional[str]:
        """Get merge base between two branches."""
        code, out, _ = self._run_git(["merge-base", branch_a, branch_b])
        return out if code == 0 else None

    def _get_diff_stats(self, branch_a: str, branch_b: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get file-level diff stats via git.

        Returns list of {file, change_type, old_path?}
        """
        code, out, err = self._run_git(
            ["diff", "--name-status", "--find-renames=20%", f"{branch_a}...{branch_b}"]
        )
        if code != 0:
            logger.error(f"git diff --name-status failed: {err}")
            return None

        stats: List[Dict[str, Any]] = []
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            status = parts[0]

            if status.startswith("R"):
                if len(parts) < 3:
                    continue
                old_path, new_path = parts[1], parts[2]
                stats.append({"file": new_path, "change_type": "renamed", "old_path": old_path})
            elif status.startswith("A"):
                stats.append({"file": parts[1], "change_type": "added"})
            elif status.startswith("D"):
                stats.append({"file": parts[1], "change_type": "deleted"})
            elif status.startswith("M"):
                stats.append({"file": parts[1], "change_type": "modified"})
        return stats

    def _get_changed_files_with_ranges(
        self,
        branch_a: str,
        branch_b: str,
        diff_stats: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """For each changed file, fetch line ranges and metadata."""
        files: List[Dict[str, Any]] = []

        for entry in diff_stats:
            path = entry["file"]
            change_type = entry["change_type"]
            old_path = entry.get("old_path")

            if change_type == "deleted":
                files.append(
                    {
                        "file": path,
                        "change_type": change_type,
                        "old_path": old_path,
                        "ranges": [],
                        "additions": 0,
                        "deletions": 0,
                        "binary": False,
                    }
                )
                continue

            code, diff_out, _ = self._run_git(
                ["diff", "--unified=0", "--find-renames=20%", f"{branch_a}...{branch_b}", "--", path]
            )
            if code != 0:
                logger.warning(f"Failed to diff file {path}")
                continue

            binary = any(
                line.startswith("Binary files") or line.startswith("GIT binary patch")
                for line in diff_out.splitlines()
            )
            ranges = parse_line_ranges(diff_out) if not binary else []
            additions, deletions = self._count_line_changes(diff_out)

            files.append(
                {
                    "file": path,
                    "change_type": change_type,
                    "old_path": old_path,
                    "ranges": ranges,
                    "additions": additions,
                    "deletions": deletions,
                    "binary": binary,
                }
            )

        return files

    def _detect_conflicts(self, branch_a: str, branch_b: str) -> List[Dict[str, Any]]:
        """
        Detect potential conflicts by checking files changed on both branches
        since their merge base. Includes overlap detection on changed ranges.
        """
        base = self._get_merge_base(branch_a, branch_b)
        if not base:
            return []

        files_a = self._files_changed_since(base, branch_a)
        files_b = self._files_changed_since(base, branch_b)

        conflicts: List[Dict[str, Any]] = []
        overlapping_files = sorted(files_a.intersection(files_b))

        for path in overlapping_files:
            ranges_a = self._file_ranges_since(base, branch_a, path)
            ranges_b = self._file_ranges_since(base, branch_b, path)

            overlap_pairs = self._find_overlaps(ranges_a, ranges_b)
            if overlap_pairs:
                conflicts.append(
                    {
                        "file": path,
                        "reason": "overlapping_changes",
                        "branch_a_ranges": [self._serialize_range(r) for r in ranges_a],
                        "branch_b_ranges": [self._serialize_range(r) for r in ranges_b],
                        "overlaps": [
                            {
                                "branch_a": self._serialize_range(a),
                                "branch_b": self._serialize_range(b),
                            }
                            for a, b in overlap_pairs
                        ],
                    }
                )
                continue

            conflicts.append(
                {
                    "file": path,
                    "reason": "changed_in_both_branches",
                }
            )
        return conflicts

    def _files_changed_since(self, base: str, branch: str) -> set:
        """Files changed from base..branch."""
        code, out, _ = self._run_git(["diff", "--name-only", f"{base}..{branch}"])
        if code != 0:
            return set()
        return {line for line in out.splitlines() if line.strip()}

    def _file_ranges_since(self, base: str, branch: str, path: str) -> List[LineRange]:
        """
        Get line ranges changed in a file since base..branch.
        """
        code, diff_out, _ = self._run_git(
            ["diff", "--unified=0", "--find-renames=20%", f"{base}..{branch}", "--", path]
        )
        if code != 0 or "Binary files" in diff_out:
            return []
        return parse_line_ranges(diff_out)

    @staticmethod
    def _find_overlaps(ranges_a: List[LineRange], ranges_b: List[LineRange]) -> List[Tuple[LineRange, LineRange]]:
        """Find overlapping line ranges between two sets."""
        overlaps: List[Tuple[LineRange, LineRange]] = []
        for ra in ranges_a:
            for rb in ranges_b:
                if BranchComparator._ranges_overlap_generic(ra.start, ra.end, rb.start, rb.end):
                    overlaps.append((ra, rb))
        return overlaps

    @staticmethod
    def _serialize_range(range_: LineRange) -> Dict[str, Any]:
        """Serialize LineRange for conflict output."""
        return {
            "start": range_.start,
            "end": range_.end,
            "change_type": range_.change_type,
        }

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------
    def _map_changes_to_symbols(
        self,
        changed_files: List[Dict[str, Any]],
        branch_a: str,
        branch_b: str,
    ) -> List[FileChange]:
        """Map line ranges to symbols using the index."""
        results: List[FileChange] = []

        for entry in changed_files:
            path = entry["file"]
            change_type = entry["change_type"]
            old_path = entry.get("old_path")
            ranges: List[LineRange] = entry.get("ranges", [])
            binary = entry.get("binary", False)

            relative_path = self._relativize(path)
            symbols = self._symbols_for_file(path)

            symbol_changes: List[SymbolChange] = []
            if binary:
                symbol_changes = []
            elif change_type == "deleted":
                # Can't map deleted symbols without base index; represent file-level change only
                symbol_changes = []
            elif change_type == "renamed" and not ranges:
                # Pure rename - mark all symbols as renamed
                for symbol in symbols:
                    symbol_changes.append(
                        SymbolChange(
                            name=symbol.name,
                            type=symbol.type,
                            change_type="renamed",
                            lines_added=0,
                            lines_removed=0,
                            file=relative_path,
                            line_number=symbol.start_line,
                            parent_class=symbol.parent_class,
                        )
                    )
            else:
                for symbol in symbols:
                    change = self._build_symbol_change(symbol, ranges, change_type, relative_path)
                    if change:
                        symbol_changes.append(change)

            # If added file and no symbol captured, include placeholders based on symbols
            if change_type == "added" and not symbol_changes and symbols:
                for symbol in symbols:
                    symbol_changes.append(
                        SymbolChange(
                            name=symbol.name,
                            type=symbol.type,
                            change_type="added",
                            lines_added=max(0, symbol.end_line - symbol.start_line + 1),
                            lines_removed=0,
                            file=relative_path,
                            line_number=symbol.start_line,
                            parent_class=symbol.parent_class,
                        )
                    )

            if change_type in {"modified", "renamed"} and symbol_changes and ranges:
                self._annotate_semantic_equivalence(
                    symbol_changes,
                    branch_a=branch_a,
                    branch_b=branch_b,
                    path=path,
                    old_path=old_path,
                )

            # Deduplicate identical symbol entries (index may contain duplicates)
            deduped_symbols = self._dedupe_symbol_changes(symbol_changes)

            results.append(
                FileChange(
                    file=relative_path,
                    change_type=change_type,
                    symbols_changed=deduped_symbols,
                    old_path=self._relativize(old_path) if old_path else None,
                    binary=binary,
                )
            )

        return results

    def _apply_focus_filter(self, changes: List[FileChange], focus: str) -> List[FileChange]:
        """Filter changes by substring across file paths and symbols."""
        focus_lower = focus.lower()
        filtered: List[FileChange] = []

        for change in changes:
            file_match = focus_lower in change.file.lower() or (
                change.old_path and focus_lower in change.old_path.lower()
            )
            if file_match:
                filtered.append(change)
                continue

            matched_symbols = [
                s for s in change.symbols_changed if focus_lower in s.name.lower()
            ]
            if matched_symbols:
                filtered.append(
                    FileChange(
                        file=change.file,
                        change_type=change.change_type,
                        symbols_changed=matched_symbols,
                        old_path=change.old_path,
                        binary=change.binary,
                    )
                )

        return filtered

    def _truncate_changes(
        self,
        changes: List[FileChange],
        limit: int = 50,
    ) -> Tuple[List[FileChange], bool]:
        """Limit to most significant symbol changes."""
        total_symbols = sum(len(c.symbols_changed) for c in changes)
        if total_symbols <= limit:
            return changes, False

        truncated: List[FileChange] = []
        remaining = limit

        for change in changes:
            if remaining <= 0:
                break

            symbol_count = len(change.symbols_changed)
            if symbol_count == 0:
                truncated.append(change)
                continue

            if symbol_count <= remaining:
                truncated.append(change)
                remaining -= symbol_count
            else:
                truncated.append(
                    FileChange(
                        file=change.file,
                        change_type=change.change_type,
                        symbols_changed=change.symbols_changed[:remaining],
                        old_path=change.old_path,
                        binary=change.binary,
                    )
                )
                remaining = 0

        return truncated, True

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _build_symbol_cache(self) -> Dict[str, List[CodeSymbol]]:
        """Create a lookup of file path -> symbols."""
        cache: Dict[str, List[CodeSymbol]] = {}

        symbols = getattr(self.index, "symbols", []) or []
        for symbol in symbols:
            normalized = str(Path(symbol.file_path).resolve())
            cache.setdefault(normalized, []).append(symbol)

        for symbol_list in cache.values():
            symbol_list.sort(key=lambda s: (s.start_line, s.name))

        return cache

    def _symbols_for_file(self, file_path: str) -> List[CodeSymbol]:
        """Return symbols for a given file path (relative)."""
        normalized = str((Path(self.project_root) / file_path).resolve())
        return self._symbol_cache.get(normalized, [])

    def _relativize(self, path: Optional[str]) -> str:
        """Convert absolute or git path to path relative to repo root."""
        if not path:
            return ""
        try:
            return str(Path(path).relative_to(self.git_root))
        except Exception:
            try:
                return str(Path(path).resolve().relative_to(self.git_root))
            except Exception:
                return path.replace("a/", "").replace("b/", "")

    def _build_symbol_change(
        self,
        symbol: CodeSymbol,
        ranges: List[LineRange],
        file_change_type: str,
        relative_path: str,
    ) -> Optional[SymbolChange]:
        """Build SymbolChange for overlapping ranges."""
        lines_added = 0
        lines_removed = 0

        for range_ in ranges:
            if not self._ranges_overlap(symbol.start_line, symbol.end_line, range_):
                continue

            overlap = min(symbol.end_line, range_.end) - max(symbol.start_line, range_.start) + 1

            if range_.change_type == "added":
                lines_added += overlap
            elif range_.change_type == "deleted":
                lines_removed += overlap
            else:
                # Modified counts toward both added and removed for risk approximation
                lines_added += overlap
                lines_removed += overlap

        if lines_added == 0 and lines_removed == 0 and file_change_type == "modified":
            return None

        if file_change_type in {"added", "deleted", "renamed"}:
            change_type = file_change_type
        elif lines_removed == 0 and lines_added > 0:
            change_type = "added"
        elif lines_added == 0 and lines_removed > 0:
            change_type = "deleted"
        else:
            change_type = "modified"

        return SymbolChange(
            name=symbol.name,
            type=symbol.type,
            change_type=change_type,
            lines_added=lines_added,
            lines_removed=lines_removed,
            file=relative_path,
            line_number=symbol.start_line,
            parent_class=symbol.parent_class,
        )

    @staticmethod
    def _ranges_overlap(symbol_start: int, symbol_end: int, changed_range: LineRange) -> bool:
        """Check if symbol range overlaps with changed range."""
        return symbol_start <= changed_range.end and changed_range.start <= symbol_end

    @staticmethod
    def _ranges_overlap_generic(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
        """Check overlap between two integer ranges."""
        return a_start <= b_end and b_start <= a_end

    # ------------------------------------------------------------------
    # Semantic equivalence (best-effort AST comparison)
    # ------------------------------------------------------------------
    def _annotate_semantic_equivalence(
        self,
        symbol_changes: List[SymbolChange],
        branch_a: str,
        branch_b: str,
        path: str,
        old_path: Optional[str],
    ) -> None:
        """Set semantically_equivalent flag for overlapping modified symbols."""
        for change in symbol_changes:
            change.semantically_equivalent = self._is_semantically_equivalent(
                change, branch_a, branch_b, path, old_path
            )

    def _is_semantically_equivalent(
        self,
        change: SymbolChange,
        branch_a: str,
        branch_b: str,
        path: str,
        old_path: Optional[str],
    ) -> Optional[bool]:
        """
        Compare symbol ASTs between branches to see if logic is equivalent.

        Returns:
            True if ASTs match (ignoring docstrings), False if they differ,
            None if comparison not possible.
        """
        path_a = old_path or path
        code_a = self._get_file_content(branch_a, path_a)
        code_b = self._get_file_content(branch_b, path)
        if code_a is None or code_b is None:
            return None

        node_a = self._extract_symbol_node(code_a, change.name, change.type, change.parent_class)
        node_b = self._extract_symbol_node(code_b, change.name, change.type, change.parent_class)
        if node_a is None or node_b is None:
            return None

        norm_a = self._normalize_node(node_a)
        norm_b = self._normalize_node(node_b)
        return norm_a == norm_b

    def _get_file_content(self, branch: str, path: str) -> Optional[str]:
        """Return file content from a branch via git show."""
        code, out, err = self._run_git(["show", f"{branch}:{path}"])
        if code != 0:
            logger.debug(f"git show failed for {branch}:{path}: {err}")
            return None
        return out

    def _extract_symbol_node(
        self,
        code: str,
        name: str,
        symbol_type: str,
        parent_class: Optional[str],
    ) -> Optional[ast.AST]:
        """Extract AST node for a symbol by name (and parent_class for methods)."""
        try:
            module = ast.parse(code)
        except SyntaxError:
            return None

        if symbol_type == "class":
            for node in module.body:
                if isinstance(node, ast.ClassDef) and node.name == name:
                    return node
            return None

        if symbol_type == "function":
            for node in module.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                    return node
            return None

        if symbol_type == "method":
            for node in module.body:
                if isinstance(node, ast.ClassDef) and (
                    parent_class is None or node.name == parent_class
                ):
                    for child in node.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == name:
                            return child
            return None

        # Fallback: search by name anywhere
        for node in ast.walk(module):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
                return node
        return None

    def _normalize_node(self, node: ast.AST) -> str:
        """Normalize node by stripping docstrings and attributes."""
        clone = copy.deepcopy(node)
        self._strip_docstrings(clone)
        return ast.dump(clone, include_attributes=False)

    def _strip_docstrings(self, node: ast.AST) -> None:
        """Remove leading docstring expressions from function/class nodes recursively."""
        def strip_in_body(body: List[ast.stmt]) -> List[ast.stmt]:
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                return body[1:]
            return body

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            node.body = strip_in_body(node.body)
            for child in node.body:
                self._strip_docstrings(child)
        elif hasattr(node, "body") and isinstance(getattr(node, "body"), list):
            for child in getattr(node, "body"):
                self._strip_docstrings(child)

    def _dedupe_symbol_changes(self, symbols: List[SymbolChange]) -> List[SymbolChange]:
        """Remove duplicate SymbolChange entries by (name, line_number, change_type)."""
        seen = set()
        deduped: List[SymbolChange] = []
        for sym in symbols:
            key = (sym.name, sym.line_number, sym.change_type, sym.parent_class)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(sym)
        return deduped

    @staticmethod
    def _count_line_changes(diff_output: str) -> Tuple[int, int]:
        """Count added/removed lines from diff output (excluding headers)."""
        added = 0
        removed = 0
        for line in diff_output.splitlines():
            if line.startswith("+++ ") or line.startswith("--- "):
                continue
            if line.startswith("+"):
                added += 1
            elif line.startswith("-"):
                removed += 1
        return added, removed

    @staticmethod
    def _assess_risk(changes: List[FileChange]) -> str:
        """Risk assessment based on symbol counts and critical paths."""
        # Flatten symbol changes
        all_symbols = [s for change in changes for s in change.symbols_changed]
        total_symbols = len(all_symbols)

        critical_patterns = ["__init__", "main", "app", "server", "core"]
        has_critical = any(
            any(pattern in change.file for pattern in critical_patterns)
            for change in changes
        )

        if total_symbols > 50 or (has_critical and total_symbols > 20):
            return "critical"
        if total_symbols > 20 or has_critical:
            return "high"
        if total_symbols > 5:
            return "medium"
        return "low"

    @staticmethod
    def _estimate_token_cost(data: Any) -> int:
        """Approximate token cost for JSON payload."""
        try:
            payload = json.dumps(data)
        except Exception:
            return 0
        return len(payload) // 4  # ~4 chars per token heuristic

    def _check_index_sync(self, branch_b: str, warnings: List[str]) -> None:
        """Warn if index git commit differs from branch_b tip."""
        index_commit = None
        try:
            if isinstance(self.index, ScanResultAdapter):
                index_commit = self.index._store.get_metadata("git_commit")
            else:
                index_commit = getattr(self.index, "metadata", {}).get("git_commit")
        except Exception:
            index_commit = None

        code, commit, _ = self._run_git(["rev-parse", branch_b])
        branch_commit = commit if code == 0 else None

        if index_commit and branch_commit and index_commit != branch_commit:
            warnings.append(
                f"Index git commit {index_commit[:7]} differs from {branch_b} ({branch_commit[:7]})."
            )


class MultiBranchComparator:
    """
    Compare a base branch against multiple target branches.

    Uses BranchComparator for per-branch analysis and aggregates results.
    """

    def __init__(self, project_root: Path, index: Any):
        self.project_root = project_root
        self.index = index
        self.single = BranchComparator(project_root, index)

    def compare_many(
        self,
        base_branch: str,
        branches: List[str],
        focus: Optional[str] = None,
        include_conflicts: bool = True,
    ) -> MultiBranchComparisonResult:
        results: List[BranchComparisonResult] = []
        errors: List[str] = []
        conflicts_branches: List[str] = []
        aggregate_files: set = set()
        aggregate_symbols: int = 0
        total_tokens = 0
        truncated_any = False

        for branch in branches:
            result = self.single.compare(base_branch, branch, focus, include_conflicts)
            results.append(result)
            if result.status != "success":
                errors.append(f"{branch}: {result.error or 'unknown error'}")
            if result.conflicts:
                conflicts_branches.append(branch)
            aggregate_files.update(change["file"] for change in result.changes)
            aggregate_symbols += result.symbols_changed
            total_tokens += result.token_cost
            truncated_any = truncated_any or result.truncated

        status = "success" if not errors else "partial"

        return MultiBranchComparisonResult(
            status=status,
            base_branch=base_branch,
            branches=branches,
            results=results,
            aggregate_files_changed=len(aggregate_files),
            aggregate_symbols_changed=aggregate_symbols,
            branches_with_conflicts=conflicts_branches,
            truncated=truncated_any,
            token_cost=total_tokens,
            errors=errors,
        )

    @staticmethod
    def _count_line_changes(diff_output: str) -> Tuple[int, int]:
        """Count added/removed lines from diff output (excluding headers)."""
        added = 0
        removed = 0
        for line in diff_output.splitlines():
            if line.startswith("+++ ") or line.startswith("--- "):
                continue
            if line.startswith("+"):
                added += 1
            elif line.startswith("-"):
                removed += 1
        return added, removed

    @staticmethod
    def _assess_risk(changes: List[FileChange]) -> str:
        """Risk assessment based on symbol counts and critical paths."""
        # Flatten symbol changes
        all_symbols = [s for change in changes for s in change.symbols_changed]
        total_symbols = len(all_symbols)

        critical_patterns = ["__init__", "main", "app", "server", "core"]
        has_critical = any(
            any(pattern in change.file for pattern in critical_patterns)
            for change in changes
        )

        if total_symbols > 50 or (has_critical and total_symbols > 20):
            return "critical"
        if total_symbols > 20 or has_critical:
            return "high"
        if total_symbols > 5:
            return "medium"
        return "low"

    @staticmethod
    def _estimate_token_cost(data: Any) -> int:
        """Approximate token cost for JSON payload."""
        try:
            payload = json.dumps(data)
        except Exception:
            return 0
        return len(payload) // 4  # ~4 chars per token heuristic

    def _check_index_sync(self, branch_b: str, warnings: List[str]) -> None:
        """Warn if index git commit differs from branch_b tip."""
        index_commit = None
        try:
            if isinstance(self.index, ScanResultAdapter):
                index_commit = self.index._store.get_metadata("git_commit")
            else:
                index_commit = getattr(self.index, "metadata", {}).get("git_commit")
        except Exception:
            index_commit = None

        code, commit, _ = self._run_git(["rev-parse", branch_b])
        branch_commit = commit if code == 0 else None

        if index_commit and branch_commit and index_commit != branch_commit:
            warnings.append(
                f"Index git commit {index_commit[:7]} differs from {branch_b} ({branch_commit[:7]})."
            )
