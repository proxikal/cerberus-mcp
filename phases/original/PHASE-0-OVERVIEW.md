# PHASE 0: ADAPTIVE LEARNING MEMORY SYSTEM - OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ⚠️  CRITICAL: PHASED ROLLOUT REQUIRED                            │
│                                                                     │
│  DO NOT build all phases at once. Follow 5-stage validation:      │
│                                                                     │
│  🔸 ALPHA (Weeks 1-2):  Phases 1-7 with JSON storage              │
│     Gate: 70%+ approval, 90%+ accuracy                             │
│                                                                     │
│  🔸 BETA (Weeks 3-4):   Phases 12-13, update 5-6 for SQLite       │
│     Gate: 80%+ token savings, 2+ weeks stable                      │
│                                                                     │
│  🔸 GAMMA (Weeks 5-6):  Phases 8, 10, 11 (enhancements)           │
│     Gate: Session continuity works, agent proposals 50%+           │
│                                                                     │
│  🔸 DELTA (Weeks 7-8):  Phases 14-15 (anchoring + mode detection) │
│     Gate: 90%+ example following, mode detection 85%+              │
│                                                                     │
│  🔸 EPSILON (Weeks 9-10): Phases 16-20 (critical fixes)           │
│     Gate: Integration works, 80%+ silent detection, <20s approval  │
│                                                                     │
│  Each phase must pass validation gates before proceeding.          │
│  Rollback to previous phase if gates fail.                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Vision
Revolutionary memory system that learns from user corrections automatically, stores intelligently, and injects contextually.

---

## TL;DR: 30-Second Summary

**What:** AI memory system that learns from you automatically, stores in SQLite FTS5, injects contextually.

**How:** 5-phase rollout
1. **Alpha (Weeks 1-2):** Validate learning pipeline with JSON (Phases 1-7)
2. **Beta (Weeks 3-4):** Migrate to SQLite FTS5 for scale (Phases 12-13, update 5-6)
3. **Gamma (Weeks 5-6):** Add enhancements (Phases 8, 10, 11)
4. **Delta (Weeks 7-8):** Dynamic anchoring + mode detection (Phases 14-15)
5. **Epsilon (Weeks 9-10):** Critical fixes (Phases 16-20: integration, lifecycle, approval, conflicts, silent divergence)

**Tech:**
- TF-IDF clustering (not embeddings) - lightweight, no downloads
- SQLite FTS5 (same as Cerberus code index) - scales to 10,000+ memories
- Template-based proposals (LLM optional) - works 100% without Ollama
- Dynamic anchoring (link rules to code examples) - addresses "text vs code disconnect"
- Mode detection (prototype/production/hotfix) - addresses "mode blindness"
- Silent divergence (catches 80% of corrections Phase 1 misses) - addresses Gemini's #1 critique
- 80% token savings (FTS5 search vs JSON load-all)

**Validation gates:** Each phase must pass metrics before proceeding (70%+ approval, 90%+ accuracy, 80%+ savings).

**Storage:** JSON (Alpha) → SQLite FTS5 (Beta) with backward compat.

**Start here:** Build Phase Alpha (Phases 1-7) with JSON storage. Validate. Then migrate.

---

## Problem Statement

**Current State:**
- AI agents repeat mistakes across sessions
- User corrections ignored ("keep it short" said 50+ times)
- Universal rules mixed with project-specific context
- Manual `memory_learn()` calls = forgotten 99% of time
- Token bloat from loading all memories

**Desired State:**
- Zero repeated corrections
- Automatic learning from user feedback AND agent observations
- Context-aware injection (2500 token budget: 1500 memories + 1000 session)
- Hierarchical storage (universal → language → project → task)
- Self-healing system (archive stale, detect conflicts, promote patterns)
- Session continuity (zero re-explanation between sessions)

---

## System Architecture

```
Session Cycle:
┌─────────────────────────────────────────────────────────────┐
│ 1. SESSION START                                            │
│    ├─ Auto-inject relevant memories (Phase 7: 1500 tokens)  │
│    ├─ Auto-inject session codes (Phase 8: 1000-1500 tokens) │
│    └─ Total budget: 2500-3000 tokens                        │
├─────────────────────────────────────────────────────────────┤
│ 2. DURING SESSION                                           │
│    ├─ Detect user corrections (Phase 1)                     │
│    ├─ Record agent observations (Phase 10)                  │
│    ├─ Capture session codes (Phase 8: impl, dec, block)     │
│    └─ No manual intervention required                       │
├─────────────────────────────────────────────────────────────┤
│ 3. SESSION END                                              │
│    ├─ Cluster user corrections (Phase 2)                    │
│    ├─ Detect agent patterns (Phase 10: success, failure)    │
│    ├─ Generate proposals (Phase 3: template-based, LLM opt) │
│    ├─ CLI approval (Phase 4: < 30 seconds)                  │
│    ├─ Store to hierarchical layers (Phase 5)                │
│    └─ Save session codes (Phase 8: no LLM, direct save)     │
│    └─ Total cost: 0-500 tokens (LLM optional)               │
├─────────────────────────────────────────────────────────────┤
│ 4. WEEKLY MAINTENANCE (automatic)                           │
│    ├─ Archive stale memories (>180 days) (Phase 11)         │
│    ├─ Detect conflicts (contradictions, redundancies)       │
│    ├─ Promote cross-project patterns                        │
│    └─ Cleanup expired sessions (>7 days) (Phase 8)          │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚠️ CRITICAL: Phased Rollout Strategy

**DO NOT implement all phases at once. Build and validate in 3 stages:**

| Phase | Scope | Storage | Duration | Gate |
|-------|-------|---------|----------|------|
| **Alpha** | Phases 1-7 | JSON | Weeks 1-2 | 70%+ approval, 90%+ accuracy |
| **Beta** | Phases 12-13 | SQLite FTS5 | Weeks 3-4 | 80%+ token savings, 2+ weeks stable |
| **Gamma** | Phases 8, 10, 11 | Enhancements | Weeks 5-6 | Session continuity works |
| **Delta** | Phases 14-15 | Post-Gamma | Weeks 7-8 | 90%+ example following, mode detection 85%+ |
| **Epsilon** | Phases 16-20 | Critical fixes | Weeks 9-10 | Integration works, 80%+ silent detection, approval time < 20s |

**Why phased:**
1. **Validate learning pipeline** (detection → clustering → proposals) **independently** before adding database complexity
2. **Measure actual token savings** empirically before full SQLite commitment
3. **Iterate fast on MVP** (JSON is simple, easy to inspect/debug)
4. **Risk mitigation** (rollback to JSON if SQLite issues)
5. **Clear validation gates** (each phase must pass metrics)

**If in doubt:** Build Phase Alpha first, validate with real usage, then proceed.

---

## Phase Breakdown (0-13)

### Phase 0: Overview
**File:** `phases/PHASE-0-OVERVIEW.md` (this file)

**Objective:** System architecture, integration, MVP definition

---

### Phase 1: Session Correction Detection
**File:** `src/cerberus/memory/session_analyzer.py`

**Objective:** Detect when user corrects AI behavior without manual storage.

**Key Features:**
- 4 detection patterns: direct negation, repetition, post-action, multi-turn
- Confidence scoring (0.7-1.0)
- Buffer to `.cerberus/session_corrections.json`
- Zero token cost (regex + keywords)

**Output:** List of `CorrectionCandidate` objects

---

### Phase 2: Semantic Deduplication
**File:** `src/cerberus/memory/semantic_analyzer.py`

**Objective:** Cluster similar corrections to prevent duplicates.

**Key Features:**
- TF-IDF similarity (scikit-learn, no model download)
- Threshold clustering (65% similarity)
- Canonical form extraction (rule-based + optional LLM)
- 60% compression ratio (10 corrections → 4 clusters)

**Output:** List of `CorrectionCluster` objects

---

### Phase 3: Session Proposal
**File:** `src/cerberus/memory/proposal_engine.py`

**Objective:** Generate proposals from corrections using template-based rules.

**Key Features:**
- Template-based proposal generation (PRIMARY, no dependencies)
- Optional LLM refinement (if Ollama available AND enabled)
- Scope inference (universal, language, project)
- Category inference (preference, rule, correction)
- Content transformation to imperative form
- Priority ranking

**Token Cost:** 0-500 tokens per session (LLM optional)

**Output:** List of `MemoryProposal` and `AgentProposal` objects

---

### Phase 4: Approval Interface
**File:** `src/cerberus/memory/approval_cli.py`

**Objective:** Simple CLI interface for proposal approval. No special dependencies.

**Key Features:**
- Uses standard `input()` only (no keyboard library)
- Works in any terminal (including Claude Code)
- Bulk operations (all, none, 1,2,3)
- Batch mode for automation (auto-approve high confidence)
- No special dependencies

**Token Cost:** 0 tokens (pure UI)

**Output:** List of approved proposal IDs

---

### Phase 5: Storage Operations
**File:** `src/cerberus/memory/storage.py`

**Objective:** Write approved proposals to hierarchical storage.

**Implementation:**
- **Phase Alpha (MVP):** JSON storage ONLY
- **Phase Beta (Migration):** Updated to write to SQLite FTS5

**Key Features:**
- Hierarchical routing (universal → language → project → task)
- Batch optimization (group by file, write once)
- Metadata tracking
- Directory auto-creation

**Directory Structure (Phase Alpha - JSON):**
```
~/.cerberus/memory/
├── profile.json              # Universal preferences
├── corrections.json          # Universal corrections
├── languages/
│   ├── go.json
│   ├── python.json
│   └── typescript.json
├── projects/
│   ├── {project}/
│   │   ├── decisions.json
│   │   └── tasks/
│   │       └── {task}.json
└── sessions/
    └── active-{session_id}.json
```

**Storage Evolution:**
- Phase Alpha: JSON files (simple, proven)
- Phase Beta: SQLite FTS5 (scales to 10,000+ memories)
- Backward compat: Keep JSON for gradual migration

**Token Cost:** 0 tokens (pure storage)

---

### Phase 6: Retrieval Operations
**File:** `src/cerberus/memory/retrieval.py`

**Objective:** Query and filter memories for context-aware injection.

**Implementation:**
- **Phase Alpha (MVP):** JSON file loading
- **Phase Beta (Migration):** Updated to query SQLite FTS5 (80% token savings)

**Key Features:**
- Scope-based loading (universal, language, project, task)
- Relevance scoring (scope + recency + confidence + task)
- Budget-aware retrieval (stop when budget exhausted)
- Integration with Phase 7 injection

**Retrieval Evolution:**
- Phase Alpha: Load all JSON, filter in Python (simple, works)
- Phase Beta: FTS5 search (returns only matches, 80% token savings)
- Backward compat: JSON fallback if SQLite unavailable

**Token Cost:** 0 tokens (pure retrieval, tokens counted in Phase 7)

**Output:** List of `RetrievedMemory` objects

---

### Phase 7: Context-Aware Retrieval
**File:** `src/cerberus/memory/context_injector.py`

**Objective:** Provide MCP tool for on-demand memory retrieval. Zero startup cost.

**Key Features:**
- MCP tool: memory_context() (like cerberus search)
- On-demand retrieval (Claude calls when needed)
- Token budget enforcement (per-query limit)
- Context detection (project, language, task auto-detected)
- Zero startup cost (no auto-injection)

**Token Cost:** 0 tokens at startup, ~1500 tokens per query (only when Claude calls it)

**Output:** Markdown string for Claude's use

---

### Phase 8: Session Continuity
**File:** `src/cerberus/memory/session_continuity.py`

**Phase:** Gamma (Enhancement layer)

**Objective:** Capture session context during work, inject at next session start. Zero re-explanation. NO LLM.

**Prerequisites:**
- ✅ Phase Beta complete (SQLite stable, 2+ weeks production)
- ✅ Core memory system proven (Phases 1-7, 12-13)

**Key Features:**
- Context Capture: AI-native codes (impl:, dec:, block:, next:)
- Auto-capture from tool usage (Edit, Write, Bash)
- Context Injection: Pure data, no LLM, no prose
- Comprehensive capture (ALL files, decisions, blockers)
- 7-day expiration with archival
- Session cleanup manager

**Token Cost:** 1000-1500 tokens per session (injection only, no LLM)

**Output:** Raw codes, newline-separated (impl:, dec:, block:, next:)

**Why Phase Gamma (not Alpha/Beta):**
- Core memory system must be stable first
- Session continuity is enhancement, not blocker
- Can be added incrementally without risk
- Depends on stable Phase 7 injection

---

### Phase 9: (Merged into Phase 8)
*Session Context Injection merged into Phase 8: Session Continuity*

---

### Phase 10: Agent Self-Learning
**File:** `src/cerberus/memory/agent_learning.py`

**Phase:** Gamma (Enhancement layer)

**Objective:** Agent detects success/failure patterns and proposes memories proactively.

**Prerequisites:**
- ✅ Phase Beta complete (SQLite stable)
- ✅ User learning validated (Phases 1-7 proven)

**Key Features:**
- Success reinforcement (repeated approved actions)
- Failure avoidance (repeated corrections)
- Project pattern inference (codebase consistency)
- Approach reinforcement (explicit praise detection)
- 4 detection patterns with confidence scoring

**Token Cost:** 2000 tokens per session (10 agent proposals)

**Output:** List of `AgentProposal` objects (fed into Phase 3)

**Why Phase Gamma:**
- User learning must work first (agent builds on top)
- Can be added incrementally
- Feeds into proven Phase 3 proposal engine
- 50%+ approval target (validation gate)

---

### Phase 11: Maintenance & Health
**File:** `src/cerberus/memory/maintenance.py`

**Phase:** Gamma (Enhancement layer)

**Objective:** Auto-maintain memory health.

**Prerequisites:**
- ✅ Phase Beta complete (SQLite with access tracking)
- ✅ Phase 8 complete (session cleanup needed)

**Key Features:**
- Stale detection (>60 days unused, using access_count)
- Auto-archival (>180 days)
- Conflict detection (contradictions, redundancies, obsolete)
- Cross-project promotion (pattern in 3+ projects → universal)
- Session cleanup (>7 days expired, Phase 8 integration)
- Weekly health checks (automated cron job)

**Token Cost:** 0 tokens (offline analysis)

**Why Phase Gamma:**
- Operates on stable SQLite (Phase Beta)
- Requires access tracking (Phase 13)
- Session cleanup depends on Phase 8
- Manual maintenance sufficient for MVP

---

### Phase 12: Memory Indexing
**File:** `src/cerberus/memory/indexing.py`

**Phase:** Beta (Migration layer)

**Objective:** Migrate memories from JSON → SQLite FTS5. Foundation for scalable search.

**Prerequisites:**
- ✅ Phase Alpha complete (Phases 1-7 validated with JSON)
- ✅ Validation gates passed (70%+ approval, 90%+ accuracy)
- ✅ Real-world testing complete (5+ sessions)

**Key Features:**
- SQLite schema with FTS5 (full-text search)
- Auto-migration from JSON (one-time, transparent)
- Backward compatibility (keep JSON as fallback)
- WAL mode for concurrency (same as Cerberus code index)
- Integrity verification
- CLI tools (migrate, verify)

**Token Cost:** 0 tokens (one-time migration, no LLM)

**Storage:** `~/.cerberus/memory.db`

**Why Phase Beta (not Alpha):**
- Database complexity isolated from learning logic
- Can measure actual token savings empirically
- MVP proves value before optimization investment
- Rollback to JSON if issues

---

### Phase 13: Indexed Search & Integration
**File:** `src/cerberus/memory/search.py`

**Phase:** Beta (Migration layer)

**Objective:** FTS5 search queries, update Phase 5-6 to use SQLite.

**Prerequisites:**
- ✅ Phase 12 complete (SQLite schema + migration)
- ✅ Migration validated (100% data integrity)

**Key Features:**
- FTS5-powered search (text, scope, category filters)
- Relevance scoring from FTS5 rank (BM25 algorithm)
- Snippet extraction (match context)
- Phase 5 updates (write to SQLite instead of JSON)
- Phase 6 updates (query SQLite instead of loading JSON)
- New MCP tool: `memory_search(query, scope, category, limit)`
- Access tracking (last_accessed, count)

**Token Cost:** 0 tokens (pure search, no LLM)

**Token Savings:** 80% reduction target (load 10 matches vs 50 all memories)

**Validation:**
- Measure actual token savings (must achieve 80%+)
- Performance: Search < 50ms for 100 memories
- Backward compat: JSON fallback works
- Production testing: 2+ weeks stable

---

### Phase 14: Dynamic Anchoring
**File:** `src/cerberus/memory/anchoring.py`

**Phase:** Delta (Post-Gamma enhancements)

**Objective:** Link abstract rules to concrete code examples. Inject example files alongside text rules.

**Prerequisites:**
- ✅ Phase Beta complete (SQLite stable)
- ✅ Phase 7 complete (context injection working)
- ✅ Phase 13 complete (memory search operational)

**Key Features:**
- Anchor discovery: Scan codebase for best example file matching rule
- TF-IDF relevance scoring between rule text and file content
- Size penalty (prefer concise examples < 500 lines)
- Recency scoring (prefer recently modified files)
- SQLite extension (anchor_file, anchor_symbol, anchor_score columns)
- Phase 7 extension (inject code examples alongside text rules)
- Token reallocation (40% text rules, 60% code examples = 1500 tokens)

**Token Cost:** 1500 tokens (same as Phase 7, reallocated for code examples)

**Impact:** LLM follows examples 90%+ of time vs 70% for text-only rules

**Why Phase Delta:**
- Requires stable code indexing (Cerberus)
- Enhancement layer on proven injection
- Addresses "text vs code disconnect" (Gemini critique)

---

### Phase 15: Mode-Aware Context
**File:** `src/cerberus/memory/mode_detection.py`

**Phase:** Delta (Post-Gamma enhancements)

**Objective:** Detect user intent mode and filter memory injection based on mode appropriateness.

**Prerequisites:**
- ✅ Phase Beta complete (SQLite stable)
- ✅ Phase 7 complete (context injection working)
- ✅ Phase 13 complete (memory search with filtering)

**Key Features:**
- Mode detection (prototype/production/hotfix/refactor/audit/exploration)
- Keyword-based scoring (urgency, scope, time indicators)
- Context signal analysis (tool usage, file count, session history)
- Memory tagging (valid_modes, mode_priority per mode)
- Auto-tagging algorithm (quality rules → production, speed rules → prototype)
- Phase 7 extension (filter memories by detected mode before injection)
- SQLite extension (valid_modes, mode_priority columns)

**Token Cost:** 0 tokens (filtering is free, happens before injection)

**Impact:** Prevents inappropriate rule injection (e.g., "Always write tests" blocked in prototype mode)

**Why Phase Delta:**
- Core memory system must work first
- Mode detection is enhancement layer
- Addresses "mode blindness" (Gemini critique)

---

### Phase 16: Integration Specification
**File:** `src/cerberus/memory/hooks.py`, `src/cerberus/memory/ipc.py`

**Phase:** Epsilon (Critical infrastructure)

**Objective:** Define concrete integration between memory system and Claude Code/Codex/Gemini CLIs.

**Prerequisites:**
- ✅ Phase Alpha complete (Phases 1-7 working)
- ✅ Phase 7 complete (injection logic proven)

**Key Features:**
- Hook implementation (session end ONLY - no session start)
- MCP tool for memory retrieval (memory_context, on-demand)
- Python subprocess for proposal hook
- Session state tracking (.cerberus/session_active.json)
- CLI commands (cerberus memory propose, install-hooks)
- Multi-CLI support (claude-code, codex-cli, gemini-cli)
- Zero startup cost (no auto-injection)

**Token Cost:** 0 tokens at startup, 0-500 tokens at session end (proposal pipeline)

**Why Phase Epsilon:**
- Integration can use Phase Alpha's JSON first
- Proves integration works before SQLite complexity
- Critical for system to function

---

### Phase 17: Session Lifecycle & Recovery
**File:** `src/cerberus/memory/session_lifecycle.py`

**Phase:** Epsilon (Critical infrastructure)

**Objective:** Define session boundaries, detect crashes, implement recovery.

**Prerequisites:**
- ✅ Phase 16 complete (integration hooks)
- ✅ Phase 1 complete (correction tracking)

**Key Features:**
- Session start/end detection (CLI process, explicit commands, idle timeout)
- Crash detection (stale session_active.json > 5 minutes)
- Auto-recovery (high-confidence proposals auto-approved)
- Manual recovery CLI (cerberus memory recover)
- Idle timeout (30 minutes default)
- File locking (prevent race conditions)
- Session history/analytics

**Token Cost:** 0-500 tokens (if running proposal pipeline during recovery)

**Why Phase Epsilon:**
- Session management needed for reliable correction detection
- Crash recovery prevents data loss
- Critical for production reliability

---

### Phase 18: Approval Optimization
**File:** `src/cerberus/memory/approval_optimizer.py`

**Phase:** Epsilon (User experience enhancement)

**Objective:** Reduce approval fatigue through auto-approval, batching, smart grouping.

**Prerequisites:**
- ✅ Phase 4 complete (CLI approval working)
- ✅ Phase 3 complete (proposals with confidence scores)

**Key Features:**
- Auto-approval (0.9+ confidence, safety checks)
- Smart batching (group similar proposals by theme)
- Skip low-confidence (< 0.5)
- Batch mode (non-interactive, CI/CD friendly)
- Approval history learning (adjust thresholds based on user behavior)
- Reduces approval time from 60s → 15s

**Token Cost:** 0 tokens (optimization is free)

**Impact:** 30-40% auto-approval rate, user satisfaction increase

**Why Phase Epsilon:**
- Addresses approval fatigue (10+ proposals per session)
- Enhancement layer on Phase 4
- Critical for user retention

---

### Phase 19: Conflict Resolution
**File:** `src/cerberus/memory/conflict_resolver.py`

**Phase:** Epsilon (Data quality enhancement)

**Objective:** Resolve memory conflicts (contradictions, redundancies, obsolescence).

**Prerequisites:**
- ✅ Phase 11 complete (conflict detection)
- ✅ Phase 5 complete (storage)
- ✅ Phase 13 complete (memory search)

**Key Features:**
- Auto-resolution (redundancy → keep newer, obsolescence → keep newer)
- Contradiction resolution (recency/confidence-based)
- User-mediated resolution (interactive prompts for ambiguous conflicts)
- Merge resolution (user provides merged content)
- Execution (delete/merge memories in storage)
- 60-70% auto-resolution rate

**Token Cost:** 0 tokens (resolution is free)

**Why Phase Epsilon:**
- Phase 11 detects, Phase 19 resolves
- Prevents memory database rot
- Critical for long-term quality

---

### Phase 20: Silent Divergence Detection
**File:** `src/cerberus/memory/silent_divergence.py`

**Phase:** Epsilon (Critical detection enhancement)

**Objective:** Detect when user silently fixes AI code without verbal correction.

**Prerequisites:**
- ✅ Phase 1 complete (verbal correction detection)
- ✅ Phase 17 complete (session activity tracking)
- ✅ Phase 16 complete (tool usage tracking)

**Key Features:**
- Tool usage tracking (Edit/Write after AI response)
- Diff analysis (difflib + AST structural changes)
- Pattern extraction (variable_rename, bug_fix, style_change, error_handling)
- Correction candidate generation (feeds into Phase 2)
- Integration with Phase 1 (verbal + silent combined)
- 80%+ silent correction detection

**Token Cost:** 0 tokens (detection is free)

**Impact:** Catches 80% of corrections Phase 1 misses

**Why Phase Epsilon:**
- Addresses Gemini's #1 critique (80% of corrections are silent)
- Critical enhancement to Phase 1
- Requires tool tracking infrastructure

---

## Implementation Strategy: Phased Rollout

**CRITICAL: Build and validate in 3 distinct phases, NOT all at once.**

### **PHASE ALPHA: MVP with JSON Storage (Weeks 1-2)**
**Goal:** Validate learning pipeline works before adding database complexity.

```
Phase 1 (Detection) → Phase 2 (Deduplication) → Phase 3 (Proposals)
         ↓                    ↓                         ↓
    Corrections          Clusters              User Proposals
         └────────────────┴─────────────────────┘
                           ↓
                    Phase 4 (CLI Approval)
                           ↓
         Phase 5 (JSON Storage) ←─── START WITH JSON
                           ↓
         Phase 6 (JSON Retrieval)
                           ↓
         Phase 7 (Context Injection)
```

**Implementation order:** 1 → 2 → 3 → 4 → 5 (JSON) → 6 (JSON) → 7

**Validation gates (MUST PASS before Phase Beta):**
- ✓ Detection: 90%+ accuracy on 10 test scenarios
- ✓ Clustering: 60%+ compression ratio (TF-IDF threshold tuned)
- ✓ Proposal: User approves 70%+ of proposals
- ✓ Injection: Always under 1500 tokens
- ✓ Zero false positives (bad memories stored)
- ✓ Real-world testing: 5+ sessions with actual corrections

**Why JSON first:**
- Simple, proven, no migration complexity
- Validates learning pipeline independently
- Fast iteration during development
- Easy to inspect/debug

---

### **PHASE BETA: SQLite Migration (Weeks 3-4)**
**Goal:** Scale to thousands of memories, 80% token savings.

```
Phase 12 (Indexing) → SQLite FTS5 schema + auto-migration
         ↓
Phase 5 (UPDATED: write to SQLite)
         ↓
Phase 6 (UPDATED: query SQLite FTS5)
         ↓
Phase 13 (Search) → New MCP tool: memory_search()
```

**Implementation order:** 12 → Update 5 → Update 6 → 13

**Validation gates (MUST PASS before Phase Gamma):**
- ✓ Migration: 100% data integrity (JSON → SQLite)
- ✓ Token savings: Measure actual 80% reduction
- ✓ Performance: Search < 50ms for 100 memories
- ✓ Backward compat: JSON fallback works
- ✓ Real-world testing: 2+ weeks stable, no data loss

**Why after MVP:**
- Database complexity isolated from learning logic
- Can measure actual token savings empirically
- MVP proves value before optimization investment
- Rollback to JSON if issues

---

### **PHASE GAMMA: Enhancements (Weeks 5-6)**
**Goal:** Session continuity, agent learning, maintenance.

```
Phase 8 (Session Continuity) → AI-native codes, NO LLM
         ↓
    Enhanced injection (1500 memory + 1000 session = 2500 tokens)

Phase 10 (Agent Learning) → Success/failure pattern detection
         ↓
    Agent proposals feed into Phase 3

Phase 11 (Maintenance) → Auto-cleanup, conflict detection
```

**Implementation order:** 8 → 10 → 11

**Validation gates:**
- ✓ Session continuity: Zero re-explanation needed
- ✓ Agent learning: 50%+ agent proposals approved
- ✓ Maintenance: Stale detection works, no data loss

**Why deferred:**
- Core memory system must be stable first
- Session continuity is enhancement, not blocker
- Agent learning can be added incrementally
- Maintenance operates on proven system

---

**PHASE DELTA: Post-Gamma Enhancements (Weeks 7-8)**
**Goal:** Dynamic anchoring and mode-aware context.

```
Phase 14 (Dynamic Anchoring) → Link rules to code examples
         ↓
    Find best example file in codebase
         ↓
    Inject code alongside text rules

Phase 15 (Mode-Aware Context) → Detect intent mode
         ↓
    Filter memories by mode appropriateness
         ↓
    Prototype mode: Skip quality rules
    Production mode: Include all quality rules
```

**Implementation order:** 14 → 15

**Validation gates:**
- ✓ Anchor discovery: 80%+ success rate
- ✓ Mode detection: 85%+ accuracy
- ✓ LLM example following: 90%+
- ✓ User approval increase: 70% → 85%

**Why Phase Delta (not Gamma):**
- Addresses Gemini's critiques (anchoring, mode blindness)
- Requires stable Gamma foundation
- Enhancement layer on proven system
- Can be added incrementally

---

## Dependency Graph

```
PHASE ALPHA (MVP - JSON):
Phase 1 (Detection) ──────────┐
                               ├─→ Phase 2 (Deduplication)
                               │         ↓
                               │    Phase 3 (Proposals)
                               │         ↓
                               │    Phase 4 (CLI Approval)
                               │         ↓
                               └─→ Phase 5 (JSON Storage)
                                        ↓
                                  Phase 6 (JSON Retrieval)
                                        ↓
                                  Phase 7 (Injection)

        ───────── VALIDATION GATE ─────────

PHASE BETA (SQLite Migration):
Phase 12 (Indexing) ──→ Phase 5 (UPDATED: SQLite writes)
                            ↓
                       Phase 6 (UPDATED: SQLite queries)
                            ↓
                       Phase 13 (FTS5 Search + MCP tool)

        ───────── VALIDATION GATE ─────────

PHASE GAMMA (Enhancements):
Phase 8 (Session Continuity) ──→ Integrated with Phase 7
Phase 10 (Agent Learning) ──────→ Feeds into Phase 3
Phase 11 (Maintenance) ──────────→ Operates on Phases 5-6

        ───────── VALIDATION GATE ─────────

PHASE DELTA (Post-Gamma Enhancements):
Phase 14 (Dynamic Anchoring) ──→ Extends Phase 7 (injection)
                                 └─→ Extends Phase 5 (storage)
Phase 15 (Mode-Aware Context) ──→ Extends Phase 7 (filtering)
                                 └─→ Extends Phase 5 (storage)

        ───────── VALIDATION GATE ─────────

PHASE EPSILON (Critical Fixes):
Phase 16 (Integration) ──────────→ Enables entire system
Phase 17 (Session Lifecycle) ────→ Supports Phase 1 + 16
Phase 18 (Approval Optimization) ─→ Extends Phase 4
Phase 19 (Conflict Resolution) ───→ Extends Phase 11
Phase 20 (Silent Divergence) ────→ Extends Phase 1
```

**Critical principle:** Each phase is independently shippable and validated before moving to next.

---

## MVP Definition: Phase Alpha (Weeks 1-2)

**Scope:** Validate learning pipeline with JSON storage ONLY.

**Must Have (Phases 1-7 with JSON):**
- Phase 1: User correction detection (4 patterns, 90%+ accuracy)
- Phase 2: Clustering (TF-IDF based, 60%+ compression ratio)
- Phase 3: Proposal (template-based PRIMARY, LLM optional)
- Phase 4: CLI approval (standard input(), batch mode)
- Phase 5: Storage (JSON ONLY - universal + language + project layers)
- Phase 6: Retrieval (JSON ONLY - scope-based, relevance scoring)
- Phase 7: Injection (1500 token budget, memory only)

**Storage format for MVP:**
```
~/.cerberus/memory/
├── profile.json              # Universal preferences
├── corrections.json          # Universal corrections
├── languages/
│   ├── go.json
│   ├── python.json
│   └── typescript.json
└── projects/
    └── {project}/
        └── decisions.json
```

**Explicitly OUT OF SCOPE for MVP:**
- SQLite migration (Phase 12-13) - defer until MVP validated
- Session continuity (Phase 8) - enhancement layer
- Agent learning (Phase 10) - enhancement layer
- Maintenance (Phase 11) - manual cleanup for MVP
- Task-specific storage - defer
- Advanced conflict detection - defer

**Success criteria (gate to Phase Beta):**
- User approves 70%+ of proposals (real sessions)
- Detection accuracy 90%+ on test scenarios
- TF-IDF clustering compression 60%+
- Injection always under 1500 tokens
- Zero false positives (no bad memories stored)
- 5+ real sessions tested successfully

---

## Success Metrics & Validation Gates

### **Phase Alpha: MVP with JSON (Weeks 1-2)**
**Validation gates (MUST PASS to proceed to Phase Beta):**

| Metric | Target | Test Method |
|--------|--------|-------------|
| Detection accuracy | 90%+ | 10 test scenarios with known corrections |
| Clustering compression | 60%+ | 50+ real corrections, measure deduplication |
| Proposal approval rate | 70%+ | 5+ real sessions, user approves proposals |
| Injection token budget | < 1500 tokens | Measure actual injection across contexts |
| False positive rate | 0% | No bad memories stored after review |
| TF-IDF threshold | Tuned | Empirical testing for 65% similarity |

**Exit criteria:**
- All metrics pass
- Real-world testing complete (5+ sessions)
- User feedback: "This learns from me"
- No regressions in existing Cerberus functionality

**If gates fail:** Iterate on MVP, do NOT proceed to SQLite.

---

### **Phase Beta: SQLite Migration (Weeks 3-4)**
**Validation gates (MUST PASS to proceed to Phase Gamma):**

| Metric | Target | Test Method |
|--------|--------|-------------|
| Migration integrity | 100% | All JSON data migrated, checksums match |
| Token savings | 80%+ | Measure FTS5 vs JSON retrieval |
| Search performance | < 50ms | 100 memories, FTS5 query time |
| Database size | ~1MB per 1000 memories | Verify SQLite efficiency |
| Backward compatibility | 100% | JSON fallback works if SQLite fails |
| Stability | 2+ weeks | No crashes, no data loss |

**Exit criteria:**
- All metrics pass
- Production testing (2+ weeks stable)
- Rollback plan tested and works
- Documentation updated

**If gates fail:** Rollback to JSON, debug SQLite issues.

---

### **Phase Gamma: Enhancements (Weeks 5-6)**
**Validation gates (OPTIONAL - enhancement layer):**

| Metric | Target | Test Method |
|--------|--------|-------------|
| Session continuity | Zero re-explanation | Resume work from last session seamlessly |
| Agent proposal approval | 50%+ | Agent-detected patterns user approves |
| Maintenance effectiveness | Stale detection works | 180+ day memories archived correctly |
| Total system health | No conflicts | 4+ weeks production, no issues |

**Exit criteria:**
- Session continuity works (Phase 8)
- Agent learning adds value (Phase 10)
- Maintenance runs automatically (Phase 11)
- User satisfaction: "This is revolutionary"

---

### **Overall System Success (Month 2+)**
**Long-term metrics:**
- Zero repeated corrections across sessions
- Memory growth: < 10 entries per week (deduplication working)
- Token efficiency: 80%+ savings maintained
- User retention: Daily active usage
- System reliability: 99%+ uptime, no data loss

---

## Technical Constraints

**Token Budget ($0.10 session cap = ~6666 tokens @ Sonnet rates):**

*Session Start:*
- Memory injection: 1500 tokens max (Phase 7)
  - Universal: 700 tokens
  - Language: 500 tokens
  - Project: 300 tokens
- Session code injection: 1000-1500 tokens (Phase 9)
  - Files: 300-500 tokens (ALL files)
  - Functions: 200-400 tokens (ALL functions)
  - Decisions: 200-300 tokens (ALL decisions)
  - Blockers: 100-200 tokens (ALL blockers)
  - Next actions: 100-200 tokens (ALL actions)
- Total start: 2500-3000 tokens

*Session End:*
- User correction proposals: 2000 tokens (10 proposals, Phase 3)
- Agent learning proposals: 2000 tokens (10 proposals, Phase 10)
- Session code save: 0 tokens (no LLM, direct save)
- Total end: 4000 tokens

*Total per session: ~6500-7000 tokens (~$0.098-$0.105)*
*Slightly over $0.10 cap but comprehensive session continuity*

**Performance:**
- Detection: Real-time (< 50ms per turn)
- Clustering: < 2 seconds for typical session
- Injection: < 100ms
- Health check: < 5 seconds (run weekly)
- Agent pattern detection: < 1 second
- Session summary: < 2 seconds

**Dependencies:**
```bash
# Required
pip install scikit-learn numpy tiktoken

# Optional (only if using LLM refinement)
pip install requests  # For Ollama API calls
```

**Model Requirements:**
- TF-IDF: scikit-learn (no model download, required)
- LLM: OPTIONAL - Ollama (llama3.2:3b) for refinement only
  - System works 100% without Ollama
  - LLM is enhancement, not requirement

---

## Integration Points

**1. Claude Code Session Hook (auto-inject):**
```python
def on_session_start():
    # Memory injection (Phase 7, uses Phase 6 retrieval)
    context = ContextDetector().detect()
    memory_context = ContextInjector().inject(context)

    # Session context injection (Phase 9)
    session_context = SessionContextInjector().inject(context.project)

    # Combine and inject into system prompt
    return memory_context + "\n\n" + session_context
```

**2. Session End Hook (propose):**
```python
def on_session_end():
    # User corrections (Phases 1-3)
    user_candidates = SessionAnalyzer().candidates
    user_clusters = SemanticAnalyzer().cluster_corrections(user_candidates)
    user_proposals = ProposalEngine().generate_user_proposals(user_clusters)

    # Agent learning (Phase 10)
    agent_proposals = AgentLearningEngine().generate_agent_proposals()

    # Session context (Phase 8 → Phase 9)
    context = SessionContextCapture().get_context()
    session_summary = SessionSummarizer().generate_summary(context)

    # TUI approval (Phase 4)
    try:
        tui = ApprovalTUI()
        approved_ids = tui.run(user_proposals, agent_proposals)
    except Exception:
        # Fallback to CLI
        cli = CLIApprovalFallback()
        approved_ids = cli.run(user_proposals, agent_proposals)

    # Storage (Phase 5)
    all_proposals = user_proposals + agent_proposals
    approved = [p for p in all_proposals if p.id in approved_ids]
    MemoryStorage().store_batch(approved)

    # Save session context (Phase 9)
    SessionContextInjector().save_context(session_summary)
```

**3. MCP Tool Removal:**
- Remove `memory_context()` from tools (auto-injected)
- Keep `memory_show()`, `memory_learn()` (manual override)
- Keep `memory_forget()`, `memory_stats()` (utilities)

**4. Skill Update:**
```markdown
Memory is auto-loaded at session start (hook-based).
No need to call memory_context().
Use memory_learn() only for explicit storage.
```

---

## Testing Strategy

**Unit Tests:**
- Each phase: 10-20 test scenarios
- Edge cases: empty input, malformed data, conflicts

**Integration Tests:**
- Full pipeline: Detection → Clustering → Proposal → Storage → Injection
- Cross-phase: Stored memories injected correctly

**User Acceptance Tests:**
- 5 real sessions with correction scenarios
- User approves 70%+ of proposals
- Zero false positives (bad memories stored)

---

## Migration Plan

**Existing Memory → New Hierarchy:**
1. Run `MemoryMigration().migrate(old_store, new_hierarchy)`
2. Validate migrated data
3. Keep old structure as backup (don't delete)
4. Gradual rollout (opt-in flag)

**Rollback Plan:**
- Keep old memory system intact
- Feature flag: `ENABLE_ADAPTIVE_MEMORY=true`
- Can disable and revert to old system

---

## File Manifest

```
phases/
├── PHASE-0-OVERVIEW.md (this file)
├── PHASE-1-SESSION-CORRECTION-DETECTION.md
├── PHASE-2-SEMANTIC-DEDUPLICATION.md
├── PHASE-3-SESSION-PROPOSAL.md
├── PHASE-4-TUI-APPROVAL-INTERFACE.md (CLI approval, no TUI)
├── PHASE-5-STORAGE-OPERATIONS.md
├── PHASE-6-RETRIEVAL-OPERATIONS.md
├── PHASE-7-CONTEXT-AWARE-INJECTION.md
├── PHASE-8-SESSION-CONTINUITY.md (merged: capture + injection)
├── PHASE-10-AGENT-SELF-LEARNING.md
├── PHASE-11-MAINTENANCE-HEALTH.md
├── PHASE-12-MEMORY-INDEXING.md
├── PHASE-13-INDEXED-SEARCH.md
├── PHASE-14-DYNAMIC-ANCHORING.md
├── PHASE-15-MODE-AWARE-CONTEXT.md
├── PHASE-16-INTEGRATION-SPECIFICATION.md
├── PHASE-17-SESSION-LIFECYCLE.md
├── PHASE-18-APPROVAL-OPTIMIZATION.md
├── PHASE-19-CONFLICT-RESOLUTION.md
└── PHASE-20-SILENT-DIVERGENCE.md

src/cerberus/memory/
├── session_analyzer.py      (Phase 1: User correction detection)
├── semantic_analyzer.py     (Phase 2: TF-IDF clustering/deduplication)
├── proposal_engine.py       (Phase 3: LLM proposal generation)
├── approval_cli.py          (Phase 4: CLI approval interface)
├── storage.py               (Phase 5: Storage operations, Phase 13: SQLite writes)
├── retrieval.py             (Phase 6: Retrieval operations, Phase 13: SQLite queries)
├── context_injector.py      (Phase 7: Memory injection)
├── session_continuity.py    (Phase 8: Session capture + injection)
├── agent_learning.py        (Phase 10: Agent self-learning)
├── maintenance.py           (Phase 11: Maintenance & health)
├── indexing.py              (Phase 12: SQLite FTS5 indexing)
├── search.py                (Phase 13: FTS5 search engine)
├── anchoring.py             (Phase 14: Dynamic anchoring)
├── mode_detection.py        (Phase 15: Mode-aware context)
├── hooks.py                 (Phase 16: Integration hooks)
├── ipc.py                   (Phase 16: Inter-process communication)
├── session_lifecycle.py     (Phase 17: Session boundaries & recovery)
├── approval_optimizer.py    (Phase 18: Smart approval)
├── conflict_resolver.py     (Phase 19: Conflict resolution)
└── silent_divergence.py     (Phase 20: Silent correction detection)

~/.cerberus/
├── memory.db                (SQLite FTS5 index, Phase 12-13)
├── memory.db-wal            (Write-ahead log)
├── memory.db-shm            (Shared memory)
└── memory/                  (Legacy JSON, backward compat)
    ├── profile.json
    ├── corrections.json
    ├── languages/
    ├── projects/
    └── sessions/
```

---

## Implementation Roadmap: Timeline & Deliverables

### **Week 1-2: Phase Alpha (MVP with JSON)**
**Deliverables:**
- ✅ Phase 1: Detection (session_analyzer.py)
- ✅ Phase 2: Deduplication (semantic_analyzer.py)
- ✅ Phase 3: Proposals (proposal_engine.py)
- ✅ Phase 4: CLI Approval (approval_cli.py)
- ✅ Phase 5: JSON Storage (storage.py - JSON version)
- ✅ Phase 6: JSON Retrieval (retrieval.py - JSON version)
- ✅ Phase 7: Injection (context_injector.py)

**Testing:**
- 10 test scenarios (90%+ detection accuracy)
- 50+ corrections (60%+ clustering compression)
- 5+ real sessions (70%+ approval rate)
- Token budget validation (<1500 tokens)

**Gate:** All metrics pass → Proceed to Phase Beta

---

### **Week 3-4: Phase Beta (SQLite Migration)**
**Deliverables:**
- ✅ Phase 12: Indexing (indexing.py + migration tool)
- ✅ Phase 5 UPDATE: SQLite writes (storage.py updated)
- ✅ Phase 6 UPDATE: FTS5 queries (retrieval.py updated)
- ✅ Phase 13: Search engine (search.py + memory_search MCP tool)

**Testing:**
- Migration integrity (100% data preserved)
- Token savings measurement (80%+ target)
- Performance benchmarks (<50ms search)
- Production stability (2+ weeks)

**Gate:** Metrics pass + 2 weeks stable → Proceed to Phase Gamma

---

### **Week 5-6: Phase Gamma (Enhancements)**
**Deliverables:**
- ✅ Phase 8: Session Continuity (session_continuity.py)
- ✅ Phase 10: Agent Learning (agent_learning.py)
- ✅ Phase 11: Maintenance (maintenance.py)

**Testing:**
- Session continuity validation (zero re-explanation)
- Agent proposal approval (50%+ target)
- Maintenance automation (stale detection works)

**Gate:** Enhancement layer works → Proceed to Phase Delta

---

### **Week 7-8: Phase Delta (Post-Gamma Enhancements)**
**Deliverables:**
- ✅ Phase 14: Dynamic Anchoring (anchoring.py)
- ✅ Phase 15: Mode-Aware Context (mode_detection.py)

**Testing:**
- Anchor discovery (80%+ success rate for project memories)
- Anchor quality (score >= 0.7)
- Mode detection accuracy (85%+ on test prompts)
- LLM example following (90%+ match anchor style)
- User approval increase (70% → 85%)

**Gate:** Anchoring + mode filtering validated → Proceed to Phase Epsilon

---

### **Week 9-10: Phase Epsilon (Critical Fixes)**
**Deliverables:**
- ✅ Phase 16: Integration Specification (hooks.py, ipc.py)
- ✅ Phase 17: Session Lifecycle & Recovery (session_lifecycle.py)
- ✅ Phase 18: Approval Optimization (approval_optimizer.py)
- ✅ Phase 19: Conflict Resolution (conflict_resolver.py)
- ✅ Phase 20: Silent Divergence Detection (silent_divergence.py)

**Testing:**
- Integration (hooks install, inject/propose work)
- Crash recovery (deliberate SIGKILL, verify recovery)
- Auto-approval (30-40% rate, approval time < 20s)
- Conflict resolution (60-70% auto-resolution)
- Silent divergence (80%+ detection rate)

**Gate:** All critical fixes validated → Production ready

---

### **Month 3+: Production & Iteration**
**Focus:**
- Monitor real-world usage
- Tune TF-IDF threshold based on data
- Optimize token budgets
- Gather user feedback
- Plan future enhancements

---

## Quick Reference: Phase Assignment

| Phase | Name | File | Rollout |
|-------|------|------|---------|
| 1 | Detection | session_analyzer.py | **Alpha** |
| 2 | Deduplication | semantic_analyzer.py | **Alpha** |
| 3 | Proposals | proposal_engine.py | **Alpha** |
| 4 | CLI Approval | approval_cli.py | **Alpha** |
| 5 | Storage | storage.py (JSON → SQLite) | **Alpha** → **Beta** |
| 6 | Retrieval | retrieval.py (JSON → SQLite) | **Alpha** → **Beta** |
| 7 | Injection | context_injector.py | **Alpha** |
| 8 | Session Continuity | session_continuity.py | **Gamma** |
| 10 | Agent Learning | agent_learning.py | **Gamma** |
| 11 | Maintenance | maintenance.py | **Gamma** |
| 12 | Indexing | indexing.py | **Beta** |
| 13 | Search | search.py | **Beta** |
| 14 | Dynamic Anchoring | anchoring.py | **Delta** |
| 15 | Mode-Aware Context | mode_detection.py | **Delta** |
| 16 | Integration | hooks.py, ipc.py | **Epsilon** |
| 17 | Session Lifecycle | session_lifecycle.py | **Epsilon** |
| 18 | Approval Optimization | approval_optimizer.py | **Epsilon** |
| 19 | Conflict Resolution | conflict_resolver.py | **Epsilon** |
| 20 | Silent Divergence | silent_divergence.py | **Epsilon** |

**Storage Evolution:**
- **Alpha:** Phases 5-6 use JSON
- **Beta:** Phases 5-6 updated for SQLite + Phase 12-13 added
- **Gamma:** Enhancements (8, 10, 11) on top of stable SQLite

---

## Quick Start for AI Agents

**IMPORTANT: Follow phased rollout. Do NOT build all phases at once.**

**Step 1:** Read this overview (PHASE-0-OVERVIEW.md)

**Step 2:** Identify current rollout phase (Alpha/Beta/Gamma)

**Step 3:** Read phase-specific documents for that rollout phase ONLY

**Step 4:** Implement phases in order within rollout phase

**Step 5:** Run tests and validate against gate criteria

**Step 6:** Only proceed to next rollout phase if gates pass

**Example for Phase Alpha:**
1. Read PHASE-0-OVERVIEW.md (this file)
2. Read PHASE-1-SESSION-CORRECTION-DETECTION.md
3. Implement Phase 1 (detection)
4. Read PHASE-2-SEMANTIC-DEDUPLICATION.md
5. Implement Phase 2 (deduplication with TF-IDF)
6. Continue through Phases 3-7 (all JSON-based)
7. Test against validation gates
8. If gates pass → proceed to Phase Beta

---

## Questions & Answers

**Q: Why not auto-store without user approval?**
A: Prevents false positives. User confirms = 100% accuracy.

**Q: Why template-based proposals instead of LLM?**
A: Works without external dependencies. LLM is optional enhancement only.

**Q: Can I use LLM for better proposals?**
A: Yes, set `use_llm=True` if Ollama is available. It refines the template output.

**Q: Why 1500 token budget for memory injection?**
A: Balance: Enough for comprehensive rules, not bloated. Tested optimal.

**Q: Why hierarchical storage?**
A: Relevance filtering. Go project doesn't need Python rules.

**Q: Why TF-IDF instead of embeddings?**
A: Lightweight (~1MB vs 80MB+400MB model), no download, works offline, sufficient for short text.

---

## Contact & Support

**Issues:** File in cerberus GitHub repo
**Discussion:** Discord #cerberus channel
**Docs:** Read phase documents in `phases/`

---

**Last Updated:** 2026-01-22
**Version:** 5.0 (Added Phase Epsilon: Critical Fixes - Integration, Lifecycle, Approval, Conflicts, Silent Divergence)
**Status:** Ready for Phase Alpha implementation

**Key Design Principles:**
- **Phased validation:** Build MVP with JSON, validate, THEN migrate to SQLite
- **LLM is OPTIONAL** throughout - system works 100% without Ollama
- **Template-based/rule-based approaches are PRIMARY** (TF-IDF, not embeddings)
- **Cerberus infrastructure reuse:** SQLite FTS5 (same as code indexing)
- **Simple CLI interface** (no TUI dependencies)
- **Validation gates:** Each phase must pass metrics before proceeding
- **Backward compatibility:** JSON fallback, gradual migration
- **Token efficiency:** 80% savings target (FTS5 vs JSON)
- **Phase Delta additions:** Dynamic anchoring (Gemini critique: text vs code disconnect), Mode detection (Gemini critique: mode blindness)
- **Phase Epsilon additions:** Integration spec (HOW system works), Session lifecycle (crash recovery), Approval optimization (reduce fatigue), Conflict resolution (beyond detection), Silent divergence (Gemini critique: 80% of corrections are silent)
