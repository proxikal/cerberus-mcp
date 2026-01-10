# Phase 14 Specification: Agent Productivity Enhancements

**Status:** Proposed (To Follow Phase 13.5)
**Goal:** Eliminate low-value agent cycles by providing explicit style fixing (Style Guard), preventing context drift (Context Anchors), and proactively suggesting related changes (Predictive Editing). This phase focuses on **maximum productivity ROI** while maintaining **100% mission compliance** with Cerberus's deterministic, AST-first, machine-parsable philosophy.

---

## 🎯 Core Objectives

### 1. Style Guard (Explicit Style Fixing)
**Mission:** Provide deterministic, AST-based style fixes as an explicit agent action.

**Problem:**
- Agents frequently make edits that introduce minor lint errors (trailing whitespace, unused imports, missing newlines)
- They then waste a full turn detecting and fixing these trivial issues
- Example workflow waste:
  ```
  Turn 1: Agent edits function → introduces trailing whitespace
  Turn 2: Agent runs linter → detects whitespace
  Turn 3: Agent fixes whitespace
  ```

**Solution (Strict Resolution Compliant):**
```bash
# EXPLICIT STYLE FIXING (No Auto-Correct)
cerberus mutations edit src/main.py --symbol foo --code "..."
# Output: ✅ Edited: foo (src/main.py:42-58)
#         ⚠️  Style Issues Detected: 3 (trailing whitespace, unsorted imports)
#         💡 Fix with: cerberus quality style-fix src/main.py

# Agent must EXPLICITLY choose to fix
cerberus quality style-fix src/main.py
# Output: [Style Guard] Fixed 3 issues:
#         - Line 42: trailing whitespace removed
#         - Lines 15-17: imports sorted alphabetically
#         - Line 58: added final newline

# Preview before fixing
cerberus quality style-check src/main.py
# Returns: [Line 42] trailing whitespace
#          [Lines 15-17] unsorted imports (should be: ast, os, sys)
#          [Line 58] missing final newline

# Batch mode for multiple files
cerberus quality style-fix src/ --recursive
```

**Deterministic Fixes (Native AST Implementation):**
- ✅ Trailing whitespace removal (string operation)
- ✅ Import sorting - alphabetical order (AST parse + rewrite)
- ✅ Missing final newline (string operation)
- ✅ Inconsistent quotes - choose dominant style in file (AST analysis + rewrite)
- ✅ Blank line normalization - PEP 8 compliant (AST-based)
- ❌ **NO external tools** (no black/isort subprocess calls)
- ❌ **NO semantic changes** (never touches logic, only whitespace/structure)

**Integration with Symbol Guard:**
```bash
# HIGH RISK files require explicit confirmation
cerberus quality style-fix critical.py
# Output: ⚠️  [Symbol Guard] HIGH RISK file (churn: 2.5/week, coverage: 45%)
#         Confirm style fixes? [y/N]: _

# Force flag bypasses (for automation)
cerberus quality style-fix critical.py --force
```

**Key Principle:** Agent CHOOSES to fix style (maintains Strict Resolution mandate). No auto-correct.

**Benefit:** Reduces agent turn count by 15-30% while preserving agent autonomy.

---

### 2. Context Anchors (Prevent Drift in Long Sessions)
**Mission:** Ground agents in codebase reality using structured, machine-parsable metadata.

**Problem:**
- In long sessions (100+ turns), agents accumulate summarized context
- They start hallucinating function signatures, forgetting file locations
- Example drift:
  ```
  Turn 50: Agent correctly edits `batch_edit()` in mutations.py
  Turn 150: Agent tries to edit `batch_edit()` in editor.py (wrong file)
  Reason: Forgot where the function lives
  ```

**Solution (Machine-First JSON):**
```json
# MACHINE MODE (default: CERBERUS_MACHINE_MODE=1)
{
  "anchor": {
    "file": "src/cerberus/mutations.py",
    "symbol": "batch_edit",
    "lines": {"start": 234, "end": 289},
    "dependencies": [
      {"name": "validate_ops", "confidence": 1.0, "type": "call"},
      {"name": "apply_mutation", "confidence": 1.0, "type": "call"}
    ],
    "risk": {
      "level": "MEDIUM",
      "score": 0.65,
      "factors": {
        "churn_per_week": 0.8,
        "test_coverage": 0.85,
        "authors": 3
      }
    },
    "temporal": {
      "last_modified": "2026-01-08T14:32:15Z",
      "last_modified_by": "alice"
    },
    "safety": {
      "symbol_guard": "WARN",
      "verifiable": true,
      "undo_available": true
    }
  },
  "body": {
    "type": "function",
    "signature": "def batch_edit(operations: List[Operation], verify: bool = False) -> Result",
    "docstring": "Execute multiple AST mutations atomically.",
    "code": "def batch_edit(...)..."
  }
}
```

```bash
# HUMAN MODE (opt-in: CERBERUS_HUMAN_MODE=1)
╭─ GPS ──────────────────────────────────────────────╮
│ File: src/cerberus/mutations.py                    │
│ Symbol: batch_edit                                  │
│ Lines: 234-289                                      │
├─ Dependencies ──────────────────────────────────────┤
│ Calls: validate_ops ✓1.0, apply_mutation ✓1.0     │
├─ Safety ────────────────────────────────────────────┤
│ Risk: 🟡 MEDIUM (churn: 0.8/wk, coverage: 85%)    │
│ Guard: WARN | Verifiable: Yes | Undo: Available    │
├─ Temporal ──────────────────────────────────────────┤
│ Modified: 2026-01-08 14:32 by alice               │
╰─────────────────────────────────────────────────────╯

def batch_edit(operations: List[Operation], verify: bool = False) -> Result:
    """Execute multiple AST mutations atomically."""
    # ... function body
```

**Anchor Components (GPS Model):**
1. **GPS Header:** File path + symbol name + line range (prevents "where is this?" confusion)
2. **Dependency Context:** Immediate dependencies with confidence scores (prevents "what does this call?" questions)
3. **Risk Signal:** Stability score + Symbol Guard status (prevents "is this safe to edit?" uncertainty)
4. **Temporal Context:** Last modified timestamp + author (prevents stale assumptions)
5. **Safety Context:** Integration with verify/undo/Symbol Guard systems

**Injection Points:**
- `cerberus retrieval get-symbol` → Full anchor with body
- `cerberus retrieval blueprint` → Anchor metadata in tree nodes
- `cerberus mutations batch-edit` → Anchors for all modified symbols
- `cerberus quality related-changes` → Anchors in suggestion list

**Validation (Hallucination Detection):**
```python
# Track wrong-file errors
class HallucinationDetector:
    def validate_mutation_request(self, request):
        if request.symbol not in request.file:
            return Error(
                f"Symbol '{request.symbol}' not found in '{request.file}'",
                anchor=get_anchor(request.symbol)  # Show correct location
            )
```

**Configuration:**
```bash
export CERBERUS_ANCHORS=json     # json (default), text, off
export CERBERUS_ANCHOR_COMPACT=1 # Minimal JSON (5% overhead vs 10%)
```

**Benefit:** Reduces hallucination-related errors by 40-60% in sessions >100 turns.

---

### 3. Predictive Editing (Deterministic Relationship Discovery)
**Mission:** Proactively suggest related changes using **only** deterministic AST relationships.

**Problem:**
- Agents make isolated changes without seeing ripple effects
- Example:
  ```
  Agent edits: validate_ops() to add new validation rule
  Agent misses: batch_edit() calls validate_ops() and needs error handling update
  Agent misses: tests/test_mutations.py needs new test case for validation rule
  ```
- Requires multiple feedback cycles to catch all related changes

**Solution (100% Signal, Zero Guesswork):**
```bash
# After any mutation, show deterministic suggestions
cerberus mutations edit src/mutations.py --symbol validate_ops --code "..."

# Output (Machine Mode):
{
  "status": "success",
  "anchor": { /* validate_ops metadata */ },
  "predictions": [
    {
      "confidence": "HIGH",
      "confidence_score": 1.0,
      "symbol": "batch_edit",
      "file": "src/cerberus/mutations.py",
      "line": 234,
      "reason": "direct_caller",
      "relationship": "calls validate_ops (AST-verified)",
      "anchor": { /* batch_edit metadata */ },
      "command": "cerberus retrieval get-symbol batch_edit"
    },
    {
      "confidence": "HIGH",
      "confidence_score": 0.95,
      "symbol": "test_validate_ops",
      "file": "tests/test_mutations.py",
      "line": 89,
      "reason": "test_file_pattern_match",
      "relationship": "test file for validate_ops (exact match)",
      "command": "cerberus retrieval get-symbol test_validate_ops"
    }
  ]
}
```

**Prediction Engine (Deterministic Only):**
```python
class PredictionEngine:
    """
    STRICT RULES:
    - Only AST-verified relationships (no heuristics)
    - Only exact pattern matches (no fuzzy matching)
    - No ML, no semantic similarity, no probabilistic models
    - Every suggestion must be explainable by code structure
    """

    def predict_related_changes(self, edited_symbol: str, file: str) -> List[Suggestion]:
        suggestions = []

        # 1. DIRECT CALLERS (Confidence: 1.0)
        # Phase 5 symbolic intelligence - AST-verified call graph
        callers = get_references(edited_symbol)
        for caller in callers:
            suggestions.append({
                "confidence": "HIGH",
                "confidence_score": 1.0,
                "symbol": caller.symbol,
                "reason": "direct_caller",
                "relationship": f"calls {edited_symbol} (AST-verified)"
            })

        # 2. EXACT TEST FILE MATCH (Confidence: 0.95)
        # Pattern: test_<symbol>.py or test_<module>.py
        test_patterns = [
            f"test_{edited_symbol}.py",
            f"test_{Path(file).stem}.py",
            f"tests/test_{edited_symbol}.py"
        ]
        for pattern in test_patterns:
            if exists(pattern):
                # Verify it actually imports the edited file
                if imports_file(pattern, file):
                    suggestions.append({
                        "confidence": "HIGH",
                        "confidence_score": 0.95,
                        "symbol": f"test_{edited_symbol}",
                        "reason": "test_file_pattern_match",
                        "relationship": f"test file for {edited_symbol} (verified import)"
                    })

        # 3. DIRECT DEPENDENCIES (Confidence: 1.0)
        # What this symbol calls (might need signature updates)
        callees = get_dependencies(edited_symbol)
        for callee in callees:
            suggestions.append({
                "confidence": "HIGH",
                "confidence_score": 1.0,
                "symbol": callee.symbol,
                "reason": "direct_dependency",
                "relationship": f"{edited_symbol} calls this (signature change propagation)"
            })

        # Filter by stability (prefer SAFE over HIGH RISK)
        prioritized = sort_by_stability(suggestions)

        # Limit to top 5 to avoid noise
        return prioritized[:5]
```

**Forbidden Prediction Methods:**
- ❌ Semantic similarity (ML-based, non-deterministic)
- ❌ "Probably related" heuristics (guesswork)
- ❌ Historical co-edit patterns (correlation ≠ causation)
- ❌ Low-confidence guesses (<0.9 confidence score)
- ❌ Fuzzy string matching (ambiguous)

**Display Modes:**
```bash
# Inline (default) - show predictions after mutation
cerberus mutations edit ...
# Shows: top 3 HIGH confidence suggestions

# Full report - show all predictions with reasoning
cerberus quality related-changes validate_ops --verbose
# Shows: all HIGH confidence + reasoning + anchor metadata

# Disable predictions
export CERBERUS_PREDICTIVE=off

# Verbose mode (shows internal reasoning)
export CERBERUS_PREDICTIVE=verbose
```

**Integration with Phase 13:**
- Uses blueprint dependency graph (Phase 13.1) → traversal for callers/callees
- Filters by stability scores (Phase 13.2) → prioritize SAFE symbols
- Leverages auto-hydration (Phase 13.5) → include mini-blueprints of suggestions
- Extends watcher ledger (Phase 13.4) → track prediction accuracy over time

**Benefit:** Reduces missed dependencies by 50-70%, catches 95% of direct relationships proactively.

---

## 🛡️ Mission Compliance

### Alignment with Core Mandates (CERBERUS.md)

| Mandate | Phase 14 Implementation |
|---------|------------------------|
| **Code > Prompts** (Line 7) | ✅ Predictions use AST call graph, not semantic guessing |
| **Verified Transactions** (Line 8) | ✅ Style Guard integrates with --verify flag |
| **Strict Resolution** (Line 9) | ✅ Style fixes require explicit agent action (no auto-correct) |
| **Parse-Perfect Output** (Line 11) | ✅ JSON schema for all outputs, >98% parse accuracy |
| **Machine-First JSON** (Line 2) | ✅ Anchors use JSON in machine mode, text only in human mode |
| **100% Signal / 0% Noise** (Line 6) | ✅ Only HIGH confidence predictions (≥0.9), deterministic only |
| **Dogfooding** (Throughout) | ✅ Zero external tools (no black/isort), native implementations |

### Forbidden Pattern Avoidance

| Forbidden (CERBERUS.md) | Phase 14 Compliance |
|-------------------------|---------------------|
| `read_file` on code (Line 7) | ✅ Anchors retrieve from index, not file reads |
| Speculative edits (Line 17) | ✅ Style fixes shown in preview, require confirmation |
| Fuzzy writes (Line 10) | ✅ All fixes are deterministic AST rewrites |
| Unverified mutations (Line 8) | ✅ Style fixes compatible with --verify workflow |

---

## 🔗 Safety Integration

Phase 14 composes with existing safety systems (Phase 12, 13.2):

### Integration Point 1: Symbol Guard + Style Guard
```bash
# HIGH RISK file blocks style fixes by default
cerberus quality style-fix src/critical.py
# Output: ⚠️  [Symbol Guard] 🔴 HIGH RISK
#         Churn: 2.5 edits/week | Coverage: 45% | Risk Score: 0.85
#         Style fixes disabled for safety.
#         Override with: --force

# Explicit override required
cerberus quality style-fix src/critical.py --force
# Logs to ledger: "style_guard: HIGH RISK override by agent"
```

### Integration Point 2: Verify + Style
```bash
# Verification-gated style fixing
cerberus quality style-fix src/main.py --verify "pytest tests/"
# Flow: apply fixes → run tests → commit if pass, rollback if fail
```

### Integration Point 3: Undo + Style/Predictions
```bash
# Undo includes style fixes
cerberus mutations undo
# Reverts: code edits + style fixes in last operation

# Predictions respect undo history
cerberus mutations edit ...
# Output: [Predictive] Note: validate_ops was recently undone (3 min ago)
#         Skipping as suggestion (likely intentional revert)
```

### Integration Point 4: Context Anchors + Safety Signals
```json
{
  "anchor": {
    "safety": {
      "symbol_guard": "HIGH_RISK",    // Phase 13.2 integration
      "verifiable": true,              // Has tests, can use --verify
      "undo_available": true,          // Can rollback
      "recent_undo": false             // Not recently reverted
    }
  }
}
```

---

## 📋 Output Schema Specification

All Phase 14 outputs in machine mode MUST conform to this JSON schema:

### Style Guard Output
```json
{
  "command": "quality.style-fix",
  "status": "success",
  "file": "src/mutations.py",
  "fixes_applied": [
    {
      "type": "trailing_whitespace",
      "line": 42,
      "before": "def foo():    ",
      "after": "def foo():"
    },
    {
      "type": "import_sort",
      "lines": [15, 16, 17],
      "before": ["import sys", "import ast", "import os"],
      "after": ["import ast", "import os", "import sys"]
    }
  ],
  "ledger_id": "style_20260110_153210",
  "safety": {
    "symbol_guard": "SAFE",
    "risk_score": 0.25
  }
}
```

### Context Anchor Schema
```json
{
  "anchor": {
    "file": "src/cerberus/mutations.py",
    "symbol": "batch_edit",
    "lines": {"start": 234, "end": 289},
    "dependencies": [
      {
        "name": "validate_ops",
        "confidence": 1.0,
        "type": "call",
        "file": "src/cerberus/mutations.py",
        "line": 245
      }
    ],
    "risk": {
      "level": "MEDIUM",
      "score": 0.65,
      "factors": {
        "churn_per_week": 0.8,
        "test_coverage": 0.85,
        "authors": 3,
        "days_since_last_edit": 12
      }
    },
    "temporal": {
      "last_modified": "2026-01-08T14:32:15Z",
      "last_modified_by": "alice",
      "created": "2025-11-20T09:15:00Z"
    },
    "safety": {
      "symbol_guard": "WARN",
      "verifiable": true,
      "undo_available": true,
      "recent_undo": false
    }
  }
}
```

### Predictive Editing Output
```json
{
  "command": "mutations.edit",
  "status": "success",
  "anchor": { /* edited symbol anchor */ },
  "predictions": [
    {
      "confidence": "HIGH",
      "confidence_score": 1.0,
      "symbol": "batch_edit",
      "file": "src/cerberus/mutations.py",
      "line": 234,
      "reason": "direct_caller",
      "relationship": "calls validate_ops (AST-verified)",
      "anchor": { /* suggestion anchor */ },
      "command": "cerberus retrieval get-symbol batch_edit"
    }
  ],
  "prediction_stats": {
    "total_analyzed": 15,
    "high_confidence": 2,
    "shown": 2,
    "filtered": 13
  }
}
```

**Validation Requirements:**
- All outputs pass JSON schema validation
- Parse accuracy >98% (tested with GPT-4/Claude extraction)
- Compact mode adds <5% token overhead vs current outputs
- Human mode uses box-drawing characters for readability (opt-in only)

---

## 🔧 Implementation Constraints

### Constraint 1: Zero External Dependencies
```python
# ✅ ALLOWED: Native Python stdlib
import ast
import re
from pathlib import Path

def fix_imports(code: str) -> str:
    tree = ast.parse(code)
    # ... AST manipulation using only stdlib

# ❌ FORBIDDEN: External formatters
import subprocess
subprocess.run(['black', '-'])  # NO!
subprocess.run(['isort', '-'])  # NO!
```

### Constraint 2: Deterministic Only
```python
# ✅ ALLOWED: AST-verified relationships
callers = get_references_from_ast(symbol)  # Deterministic call graph

# ✅ ALLOWED: Exact pattern matching
if exists(f"test_{symbol}.py"):  # Exact file name match

# ❌ FORBIDDEN: Probabilistic models
similarity = ml_model.semantic_similarity(a, b)  # Non-deterministic

# ❌ FORBIDDEN: Heuristics
if "test" in filename and "mock" in content:  # Fuzzy logic
```

### Constraint 3: AST-Based Fixes Only
```python
# ✅ ALLOWED: Whitespace (string operations)
def fix_whitespace(code: str) -> str:
    return code.rstrip() + '\n'

# ✅ ALLOWED: Import sorting (AST rewrite)
def fix_imports(code: str) -> str:
    tree = ast.parse(code)
    # ... sort imports, regenerate with ast.unparse()

# ❌ FORBIDDEN: Semantic refactoring
def fix_complexity(code: str) -> str:
    # Trying to simplify logic → semantic change → forbidden
```

### Constraint 4: Performance Budget
- Style Guard: <50ms per file
- Context Anchor: <10ms overhead per symbol output
- Predictive Engine: <200ms per mutation
- **Total Phase 14 overhead: <250ms per operation**

---

## 🗂️ Ledger Integration

All Phase 14 operations logged for transparency and tuning:

```bash
# View style fix history
cerberus ledger show --filter style_guard --limit 10
# Output:
# [2026-01-10 15:32:10] style_guard: fixed 3 issues in src/mutations.py
#   - Line 42: trailing whitespace removed
#   - Lines 15-17: imports sorted
#   - Risk: SAFE (0.25)
# [2026-01-10 15:35:22] style_guard: HIGH RISK override in src/core.py
#   - Agent: claude-sonnet-4.5
#   - Risk: HIGH (0.87)

# View prediction accuracy
cerberus ledger show --filter predictions --stats
# Output:
# [2026-01-10 15:33:05] prediction: suggested batch_edit (HIGH, 1.0) → followed
# [2026-01-10 15:34:12] prediction: suggested test_validate (HIGH, 0.95) → followed
# [2026-01-10 15:36:45] prediction: suggested review_handler (HIGH, 1.0) → ignored
#
# Stats (last 100 predictions):
#   High Confidence Accuracy: 94% (47/50 followed)
#   Avg suggestions per mutation: 2.3
#   False positive rate: 6%

# View anchor usage
cerberus ledger show --filter anchors --stats
# Output:
# Anchors generated: 1,234
# Hallucination corrections: 12 (1.0%)
# Avg token overhead: 4.8%
```

**Benefits:**
- Track which style fixes are most common (optimize detector)
- Measure prediction accuracy over time (tune confidence thresholds)
- Identify hallucination patterns (improve anchor design)
- Audit HIGH RISK overrides (security review)

---

## 🏗 Implementation Strategy

### Phase 14.1: Style Guard Foundation (Week 1-2)
- [ ] Create `src/cerberus/quality/style_guard.py`
- [ ] Implement native fixes: whitespace, imports (AST), newlines, quotes
- [ ] Add `cerberus quality style-check` command (preview)
- [ ] Add `cerberus quality style-fix` command (apply)
- [ ] Integrate with Symbol Guard (HIGH RISK protection)
- [ ] Add ledger logging for all style operations
- [ ] Integration with mutation pipeline: detect issues, show fix command

**Success Criteria:**
- 100 test cases pass without breaking code
- Zero external tool dependencies (no black/isort)
- Performance: <50ms per file
- Symbol Guard blocks HIGH RISK by default

### Phase 14.2: Context Anchors (Week 3)
- [ ] Design JSON schema for anchors (GPS + deps + risk + temporal + safety)
- [ ] Implement anchor generation in retrieval layer
- [ ] Add anchors to `get-symbol` output
- [ ] Add anchors to `blueprint` output (tree nodes)
- [ ] Add anchors to mutation diffs
- [ ] Implement compact mode (<5% token overhead)
- [ ] Add hallucination detector (wrong-file validation)

**Success Criteria:**
- All outputs conform to JSON schema
- Parse accuracy >98% (GPT-4 extraction test)
- Token overhead <5% in compact mode
- Hallucination detector catches wrong-file errors

### Phase 14.3: Predictive Editing Engine (COMPLETE)
- [x] Create `src/cerberus/quality/predictor.py`
- [x] Implement direct caller analysis (AST call graph)
- [x] Implement test file detection (exact pattern match + import verification)
- [x] Implement direct dependency analysis (callees)
- [x] Build deterministic ranking (confidence ≥0.9 only)
- [x] Integrate with stability scores (prioritize SAFE)
- [x] Add basic ledger logging (record predictions made)
- [ ] ~~Add prediction accuracy tracking~~ → **Deferred to Phase 14.4**

**Success Criteria:**
- ✅ Zero heuristics or ML-based predictions
- ✅ Performance: <200ms per mutation
- ✅ 15 tests passing
- ✅ CLI integration complete (`cerberus quality related-changes`)
- ✅ Automatic suggestions after edits
- ✅ Basic logging to ledger (what predictions were made)

**Deferred:**
- Accuracy tracking (whether agents followed suggestions) - requires user action correlation

### Phase 14.4: Advanced Analytics & Integration (Future)
- [ ] **Prediction Accuracy Tracking** (deferred from 14.3)
  - Track correlation between predictions and subsequent agent actions
  - Detect if agents followed suggestions within temporal window
  - Calculate accuracy metrics (% of predictions acted upon)
  - Surface insights: `cerberus ledger show --filter predictions --stats`
- [ ] Integrate Style Guard with --verify workflow
- [ ] Integrate predictions with undo history
- [ ] Add safety metadata to all anchors
- [ ] Implement progressive rollout flags
- [ ] Performance optimization (meet <250ms total budget)

**Success Criteria:**
- All Phase 14 features compose with Phase 12/13 safety systems
- Feature flags work independently
- Total latency <250ms per operation
- Zero regressions in existing functionality

### Phase 14.5: Polish & Documentation (Week 7)
- [ ] Update CERBERUS.md with Phase 14 commands
- [ ] Add formal output schemas to documentation
- [ ] Write agent-facing guide: "Phase 14 Usage Patterns"
- [ ] Benchmark: measure turn reduction in 50 workflows
- [ ] Dogfood: use Phase 14 features to complete Phase 14
- [ ] Final compliance audit: verify 100% mission alignment

**Success Criteria:**
- Documentation complete with examples
- Turn reduction measured: 25-50% in complex workflows
- 100% mission compliance verified
- Ledger shows all operations tracked correctly

---

## 📉 Success Metrics (Mission-Aligned Standards)

### Style Guard
1. **Turn Reduction:** 15-30% fewer agent turns in typical editing workflows
2. **Fix Accuracy:** 100% non-breaking + zero semantic changes (AST-verified)
3. **Coverage:** Handles 95% of common style issues (whitespace, imports, quotes, newlines)
4. **External Dependencies:** Zero (no black/isort/external formatters)
5. **Performance:** <50ms per file
6. **Safety:** HIGH RISK files blocked by default, require --force

### Context Anchors
1. **Hallucination Reduction:** 40-60% fewer wrong-file/wrong-symbol errors in sessions >100 turns
2. **Anchor Coverage:** 100% of symbol outputs include GPS metadata
3. **Token Overhead:** <5% in compact JSON mode (machine mode default)
4. **Parse Accuracy:** >98% (LLM extraction test with GPT-4/Claude)
5. **Format Compliance:** JSON in machine mode, text only in human mode (no mixing)
6. **Schema Validity:** 100% of outputs pass JSON schema validation

### Predictive Editing
1. **Detection Rate:** 95% of direct dependencies flagged proactively
2. **Suggestion Accuracy:** HIGH confidence (≥0.9) suggestions correct 95% of time
3. **False Positive Rate:** <10% of suggestions irrelevant (deterministic filtering)
4. **Signal/Noise:** 100% signal (zero heuristics, zero ML guessing)
5. **Performance:** <200ms per mutation
6. **Integration:** Seamless composition with Phase 13 blueprint/stability features

### Overall Phase 14
1. **Combined Turn Reduction:** 25-50% fewer agent turns in complex workflows
2. **Mission Compliance:** 100% alignment with CERBERUS.md mandates
3. **Performance:** <250ms total added latency (all features combined)
4. **External Dependencies:** Zero (native implementations only)
5. **Parse Accuracy:** >98% for all outputs (machine-parsable standard)
6. **Ledger Coverage:** 100% of operations logged for transparency
7. **Safety Integration:** Full composition with Phase 12 (verify/undo) and 13.2 (Symbol Guard)

---

## 🔗 Connection to Phase 13

Phase 14 is the **productivity layer** on top of Phase 13's **intelligence layer**:

| Phase 13 Provides | Phase 14 Leverages |
|-------------------|-------------------|
| Blueprint structure | Context Anchors embed blueprint metadata in all outputs |
| Stability scores (13.2) | Symbol Guard integration + prediction prioritization |
| Dependency graph (13.1) | Predictive engine traverses graph for callers/callees |
| Auto-hydration (13.5) | Predictions include mini-blueprints of suggestions |
| Watcher integration (13.4) | Ledger tracks style fixes and prediction accuracy |
| Complexity metrics (13.1) | Anchor metadata includes complexity in risk calculation |

**Synergy Example:**
```bash
# Agent edits a HIGH RISK function
cerberus mutations edit src/core.py --symbol critical_function --code "..."

# Phase 13 provides:
# - Risk score: 🔴 HIGH RISK (churn: 2.5/week, coverage: 45%)
# - Dependency graph: Shows 15 direct callers
# - Blueprint structure: Function complexity = 8

# Phase 14 leverages:
# 1. [Context Anchor] Displays risk + deps + complexity in structured JSON
# 2. [Style Guard] Detects whitespace issues, shows fix command
# 3. [Predictive Editing] Suggests top 3 HIGH RISK callers with anchors
# 4. [Safety Integration] Symbol Guard warns before allowing changes

# Result: Agent has complete context + actionable suggestions in one output
```

**Why This Works:**
- Phase 13 = **What you need to know** (complexity, dependencies, risk)
- Phase 14 = **How to work efficiently** (explicit fixes, grounding anchors, proactive suggestions)
- Together = **Smart, fast, safe editing with full transparency**

---

## 🚧 Considerations & Risks

### Risks
1. **Style Guard Complexity:** Native implementation may miss edge cases that black/isort handle
2. **Anchor Token Overhead:** Even at 5%, adds up in large sessions
3. **Prediction False Positives:** Even 10% noise can distract in high-velocity workflows
4. **Performance Budget:** 250ms per operation may be tight with all features enabled

### Mitigations
1. **Limited Scope:** Style Guard only handles most common issues (80/20 rule), skip complex cases
2. **Configurable Overhead:** `CERBERUS_ANCHOR_COMPACT=1` reduces to minimum viable metadata
3. **Confidence Filtering:** Only show ≥0.9 confidence, aggressive filtering of ambiguous suggestions
4. **Async Optimization:** Run predictions in background thread, don't block mutation response
5. **Progressive Rollout:** Feature flags allow disabling any component if issues arise

### Alternatives Considered
- **External Linters:** Use black/isort → Rejected (violates dogfooding mandate)
- **Text Anchors:** Human-readable format → Rejected (violates machine-first mandate)
- **ML Predictions:** Semantic similarity models → Rejected (violates deterministic mandate)
- **Auto-Fix Style:** Apply fixes automatically → Rejected (violates strict resolution mandate)

### Decision Rationale
Implement all three features with strict constraints:
- Style fixes require explicit action (preserves agent autonomy)
- Anchors use JSON (machine-parsable, >98% accuracy)
- Predictions use AST only (deterministic, 100% signal)
- Together they provide multiplicative value while maintaining 100% mission compliance

---

## 🎓 Agent Usage Patterns

### Before Phase 14 (Current - 7 turns)
```bash
Turn 1: cerberus retrieval get-symbol validate_ops
Turn 2: cerberus mutations edit src/mutations.py --symbol validate_ops --code "..."
Turn 3: cerberus dogfood read src/mutations.py --lines 234-250  # Check for lint errors
Turn 4: cerberus mutations edit src/mutations.py --symbol validate_ops --code "..."  # Fix whitespace
Turn 5: cerberus retrieval search "calls validate_ops"  # Find related code
Turn 6: cerberus retrieval get-symbol batch_edit  # Check caller
Turn 7: cerberus mutations edit src/mutations.py --symbol batch_edit --code "..."  # Update caller
```

### After Phase 14 (Optimized - 4 turns, 43% reduction)
```bash
Turn 1: cerberus retrieval get-symbol validate_ops
# Output includes:
# - [Context Anchor] Full GPS metadata (file, lines, deps, risk)
# - Shows: calls apply_mutation ✓1.0, called by batch_edit ✓1.0

Turn 2: cerberus mutations edit src/mutations.py --symbol validate_ops --code "..."
# Output includes:
# - ✅ Edited successfully
# - ⚠️  Style issues detected: trailing whitespace (line 42), unsorted imports (lines 15-17)
# - 💡 Fix with: cerberus quality style-fix src/mutations.py
# - 🔮 [Predictive] HIGH confidence suggestions:
#     1. Update batch_edit (direct caller, line 234)
#     2. Update test_validate_ops (test file, line 89)

Turn 3: cerberus quality style-fix src/mutations.py
# Output: [Style Guard] Fixed 2 issues (whitespace, imports)

Turn 4: cerberus retrieval get-symbol batch_edit  # Review suggested caller
# Output includes:
# - [Context Anchor] Shows calls validate_ops ✓1.0 (confirming relationship)
# - Risk: 🟡 MEDIUM

Turn 5: cerberus mutations edit src/mutations.py --symbol batch_edit --code "..."
# Update with confidence, grounded by anchor metadata
```

### Advanced: Batch Workflow with Verification
```bash
Turn 1: cerberus mutations edit src/mutations.py --symbol validate_ops --code "..."
# [Predictive] Suggests: batch_edit, test_validate_ops

Turn 2: cerberus retrieval get-symbol batch_edit  # Review suggestion

Turn 3: cerberus mutations edit src/mutations.py --symbol batch_edit --code "..."

Turn 4: cerberus quality style-fix src/mutations.py --verify "pytest tests/"
# Applies style fixes, runs tests, commits if pass (atomic)
```

---

## 🚀 Implementation Priority

### Why This Phase Next
1. ✅ **Immediate ROI:** Every feature directly reduces wasted agent turns (25-50% combined)
2. ✅ **Leverages Phase 13:** Builds on existing blueprint intelligence (multiplicative value)
3. ✅ **100% Mission-Aligned:** Strict compliance with all CERBERUS.md mandates
4. ✅ **Low Risk:** Additive features, zero modifications to core indexing/mutation logic
5. ✅ **Dogfoodable:** Productivity gains felt immediately during development
6. ✅ **Completes Core Loop:** Read (Blueprint) → Think (Predict) → Write (Style) → Verify

### Compared to Documentation Phase (Deferred)
| Criteria | Documentation Phase | Phase 14 |
|----------|---------------------|----------|
| ROI | Removes exception clause (philosophical) | Reduces 25-50% wasted turns (practical) |
| Synergy | Orthogonal to Phase 13 | Directly leverages Phase 13 intelligence |
| Complexity | Markdown parsing edge cases | Well-defined AST operations |
| Impact | Better dogfooding compliance | Immediate agent productivity |
| **Winner** | Lower priority | **Phase 14 (High Impact)** |

---

## 🔄 Progressive Rollout Plan

Phase 14 features launch with feature flags for safe adoption:

```bash
# Week 1-2: Style Guard beta
export CERBERUS_STYLE_GUARD=beta  # Enabled for testing, feedback collection

# Week 3: Context Anchors beta
export CERBERUS_ANCHORS=json  # Enable anchors in JSON mode

# Week 4-5: Predictive Editing beta
export CERBERUS_PREDICTIVE=inline  # Show predictions after mutations

# Week 6: Full integration testing
# All features enabled, verify composition with Phase 12/13

# Week 7: General availability
# All features enabled by default, documentation complete
# Default configuration:
#   CERBERUS_ANCHORS=json (compact mode)
#   CERBERUS_PREDICTIVE=inline (HIGH confidence only)
#   Style fixes require explicit cerberus quality style-fix
```

**Rollback Plan:**
- Each feature has independent flag (can disable individually)
- Ledger tracks all operations (can analyze impact before/after)
- Performance monitoring (alerts if >250ms latency)
- User feedback collection (track agent turn counts)

---

## 📚 Appendix: Configuration Reference

```bash
# Style Guard
export CERBERUS_STYLE_GUARD=beta         # beta, disabled

# Context Anchors
export CERBERUS_ANCHORS=json             # json (default), text, off
export CERBERUS_ANCHOR_COMPACT=1         # Minimal JSON (<5% overhead)

# Predictive Editing
export CERBERUS_PREDICTIVE=inline        # off, inline (default), verbose
export CERBERUS_PREDICT_CONFIDENCE=0.9   # Minimum confidence threshold

# Ledger
export CERBERUS_LEDGER_TRACK_STYLE=1     # Track style operations
export CERBERUS_LEDGER_TRACK_PREDICT=1   # Track prediction accuracy

# Performance
export CERBERUS_PHASE14_PERF_BUDGET=250  # Max latency in ms
export CERBERUS_PREDICT_ASYNC=1          # Run predictions in background

# Safety Integration
export CERBERUS_STYLE_GUARD_RESPECT_RISK=1  # Block HIGH RISK files
```
