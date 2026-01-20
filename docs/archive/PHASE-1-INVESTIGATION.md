# Phase 1: Root Cause Investigation

**Status:** 🔴 NOT STARTED
**Estimated Duration:** 1-2 days
**Dependencies:** None
**Success Criteria:** Complete understanding of all three duplicate sources

---

## Overview

Before fixing the duplicate bugs, we must understand WHERE and WHY they occur. This phase involves systematic investigation, logging, and tracing through the codebase to pinpoint the exact source of each duplication issue.

**Why this phase is critical:**
- Fixing without understanding = high risk of incomplete fix or introducing new bugs
- Different duplicates may have different root causes
- Need to verify if duplicates are in storage, retrieval, or presentation layer

---

## Investigation 1: Duplicate Search Results

### Problem Statement
`mcp__cerberus__search(query="format_output", limit=5)` returns 5 IDENTICAL results with:
- Same file path
- Same line numbers
- Same score
- Same symbol name

**Question:** Are these duplicates stored in the database, or created during retrieval?

### Investigation Steps

#### Step 1.1: Check Raw Database State
**File:** Manual SQL query
**Action:**
```sql
-- Connect to index: sqlite3 /Users/proxikal/dev/projects/cerberus/.cerberus/cerberus.db

-- Query 1: Count how many times "format_output" appears
SELECT name, file_path, start_line, COUNT(*) as count
FROM symbols
WHERE name = 'format_output'
GROUP BY name, file_path, start_line
HAVING count > 1;

-- Query 2: If duplicates exist, find their IDs
SELECT id, name, file_path, start_line, end_line, type
FROM symbols
WHERE name = 'format_output'
ORDER BY file_path, start_line;

-- Query 3: Check if it's an indexing issue (same symbol indexed multiple times)
SELECT COUNT(*), name, file_path
FROM symbols
GROUP BY name, file_path
HAVING COUNT(*) > 1
LIMIT 10;
```

**Expected outcomes:**
- **Scenario A:** Database has 1 unique row → duplication happens during retrieval
- **Scenario B:** Database has 5+ rows → indexing bug creating duplicates at storage time

**Log findings:** Record exact SQL results in investigation log.

---

#### Step 1.2: Trace Search Tool Execution
**File:** `src/cerberus/mcp/tools/search.py`

**Action:** Add logging to trace execution:
```python
def search(query: str, limit: int = 10, mode: str = "auto") -> List[dict]:
    # ADD THIS LOGGING
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[SEARCH TRACE] query={query}, limit={limit}, mode={mode}")

    # Existing code
    manager = get_index_manager()
    index_path = manager.get_index_path()

    results = unified_search(
        query,
        index_path=index_path,
        mode=mode,
        top_k=limit,
    )

    # ADD THIS LOGGING
    logger.info(f"[SEARCH TRACE] unified_search returned {len(results)} results")
    for i, r in enumerate(results):
        logger.info(f"[SEARCH TRACE] Result {i}: {r.name} @ {r.file_path}:{r.start_line}")

    return results
```

**Run test:**
```python
mcp__cerberus__search(query="format_output", limit=5, mode="keyword")
```

**Check logs:** Look for duplicate results in logger output.

---

#### Step 1.3: Trace Unified Search
**File:** `src/cerberus/retrieval.py` or `src/cerberus/retrieval/facade.py`

**Action:** Find the `unified_search` function and add logging:
```python
def unified_search(query, index_path, mode="auto", top_k=10):
    logger.info(f"[UNIFIED_SEARCH] mode={mode}, top_k={top_k}")

    # If using hybrid search
    if mode == "auto" or mode == "balanced":
        keyword_results = bm25_search(...)
        semantic_results = vector_search(...)
        logger.info(f"[UNIFIED_SEARCH] BM25 returned {len(keyword_results)}")
        logger.info(f"[UNIFIED_SEARCH] Vector returned {len(semantic_results)}")

        merged = hybrid_ranker.merge(keyword_results, semantic_results)
        logger.info(f"[UNIFIED_SEARCH] After merge: {len(merged)}")

        return merged[:top_k]
```

**Hypothesis to test:**
- Are BM25 and vector search returning the same results?
- Does hybrid ranker deduplicate before merging?
- Is the merge creating duplicates?

---

#### Step 1.4: Check BM25 Search Implementation
**File:** `src/cerberus/retrieval/bm25_search.py`

**Action:** Examine SQL query:
```python
def bm25_search(query, db_path, top_k=10):
    # Find the actual SQL query
    # Look for something like:
    cursor.execute("""
        SELECT DISTINCT s.id, s.name, s.file_path, s.start_line, ...
        FROM symbols_fts
        JOIN symbols s ON symbols_fts.rowid = s.id
        WHERE symbols_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, top_k))
```

**Check:**
- Is `DISTINCT` present? If not, this could be the bug.
- Are there multiple JOINs that could create duplicates?
- Is the FTS5 table properly configured?

---

#### Step 1.5: Check Vector Search Implementation
**File:** `src/cerberus/retrieval/vector_search.py` or `src/cerberus/semantic/search.py`

**Action:** Check if vector search is returning duplicate IDs:
```python
def vector_search(query, top_k=10):
    # Trace the FAISS search
    distances, indices = faiss_index.search(query_vector, top_k)

    # ADD LOGGING
    logger.info(f"[VECTOR_SEARCH] FAISS returned indices: {indices}")
    logger.info(f"[VECTOR_SEARCH] Unique indices: {len(set(indices.flatten()))}")

    # Check if we're looking up the same symbol ID multiple times
```

**Check:**
- Are vector indices unique?
- Is symbol lookup creating duplicates?

---

#### Step 1.6: Check Hybrid Ranker
**File:** `src/cerberus/retrieval/hybrid_ranker.py`

**Action:** Examine merge logic:
```python
def merge(keyword_results, semantic_results, weights=None):
    # Check if deduplication happens
    all_results = keyword_results + semantic_results

    # IS THERE DEDUPLICATION HERE?
    # Look for something like:
    seen = set()
    unique_results = []
    for r in all_results:
        key = (r.name, r.file_path, r.start_line)
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    # If not, THIS IS THE BUG
```

---

### Investigation 1: Conclusion

**Document findings:**
- [ ] Database state: Duplicates in DB? Yes/No
- [ ] Search pipeline: Where do duplicates first appear?
- [ ] Root cause identified: [Storage | BM25 | Vector | Hybrid Ranker | MCP Tool]
- [ ] SQL queries: Missing DISTINCT? Problematic JOINs?

**Write summary:** Create `INVESTIGATION-1-SEARCH-DUPLICATES.md` with:
1. Root cause explanation
2. Stack trace of duplication point
3. Proposed fix approach
4. Risk assessment

---

## Investigation 2: Duplicate Get Symbol Results

### Problem Statement
`mcp__cerberus__get_symbol(name="format_output", exact=True)` returns 7 IDENTICAL results with full method code duplicated.

**Question:** Is this the same bug as search duplicates, or a different issue?

### Investigation Steps

#### Step 2.1: Trace Get Symbol Execution
**File:** `src/cerberus/mcp/tools/symbols.py`

**Action:** Add logging:
```python
def get_symbol(name: str, exact: bool = True, context_lines: int = 5) -> List[dict]:
    logger.info(f"[GET_SYMBOL] name={name}, exact={exact}")

    manager = get_index_manager()
    index = manager.get_index()
    matches = index.find_symbols(name, exact=exact)

    logger.info(f"[GET_SYMBOL] find_symbols returned {len(matches)} matches")
    for i, sym in enumerate(matches):
        logger.info(f"[GET_SYMBOL] Match {i}: {sym.name} @ {sym.file_path}:{sym.start_line}")

    results = []
    for symbol in matches:
        snippet = read_range(
            Path(symbol.file_path),
            symbol.start_line,
            symbol.end_line,
            padding=context_lines,
        )
        results.append({...})

    logger.info(f"[GET_SYMBOL] Returning {len(results)} results")
    return results
```

**Run test:**
```python
mcp__cerberus__get_symbol(name="format_output", exact=True)
```

**Analyze logs:**
- Does `find_symbols` return 1 match or 7 matches?
- Are duplicates introduced by snippet extraction?

---

#### Step 2.2: Check find_symbols Implementation
**File:** `src/cerberus/storage/sqlite/symbols.py` or similar

**Action:** Find the `find_symbols` method:
```python
def find_symbols(self, name: str, exact: bool = True):
    if exact:
        query = "SELECT * FROM symbols WHERE name = ?"
    else:
        query = "SELECT * FROM symbols WHERE name LIKE ?"

    cursor = self.conn.execute(query, (name,))
    rows = cursor.fetchall()

    # ADD LOGGING
    logger.info(f"[FIND_SYMBOLS] SQL returned {len(rows)} rows")

    return [CodeSymbol.from_row(r) for r in rows]
```

**Check:**
- Does SQL return multiple rows for same symbol?
- Is the query missing a UNIQUE constraint?

---

#### Step 2.3: Check Index Building
**File:** `src/cerberus/index/index_builder.py`

**Action:** Verify symbols are not indexed multiple times:
```python
def add_symbol(self, symbol):
    # Is there a check for duplicates before INSERT?
    # Should use: INSERT OR IGNORE / INSERT OR REPLACE
    # Or check: SELECT COUNT(*) before INSERT

    # ADD LOGGING during next index build
    logger.info(f"[INDEX] Adding symbol: {symbol.name} @ {symbol.file_path}:{symbol.start_line}")
```

**Test:** Rebuild index with logging enabled, check for duplicate insertions.

---

### Investigation 2: Conclusion

**Document findings:**
- [ ] Database has duplicate symbols? Yes/No
- [ ] find_symbols returns duplicates? Yes/No
- [ ] Indexing inserts same symbol multiple times? Yes/No
- [ ] Root cause: [Storage | Indexing | Query]

**Write summary:** Create `INVESTIGATION-2-SYMBOL-DUPLICATES.md`

---

## Investigation 3: Duplicate Blueprint Symbols

### Problem Statement
Blueprint on `call_graph_builder.py` shows 6 classes instead of 3. First 3 are false positives from lines inside a set literal.

**Question:** Why does the parser think lines in a set literal are class definitions?

### Investigation Steps

#### Step 3.1: Reproduce Parser Behavior Directly
**File:** Test script

**Action:** Create `test_parser_bug.py`:
```python
from cerberus.parser import PythonParser
from pathlib import Path

# Test on the actual file
file_path = Path("/Users/proxikal/dev/projects/cerberus/src/cerberus/resolution/call_graph_builder.py")
parser = PythonParser()

with open(file_path) as f:
    source = f.read()

symbols = parser.parse(source, str(file_path))

print(f"Found {len(symbols)} symbols")
for sym in symbols:
    if sym.type == "class":
        print(f"Class: {sym.name} at lines {sym.start_line}-{sym.end_line}")
```

**Expected output:**
```
Found X symbols
Class: CallNode at lines 45-51
Class: CallGraph at lines 55-62
Class: CallGraphBuilder at lines 65-431
```

**Actual output:** (if bug exists)
```
Class: CallNode at lines 18-24   ← FALSE POSITIVE
Class: CallGraph at lines 28-35   ← FALSE POSITIVE
Class: CallGraphBuilder at lines 38-343  ← FALSE POSITIVE
Class: CallNode at lines 45-51
Class: CallGraph at lines 55-62
Class: CallGraphBuilder at lines 65-431
```

---

#### Step 3.2: Examine Parser Class Detection Logic
**File:** `src/cerberus/parser/python_parser.py`

**Action:** Find how classes are detected:
```python
def _extract_classes(self, tree):
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # This should be the only way to detect classes
            classes.append(...)
    return classes
```

**Possible bugs:**
1. **String matching instead of AST:** Searching for "class " in source code
2. **Regex gone wrong:** Pattern matching "^class" but matching inside strings
3. **Tree-sitter issue:** Language parser misidentifying constructs

**Check:** How is class detection actually implemented?

---

#### Step 3.3: Inspect File Around Line 18
**File:** `src/cerberus/resolution/call_graph_builder.py`

**Action:** Read lines 15-45:
```python
# Line 17
BUILTIN_FILTER = {
    # Line 18-24: Strings inside set
    'print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'set', 'tuple',
    'range', 'enumerate', 'zip', 'map', 'filter', 'sum', 'min', 'max', 'abs',
    'isinstance', 'issubclass', 'type', 'getattr', 'setattr', 'hasattr', 'delattr',
    'open', 'input', 'sorted', 'reversed', 'all', 'any', 'next', 'iter',
    # ... more strings ...
}

# Line 45: ACTUAL CLASS
@dataclass
class CallNode:
    ...
```

**Question:** Is the parser confusing the set literal with code structure?

---

#### Step 3.4: Test Tree-sitter vs AST
**File:** Investigation script

**Action:** Test both parsers:
```python
import ast
from tree_sitter import Language, Parser

# Test 1: Python AST (should be correct)
with open("call_graph_builder.py") as f:
    source = f.read()
    tree = ast.parse(source)
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    print(f"AST found {len(classes)} classes:")
    for cls in classes:
        print(f"  {cls.name} at line {cls.lineno}")

# Test 2: Tree-sitter (might be buggy)
# ... check tree-sitter output
```

**Hypothesis:** If AST is correct but tree-sitter is wrong, the bug is in tree-sitter integration.

---

#### Step 3.5: Check Blueprint Query Logic
**File:** `src/cerberus/blueprint/facade.py:180-245`

**Action:** Examine `_query_symbols` method:
```python
def _query_symbols(self, file_path: str) -> List[CodeSymbol]:
    # Does this query add any filtering?
    cursor.execute("SELECT * FROM symbols WHERE file_path = ?", (file_path,))

    # Are symbols pre-filtered or is everything returned?
    # Check if duplicate symbols exist in results
```

**Question:** Are duplicate symbols in the database, or created during blueprint generation?

---

### Investigation 3: Conclusion

**Document findings:**
- [ ] Parser type: AST / Tree-sitter / Regex-based
- [ ] AST detection working correctly? Yes/No
- [ ] Tree-sitter detection working correctly? Yes/No
- [ ] Root cause: [Parser | Indexing | Blueprint query]
- [ ] Why set literal confused for class: [Explanation]

**Write summary:** Create `INVESTIGATION-3-BLUEPRINT-DUPLICATES.md`

---

## Phase 1 Deliverables

At the end of this phase, produce:

1. **INVESTIGATION-1-SEARCH-DUPLICATES.md**
   - Root cause analysis
   - Code path where duplicates are introduced
   - Proposed fix location and approach

2. **INVESTIGATION-2-SYMBOL-DUPLICATES.md**
   - Root cause analysis (may reference Investigation 1 if same bug)
   - Specific differences from search duplicates if any
   - Proposed fix

3. **INVESTIGATION-3-BLUEPRINT-DUPLICATES.md**
   - Parser bug explanation
   - Examples of false positive class detection
   - Proposed parser fix

4. **INVESTIGATION-SUMMARY.md**
   - Executive summary of all findings
   - Interdependencies between bugs
   - Recommended fix order
   - Risk assessment for each fix

---

## Success Criteria

- [ ] All three duplicate sources completely understood
- [ ] Root causes documented with evidence
- [ ] Fix approaches proposed and reviewed
- [ ] No remaining unknowns about duplication mechanisms
- [ ] Ready to proceed to Phase 2 with confidence

---

## Notes

- Use logging extensively - don't rely on intuition
- Save all test outputs and SQL query results
- If multiple root causes found, document all of them
- If investigations reveal additional bugs, document them for Phase 4
- Do not attempt fixes during this phase - understanding first, fixing second

---

**Next Phase:** PHASE-2-CRITICAL-FIXES.md
