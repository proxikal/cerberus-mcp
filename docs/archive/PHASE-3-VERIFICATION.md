# Phase 3: Comprehensive Verification

**Status:** 🔴 NOT STARTED
**Estimated Duration:** 1 day
**Dependencies:** Phase 2 (Critical Fixes) must be complete
**Success Criteria:** All tests pass, token usage validated, no regressions

---

## Overview

This phase ensures that:
1. All duplicate bugs are completely fixed
2. Token usage matches expectations
3. No new bugs were introduced
4. Edge cases are handled correctly
5. System performs well under real-world usage

**CRITICAL:** This is NOT optional. Do not skip to Phase 4 until all verification passes.

---

## Verification 1: Automated Test Suite

### Unit Tests

**Run all existing tests:**
```bash
cd /Users/proxikal/dev/projects/cerberus
source .venv/bin/activate
pytest tests/ -v --tb=short
```

**Expected outcome:**
- All tests pass (0 failures)
- No new warnings introduced
- Test coverage maintained or improved

**If failures occur:**
1. Determine if test expectations need updating (if testing old buggy behavior)
2. Or if fix introduced a regression (if testing valid behavior)
3. Fix the issue before proceeding

---

### Integration Tests

**File:** `tests/integration/test_mcp_tools_no_duplicates.py`

```python
import pytest
from cerberus.mcp.tools.search import search
from cerberus.mcp.tools.symbols import get_symbol
from cerberus.mcp.tools.structure import blueprint

class TestNoDuplicates:
    """Comprehensive tests for duplicate elimination."""

    def test_search_unique_results(self):
        """Search returns unique results across all modes."""
        for mode in ["keyword", "semantic", "balanced", "auto"]:
            results = search(query="__init__", limit=10, mode=mode)

            # Extract keys
            keys = [(r['name'], r['file'], r['start_line']) for r in results]

            # Verify uniqueness
            assert len(keys) == len(set(keys)), f"Duplicates found in {mode} mode"

    def test_get_symbol_exact_unique(self):
        """Exact symbol match returns unique results."""
        results = get_symbol(name="BlueprintGenerator", exact=True)

        keys = [(r['name'], r['file'], r['start_line']) for r in results]
        assert len(keys) == len(set(keys)), "Duplicate symbols found"

    def test_get_symbol_fuzzy_unique(self):
        """Fuzzy symbol match returns unique results."""
        results = get_symbol(name="Blueprint", exact=False)

        keys = [(r['name'], r['file'], r['start_line']) for r in results]
        assert len(keys) == len(set(keys)), "Duplicate symbols found"

    def test_blueprint_no_false_positives(self):
        """Blueprint parser doesn't detect false positive classes."""
        result = blueprint(
            path="/Users/proxikal/dev/projects/cerberus/src/cerberus/resolution/call_graph_builder.py",
            format="tree"
        )

        # Count classes
        class_count = result.count("[Class:")

        # Known file has 3 classes
        assert class_count == 3, f"Expected 3 classes, found {class_count}"

    def test_blueprint_multiple_files_no_duplicates(self):
        """Test blueprint on multiple files."""
        test_files = [
            "src/cerberus/blueprint/facade.py",
            "src/cerberus/quality/predictor.py",
            "src/cerberus/retrieval/hybrid_ranker.py",
        ]

        for file_path in test_files:
            result = blueprint(path=file_path, format="tree")

            # Verify no obvious duplicates in output
            # (same symbol appearing twice in succession)
            lines = result.split('\n')
            for i in range(len(lines) - 1):
                assert lines[i] != lines[i+1], f"Duplicate line in blueprint: {lines[i]}"

class TestTokenEfficiency:
    """Verify token usage matches expectations."""

    def test_search_token_usage(self):
        """Search results within expected token budget."""
        results = search(query="format_output", limit=5, mode="keyword")

        # Estimate tokens (4 chars ≈ 1 token)
        result_str = str(results)
        estimated_tokens = len(result_str) / 4

        # 5 results × 100 tokens/result = 500 tokens expected
        assert estimated_tokens < 600, f"Search too expensive: ~{estimated_tokens} tokens"

    def test_get_symbol_token_usage(self):
        """Get symbol within expected token budget."""
        results = get_symbol(name="format_output", exact=True, context_lines=5)

        result_str = str(results)
        estimated_tokens = len(result_str) / 4

        # Single method ~400 tokens expected
        assert estimated_tokens < 600, f"Get symbol too expensive: ~{estimated_tokens} tokens"

    def test_blueprint_basic_token_usage(self):
        """Basic blueprint within token budget."""
        result = blueprint(
            path="src/cerberus/mcp/tools/structure.py",
            format="tree",
            show_deps=False,
            show_meta=False
        )

        estimated_tokens = len(result) / 4

        # Basic blueprint ~350 tokens expected
        assert estimated_tokens < 500, f"Blueprint too expensive: ~{estimated_tokens} tokens"

    def test_blueprint_metadata_token_multiplier(self):
        """Verify metadata increases tokens by ~4x."""
        # Basic blueprint
        basic = blueprint(
            path="src/cerberus/blueprint/facade.py",
            format="tree",
            show_deps=False,
            show_meta=False
        )

        # With metadata
        with_meta = blueprint(
            path="src/cerberus/blueprint/facade.py",
            format="tree",
            show_deps=True,
            show_meta=True
        )

        basic_tokens = len(basic) / 4
        meta_tokens = len(with_meta) / 4

        multiplier = meta_tokens / basic_tokens

        # Should be approximately 4-5x
        assert 3.5 < multiplier < 6, f"Metadata multiplier unexpected: {multiplier}x"

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_search_empty_results(self):
        """Search with no matches returns empty list."""
        results = search(query="xyzabc123notfound", limit=10)
        assert results == [] or len(results) == 0

    def test_search_limit_respected(self):
        """Search respects limit parameter."""
        for limit in [1, 5, 10, 20]:
            results = search(query="__init__", limit=limit)
            assert len(results) <= limit

    def test_get_symbol_not_found(self):
        """Get symbol with non-existent name."""
        results = get_symbol(name="NonExistentSymbolXYZ123", exact=True)
        assert results == [] or len(results) == 0

    def test_blueprint_non_existent_file(self):
        """Blueprint on non-existent file returns error."""
        result = blueprint(path="/path/to/nonexistent/file.py")
        assert "error" in result or "not found" in result.lower()

    def test_blueprint_empty_file(self):
        """Blueprint on empty file."""
        # Create temp empty file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("")
            temp_path = f.name

        result = blueprint(path=temp_path)
        # Should handle gracefully (empty result or minimal structure)
        assert isinstance(result, (str, dict))
```

**Run integration tests:**
```bash
pytest tests/integration/test_mcp_tools_no_duplicates.py -v
```

---

## Verification 2: Manual MCP Testing

### Test Suite via MCP Interface

**Setup:**
```bash
# Ensure index is fresh
cd /Users/proxikal/dev/projects/cerberus
rm -rf .cerberus/
```

**Test 1: Search - No Duplicates**
```python
# Test via Claude Code or MCP client
mcp__cerberus__index_build(path="/Users/proxikal/dev/projects/cerberus")

# Search test
results = mcp__cerberus__search(query="format_output", limit=5, mode="keyword")

# Manual verification:
# 1. Print all results
# 2. Check each file path + line number is unique
# 3. Count results (should be ≤ 5)
# 4. Visual inspection: no identical entries
```

**Expected Output:**
```json
{
  "result": [
    {"name": "format_output", "file": "path/to/file1.py", "start_line": 601, ...},
    {"name": "format_as_output", "file": "path/to/file2.py", "start_line": 123, ...},
    ... (5 unique results total)
  ]
}
```

---

**Test 2: Get Symbol - No Duplicates**
```python
results = mcp__cerberus__get_symbol(name="format_output", exact=True)

# Manual verification:
# 1. Count results
# 2. Check if same method appears multiple times (should NOT)
# 3. Verify code snippets are different (if multiple matches)
```

**Expected Output:**
```json
{
  "result": [
    {
      "name": "format_output",
      "file": "src/cerberus/blueprint/facade.py",
      "start_line": 601,
      "end_line": 637,
      "code": "... (full method code) ..."
    }
    // Should be 1-3 unique results, NOT 7 duplicates
  ]
}
```

---

**Test 3: Blueprint - No False Positives**
```python
result = mcp__cerberus__blueprint(
    path="/Users/proxikal/dev/projects/cerberus/src/cerberus/resolution/call_graph_builder.py",
    format="tree"
)

# Manual verification:
# 1. Count "[Class:" occurrences
# 2. Should be exactly 3: CallNode, CallGraph, CallGraphBuilder
# 3. Verify line numbers are correct (~45, ~55, ~65)
```

**Expected Output:**
```
[File: .../call_graph_builder.py]
├── [Class: CallNode] (Lines 45-51)
├── [Class: CallGraph] (Lines 55-62)
└── [Class: CallGraphBuilder] (Lines 65-431)
    ├── (method1)
    ├── (method2)
    ...
```

---

**Test 4: Token Usage Measurements**

```python
# Measure search
import sys
result = mcp__cerberus__search(query="__init__", limit=5)
tokens = len(str(result)) / 4  # Rough estimate
print(f"Search (limit=5): ~{tokens} tokens")
# Expected: 400-500 tokens

# Measure get_symbol
result = mcp__cerberus__get_symbol(name="BlueprintGenerator", exact=True)
tokens = len(str(result)) / 4
print(f"Get symbol: ~{tokens} tokens")
# Expected: 400-500 tokens

# Measure blueprint basic
result = mcp__cerberus__blueprint(path="src/cerberus/mcp/tools/structure.py", format="tree")
tokens = len(result) / 4
print(f"Blueprint (basic): ~{tokens} tokens")
# Expected: 300-400 tokens

# Measure blueprint with metadata
result = mcp__cerberus__blueprint(
    path="src/cerberus/blueprint/facade.py",
    format="tree",
    show_deps=True,
    show_meta=True
)
tokens = len(result) / 4
print(f"Blueprint (with metadata): ~{tokens} tokens")
# Expected: 1200-1800 tokens
```

---

## Verification 3: Regression Testing

### Test Previously Working Features

**File:** `tests/regression/test_no_regressions.py`

```python
class TestNoRegressions:
    """Ensure fixes didn't break existing functionality."""

    def test_index_building_still_works(self):
        """Index building completes successfully."""
        from cerberus.mcp.tools.indexing import index_build

        result = index_build(
            path="/Users/proxikal/dev/projects/cerberus/tests/test_files",
            extensions=["py"]
        )

        assert result['files'] > 0
        assert result['symbols'] > 0

    def test_skeletonize_still_works(self):
        """Skeletonization produces correct output."""
        from cerberus.mcp.tools.synthesis import skeletonize

        result = skeletonize(
            path="/Users/proxikal/dev/projects/cerberus/src/cerberus/mcp/tools/structure.py"
        )

        assert 'skeleton' in result
        assert result['compression_ratio'] < 1.0  # Should be compressed

    def test_call_graph_still_works(self):
        """Call graph generation works."""
        from cerberus.mcp.tools.analysis import call_graph

        result = call_graph(
            symbol_name="format_output",
            depth=2,
            direction="both"
        )

        assert result['status'] == 'ok'
        assert len(result['graphs']) > 0

    def test_related_changes_still_works(self):
        """Related changes prediction works."""
        from cerberus.mcp.tools.quality import related_changes

        result = related_changes(
            file_path="src/cerberus/blueprint/facade.py",
            symbol_name="format_output"
        )

        assert result['status'] == 'analyzed'
        assert 'suggestions' in result
        assert len(result['suggestions']) <= 5

    def test_memory_operations_still_work(self):
        """Memory learn/show operations work."""
        from cerberus.mcp.tools.memory import memory_learn, memory_show

        # Learn a preference
        learn_result = memory_learn(
            category="preference",
            content="Test preference for verification"
        )
        assert learn_result['status'] == 'learned'

        # Show preferences
        show_result = memory_show(category="preferences")
        assert 'preferences' in show_result
```

---

## Verification 4: Performance Testing

### Measure Performance Impact

**File:** `tests/performance/test_fix_performance.py`

```python
import time
import pytest

class TestPerformanceAfterFixes:
    """Ensure fixes don't significantly impact performance."""

    def test_search_performance(self):
        """Search completes within reasonable time."""
        start = time.time()
        results = search(query="__init__", limit=10)
        duration = time.time() - start

        assert duration < 1.0, f"Search too slow: {duration}s"

    def test_get_symbol_performance(self):
        """Get symbol completes within reasonable time."""
        start = time.time()
        results = get_symbol(name="BlueprintGenerator", exact=True)
        duration = time.time() - start

        assert duration < 0.5, f"Get symbol too slow: {duration}s"

    def test_blueprint_performance(self):
        """Blueprint generation completes within reasonable time."""
        start = time.time()
        result = blueprint(path="src/cerberus/blueprint/facade.py")
        duration = time.time() - start

        assert duration < 2.0, f"Blueprint too slow: {duration}s"

    def test_index_build_performance(self):
        """Index building completes in reasonable time."""
        # Small test directory
        start = time.time()
        result = index_build(
            path="/Users/proxikal/dev/projects/cerberus/tests/test_files"
        )
        duration = time.time() - start

        # Should be fast for small directory
        assert duration < 10.0, f"Index build too slow: {duration}s"
```

---

## Verification 5: Cross-Language Testing

### Test Non-Python Files

If Cerberus supports other languages, verify fixes work there too:

**Test JavaScript/TypeScript:**
```python
# If JS/TS support exists
result = blueprint(path="path/to/file.ts", format="tree")
# Verify no duplicates, no false positives
```

**Test Go:**
```python
# If Go support exists (from xcalibr test earlier)
result = blueprint(path="path/to/file.go", format="tree")
# Verify parser doesn't break on Go syntax
```

---

## Verification 6: Real-World Workflow Test

### Simulate Actual User Workflow

**Scenario:** Developer searching for a function, viewing details, then checking structure

```python
def test_realistic_workflow():
    """Simulate real developer workflow."""

    # Step 1: Search for a function
    print("1. Searching for format_output...")
    search_results = search(query="format_output", limit=5)
    assert len(search_results) > 0
    print(f"   Found {len(search_results)} results")

    # Step 2: Get detailed info on first result
    print("2. Getting symbol details...")
    first_result = search_results[0]
    symbol_details = get_symbol(name=first_result['name'], exact=True)
    assert len(symbol_details) > 0
    print(f"   Retrieved details for {symbol_details[0]['name']}")

    # Step 3: View file structure
    print("3. Viewing file structure...")
    file_path = symbol_details[0]['file']
    blueprint_result = blueprint(path=file_path, format="tree")
    assert len(blueprint_result) > 0
    print(f"   Blueprint generated ({len(blueprint_result)} chars)")

    # Step 4: Verify no duplicates anywhere
    print("4. Verifying no duplicates...")

    # Check search uniqueness
    search_keys = [(r['name'], r['file'], r['start_line']) for r in search_results]
    assert len(search_keys) == len(set(search_keys))

    # Check symbol uniqueness
    symbol_keys = [(s['name'], s['file'], s['start_line']) for s in symbol_details]
    assert len(symbol_keys) == len(set(symbol_keys))

    print("✅ Workflow completed successfully with no duplicates!")
```

---

## Verification Checklist

### Before proceeding to Phase 4:

**Automated Tests:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All regression tests pass
- [ ] Performance tests pass

**Manual Verification:**
- [ ] Search returns unique results (no duplicates)
- [ ] Get symbol returns unique results (no duplicates)
- [ ] Blueprint shows correct classes (no false positives)
- [ ] Token usage matches expected values
- [ ] No obvious regressions in existing features

**Token Measurements:**
- [ ] Search (limit=5): ≤ 600 tokens
- [ ] Get symbol: ≤ 600 tokens
- [ ] Blueprint (basic): ≤ 500 tokens
- [ ] Blueprint (with metadata): ≤ 2000 tokens
- [ ] Total workflow: ≤ 2000 tokens (not 5500+)

**Edge Cases:**
- [ ] Empty search results handled gracefully
- [ ] Non-existent files handled gracefully
- [ ] Empty files handled gracefully
- [ ] Large files respect token limits
- [ ] Deeply nested structures respect max_depth

**Cross-Platform:**
- [ ] Python files work correctly
- [ ] JavaScript/TypeScript work (if supported)
- [ ] Go files work (if supported)
- [ ] Other supported languages tested

---

## Issue Tracking

If verification reveals issues:

**Document in:** `VERIFICATION-ISSUES.md`

Template:
```markdown
## Issue: [Brief Description]

**Discovered During:** [Test name]
**Severity:** [P0/P1/P2]
**Root Cause:** [If known]

### Steps to Reproduce:
1. ...
2. ...
3. ...

### Expected Behavior:
...

### Actual Behavior:
...

### Proposed Fix:
...
```

**Process:**
1. Document all issues found
2. Triage by severity
3. Fix P0 issues before proceeding
4. P1/P2 issues can be fixed in Phase 4 or later

---

## Phase 3 Deliverables

1. **All tests passing**
   - Unit test report
   - Integration test report
   - Regression test report
   - Performance test report

2. **VERIFICATION-REPORT.md**
   - Summary of all verification activities
   - Test results and measurements
   - Token usage comparisons (before/after)
   - Any issues found and their status

3. **Token usage validation**
   - Documented measurements for all operations
   - Comparison to audit expectations
   - Confirmation of 5-7x waste eliminated

4. **Sign-off**
   - Confirmation that all P0 issues resolved
   - Confirmation that no critical regressions introduced
   - Approval to proceed to Phase 4

---

## Success Criteria

✅ **Complete when:**
- All automated tests pass (100% pass rate)
- Manual verification confirms no duplicates
- Token usage matches expected values
- No critical regressions found
- Performance within acceptable bounds
- All edge cases handled correctly

---

**Next Phase:** PHASE-4-ENHANCEMENTS.md
