# Phase 7 Specification: Zero-Footprint Retrieval

**Status:** Active Planning
**Goal:** Demolish the "Memory Wall" by reducing Cerberus's constant RAM footprint to **< 50MB**, beating Aider in resource efficiency while maintaining absolute AST integrity.

---

## 🎯 Optimization Strategies

### 1. Strict Lazy "Brain" Loading
**Problem:** The 400MB+ local embedding model (all-MiniLM-L6-v2) loads into RAM whenever the retrieval module is initialized, even for keyword-only searches.
**Implementation:**
- Move model initialization inside the search function scope.
- If search mode is `keyword` or if the user is running `get-symbol`/`skeletonize`, the model must **NEVER** touch RAM.
- **Success Metric:** Constant RAM usage < 50MB for non-semantic operations.

### 2. SQLite FTS5 (Full-Text Search) Integration
**Problem:** The BM25 algorithm currently requires loading all symbol names and signatures into a Python list to calculate rankings.
**Implementation:**
- Replace `rank-bm25` with SQLite's native **FTS5** virtual tables.
- Index symbol names, file paths, and signatures directly in SQLite.
- Offload keyword scoring to the SQLite C-engine.
- **Success Metric:** Keyword search uses near-zero extra RAM, scaling O(1) with memory.

### 3. Remote Embedding Provider Support (Optional)
**Problem:** Local-first is the mission, but some environments (tiny VPS, shared CI) cannot afford 400MB for a local model.
**Implementation:**
- Add an optional flag `--remote-embeddings [gemini|openai]`.
- Implement an adapter layer to fetch vectors via API.
- Use API-side embeddings for indexing and searching.
- **Success Metric:** Full semantic search capability with the footprint of a standard CLI tool.

### 4. AST Buffer Streaming & Discard
**Problem:** During indexing, Tree-sitter objects for large files can accumulate in memory before they are converted to Cerberus schemas and saved to SQLite.
**Implementation:**
- Implement a strict "Parse -> Extract -> Discard" loop.
- Ensure the `Tree` and `Node` objects are explicitly cleared or go out of scope immediately after the surgical symbol data is moved to the SQLite buffer.
- **Success Metric:** Memory usage during indexing stays flat, regardless of file size or symbol count.

---

## 🏗️ Codebase De-Monolithization (Modularity Upgrade)

To adhere to the **Self-Similarity Mandate**, we must break down the monolithic "God Files" that have exceeded 1,000+ lines. This will make the codebase "Agent-Optimized" by reducing the context wall for future development.

### 1. Refactor `src/cerberus/main.py` (2,939 lines)
**Target:** Create `src/cerberus/cli/` package.
- **`cli/index.py`**: Implementation of `index` and `scan` commands.
- **`cli/retrieval.py`**: Implementation of `search`, `get-symbol`, `get-context`, `skeleton-file`, and `skeletonize`.
- **`cli/symbolic.py`**: Implementation of all Phase 5/6 symbolic intelligence commands (`deps`, `inherit-tree`, `calls`, `references`, `smart-context`, etc.).
- **`cli/operational.py`**: Implementation of `watcher`, `update`, `hello`, `version`, `doctor`, and `session` commands.
- **`main.py` (Minimalist Orchestrator)**: Acts as the entry point, using `app.add_typer()` to assemble the sub-modules.

### 2. Refactor `src/cerberus/storage/sqlite_store.py` (1,063 lines)
**Target:** Create `src/cerberus/storage/sqlite/` package.
- **`sqlite/schema.py`**: Table definitions, indices, and FTS5 configuration.
- **`sqlite/symbols.py`**: Logic for symbol and file CRUD operations.
- **`sqlite/resolution.py`**: Logic for method calls, type infos, import links, and symbol references.
- **`sqlite/persistence.py`**: Connection management, transactions, and metadata handling.

---

## ✅ Integrity Mandate

---

**Mission:** Build the world's most powerful, lightest context engine for autonomous engineering.
