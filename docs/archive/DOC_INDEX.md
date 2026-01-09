# Documentation Index

Complete guide to Cerberus documentation - what to read, what to trust, and what's archived.

---

## 🎯 Start Here

### For Users
1. **[README.md](./README.md)** - Main entry point, features, installation, quick start
2. **[CERBERUS.md](./CERBERUS.md)** - AI agent context file (UACP v1.0 format) - **SOURCE OF TRUTH**
3. **[docs/AGENT_GUIDE.md](./docs/AGENT_GUIDE.md)** - How to integrate Cerberus with AI agents

### For Developers
1. **[docs/MANDATES.md](./docs/MANDATES.md)** - Development rules and architectural principles
2. **[docs/VISION.md](./docs/VISION.md)** - Philosophy and long-term strategy
3. **[docs/ROADMAP.md](./docs/ROADMAP.md)** - Phase status and future plans
4. **[FEATURE_MATRIX.md](./FEATURE_MATRIX.md)** - Complete feature catalog by phase

---

## 📚 Current Documentation (v0.5.0)

### Core Documentation
| File | Purpose | Audience | Last Updated |
|------|---------|----------|--------------|
| [README.md](./README.md) | Main overview, installation, usage | Everyone | 2026-01-08 |
| [CERBERUS.md](./CERBERUS.md) | AI agent context (UACP v1.0) | AI Agents | 2026-01-08 |
| [FEATURE_MATRIX.md](./FEATURE_MATRIX.md) | Complete feature catalog | Developers | 2026-01-08 |

### Developer Documentation
| File | Purpose | Audience | Last Updated |
|------|---------|----------|--------------|
| [docs/VISION.md](./docs/VISION.md) | Philosophy & strategy | Contributors | 2026-01-08 |
| [docs/MANDATES.md](./docs/MANDATES.md) | Development rules | Contributors | 2026-01-08 |
| [docs/ROADMAP.md](./docs/ROADMAP.md) | Phase status & plans | Everyone | 2026-01-08 |
| [docs/AGENT_GUIDE.md](./docs/AGENT_GUIDE.md) | AI agent integration | Agent Developers | 2026-01-08 |
| [docs/DOGFOODING_IMPROVEMENTS.md](./docs/DOGFOODING_IMPROVEMENTS.md) | Internal improvements log | Contributors | 2026-01-08 |

### Verification & Analysis
| File | Purpose | Audience | Last Updated |
|------|---------|----------|--------------|
| [CERBERUS_AUDIT_2026-01-08.md](./CERBERUS_AUDIT_2026-01-08.md) | Phase 6 completion audit | Developers | 2026-01-08 |
| [AGENT_COMPATIBILITY_REPORT.md](./AGENT_COMPATIBILITY_REPORT.md) | Cross-agent test results | Developers | 2026-01-08 |
| [COMPRESSION_ANALYSIS.md](./COMPRESSION_ANALYSIS.md) | Context file optimization | Developers | 2026-01-08 |
| [tools/competitive_analysis.md](./tools/competitive_analysis.md) | Honest competitor comparison | Decision Makers | 2026-01-08 |

---

## 📦 Archived Documentation

These files are kept for historical reference but are **superseded** by current documentation.

### Location: `docs/archive/`

| File | Reason Archived | Superseded By |
|------|-----------------|---------------|
| `PHASE2_DESIGN.md` | Phase complete | ROADMAP.md |
| `PHASE2_SUMMARY.md` | Phase complete | ROADMAP.md |
| `PHASE2_VALIDATION_RESULTS.md` | Phase complete | CERBERUS_AUDIT_2026-01-08.md |
| `PHASE3_COMPLETE.md` | Phase complete | ROADMAP.md |
| `PHASE3_DESIGN.md` | Phase complete | ROADMAP.md |
| `PHASE3_BENCHMARK_RESULTS.md` | Phase complete | CERBERUS_AUDIT_2026-01-08.md |
| `PHASE3_MILESTONE1_COMPLETE.md` | Milestone complete | ROADMAP.md |
| `PHASE3_MILESTONE2_COMPLETE.md` | Milestone complete | ROADMAP.md |
| `PHASE3_MILESTONE3_COMPLETE.md` | Milestone complete | ROADMAP.md |
| `PHASE4_COMPLETION.md` | Phase complete | ROADMAP.md |
| `PHASE4_ENHANCEMENTS.md` | Phase complete | ROADMAP.md |
| `Phase 4 -TODO.md` | Phase complete | ROADMAP.md |
| `PHASE5_COMPLETE.md` | Phase complete | ROADMAP.md |
| `PHASE6_COMPLETE.md` | Phase complete | ROADMAP.md |
| `LLM_FEATURE_NOTES.md` | Design notes | VISION.md |
| `AGENT_INSTRUCTIONS.md` | Old agent format | CERBERUS.md (UACP v1.0) |
| `COMPLETION_SUMMARY.md` | Session summary | CERBERUS_AUDIT_2026-01-08.md |
| `CERBERUS_COMPRESSION_TEST.md` | Old compression test | COMPRESSION_ANALYSIS.md |
| `CERBERUS_VALIDATION_TEST.md` | Old validation test | AGENT_COMPATIBILITY_REPORT.md |
| `SESSION_SUMMARY_2026-01-08.md` | Session summary | CERBERUS_AUDIT_2026-01-08.md |

---

## 🔍 How to Navigate

### "I want to understand what Cerberus does"
→ Start with [README.md](./README.md)

### "I want to integrate Cerberus with my AI agent"
→ Read [CERBERUS.md](./CERBERUS.md) then [docs/AGENT_GUIDE.md](./docs/AGENT_GUIDE.md)

### "I want to contribute to Cerberus"
→ Read [docs/MANDATES.md](./docs/MANDATES.md) and [docs/VISION.md](./docs/VISION.md)

### "I want to know what features are available"
→ Check [FEATURE_MATRIX.md](./FEATURE_MATRIX.md)

### "I want to know what's coming next"
→ See [docs/ROADMAP.md](./docs/ROADMAP.md)

### "I want to see how Cerberus compares to alternatives"
→ Read the "Competitive Comparison" section in [README.md](./README.md)
→ For detailed analysis: [tools/competitive_analysis.md](./tools/competitive_analysis.md)

### "I want to verify the project's current state"
→ Run `cerberus verify-context` to check CERBERUS.md validity
→ Read [CERBERUS_AUDIT_2026-01-08.md](./CERBERUS_AUDIT_2026-01-08.md) for Phase 6 audit

---

## 📝 Documentation Standards

All current documentation follows these principles:

1. **No Speculative Features** - Document only what exists today
2. **Real Data** - Use actual metrics from tests (no estimates or goals)
3. **Honest Assessment** - Clearly state limitations and when alternatives are better
4. **Agent-Readable** - CERBERUS.md uses UACP v1.0 format for AI agent consumption
5. **Version Stamped** - All docs reference current version (0.5.0)

---

## 🔄 Keeping Documentation Current

**After code changes:**
```bash
# Verify CERBERUS.md matches codebase
cerberus verify-context

# Auto-regenerate if needed
cerberus verify-context --fix
```

**After completing a major feature:**
1. Update FEATURE_MATRIX.md
2. Update docs/ROADMAP.md
3. Run `cerberus verify-context`
4. Update README.md if user-facing

**Archive old documentation when:**
- Phase completes → Move PHASE*_COMPLETE.md to docs/archive/
- Design superseded → Move design docs to docs/archive/
- Summary replaced → Move to docs/archive/

---

## 📊 Documentation Metrics

- **Current docs:** 10 files
- **Archived docs:** 19 files
- **Total markdown:** 29 files (excluding test_data/)
- **CERBERUS.md size:** 756 tokens (~6,798 bytes)
- **README.md size:** ~2,500 words
- **Last full audit:** 2026-01-08

---

**For questions about documentation, see [docs/MANDATES.md](./docs/MANDATES.md) or open an issue.**
