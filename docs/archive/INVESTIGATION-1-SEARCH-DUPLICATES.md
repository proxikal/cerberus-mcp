# Investigation 1: Duplicate Search Results

**Status:** ✅ Completed (Phase 1)  
**Owner:** Codex (GPT-5)  
**Last updated:** 2026-01-20  
**Scope:** `mcp__cerberus__search` returning identical entries

---

## What we observed
- Running `mcp__cerberus__search(query="format_output", limit=5, mode="keyword")` returns 5 copies of the same symbol from `src/cerberus/blueprint/facade.py:601-637`.
- Duplicates originate before ranking/formatting; nothing in the MCP tool layer creates new rows.

---

## Evidence

### Database state (Scenario B)
SQLite query against `.cerberus/cerberus.db`:
```sql
SELECT name, file_path, start_line, COUNT(*) AS count
FROM symbols
WHERE name = 'format_output'
GROUP BY name, file_path, start_line
HAVING count > 1;
```
Result:
```
format_output|/Users/proxikal/dev/projects/cerberus/src/cerberus/blueprint/facade.py|601|7
```

Full rows confirm 7 identical symbols (IDs differ, data identical):
```
2631|format_output|.../blueprint/facade.py|601|637|method
... (7 rows total, same file/start/end/type)
```

### Broader duplication footprint
Top 10 `(name,file_path)` groups with duplicates:
```sql
SELECT COUNT(*), name, file_path
FROM symbols
GROUP BY name, file_path
HAVING COUNT(*) > 1
LIMIT 10;
```
Returned multiple duplicates across docs and code files, showing systemic re-insertion rather than one-off corruption.

### Search pipeline behavior
- MCP tool: `src/cerberus/mcp/tools/search.py` calls `hybrid_search(...)` with `mode="keyword"` → uses streaming FTS5 path.
- Streaming keyword path (`_hybrid_search_streaming`):
  - Uses `SQLiteSymbolsOperations.fts5_search` (no DISTINCT).
  - Returns rows directly to `_finalize_results`; no deduplication for keyword-only mode.
- Hybrid ranker dedupes only when fusion is used; keyword-only path bypasses fusion, so duplicates surface 1:1 from storage.

---

## Root cause
1) **Index build never clears existing symbols for a file**  
   - `_build_sqlite_index` writes new symbols via `write_symbols_batch` without calling `delete_file` or equivalent.  
   - Schema lacks a UNIQUE constraint on `(file_path, name, start_line, end_line, type)`.  
   - Rebuilding the index appends rows for unchanged files, preserving stale rows from older parser versions and creating exact duplicates.

2) **Search keyword path lacks defensive deduplication**  
   - `fts5_search` + `_finalize_results` emit every row returned by SQLite.  
   - With duplicate rows in `symbols`/`symbols_fts`, search emits duplicates even though fusion paths would collapse them.

---

## Proposed fix approach
1) **Storage-level correctness (primary fix)**
   - On re-index: before inserting a file’s symbols, call `delete_file(file_path)` to cascade-remove old symbols/imports/calls.
   - Add a UNIQUE index on `(file_path, name, start_line, end_line, type)` to prevent accidental reinsertion. Use `INSERT OR IGNORE` or `ON CONFLICT DO NOTHING` semantics for safety.
   - Provide a one-time migration to purge existing duplicates (KEEP the latest by `id`, or delete all then re-insert).

2) **Retrieval safety net**
   - In `fts5_search` or immediately after fetching results, collapse duplicates by `(file_path, name, start_line, end_line, type)`.
   - In `_finalize_results`, dedupe before ranking/return when `match_type="keyword"`.

3) **Operational hygiene**
   - Force a clean rebuild of `.cerberus/cerberus.db` after the above changes to remove stale rows.
   - Add an index version/metadata flag so parser changes trigger a rebuild instead of accumulating legacy rows.

---

## Risks / considerations
- Adding UNIQUE constraints requires a data migration; need to guard against failing inserts for legitimate overload cases (e.g., overloaded functions in other languages—ensure key includes `type` and line range).
- Deleting per-file before insert changes incremental semantics; ensure `previous_files` skip still applies to avoid unnecessary deletes.
- Dedup in retrieval should be lightweight (use tuples, not hashing large objects) to avoid perf regressions.

---

## Conclusion
- Duplicates are **stored** in SQLite due to non-clearing re-index + lack of uniqueness.  
- The keyword search path simply surfaces these rows unchanged.  
- Fix requires storage cleanup + UNIQUE constraints, plus optional retrieval dedup as a guardrail.

