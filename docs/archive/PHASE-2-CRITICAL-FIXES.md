# Phase 2: Critical Duplicate Fixes

**Status:** 🔴 NOT STARTED
**Estimated Duration:** 2-3 days
**Dependencies:** Phase 1 (Investigation) must be complete
**Success Criteria:** Zero duplicate results in search, get_symbol, and blueprint

---

## Overview

This phase implements fixes for the three P0 duplicate bugs identified in the audit. Each fix must be:
- Based on Phase 1 investigation findings
- Implemented with comprehensive error handling
- Tested in isolation before integration
- Validated against token usage expectations

**CRITICAL:** Do not proceed to Phase 3 until ALL fixes are applied and basic smoke tests pass.

---

## Fix 1: Duplicate Search Results

### Prerequisites
- Phase 1 Investigation 1 completed
- Root cause identified and documented
- Fix approach approved

### Implementation Plan

#### Scenario A: Duplicates in Hybrid Ranker (Most Likely)

**Root Cause:** Hybrid ranker merges BM25 + vector results without deduplication

**File to Fix:** `src/cerberus/retrieval/hybrid_ranker.py`

**Current Code (Hypothetical):**
```python
def merge_results(bm25_results, vector_results, weights=(0.7, 0.3)):
    """Merge and rank results from multiple sources."""
    combined = []

    # Add BM25 results
    for r in bm25_results:
        combined.append((r, weights[0] * r.score))

    # Add vector results
    for r in vector_results:
        combined.append((r, weights[1] * r.score))

    # Sort by combined score
    combined.sort(key=lambda x: x[1], reverse=True)

    return [r for r, score in combined]
```

**Bug:** If both BM25 and vector search return the same symbol, it appears twice.

**Fix:**
```python
def merge_results(bm25_results, vector_results, weights=(0.7, 0.3)):
    """Merge and rank results from multiple sources with deduplication."""
    # Use dict to deduplicate by (name, file_path, start_line)
    deduplicated = {}

    # Process BM25 results
    for r in bm25_results:
        key = (r.name, r.file_path, r.start_line)
        score = weights[0] * r.score

        # Keep highest scoring version
        if key not in deduplicated or score > deduplicated[key][1]:
            deduplicated[key] = (r, score)

    # Process vector results
    for r in vector_results:
        key = (r.name, r.file_path, r.start_line)
        score = weights[1] * r.score

        # Add to existing score if already present (hybrid scoring)
        if key in deduplicated:
            existing_result, existing_score = deduplicated[key]
            deduplicated[key] = (existing_result, existing_score + score)
        else:
            deduplicated[key] = (r, score)

    # Sort by combined score
    sorted_results = sorted(deduplicated.values(), key=lambda x: x[1], reverse=True)

    return [r for r, score in sorted_results]
```

**Testing:**
```python
# Test case 1: Overlapping results
bm25 = [Symbol("foo", "file.py", 10, score=0.9)]
vector = [Symbol("foo", "file.py", 10, score=0.8)]
merged = merge_results(bm25, vector)
assert len(merged) == 1  # Should be deduplicated

# Test case 2: Different symbols
bm25 = [Symbol("foo", "file.py", 10, score=0.9)]
vector = [Symbol("bar", "file.py", 20, score=0.8)]
merged = merge_results(bm25, vector)
assert len(merged) == 2  # Both should appear

# Test case 3: Duplicate within same source (should never happen but handle it)
bm25 = [Symbol("foo", "file.py", 10, score=0.9), Symbol("foo", "file.py", 10, score=0.8)]
vector = []
merged = merge_results(bm25, vector)
assert len(merged) == 1  # Deduplicated, keeping higher score
```

---

#### Scenario B: Duplicates in SQL Query

**Root Cause:** SQL JOIN creates duplicate rows

**File to Fix:** `src/cerberus/retrieval/bm25_search.py` (or similar)

**Current Code (Hypothetical):**
```python
def bm25_search(query, db_path, top_k=10):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        SELECT s.id, s.name, s.file_path, s.start_line, s.end_line, s.signature
        FROM symbols_fts
        JOIN symbols s ON symbols_fts.rowid = s.id
        WHERE symbols_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, top_k * 2))  # Bug: might be over-fetching

    results = [CodeSymbol.from_row(row) for row in cursor.fetchall()]
    return results
```

**Fix:**
```python
def bm25_search(query, db_path, top_k=10):
    conn = sqlite3.connect(db_path)

    # Add DISTINCT to prevent duplicates from JOIN
    cursor = conn.execute("""
        SELECT DISTINCT s.id, s.name, s.file_path, s.start_line, s.end_line, s.signature
        FROM symbols_fts
        JOIN symbols s ON symbols_fts.rowid = s.id
        WHERE symbols_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, top_k))

    results = [CodeSymbol.from_row(row) for row in cursor.fetchall()]

    # Additional safety: deduplicate in Python
    seen = set()
    unique_results = []
    for r in results:
        key = (r.name, r.file_path, r.start_line)
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    return unique_results[:top_k]
```

---

#### Scenario C: Duplicates in Database

**Root Cause:** Index builder inserts same symbol multiple times

**File to Fix:** `src/cerberus/index/index_builder.py`

**Current Code (Hypothetical):**
```python
def add_symbol(self, symbol: CodeSymbol):
    self.conn.execute("""
        INSERT INTO symbols (name, file_path, start_line, end_line, ...)
        VALUES (?, ?, ?, ?, ...)
    """, (symbol.name, symbol.file_path, symbol.start_line, ...))
```

**Fix:**
```python
def add_symbol(self, symbol: CodeSymbol):
    # Use INSERT OR REPLACE to prevent duplicates
    self.conn.execute("""
        INSERT OR REPLACE INTO symbols (name, file_path, start_line, end_line, ...)
        VALUES (?, ?, ?, ?, ...)
    """, (symbol.name, symbol.file_path, symbol.start_line, ...))

    # OR: Use UNIQUE constraint in schema and INSERT OR IGNORE
    # Schema should have: UNIQUE(name, file_path, start_line)
```

**Schema Update (if needed):**
```sql
-- Add unique constraint to prevent duplicates at database level
CREATE UNIQUE INDEX IF NOT EXISTS idx_symbols_unique
ON symbols(name, file_path, start_line);
```

---

### Testing Fix 1

**Test Script:** `tests/test_search_duplicates.py`
```python
import pytest
from cerberus.mcp.tools.search import search

def test_search_no_duplicates():
    """Verify search returns unique results only."""
    results = search(query="format_output", limit=5, mode="keyword")

    # Check no duplicates
    seen = set()
    for r in results:
        key = (r['name'], r['file'], r['start_line'])
        assert key not in seen, f"Duplicate found: {key}"
        seen.add(key)

    # Check result count
    assert len(results) <= 5

def test_search_hybrid_deduplication():
    """Verify hybrid search deduplicates across sources."""
    # This test requires access to internal functions
    from cerberus.retrieval.hybrid_ranker import merge_results

    # Mock results that would cause duplicates
    bm25 = [MockSymbol("foo", "file.py", 10)]
    vector = [MockSymbol("foo", "file.py", 10)]

    merged = merge_results(bm25, vector)

    assert len(merged) == 1
```

**Manual Verification:**
```python
# Test via MCP
mcp__cerberus__search(query="format_output", limit=5)
# Visually inspect: Should see 5 UNIQUE results, not duplicates

# Test with common names
mcp__cerberus__search(query="__init__", limit=10)
# Should return 10 different __init__ methods from different files
```

---

## Fix 2: Duplicate Get Symbol Results

### Prerequisites
- Phase 1 Investigation 2 completed
- Determined if this is same bug as Fix 1 or separate issue

### Implementation Plan

**File to Fix:** `src/cerberus/mcp/tools/symbols.py`

**Current Code:**
```python
@mcp.tool()
def get_symbol(name: str, exact: bool = True, context_lines: int = 5) -> List[dict]:
    manager = get_index_manager()
    index = manager.get_index()
    matches = index.find_symbols(name, exact=exact)

    results = []
    for symbol in matches:
        snippet = read_range(
            Path(symbol.file_path),
            symbol.start_line,
            symbol.end_line,
            padding=context_lines,
        )
        results.append({
            "name": symbol.name,
            "type": symbol.type,
            "file": symbol.file_path,
            "start_line": symbol.start_line,
            "end_line": symbol.end_line,
            "signature": symbol.signature,
            "code": snippet.content,
        })

    return results
```

**Potential Bug:** `find_symbols` returns duplicate matches from database.

**Fix:**
```python
@mcp.tool()
def get_symbol(name: str, exact: bool = True, context_lines: int = 5) -> List[dict]:
    manager = get_index_manager()
    index = manager.get_index()
    matches = index.find_symbols(name, exact=exact)

    # ADDED: Deduplicate matches
    seen = set()
    unique_matches = []
    for symbol in matches:
        key = (symbol.name, symbol.file_path, symbol.start_line)
        if key not in seen:
            seen.add(key)
            unique_matches.append(symbol)

    results = []
    for symbol in unique_matches:
        snippet = read_range(
            Path(symbol.file_path),
            symbol.start_line,
            symbol.end_line,
            padding=context_lines,
        )
        results.append({
            "name": symbol.name,
            "type": symbol.type,
            "file": symbol.file_path,
            "start_line": symbol.start_line,
            "end_line": symbol.end_line,
            "signature": symbol.signature,
            "code": snippet.content,
        })

    return results
```

**Alternative Fix:** Fix in `find_symbols` method itself.

**File:** `src/cerberus/storage/sqlite/symbols.py` or similar

```python
def find_symbols(self, name: str, exact: bool = True) -> List[CodeSymbol]:
    if exact:
        # ADDED: DISTINCT to prevent duplicates
        query = "SELECT DISTINCT * FROM symbols WHERE name = ?"
        params = (name,)
    else:
        query = "SELECT DISTINCT * FROM symbols WHERE name LIKE ?"
        params = (f"%{name}%",)

    cursor = self.conn.execute(query, params)
    rows = cursor.fetchall()

    # Additional safety: deduplicate results
    seen = set()
    unique_symbols = []
    for row in rows:
        key = (row['name'], row['file_path'], row['start_line'])
        if key not in seen:
            seen.add(key)
            unique_symbols.append(CodeSymbol.from_row(row))

    return unique_symbols
```

### Testing Fix 2

**Test Script:** `tests/test_symbol_duplicates.py`
```python
def test_get_symbol_unique_results():
    """Verify get_symbol returns unique results."""
    results = get_symbol(name="format_output", exact=True)

    # Check no duplicates
    seen = set()
    for r in results:
        key = (r['name'], r['file'], r['start_line'])
        assert key not in seen, f"Duplicate found: {key}"
        seen.add(key)

def test_get_symbol_exact_match():
    """Exact match should return 1 result for unique names."""
    results = get_symbol(name="format_output", exact=True)

    # If the name is unique, should only return 1 result
    # (This test may need adjustment based on actual codebase)
    assert len(results) >= 1  # At least one match
    # All results should have exactly the name we searched for
    for r in results:
        assert r['name'] == "format_output"
```

**Manual Verification:**
```python
# Test exact match
mcp__cerberus__get_symbol(name="format_output", exact=True)
# Should return 1-2 unique symbols (if overloaded), NOT 7 duplicates

# Test fuzzy match
mcp__cerberus__get_symbol(name="format", exact=False)
# Should return N unique symbols with "format" in name, no duplicates
```

---

## Fix 3: Duplicate Blueprint Symbols (Parser Bug)

### Prerequisites
- Phase 1 Investigation 3 completed
- Parser bug mechanism understood

### Implementation Plan

#### Likely Root Cause: Tree-sitter Confusion

**File to Fix:** `src/cerberus/parser/python_parser.py`

**Current Code (Hypothetical):**
```python
def parse(self, source_code: str, file_path: str) -> List[CodeSymbol]:
    tree = self.parser.parse(bytes(source_code, "utf8"))
    symbols = []

    # Walk the tree and extract symbols
    def walk_tree(node, depth=0):
        if node.type == "class_definition":
            # BUG: This might trigger on non-class constructs
            symbols.append(self._extract_class(node, source_code))

        for child in node.children:
            walk_tree(child, depth + 1)

    walk_tree(tree.root_node)
    return symbols
```

**Problem:** Tree-sitter might misidentify set/dict literals as class definitions.

**Fix Approach 1: Add Validation**
```python
def _extract_class(self, node, source_code):
    # Verify this is actually a class definition
    # Get the actual source text for this node
    start = node.start_byte
    end = node.end_byte
    text = source_code[start:end]

    # Validation: Must start with "class " or "@dataclass\nclass "
    if not (text.strip().startswith("class ") or "@dataclass" in text[:100]):
        return None  # Skip this false positive

    # Validation: Check for colon (class definitions must have "class Name:")
    first_line = text.split('\n')[0]
    if ':' not in first_line:
        return None  # Not a class definition

    # Extract class info
    class_name = self._extract_class_name(node)
    start_line = node.start_point[0] + 1
    end_line = node.end_point[0] + 1

    return CodeSymbol(
        name=class_name,
        type="class",
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        ...
    )
```

**Fix Approach 2: Use AST Instead**
```python
import ast

def parse(self, source_code: str, file_path: str) -> List[CodeSymbol]:
    # Use Python's built-in AST parser instead of tree-sitter
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        logger.warning(f"Syntax error in {file_path}: {e}")
        return []

    symbols = []

    # Walk AST and extract symbols
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # This is guaranteed to be a real class
            symbols.append(CodeSymbol(
                name=node.name,
                type="class",
                file_path=file_path,
                start_line=node.lineno,
                end_line=node.end_lineno,
                ...
            ))
        elif isinstance(node, ast.FunctionDef):
            symbols.append(...)
        # ... other symbol types

    return symbols
```

**Recommendation:** Use Python's AST for Python files (more reliable), keep tree-sitter for other languages.

### Testing Fix 3

**Test Script:** `tests/test_blueprint_duplicates.py`
```python
def test_parser_no_false_positive_classes():
    """Verify parser doesn't detect classes in set literals."""
    source = '''
BUILTIN_FILTER = {
    'print', 'len', 'str', 'int', 'float',
}

@dataclass
class RealClass:
    pass
'''
    parser = PythonParser()
    symbols = parser.parse(source, "test.py")

    classes = [s for s in symbols if s.type == "class"]

    # Should only find RealClass
    assert len(classes) == 1
    assert classes[0].name == "RealClass"

def test_blueprint_no_duplicate_symbols():
    """Verify blueprint doesn't show duplicate classes."""
    from cerberus.mcp.tools.structure import blueprint

    result = blueprint(
        path="/Users/proxikal/dev/projects/cerberus/src/cerberus/resolution/call_graph_builder.py",
        format="tree"
    )

    # Count class definitions in output
    class_count = result.count("[Class:")

    # Should be exactly 3: CallNode, CallGraph, CallGraphBuilder
    assert class_count == 3, f"Expected 3 classes, found {class_count}"
```

**Manual Verification:**
```python
# Test blueprint on problematic file
mcp__cerberus__blueprint(
    path="/Users/proxikal/dev/projects/cerberus/src/cerberus/resolution/call_graph_builder.py",
    format="tree"
)

# Manually count classes in output
# Should see:
# - CallNode (line ~45)
# - CallGraph (line ~55)
# - CallGraphBuilder (line ~65)
# Total: 3 classes (not 6)
```

---

## Integration and Smoke Testing

After all three fixes applied:

### Smoke Test Suite

**File:** `tests/test_duplicate_fixes_integration.py`

```python
def test_all_duplicates_fixed():
    """Integration test: Verify no duplicates in entire workflow."""

    # Test 1: Search
    search_results = search(query="__init__", limit=10)
    assert len(search_results) == len(set((r['name'], r['file'], r['start_line']) for r in search_results))

    # Test 2: Get symbol
    symbol_results = get_symbol(name="__init__", exact=True)
    assert len(symbol_results) == len(set((r['name'], r['file'], r['start_line']) for r in symbol_results))

    # Test 3: Blueprint
    bp_result = blueprint(path="src/cerberus/resolution/call_graph_builder.py")
    # Verify class count (specific to this file)
    assert bp_result.count("[Class:") == 3

def test_token_usage_after_fixes():
    """Verify token usage matches expectations."""

    # Search should be ~400-500 tokens for 5 results
    results = search(query="format_output", limit=5)
    # Rough token estimate: 80-100 tokens per result
    estimated_tokens = len(str(results)) / 4  # 4 chars ≈ 1 token
    assert estimated_tokens < 600, f"Search too expensive: ~{estimated_tokens} tokens"

    # Get symbol should be ~400 tokens for single method
    symbol = get_symbol(name="format_output", exact=True)
    estimated_tokens = len(str(symbol)) / 4
    assert estimated_tokens < 500, f"Get symbol too expensive: ~{estimated_tokens} tokens"
```

---

## Phase 2 Deliverables

1. **All three duplicate bugs fixed**
   - Search duplicates eliminated
   - Get symbol duplicates eliminated
   - Blueprint parser false positives eliminated

2. **Test suite passing**
   - Unit tests for each fix
   - Integration tests for workflow
   - Manual verification documented

3. **Code review completed**
   - All fixes peer reviewed
   - Edge cases considered
   - Error handling validated

4. **FIXES-APPLIED.md document**
   - Summary of each fix
   - Files changed
   - Testing results
   - Before/after token measurements

---

## Success Criteria

- [ ] Search: Returns unique results only (no duplicates)
- [ ] Get symbol: Returns unique symbols (no duplicates)
- [ ] Blueprint: Shows correct number of classes (no false positives)
- [ ] Token usage: Matches expected values (no 5-7x waste)
- [ ] All automated tests passing
- [ ] Manual verification confirms fixes work
- [ ] No regressions introduced

---

## Rollback Plan

If fixes cause issues:
1. Each fix is in separate commit with clear message
2. Can revert individual fixes using git
3. Feature flags can disable fixes if needed:
   ```python
   # In config
   ENABLE_SEARCH_DEDUPLICATION = True
   ENABLE_SYMBOL_DEDUPLICATION = True
   ENABLE_PARSER_FIX = True
   ```

---

**Next Phase:** PHASE-3-VERIFICATION.md
