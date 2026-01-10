# Phase 13 Specification: The Predictive Blueprint (Architectural Intelligence)

**Status:** Proposed (To Follow Phase 12.5)
**Goal:** Transform the basic `blueprint` command from a simple "Symbol List" into a high-fidelity **Architectural Intelligence System**. By layering Dependency Data, Complexity Metrics, Git Churn, Test Coverage, and Stability Analysis onto a **Token-Efficient Visual Structure**, we enable Agents to understand *how* code works, *why* it exists, and *what risks exist* without reading the implementation.

---

## 🎯 Core Objectives

### 1. Visual Hierarchy (The Semantic Tree)
**Mission:** Provide an instant "Mental Model" using the most token-efficient format possible.

**Why Visuals for AI?** LLMs process indentation-based hierarchy (Trees) more efficiently than deeply nested JSON syntax (brackets/quotes).

**Mandate:** **Strict Visuals Only.**
- ✅ **Allowed:** Indentation, Tree characters (`├──`, `└──`).
- ❌ **Forbidden:** Decorative boxes, colors, ambiguous ASCII art (arrows pointing across lines).

**Core Command:**
```bash
cerberus blueprint <file_or_package> [OPTIONS]
```

**Basic Output Standard:**
```text
[File: src/auth_manager.py]
├── [Class: AuthConfig] (Lines 10-45)
│   ├── __init__(env_prefix: str)
│   └── load_from_env() -> AuthConfig
└── [Class: SessionManager] (Lines 48-200)
    ├── create_session(user: User) -> str
    └── validate_token(token: str) -> bool
```

**Benefit:** 30-50% token reduction vs JSON.

**Agent Usage Pattern:**
```bash
# BEFORE: Agent reads full file (wasteful)
Read src/auth_manager.py  # 2000 tokens

# AFTER: Agent gets architectural map (efficient)
cerberus blueprint src/auth_manager.py  # 800 tokens
# Then only reads specific symbols if needed
cerberus retrieval get-symbol SessionManager.create_session  # 200 tokens
```

---

### 2. Dependency Overlay (`--deps`) (Hybrid Strategy)
**Mission:** Explain *what* a function does using **Inline Annotations**.

**Strategy:** Do not draw complex arrows. Use structured inline tags.

**Output:**
```text
└── process_payment(order: Order) -> PaymentResult
    [Calls: stripe.charge, email.send, DB.update]
    [Raises: PaymentFailed, InsufficientFunds]
```

**With Confidence Scores (Phase 5 Integration):**
```text
└── process_payment(order: Order) -> PaymentResult
    [Calls: stripe.charge ✓1.0, email.send ✓0.9, log_event ✓0.6]
    [Raises: PaymentFailed]
```
- `✓1.0` = Import trace (certain)
- `✓0.9` = Type annotation (high confidence)
- `✓0.6` = Heuristic inference (verify manually)

**Benefit:** **Zero-Token Logic Inspection.** The Agent knows the side effects without spending tokens on the body.

**Agent Usage Pattern:**
```bash
# Get high-level architecture with dependencies
cerberus blueprint src/payment.py --deps

# Agent sees:
# └── process_payment() [Calls: stripe.charge ✓1.0, DB.save ✓1.0]
# Decision: High confidence, can trust these dependencies
# Agent proceeds without reading stripe/DB internals

# Low confidence example:
# └── legacy_handler() [Calls: unknown_func ✓0.4]
# Decision: Low confidence, read the implementation to verify
cerberus retrieval get-symbol legacy_handler
```

---

### 3. Complexity & Size Metrics (`--meta`)
**Mission:** Warning signs for "Dragons" (high-risk code areas).

**Feature:** Annotate symbols with metadata.

**Output:**
```text
└── complex_algo()
    [Lines: 150]
    [Complexity: High]
    [Branches: 23]
    [Nesting: 6]
```

**Complexity Calculation:**
- **Low:** < 10 cyclomatic complexity, < 50 lines
- **Medium:** 10-20 complexity, 50-150 lines
- **High:** > 20 complexity or > 150 lines

**Benefit:** Signals the Agent to "Read carefully" or "Refactor this" before touching it.

**Agent Usage Pattern:**
```bash
cerberus blueprint src/legacy.py --meta

# Agent sees:
# └── parse_config() [Lines: 320] [Complexity: High] [Nesting: 8]
# Decision: This is a dragon. Add tests before refactoring.
# Agent creates test plan first, then refactors carefully
```

---

### 4. Git Churn Intelligence (`--churn`)
**Mission:** Contextual awareness of recent activity and edit frequency.

**Feature:** Mark symbols modified in the last N commits with frequency analysis.

**Output:**
```text
└── new_feature()
    [Modified: 2h ago]
    [Edits: 5 this week]
    [Authors: 2]
    [Last: @alice]
```

**Churn Calculation:**
```python
# Per symbol tracking via git blame
churn_score = {
    'last_modified': '2h ago',           # Most recent edit
    'edit_frequency': 5,                  # Edits in last 7 days
    'unique_authors': 2,                  # Different contributors
    'last_author': '@alice'               # Most recent editor
}
```

**Benefit:**
- Helps Agent identify "Active Work Zone" (potential merge conflicts)
- Highlights unstable code (frequent changes = high risk)
- Shows ownership (who to ask about this code)

**Agent Usage Pattern:**
```bash
cerberus blueprint src/api.py --churn

# Agent sees:
# └── handle_request() [Modified: 30min ago] [Edits: 12 this week] [Authors: 3]
# Decision: High churn = unstable. Check recent commits before editing.
git log -5 --oneline src/api.py  # See what's changing
# Agent waits or coordinates with team before editing

# Stable code example:
# └── get_version() [Modified: 6mo ago] [Edits: 0 this year]
# Decision: Stable, safe to edit
```

---

### 5. Test Coverage Overlay (`--coverage`)
**Mission:** Show which symbols have tests to guide safe refactoring.

**Feature:** Integrate with pytest/coverage.py to show test status.

**Output:**
```text
└── process_payment(order: Order) -> PaymentResult
    [Coverage: 87% ✓]
    [Tests: test_payment.py::test_success, test_payment.py::test_failure]
    [Assertions: 12]

└── legacy_helper()
    [Coverage: 0% ⚠️]
    [Tests: none]
```

**Integration:**
```bash
# Requires coverage data file (.coverage)
pytest --cov=src --cov-report=json
cerberus blueprint src/payment.py --coverage
```

**Benefit:**
- Untested code is risky to refactor
- Agents prioritize adding tests before modifying low-coverage symbols

**Agent Usage Pattern:**
```bash
cerberus blueprint src/auth.py --coverage

# Agent sees:
# └── validate_token() [Coverage: 0% ⚠️] [Tests: none]
# Decision: No tests = high risk. Write tests first.
# Agent creates test file before refactoring

# Well-tested code:
# └── hash_password() [Coverage: 100% ✓] [Tests: 8 passing]
# Decision: Safe to refactor, tests will catch regressions
```

---

### 6. Symbol Stability Score (`--stability`)
**Mission:** Single metric combining coverage, complexity, churn, and dependencies to guide edit decisions.

**Formula:**
```python
stability = (
    (coverage * 0.4) +              # Well-tested = safer (40% weight)
    ((1 - complexity) * 0.3) +      # Simpler = safer (30% weight)
    ((1 - churn_rate) * 0.2) +      # Stable = safer (20% weight)
    ((1 - dep_count/10) * 0.1)      # Fewer deps = safer (10% weight)
)

# Normalization:
# coverage: 0.0-1.0 (0% to 100%)
# complexity: 0.0-1.0 (Low=0.2, Medium=0.5, High=0.9)
# churn_rate: 0.0-1.0 (0 edits=0, >10 edits/week=1.0)
# dep_count: normalized by /10 (0 deps=0, 10+ deps=1.0)
```

**Output:**
```text
└── process_payment()
    [Complexity: High] [Churn: 5/week] [Coverage: 90%] [Deps: 8]
    [Stability: 🟡 MEDIUM RISK (0.62)]

└── get_user_email()
    [Complexity: Low] [Churn: 0/year] [Coverage: 100%] [Deps: 1]
    [Stability: 🟢 SAFE (0.94)]

└── legacy_parser()
    [Complexity: High] [Churn: 12/week] [Coverage: 15%] [Deps: 15]
    [Stability: 🔴 HIGH RISK (0.23)]
```

**Risk Thresholds:**
- 🟢 **SAFE:** > 0.75 (well-tested, simple, stable)
- 🟡 **MEDIUM RISK:** 0.50-0.75 (acceptable with caution)
- 🔴 **HIGH RISK:** < 0.50 (needs attention before editing)

**Benefit:** Single metric guides agent decisions without reading full metadata.

**Agent Usage Pattern:**
```bash
cerberus blueprint src/core.py --stability

# Agent sees:
# └── critical_function() [Stability: 🔴 HIGH RISK (0.31)]
# Decision: Do NOT edit without comprehensive testing plan
# Agent creates: integration tests, rollback plan, gradual rollout

# Safe symbol:
# └── format_date() [Stability: 🟢 SAFE (0.89)]
# Decision: Edit freely, well-protected by tests
```

---

### 7. Structural Diff Mode (`--diff`)
**Mission:** Show architectural changes between commits, not just timestamps.

**Feature:** Compare blueprint structure across git refs.

**Command:**
```bash
cerberus blueprint src/auth.py --diff HEAD~1
cerberus blueprint src/auth.py --diff main...feature-branch
cerberus blueprint src/auth.py --diff v1.0.0..HEAD
```

**Output:**
```text
[File: src/auth.py] (Diff: HEAD~1..HEAD)
├── [Class: SessionManager]
│   ├── create_session() [Modified: signature changed]
│   │   Before: create_session(user: str) -> str
│   │   After:  create_session(user: User) -> SessionToken
│   ├── + validate_token() [NEW: added 2h ago]
│   │   [Coverage: 85% ✓] [Tests: test_auth.py::test_validate]
│   └── - legacy_auth() [REMOVED: 1 commit ago]
└── + [Class: TokenRefresher] [NEW: entire class added]
    └── refresh(token: str) -> str
```

**Change Types:**
- `+` = Added (new symbol)
- `-` = Removed (deleted symbol)
- `Modified` = Changed (signature, body, or metadata)
- `Moved` = Relocated (different file/class)

**Benefit:** Eliminates "read old version to compare" token waste.

**Agent Usage Pattern:**
```bash
# Before merging feature branch
cerberus blueprint src/ --diff main...feature-branch --aggregate

# Agent sees all structural changes:
# + Added: 5 new classes, 23 new methods
# - Removed: 2 deprecated functions
# Modified: 8 signature changes
# Decision: Review signature changes for breaking API compatibility
```

---

### 8. Smart "Auto-Hydration" (`--hydrate`)
**Mission:** Pre-emptive context loading for dependencies.

**Logic:** If `cerberus blueprint src/main.py` reveals that `main.py` heavily depends on `src/utils.py`, automatically append a *minified* summary of `src/utils.py` to the output.

**Hydration Strategy:**
```python
# Auto-hydrate if:
# 1. Symbol has >3 calls to same external file
# 2. External file is internal (not stdlib/third-party)
# 3. Total hydrated size < 2000 tokens

# Example: main.py calls utils.py 5 times
# → Append mini-blueprint of utils.py automatically
```

**Output:**
```text
[File: src/main.py]
└── process_data()
    [Calls: utils.validate ✓1.0, utils.transform ✓1.0, utils.save ✓1.0]

[Auto-Hydrated: src/utils.py] (Referenced 5x above)
├── validate(data: Dict) -> bool
├── transform(data: Dict) -> ProcessedData
└── save(data: ProcessedData) -> None
```

**Benefit:** Eliminates the "Read A → See Import B → Read B" exploration loop.

**Agent Usage Pattern:**
```bash
cerberus blueprint src/main.py --hydrate

# Agent sees main.py + auto-included utils.py
# No need for follow-up reads
# Immediate understanding of full execution context
```

---

### 9. Cross-File Aggregation (`--aggregate`)
**Mission:** Architectural view across multiple files (package-level blueprint).

**Command:**
```bash
cerberus blueprint src/auth/ --aggregate
cerberus blueprint src/ --aggregate --max-depth 2
```

**Output:**
```text
[Package: src/auth/] (3 files, 8 classes, 42 functions)
├── [File: manager.py]
│   └── [Class: SessionManager]
│       ├── create_session() [Depends: config.AuthConfig ✓1.0]
│       └── validate_token() [Depends: db.TokenStore ✓0.9]
├── [File: config.py]
│   └── [Class: AuthConfig] [Used by: 3 files ⭐]
│       ├── load_from_env()
│       └── validate_config()
└── [File: tokens.py]
    ├── [Class: TokenStore] [Used by: 2 files]
    └── [Function: generate_token]
        [Calls: secrets.token_urlsafe 📦external]
```

**Annotations:**
- `⭐` = Hot symbol (used by many files)
- `📦external` = Third-party dependency
- `🏠internal` = Internal cross-file dependency

**Benefit:** Understand architecture without reading every file.

**Agent Usage Pattern:**
```bash
# Understanding new codebase
cerberus blueprint src/ --aggregate --depth 1

# Agent sees:
# - Package structure
# - Key classes and their relationships
# - Cross-file dependencies
# Decision: Now knows where to dive deeper
```

---

### 10. Performance Optimization (`--fast`, `--cached`)
**Mission:** Handle large files efficiently without sacrificing quality.

**Workaround for Performance Degradation:**

**Fast Mode (Skip Expensive Analysis):**
```bash
cerberus blueprint main.py --fast
# Output: Structure only (no deps/churn/complexity)
# Use case: Quick orientation, speed over detail
```

**Cached Mode (Reuse Recent Blueprints):**
```bash
cerberus blueprint main.py --cached
# Uses cached version if file unchanged and cache <5min old
# Watcher auto-invalidates cache on file changes
```

**Implementation:**
```python
# Cache key: file_path + mtime + flags
cache_key = f"{file_path}:{mtime}:{flags_hash}"

# Cache storage: SQLite table
CREATE TABLE blueprint_cache (
    cache_key TEXT PRIMARY KEY,
    blueprint_json TEXT,
    created_at TIMESTAMP,
    expires_at TIMESTAMP
);

# Watcher integration:
# On file change: DELETE FROM blueprint_cache WHERE cache_key LIKE 'file_path:%'
```

**Benefit:** Maintains speed even for large files with expensive analysis.

**Agent Usage Pattern:**
```bash
# First time (slow but comprehensive)
cerberus blueprint src/large_file.py --deps --coverage --stability

# Subsequent calls (fast, uses cache)
cerberus blueprint src/large_file.py --cached

# Force refresh
cerberus blueprint src/large_file.py --no-cache
```

---

### 11. Width Management (`--max-depth`, `--collapse-private`)
**Mission:** Handle deeply nested code without terminal width overflow.

**Workaround for Width Explosion:**

**Depth Limiting:**
```bash
cerberus blueprint src/nested.py --max-depth 3
```

**Output:**
```text
[File: src/nested.py]
├── [Class: Outer]
│   ├── [Class: Middle]
│   │   ├── [Class: Inner]
│   │   │   └── ... (2 more levels, use --max-depth 5 to see)
```

**Private Symbol Collapse:**
```bash
cerberus blueprint src/module.py --collapse-private
```

**Output:**
```text
[File: src/module.py]
├── [Class: PublicAPI]
│   ├── public_method()
│   └── [Private: 8 methods collapsed]
```

**Smart Truncation for Wide Lines:**
```text
# Before (overflows):
├── very_long_function_name() [Calls: A, B, C, D, E, F, G, H, I, J, K, L]

# After (truncated):
├── very_long_function_name() [Calls: 12 functions (use --verbose)]
```

**Benefit:** Preserves token efficiency by preventing visual bloat.

---

### 12. Cycle Detection (`--cycles`)
**Mission:** Highlight circular dependencies (import cycles, recursive calls).

**Feature:** Mark symbols involved in circular relationships.

**Output:**
```text
[File: src/module_a.py]
└── [Class: ClassA] [CYCLE WARNING: A→B→C→A ⚠️]
    └── call_b()
        [Calls: module_b.ClassB.call_c ✓1.0]
        [Cycle: This creates circular dependency]

[File: src/module_b.py]
└── [Class: ClassB] [CYCLE WARNING: B→C→A→B ⚠️]
    └── call_c() [Calls: module_c.ClassC.call_a ✓1.0]
```

**Detection Strategy:**
```python
# Build call graph
# Detect cycles using DFS
# Annotate symbols in cycle paths

# Types of cycles:
# 1. Import cycles (file level)
# 2. Call cycles (function level)
# 3. Inheritance cycles (class level)
```

**Benefit:** Prevents agents from making cycles worse.

**Agent Usage Pattern:**
```bash
cerberus blueprint src/ --aggregate --cycles

# Agent sees:
# └── ClassA [CYCLE: A→B→A ⚠️]
# Decision: Do NOT add more dependencies to ClassA
# Refactor to break cycle first
```

---

### 13. Incremental Blueprint Updates (Watcher Integration)
**Mission:** Keep blueprints synchronized with code changes automatically.

**Strategy:**
1. Watcher detects file change (Phase 3)
2. Invalidates cached blueprint for that file
3. Next `cerberus blueprint` call regenerates only changed files
4. Background regeneration for frequently-accessed blueprints

**Health Monitoring:**
```bash
cerberus watcher health --blueprints

# Output:
{
  "status": "healthy",
  "cached_blueprints": 47,
  "stale_blueprints": 3,
  "stale_files": ["main.py", "config.py", "utils.py"],
  "cache_hit_rate": 0.89,
  "avg_regeneration_time_ms": 45
}
```

**Auto-Regeneration (Background):**
```bash
# Enable background blueprint regeneration
cerberus watcher start --auto-blueprint

# When file changes:
# 1. Watcher invalidates cache
# 2. Watcher regenerates blueprint in background
# 3. Next access gets fresh blueprint instantly
```

**Benefit:** Agents always see current architecture without manual refresh.

---

### 14. Machine-Readable Export (`--format json`)
**Mission:** Enable programmatic consumption and composition.

**Command:**
```bash
cerberus blueprint src/main.py --format json
cerberus blueprint src/main.py --format json --deps --stability
```

**Output:**
```json
{
  "file": "src/main.py",
  "symbols": [
    {
      "type": "class",
      "name": "SessionManager",
      "lines": [48, 200],
      "methods": [
        {
          "name": "create_session",
          "signature": "create_session(user: User) -> str",
          "dependencies": [
            {"target": "DB.save", "confidence": 1.0},
            {"target": "uuid.uuid4", "confidence": 1.0}
          ],
          "complexity": {"score": 12, "level": "medium"},
          "coverage": {"percent": 87, "tests": ["test_auth.py::test_create"]},
          "stability": {"score": 0.78, "level": "safe"},
          "churn": {"edits_7d": 2, "last_modified": "2h ago"}
        }
      ]
    }
  ]
}
```

**Benefit:** Agents can parse structured data more reliably + composability with `jq`, etc.

**Agent Usage Pattern:**
```bash
# Extract all high-risk functions
cerberus blueprint src/ --format json --stability | \
  jq '.symbols[].methods[] | select(.stability.level == "high_risk")'

# Find untested code
cerberus blueprint src/ --format json --coverage | \
  jq '.symbols[].methods[] | select(.coverage.percent < 50)'
```

---

### 15. External Dependency Marking
**Mission:** Distinguish between internal code (editable) and external libraries (read-only).

**Feature:** Mark calls to third-party packages vs internal modules.

**Output:**
```text
└── process_payment(order: Order) -> PaymentResult
    [Calls: stripe.charge 📦external, DB.save 🏠internal, log 📦stdlib]
    [Editable: DB.save only]
```

**Markers:**
- `📦external` = Third-party package (PyPI, npm)
- `🏠internal` = Project code (src/)
- `📦stdlib` = Standard library (safe, read-only)

**Detection:**
```python
# Check import source:
# - In src/ or project root → internal
# - In site-packages/ → external
# - In stdlib path → stdlib
```

**Benefit:** Prevents agents from trying to edit third-party code.

---

## 📋 Command Reference

### Basic Usage
```bash
# Simple structure
cerberus blueprint <file>

# Structure with dependencies
cerberus blueprint <file> --deps

# Full analysis (all overlays)
cerberus blueprint <file> --deps --meta --churn --coverage --stability

# Package-level view
cerberus blueprint <directory> --aggregate
```

### Flag Combinations
```bash
# Safe refactoring guide
cerberus blueprint src/ --stability --coverage --aggregate

# Recent changes analysis
cerberus blueprint src/ --churn --diff HEAD~5

# Performance-optimized
cerberus blueprint src/large_file.py --fast --cached

# JSON export for tooling
cerberus blueprint src/ --format json --stability | jq '.symbols[]'
```

### Common Agent Workflows

**Workflow 1: Understanding New Codebase**
```bash
# Step 1: Get high-level structure
cerberus blueprint src/ --aggregate --max-depth 2

# Step 2: Identify key modules (high usage)
cerberus blueprint src/ --aggregate --format json | jq '.symbols[] | select(.used_by_count > 5)'

# Step 3: Drill into specific module
cerberus blueprint src/core/auth.py --deps --coverage
```

**Workflow 2: Safe Refactoring**
```bash
# Step 1: Check stability
cerberus blueprint src/target.py --stability --coverage

# Step 2: If high risk, review tests
cerberus retrieval search "test_target" --type test

# Step 3: Check recent changes (avoid conflicts)
cerberus blueprint src/target.py --churn --diff HEAD~10

# Step 4: Proceed with refactor (if safe)
```

**Workflow 3: Debugging Production Issue**
```bash
# Step 1: Find recently changed code
cerberus blueprint src/ --churn --aggregate | grep "Modified: [0-9]h ago"

# Step 2: Check dependencies of changed code
cerberus blueprint src/changed_file.py --deps --hydrate

# Step 3: Review stability of hot path
cerberus blueprint src/changed_file.py --stability --cycles
```

**Workflow 4: Code Review Preparation**
```bash
# Step 1: See all structural changes
cerberus blueprint src/ --diff main...feature-branch --aggregate

# Step 2: Identify risky changes
cerberus blueprint src/ --diff main...feature-branch --stability

# Step 3: Check test coverage of changes
cerberus blueprint src/ --diff main...feature-branch --coverage
```

---

## 🏗 Implementation Strategy

### Phase 13.1: Foundation (Week 1-2)
**Goal:** Core blueprint infrastructure with basic overlays.

**Tasks:**
- [ ] Implement ASCII tree generator with token optimization
- [ ] Add `--deps` flag with confidence scores (integrate Phase 5)
- [ ] Add `--meta` flag with complexity calculation
- [ ] Basic caching system (file mtime-based)
- [ ] Unit tests for tree rendering

**Deliverables:**
```bash
cerberus blueprint <file>
cerberus blueprint <file> --deps
cerberus blueprint <file> --meta
```

---

### Phase 13.2: Intelligence Layer (Week 3)
**Goal:** Git integration and stability scoring.

**Tasks:**
- [ ] Implement `--churn` flag (git blame integration)
- [ ] Implement `--coverage` flag (pytest/coverage.py integration)
- [ ] Implement `--stability` with composite scoring algorithm
- [ ] Add `--diff` mode for structural comparisons
- [ ] Performance testing for large files (>1000 symbols)

**Deliverables:**
```bash
cerberus blueprint <file> --churn
cerberus blueprint <file> --coverage
cerberus blueprint <file> --stability
cerberus blueprint <file> --diff HEAD~1
```

---

### Phase 13.3: Advanced Features (Week 4)
**Goal:** Auto-hydration, aggregation, and optimization.

**Tasks:**
- [ ] Implement `--hydrate` with smart dependency inclusion
- [ ] Implement `--aggregate` for package-level views
- [ ] Add `--cycles` detection (call graph analysis)
- [ ] Add `--fast` and `--cached` performance modes
- [ ] Add `--max-depth` and `--collapse-private` width management

**Deliverables:**
```bash
cerberus blueprint <file> --hydrate
cerberus blueprint <dir> --aggregate
cerberus blueprint <file> --cycles
cerberus blueprint <file> --fast --cached
```

---

### Phase 13.4: Watcher Integration (Week 5)
**Goal:** Automatic cache invalidation and background regeneration.

**Tasks:**
- [ ] Integrate blueprint cache with watcher daemon
- [ ] Implement auto-invalidation on file changes
- [ ] Add `cerberus watcher health --blueprints` monitoring
- [ ] Background blueprint regeneration for hot files
- [ ] Cache hit rate metrics

**Deliverables:**
```bash
cerberus watcher start --auto-blueprint
cerberus watcher health --blueprints
# Blueprints auto-refresh on file changes
```

---

### Phase 13.5: Export & Polish (Week 6)
**Goal:** JSON export, external dependency marking, final optimizations.

**Tasks:**
- [ ] Implement `--format json` with full schema
- [ ] Add external dependency detection (📦external, 🏠internal)
- [ ] Width management and smart truncation
- [ ] Comprehensive test suite (50+ test cases)
- [ ] Performance benchmarks (target: <200ms for 1000 symbols)
- [ ] Documentation and agent usage examples

**Deliverables:**
```bash
cerberus blueprint <file> --format json
cerberus blueprint <file> --deps  # Shows 📦external vs 🏠internal
# All edge cases handled
# Production-ready performance
```

---

## 📉 Success Metrics

### Token Efficiency
- **Target:** Blueprint output < 60% of raw source token cost
- **Measurement:** Compare tokens for `blueprint` vs `Read` on 100 files
- **Success Criteria:**
  - Simple blueprint: 40-50% of raw source
  - Full analysis (`--deps --stability`): 50-60% of raw source
  - Auto-hydration: Still < 70% of reading all dependencies manually

### Parsing Accuracy
- **Target:** LLMs extract dependencies with > 98% accuracy
- **Measurement:** GPT-4 extracts dependency lists from blueprint, compare to ground truth
- **Success Criteria:** <2% hallucination rate on relationships

### Performance
- **Target:** < 200ms for files with < 1000 symbols
- **Target:** < 500ms for files with > 1000 symbols
- **Target:** Cache hit rate > 85% in typical workflows
- **Measurement:** Benchmark on TensorFlow codebase (68k symbols)

### Stability Score Accuracy
- **Target:** Stability score correlates with actual bug density
- **Measurement:** Historical analysis - do "high risk" symbols have more bugs?
- **Success Criteria:**
  - High risk symbols have 3x more bugs than safe symbols
  - Medium risk symbols have 1.5x more bugs than safe symbols

### Agent Adoption
- **Target:** 80% of agent file reads replaced by blueprint calls
- **Measurement:** Track tool usage in dogfooding sessions
- **Success Criteria:** Agents prefer blueprint over Read for code exploration

---

## 🔗 Connection to Mission

### Core Mandate Alignment

| Mandate | Phase 13 Implementation | Status |
|---------|------------------------|--------|
| **Code > Prompts** | AST-based complexity, git-based churn (deterministic) | ✅ STRICT |
| **Verified Transactions** | Read-only (no mutations), verified metrics | ✅ STRICT |
| **Strict Resolution** | Confidence scores show uncertainty, no hallucination | ✅ STRICT |
| **Symbiosis** | Visual trees match LLM cognition, token-optimized | ✅ STRICT |

### 100% Signal / 0% Noise

**Signal (What Agents Get):**
- Architecture (structure)
- Dependencies (what it calls)
- Stability (safe to edit?)
- Coverage (protected by tests?)
- Churn (recently changed?)
- Complexity (hard to understand?)
- All data: Deterministic, verifiable, no LLM guesswork

**Noise Eliminated:**
- No decorative formatting
- No ambiguous visualizations
- No unverified speculation
- No token waste on implementation details (until needed)

### Symbiosis Benefits

**Before Phase 13 (Flashlight Approach):**
```
Agent: I need to understand auth.py
Tool: Read 500 lines (2000 tokens)
Agent: What does this function call?
Tool: Grep for function calls (500 tokens)
Agent: Is this code stable?
Tool: Git log + complexity analysis (800 tokens)
Agent: Does it have tests?
Tool: Find test files (400 tokens)
Total: 3700 tokens, 4 tool calls, linear exploration
```

**After Phase 13 (Map Approach):**
```
Agent: I need to understand auth.py
Tool: Blueprint with --deps --stability --coverage (800 tokens)
Agent: (Now knows: structure, dependencies, stability, test status)
Agent: Focus on high-risk untested function
Tool: Get-symbol for that one function (200 tokens)
Total: 1000 tokens, 2 tool calls, targeted exploration
```

**Result:** 73% token reduction, 50% fewer tool calls, complete context.

---

## 🚧 Risks & Mitigations

### Risk 1: Index Bloat
**Problem:** Storing blueprints, coverage data, git churn increases database size.

**Mitigation:**
- Separate cache table with TTL (auto-expire after 1 hour)
- Lazy computation (only calculate on request, not during indexing)
- Compression for large blueprints (gzip JSON)

**Target:** < 10% increase in database size.

---

### Risk 2: Git Operation Slowness
**Problem:** Running `git blame` on large files is slow (>1s per file).

**Mitigation:**
- Cache git blame results (invalidate on commits)
- Batch git operations (process multiple files in one command)
- Optional flag: `--skip-churn` for fast mode
- Background pre-computation via watcher

**Target:** < 50ms overhead for churn analysis via caching.

---

### Risk 3: Coverage Integration Complexity
**Problem:** Different test frameworks (pytest, unittest, nose) have different formats.

**Mitigation:**
- Phase 1: Support pytest + coverage.py only (80% of Python projects)
- Phase 2: Add unittest support
- Graceful degradation: If no coverage data, show "[Coverage: Unknown]"

**Target:** Works for 80% of projects out of the box.

---

### Risk 4: False Confidence Scores
**Problem:** Phase 5 confidence scores might be inaccurate, misleading agents.

**Mitigation:**
- Conservative scoring (prefer "unknown" over wrong answer)
- Manual verification mode: `--verify-deps` runs AST analysis to confirm
- Feedback loop: Track when agents find wrong dependencies, tune algorithm

**Target:** < 5% false positive rate on confidence scores.

---

### Risk 5: Overwhelming Output
**Problem:** Full analysis (`--deps --meta --churn --coverage --stability --cycles`) is too much info.

**Mitigation:**
- Sane defaults: `cerberus blueprint` shows structure only
- Progressive disclosure: Agents request specific overlays
- Presets: `--refactor-safe` (stability + coverage), `--debug` (churn + deps)
- Smart filtering: Auto-hide low-value data

**Target:** Default output < 1000 tokens for typical files.

---

## 🎓 Agent Training Examples

### Example 1: Finding Safe Refactoring Targets
```bash
# Agent wants to refactor payment processing

# Step 1: Get stability overview
cerberus blueprint src/payment.py --stability --coverage

# Output shows:
# └── process_payment() [Stability: 🔴 HIGH RISK (0.31)] [Coverage: 45%]
# └── validate_order() [Stability: 🟢 SAFE (0.89)] [Coverage: 98%]

# Agent decision: Refactor validate_order (safe), fix process_payment tests first
```

---

### Example 2: Investigating Production Bug
```bash
# Production error in checkout flow

# Step 1: Find recently changed code
cerberus blueprint src/checkout/ --churn --aggregate

# Output shows:
# └── calculate_total() [Modified: 3h ago] [Edits: 8 this week] [Authors: 2]

# Step 2: See what it depends on
cerberus blueprint src/checkout/pricing.py --deps --hydrate

# Output shows:
# └── calculate_total() [Calls: get_discount ✓0.6, apply_tax ✓0.9]
# [Auto-Hydrated: discount.py]
#   └── get_discount() [Modified: 3h ago] [Coverage: 0% ⚠️]

# Agent decision: Bug likely in get_discount (recent change, no tests)
```

---

### Example 3: Pre-Merge Code Review
```bash
# Reviewing feature branch before merge

# Step 1: See architectural changes
cerberus blueprint src/ --diff main...feature/new-auth --aggregate

# Output shows:
# + Added: AuthV2 class (120 lines)
# Modified: login() signature changed
# - Removed: legacy_auth()

# Step 2: Check stability of changes
cerberus blueprint src/auth.py --diff main...feature/new-auth --stability

# Output shows:
# + AuthV2 [Stability: 🟡 MEDIUM (0.67)] [Coverage: 78%] [Complexity: High]

# Agent decision: Request more tests for AuthV2 before merging
```

---

## 🔮 Future Enhancements (Post-Phase 13)

### Data Flow Analysis
**What:** Track data mutations through execution paths.
**Example:** `[Reads: DB.users, Config.api_key] [Writes: DB.sessions, Cache.tokens]`
**Benefit:** Understand side effects without reading implementation.

### Runtime Profiling Integration
**What:** Show hot paths from profiler data.
**Example:** `[CPU: 45% of total] [Calls: 1.2M/day]`
**Benefit:** Identify performance bottlenecks from blueprint.

### Security Annotations
**What:** Mark security-sensitive code.
**Example:** `[Security: Handles PII] [Auth: Required]`
**Benefit:** Prevent accidental security regressions.

### AI-Generated Summaries (Optional)
**What:** LLM-generated one-line summaries for complex functions.
**Example:** `# Summary: Validates JWT tokens and refreshes expired ones`
**Benefit:** Human-readable context (opt-in, not required).

---

## 📚 Related Phases

- **Phase 5:** Symbol resolution with confidence scores (foundation for `--deps`)
- **Phase 3:** Watcher daemon (foundation for auto-cache invalidation)
- **Phase 11:** Symbolic editing (blueprint guides safe mutations)
- **Phase 12:** Batch edits with verification (blueprint shows impact scope)
- **Phase 14:** Documentation blueprint (same architecture for .md files)

---

## ✅ Definition of Done

**Phase 13 is complete when:**

1. ✅ All commands implemented and tested
2. ✅ Token efficiency: < 60% vs raw source
3. ✅ Performance: < 200ms for <1000 symbols
4. ✅ Accuracy: < 2% hallucination rate
5. ✅ Watcher integration: Auto-cache invalidation working
6. ✅ JSON export: Full schema with all overlays
7. ✅ Test suite: 50+ test cases covering edge cases
8. ✅ Dogfooding: Used in Cerberus development for 2 weeks
9. ✅ Documentation: Agent usage guide with 10+ examples
10. ✅ Benchmarks: Validated on 3 large codebases (TensorFlow, Django, FastAPI)

---

**Phase 13 transforms blueprint from a "symbol list" into a comprehensive Architectural Intelligence System. Agents receive deterministic, token-efficient, multi-dimensional views of code structure, enabling confident navigation and modification with zero guesswork.**
