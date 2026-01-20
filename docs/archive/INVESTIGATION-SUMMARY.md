# Phase 1 Summary: Duplicate Issues

**Status:** ✅ Investigation complete  
**Owner:** Codex (GPT-5)  
**Date:** 2026-01-20

---

## Findings (by issue)
- **Search duplicates (Investigation 1):** Duplicates are stored in SQLite (e.g., `format_output` has 7 identical rows). Keyword search path surfaces rows 1:1 because it lacks deduplication; fusion paths would mask some cases but keyword-only mode does not.
- **Get symbol duplicates (Investigation 2):** Same duplicated rows are returned directly by `find_symbols/query_symbols`, which apply no DISTINCT or deduplication.
- **Blueprint duplicates (Investigation 3):** Database still contains stale regex-era class rows (e.g., `CallNode` at line 18), even though the current AST parser emits only the three real classes. Blueprint renders what is in storage without filtering.

---

## Root cause (shared)
1) **Index build never clears per-file data.** `_build_sqlite_index` inserts new symbols without deleting existing rows for that file; reruns and parser changes accumulate stale/duplicate symbols.
2) **No uniqueness enforcement.** `symbols` table lacks a UNIQUE constraint; repeated inserts for the same `(file_path, name, start_line, end_line, type)` succeed.
3) **Tooling lacks defensive dedup in keyword/symbol paths.** Keyword search and `get_symbol` return whatever storage provides, so stored duplicates are surfaced unfiltered.

---

## Proposed fix plan (inputs to Phase 2)
1) **Storage lifecycle fix**
   - Before writing a file’s symbols/imports/calls, call `delete_file(file_path)` to clear prior rows.
   - Add UNIQUE index on `(file_path, name, start_line, end_line, type)`; adjust inserts to honor it (`INSERT OR IGNORE`/`REPLACE`).
   - Add migration to purge existing duplicates (keep lowest `id` per unique key) and rebuild the index.

2) **Defensive retrieval**
   - Deduplicate in `fts5_search`/`_finalize_results` for keyword search.
   - Deduplicate in `find_symbols`/`get_symbol` before returning results.
   - Optional: dedupe in blueprint facade before formatting as a safety net.

3) **Operational hygiene**
   - Rebuild `.cerberus/cerberus.db` after schema changes.
   - Add an index/metadata version flag so parser changes force a clean rebuild.

---

## Confidence & risks
- **Confidence:** High—SQL evidence shows storage-level duplication; parser validation confirms current parser is correct for the blueprint case.
- **Risks:** Schema migration (UNIQUE) must handle legitimate overloaded symbols; per-file delete changes incremental semantics (verify performance); retrieval dedup should stay lightweight.

---

## Ready for Phase 2?
Yes. Root causes are understood, evidence captured, and fix approaches identified. Proceed to implement storage cleanup + uniqueness, then add retrieval guardrails and migrations.
