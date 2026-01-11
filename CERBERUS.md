# CERBERUS v0.20.0 | UACP/1.2 | Machine-First Protocol
# Arch: AST/SQLite/FAISS | Tests: 610 pass | Updated: 2026-01-10
# Mission: 100% Signal, 0% Noise. Deterministic AST > LLM Guesswork.

---

## AGENT ETIQUETTE [CRITICAL - ALL AGENTS MUST FOLLOW]

```
PURPOSE: This section governs how AI agents interact with and maintain CERBERUS.md.
         Violation of these rules degrades the protocol for all future agents.

IDENTITY: You are an AI agent whose ONLY interface to code is Cerberus commands.
FIDELITY: This file is the single source of truth. Follow every rule without exception.

DOCUMENT_RULES:
  1. SINGLE_SOURCE: This file is the ONLY source of truth for Cerberus usage
  2. NO_DUPLICATION: Never add info that exists elsewhere in this file
  3. NO_PROSE: Use structured formats (tables, code blocks, lists) - not paragraphs
  4. NO_EXAMPLES_OUTPUT: Do not add sample command outputs - only command syntax
  5. MACHINE_FIRST: Optimize for LLM parsing, not human readability
  6. CONSOLIDATE: New features go in existing sections, not new sections

ADDING_CONTENT:
  - New command? → Add to COMMAND REFERENCE under correct category
  - New env var? → Add to CONFIGURATION section
  - New rule? → Add to RULES section (check if rule already exists first)
  - New phase? → Add single line to FEATURE STATUS
  - NEVER create new top-level sections without explicit user approval

FORBIDDEN_ADDITIONS:
  - Human-readable output examples (wastes tokens)
  - Explanatory prose (use terse rules instead)
  - Duplicate information (search document first)
  - Emoji descriptions (use symbols: ✓ ✗ only)
  - Marketing language or feature descriptions

BEFORE_EDITING:
  1. Read ENTIRE document first
  2. Search for existing coverage of your topic
  3. Identify the ONE correct location for new content
  4. Add minimally - fewest tokens that convey the information

VERSIONING:
  - Increment patch version (0.19.X) for any content change
  - Update test count in header if tests added
  - Update date in header on every edit
```

---

## ARCHITECTURE

```
STARTUP (cerberus start):
  Index check/build → Daemon start → Watcher start → Memory load
  All components auto-initialize. Agents just run commands.

DATA FLOW:
  Agent → CLI → Daemon (if running) → Index → Response
              ↓
         Thin client auto-routes to daemon when available
         Falls back to direct execution if daemon unavailable

COMPONENTS:
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
│   - Profile: coding style, patterns                                │
│   - Decisions: architectural choices with rationale                │
│   - Corrections: learned mistakes to avoid                         │
│   - Access: cerberus memory context                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## RULES

### Tool Selection [MANDATORY]

```
╔═══════════════════════════╦═══════════════════════════════════════════════════╗
║ TASK                      ║ REQUIRED TOOL                                     ║
╠═══════════════════════════╬═══════════════════════════════════════════════════╣
║ Understand file structure ║ cerberus blueprint (77-95% savings vs full read)  ║
║ Find symbol locations     ║ cerberus search (98% savings vs grep+read)        ║
║ Track who calls what      ║ cerberus references (90% savings vs manual grep)  ║
║ Get code for editing      ║ Direct Read tool with line numbers                ║
║ Edit/write code           ║ Direct Edit/Write tool                            ║
║ Read .md/.txt/.rst files  ║ Direct Read tool (not indexed)                    ║
║ Git/Build/Test operations ║ Bash tool                                         ║
╚═══════════════════════════╩═══════════════════════════════════════════════════╝

FORBIDDEN: get-symbol for code retrieval (1100% overhead vs direct Read)
PERMITTED: get-symbol --snippet --exact (sparingly, for AST context only)
```

### Core Rules

```
1. EXPLORE>EXTRACT: Blueprint/search/references for exploration. Direct Read for code.
2. VERIFY_WRITES: All mutations MUST use --verify to prevent regression
3. STRICT_RESOLUTION: No auto-correct on mutations. Ambiguity = Error
4. MAP_FIRST: Blueprint first, THEN direct Read for specific lines
5. PARSE_PERFECT: All outputs LLM-parsable >98% accuracy
6. DEPS_CHECK: Never delete/edit referenced symbols without checking deps
```

### Violation Protocol

```
ON_DETECT: Stop → Acknowledge violation → Redo with Cerberus → Continue
ON_ERROR: Try alt Cerberus cmd → Report to user → NEVER silent fallback
ON_CATCH_SELF: Cancel action → Show correct command → Execute correctly
AUDIT_FREQ: Every 10 tool calls, review compliance
```

### Output Standards

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

### Risk Prevention [AGENT PRE-FLIGHT]

```
BEFORE IMPLEMENTING, WARN DEVELOPER IF:
  1. FILE_LOGGING: Adding always-on file logging or disk writes
  2. UNBOUNDED_STORAGE: Caching/storage without size limits or rotation
  3. IMPORT_SIDE_EFFECTS: Code that runs on every import (not lazy)
  4. BACKGROUND_PROCESSES: Daemons/watchers without auto-shutdown
  5. ROOT_FILE_CREATION: Creating files outside .cerberus/ directory
  6. LARGE_DEFAULTS: Default values >1MB or >1000 items

WARNING FORMAT (context-light):
  ⚠️ RISK: [CATEGORY] - [1-line description]
  IMPACT: [potential consequence]
  SAFER: [alternative approach]
  PROCEED? [wait for user confirmation]

HISTORICAL ISSUES (learn from past):
  - Phase 17: Logging on import → 3.3GB bloat
  - Always validate: rotation limits, retention policies, lazy init
```

---

## WORKFLOW

```
RECOMMENDED SEQUENCE:
1. cerberus start              # Initialize (see ARCHITECTURE for what this does)
2. cerberus orient [dir]       # Understand project structure
3. cerberus go <file>          # Analyze specific file, get line numbers
4. Direct Read lines X-Y       # Get actual code for editing
5. Direct Edit                 # Make changes
6. cerberus mutations --verify # Verify changes don't break tests

ALTERNATIVE (without streamlined commands):
1. cerberus memory context     # Load developer preferences
2. cerberus blueprint <file>   # Understand file structure
3. cerberus search "<query>"   # Find specific symbols
4. Direct Read lines X-Y       # Get code
5. Direct Edit                 # Make changes
```

---

## COMMAND REFERENCE

### Session & Lifecycle

```bash
cerberus start                              # Initialize session (index + daemon + watcher + memory)
cerberus start --json                       # Machine-parsable status
cerberus update                             # Reindex changed files
cerberus clean --preserve-index             # Clean cache, keep index
cerberus validate-docs                      # Validate CERBERUS.md sync
cerberus validate-docs --json --strict      # Machine output, strict mode
```

### Orientation & Exploration

```bash
# Quick orientation
cerberus orient [dir]                       # Project overview, hot spots, recent changes
cerberus orient --json                      # Machine-parsable
cerberus go <file>                          # Blueprint + suggested read commands
cerberus go <file> --threshold 50           # Custom "heavy" symbol threshold (default: 30)
cerberus go <file> --json                   # Machine output with quick_reads array

# Blueprint - Structure Analysis
cerberus blueprint <file>                   # Base structure with line numbers
cerberus blueprint <file> --deps            # + Dependencies with confidence scores
cerberus blueprint <file> --meta            # + Complexity metrics
cerberus blueprint <file> --churn           # + Git history (edits/authors)
cerberus blueprint <file> --coverage        # + Test coverage (needs coverage.json)
cerberus blueprint <file> --stability       # + Risk score
cerberus blueprint <file> --cycles          # + Circular dependency detection
cerberus blueprint <file> --hydrate         # + Auto-include heavy deps
cerberus blueprint <file> --diff HEAD~1     # Structural diff vs git ref
cerberus blueprint <dir> --aggregate        # Package-level view
cerberus blueprint <file> --with-memory     # Include developer context
# Flags: --format tree|json, --no-cache, --fast, --max-width N, --collapse-private

# Search
cerberus search "<query>"                   # Semantic/hybrid search
cerberus search "<query>" --mode keyword    # Keyword-only search
cerberus search "<query>" --mode semantic   # Embedding-based search
cerberus search "<query>" --mode balanced   # Hybrid (default)

# Symbol lookup (USE SPARINGLY - high overhead)
cerberus get-symbol <name> --snippet --exact  # Raw code only, exact match
# Flags: --context N, --limit N, --show-callers (all opt-in)

# File tree
cerberus dogfood tree --depth N             # Directory structure
cerberus dogfood ls <path>                  # List files
cerberus dogfood grep "<pattern>" <path>    # Search in files
```

### Symbolic Analysis

```bash
cerberus symbolic deps <symbol>             # What does this symbol call?
cerberus symbolic references <symbol>       # What calls this symbol?
cerberus symbolic calls <symbol>            # Outgoing calls
cerberus symbolic inherit-tree <class>      # Inheritance hierarchy
cerberus symbolic descendants <class>       # Child classes
cerberus symbolic overrides <method>        # Override chain
cerberus symbolic call-graph <symbol>       # Full call graph
cerberus symbolic smart-context <symbol>    # Contextual information
cerberus symbolic trace-path <from> <to>    # Path between symbols
cerberus symbolic resolution-stats          # Type resolution statistics
```

### Mutations

```bash
# Batch operations (preferred)
cerberus mutations batch-edit ops.json --verify "pytest" --preview
# ops.json format: [{"op":"edit","file":"...","symbol":"...","code":"..."}]

# Single mutations
cerberus mutations edit <file> --symbol <name> --code "..."
cerberus mutations edit <file> --symbol <name> --code "..." --check-corrections
cerberus mutations delete <file> --symbol <name>
cerberus mutations delete <file> --symbol <name> --force  # Override HIGH RISK
cerberus mutations insert <file> --after <symbol> --code "..."
cerberus mutations undo                     # Revert last batch
cerberus mutations stats                    # Mutation statistics
```

### Quality

```bash
# Style checking
cerberus quality style-check <file>
cerberus quality style-check <dir> --recursive
cerberus quality style-fix <file>
cerberus quality style-fix <file> --preview
cerberus quality style-fix <file> --force
cerberus quality style-fix <file> --verify "pytest"

# Predictions
cerberus quality related-changes <symbol>
cerberus quality related-changes <symbol> --file <path> --verbose --json
cerberus quality prediction-stats
cerberus quality prediction-stats --window 600 --limit 50 --json
```

### Memory

```bash
# Learn preferences
cerberus memory learn "prefer early returns"             # Style
cerberus memory learn -d "chose SQLite for portability"  # Decision
cerberus memory learn -c "always log before throw"       # Correction
cerberus memory learn --prompt "security" -t code-review # Prompt template

# View memory
cerberus memory show                        # Show all
cerberus memory show profile                # Preferences only
cerberus memory show decisions -p <project> # Project decisions
cerberus memory stats                       # Storage statistics

# Generate context
cerberus memory context                     # Full context
cerberus memory context --compact           # Minimal version
cerberus memory context -p <project> -t <task-type>

# Manage
cerberus memory edit profile                # Open in editor
cerberus memory forget "<key>"              # Remove preference
cerberus memory export -o backup.json       # Backup
cerberus memory import backup.json          # Restore
cerberus memory extract --from-git          # Extract from git history
```

### Protocol Refresh (AI Memory Restoration)

```bash
cerberus refresh                            # Light refresh (~150 tokens) - critical rules
cerberus refresh --rules                    # Standard refresh (~300 tokens) - tool selection + rules
cerberus refresh --full                     # Full CERBERUS.md reload (~1500+ tokens)
cerberus refresh --status                   # Check protocol tracking state
cerberus refresh --json                     # Machine-parsable output
```

### Watcher

```bash
cerberus watcher status                     # Check if watcher running
cerberus watcher start                      # Start file watcher
cerberus watcher stop                       # Stop watcher
cerberus watcher health --json              # Health metrics (log size, CPU)
```

### Metrics

```bash
cerberus metrics report                     # Last 7 days efficiency report
cerberus metrics report --days 30           # Custom period
cerberus metrics report --json              # Machine-parsable
cerberus metrics status                     # Collection status
cerberus metrics status --json              # Machine-parsable
cerberus metrics clear --yes                # Delete all metrics
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

```
DEFAULT LIMITS (conservative - prevents runaway indexing):
  CERBERUS_MAX_FILE_BYTES=1048576         # 1MB per file
  CERBERUS_MAX_SYMBOLS_PER_FILE=500       # Symbols per file (truncates excess)
  CERBERUS_MAX_TOTAL_SYMBOLS=100000       # Total symbols in index (stops at limit)
  CERBERUS_MAX_INDEX_SIZE_MB=100          # SQLite DB size
  CERBERUS_MAX_VECTORS=100000             # FAISS vector count
  CERBERUS_MIN_FREE_DISK_MB=100           # Pre-flight disk check
  CERBERUS_WARN_THRESHOLD=0.80            # Warning at 80% of limits
  CERBERUS_LIMITS_STRICT=false            # true = fail on warnings

OVERRIDE FOR LARGE PROJECTS:
  CERBERUS_MAX_TOTAL_SYMBOLS=500000 cerberus index .
  # OR via CLI:
  cerberus index . --max-total-symbols 500000

CLI FLAGS:
  --show-limits        # Display current limits and exit
  --skip-preflight     # Skip disk/permission checks
  --strict             # Exit with error on validation warnings
  --max-bytes N        # Override max file size
  --max-symbols-per-file N
  --max-total-symbols N

ENFORCEMENT PHASES:
  1. Pre-flight: Disk space, permissions (run_preflight_checks)
  2. Real-time: Per-file limits, total symbol limit (BloatEnforcer)
  3. Post-index: Validation health check (validate_index_health)
```

### Protocol Refresh Tracking (AI Memory)

```
PURPOSE: Prevent AI agent protocol degradation over long sessions.
         Auto-suggests refresh after threshold commands/time.

THRESHOLDS:
  Commands: 20 cerberus commands without refresh -> hint
  Time: 10 minutes without refresh -> hint
  Stale: 30 minutes since last refresh -> hint

STATE FILE: .cerberus_protocol.json (session-based, 1hr expiry)

REFRESH LEVELS:
  light (~150 tokens): Critical rules only - TOOL SELECTION + FORBIDDEN
  rules (~300 tokens): Tool selection table + core rules + violations
  full (~1500+ tokens): Complete CERBERUS.md reload

WHEN TO REFRESH:
  - After context compaction (agent memory summarized)
  - When hint suggests "Protocol memory may be degraded"
  - Before complex multi-file operations
  - If unsure which cerberus command to use
```

### Operational Limits

```
WATCHER THRESHOLDS:
  Log >10MB or CPU >50%: CRITICAL (auto-stops)
  Log >5MB or CPU >15%: WARNING
  Recovery: cerberus clean --preserve-index && cerberus watcher start

TOKEN TRACKING:
  Output format: [Task] Saved: N tokens (~$X) | Efficiency: Y%
  Pricing: $3.00/1M input, $15.00/1M output (Claude Sonnet 4.5)
  Storage: .cerberus_session.json (auto-resets after 1hr inactivity)

METRICS STORAGE:
  Location: ~/.config/cerberus/metrics/
  Privacy: All data local, no telemetry
  Tracked: command counts, flag usage, workflow patterns, token savings
```

### Command Prerequisites

```
--deps/--hydrate/--cycles: Requires symbol_references (run: cerberus index .)
--coverage: Requires coverage.json (run: pytest --cov=src --cov-report=json)
--churn/--diff: Requires git repository
--stability: Requires at least one of --meta, --churn, or --coverage
```

### Efficiency Hints

```
Hints are non-blocking suggestions in command output.
Trigger conditions:
  - get-symbol returns >500 lines without --snippet
  - blueprint without --with-memory when memory has relevant data
  - edit without --check-corrections when corrections exist
  - index is stale (>60 min old)

JSON output includes "hints" array. Process only "results" to ignore hints.
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

## END OF PROTOCOL

```
REMEMBER:
- This document is MACHINE-FIRST
- Follow AGENT ETIQUETTE when modifying
- When in doubt, use cerberus validate-docs to check
- Signal > Noise. Always.
```
