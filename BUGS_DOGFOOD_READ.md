# Bug Reports: cerberus dogfood read

## Bug #1: Relative Path Rejection
**Severity:** Medium
**Component:** `src/cerberus/cli/dogfood.py` - `read` command
**Status:** ✅ FIXED (2026-01-10)

### Description
The `cerberus dogfood read` command fails when given relative paths, requiring absolute paths instead. This is inconsistent with other Cerberus commands that accept relative paths.

### Steps to Reproduce
```bash
# From project root
cerberus dogfood read src/cerberus/cli/mutations.py
```

### Expected Behavior
Command should resolve relative path to absolute path and read the file.

### Actual Behavior
```
Error: File 'src/cerberus/cli/mutations.py' not in index.
→ Run 'cerberus index .' to index this file.
```

### Workaround
Use absolute paths:
```bash
cerberus dogfood read /Users/proxikal/Desktop/Dev/Cerberus/src/cerberus/cli/mutations.py
```

### Root Cause
The SQLite index stores absolute paths, but the dogfood read command doesn't resolve relative-to-absolute before querying the database.

### Fix Applied
In `src/cerberus/cli/dogfood.py:90-92`, added path resolution:
```python
# BUG FIX #1: Convert to absolute path (database stores absolute paths)
file_absolute = file_path.resolve()
file_str = str(file_absolute)
```

---

## Bug #2: --lines Parameter Returns Blueprint Instead of Content
**Severity:** High
**Component:** `src/cerberus/cli/dogfood.py` - `read` command with `--lines` parameter
**Status:** ✅ FIXED (2026-01-10)

### Description
When using the `--lines` parameter, `cerberus dogfood read` returns blueprint/symbol output instead of actual file content lines.

### Steps to Reproduce
```bash
cerberus dogfood read /Users/proxikal/Desktop/Dev/Cerberus/src/cerberus/cli/mutations.py --lines 1-50
```

### Expected Behavior
Should output lines 1-50 of the file content with line numbers.

### Actual Behavior
Returns:
```json
{
  "file_path": "...",
  "mode": "blueprint",
  "lines_shown": {"start": 1, "end": 48},
  "content": "# Blueprint: ...\n# Symbols: 45 | Mode: index-backed AST\n\n   28 | function edit_cmd\n   ..."
}
```

### Impact
- Makes `cerberus dogfood read --lines` unusable for reading code
- Forces protocol violations (using Read tool instead)
- Breaks dogfooding mandate

### Priority
High - This blocks adherence to the CERBERUS.md protocol mandate requiring `cerberus dogfood read --lines` instead of the Read tool.

### Fix Applied
In `src/cerberus/cli/dogfood.py:102-127`, added conditional logic:
```python
# BUG FIX #2: If line range specified, read actual file content
# Blueprint mode is only for structure viewing (no line range)
use_blueprint = (start_line is None and end_line is None and lines is None)

if use_blueprint:
    # Build blueprint output (Phase 8 engine)
    # ... blueprint logic ...
else:
    # Read actual file content for line range queries
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
```

Also updated output mode indicator to reflect actual behavior:
- JSON output: `"mode": "blueprint"` or `"mode": "content"`
- Human output: `[Status: Blueprint]` or `[Status: Content]`

---

**Session Context:** 2026-01-10
**Discovered During:** Phase 11 implementation (cerberus mutations insert)
**Impact:** Blocks protocol compliance and dogfooding workflow
