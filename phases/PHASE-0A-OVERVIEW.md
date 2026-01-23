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
- Context-aware injection (2500-3000 token budget: 1500 memories + 1000-1500 session)
  - SessionStart hook auto-injects filtered context (not all memories)
  - Tiered filtering: universal + language + project only
  - Scope matching: only current project session loaded
- Hierarchical storage (universal → language → project → task)
- Self-healing system (archive stale, detect conflicts, promote patterns)
- Session continuity (zero re-explanation between sessions)

---

## System Architecture

```
Session Cycle:
┌─────────────────────────────────────────────────────────────┐
│ 1. SESSION START (SessionStart hook)                        │
│    ├─ Auto-inject relevant memories (Phase 7: 1500 tokens)  │
│    │  └─ Context-aware: universal + language + project      │
│    ├─ Auto-inject session codes (Phase 8: 1000-1500 tokens) │
│    │  └─ Scope-matched: only current project session        │
│    └─ Total budget: 2500-3000 tokens (filtered, not all)    │
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

