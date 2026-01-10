# CERBERUS v0.13.0 - AI Agent Operating System
# Protocol: UACP/1.2 | Fidelity: 100% | Mode: Machine-First (JSON) | Arch: AST/SQLite

## ⚡ CORE MANDATES [REQUIRED]
MISSION: 100% Signal / 0% Noise. Deterministic AST > LLM Guesswork.
PRINCIPLES:
  1. Code > Prompts: Use `get-symbol` (AST), never `read_file` (Text).
  2. Verified Transactions: writes MUST use `--verify` to prevent regression.
  3. Strict Resolution: No auto-correct on mutations. Ambiguity = Error.
  4. Symbiosis: Use `blueprint` (Map) before `read` (Flashlight).

## 🚫 FORBIDDEN [STRICT]
- `cat/read_file` on full files (>50 lines). USE: `blueprint` or `read --lines`.
- `grep`. USE: `cerberus search` (Semantic/Hybrid).
- `ls -R`. USE: `cerberus tree`.
- Speculative/Unverified Edits. USE: `batch-edit --verify`.
- Deleting referenced symbols WITHOUT checking deps. (Symbol Guard: 🔜).

## 🗺 PHASE STATUS [CAPABILITIES]
P1-11 [CORE]: Indexing (SQLite/FAISS), Retrieval (Hybrid), Editing (AST). ✅
P12 [HARMONY]: 
  - Batch: Atomic multi-file edits (`batch-edit`). ✅
  - Verify: Auto-revert on test failure (`--verify`). ✅
  - Strict: Optimistic Locking + No Fuzzy Writes. ✅
P12.5 [SAFETY/INTEL]:
  - Undo: Persistent Rollback (`cerberus undo`). ✅
  - JIT: Output footers guide next steps ("Whisper Protocol"). ✅
  - Guard: Blocks deleting referenced symbols. 🔜
  - Smart Merge: Auto-resolves non-overlapping AST conflicts. 🔜
  - Anchors: Standardized headers `[File: X] [Symbol: Y]` ("GPS"). 🔜
P13 [PREDICTIVE]:
  - Blueprint: Visual ASCII Trees + Dependency Overlay + Churn. 🔜

## 🛠 COMMAND QUICKREF
# 1. ORIENT (Map)
cerberus blueprint src/main.py --visual    # Architecture Map (Phase 13)
cerberus tree --depth 2                    # File Hierarchy

# 2. READ (Flashlight)
cerberus retrieval get-symbol AuthConfig   # Get Code + Docstring
cerberus retrieval search "login error"    # Semantic Search
cerberus symbolic deps AuthConfig          # Who does this call?
cerberus symbolic references AuthConfig    # Who calls this?

# 3. WRITE (Scalpel)
# ATOMIC BATCH (Preferred):
cerberus mutations batch-edit ops.json --verify "pytest tests/" --preview
# JSON Format: [{"op": "edit", "file": "...", "symbol": "...", "code": "..."}]

# UNDO (Safety Net):
cerberus mutations undo                    # Revert last batch

## 🧠 SYMBOLIC INTELLIGENCE
- **JIT Guidance:** Follow the `[Tip]` footer in commands for correct syntax. ✅
- **Diff Feedback:** All edits return Unified Diffs. Review them before confirming. ✅
- **Style Guard:** Simple lint errors (whitespace/imports) are auto-fixed. Don't waste turns fixing them. 🔜
- **Context Anchors:** Coming soon to ground large-context models. 🔜

## ⚙️ CONFIGURATION
- `CERBERUS_MACHINE_MODE=1`: Force JSON output (Default).
- `CERBERUS_SILENT_METRICS=1`: Hide `[Meta]` token stats.
- `CERBERUS_HUMAN_MODE=1`: Opt-in to rich text/tables (Not for Agents).