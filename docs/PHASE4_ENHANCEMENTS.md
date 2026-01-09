# Phase 4: Planned Enhancements

**Status:** Planned for future implementation
**Dependencies:** Phase 3 complete ✅

## Phase 4: Core Infrastructure & Ecosystem

### 1. Aegis-Scale Memory Optimization (High Priority)
**Priority:** High
**Effort:** High (7-10 days)

**Description:**
Exponentially shrink the memory footprint to support enterprise-scale projects (10,000+ files) on consumer hardware.

**Current Performance:**
- 428 files: 522 MB RAM
- 10,000 files: 12 GB RAM (Projected)

**Target Performance:**
- 10,000+ files: <250 MB RAM constant usage

**Optimization Strategies:**
- **Streaming Indexing:** Implement generator-based parsing that streams symbols directly to a disk-backed buffer instead of holding the entire project in a list.
- **SQLite Symbol Store:** Replace `json_store.py` with a disk-first architecture. Only load search metadata into RAM; "hydrate" full code content from disk only when a specific symbol is requested.
- **8-bit Embedding Quantization:** Integrate scalar quantization for vector embeddings, reducing the semantic search memory footprint by 4x with minimal integrity loss.
- **Memory-Mapped Indices (mmap):** Use memory-mapped files for search indices to allow zero-copy access shared between the Watcher daemon and the CLI.

**Benefits:**
- Support for massive codebases on low-resource machines.
- True "Invisible" operation (Ghost-in-the-machine footprint).
- Resilience against OOM crashes.

---

### 2. Watcher Auto-Start
**Priority:** High
**Effort:** Low (1-2 days)

**Description:**
Enable automatic watcher startup when running `cerberus index` command.

**Current Behavior:**
```bash
cerberus index ./project -o project.db
# Watcher must be started manually
cerberus watcher start
```

**Desired Behavior:**
```bash
cerberus index ./project -o project.db --watch
# Watcher auto-starts in background
```

**Implementation:**
- Add `--watch / --no-watch` flag to `index` command
- Default: `--watch` enabled
- Check if watcher already running before starting
- Graceful handling if watcher fails to start

**Benefits:**
- Invisible operation (aligns with Phase 3 philosophy)
- Users don't need to remember separate command
- Better developer experience

---

### 2. Path Normalization Improvements
**Priority:** Medium
**Effort:** Low (1-2 days)

**Description:**
Improve handling of edge cases in git diff path normalization.

**Current Issues:**
- Git diff returns relative paths: `src/file.py`
- Scanner stores absolute paths: `/Users/user/project/src/file.py`
- Edge cases with symbolic links and nested repos

**Improvements:**
- Robust path resolution algorithm
- Handle symbolic links correctly
- Support nested git repositories
- Better error messages when paths don't match

**Implementation:**
- Enhance `change_analyzer.py:identify_affected_symbols()`
- Add path canonicalization utilities
- Comprehensive path handling tests

**Benefits:**
- Fewer false negatives in incremental updates
- Better support for complex project structures
- More reliable git integration

---

### 3. Embedding Model Caching
**Priority:** Medium
**Effort:** Medium (2-3 days)

**Description:**
Persist loaded embedding model to disk to eliminate 4-second cold-start delay.

**Current Behavior:**
- First search: 7.62s (4s model loading + 3.62s search)
- Subsequent searches: 3.62s (model cached in memory)
- Model evicted when process ends

**Desired Behavior:**
- First search: 3.62s (model loaded from disk cache)
- Subsequent searches: 3.62s (same speed)
- Model cache persists across sessions

**Implementation:**
- Cache model files in `~/.cerberus/models/`
- Use `transformers` model caching API
- Add `--clear-cache` flag to clear model cache
- Verify model integrity on load

**Cache Location:**
```
~/.cerberus/
├── models/
│   └── all-MiniLM-L6-v2/
│       ├── config.json
│       ├── pytorch_model.bin
│       └── tokenizer.json
└── cache_manifest.json
```

**Benefits:**
- Eliminate 4-second cold-start delay
- Better user experience for first search
- Consistent search performance

---

## Implementation Priority

### High Priority (Do First)
1. ✅ Aegis-Scale Memory Optimization (Streaming + SQLite Store)
2. ✅ Watcher Auto-Start
3. ✅ Official Agent Plugins (LangChain, CrewAI)

### Medium Priority (Do Next)
4. ✅ Embedding Model Caching & Quantization
5. ✅ Path Normalization Improvements
6. ✅ Security Scanning

### Low Priority (Nice to Have)
7. ✅ Web UI
8. ✅ Multi-Language Support (Rust, Go, Java)

---

## Estimated Timeline

**Phase 4 Sprint 1 (2 weeks):**
- Aegis-Scale Memory Optimization (SQLite Store)
- Watcher auto-start

**Phase 4 Sprint 2 (3 weeks):**
- LangChain / CrewAI plugins
- Documentation

**Phase 4 Sprint 3 (2 weeks):**
- Security scanning
- Path normalization

**Phase 4 Sprint 4 (3 weeks - Optional):**
- Web UI
- Multi-language support

**Total:** 10 weeks for full Phase 4

---

## Success Criteria

Phase 4 is complete when:
1. ✅ Constant RAM usage <250MB for 10,000+ files
2. ✅ Watcher auto-starts on index command
3. ✅ Official plugins published to PyPI
4. ✅ Path normalization handles all edge cases
5. ✅ Security scanning detects common patterns
6. ✅ Documentation complete for all features

---

**Saved for Phase 4 Implementation**

**Date:** 2026-01-08
**Source:** Phase 3 Completion Analysis
