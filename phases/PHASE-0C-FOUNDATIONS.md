
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
    Enhanced injection (1500 memory + 1000-1500 session = 2500-3000 tokens)

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
- Session code injection: 1000-1500 tokens (Phase 8)
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
