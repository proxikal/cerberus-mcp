# PHASE 0B: ARCHITECTURE

## MCP Tools Reference

**All MCP tools provided by Cerberus memory system:**

1. **memory_context(query=None, scope=None)** - Phase 7/8
   - Context retrieval for injection (startup + on-demand)
   - Session start: auto-called by Claude Code (2000 tokens)
   - During work: on-demand queries (500 tokens per query, max 2)
   - Combines Phase 7 memories + Phase 8 session codes

2. **memory_search(query, scope=None, category=None, limit=10)** - Phase 13
   - FTS5 full-text search across memories
   - Explicit search queries (not automatic)
   - Returns ranked results with snippets

3. **memory_learn(content, category, scope=None)** - Phase 3
   - Manual memory creation (user override)
   - Bypasses approval flow

4. **memory_show(category=None)** - Phase 6
   - View stored memories
   - Debugging and inspection

5. **memory_forget(memory_id)** - Phase 11
   - Delete specific memory
   - Conflict resolution

6. **memory_stats()** - Phase 11
   - Memory system statistics
   - Health metrics

**Note:** memory_query() does not exist. Use memory_context() for retrieval or memory_search() for FTS5 queries.

---

## Storage Architecture

**Single Global Database Design:**

All persistent data is stored in ONE location: `~/.cerberus/memory.db` (SQLite)

**What's stored in the global DB:**
- Memories (universal, language-specific, project-specific)
- Sessions (all projects, multi-tier scopes)
- Session history (completed, crashed, archived)
- Access tracking (last_accessed, usage counts)
- Anchors (Phase 14)
- Mode tags (Phase 15)
- Conflict tracking (Phase 19)

**Project-specific filtering:** Use `WHERE project_path = '/path/to/project'` in SQL queries

**Temporary runtime state:** `.cerberus-session.json` (project root, deleted at session end)
- Current session tracking only
- Session ID, turn counter, timestamp
- Deleted automatically on clean exit or stale session detection

**No other local files.** All persistent storage uses the global DB.

**Benefits:**
- Simple backups (one file)
- SQL joins work across projects
- No sync issues
- No config confusion
- Easy migrations

---

## Standardized Algorithms

### Recency Scoring (Memory Timestamps)

**Used in:** Phase 6 (retrieval), Phase 7 (context injection)

**Standardized decay curve:**
```python
if days_ago < 7:
    return 1.0
elif days_ago < 30:
    return 0.8
elif days_ago < 90:
    return 0.6
elif days_ago < 180:
    return 0.4
else:
    return 0.2
```

**Rationale:**
- Gradual decay over 180 days
- Recent memories (< 7 days) = maximum relevance
- Old memories (> 180 days) still retain 20% relevance
- Consistent across retrieval and injection phases

**Note:** Phase 14 (anchor discovery) uses exponential decay for **file modification times** (not memory timestamps), which is a different use case and intentionally different formula.

### Mode Detection Keywords (Phase 15)

**Used in:** Phase 15 (mode-aware context)

**Keyword Disambiguation:**
- **"show me"** → Exploration mode only (not audit)
  - Exploration: "show me what files", "show me the API"
  - Audit: "walk me through", "explain how", "what does"
- **Rationale:** "show me" implies listing/displaying (exploration action), while audit is about understanding (use "walk me through" instead)

**No overlaps allowed:** Each mode indicator must be unique to prevent ambiguous detection.

### Anchor Quality Scoring (Phase 14)

**Used in:** Phase 14 (anchor discovery for abstract rules)

**Quality Formula:**
```python
quality_score = (
    0.6 * relevance_score +    # TF-IDF similarity to rule text
    0.2 * size_score +         # Prefer concise examples (1.0 - size/500)
    0.2 * recency_score        # Exponential decay based on file mtime
)
```

**Component Weights:**
- **Relevance (60%)**: How well the file content matches the rule keywords
- **Size (20%)**: Smaller files are better examples (normalized to 500 lines max)
- **Recency (20%)**: Recently modified files reflect current patterns

**Threshold:**
- **Default**: `min_quality = 0.7` (70% minimum to be considered)
- **Configurable**: Can be adjusted per query
- **Range**: 0.0-1.0 (0.7 is balanced between precision and recall)

**Rationale:**
- Relevance is dominant (60%) because the example must match the rule
- Size and recency are secondary signals (20% each) for quality
- 0.7 threshold filters out weak matches while allowing good examples

### Conflict Severity Scoring (Phase 19)

**Used in:** Phase 19 (conflict detection and resolution)

**Severity Formula:**
```python
score = 0
score += 3 if (universal scope)         # Scope factor
score += 2 if (both recent < 7 days)    # Recency factor
score += 2 if (confidence > 0.9)        # Confidence factor
score += 2 if CONTRADICTION             # Type: most severe
score += 1 if OBSOLESCENCE              # Type: medium severity
score += 0 if REDUNDANCY                # Type: least severe

# Mapping
score >= 7: "critical"
score >= 5: "high"
score >= 3: "medium"
score < 3: "low"
```

**Scoring Factors:**
- **Scope (+3)**: Universal conflicts affect all projects, highest weight
- **Recency (+2)**: Both memories recent (< 7 days) = active conflict requiring quick resolution
- **Confidence (+2)**: High confidence (> 0.9) = well-established rules in conflict
- **Type (+2/+1/+0)**:
  - Contradiction (+2): Opposing rules ("use X" vs "avoid X")
  - Obsolescence (+1): Superseded rules (newer overwrites older)
  - Redundancy (+0): Duplicates (safe to merge/delete)

**Rationale:**
- Consistent formula for all conflict types
- Type severity: Contradiction > Obsolescence > Redundancy
- Max possible score: 9 (universal + recent + high confidence + contradiction)
- Min possible score: 0 (project scope + old + low confidence + redundancy)

### Auto-Approval Threshold (Phase 4)

**Used in:** Phase 4 (batch approval mode)

**Default:** `auto_approve_threshold = 0.9` (90% confidence)

**Purpose:**
When running in non-interactive batch mode, only proposals with confidence >= threshold are auto-approved.

**Configuration:**
```python
on_session_end(
    interactive=False,
    auto_approve_threshold=0.9  # Configurable, default 0.9
)
```

**Threshold Guidelines:**
- **0.9 (default)**: Conservative, high-quality proposals only
- **0.8**: Moderate, includes good proposals with some uncertainty
- **0.7**: Permissive, accepts more proposals (higher recall, lower precision)
- **1.0**: Only absolutely certain proposals (very strict)

**Rationale:**
- Default 0.9 balances quality and automation
- Configurable per invocation for different use cases
- Interactive mode ignores threshold (user decides)

### Session Timeout Values (Phases 8, 17)

**Used in:** Phase 17 (lifecycle), Phase 8 (continuity)

**Timeout Types:**

| Timeout | Default | Purpose | Phase | Configurable |
|---------|---------|---------|-------|--------------|
| **Stale Detection** | 5 min (300 sec) | Detect crashed sessions on startup | 17A | `SESSION_TIMEOUTS["stale_detection_seconds"]` |
| **Idle Timeout** | 30 min | Auto-end active sessions with no activity | 17A | `check_idle_timeout(timeout_minutes=N)` |
| **Check Interval** | 60 sec | Daemon frequency for idle checking | 17A | `idle_timeout_daemon(interval_seconds=N)` |
| **Archive Threshold** | 7 days | Archive completed sessions | 8 | `SessionContextInjector(idle_days=N)` |

**Configuration Examples:**
```python
# Phase 17A: Lifecycle timeouts
SESSION_TIMEOUTS = {
    "stale_detection_seconds": 300,   # 5 minutes
    "idle_timeout_minutes": 30,       # 30 minutes
    "check_interval_seconds": 60      # 60 seconds
}

# Phase 8: Archive threshold
injector = SessionContextInjector(
    db_path=db_path,
    idle_days=7  # Configurable
)

# Cleanup function
cleanup = SessionCleanup()
cleanup.cleanup_idle(days=7)  # Configurable
```

**Rationale:**
- Stale detection (5 min): Short window to catch crashes without false positives
- Idle timeout (30 min): Balance between auto-cleanup and user convenience
- Archive threshold (7 days): Keep recent sessions accessible, archive old ones
- All values configurable for different use cases

---

## Phase Breakdown (0-20)

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
- In-memory buffer during session (written to global DB at end)
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

**Implementation (TWO VERSIONS):**
- **Phase Alpha (MVP):** JSON storage ONLY (Version 1)
- **Phase Beta (Migration):** Code REPLACED with SQLite writes (Version 2 in PHASE-13B)

**Key Features:**
- Hierarchical routing (universal → language → project → task)
- Batch optimization (group by file, write once)
- Metadata tracking
- Directory/table auto-creation

**Directory Structure (Phase Alpha - JSON):**
```
~/.cerberus/memory.db (global SQLite database)
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

**Storage Evolution Timeline:**
- Phase Alpha: Phase 5 writes to JSON files (Version 1 code)
- Phase 12 (Beta): JSON data migrated to SQLite, JSON becomes backup
- Phase 13 (Beta): Phase 5 code REPLACED to write to SQLite (Version 2 code)
- Result: New writes go to SQLite, JSON is read-only backup

**Token Cost:** 0 tokens (pure storage)

---

### Phase 6: Retrieval Operations
**File:** `src/cerberus/memory/retrieval.py`

**Objective:** Query and filter memories for context-aware injection.

**Implementation (TWO VERSIONS):**
- **Phase Alpha (MVP):** JSON file loading (Version 1)
- **Phase Beta (Migration):** Code REPLACED with SQLite FTS5 queries (Version 2 in PHASE-13B)

**Key Features:**
- Scope-based loading (universal, language, project, task)
- Relevance scoring (scope + recency + confidence + task)
- Budget-aware retrieval (stop when budget exhausted)
- Integration with Phase 7 injection

**Retrieval Evolution Timeline:**
- Phase Alpha: Phase 6 loads all JSON files, filters in Python (Version 1 code)
- Phase 12 (Beta): JSON data available in SQLite after migration
- Phase 13 (Beta): Phase 6 code REPLACED to query SQLite FTS5 (Version 2 code)
- Result: Queries hit SQLite index (80% token savings), fallback to JSON if SQLite fails

**Token Cost:** 0 tokens (pure retrieval, tokens counted in Phase 7)

**Output:** List of `RetrievedMemory` objects

---

### Phase 7: Context-Aware Injection
**File:** `src/cerberus/memory/context_injector.py`

**Objective:** Hybrid memory injection - auto-inject high-relevance memories at session start, provide on-demand tool for additional context during work.

**Key Features:**
- Session start auto-injection (1000 tokens: preferences, project context, session continuity)
- On-demand MCP tool: memory_context(query) for specific topics during work
- Token budget enforcement (1000 startup + 1000 on-demand max = 2000 cap)
- Context detection (project, language, task auto-detected)
- Relevance scoring (high threshold for startup, broader for queries)

**Token Cost:** 2000 tokens at startup (1200 memories + 800 session codes), 0-1000 tokens on-demand (if Claude calls tool)

**Total Cap:** 3000 tokens per session

**Output:** Markdown-formatted memories for Claude's use

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
- Multi-tier sessions: universal + per-project isolation
- Storage: Uses `sessions` table in Phase 12's memory.db

**Token Cost:** 800 tokens per session (injection only, no LLM, AI-native codes)

**Output:** Raw codes, newline-separated (impl:, dec:, block:, next:)

**Storage:** Phase 12's `sessions` table (schema defined in PHASE-12-MEMORY-INDEXING.md)

**Why Phase Gamma (not Alpha/Beta):**
- Core memory system must be stable first
- Session continuity is enhancement, not blocker
- Can be added incrementally without risk
- Depends on stable Phase 7 injection

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
- SQLite schema with FTS5 (full-text search for memories)
- Sessions table (used by Phase 8 for session continuity)
- Session activity tracking table
- Auto-migration from JSON (one-time, transparent)
- Backward compatibility (keep JSON as fallback)
- WAL mode for concurrency (same as Cerberus code index)
- Integrity verification
- CLI tools (migrate, verify, migrate-sessions)

**Token Cost:** 0 tokens (one-time migration, no LLM)

**Storage:** `~/.cerberus/memory.db` (unified database for memories + sessions)

**Why Phase Beta (not Alpha):**
- Database complexity isolated from learning logic
- Can measure actual token savings empirically
- MVP proves value before optimization investment
- Rollback to JSON if issues

---

### Phase 13: Indexed Search & Integration
**File:** `src/cerberus/memory/search.py`

**Phase:** Beta (Migration layer)

**Objective:** FTS5 search queries, **replace** Phase 5-6 code with SQLite versions.

**Prerequisites:**
- ✅ Phase 12 complete (SQLite schema + migration)
- ✅ Migration validated (100% data integrity)

**Key Features:**
- FTS5-powered search engine (text, scope, category filters)
- Relevance scoring from FTS5 rank (BM25 algorithm)
- Snippet extraction (match context)
- **Phase 5 code replacement:** JSON writes → SQLite writes (Version 2)
- **Phase 6 code replacement:** JSON reads → SQLite FTS5 queries (Version 2)
- New MCP tool: `memory_search(query, scope, category, limit)`
- Access tracking (last_accessed, count)

**What "replacement" means:**
- Alpha: Phase 5/6 use JSON file code
- Beta: Phase 5/6 code completely rewritten to use SQLite
- Beta versions documented in PHASE-13B-INTEGRATION.md

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
- Session state tracking (.cerberus-session.json temp file, data in global DB)
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
- Crash detection (stale .cerberus-session.json > 5 minutes)
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
