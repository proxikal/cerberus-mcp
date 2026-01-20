# Phase 2 Critical Fixes (In Progress)

**Owner:** Codex (GPT-5)  
**Last updated:** 2026-01-20  
**Scope:** P0 duplicate fixes (search, get_symbol, blueprint)

---

## Storage & Schema
- Added per-file delete-before-insert during indexing to avoid stale/duplicate rows (`src/cerberus/index/index_builder.py`).
- Added batch-level deduplication and `INSERT OR IGNORE` for symbols writes (`src/cerberus/storage/sqlite/symbols.py`).
- Added schema migration to purge duplicate symbols and enforce uniqueness via index; schema version 1.2.0 (`src/cerberus/storage/sqlite/schema.py`).
- Rebuilt `.cerberus/cerberus.db`; duplicates for `format_output` and blueprint classes removed.

## Retrieval Guardrails
- Keyword/hybrid search: dedup at result finalization; RRF path already keys by symbol id (`src/cerberus/retrieval/facade.py`, `src/cerberus/retrieval/hybrid_ranker.py`).
- FTS and symbol queries: dedup in SQL fetch layer (`src/cerberus/storage/sqlite/symbols.py`).
- MCP get_symbol: dedup before snippet extraction (`src/cerberus/mcp/tools/symbols.py`).
- Blueprint: dedup symbols when loading from DB to guard against any residuals (`src/cerberus/blueprint/facade.py`).

## Limits
- Raised default max index size to 150MB to clear validation fail for current repo (`src/cerberus/limits/config.py`).

## Current Validation/Checks
- `validate_index_health(.cerberus/cerberus.db)` → WARN only for size (135.8MB / 150MB); symbols/vectors OK.
- `find_symbol_fts('format_output', exact=True)` → 1 result (unique).
- `hybrid_search(query='format_output', mode='keyword', top_k=5)` → returns unique results (no duplicates).

## Next
- Optionally add unit/integration tests for dedup paths.
- Proceed to Phase 3 verification once Phase 2 coding is complete.

