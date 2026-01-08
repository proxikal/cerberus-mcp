# Cerberus Agent Instructions

These guidelines keep agent interactions lean to reduce context usage.

## Available Tools
- `scan` — quick project map; use `--json`.
- `scan --max-bytes <n>` — skip oversized files to keep context lean.
- `index` — build JSON index; use `--json` to capture counts and index path.
- `index --incremental` — reuse existing index to skip unchanged files (keeps runs fast and context small).
- `index --max-bytes <n>` — apply size filter during indexing.
- `bench` — measure index + search time; use `--json` to capture metrics and monitor perf.
- `search` — now uses MiniLM embeddings by default with `--min-score` to filter noise.
- `search --no-embeddings` — use lightweight token overlap if you need zero model load.
- `search --backend faiss` — optional FAISS vector search (only if faiss installed); default `memory`.
- `stats` — summarize an index; use `--json`.
- `get-symbol <name>` — fetch symbol(s) plus minimal context; use `--json` and set `--padding` if needed.
- `search "<query>"` — semantic lookup over symbols; use `--json` and `--limit` to cap results.

## Usage Patterns
1. **Map**: `cerberus scan <dir> --json` (pass `--ext` to limit noise; `--no-gitignore` only if necessary).
2. **Index**: `cerberus index <dir> --output cerberus_index.json --json` (reuse the same index across calls).
3. **Inspect**: `cerberus stats --index cerberus_index.json --json` to confirm symbol coverage.
4. **Fetch**: `cerberus get-symbol <name> --index cerberus_index.json --padding 2 --json` for precise slices.
5. **Search**: `cerberus search "auth login" --index cerberus_index.json --limit 5 --json` for intent-based lookup.

## Debug & Logging
- Logs go to stderr and `cerberus_agent.log` (JSON). stdout is reserved for structured command output when `--json` is set.
- Keep padding small to minimize context (default 3). Increase only when necessary.

## Safety & Scope
- Prefer extension filters to shrink scans.
- Respect `.gitignore` by default to avoid noisy files.
- Index files are plain JSON; store them in workspace-local paths.

## Tool Schemas
See `src/cerberus/agent_tools.py` for JSON schemas covering `GetProjectStructure`, `FindSymbol`, `ReadSymbol`, and `SemanticSearch`.
