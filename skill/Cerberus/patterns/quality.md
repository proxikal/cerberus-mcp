# PROTOCOL: QUALITY

**OBJECTIVE:** Check, fix, and predict code quality issues.

## MCP TOOLS

### 1. `style_check`
**Use:** Check code for style violations.
**Cost:** Low-Medium (limited to 30 violations).
**Params:**
- `path`: File or directory to check
- `rules`: Optional specific rules (default: all)
- `fix_preview`: Preview auto-fixes (default: false)

**Examples:**
```
style_check(path="src/auth.py")
style_check(path="src/", fix_preview=true)
```

**Returns:** violation_count, violations (limited), truncated flag

### 2. `style_fix`
**Use:** Auto-fix style violations.
**Cost:** Low.
**Params:**
- `path`: File or directory to fix
- `rules`: Optional specific rules (default: all fixable)
- `dry_run`: Preview only (default: false)
- `create_backup`: Backup before modifying (default: true)

**Examples:**
```
style_fix(path="src/auth.py", dry_run=true)  # Preview
style_fix(path="src/auth.py")                 # Apply fixes
```

**Returns:** files_modified, violations_fixed, applied_fixes

### 3. `related_changes`
**Use:** Predict what else needs updating when you modify code.
**Cost:** ~500 tokens.
**Params:**
- `file_path`: File being modified
- `symbol_name`: Optional specific symbol (uses filename stem if not provided)

**Examples:**
```
related_changes(file_path="src/auth.py", symbol_name="authenticate")
related_changes(file_path="src/handlers/user.py")
```

**Returns:** suggestions with file, symbol, line, reason, confidence, relationship

### 4. `check_pattern`
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

### 5. `validate_architecture`
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

## STRATEGY

### Style Checking (Iterative)
1. `style_check(path="file.py")` → See first 30 violations
2. `style_fix(path="file.py")` → Fix automatically
3. `style_check(path="file.py")` → Re-check for remaining
4. Repeat until clean

### Before Committing
1. `style_check(path=".")` → Check entire codebase
2. `style_fix(path=".", dry_run=true)` → Preview fixes
3. `style_fix(path=".")` → Apply fixes
4. `check_pattern(pattern="error_handling", path=".")` → Verify conventions
5. `validate_architecture(rules=[...], path="src/")` → Enforce architecture

### After Editing
1. `related_changes(file_path="edited_file.py")` → See what else might need updating
2. Review suggestions with high confidence
3. Update related files as needed

### Code Review / PR
1. `check_pattern(pattern="error_handling", path="changed_files/")` → Convention compliance
2. `validate_architecture(rules=["no_circular_imports"], path="src/")` → Architecture validation

## WORKFLOW INTEGRATION

After modifying code:
```
1. Edit file with native Edit tool
2. related_changes(file_path="edited_file.py")  → Predict ripple effects
3. style_check(path="edited_file.py")           → Check for issues
4. style_fix(path="edited_file.py")             → Auto-fix
5. smart_update()                               → Update index
```
