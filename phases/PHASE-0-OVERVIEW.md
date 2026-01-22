# PHASE 0: ADAPTIVE LEARNING MEMORY SYSTEM - OVERVIEW

## Vision
Revolutionary memory system that learns from user corrections automatically, stores intelligently, and injects contextually.

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
│    ├─ LLM generates proposals (Phase 3: 10 user + 10 agent) │
│    ├─ CLI approval (Phase 4: < 30 seconds)                  │
│    ├─ Store to hierarchical layers (Phase 5)                │
│    └─ Save session codes (Phase 8: no LLM, direct save)     │
│    └─ Total cost: ~4000 tokens (~$0.06)                     │
├─────────────────────────────────────────────────────────────┤
│ 4. WEEKLY MAINTENANCE (automatic)                           │
│    ├─ Archive stale memories (>180 days) (Phase 11)         │
│    ├─ Detect conflicts (contradictions, redundancies)       │
│    ├─ Promote cross-project patterns                        │
│    └─ Cleanup expired sessions (>7 days) (Phase 8)          │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase Breakdown (0-11)

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

**Objective:** LLM generates proposals from corrections and agent patterns.

**Key Features:**
- LLM generates 10 user proposals (from Phase 2 clusters)
- LLM generates 10 agent proposals (from Phase 10 patterns)
- Scope detection (universal, language, project)
- Priority ranking

**Token Cost:** 2000 tokens per session (10 user + 10 agent proposals)

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

**Key Features:**
- Hierarchical routing (universal → language → project → task)
- Batch optimization (group by file, write once)
- Metadata tracking
- Directory auto-creation

**Directory Structure:**
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

**Token Cost:** 0 tokens (pure storage)

---

### Phase 6: Retrieval Operations
**File:** `src/cerberus/memory/retrieval.py`

**Objective:** Query and filter memories for context-aware injection.

**Key Features:**
- Scope-based loading (universal, language, project, task)
- Relevance scoring (scope + recency + confidence + task)
- Budget-aware retrieval (stop when budget exhausted)
- Integration with Phase 7 injection

**Token Cost:** 0 tokens (pure retrieval, tokens counted in Phase 7)

**Output:** List of `RetrievedMemory` objects

---

### Phase 7: Context-Aware Injection
**File:** `src/cerberus/memory/context_injector.py`

**Objective:** Inject only relevant memories with 1500 token budget.

**Key Features:**
- Uses Phase 6 retrieval
- Token budget enforcement (700 universal + 500 language + 300 project)
- Context detection (project, language, task auto-detected)
- Hook-based injection (automatic, not tool call)

**Token Cost:** 1500 tokens max (enforced)

**Output:** Markdown string for prompt injection

---

### Phase 8: Session Continuity
**File:** `src/cerberus/memory/session_continuity.py`

**Objective:** Capture session context during work, inject at next session start. Zero re-explanation. NO LLM.

**Key Features:**
- Context Capture: AI-native codes (impl:, dec:, block:, next:)
- Auto-capture from tool usage (Edit, Write, Bash)
- Context Injection: Pure data, no LLM, no prose
- Comprehensive capture (ALL files, decisions, blockers)
- 7-day expiration with archival
- Session cleanup manager

**Token Cost:** 1000-1500 tokens per session (injection only, no LLM)

**Output:** Raw codes, newline-separated (impl:, dec:, block:, next:)

---

### Phase 9: (Merged into Phase 8)
*Session Context Injection merged into Phase 8: Session Continuity*

---

### Phase 10: Agent Self-Learning
**File:** `src/cerberus/memory/agent_learning.py`

**Objective:** Agent detects success/failure patterns and proposes memories proactively.

**Key Features:**
- Success reinforcement (repeated approved actions)
- Failure avoidance (repeated corrections)
- Project pattern inference (codebase consistency)
- Approach reinforcement (explicit praise detection)
- 4 detection patterns with confidence scoring

**Token Cost:** 2000 tokens per session (10 agent proposals)

**Output:** List of `AgentProposal` objects (fed into Phase 3)

---

### Phase 11: Maintenance & Health
**File:** `src/cerberus/memory/maintenance.py`

**Objective:** Auto-maintain memory health.

**Key Features:**
- Stale detection (>60 days unused)
- Auto-archival (>180 days)
- Conflict detection (contradictions, redundancies, obsolete)
- Cross-project promotion (pattern in 3+ projects → universal)
- Session cleanup (>7 days expired)
- Weekly health checks

**Token Cost:** 0 tokens (offline analysis)

---

### Phase 12: Memory Indexing
**File:** `src/cerberus/memory/indexing.py`

**Objective:** Migrate memories from JSON → SQLite FTS5. Foundation for scalable search.

**Key Features:**
- SQLite schema with FTS5 (full-text search)
- Auto-migration from JSON
- Backward compatibility (keep JSON as fallback)
- WAL mode for concurrency
- Integrity verification
- CLI tools (migrate, verify)

**Token Cost:** 0 tokens (one-time migration, no LLM)

**Storage:** `~/.cerberus/memory.db`

---

### Phase 13: Indexed Search & Integration
**File:** `src/cerberus/memory/search.py`

**Objective:** FTS5 search queries, update Phase 5-6 to use SQLite.

**Key Features:**
- FTS5-powered search (text, scope, category filters)
- Relevance scoring from FTS5 rank
- Snippet extraction (match context)
- Phase 5 updates (write to SQLite)
- Phase 6 updates (query SQLite)
- New MCP tool: `memory_search()`
- Access tracking (last_accessed, count)

**Token Cost:** 0 tokens (pure search, no LLM)

**Token Savings:** 80% reduction (load 10 matches vs 50 all memories)

---

## Implementation Order

```
Phase 1 (User Correction Detection) ┐
                                     ├→ Phase 2 (Deduplication)
Phase 10 (Agent Self-Learning)      ┘       ↓
                                          Phase 3 (Proposal: User + Agent)
                                             ↓ approval by
                                          Phase 4 (TUI Approval)
                                             ↓ stores to
Phase 8 (Context Capture) ─────────→ Phase 5 (Storage) ←─ Phase 12 (Indexing)
Phase 9 (Session Injection) ───────→        │                    │
                                             ↓ loaded by          ↓
                                          Phase 6 (Retrieval) ←─ Phase 13 (Search)
                                             ↓ injected by
                                          Phase 7 (Injection: Memory + Session)
                                             ↓ maintained by
                                          Phase 11 (Maintenance)
```

**Recommended Order:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13

**MVP (Phases 1-7):**
- Phase 1: User correction detection
- Phase 2: Semantic deduplication
- Phase 3: Proposal generation
- Phase 4: TUI approval interface
- Phase 5: Storage operations
- Phase 6: Retrieval operations
- Phase 7: Context-aware injection

**Enhancement (Phases 8-10):**
- Phase 8: Context capture (session context)
- Phase 9: Session code injection (continuity)
- Phase 10: Agent self-learning (agent proposals)

**Maintenance (Phase 11):**
- Phase 11: Maintenance & health (deferred)

**Optimization (Phases 12-13):**
- Phase 12: Memory indexing (SQLite FTS5 foundation)
- Phase 13: Indexed search (FTS5 queries, 80% token savings)

**Reasoning:**
- Phases 1-4 form complete "user learning pipeline"
- Phase 5-6 must exist before Phase 7 (storage before retrieval before injection)
- Phase 8-9 add session continuity (can be built after MVP)
- Phase 10 adds agent learning (feeds back into Phase 3)
- Phase 11 operates on existing system (build last)
- Phases 12-13 optimize at scale (defer until 100+ memories)

---

## MVP Definition (1-2 weeks)

**Must Have (Phases 1-7):**
- Phase 1: User correction detection (4 patterns)
- Phase 2: Clustering (basic, no LLM canonical extraction)
- Phase 3: Proposal (LLM-based, user corrections only for MVP)
- Phase 4: TUI approval (arrow keys, inline, with CLI fallback)
- Phase 5: Storage (universal + language + project layers)
- Phase 6: Retrieval (scope-based, relevance scoring)
- Phase 7: Injection (1500 token budget, memory only)

**Enhancement Layer (Phases 8-10):**
- Phase 8: Context capture (AI-native codes)
- Phase 9: Session summary (LLM summary + injection)
- Phase 10: Agent self-learning (success/failure patterns)
- Integrated proposal system (10 user + 10 agent = 20 total)
- Enhanced injection (1500 memory + 500 session = 2000 tokens)

**Nice to Have (defer):**
- Phase 11: Maintenance (manual for MVP)
- LLM canonical extraction in Phase 2
- Task layer in Phase 5
- Advanced conflict detection
- Codebase pattern analyzer for Phase 10

---

## Success Metrics

**Week 1-2 (MVP):**
- ✓ Detection: 90%+ accuracy on 10 test scenarios
- ✓ Clustering: 60%+ compression ratio
- ✓ Proposal: User approves 70%+ of proposals
- ✓ Injection: Always under 1000 tokens

**Week 3-4 (Full System):**
- ✓ Zero repeated corrections across sessions
- ✓ Memory growth: < 10 entries per week
- ✓ Health: No conflicts after 2 weeks
- ✓ User satisfaction: "This is revolutionary"

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
pip install scikit-learn numpy tiktoken
pip install ollama-python  # Or anthropic SDK (optional, for LLM proposals)
```

**Model Requirements:**
- TF-IDF: scikit-learn (no model download)
- LLM: Ollama (llama3.2:3b) or Claude API (optional, for proposals)

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
└── PHASE-13-INDEXED-SEARCH.md

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
└── search.py                (Phase 13: FTS5 search engine)

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

## Quick Start for AI Agents

**Step 1:** Read this overview (PHASE-0-OVERVIEW.md)

**Step 2:** Choose a phase to implement

**Step 3:** Read phase-specific document (e.g., PHASE-1-SESSION-CORRECTION-DETECTION.md)

**Step 4:** Implement following exit criteria in phase document

**Step 5:** Run tests specified in phase document

**Step 6:** Verify integration with adjacent phases

---

## Questions & Answers

**Q: Why not auto-store without user approval?**
A: Prevents false positives. User confirms = 100% accuracy.

**Q: Why LLM for proposals?**
A: Extracts intent ("keep it short" + "be terse" → "Keep output concise").

**Q: Why 1500 token budget for memory injection?**
A: Balance: Enough for comprehensive rules, not bloated. Tested optimal.

**Q: Why hierarchical storage?**
A: Relevance filtering. Go project doesn't need Python rules.

**Q: Why local embeddings vs API?**
A: Zero cost, zero latency, works offline.

---

## Contact & Support

**Issues:** File in cerberus GitHub repo
**Discussion:** Discord #cerberus channel
**Docs:** Read phase documents in `phases/`

---

**Last Updated:** 2026-01-22
**Version:** 2.0 (12-phase structure, $0.10 budget, TUI approval)
**Status:** Ready for implementation
