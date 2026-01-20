# Phase 4: Documentation and Enhancements

**Status:** 🔴 NOT STARTED
**Estimated Duration:** 1 day
**Dependencies:** Phase 3 (Verification) must be complete
**Success Criteria:** P1 documentation complete, P2 features implemented

---

## Overview

This phase implements non-critical improvements identified in the audit:
- **P1:** Documentation of token costs and usage patterns
- **P2:** Directory blueprint support
- **P2:** Compact JSON mode for blueprints

These enhancements improve user experience and prevent misuse, but are not blocking issues.

---

## Enhancement 1: Document Token Costs (P1)

### 1.1: Update Blueprint Tool Docstring

**File:** `src/cerberus/mcp/tools/structure.py`

**Current docstring:**
```python
def blueprint(
    path: str,
    show_deps: bool = False,
    show_meta: bool = False,
    format: str = "tree",
):
    """
    Generate structural blueprint of a file or directory.

    Provides a high-level view of code structure including classes,
    functions, and their relationships.

    Args:
        path: File or directory path to analyze
        show_deps: Include dependency information (imports, calls)
        show_meta: Include metadata (docstrings, line counts)
        format: Output format - "tree" (visual), "json" (structured), "flat" (list)

    Returns:
        Formatted blueprint showing code structure.
    """
```

**Enhanced docstring:**
```python
def blueprint(
    path: str,
    show_deps: bool = False,
    show_meta: bool = False,
    format: str = "tree",
):
    """
    Generate structural blueprint of a file or directory.

    Provides a high-level view of code structure including classes,
    functions, and their relationships.

    **TOKEN EFFICIENCY GUIDE:**

    Format Costs:
    - tree format: ~350 tokens (RECOMMENDED for LLM consumption)
    - json format: ~1,800 tokens (5x more expensive, use only if you need machine-parseable structure)

    Metadata Costs:
    - Basic (show_deps=False, show_meta=False): ~350 tokens
    - With metadata (show_deps=True, show_meta=True): ~1,500 tokens (4x increase)

    Token Limits:
    - max_depth=10: Prevents excessive nesting (automatically applied)
    - max_width=120: Truncates long lines (automatically applied)

    Best Practices:
    - Use tree format for code exploration and understanding
    - Only enable show_deps/show_meta when you need detailed analysis
    - Use json format only for programmatic processing

    Args:
        path: File or directory path to analyze
        show_deps: Include dependency info (calls, imports) - adds ~1000 tokens
        show_meta: Include metadata (complexity, lines, branches) - adds ~1000 tokens
        format: Output format - "tree" (visual, efficient), "json" (verbose, structured)

    Returns:
        Formatted blueprint showing code structure. Format depends on 'format' parameter:
        - tree: ASCII tree visualization (~350 tokens)
        - json: Structured dict with full metadata (~1,800 tokens)
        - flat: Simple list of symbols (~200 tokens)

    Examples:
        # Efficient: Basic tree view
        blueprint(path="file.py", format="tree")
        # ~350 tokens

        # Expensive: Full analysis
        blueprint(path="file.py", format="json", show_deps=True, show_meta=True)
        # ~2,500 tokens

        # Balanced: Tree with dependencies
        blueprint(path="file.py", format="tree", show_deps=True)
        # ~1,200 tokens
    """
```

---

### 1.2: Update Search Tool Docstring

**File:** `src/cerberus/mcp/tools/search.py`

**Add token efficiency notes:**
```python
def search(
    query: str,
    limit: int = 10,
    mode: str = "auto",
) -> List[dict]:
    """
    Search codebase for symbols matching query.

    **TOKEN EFFICIENCY:**
    - Each result: ~80-100 tokens
    - Recommended limit: 5-10 results (~400-1000 tokens)
    - Max limit: 100 results (~8,000-10,000 tokens) - use cautiously

    The limit parameter directly controls token usage:
    - limit=5: ~500 tokens
    - limit=10: ~1,000 tokens
    - limit=20: ~2,000 tokens

    Args:
        query: Search query (keyword or natural language)
        limit: Maximum results to return (default: 10, recommended: 5-10)
        mode: Search mode - "auto", "keyword", "semantic", "balanced"

    Returns:
        List of matching symbols with file paths and line numbers
    """
```

---

### 1.3: Update Get Symbol Docstring

**File:** `src/cerberus/mcp/tools/symbols.py`

**Add token efficiency notes:**
```python
def get_symbol(
    name: str,
    exact: bool = True,
    context_lines: int = 5,
) -> List[dict]:
    """
    Retrieve symbol by name with surrounding code context.

    **TOKEN EFFICIENCY:**
    - Single method: ~400 tokens (includes 5 lines of context)
    - context_lines parameter directly affects token usage:
        - context_lines=0: ~300 tokens (just the symbol)
        - context_lines=5: ~400 tokens (recommended)
        - context_lines=10: ~500 tokens
        - context_lines=20: ~700 tokens

    Best practice: Use context_lines=5 for most use cases.
    Only increase if you need more surrounding code for understanding.

    Args:
        name: Symbol name to find
        exact: If True, exact match only. If False, includes partial matches.
        context_lines: Lines of context before/after symbol (default: 5)

    Returns:
        List of matching symbols with code snippets

    Examples:
        # Efficient: Get symbol with default context
        get_symbol(name="MyClass", exact=True)
        # ~400 tokens

        # Minimal: No context
        get_symbol(name="MyClass", exact=True, context_lines=0)
        # ~300 tokens

        # Detailed: More context (use sparingly)
        get_symbol(name="MyClass", exact=True, context_lines=20)
        # ~700 tokens
    """
```

---

### 1.4: Create User Guide Document

**File:** `docs/TOKEN-EFFICIENCY-GUIDE.md`

```markdown
# Cerberus Token Efficiency Guide

## Overview

Cerberus is designed to minimize token usage while providing comprehensive code intelligence. This guide helps you use Cerberus efficiently.

## Token Costs by Operation

### Search Operations

| Operation | Typical Cost | Notes |
|-----------|-------------|-------|
| `search(query, limit=5)` | ~500 tokens | Recommended default |
| `search(query, limit=10)` | ~1,000 tokens | Good for broader search |
| `search(query, limit=20)` | ~2,000 tokens | Use cautiously |

**Best Practice:** Start with limit=5, increase only if needed.

### Symbol Retrieval

| Operation | Typical Cost | Notes |
|-----------|-------------|-------|
| `get_symbol(name, context_lines=0)` | ~300 tokens | Minimal (signature only) |
| `get_symbol(name, context_lines=5)` | ~400 tokens | Recommended default |
| `get_symbol(name, context_lines=20)` | ~700 tokens | Detailed context |

**Best Practice:** Use context_lines=5 for most cases.

### Blueprint Operations

| Operation | Typical Cost | Notes |
|-----------|-------------|-------|
| `blueprint(path, format="tree")` | ~350 tokens | Most efficient |
| `blueprint(path, format="json")` | ~1,800 tokens | 5x more expensive |
| `blueprint(path, format="tree", show_deps=True)` | ~1,200 tokens | Adds dependency info |
| `blueprint(path, format="tree", show_deps=True, show_meta=True)` | ~1,500 tokens | Full analysis |

**Best Practice:** Use tree format without metadata for exploration.

### Other Operations

| Operation | Typical Cost | Notes |
|-----------|-------------|-------|
| `skeletonize(path)` | ~200 tokens | 70-90% savings vs full file |
| `call_graph(symbol, depth=2)` | ~1,000 tokens | Limited to 100 nodes |
| `related_changes(file, symbol)` | ~500 tokens | Max 5 suggestions |

## Token Saving Strategies

### 1. Use Skeletonization for Large Files

**Instead of:**
```python
# Reading full file (could be 10,000+ tokens)
Read(path="large_file.py")
```

**Do this:**
```python
# Get skeleton first (200-500 tokens)
skeletonize(path="large_file.py")

# Then get specific symbols if needed
get_symbol(name="specific_function", context_lines=5)
```

**Savings:** 90-95% token reduction

---

### 2. Start with Tree Format, Use JSON Only When Needed

**Instead of:**
```python
# JSON for everything (1,800 tokens)
blueprint(path="file.py", format="json")
```

**Do this:**
```python
# Tree format for exploration (350 tokens)
blueprint(path="file.py", format="tree")

# Use JSON only if you need programmatic processing
if need_machine_parsing:
    blueprint(path="file.py", format="json")
```

**Savings:** 80% token reduction

---

### 3. Use Targeted Searches with Low Limits

**Instead of:**
```python
# Broad search with high limit (2,000+ tokens)
search(query="function", limit=20)
```

**Do this:**
```python
# Specific search with low limit (500 tokens)
search(query="specific_function_name", limit=5)
```

**Savings:** 75% token reduction

---

### 4. Disable Metadata Unless Needed

**Instead of:**
```python
# Full metadata (1,500 tokens)
blueprint(path="file.py", show_deps=True, show_meta=True)
```

**Do this:**
```python
# Basic blueprint first (350 tokens)
blueprint(path="file.py")

# Add metadata only if needed for specific analysis
if need_complexity_analysis:
    blueprint(path="file.py", show_meta=True)
```

**Savings:** 75% token reduction

---

## Recommended Workflows

### Workflow 1: Code Exploration

**Efficient approach (~1,000 tokens total):**
1. Search for symbol: `search(query="MyClass", limit=5)` → 500 tokens
2. Get details: `get_symbol(name="MyClass", context_lines=5)` → 400 tokens
3. View structure: `blueprint(path="file.py", format="tree")` → 350 tokens

**Total:** ~1,250 tokens

---

### Workflow 2: Understanding a Function

**Efficient approach (~800 tokens total):**
1. Get function code: `get_symbol(name="my_function", context_lines=5)` → 400 tokens
2. Check callers: `call_graph(symbol="my_function", depth=1, direction="callers")` → 400 tokens

**Total:** ~800 tokens

---

### Workflow 3: File Analysis

**Efficient approach (~1,200 tokens total):**
1. Get skeleton: `skeletonize(path="file.py")` → 300 tokens
2. View structure: `blueprint(path="file.py", format="tree")` → 350 tokens
3. Get specific symbol: `get_symbol(name="interesting_function")` → 400 tokens

**Total:** ~1,050 tokens

---

## Anti-Patterns (Avoid These)

### ❌ Anti-Pattern 1: Always Using JSON Format
```python
# WASTEFUL: JSON for everything
blueprint(path="file.py", format="json")  # 1,800 tokens
```
**Why it's bad:** 5x more expensive than tree format
**Fix:** Use tree format for exploration, JSON only for programmatic parsing

---

### ❌ Anti-Pattern 2: High Search Limits by Default
```python
# WASTEFUL: Always searching with limit=50
search(query="class", limit=50)  # 4,000+ tokens
```
**Why it's bad:** Most of the time you don't need 50 results
**Fix:** Start with limit=5, increase only if needed

---

### ❌ Anti-Pattern 3: Always Enabling All Metadata
```python
# WASTEFUL: Full metadata every time
blueprint(path="file.py", show_deps=True, show_meta=True)  # 1,500 tokens
```
**Why it's bad:** 4x more expensive, usually not needed
**Fix:** Enable metadata only when you need specific analysis

---

### ❌ Anti-Pattern 4: Reading Full Files Instead of Skeletons
```python
# WASTEFUL: Reading full 5000-line file
Read(path="large_file.py")  # 50,000+ tokens
```
**Why it's bad:** Massive token waste for overview
**Fix:** Use skeletonize first, then get specific symbols

---

## Quick Reference

**When to use each tool:**

| Task | Tool | Typical Cost |
|------|------|--------------|
| Find a symbol | search(limit=5) | 500 tokens |
| View symbol code | get_symbol() | 400 tokens |
| Understand file structure | blueprint(format="tree") | 350 tokens |
| Overview of large file | skeletonize() | 300 tokens |
| Find callers/callees | call_graph(depth=1) | 400 tokens |
| Find related changes | related_changes() | 500 tokens |

**Total for typical session:** 1,000-2,000 tokens

---

## Monitoring Your Token Usage

Most LLM interfaces show token usage per request. Monitor your usage and:
- If a query uses >2,000 tokens, consider if you can be more targeted
- Compare actual usage to estimates in this guide
- Adjust parameters (limit, context_lines, format) to optimize

---

## Questions?

If you find token usage higher than expected:
1. Check if you're using recommended defaults
2. Verify no duplicate results (bug)
3. Consider if you need all the data you're requesting

Report issues at: https://github.com/anthropics/cerberus/issues
```

---

## Enhancement 2: Fix Directory Blueprint (P2)

### Current State

**File:** `src/cerberus/blueprint/facade.py:621-629`

```python
# Phase 13.3: Handle aggregated blueprints
if isinstance(blueprint, AggregatedBlueprint):
    if output_format == "json":
        import json
        return json.dumps(blueprint.to_dict(), indent=None)
    else:
        # For tree format, convert to simple string representation
        # TODO: Implement proper tree formatting for aggregated blueprints
        return f"[Package: {blueprint.package_path}] ({blueprint.total_files} files, {blueprint.total_symbols} symbols)"
```

### Option 1: Implement Tree Formatting (Recommended)

**File:** `src/cerberus/blueprint/tree_builder.py`

**Add method:**
```python
def build_aggregated_tree(self, aggregated: AggregatedBlueprint) -> str:
    """
    Build tree representation for aggregated blueprint.

    Shows package structure with file summaries.
    """
    lines = []

    # Header
    lines.append(f"[Package: {aggregated.package_path}]")
    lines.append(f"({aggregated.total_files} files, {aggregated.total_symbols} symbols)")
    lines.append("")

    # List files with symbol counts
    for file_bp in aggregated.files[:20]:  # Limit to first 20 files
        file_name = Path(file_bp.file_path).name
        symbol_count = len(file_bp.nodes)

        lines.append(f"├── {file_name} ({symbol_count} symbols)")

    if aggregated.total_files > 20:
        lines.append(f"└── ... and {aggregated.total_files - 20} more files")

    return "\n".join(lines)
```

**Update facade.py:**
```python
if isinstance(blueprint, AggregatedBlueprint):
    if output_format == "json":
        import json
        return json.dumps(blueprint.to_dict(), indent=None)
    else:
        # Use tree builder for aggregated blueprints
        builder = TreeBuilder(tree_options)
        return builder.build_aggregated_tree(blueprint)
```

---

### Option 2: Return Clear Error (Alternative)

If aggregated blueprints aren't priority:

```python
if isinstance(blueprint, AggregatedBlueprint):
    if output_format == "json":
        import json
        return json.dumps(blueprint.to_dict(), indent=None)
    else:
        return {
            "error": "Directory blueprints with tree format not yet supported",
            "suggestion": "Use format='json' or specify a specific file path",
            "package_info": {
                "path": blueprint.package_path,
                "files": blueprint.total_files,
                "symbols": blueprint.total_symbols
            }
        }
```

### Testing

```python
def test_directory_blueprint_works():
    """Directory blueprints return useful output."""
    result = blueprint(
        path="/Users/proxikal/dev/projects/cerberus/src/cerberus/blueprint",
        format="tree"
    )

    # Should not be empty
    assert len(result) > 0

    # Should mention files/symbols or be clear error
    assert "files" in result or "error" in result
```

---

## Enhancement 3: Compact JSON Mode (P2)

### Implementation

**File:** `src/cerberus/blueprint/formatter.py`

**Add method:**
```python
@staticmethod
def format_as_json_compact(blueprint: Blueprint) -> str:
    """
    Format blueprint as compact JSON (minimal tokens).

    Differences from full JSON:
    - No metadata timestamps
    - No null fields
    - Minimal whitespace
    - Exclude parent_class if None
    """
    symbols_data = []

    for node in blueprint.nodes:
        symbol_dict = {
            "name": node.name,
            "type": node.type,
            "line": node.start_line,
        }

        # Only include signature if present
        if node.signature:
            symbol_dict["signature"] = node.signature

        # Only include parent if present
        if node.parent_class:
            symbol_dict["parent"] = node.parent_class

        # Include methods if it's a class
        if node.methods:
            symbol_dict["methods"] = [
                {"name": m.name, "line": m.start_line}
                for m in node.methods
            ]

        symbols_data.append(symbol_dict)

    result = {
        "file": blueprint.file_path,
        "symbols": symbols_data
    }

    # Minified JSON (no whitespace)
    return json.dumps(result, separators=(',', ':'))
```

**Update facade.py:**
```python
def format_output(self, blueprint, output_format, tree_options=None):
    if output_format == "tree":
        return BlueprintFormatter.format_as_tree(blueprint, tree_options)
    elif output_format == "json":
        return BlueprintFormatter.format_as_json(blueprint, pretty=False)
    elif output_format == "json-compact":
        return BlueprintFormatter.format_as_json_compact(blueprint)
    else:
        raise ValueError(f"Unknown output format: {output_format}")
```

**Update MCP tool:**
```python
@mcp.tool()
def blueprint(
    path: str,
    show_deps: bool = False,
    show_meta: bool = False,
    format: str = "tree",  # Options: tree, json, json-compact
):
```

### Testing

```python
def test_json_compact_smaller_than_full():
    """Compact JSON uses fewer tokens than full JSON."""
    full_json = blueprint(path="file.py", format="json")
    compact_json = blueprint(path="file.py", format="json-compact")

    full_tokens = len(full_json) / 4
    compact_tokens = len(compact_json) / 4

    # Compact should be 40-60% of full JSON
    assert compact_tokens < full_tokens * 0.7
    assert compact_tokens > full_tokens * 0.3
```

---

## Enhancement 4: Add Usage Examples

### Create Example Scripts

**File:** `docs/examples/efficient-search.md`

````markdown
# Efficient Search Examples

## Example 1: Finding a Specific Function

```python
# Step 1: Search with targeted query
results = search(query="parse_arguments", limit=5)

# Step 2: Review results, pick the right one
for r in results:
    print(f"{r['name']} in {r['file']}")

# Step 3: Get full details for chosen symbol
details = get_symbol(name="parse_arguments", exact=True)
print(details[0]['code'])
```

**Token usage:** ~900 tokens total

---

## Example 2: Understanding a Module

```python
# Step 1: Get module structure
structure = blueprint(path="src/mypackage/module.py", format="tree")
print(structure)

# Step 2: Skeletonize to see all signatures
skeleton = skeletonize(path="src/mypackage/module.py")
print(skeleton['skeleton'])

# Step 3: Deep dive on interesting function
details = get_symbol(name="interesting_func", context_lines=10)
```

**Token usage:** ~1,200 tokens total
````

---

## Phase 4 Deliverables

1. **Documentation Updates**
   - [ ] Blueprint tool docstring enhanced
   - [ ] Search tool docstring enhanced
   - [ ] Get symbol docstring enhanced
   - [ ] TOKEN-EFFICIENCY-GUIDE.md created
   - [ ] Example scripts created

2. **Directory Blueprint Feature**
   - [ ] Implementation choice made (tree format or clear error)
   - [ ] Code implemented
   - [ ] Tests added
   - [ ] Documentation updated

3. **Compact JSON Mode**
   - [ ] Compact formatter implemented
   - [ ] MCP tool updated to support format="json-compact"
   - [ ] Tests added
   - [ ] Documentation updated with token comparisons

4. **User Guide Materials**
   - [ ] Token efficiency guide complete
   - [ ] Example workflows documented
   - [ ] Anti-patterns documented
   - [ ] Quick reference guide created

---

## Success Criteria

- [ ] All P1 documentation completed and reviewed
- [ ] Directory blueprint works or returns clear error
- [ ] Compact JSON mode reduces tokens by 40-60% vs full JSON
- [ ] User guide is comprehensive and helpful
- [ ] Examples are practical and demonstrate best practices
- [ ] All new features tested

---

## Optional Enhancements (Time Permitting)

### Add Token Usage Metrics

**File:** `src/cerberus/metrics/token_tracker.py`

Add logging of actual token usage:
```python
class TokenTracker:
    """Track token usage across operations."""

    def log_operation(self, operation, result, metadata):
        """Log operation with estimated token usage."""
        estimated_tokens = len(str(result)) / 4

        logger.info(f"[TOKEN_TRACKER] {operation}: ~{estimated_tokens} tokens")

        # Store in metrics DB
        self.store_metric(
            operation=operation,
            tokens=estimated_tokens,
            timestamp=time.time(),
            **metadata
        )
```

---

### Add Token Usage Dashboard

Create endpoint to view token usage statistics:
```python
@mcp.tool()
def token_stats(period: str = "today"):
    """Get token usage statistics."""
    tracker = TokenTracker()
    stats = tracker.get_stats(period)

    return {
        "period": period,
        "total_operations": stats.operation_count,
        "total_tokens": stats.total_tokens,
        "avg_tokens_per_operation": stats.avg_tokens,
        "by_operation": stats.breakdown,
        "most_expensive": stats.top_operations
    }
```

---

## Final Review

Before marking Phase 4 complete:

1. **Documentation Review**
   - All docstrings accurate and helpful
   - Token estimates match reality
   - Examples work correctly

2. **Feature Testing**
   - Directory blueprints work or error clearly
   - Compact JSON saves significant tokens
   - No regressions introduced

3. **User Feedback**
   - Documentation is clear to target users
   - Examples are practical
   - Token costs are well-explained

---

**End of Phase 4**

After completion, Cerberus will have:
- ✅ All critical duplicate bugs fixed (Phase 2)
- ✅ Comprehensive testing and verification (Phase 3)
- ✅ Clear documentation on token efficiency (Phase 4)
- ✅ Enhanced features for better user experience (Phase 4)
- ✅ Production-ready status

**Recommendation:** Tag release as v2.1.0 after all phases complete.
