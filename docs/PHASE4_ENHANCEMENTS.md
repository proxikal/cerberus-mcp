# Phase 4: Planned Enhancements

**Status:** Planned for future implementation
**Dependencies:** Phase 3 complete ✅

---

## Immediate Enhancements (From Phase 3 Completion)

### 1. Watcher Auto-Start
**Priority:** High
**Effort:** Low (1-2 days)

**Description:**
Enable automatic watcher startup when running `cerberus index` command.

**Current Behavior:**
```bash
cerberus index ./project -o index.json
# Watcher must be started manually
cerberus watcher start
```

**Desired Behavior:**
```bash
cerberus index ./project -o index.json --watch
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

### 4. Large Project Optimization (10,000+ Files)
**Priority:** Medium
**Effort:** High (5-7 days)

**Description:**
Optimize indexing and search for very large projects (10,000+ files).

**Current Performance:**
- 1,000 files: ~5 minutes, ~1.2 GB RAM
- 5,000 files: ~25 minutes, ~6 GB RAM
- 10,000 files: ~50 minutes, ~12 GB RAM (projected)

**Optimization Targets:**
- 10,000 files: <30 minutes, <8 GB RAM
- Search: <10s for all query types
- Update: <5s for incremental updates

**Optimization Strategies:**

#### A. Parallel Parsing
- Use multiprocessing for file parsing
- Batch files into worker pools
- Aggregate results in main process

**Implementation:**
```python
from concurrent.futures import ProcessPoolExecutor

with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
    futures = [executor.submit(parse_file, f) for f in files]
    symbols = [f.result() for f in futures]
```

#### B. Streaming JSON Serialization
- Stream large indexes instead of loading entirely in memory
- Use `ijson` for incremental parsing
- Reduce memory footprint by 50%

#### C. Index Compression
- Compress index with gzip/lz4
- 23 MB → ~5 MB (5x reduction)
- Fast decompression (<100ms overhead)

#### D. Symbol Deduplication
- Deduplicate identical symbols across files
- Reduce index size by 20-30%
- Reference counting for shared symbols

#### E. Lazy Loading
- Load only required index sections
- On-demand symbol hydration
- Faster startup for targeted queries

**Testing:**
- Benchmark on open-source projects:
  - Django (~5,000 files)
  - TensorFlow (~15,000 files)
  - Linux kernel (~30,000 files)

**Benefits:**
- Support enterprise-scale codebases
- Better memory efficiency
- Faster indexing and search

---

## Phase 4: Integration Ecosystem (From Roadmap)

### 5. Official Agent Plugins
**Priority:** High
**Effort:** High (10-14 days)

**Description:**
Native tool-sets for popular AI agent frameworks.

**Frameworks:**
- **LangChain:** Custom tool wrapper for LangChain agents
- **CrewAI:** Cerberus tool integration for CrewAI
- **AutoGPT:** Plugin for AutoGPT ecosystem

**Implementation Example (LangChain):**
```python
from langchain.tools import BaseTool
from cerberus import hybrid_search, get_symbol

class CerberusSearchTool(BaseTool):
    name = "cerberus_search"
    description = "Search codebase for functions, classes, or concepts"

    def _run(self, query: str) -> str:
        results = hybrid_search(query, index_path="index.json")
        return format_results(results)

class CerberusGetSymbolTool(BaseTool):
    name = "cerberus_get_symbol"
    description = "Retrieve exact code for a specific symbol"

    def _run(self, symbol_name: str) -> str:
        code = get_symbol(symbol_name, index_path="index.json")
        return code
```

**Deliverables:**
- PyPI package: `cerberus-langchain`
- PyPI package: `cerberus-crewai`
- PyPI package: `cerberus-autogpt`
- Documentation for each integration
- Example notebooks/scripts

**Benefits:**
- Easy integration for agent developers
- Standardized API across frameworks
- Increased adoption

---

### 6. Web UI (Optional)
**Priority:** Low
**Effort:** High (10-14 days)

**Description:**
Lightweight local dashboard for visual exploration of project graph.

**Features:**
- Interactive code graph visualization
- Search interface with highlighting
- Dependency tree explorer
- Index statistics dashboard
- Real-time watcher status

**Tech Stack:**
- Backend: FastAPI (Python)
- Frontend: React + D3.js (visualization)
- Communication: WebSocket for real-time updates

**UI Mockup:**
```
┌────────────────────────────────────────────────┐
│ Cerberus Dashboard                    [Status] │
├────────────────────────────────────────────────┤
│  Search: [_________________________] 🔍        │
│                                                │
│  ┌─ Results ─────────────────────────────┐    │
│  │ 1. getAllergenById (function)         │    │
│  │    src/allergen-checker.ts:493        │    │
│  │ 2. getUniqueAllergens (function)      │    │
│  │    src/allergen-matcher.ts:167        │    │
│  └────────────────────────────────────────┘    │
│                                                │
│  ┌─ Call Graph ───────────────────────────┐   │
│  │      [getAllergenById]                 │   │
│  │       ├── checkAllergens               │   │
│  │       └── validateIngredients          │   │
│  └────────────────────────────────────────┘   │
│                                                │
│  ┌─ Statistics ───────────────────────────┐   │
│  │ Files: 428  Symbols: 1,199  Calls: 111K│   │
│  │ Watcher: ✅ Running  Last Update: 2s   │   │
│  └────────────────────────────────────────┘   │
└────────────────────────────────────────────────┘
```

**Commands:**
```bash
cerberus serve --index index.json --port 8080
# Opens browser to http://localhost:8080
```

**Benefits:**
- Visual exploration for humans
- Debug and validate index contents
- Marketing/demo tool

---

### 7. Security Scanning
**Priority:** Medium
**Effort:** Medium (5-7 days)

**Description:**
Automated PII and secret detection within the indexing pipeline.

**Features:**
- Detect hardcoded secrets (API keys, passwords)
- Identify PII (emails, SSNs, credit cards)
- Flag security anti-patterns
- Generate security report

**Detection Methods:**
- Regex patterns for common secrets
- Entropy analysis for random strings
- Integration with tools like `truffleHog`, `detect-secrets`

**Implementation:**
```python
# During indexing
from cerberus.security import scan_for_secrets

for symbol in symbols:
    secrets = scan_for_secrets(symbol.content)
    if secrets:
        symbol.metadata['security_warnings'] = secrets
```

**Output:**
```bash
cerberus scan-security --index index.json

⚠️  Security Scan Results:

  🔴 CRITICAL: API key detected
     File: src/config.py:42
     Pattern: AWS_SECRET_ACCESS_KEY = "AKIA..."

  🟡 WARNING: Possible PII
     File: src/user.py:128
     Pattern: email = "john.doe@example.com"

  Found 2 issues across 428 files.
```

**Benefits:**
- Prevent secret leaks
- Security compliance
- Automated security review

---

### 8. Multi-Language Support
**Priority:** Medium
**Effort:** High (per language)

**Description:**
Expand beyond Python/JS/TS to support more languages.

**Planned Languages:**
- **Go:** Use tree-sitter-go
- **Rust:** Use tree-sitter-rust
- **Java:** Use tree-sitter-java
- **C/C++:** Use tree-sitter-c/cpp
- **Ruby:** Use tree-sitter-ruby

**Implementation (per language):**
1. Add tree-sitter grammar
2. Create language-specific parser
3. Map AST nodes to Cerberus schemas
4. Add language-specific patterns (imports, calls)
5. Write comprehensive tests

**Example (Go):**
```python
# cerberus/parser/go_parser.py
from cerberus.parser.base import BaseParser

class GoParser(BaseParser):
    language = "go"

    def extract_functions(self, tree):
        query = """
        (function_declaration
          name: (identifier) @name
          parameters: (parameter_list) @params
          result: (_)? @return_type
        ) @function
        """
        return self._query(tree, query)
```

**Benefits:**
- Support polyglot codebases
- Wider adoption across ecosystems
- Comprehensive context for multi-language projects

---

## Implementation Priority

### High Priority (Do First)
1. ✅ Watcher Auto-Start
2. ✅ Official Agent Plugins (LangChain, CrewAI)

### Medium Priority (Do Next)
3. ✅ Embedding Model Caching
4. ✅ Path Normalization Improvements
5. ✅ Security Scanning

### Low Priority (Nice to Have)
6. ✅ Large Project Optimization (10K+ files)
7. ✅ Web UI
8. ✅ Multi-Language Support

---

## Estimated Timeline

**Phase 4 Sprint 1 (2 weeks):**
- Watcher auto-start
- Path normalization
- Model caching

**Phase 4 Sprint 2 (3 weeks):**
- LangChain plugin
- CrewAI plugin
- Documentation

**Phase 4 Sprint 3 (2 weeks):**
- Security scanning
- Large project optimization

**Phase 4 Sprint 4 (3 weeks - Optional):**
- Web UI
- Multi-language (1-2 languages)

**Total:** 8-10 weeks for full Phase 4

---

## Success Criteria

Phase 4 is complete when:
1. ✅ Watcher auto-starts on index command
2. ✅ Model loading <1s (cached)
3. ✅ Official plugins published to PyPI
4. ✅ Path normalization handles all edge cases
5. ✅ Security scanning detects common patterns
6. ✅ 10,000+ file projects supported
7. ✅ Documentation complete for all features

---

**Saved for Phase 4 Implementation**

**Date:** 2026-01-08
**Source:** Phase 3 Completion Analysis
