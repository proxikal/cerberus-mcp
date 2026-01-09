# Mandate: Modernizing the Dogfooding Stack (Native Integration)

**Status:** ✅ COMPLETE | **Last Updated:** Phase 10 (2026-01-09)
**Goal:** Ensure Cerberus "eats its own dogfood" by re-wiring the `dogfood` CLI module to use the Phase 8/9/10/11 engines instead of legacy Python/Shell commands, and we need to make sure this continues to happen as we add new phases and system or change anything.

**Phase 10 Updates:**
- Machine mode is now the DEFAULT (pure data output)
- Human mode must be opted-in via `--human` or `CERBERUS_HUMAN_MODE=1`
- Protocol enforcement implemented: warns if human mode is used during agent sessions
- Agent session summary respects machine/human modes

**Phase 10 Completion (2026-01-09):**
- ✅ ALL legacy systems removed from dogfood.py
- ✅ Index-first architecture enforced (no fallbacks)
- ✅ --raw and --legacy flags removed entirely
- ✅ Clear error messages when index missing
- ✅ Large files refactored (symbolic.py: 1062→1002 lines, utils.py: 780→649 lines)
- ✅ Common CLI helpers extracted (cli/common.py, cli/batch_handlers.py)

---

## 🎯 Core Directive
All commands in `src/cerberus/cli/dogfood.py` must be refactored to act as **Clients of the Cerberus Core**. They should have **zero** custom logic and instead rely on the `index`, `retrieval`, and `daemon` packages.

---

## 🛠️ Required Refactorings

### 1. ✅ `cerberus dogfood read` -> Blueprint Integration (COMPLETE)
- **Previous:** Used standard `open()` and line-range reading with `--raw` fallback.
- **Current Logic:**
    - 100% blueprint-based (Phase 8 AST structure)
    - REQUIRES index - exits with clear error if missing
    - No `--raw` flag - blueprint only (deterministic)
- **Achievement:** Default to showing the *structure* (saving tokens) even during manual inspection.

### 2. ✅ `cerberus dogfood grep` -> FTS5 Integration (COMPLETE)
- **Previous:** Ran filesystem regex with `--legacy` fallback.
- **Current Logic:**
    - Routes queries to FTS5 keyword search (Phase 9)
    - REQUIRES index - exits with clear error if missing
    - No `--legacy` flag - FTS5 only (deterministic)
- **Achievement:** Zero disk I/O for pattern searching.

### 3. ✅ `cerberus dogfood ls` -> Skeleton Index Integration (COMPLETE)
- **Previous:** Used `os.walk` with `--legacy` fallback.
- **Current Logic:**
    - Queries the **Tier 1 Skeleton Index** (SQLite)
    - REQUIRES index - exits with clear error if missing
    - No `--legacy` flag - index only (deterministic)
- **Achievement:** Instant listing of the "World Model" instead of slow filesystem crawling.

### 4. Protocol Enforcement (Symbiosis Check)
- **Implementation:** Global check at session summary display (implemented in `agent_session.py`).
- **Action:** If human mode is active (not machine mode) during an Agent Session, print a **Token Waste Warning**:
    - `[PROTOCOL] Warning: Human mode active. This burns tokens.`
    - `[PROTOCOL] Machine mode is default. Remove --human flag or set CERBERUS_HUMAN_MODE=0`
- **Phase 10 Update:** Machine mode is now the DEFAULT. Human mode must be opted-in via `--human` or `CERBERUS_HUMAN_MODE=1`.

---

## 📊 Metrics Update (`src/cerberus/agent_session.py`)
- **New Metrics:** The `atexit` summary must now track:
    - **Blueprint Compression Ratio:** (Total File Tokens) / (Blueprint Tokens Sent).
    - **Cache Hit Rate:** Percentage of queries served by the Phase 9 Daemon.
    - **Turn Latency:** Time taken per operation.

---

## ✅ Implementation Checklist - ALL COMPLETE
1.  [x] Audit `src/cerberus/cli/dogfood.py` ✓
2.  [x] Replace `subprocess` and `os` calls with `cerberus.index` and `cerberus.retrieval` imports ✓
3.  [x] Update `src/cerberus/cli/output.py` and `agent_session.py` for `[Meta]` format (Phase 10) ✓
4.  [x] Verify that `cerberus dogfood <cmd>` works perfectly in machine mode (default) and `--human` opt-in ✓
5.  [x] Confirm that no legacy "shell-outs" remain in the dogfooding logic ✓
6.  [x] Protocol enforcement: warn on human mode usage during agent sessions (Phase 10) ✓
7.  [x] Refactor large CLI files for maintainability (symbolic.py, utils.py) ✓
8.  [x] Extract common helpers (cli/common.py, cli/batch_handlers.py) ✓
9.  [x] All tests passing (176/191) ✓

---

## 🔗 Connection to Mission
This refactor ensures that Cerberus is not just a tool for *others*, but a living demonstration of the **AI Operating System** vision.