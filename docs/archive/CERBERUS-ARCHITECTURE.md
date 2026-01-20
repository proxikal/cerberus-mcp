# CERBERUS - ARCHITECTURE & CONFIGURATION

**Module Type:** On-Demand (load when you need internals/config details)
**Core Reference:** See CERBERUS.md for tool selection and workflows
**Purpose:** Deep dive into Cerberus internals, configuration, and operational limits

---

## ARCHITECTURE

### Startup Sequence

```
cerberus start:
  Index check/build → Daemon start → Watcher start → Memory load
  All components auto-initialize. Agents just run commands.
```

### Data Flow

```
Agent → CLI → Daemon (if running) → Index → Response
            ↓
       Thin client auto-routes to daemon when available
       Falls back to direct execution if daemon unavailable
```

### Components

```
┌─────────────────────────────────────────────────────────────────────┐
│ INDEX: SQLite (symbols/metadata) + FAISS (embeddings)              │
│   - Location: .cerberus/                                           │
│   - Build: cerberus index .                                        │
│   - Update: cerberus update (incremental, git-aware)               │
├─────────────────────────────────────────────────────────────────────┤
│ DAEMON: Background server for zero-latency queries                 │
│   - Auto-starts via cerberus start                                 │
│   - RPC protocol for structured communication                      │
│   - Manages sessions internally (no agent action needed)           │
├─────────────────────────────────────────────────────────────────────┤
│ WATCHER: File system monitor                                       │
│   - Triggers re-index on file changes                              │
│   - Control: cerberus watcher start|stop|status                    │
│   - Auto-stops on high CPU/log bloat (see CONFIGURATION)           │
├─────────────────────────────────────────────────────────────────────┤
│ SESSIONS: Automatic agent tracking (internal to daemon)            │
│   - Created automatically when daemon starts                       │
│   - Timeout: CERBERUS_SESSION_TIMEOUT env var (default: 3600s)     │
│   - Tracks: query count, activity, idle cleanup                    │
├─────────────────────────────────────────────────────────────────────┤
│ MEMORY: Persistent developer preferences (Phase 18)                │
│   - Profile: coding style, patterns (4KB limit)                    │
│   - Decisions: architectural choices with rationale (per-project)  │
│   - Corrections: learned mistakes to avoid                         │
│   - Access: cerberus memory context                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## CONFIGURATION

### Environment Variables

```
CERBERUS_MACHINE_MODE=1         # Force JSON output (default for agents)
CERBERUS_HUMAN_MODE=1           # Rich text/tables (not for agents)
CERBERUS_SILENT_METRICS=1       # Hide token stats in output
CERBERUS_NO_TRACK=true          # Disable token tracking entirely
CERBERUS_NO_METRICS=true        # Disable efficiency metrics collection
CERBERUS_SESSION_TIMEOUT=N      # Session timeout in seconds (default: 3600)
CERBERUS_ANCHORS=json|compact|text|off  # Anchor output mode (default: json)
```

### Index Limits (Bloat Protection)

**Default Limits (conservative - prevents runaway indexing):**

```
CERBERUS_MAX_FILE_BYTES=1048576         # 1MB per file
CERBERUS_MAX_SYMBOLS_PER_FILE=500       # Symbols per file (truncates excess)
CERBERUS_MAX_TOTAL_SYMBOLS=100000       # Total symbols in index (stops at limit)
CERBERUS_MAX_INDEX_SIZE_MB=100          # SQLite DB size
CERBERUS_MAX_VECTORS=100000             # FAISS vector count
CERBERUS_MIN_FREE_DISK_MB=100           # Pre-flight disk check
CERBERUS_WARN_THRESHOLD=0.80            # Warning at 80% of limits
CERBERUS_LIMITS_STRICT=false            # true = fail on warnings
```

**Override for Large Projects:**

```bash
# Via environment
CERBERUS_MAX_TOTAL_SYMBOLS=500000 cerberus index .

# Via CLI flags
cerberus index . --max-total-symbols 500000
cerberus index . --show-limits        # Display current limits and exit
cerberus index . --skip-preflight     # Skip disk/permission checks
cerberus index . --strict             # Exit with error on validation warnings
cerberus index . --max-bytes N        # Override max file size
cerberus index . --max-symbols-per-file N
```

**Enforcement Phases:**

```
1. Pre-flight: Disk space, permissions (run_preflight_checks)
2. Real-time: Per-file limits, total symbol limit (BloatEnforcer)
3. Post-index: Validation health check (validate_index_health)
```

### Protocol Refresh Tracking (AI Memory)

**Purpose:** Prevent AI agent protocol degradation over long sessions.
Auto-suggests refresh after threshold commands/time.

**Thresholds:**

```
Commands: 20 cerberus commands without refresh → hint
Time: 10 minutes without refresh → hint
Stale: 30 minutes since last refresh → hint
```

**State File:** `.cerberus_protocol.json` (session-based, 1hr expiry)

**Refresh Levels:**

```
light (~150 tokens): Critical rules only - TOOL SELECTION + FORBIDDEN
rules (~300 tokens): Tool selection table + core rules + violations
full (~1500+ tokens): Complete CERBERUS.md reload
```

**When to Refresh:**

```
- After context compaction (agent memory summarized)
- When hint suggests "Protocol memory may be degraded"
- Before complex multi-file operations
- If unsure which cerberus command to use
```

### Operational Limits

**Watcher Thresholds:**

```
Log >10MB or CPU >50%: CRITICAL (auto-stops)
Log >5MB or CPU >15%: WARNING
Recovery: cerberus clean --preserve-index && cerberus watcher start
```

**Token Tracking:**

```
Output format: [Task] Saved: N tokens (~$X) | Efficiency: Y%
Pricing: $3.00/1M input, $15.00/1M output (Claude Sonnet 4.5)
Storage: .cerberus_session.json (auto-resets after 1hr inactivity)
```

**Metrics Storage:**

```
Location: ~/.config/cerberus/metrics/
Privacy: All data local, no telemetry
Tracked: command counts, flag usage, workflow patterns, token savings
```

### Efficiency Hints

**Purpose:** Non-blocking suggestions in command output

**Trigger Conditions:**

```
- get-symbol returns >500 lines without --snippet
- blueprint without --with-memory when memory has relevant data
- edit without --check-corrections when corrections exist
- index is stale (>60 min old)
```

**Usage:** JSON output includes "hints" array. Process only "results" to ignore hints.

---

## OUTPUT STANDARDS

### Parsability

```
PARSABILITY: >98% agent extraction accuracy required
CONFIDENCE: Dependencies show scores (✓1.0=certain, ✓0.6=verify)
STABILITY: Risk levels (🟢 Safe, 🟡 Medium, 🔴 High Risk)
ANCHORS: GPS + deps + risk + temporal + safety metadata in outputs
FORMAT: Unambiguous delimiters, structured data, strict schemas
```

### Symbol Guard

```
🟢 SAFE: Mutation allowed
🟡 MEDIUM: Warning shown, mutation allowed
🔴 HIGH: Mutation BLOCKED (use --force to override)
Factors: Reference count, stability score, test coverage
```

---

## FEATURE STATUS

```
P1-11  [CORE]     Indexing (SQLite/FAISS), Retrieval (Hybrid), Editing (AST) ✓
P12    [HARMONY]  Batch edits, --verify, Optimistic Locking, No Fuzzy Writes ✓
P12.5  [SAFETY]   Undo, JIT Guidance, Symbol Guard, Risk Protection ✓
P13    [PREDICT]  Blueprint, Overlays, Caching, Cycles, Hydration, Aggregation ✓
P14    [PRODUCT]  Style Guard, Context Anchors, Hallucination Detection, Predictions ✓
P16    [REHAB]    Token Tracking, Facade Fixes, Prerequisite Warnings ✓
P18    [MEMORY]   Session Memory: Profile, Decisions, Corrections, Prompts, Context ✓
P19.1  [WORKFLOW] Streamlined Entry: start, go, orient commands ✓
P19.2  [HINTS]    Smart Defaults & Auto-Suggestions ✓
P19.3  [METRICS]  Efficiency Metrics & Observability ✓
P19.4  [DEBT]     Technical Debt Audit: Consolidated duplicates, verified health ✓
P19.5  [DOCS]     Self-Maintaining Docs: validate-docs command ✓
P19.6  [BLOAT]    Index Limits: Preflight, Enforcement, Validation (100K default cap) ✓
P19.7  [REFRESH]  Protocol Refresh: AI memory restoration, auto-hints after 20 cmds ✓
```

---

**Version:** 1.0 (2026-01-11)
**Origin:** Extracted from CERBERUS.md v0.20.1
**Purpose:** On-demand architecture and configuration reference
**Maintainer:** Proxikal + AI Agents
