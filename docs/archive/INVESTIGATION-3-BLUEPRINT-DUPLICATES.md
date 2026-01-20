# Investigation 3: Duplicate Blueprint Symbols

**Status:** ✅ Completed (Phase 1)  
**Owner:** Codex (GPT-5)  
**Last updated:** 2026-01-20  
**Scope:** Blueprint shows extra/false-positive classes for `call_graph_builder.py`

---

## What we observed
- Blueprint for `src/cerberus/resolution/call_graph_builder.py` reports six classes instead of three:
  - False positives at lines 18, 28, 38 (inside `BUILTIN_FILTER` set literal).
  - Correct classes at lines 45, 55, 65.

---

## Evidence

### Database contains stale/false symbols
```sql
SELECT name, start_line, type, COUNT(*)
FROM symbols
WHERE file_path='/Users/proxikal/dev/projects/cerberus/src/cerberus/resolution/call_graph_builder.py'
  AND type='class'
GROUP BY name, start_line, type
ORDER BY start_line;
```
Result:
```
CallNode|18|class|6
CallGraph|28|class|6
CallGraphBuilder|38|class|6
CallNode|45|class|1
CallGraph|55|class|1
CallGraphBuilder|65|class|1
```

### Current parser does NOT produce these classes
Direct parser run:
```bash
python3 - <<'PY'
from pathlib import Path
from cerberus.parser.python_parser import parse_python_file
file_path = Path('src/cerberus/resolution/call_graph_builder.py')
symbols = parse_python_file(file_path, file_path.read_text())
classes = [s for s in symbols if s.type == 'class']
print('Class count', len(classes))
for c in classes: print(c.name, c.start_line, c.end_line)
PY
```
Output:
```
Class count 3
CallNode 45 51
CallGraph 55 62
CallGraphBuilder 65 431
```

### Blueprint query path
- Blueprint reads symbols from the database (`blueprint/facade.py` → `_query_symbols`).
- With stale rows present, blueprint faithfully renders them; no dedup/filtering exists.

---

## Root cause
- **Stale, non-cleared symbols from older parser versions remain in SQLite.**
  - The current AST-based parser is correct, but previous regex-based indexing runs wrote false positives.
  - `_build_sqlite_index` does not delete existing symbols per file before inserting new ones, so old rows persist even after parser fixes.
  - Lack of UNIQUE constraint allows multiple stale copies (six per bogus class entry).

---

## Proposed fix approach
1) **Clean per-file before write**  
   - During index build, call `delete_file(file_path)` before inserting new symbols/imports/calls.

2) **Enforce uniqueness**  
   - Add UNIQUE index on `(file_path, name, start_line, end_line, type)` with `ON CONFLICT REPLACE/IGNORE` semantics.

3) **Data cleanup & migrations**  
   - Migration script to remove duplicate/stale rows (keep lowest `id` per unique key).  
   - Force a fresh rebuild of `.cerberus/cerberus.db` after the migration to ensure only AST-derived symbols remain.
   - Consider an index version flag so parser changes trigger a full rebuild automatically.

4) **Optional blueprint guardrail**  
   - Deduplicate symbols by `(file_path, name, start_line)` before formatting output to protect against unexpected DB issues.

---

## Conclusion
- The blueprint tool is rendering stale data, not mis-parsing current code.  
- Root cause matches Investigations 1 and 2: index rebuilds append without clearing, and uniqueness is not enforced.  
- Fix requires storage cleanup + uniqueness, plus a one-time purge/rebuild to drop legacy regex artifacts.

