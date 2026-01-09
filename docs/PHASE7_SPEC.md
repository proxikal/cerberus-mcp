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

## 🛠️ Architecture Changes

### Package: `cerberus/retrieval`
- Refactor `facade.py` to handle on-demand model loading.
- Update `config.py` to include `REMOTE_EMBEDDING_CONFIG`.

### Package: `cerberus/storage`
- Update `sqlite_store.py` to initialize FTS5 virtual tables.
- Implement triggers or manual procedures to keep FTS index synced with the `symbols` table.

---

## ✅ Integrity Mandate
These optimizations are **Upgrades only**.
1. **No Hallucinations:** Search results must remain 100% grounded in the local AST.
2. **Deterministic:** FTS5 rankings must be consistent across runs.
3. **Agent-Native:** JSON response schemas must remain unchanged to avoid breaking downstream AI agents.

---

**Mission:** Build the world's most powerful, lightest context engine for autonomous engineering.
