# Investigation 2: Duplicate Get Symbol Results

**Status:** ✅ Completed (Phase 1)  
**Owner:** Codex (GPT-5)  
**Last updated:** 2026-01-20  
**Scope:** `mcp__cerberus__get_symbol` returning repeated identical symbols/snippets

---

## What we observed
- `mcp__cerberus__get_symbol(name="format_output", exact=True)` returns 7 identical entries of the same method from `src/cerberus/blueprint/facade.py:601-637`.
- Duplicates appear before snippet rendering; they are present in `find_symbols` results.

---

## Evidence

### Database rows are duplicated
Same queries as Investigation 1 show 7 identical rows for `format_output` (IDs differ; fields identical):
```
id|name|file_path|start_line|end_line|type
2631|format_output|.../blueprint/facade.py|601|637|method
5404|format_output|.../blueprint/facade.py|601|637|method
8177|format_output|.../blueprint/facade.py|601|637|method
15943|format_output|.../blueprint/facade.py|601|637|method
18130|format_output|.../blueprint/facade.py|601|637|method
20364|format_output|.../blueprint/facade.py|601|637|method
22280|format_output|.../blueprint/facade.py|601|637|method
```

### Code path returns all rows
- MCP tool: `src/cerberus/mcp/tools/symbols.py:get_symbol` → `index.find_symbols` → `SQLiteSymbolsOperations.query_symbols`.
- `query_symbols` issues `SELECT * FROM symbols` (optionally filtered) with no deduplication or DISTINCT.
- Snippet extraction simply maps over returned rows, so duplicates from storage become duplicate payloads.

---

## Root cause
- **Same as Investigation 1:** Index builds append rows for files without clearing previous entries, and schema lacks a uniqueness constraint. Multiple re-indexes created multiple identical symbol rows.
- No deduplication or DISTINCT in `find_symbols/query_symbols`, so storage duplication is directly surfaced to the MCP tool.

---

## Proposed fix approach
1) **Fix storage lifecycle**
   - Delete existing rows for a file before inserting new symbols (`delete_file` during index build).
   - Add UNIQUE constraint on `(file_path, name, start_line, end_line, type)` to prevent duplication.
   - Ship a migration that removes duplicate symbol rows (keep the lowest `id` per unique key).

2) **Defensive query layer**
   - Apply DISTINCT (or dedupe in Python) in `query_symbols`/`find_symbols` before returning results to tools.
   - Optionally expose a `LIMIT` guardrail in `get_symbol` to cap pathological result sets.

3) **Operational cleanup**
   - Trigger a clean rebuild of `.cerberus/cerberus.db` after fixes so MCP calls read from a clean dataset.

---

## Risks / considerations
- Need to ensure uniqueness key covers overloaded cases across languages (include `type` and line range to keep legitimate variants distinct).
- Deleting per-file on each scan changes incremental behavior; verify `previous_files` skip still prevents unnecessary work.
- Dedup at query time should be lightweight to avoid slowing `get_symbol` calls.

---

## Conclusion
- Duplicate symbol responses are directly caused by duplicated rows in SQLite.  
- Fix storage (cleanup + uniqueness) and add light dedup in `find_symbols/get_symbol` to prevent reoccurrence and provide a safety net.

