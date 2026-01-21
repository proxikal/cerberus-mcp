# Cross-Branch Comparison Design

**Date:** 2026-01-20
**Status:** Approved
**Phase:** 4
**Estimated Implementation:** 3-4 days

---

## Overview

Cross-Branch Comparison provides symbol-level diff analysis between git branches. Instead of showing raw line changes, it identifies which functions, classes, and methods were modified, added, or deleted. This enables AI agents to quickly understand feature branch changes before merging.

**Primary Use Case:** Review feature branch changes at the symbol level to understand what actually changed in the code.

---

## API Design

### Primary Interface

```python
cerberus.diff_branches(
    branch_a: str,                    # Base branch (e.g., "main")
    branch_b: str,                    # Compare branch (e.g., "feature/auth")
    focus: Optional[str] = None,      # Filter by path/symbol substring
    include_conflicts: bool = True    # Detect potential conflicts
) -> BranchComparisonResult
```

### Return Structure

```json
{
    "status": "success",
    "branch_a": "main",
    "branch_b": "feature/auth",
    "focus": "authentication",
    "files_changed": 12,
    "symbols_changed": 27,
    "changes": [
        {
            "file": "auth/handlers.py",
            "change_type": "modified",
            "symbols_changed": [
                {
                    "name": "login",
                    "type": "function",
                    "change_type": "modified",
                    "lines_added": 15,
                    "lines_removed": 8
                }
            ]
        }
    ],
    "conflicts": [],
    "risk_assessment": "medium",
    "token_cost": 450
}
```

### Key Features

- **Optional focus parameter:** Show all changes by default, filter when focus provided
- **Substring matching:** Focus matches both file paths and symbol names
- **Token-efficient:** Target <2000 tokens for typical feature branches
- **Symbol-level granularity:** See which functions/classes changed, not just files

---

## Architecture

### Implementation Strategy

**Approach:** Git diff + symbol mapping (leverages existing tools)

```python
class BranchComparator:
    def __init__(self, project_root: Path, index_manager):
        self.project_root = project_root
        self.index_manager = index_manager

    def compare(self, branch_a: str, branch_b: str, focus: Optional[str] = None):
        # Step 1: Get git diff summary
        diff_stats = self._get_diff_stats(branch_a, branch_b)

        # Step 2: For each changed file, get line ranges
        changed_files = self._get_changed_files_with_ranges(branch_a, branch_b)

        # Step 3: Map line ranges to symbols using index
        symbol_changes = self._map_changes_to_symbols(changed_files)

        # Step 4: Apply focus filter if provided
        if focus:
            symbol_changes = self._apply_focus_filter(symbol_changes, focus)

        # Step 5: Calculate risk assessment
        risk = self._assess_risk(symbol_changes)

        return BranchComparisonResult(...)
```

### Git Commands

1. `git diff --name-status branch_a...branch_b` → Changed files and types
2. `git diff --unified=0 branch_a...branch_b -- <file>` → Exact line ranges
3. `git merge-base branch_a branch_b` → Common ancestor for accurate diff
4. `git diff --find-renames` → Detect file renames

### Symbol Mapping

- Use existing Cerberus index (must be current with branch_b)
- For each changed line range, query index for overlapping symbols
- Mark symbol as "modified" if any lines changed within it
- Mark as "added"/"deleted" if entire symbol is new/removed

### Token Efficiency

- Limit to 50 most significant changes by default
- Group small changes within same file
- Omit trivial changes (whitespace-only, comment-only)
- Add "truncated" flag if more changes exist
- Target: 400-800 tokens for typical feature branch

---

## Data Structures

```python
@dataclass
class SymbolChange:
    name: str
    type: str  # "function", "class", "method"
    change_type: str  # "modified", "added", "deleted", "renamed"
    lines_added: int
    lines_removed: int
    file: str
    line_number: int

@dataclass
class FileChange:
    file: str
    change_type: str  # "modified", "added", "deleted", "renamed"
    symbols_changed: List[SymbolChange]
    old_path: Optional[str] = None  # For renames

@dataclass
class BranchComparisonResult:
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "branch_a": self.branch_a,
            "branch_b": self.branch_b,
            "focus": self.focus,
            "files_changed": self.files_changed,
            "symbols_changed": self.symbols_changed,
            "changes": self.changes,
            "conflicts": self.conflicts,
            "risk_assessment": self.risk_assessment,
            "token_cost": self.token_cost
        }
```

---

## Edge Cases

| Case | Handling |
|------|----------|
| **File renames** | Detect via `--find-renames`, preserve symbol continuity |
| **Branch doesn't exist** | Return `status="error"` with helpful message |
| **Index out of sync** | Warn if index is stale relative to branch_b |
| **Binary files** | Skip with note in summary |
| **No changes** | Return empty changes list, `status="success"` |
| **Focus yields nothing** | Return empty but indicate total changes available |
| **Very large diffs** | Truncate to top 50 changes, set `truncated=true` |

---

## Risk Assessment

Risk levels based on change scope and impact:

```python
def _assess_risk(self, changes):
    total_symbols = len(changes)

    # Check for critical modules
    critical_patterns = ['__init__', 'main', 'app', 'server', 'core']
    has_critical = any(
        any(pattern in change.file for pattern in critical_patterns)
        for change in changes
    )

    # Risk levels
    if total_symbols > 50 or has_critical and total_symbols > 20:
        return "critical"
    elif total_symbols > 20 or has_critical:
        return "high"
    elif total_symbols > 5:
        return "medium"
    else:
        return "low"
```

---

## MCP Tool Integration

### Tool Registration

Add to `/src/cerberus/mcp/tools/analysis.py`:

```python
@mcp.tool()
def diff_branches(
    branch_a: str,
    branch_b: str,
    focus: str | None = None,
    include_conflicts: bool = True
) -> dict:
    """
    Compare code changes between two git branches at symbol level.

    Returns symbol-level changes (which functions/classes modified) rather
    than raw line diffs. Useful for reviewing feature branches before merge.

    Args:
        branch_a: Base branch (e.g., "main")
        branch_b: Compare branch (e.g., "feature/auth")
        focus: Optional filter - matches paths and symbol names (e.g., "auth")
        include_conflicts: Whether to detect potential conflicts

    Returns:
        Dict with changes, risk assessment, and token cost

    Example:
        >>> diff_branches("main", "feature/auth", focus="authentication")
        {
            "status": "success",
            "symbols_changed": 12,
            "changes": [...],
            "risk_assessment": "medium"
        }
    """
    try:
        index = get_index_manager().get_index()
        comparator = BranchComparator(Path.cwd(), index)
        result = comparator.compare(branch_a, branch_b, focus, include_conflicts)
        return result.to_dict()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
```

### File Structure

```
src/cerberus/
├── analysis/
│   ├── circular_dependency_detector.py  # Existing
│   └── branch_comparator.py             # NEW - Core implementation
├── mcp/tools/
│   └── analysis.py                      # Add diff_branches tool
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_branch_comparator.py

def test_symbol_mapping():
    """Test that line ranges correctly map to symbols."""

def test_focus_filtering():
    """Test focus parameter filters paths and symbols."""

def test_risk_assessment():
    """Test risk levels are calculated correctly."""

def test_file_renames():
    """Test renamed files are handled correctly."""
```

### Integration Tests

```python
def test_real_branch_comparison():
    """Use Cerberus repo itself to test real branch diffs."""

def test_token_efficiency():
    """Verify output stays under 2000 tokens for typical branches."""
```

### Dog-Fooding

- Test on actual Cerberus feature branches during development
- Use on Phase 4 implementation branch
- Measure token costs on real diffs

---

## Success Criteria

- ✅ Accurately maps line changes to symbols (>90% accuracy)
- ✅ Token-efficient output (<2000 tokens for 20+ file changes)
- ✅ Handles edge cases gracefully (renames, binary files, missing branches)
- ✅ Focus filtering works intuitively (substring matching)
- ✅ Risk assessment is helpful and accurate
- ✅ Works with Cerberus index infrastructure
- ✅ Performance: <2 seconds for typical feature branch comparison

---

## Implementation Timeline

### Day 1: Core Implementation
- Create `BranchComparator` class
- Implement git command integration
- Basic diff stats and file change detection

### Day 2: Symbol Mapping
- Implement line-range to symbol mapping
- Add focus filtering logic
- Handle file renames and moves

### Day 3: MCP Integration
- Add MCP tool registration
- Implement edge case handling
- Add risk assessment logic

### Day 4: Testing & Refinement
- Write unit and integration tests
- Dog-food on real branches
- Measure and optimize token efficiency
- Update documentation

---

## Future Enhancements

**Not in scope for initial implementation:**

1. **Conflict prediction:** Detect overlapping changes between branches
2. **Semantic diff:** Understand if changes are functionally equivalent
3. **Multi-branch comparison:** Compare more than 2 branches simultaneously
4. **Change impact analysis:** Integrate with existing call graph to show downstream effects
5. **Historical analysis:** Track how symbols evolved across multiple branch comparisons

These can be added in future iterations based on usage patterns.

---

## Dependencies

- **Existing:** Cerberus index, git, AST parsing infrastructure
- **New:** Git command execution utilities (subprocess)
- **Python:** 3.10+ (for match statements and type hints)

---

## Notes

- Index must be current with branch_b for accurate symbol mapping
- Uses three-dot diff syntax (`branch_a...branch_b`) for proper comparison
- Gracefully degrades if index unavailable (returns file-level changes only)
- Complements existing Cerberus tools (doesn't duplicate git's raw diff capabilities)
