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

## 🔒 ENFORCEMENT PROTOCOL [ZERO TOLERANCE]

**BEFORE USING ANY TOOL - CHECK THIS DECISION TREE:**
```
┌────────────────────────────────────────┐
│ Do you need to read/search/explore?    │
└──────────────┬─────────────────────────┘
               │
               ├─ Code/Config? ────→ USE CERBERUS (mandatory)
               ├─ Documentation? ──→ Read tool OK (see exceptions)
               └─ Git/Build/Test? ─→ Bash OK (non-file operations)
```

**ABSOLUTE PROHIBITIONS (These Tools Are BANNED):**

| ❌ FORBIDDEN TOOL      | ✅ MUST USE INSTEAD                    | Zero Exceptions  |
|------------------------|----------------------------------------|------------------|
| `Read` (code >50L)     | `cerberus dogfood read --lines`        | STRICT           |
| `grep` / `rg`          | `cerberus retrieval search`            | STRICT           |
| `Glob` / `find`        | `cerberus tree` / `get-symbol`         | STRICT           |
| `cat` / `head` / `tail`| `cerberus dogfood read --lines`        | STRICT           |
| `Edit` / `Write` (code)| `cerberus mutations batch-edit`        | STRICT           |
| `ls -R` / `tree` (cmd) | `cerberus dogfood tree`                | STRICT           |

**COMPLIANCE CHECKLIST (Every Time You Use a Tool):**
1. **STOP:** Is this file/code exploration or mutation?
2. **CHECK:** Does a Cerberus command exist for this? (Answer: YES, 99% of time)
3. **COMPLY:** Use the Cerberus command from the table above.
4. **VERIFY:** Did I violate this in the last 5 actions? If yes, REDO immediately.

**WHY THIS IS CRITICAL:**
- Violating = Breaking dogfooding (you're not testing what agents use)
- Violating = Bypassing safety (no undo, ledger, verification)
- Violating = Wasting tokens (no session metrics)
- Violating = Defeating symbiosis (Cerberus IS the agent OS, not a helper)

**MENTAL MODEL:**
You are NOT a human with access to Cerberus.
You ARE an AI agent whose ONLY interface to code is Cerberus commands.

**SELF-AUDIT (Every 10 Actions):**
Ask yourself:
- "Have I used `Read` directly on code files?" → VIOLATION
- "Have I used `grep`/`Glob` for code search?" → VIOLATION
- "Did I use `Edit`/`Write` instead of `batch-edit`?" → VIOLATION

If YES to any → Acknowledge violation, redo with Cerberus, then continue.

## ⚠️ EXCEPTIONS [NARROW & EXPLICIT]

**Documentation Files ONLY:**
- `.md`, `.txt`, `.rst`, `.LICENSE` files → `Read` tool is permitted
- **Reason:** No code symbols, not indexed (by design)
- **Scope:** ONLY for reading project documentation/specs
- **Future:** Phase 14 will add doc indexing for full dogfooding

**Everything Else:** ZERO exceptions. Use Cerberus exclusively.

## 🔄 DAEMON MANAGEMENT [REQUIRED]
**AT SESSION START - CHECK FIRST:**
1. Status: `cerberus watcher status` - Returns PID if running.
2. Start ONLY if stopped: `cerberus watcher start`
3. NEVER start multiple watchers → Performance catastrophe (logs, CPU).

**HEALTH MONITORING (Required During Session):**
Check health BEFORE: batch operations, index updates, every 10 commands.
```bash
cerberus watcher health --json
# Returns: {"status": "healthy|warning|critical", "log_size_mb": 2.5, "cpu_percent": 15}
```

**Thresholds (Auto-Stop if Critical):**
- Log > 50MB = CRITICAL (rotation failure) → Watcher auto-stops
- CPU > 80% = CRITICAL (runaway process) → Watcher auto-stops
- Log > 20MB or CPU > 50% = WARNING (monitor closely)

**If Watcher Auto-Stopped:**
```
⚠️ WATCHER STOPPED: [reason]

Options:
1. Clean logs and restart: cerberus clean --preserve-index && cerberus watcher start
2. Investigate logs: cerberus watcher logs
3. Continue without watcher
```

**Commands:**
cerberus watcher status    # Check daemon state
cerberus watcher start     # Start if not running
cerberus watcher stop      # Stop daemon
cerberus watcher health    # Check health (log size, CPU)
cerberus watcher logs      # View daemon logs

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