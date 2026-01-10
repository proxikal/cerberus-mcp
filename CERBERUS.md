# CERBERUS v0.13.0 - AI Agent Operating System
# Protocol: UACP/1.2 | Fidelity: 100% | Mode: Machine-First (JSON) | Arch: AST/SQLite

## ⚡ CORE MANDATES [REQUIRED]
MISSION: 100% Signal / 0% Noise. Deterministic AST > LLM Guesswork.
PRINCIPLES:
  1. Code > Prompts: Use `get-symbol` (AST), never `read_file` (Text).
  2. Verified Transactions: writes MUST use `--verify` to prevent regression.
  3. Strict Resolution: No auto-correct on mutations. Ambiguity = Error.
  4. Symbiosis: Use `blueprint` (Map) before `read` (Flashlight).
  5. Parse-Perfect Output: All outputs must be LLM-parsable with >98% accuracy.

## 🚫 FORBIDDEN [STRICT]
- `cat/read_file` on full files (>50 lines). USE: `blueprint` or `read --lines`.
- `grep`. USE: `cerberus search` (Semantic/Hybrid).
- `ls -R`. USE: `cerberus tree`.
- Speculative/Unverified Edits. USE: `batch-edit --verify`.
- Deleting/editing referenced symbols WITHOUT checking deps. (Symbol Guard: ✅ Phase 13.2).

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

## 🚨 VIOLATION DETECTION & REMEDIATION [ACCOUNTABILITY]

**When You (User) Catch Me Violating:**
1. I MUST immediately acknowledge the specific violation
2. I MUST explain which rule was broken and why I broke it
3. I MUST redo the action using the correct Cerberus command
4. I MUST document the correct approach for future sessions

**When I Catch Myself Mid-Action:**
1. Stop immediately and cancel the violating action
2. Acknowledge the near-violation publicly
3. Show the correct Cerberus command
4. Execute correctly before proceeding

**Violation Log (Transparency):**
If violations occur, maintain a session log:
```markdown
## Protocol Adherence Log
- ✅ cerberus blueprint facade.py (correct)
- ❌ Read(schema.py) - VIOLATION - Corrected to: cerberus retrieval get-symbol
- ✅ cerberus dogfood tree (correct)
```

**Zero Tolerance Means:**
- No "just this once" exceptions
- No "it's faster this way" justifications
- No silent bypasses when tools fail
- Every violation gets corrected, not excused

## 🔧 ERROR HANDLING [WHEN CERBERUS COMMANDS FAIL]

**CRITICAL RULE: Never silently fall back to forbidden tools.**

**If a Cerberus command fails, follow this escalation:**

```
┌─────────────────────────────────────────────┐
│ Cerberus command failed with error         │
└──────────────┬──────────────────────────────┘
               │
               ├─ 1. Try Alternative Cerberus Command
               │    └─ dogfood read failed? → retrieval get-symbol
               │    └─ search failed? → tree + manual inspection
               │    └─ blueprint failed? → get-symbol on specific symbols
               │
               ├─ 2. Report Error to User
               │    └─ "⚠️ Cerberus command failed: [error]"
               │    └─ "I need access to [file]. Options:"
               │    └─ "  1. Debug the Cerberus error"
               │    └─ "  2. Use alternative: [command]"
               │    └─ "  3. File a bug if this is unexpected"
               │    └─ "Which approach should I take?"
               │
               └─ 3. NEVER Use Forbidden Tools Without Approval
                    └─ If user approves bypass → Note in violation log
                    └─ If no approval → Wait for guidance
```

**Common Errors & Correct Responses:**

| Error Scenario | ❌ WRONG Response | ✅ CORRECT Response |
|----------------|------------------|---------------------|
| `dogfood read` crashes | Use `Read` tool silently | Report error + try `get-symbol` |
| Symbol not in index | Use `grep` to find it | Report + suggest re-indexing |
| Index corrupted | Read files directly | Report + suggest `cerberus index .` |
| Command not implemented | Fall back to bash | Ask user for guidance |

**Debugging Over Bypassing:**
- Cerberus bugs are opportunities to improve the system
- Bypassing defeats the dogfooding purpose
- Every error should result in either: fix, workaround docs, or user escalation

## 📋 SYSTEMATIC SELF-AUDIT [TRIGGER POINTS]

**Mandatory Audit Moments:**

1. **Every 10 Tool Calls:**
   - Review last 10 actions in detail
   - Check for any Read/grep/Glob on code files
   - Verify all file operations used Cerberus commands

2. **After Any Tool Error:**
   - Did the error tempt me to bypass?
   - Did I use the error handling protocol above?
   - Is there a pattern of failures that needs reporting?

3. **Before Major Operations:**
   - Before batch edits: Confirm all reads were via Cerberus
   - Before commits: Scan session for protocol violations
   - Before ending session: Final compliance check

4. **Pattern Detection:**
   - Am I repeatedly using the same forbidden tool?
   - Am I finding "reasons" to bypass frequently?
   - Are Cerberus commands failing more than they should?

**Self-Audit Checklist:**
```markdown
□ No Read tool on .py/.js/.ts/.go files
□ No grep/rg commands for code search
□ No Glob/find for code file discovery
□ No Edit/Write without batch-edit
□ All errors escalated, not bypassed
□ All violations logged and corrected
```

**If Audit Fails:**
- Immediately stop current task
- Correct all violations in reverse chronological order
- Resume only after full compliance restored

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
  - Guard: Risk-aware mutation protection with Phase 13.2 stability integration. ✅
  - Smart Merge: Auto-resolves non-overlapping AST conflicts. 🔜
  - Anchors: Standardized headers `[File: X] [Symbol: Y]` ("GPS"). 🔜
P13 [PREDICTIVE]:
  - Blueprint: Visual ASCII Trees + Dependency Overlay (Confidence Scores). ✅ (Phase 13.1)
  - Intelligence: Complexity Metrics (cyclomatic, nesting, branches). ✅ (Phase 13.1)
  - Caching: Mtime-based with TTL + cache invalidation. ✅ (Phase 13.1)
  - JSON Export: Machine-readable blueprint format. ✅ (Phase 13.1)
  - Stability: Git Churn + Test Coverage + Composite Risk Scoring. ✅ (Phase 13.2)
  - Analysis: Structural Diffs + Cycle Detection + Auto-Hydration. 🔜 (Phase 13.3+)

## 🛠 COMMAND QUICKREF
# 1. ORIENT (Map - Use This First)
# Phase 13.1 - Implemented:
cerberus retrieval blueprint src/main.py                    # Structure only (fast)
cerberus retrieval blueprint src/main.py --deps             # + Dependencies with confidence ✅
cerberus retrieval blueprint src/main.py --meta             # + Complexity metrics ✅
cerberus retrieval blueprint src/main.py --format tree      # ASCII tree format ✅
cerberus retrieval blueprint src/main.py --format json      # Machine-readable JSON ✅
cerberus retrieval blueprint src/main.py --no-cache         # Skip cache ✅
cerberus retrieval blueprint src/main.py --fast             # Skip expensive analysis ✅

# Phase 13.2 - Implemented:
cerberus retrieval blueprint src/main.py --churn            # + Git churn (edits/week, authors, recency) ✅
cerberus retrieval blueprint src/main.py --coverage         # + Test coverage (percent, test files) ✅
cerberus retrieval blueprint src/main.py --stability        # + Risk score (🟢 SAFE/🟡 MEDIUM/🔴 HIGH RISK) ✅

# Phase 13.3+ - Future:
cerberus retrieval blueprint src/main.py --diff HEAD~5      # Structural changes 🔜
cerberus retrieval blueprint src/ --aggregate               # Package-level view 🔜

# Other orientation commands:
cerberus dogfood tree --depth 2                             # File Hierarchy

# 2. READ (Flashlight - After Orient)
cerberus retrieval get-symbol AuthConfig   # Get Code + Docstring
cerberus retrieval search "login error"    # Semantic Search
cerberus symbolic deps AuthConfig          # Who does this call?
cerberus symbolic references AuthConfig    # Who calls this?

# 3. WRITE (Scalpel)
# ATOMIC BATCH (Preferred):
cerberus mutations batch-edit ops.json --verify "pytest tests/" --preview
# JSON Format: [{"op": "edit", "file": "...", "symbol": "...", "code": "..."}]

# SINGLE MUTATIONS (Symbol Guard protected - Phase 13.2):
cerberus mutations edit file.py --symbol foo --code "def foo(): pass"
cerberus mutations delete file.py --symbol bar           # Blocked if HIGH RISK
cerberus mutations delete file.py --symbol bar --force   # Override Symbol Guard (use carefully)

# UNDO (Safety Net):
cerberus mutations undo                    # Revert last batch

## 🧠 SYMBOLIC INTELLIGENCE

### Output Quality Standards (Parsability Requirement)
- **Agent Interpretation Accuracy:** >98% (hallucination rate <2%).
- **Validation Method:** Test outputs against GPT-4/Claude to verify correct extraction of:
  - Dependencies and call relationships
  - Symbol hierarchies and structure
  - Metadata (complexity, coverage, churn, stability)
- **Design Principle:** Unambiguous formats only. If agents misinterpret, the OUTPUT is wrong, not the agent.

### Agent Guidance Features
- **JIT Guidance:** Follow the `[Tip]` footer in commands for correct syntax. ✅
- **Diff Feedback:** All edits return Unified Diffs. Review them before confirming. ✅
- **Confidence Scores:** All dependencies show provenance (✓1.0 = certain, ✓0.6 = verify). ✅
- **Stability Scoring:** Composite risk metrics (🟢 Safe, 🟡 Medium, 🔴 High Risk). ✅ (Phase 13.2)
- **Symbol Guard:** Blocks HIGH RISK mutations, warns on MEDIUM risk, allows SAFE (use --force to override). ✅ (Phase 13.2)
- **Style Guard:** Simple lint errors (whitespace/imports) are auto-fixed. Don't waste turns fixing them. 🔜
- **Context Anchors:** Coming soon to ground large-context models. 🔜

## 🎯 QUALITY ASSURANCE [STANDARDS]

### Parsability Standard (Agent-First Design)
**Mandate:** All Cerberus outputs must be machine-parsable with >98% accuracy.

**What This Means:**
- When an LLM reads Cerberus output, it must extract information correctly >98% of the time
- Hallucination rate for relationships/dependencies must be <2%
- Ambiguity in output format = Bug in Cerberus, not the agent

**Validation Process:**
1. For each new command/feature, generate 100 test outputs
2. Run through GPT-4/Claude with extraction prompts
3. Compare extracted data to ground truth
4. If accuracy < 98%, redesign the output format

**Examples:**
```bash
# GOOD: Unambiguous dependency list
[Calls: stripe.charge ✓1.0, DB.save ✓1.0]
# Agent extracts: ["stripe.charge", "DB.save"] - 100% accurate

# BAD: Ambiguous prose
"This function probably calls stripe and might update the database"
# Agent might hallucinate: calls redis, calls cache - accuracy <80%
```

**Application:**
- Blueprint outputs (Phase 13) - structured trees, clear delimiters
- Dependency listings (Phase 5) - confidence scores, explicit targets
- Diff outputs (Phase 12) - unified format, clear change markers
- All JSON exports - strict schema validation
- Error messages and guidance - actionable, unambiguous

**Testing:**
- Automated: Include parsability tests in CI/CD
- Manual: During dogfooding, track agent misinterpretations
- Continuous: Log when agents request re-clarification (indicates ambiguity)

**Failure Response:**
If parsability < 98%:
- ❌ Don't blame the LLM ("GPT-4 is stupid")
- ✅ Redesign the output ("Our format is ambiguous")
- ✅ Add delimiters (`[Calls: A, B]` not "calls A and B")
- ✅ Use structured formats (JSON, tables, strict syntax)

## ⚙️ CONFIGURATION
- `CERBERUS_MACHINE_MODE=1`: Force JSON output (Default).
- `CERBERUS_SILENT_METRICS=1`: Hide `[Meta]` token stats.
- `CERBERUS_HUMAN_MODE=1`: Opt-in to rich text/tables (Not for Agents).
## 📊 TOKEN SAVINGS TRACKING

Every Cerberus command automatically tracks token savings vs. reading full files.

**Features:**
- **Per-Task Tracking**: Shows tokens saved for each individual task (resets after display)
- **Session Accumulation**: Tracks cumulative savings across the entire session
- **Dollar Conversion**: Displays cost savings in USD (Claude Sonnet 4.5 pricing)
- **Auto-Reset**: Session resets after 1 hour of inactivity (configurable)

**Output Format (Machine Mode - Default):**
```
[Task] Saved: 1,500 tokens (~$0.0045) | Efficiency: 83.3%
[Session] Saved: 8,043,223 tokens (~$24.13) | Efficiency: 92.1%
```

**Configuration:**
- `CERBERUS_NO_TRACK=true` - Disable tracking entirely
- `CERBERUS_SESSION_TIMEOUT=3600` - Session timeout in seconds (default: 1 hour)
- `CERBERUS_SILENT_METRICS=1` - Hide token savings output

**Pricing (as of Jan 2026):**
- Input tokens: $3.00 per 1M tokens
- Output tokens: $15.00 per 1M tokens
- Savings calculated using input token pricing (conservative estimate)

**How It Works:**
1. Each Cerberus command records tokens that would have been used with `Read` tool
2. Per-task metrics accumulate during operations and display after each task
3. Session metrics accumulate continuously and persist to `.cerberus_session.json`
4. After 1 hour of inactivity, session automatically resets
5. Task metrics reset after each display, session metrics continue accumulating
