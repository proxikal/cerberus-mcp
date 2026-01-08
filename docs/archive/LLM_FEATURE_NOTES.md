# LLM Feature Classification - Important Notes

## Overview

Cerberus includes LLM-based summarization features, but these are **LOW PRIORITY** and marked as **FUTURE DEVELOPMENT**.

## Why LLM Features Are Low Priority

**Core Purpose of Cerberus:**
Cerberus is designed to provide context **TO** AI agents (Claude, Codex, etc.), not to use LLMs itself.

**The Contradiction:**
- Cerberus generates context for AI agents to consume
- AI agents receiving this context can perform their own analysis and summarization
- Having Cerberus use its own LLM to summarize contradicts the design principle: *"Code over Prompts: We don't rely on LLMs for the heavy lifting"* (from VISION.md)

## What Users Actually Need

### ✅ CORE FEATURES (High Priority)
1. **Skeletonization** - AST-based code pruning (deterministic, no LLM)
2. **Payload Synthesis** - Smart context assembly (deterministic, no LLM)

These are the features that matter for providing context to AI agents.

### ⚠️ OPTIONAL FEATURES (Low Priority)
3. **Summarization** - LLM-based code summaries (requires ollama)

This is implemented but most users will never need it.

## Implementation Status

The summarization module (`cerberus/summarization/`) is **fully implemented** but marked as low priority throughout the codebase.

### Modules Created
- `src/cerberus/summarization/facade.py`
- `src/cerberus/summarization/local_llm.py`
- `src/cerberus/summarization/config.py`
- `src/cerberus/summarization/__init__.py`

### CLI Command
- `cerberus summarize` - Marked as `[LOW PRIORITY - OPTIONAL]` in help text

## Documentation Updates

All documentation has been updated to clearly mark LLM features as low priority:

### Files Updated with Low Priority Warnings:
1. ✅ `docs/PHASE2_DESIGN.md` - Added warnings and notes
2. ✅ `PHASE2_QUICKSTART.md` - Marked ollama installation as optional/skip
3. ✅ `docs/PHASE2_SUMMARY.md` - Updated all summaries and success criteria
4. ✅ `docs/ROADMAP.md` - Marked Auto-Summarization as low priority
5. ✅ `src/cerberus/main.py` - Updated CLI help text

### Markers Used:
- ✅ **CORE FEATURE** - For skeletonization and payload synthesis
- ⚠️ **LOW PRIORITY - FUTURE DEVELOPMENT** - For summarization features
- ⚠️ **LOW PRIORITY - OPTIONAL** - For optional features
- ⚠️ **LOW PRIORITY - SKIP FOR MOST USERS** - For installation steps

## Recommendations

### For Most Users:
1. **Skip** ollama installation
2. **Skip** the summarization tests
3. **Focus on** skeletonization and payload synthesis
4. **Use** AI agents (Claude/Codex) to analyze the context Cerberus provides

### For Development:
1. Keep the summarization code as-is (it's implemented and tested)
2. Don't prioritize improvements to summarization
3. Focus on Phase 3 features (git-aware incrementalism, etc.)
4. Consider removing summarization in a future major version if unused

## Future Considerations

### Potential Alternatives to LLM Summarization:
1. **Context Validation** - Check if synthesized payloads are well-formed
2. **Quality Metrics** - Measure coverage, completeness, token efficiency
3. **Relevance Scoring** - Deterministic scoring of how relevant context is
4. **Coverage Analysis** - Show what percentage of dependencies are included

These would be more aligned with Cerberus's deterministic, code-based philosophy.

---

**Key Takeaway:** The summarization module exists and works, but it's not the focus. Cerberus's value is in providing structured, compact context to AI agents—not in being an AI agent itself.

**Date:** 2026-01-08
**Status:** Documentation updated, low priority clearly marked
