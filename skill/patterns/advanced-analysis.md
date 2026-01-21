# PROTOCOL: ADVANCED ANALYSIS

**OBJECTIVE:** Deep code analysis for refactoring, review, and architecture validation.

## MCP TOOLS

### 1. `analyze_impact`
**Use:** Find what breaks if you change a symbol.
**Cost:** Medium (~1,000-2,000 tokens).
**Params:**
- `symbol_name`: Symbol to analyze
- `file_path`: Optional file path to disambiguate

**Examples:**
```
analyze_impact(symbol_name="processPayment")
analyze_impact(symbol_name="authenticate", file_path="src/auth/service.py")
```

**Returns:** List of impacted symbols with locations, types, and relationships.

### 2. `test_coverage`
**Use:** Find which tests cover a symbol.
**Cost:** Medium (~800-1,500 tokens).
**Params:**
- `symbol_name`: Symbol to check
- `file_path`: Optional file path to disambiguate

**Examples:**
```
test_coverage(symbol_name="calculateTotal")
test_coverage(symbol_name="User", file_path="src/models/user.py")
```

**Returns:** Test files, test names, and coverage type (direct/indirect).

### 3. `find_circular_deps`
**Use:** Detect circular import dependencies.
**Cost:** Low-Medium (~500-1,000 tokens).
**Params:**
- `path`: Path to analyze (file or directory)

**Examples:**
```
find_circular_deps(path="src/")
find_circular_deps(path="src/services/")
```

**Returns:** List of circular dependency chains with file paths.

### 4. `diff_branches`
**Use:** Symbol-level diff between two git branches.
**Cost:** Medium-High (depends on changes).
**Params:**
- `branch_a`: First branch (e.g., "main")
- `branch_b`: Second branch (e.g., "feature/auth")
- `file_pattern`: Optional glob pattern to filter files

**Examples:**
```
diff_branches(branch_a="main", branch_b="feature/auth")
diff_branches(branch_a="main", branch_b="develop", file_pattern="src/**/*.py")
```

**Returns:** Added, modified, deleted symbols with change types.

### 5. `diff_branches_multi`
**Use:** Compare multiple feature branches to base branch.
**Cost:** High (multiple branch comparisons).
**Params:**
- `base_branch`: Base branch to compare against (e.g., "main")
- `feature_branches`: List of feature branches
- `file_pattern`: Optional glob pattern

**Examples:**
```
diff_branches_multi(base_branch="main", feature_branches=["feature/auth", "feature/api"])
```

**Returns:** Per-branch change summary with symbol-level details.

### 6. `check_pattern`
**Use:** Verify code follows project conventions.
**Cost:** Medium (~800-1,200 tokens).
**Params:**
- `pattern`: Pattern type (e.g., "error_handling", "logging", "naming")
- `path`: Path to check (file or directory)

**Examples:**
```
check_pattern(pattern="error_handling", path="src/")
check_pattern(pattern="logging", path="src/services/payment.py")
```

**Returns:** Violations with locations and suggested fixes.

### 7. `validate_architecture`
**Use:** Enforce architectural rules.
**Cost:** Medium-High (~1,000-2,000 tokens).
**Params:**
- `rules`: Architecture rules to validate
- `path`: Path to validate

**Examples:**
```
validate_architecture(rules=["no_circular_imports", "layer_separation"], path="src/")
```

**Returns:** Rule violations with severity and locations.

### 8. `project_summary`
**Use:** 80/20 overview of new codebase.
**Cost:** High (~2,000-3,000 tokens, but 80%+ savings vs full exploration).
**Params:**
- `path`: Project root (default: current directory)
- `focus`: Optional focus area (e.g., "architecture", "patterns", "tech_stack")

**Examples:**
```
project_summary()
project_summary(path=".", focus="architecture")
```

**Returns:** High-level summary: structure, key components, patterns, tech stack.

### 9. `related_changes`
**Use:** Predict what else needs updating after editing code.
**Cost:** ~500-800 tokens.
**Params:**
- `file_path`: File being modified
- `symbol_name`: Optional specific symbol

**Examples:**
```
related_changes(file_path="src/auth.py", symbol_name="authenticate")
related_changes(file_path="src/handlers/user.py")
```

**Returns:** Suggested files/symbols to update with confidence scores.

## STRATEGY

### Before Refactoring (Safety First)
```
1. analyze_impact(symbol_name="target_function")     → What breaks?
2. test_coverage(symbol_name="target_function")      → What tests exist?
3. context(symbol_name="target_function")            → Get implementation
4. [Make changes with Edit/Write]
5. related_changes(file_path="changed_file.py")      → What else needs updating?
6. smart_update()                                     → Update index
```

### Code Review (PR Workflow)
```
1. diff_branches(branch_a="main", branch_b="feature/new-api")  → What changed?
2. For each changed symbol:
   - analyze_impact(symbol_name="changed_symbol")              → Impact analysis
   - test_coverage(symbol_name="changed_symbol")               → Test coverage
3. check_pattern(pattern="error_handling", path="src/")        → Convention compliance
4. find_circular_deps(path="src/")                             → No new cycles?
```

### Multi-Feature Comparison
```
1. diff_branches_multi(
     base_branch="main",
     feature_branches=["feature/auth", "feature/payments", "feature/notifications"]
   )
2. Review per-branch summaries for conflicts or overlapping changes
```

### Learning New Codebase
```
1. project_summary()                                  → 80/20 overview (2-3k tokens)
   vs full exploration with blueprint/search/read     → 20-30k tokens
2. search(query="authentication", limit=5)            → Find key areas
3. context(symbol_name="main_entry_point")            → Deep dive on entry
```

### Architecture Validation (CI/CD)
```
1. find_circular_deps(path="src/")                    → No import cycles
2. validate_architecture(
     rules=["no_circular_imports", "layer_separation"],
     path="src/"
   )                                                   → Enforce rules
3. check_pattern(pattern="error_handling", path="src/") → Style compliance
```

### After Major Changes
```
1. [Make changes with Edit/Write]
2. related_changes(file_path="modified_file.py")      → Predict ripple effects
3. For each high-confidence suggestion:
   - context(symbol_name="suggested_symbol")          → Review suggested change
   - [Update if needed]
4. smart_update()                                      → Update index
5. find_circular_deps(path="src/")                    → Verify no new cycles
```

## WORKFLOW INTEGRATION

### New Project Session (First Time)
```
project_summary()                    # 2,500T: Get 80/20 overview
search(query="main", limit=5)        # 500T: Find entry points
context(symbol_name="main")          # 1,500T: Deep dive
Total: ~4,500 tokens vs ~25,000 tokens with full exploration
```

### Pre-Commit Validation
```
related_changes(file_path="edited.py")              # Check ripple effects
check_pattern(pattern="error_handling", path=".")   # Style check
find_circular_deps(path="src/")                     # Architecture check
```

### PR Review Automation
```
diff_branches(branch_a="main", branch_b="feature/X")
analyze_impact(symbol_name="changed_function")
test_coverage(symbol_name="changed_function")
```

## BEST PRACTICES

1. **Always check impact before refactoring** - Use `analyze_impact` to see blast radius
2. **Verify test coverage before changes** - Use `test_coverage` to ensure safety net
3. **Use project_summary for new codebases** - 80%+ token savings vs manual exploration
4. **Check related_changes after edits** - Catch ripple effects early
5. **Run find_circular_deps regularly** - Prevent architecture decay
6. **Use diff_branches for PR reviews** - Symbol-level understanding vs line diffs
