# PHASE RESTRUCTURING SUMMARY

## Changes Made

### Budget Increase
**Old:** $0.05/session (~3333 tokens)
**New:** $0.10/session (~6666 tokens)

**Allocation:**
- Session start: 2000 tokens (1500 memory + 500 session)
- Session end: 4500 tokens (2000 user + 2000 agent + 500 summary)
- Total: 6500 tokens (~$0.098)

### New Phase Structure (12 phases total)

**PHASE 0: OVERVIEW** (updated)
- Added TUI interface
- Updated budget to $0.10
- New phase structure
- Enhanced token allocation

**PHASE 1: SESSION CORRECTION DETECTION** (unchanged)
- User correction detection
- 4 patterns, 0 tokens
- File: session_analyzer.py

**PHASE 2: SEMANTIC DEDUPLICATION** (unchanged)
- Clustering, embeddings
- 60% compression
- File: semantic_analyzer.py

**PHASE 3: PROPOSAL GENERATION** (trimmed)
- LLM proposal generation ONLY
- Removed approval interface (moved to Phase 4)
- File: proposal_engine.py

**PHASE 4: TUI APPROVAL INTERFACE** (NEW - created)
- Inline TUI with arrow keys
- Rich + keyboard libraries
- 6x faster than CLI typing
- File: approval_tui.py

**PHASE 5: STORAGE OPERATIONS** (rewritten - focused)
- Write operations ONLY
- Hierarchical routing
- Batch optimization
- File: storage.py

**PHASE 6: RETRIEVAL OPERATIONS** (needs creation)
- Read operations ONLY
- Filtering, querying
- Relevance scoring
- File: retrieval.py

**PHASE 7: CONTEXT-AWARE INJECTION** (renamed from old 4)
- Memory injection at session start
- 1500 tokens (1000 memory + 500 session)
- File: context_injector.py

**PHASE 8: CONTEXT CAPTURE** (split from old 8)
- Auto-capture during session
- Files, functions, decisions, blockers
- AI-native storage codes
- File: context_capture.py

**PHASE 9: SESSION SUMMARY** (needs creation)
- LLM summary generation
- Injection at session start
- 500 token budget
- File: session_summary.py

**PHASE 10: AGENT SELF-LEARNING** (renamed from old 7)
- Success/failure patterns
- 2000 token budget (10 proposals)
- File: agent_learning.py

**PHASE 11: MAINTENANCE & HEALTH** (renamed from old 6)
- Stale detection, conflicts, promotion
- Weekly execution
- File: maintenance.py

---

## Files Created

✓ PHASE-4-TUI-APPROVAL-INTERFACE.md (8.5K)
✓ PHASE-5-STORAGE-OPERATIONS.md (rewritten, 6.5K)

## Files Renamed

✓ Old PHASE-4 → PHASE-7 (Context-Aware Injection)
✓ Old PHASE-5 → PHASE-5 (rewritten as Storage Operations)
✓ Old PHASE-6 → PHASE-11 (Maintenance & Health)
✓ Old PHASE-7 → PHASE-10 (Agent Self-Learning)
✓ Old PHASE-8 → PHASE-8 (split into capture only)

---

## Still Needs Creation

**PHASE-6-RETRIEVAL-OPERATIONS.md**
- Query memories by scope
- Filter by relevance
- Ranking algorithms
- Integration with Phase 7 injection

**PHASE-9-SESSION-CONTEXT-INJECTION.md**
- Direct Phase 8 code injection (NO LLM)
- Comprehensive capture (ALL files, decisions, blockers)
- Pure data injection (no prose, no markdown)
- 1000-1500 token budget (temporary, deleted after read)
- Expiration/cleanup (7 days)

---

## Updated Token Budget ($0.10 cap)

### Session Start: 2000 tokens
```
Memory injection (Phase 7):  1500 tokens
  - Universal: 700 tokens
  - Language: 500 tokens
  - Project: 300 tokens

Session context (Phase 9):   500 tokens
  - Summary: 150 tokens
  - Next actions: 150 tokens
  - Decisions: 100 tokens
  - Blockers: 100 tokens
```

### Session End: 4500 tokens
```
User proposals (Phase 3):    2000 tokens
  - 10 proposals × 200 tokens each

Agent proposals (Phase 10):  2000 tokens
  - 10 proposals × 200 tokens each

Session summary (Phase 9):   500 tokens
  - Context capture formatting
  - LLM summary generation
```

**Total: 6500 tokens (~$0.098 with safety margin)**

---

## Implementation Order

**MVP (Phases 1-7):**
1. Phase 1: User Correction Detection
2. Phase 2: Semantic Deduplication
3. Phase 3: Proposal Generation
4. Phase 4: TUI Approval Interface
5. Phase 5: Storage Operations
6. Phase 6: Retrieval Operations (needs creation)
7. Phase 7: Context-Aware Injection

**Enhancement (Phases 8-10):**
8. Phase 8: Context Capture
9. Phase 9: Session Summary (needs creation)
10. Phase 10: Agent Self-Learning

**Maintenance (Phase 11):**
11. Phase 11: Maintenance & Health (deferred)

---

## Next Steps for AI Agent

1. **Create PHASE-6-RETRIEVAL-OPERATIONS.md**
   - Focus: Query, filter, rank memories
   - Integration: Load data from Phase 5 storage
   - Output: Filtered memory list for Phase 7
   - Size target: 8-10K (focused, no storage logic)

2. **Create PHASE-9-SESSION-SUMMARY.md**
   - Focus: LLM summary + injection
   - Integration: Use context from Phase 8
   - Output: Session context for next session
   - Size target: 8-10K (focused, no capture logic)

3. **Update PHASE-0-OVERVIEW.md**
   - New phase structure (0-11)
   - Updated token budget ($0.10)
   - Updated implementation order
   - Updated file manifest

4. **Update PHASE-8-CONTEXT-CAPTURE.md**
   - Remove summary generation (moved to Phase 9)
   - Focus only on capture during session
   - Remove injection logic (moved to Phase 9)
   - Size target: 8-10K (capture only)

5. **Update PHASE-3-SESSION-PROPOSAL.md**
   - Remove approval interface (moved to Phase 4)
   - Focus only on LLM proposal generation
   - Size target: 8-10K (generation only)

6. **Verify all cross-references**
   - Update phase numbers in all docs
   - Fix integration examples
   - Update file paths

---

## Quality Checklist

**Per Phase:**
- [ ] AI-native format (no prose)
- [ ] Single responsibility (< 12K, focused)
- [ ] Clear integration points
- [ ] Exit criteria defined
- [ ] 10+ test scenarios
- [ ] Token budget specified
- [ ] Dependencies listed
- [ ] Performance targets

**System-Wide:**
- [ ] Total budget under $0.10
- [ ] No circular dependencies
- [ ] Clear data flow (1→2→3→4→5→7, 8→9→7, 10→3)
- [ ] Graceful fallbacks (TUI→CLI, LLM→template)
- [ ] Session isolation (no leaks)

---

## File Sizes (Current)

```
PHASE-0-OVERVIEW.md:                      16K (needs update)
PHASE-1-SESSION-CORRECTION-DETECTION.md:  6.9K ✓
PHASE-2-SEMANTIC-DEDUPLICATION.md:        9K ✓
PHASE-3-SESSION-PROPOSAL.md:              13K (needs trim)
PHASE-4-TUI-APPROVAL-INTERFACE.md:        8.5K ✓
PHASE-5-STORAGE-OPERATIONS.md:            6.5K ✓
PHASE-6-RETRIEVAL-OPERATIONS.md:          MISSING
PHASE-7-CONTEXT-AWARE-INJECTION.md:       15K ✓
PHASE-8-CONTEXT-CAPTURE.md:               19K (needs trim)
PHASE-9-SESSION-SUMMARY.md:               MISSING
PHASE-10-AGENT-SELF-LEARNING.md:          16K ✓
PHASE-11-MAINTENANCE-HEALTH.md:           18K ✓
```

**Target:** All phases 8-12K (focused, single responsibility)

---

## Critical Path (What User Needs Most)

1. **Session Continuity** (Phases 8-9)
   - Solves momentum problem IMMEDIATELY
   - Highest user value

2. **TUI Approval** (Phase 4)
   - 6x faster than CLI
   - Better UX = more proposals reviewed

3. **Enhanced Learning** (Phase 10)
   - Agent observations
   - Proactive pattern detection

4. **Proper Storage** (Phases 5-6)
   - Foundation for everything
   - Must be correct first time

---

## Risk Assessment

**Low Risk (90% confidence):**
- Phases 1-5: Core learning pipeline works
- Phase 7: Injection mechanism validated
- Phase 11: Maintenance is deferred, low pressure

**Medium Risk (70% confidence):**
- Phase 4: TUI library compatibility
- Phase 6: Relevance scoring needs tuning
- Phase 9: Direct code injection (removed LLM risk)

**High Risk (50% confidence):**
- Phase 8: Auto-capture accuracy
- Phase 10: Agent pattern detection subtlety

**Mitigation:**
- All high-risk phases have fallbacks
- Iterative tuning expected
- User feedback loop critical

---

## Success Metrics (Updated)

**Week 1-2 (MVP: Phases 1-7):**
- ✓ User correction detection: 70%+ accuracy
- ✓ Clustering: 60%+ compression
- ✓ TUI approval: < 10 seconds
- ✓ Storage: 100% reliable
- ✓ Injection: Always under 1500 tokens

**Week 3-4 (Enhancement: Phases 8-10):**
- ✓ Session continuity: Zero re-explanation
- ✓ Agent learning: 50%+ user approval rate
- ✓ Combined proposals: 20 total, 60%+ approved

**Month 2 (Polish: Phase 11):**
- ✓ No stale memories (auto-archived)
- ✓ No conflicts detected
- ✓ Cross-project patterns promoted

---

## Final System Capacity

**With $0.10-0.105 budget:**
- 20 proposals per session (10 user + 10 agent)
- 1500 tokens memory injection (vs 1000 before)
- 1000-1500 tokens session codes (comprehensive, temporary)
- Rich session continuity (zero re-explanation)
- Fast TUI approval (< 10 sec vs 30+ sec)
- Pure AI-native data (no human prose anywhere)

**Result:** Revolutionary memory system that actually works.

---

## Phase 9 V2 Changes (AI-Native Session Continuity)

**Problem:** V1 used LLM to summarize into 2-3 sentences (human prose, token waste, detail loss)

**Solution:** Direct code injection, no LLM, comprehensive capture

**REMOVED from Phase 9:**
- LLM summary generation (was 150 tokens)
- Human prose sentences
- Markdown formatting
- Headers, sections
- "Top 5" selection (now captures ALL)

**ADDED to Phase 9:**
- Direct Phase 8 code injection (no processing)
- Comprehensive capture (ALL files, decisions, blockers)
- Higher budget: 500 → 1000-1500 tokens
- Temporary storage justification
- Pure AI-native format (impl:, dec:, block:, next:)

**Budget Impact:**
- Session start: 2000 → 2500-3000 tokens (increased)
- Session end: 4500 → 4000 tokens (decreased, no LLM)
- Total: 6500 → 6500-7000 tokens (~$0.098-0.105)

**Result:** Zero re-explanation, worth slight budget overage.

---

## Phase 12-13: Memory Indexing & Search (Optimization Layer)

**Problem:** JSON-based storage doesn't scale past 100 memories, wastes tokens

**Solution:** SQLite FTS5 indexing (same pattern as Cerberus code indexing)

### Phase 12: Memory Indexing (Foundation)
**File:** `src/cerberus/memory/indexing.py`

**Created:**
- SQLite schema with FTS5
- Auto-migration from JSON → SQLite
- Backward compatibility (keep JSON as fallback)
- CLI tools (cerberus memory migrate, verify)
- Integrity verification

**Key Features:**
- `~/.cerberus/memory.db` (SQLite with FTS5)
- WAL mode for concurrency
- Stale detection support (last_accessed, access_count)
- One-time migration, no LLM

**Why Defer to Optimization:**
- MVP proves concept with JSON
- Add indexing when scale matters (100+ memories)
- Can migrate JSON → SQL later without breaking

### Phase 13: Indexed Search & Integration
**File:** `src/cerberus/memory/search.py`

**Created:**
- FTS5 search engine
- Relevance scoring (FTS5 rank)
- Snippet extraction (match context)
- Budget-aware search
- Phase 5 updates (write to SQLite)
- Phase 6 updates (query SQLite)
- New MCP tool: `memory_search(query, scope, category, limit)`

**Token Efficiency Gain:**
```
Before (JSON):
  Load all 50 memories → Filter in Python → Keep 10
  Tokens: 50 × 30 = 1500 tokens (1200 wasted)

After (SQLite FTS5):
  FTS5 query returns 10 matches only
  Tokens: 10 × 30 = 300 tokens (0 wasted)

Savings: 80% token reduction
```

**Example Queries:**
```python
# Find Go split rules
memory_search("split files", scope="language:go", limit=5)

# Recent project decisions
memory_search("", scope="project:hydra", category="decision", limit=10)

# High-confidence corrections
memory_search("keep output short", min_confidence=0.8, limit=20)
```

**No Infrastructure Needed:**
- SQLite is just a file (no daemon)
- Python sqlite3 module (built-in)
- Same pattern as Cerberus index.db
- File locking handled automatically (WAL mode)

**Implementation Order:**
- Defer to optimization phase (after MVP working)
- Phase 12 → Phase 13 (foundation then search)
- Update Phase 5-6 incrementally
- Keep JSON fallback during transition

**Result:** Scales to 1000+ memories, 80% token savings, no infrastructure.
