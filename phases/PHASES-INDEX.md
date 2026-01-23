# CERBERUS MEMORY SYSTEM - PHASE INDEX

**Total Phases:** 20 phases (0-20, no Phase 9 - merged into Phase 8)
**Total Files:** 30 implementation specs

---

## Single-File Phases (13 phases)

**Core Pipeline (Alpha):**
- **PHASE-1**: Session Correction Detection (259 lines)
- **PHASE-2**: Semantic Deduplication (477 lines)
- **PHASE-3**: Session Proposal (573 lines)
- **PHASE-4**: TUI Approval Interface (318 lines)
- **PHASE-5**: Storage Operations (345 lines)
- **PHASE-6**: Retrieval Operations (587 lines)
- **PHASE-7**: Context-Aware Injection (605 lines)

**Enhancements (Gamma):**
- **PHASE-8**: Session Continuity (604 lines)
- **PHASE-11**: Maintenance & Health (607 lines)
- **PHASE-12**: Memory Indexing (590 lines)

**Integration (Epsilon):**
- **PHASE-16**: Integration Specification (538 lines)

---

## Multi-Part Phases (9 phases split into 20 files)

### Phase 0: System Overview (3 parts)
- **PHASE-0A-OVERVIEW** (140 lines): Vision, TL;DR, rollout strategy
- **PHASE-0B-ARCHITECTURE** (532 lines): System architecture, phase breakdown (0-20)
- **PHASE-0C-FOUNDATIONS** (719 lines): Implementation strategy, roadmap, validation gates

### Phase 10: Agent Self-Learning (2 parts)
- **PHASE-10A-DETECTION** (601 lines): 4 detection patterns, codebase analysis
- **PHASE-10B-REFINEMENT** (312 lines): Proposal refinement (template + LLM)

### Phase 13: Indexed Search (2 parts)
- **PHASE-13A-SEARCH-ENGINE** (244 lines): FTS5 search, query building
- **PHASE-13B-INTEGRATION** (499 lines): Phase 5/6 updates, MCP tool

### Phase 14: Dynamic Anchoring (2 parts)
- **PHASE-14A-ANCHOR-DISCOVERY** (227 lines): Anchor discovery algorithm, scoring
- **PHASE-14B-ANCHOR-INTEGRATION** (541 lines): Storage schema, injection, CLI

### Phase 15: Mode-Aware Context (2 parts)
- **PHASE-15A-MODE-DETECTION** (308 lines): Mode detection algorithm, definitions
- **PHASE-15B-MODE-INTEGRATION** (546 lines): Memory tagging, storage, injection filtering

### Phase 17: Session Lifecycle (2 parts)
- **PHASE-17A-LIFECYCLE** (308 lines): Session start/end, activity tracking
- **PHASE-17B-RECOVERY** (339 lines): Crash detection, timeout, file locking

### Phase 18: Approval Optimization (2 parts)
- **PHASE-18A-ALGORITHMS** (285 lines): Auto-approval + smart batching
- **PHASE-18B-INTERFACE** (389 lines): Optimized UI, history learning

### Phase 19: Conflict Resolution (2 parts)
- **PHASE-19A-CONFLICT-DETECTION** (235 lines): Extended conflict detection
- **PHASE-19B-CONFLICT-RESOLUTION** (470 lines): Auto-resolution, user-mediated

### Phase 20: Silent Divergence (2 parts)
- **PHASE-20A-TRACKING** (208 lines): Tool usage tracking, detection
- **PHASE-20B-ANALYSIS** (448 lines): Diff analysis, pattern extraction

---

## Why Some Phases Are Split

**Phases split for AI agent context management:**
- Original files over 650 lines → Split at natural boundaries
- Each part focuses on ONE major algorithm or system
- Prevents rushed implementations and stub generation
- Maintains semantic cohesion (related code stays together)

**Reading order for split phases:**
- Read part A first (detection/discovery/algorithms)
- Then read part B (integration/processing/interface)
- Parts are sequential, not parallel

---

## Quick Reference: Rollout Phases

| Rollout | Phases | Files |
|---------|--------|-------|
| **Alpha** | 1-7 | 7 files (JSON storage) |
| **Beta** | 12-13, update 5-6 | 4 files (SQLite migration) |
| **Gamma** | 8, 10, 11 | 5 files (enhancements) |
| **Delta** | 14-15 | 4 files (anchoring + modes) |
| **Epsilon** | 16-20 | 10 files (critical fixes) |

---

## File Sizes (for reference)

**Optimal range (200-600 lines):** 28 files
**Acceptable range (600-720 lines):** 2 files (0C, 11)
**All files under:** 720 lines

**Largest files:**
1. PHASE-0C-FOUNDATIONS: 719 lines (reference material)
2. PHASE-11-MAINTENANCE-HEALTH: 607 lines (cohesive operations)
3. PHASE-7-CONTEXT-AWARE-INJECTION: 605 lines (single purpose)
4. PHASE-8-SESSION-CONTINUITY: 604 lines (unified concept)
5. PHASE-10A-DETECTION: 601 lines (detection patterns)

---

**Last Updated:** 2026-01-22
**Status:** All phases finalized and split for optimal AI agent implementation
**Originals:** Backed up in `phases/original/` (9 large files before splitting)
