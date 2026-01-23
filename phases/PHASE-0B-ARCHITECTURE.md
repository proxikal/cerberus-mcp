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
