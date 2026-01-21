# MCP Tools Reference

Complete reference for all 51 Cerberus MCP tools organized by category.

## Table of Contents

- [Context Assembly](#context-assembly)
- [Search & Discovery](#search--discovery)
- [Code Structure](#code-structure)
- [Reading](#reading)
- [Synthesis](#synthesis)
- [Advanced Analysis](#advanced-analysis)
- [Session Memory](#session-memory)
- [Quality & Validation](#quality--validation)
- [Index Management](#index-management)
- [Diagnostics](#diagnostics)
- [Metrics](#metrics)

---

## Context Assembly

### `context`

**Power tool:** Assembles complete context for a symbol in ONE call.

**Replaces:** search → get_symbol → deps → skeletonize (4-5 calls)

**Parameters:**
- `symbol_name` (required): Name of function/class/method
- `file_path` (optional): Disambiguate if multiple symbols share name
- `include_bases` (default: true): Include skeletonized base classes
- `include_deps` (default: true): Include callers/callees

**Returns:**
- Target symbol's full code
- Skeletonized base classes (if applicable)
- Callers (functions that call this symbol)
- Callees (functions this symbol calls)
- Related imports and type dependencies

**Token cost:** ~1,500 tokens (vs 10,000+ for manual workflow)

**Example:**
```
context(symbol_name="authenticate")
context(symbol_name="User", file_path="src/models/user.py")
context(symbol_name="processPayment", include_bases=true, include_deps=true)
```

**Best for:**
- Understanding how a function works
- Before refactoring
- Reviewing code changes

---

## Search & Discovery

### `search`

Hybrid keyword + semantic search for symbols.

**Parameters:**
- `query` (required): Search term (keyword or natural language)
- `limit` (default: 10): Maximum results
- `mode` (default: "auto"): "keyword", "semantic", or "balanced"

**Returns:**
- List of matching symbols with file paths and line numbers

**Token cost:** ~400-500 tokens for limit=5, ~800-1,000 for limit=10

**Examples:**
```
search(query="authentication", limit=5)
search(query="function that validates email", mode="semantic", limit=10)
search(query="UserModel", mode="keyword", limit=3)
```

**Tips:**
- Start with `limit=5` to minimize tokens
- Use `mode="keyword"` for exact name matches
- Use `mode="semantic"` for "find code that does X"

### `get_symbol`

Retrieve a specific symbol with surrounding code context.

**Parameters:**
- `name` (required): Symbol name to find
- `exact` (default: true): Exact match only (false includes partial matches)
- `context_lines` (default: 5): Lines of context before/after symbol

**Returns:**
- Symbol code with context
- File path and line numbers

**Token cost:** ~400 tokens with default context

**Examples:**
```
get_symbol(name="authenticate", exact=true)
get_symbol(name="process", exact=false, context_lines=10)
```

**Best for:**
- Quick symbol lookup when you know the name
- Getting surrounding context for a function

---

## Code Structure

### `blueprint`

Generate structural view of files or directories.

**Parameters:**
- `path` (required): File or directory path
- `show_deps` (default: false): Include dependency information
- `show_meta` (default: false): Include metadata (docstrings, line counts)
- `format` (default: "tree"): Output format

**Format options:**
| Format | Tokens | Use Case |
|--------|--------|----------|
| `flat` | ~200 | Symbol names only |
| `tree` | ~350 | **Default** - best balance |
| `json-compact` | ~800 | Structured data |
| `json` | ~1,800 | **Avoid** - too verbose |

**Examples:**
```
blueprint(path="src/", format="tree")
blueprint(path="src/auth/service.py", show_deps=true, format="json-compact")
blueprint(path=".", format="flat")
```

**Warning:** `show_deps=true` and `show_meta=true` increase cost by 2-3x

### `skeletonize`

Get code skeleton (signatures without implementation).

**Parameters:**
- `path` (required): File path
- `preserve_symbols` (optional): List of symbols to keep full implementation
- `format` (default: "code"): "code" or "json"

**Returns:**
- Function/class signatures
- Type annotations
- Docstrings (first line only)
- No implementation bodies

**Token savings:** 67-90% vs reading full file

**Examples:**
```
skeletonize(path="src/auth/service.py")
skeletonize(path="src/handlers.py", preserve_symbols=["critical_handler"])
```

**Best for:**
- Understanding API surface without implementation details
- Quick overview of large files

### `skeletonize_directory`

Skeleton view of entire module/package.

**Parameters:**
- `path` (default: "."): Directory path
- `pattern` (default: "**/*.py"): Glob pattern for files
- `format` (default: "summary"): "summary" or "combined"

**Returns:**
- Skeleton of all files in directory
- Summary statistics

**Token savings:** 51% vs reading all files

**Examples:**
```
skeletonize_directory(path="src/core/", format="summary")
skeletonize_directory(path=".", pattern="**/*.ts")
```

---

## Reading

### `read_range`

Read specific line ranges from a file.

**Parameters:**
- `file_path` (required): Path to file
- `start_line` (required): Starting line (1-indexed)
- `end_line` (required): Ending line (1-indexed)
- `context_lines` (default: 0): Additional context lines before/after

**Examples:**
```
read_range(file_path="src/auth.py", start_line=45, end_line=67)
read_range(file_path="main.go", start_line=100, end_line=150, context_lines=5)
```

**Best for:**
- Reading specific sections when you know line numbers
- Following up from search results

### `deps`

Get callers and callees for a symbol.

**Parameters:**
- `symbol_name` (required): Function/method to analyze
- `file_path` (optional): Disambiguate if multiple symbols

**Returns:**
- Callers: Functions that call this symbol
- Callees: Functions this symbol calls
- Imports used by symbol

**Token cost:** ~500-800 tokens

**Examples:**
```
deps(symbol_name="authenticate")
deps(symbol_name="process_payment", file_path="src/payments/service.py")
```

**Best for:**
- Quick dependency check
- Understanding call relationships

### `call_graph`

Build recursive call graph from a symbol.

**Parameters:**
- `symbol_name` (required): Starting symbol
- `depth` (default: 2): How many levels deep (max recommended: 3)
- `direction` (default: "both"): "callers", "callees", or "both"

**Returns:**
- Nodes: All symbols in the graph
- Edges: Call relationships
- Max depth reached flag

**Token cost:**
- depth=1: 100-500 tokens
- depth=2: 500-2,000 tokens
- depth=3+: Exponential growth (**avoid**)

**Examples:**
```
call_graph(symbol_name="main", depth=2, direction="callees")
call_graph(symbol_name="authenticate", depth=1, direction="callers")
```

**Warning:** Filters out built-in functions (print, len, etc.). Limited to 100 nodes and 200 edges.

---

## Synthesis

Synthesis tools are covered under Context Assembly and Code Structure.

---

## Advanced Analysis

### `analyze_impact`

Find what breaks if you change a symbol.

**Parameters:**
- `symbol_name` (required): Symbol to analyze
- `file_path` (optional): Disambiguate

**Returns:**
- List of impacted symbols
- File locations
- Relationship types

**Token cost:** ~1,000-2,000 tokens

**Examples:**
```
analyze_impact(symbol_name="processPayment")
analyze_impact(symbol_name="User", file_path="src/models/user.py")
```

**Best for:**
- Before refactoring
- Understanding blast radius of changes

### `test_coverage`

Find which tests cover a symbol.

**Parameters:**
- `symbol_name` (required): Symbol to check
- `file_path` (optional): Disambiguate

**Returns:**
- Test files that cover this symbol
- Test names
- Coverage type (direct/indirect)

**Token cost:** ~800-1,500 tokens

**Examples:**
```
test_coverage(symbol_name="calculateTotal")
test_coverage(symbol_name="User", file_path="src/models.py")
```

**Best for:**
- Safety check before changes
- Finding existing tests

### `find_circular_deps`

Detect circular import dependencies.

**Parameters:**
- `path` (required): File or directory to analyze

**Returns:**
- List of circular dependency chains
- File paths in each cycle

**Token cost:** ~500-1,000 tokens

**Examples:**
```
find_circular_deps(path="src/")
find_circular_deps(path="src/services/")
```

**Best for:**
- Architecture validation
- Preventing dependency issues

### `diff_branches`

Symbol-level diff between two git branches.

**Parameters:**
- `branch_a` (required): First branch (e.g., "main")
- `branch_b` (required): Second branch (e.g., "feature/auth")
- `file_pattern` (optional): Glob pattern to filter files

**Returns:**
- Added symbols
- Modified symbols
- Deleted symbols
- Change types

**Token cost:** Medium-High (depends on changes)

**Examples:**
```
diff_branches(branch_a="main", branch_b="feature/auth")
diff_branches(branch_a="main", branch_b="develop", file_pattern="src/**/*.py")
```

**Best for:**
- PR review
- Understanding branch differences

### `diff_branches_multi`

Compare multiple feature branches to base branch.

**Parameters:**
- `base_branch` (required): Base branch (e.g., "main")
- `feature_branches` (required): List of feature branches
- `file_pattern` (optional): Filter files

**Returns:**
- Per-branch change summary
- Symbol-level details for each branch

**Token cost:** High (multiple branch comparisons)

**Examples:**
```
diff_branches_multi(
    base_branch="main",
    feature_branches=["feature/auth", "feature/api", "feature/payments"]
)
```

**Best for:**
- Multi-feature comparison
- Release planning

### `check_pattern`

Verify code follows project conventions.

**Parameters:**
- `pattern` (required): Pattern type ("error_handling", "logging", "naming")
- `path` (required): File or directory to check

**Returns:**
- Violations with locations
- Suggested fixes

**Token cost:** ~800-1,200 tokens

**Examples:**
```
check_pattern(pattern="error_handling", path="src/")
check_pattern(pattern="logging", path="src/services/payment.py")
```

**Best for:**
- Code quality validation
- Convention enforcement

### `validate_architecture`

Enforce architectural rules.

**Parameters:**
- `rules` (required): Architecture rules to validate
- `path` (required): Path to validate

**Returns:**
- Rule violations
- Severity levels
- Locations

**Token cost:** ~1,000-2,000 tokens

**Examples:**
```
validate_architecture(
    rules=["no_circular_imports", "layer_separation"],
    path="src/"
)
```

**Best for:**
- Architecture compliance
- Preventing design violations

### `project_summary`

80/20 overview of new codebase.

**Parameters:**
- `path` (default: "."): Project root
- `focus` (optional): Focus area ("architecture", "patterns", "tech_stack")

**Returns:**
- High-level summary
- Key components
- Patterns and technologies
- Project structure

**Token cost:** ~2,000-3,000 tokens (but 80%+ savings vs full exploration)

**Examples:**
```
project_summary()
project_summary(path=".", focus="architecture")
```

**Best for:**
- First time exploring new codebase
- Getting quick overview

### `related_changes`

Predict what else needs updating after modifying code.

**Parameters:**
- `file_path` (required): File being modified
- `symbol_name` (optional): Specific symbol (uses filename stem if not provided)

**Returns:**
- Suggested files/symbols to update
- Confidence scores
- Relationship types

**Token cost:** ~500-800 tokens

**Examples:**
```
related_changes(file_path="src/auth.py", symbol_name="authenticate")
related_changes(file_path="src/handlers/user.py")
```

**Best for:**
- After editing code
- Catching ripple effects

---

## Session Memory

### `memory_learn`

Store preference, decision, or correction.

**Parameters:**
- `category` (required): "preference", "decision", or "correction"
- `content` (required): What to remember
- `project` (optional): Project name (auto-detected for decisions)
- `metadata` (optional): Additional structured data

**Storage:**
- `preference` → Global (~/.cerberus/memory/)
- `decision` → Project-specific (.cerberus/memory/)
- `correction` → Global (~/.cerberus/memory/)

**Examples:**
```
memory_learn(category="decision", content="Uses Factory pattern for handlers")
memory_learn(category="correction", content="Always validate input in controllers")
memory_learn(category="preference", content="Prefer early returns over nested ifs")
```

### `memory_context`

Generate context for current task. **Call at session start.**

**Parameters:**
- `project` (optional): Project name (auto-detected)
- `compact` (default: true): Concise output

**Returns:**
- Global preferences
- Project-specific decisions
- Global corrections

**Token cost:** ~200-500 tokens

**Example:**
```
memory_context(compact=true)
```

### `memory_show`

View all stored memory.

**Parameters:**
- `category` (optional): Filter by type
- `project` (optional): Project name

**Examples:**
```
memory_show()
memory_show(category="decisions", project="myapp")
memory_show(category="preferences")
```

### `memory_stats`

Storage statistics.

**Returns:**
- Count of preferences
- Count of decisions (per-project)
- Count of corrections
- Storage paths

**Example:**
```
memory_stats()
```

### `memory_forget`

Remove specific memory entry.

**Parameters:**
- `category` (required): Entry type
- `identifier` (required): Content to remove
- `project` (optional): For decisions

**Examples:**
```
memory_forget(category="preference", identifier="outdated rule")
memory_forget(category="decision", identifier="old pattern", project="myapp")
```

### `memory_export`

Export all memory for backup or sharing.

**Parameters:**
- `output_path` (optional): Export file path (default: cerberus-memory-export-YYYYMMDD.json)

**Examples:**
```
memory_export()
memory_export(output_path="/backup/memory.json")
```

### `memory_import`

Import memory from backup.

**Parameters:**
- `input_path` (required): Path to export JSON file
- `merge` (default: true): Merge with existing (false = replace)

**Examples:**
```
memory_import(input_path="/backup/memory.json")
memory_import(input_path="/backup/memory.json", merge=false)
```

### `memory_extract`

Extract patterns from git history automatically.

**Parameters:**
- `path` (default: "."): Path to git repository
- `lookback_days` (default: 30): Days of history to analyze

**Returns:**
- Learned patterns from commit history
- Statistics

**Examples:**
```
memory_extract()
memory_extract(lookback_days=60)
```

**Best for:**
- Batch learning from project history
- Onboarding to new project

---

## Quality & Validation

### `style_check`

Check code for style violations.

**Parameters:**
- `path` (required): File or directory
- `rules` (optional): Specific rules to check
- `fix_preview` (default: false): Preview auto-fixes

**Returns:**
- Violation count
- Violations (limited to first 30)
- Truncated flag if more exist

**Token cost:** Low-Medium (limited output)

**Examples:**
```
style_check(path="src/auth.py")
style_check(path="src/", fix_preview=true)
```

**Iterative workflow:**
1. `style_check` → See first 30 violations
2. `style_fix` → Fix automatically
3. `style_check` → Re-check remaining
4. Repeat until clean

### `style_fix`

Auto-fix style violations.

**Parameters:**
- `path` (required): File or directory
- `rules` (optional): Specific rules to fix
- `dry_run` (default: false): Preview only
- `create_backup` (default: true): Backup before modifying

**Returns:**
- Files modified count
- Violations fixed count
- Applied fixes list

**Examples:**
```
style_fix(path="src/auth.py", dry_run=true)
style_fix(path="src/auth.py")
style_fix(path="src/", rules=["naming", "formatting"])
```

---

## Index Management

### `health_check`

MCP server + index status.

**Returns:**
- Status: healthy or error
- Context: project or general
- Index availability
- Memory status
- Recommendations

**Example:**
```
health_check()
```

### `index_status`

Index health and statistics.

**Returns:**
- Index path
- File count
- Symbol count
- Index size

**Example:**
```
index_status()
```

### `index_build`

Rebuild entire index.

**Parameters:**
- `path` (default: "."): Directory to index
- `extensions` (optional): File extensions to include

**Examples:**
```
index_build(path=".")
index_build(path="src/", extensions=[".py", ".js"])
```

**When to use:** First time in project or after corruption

### `smart_update`

Git-aware incremental index update.

**Parameters:**
- `force_full` (default: false): Force full re-parse

**Returns:**
- Strategy used (surgical, incremental, or full_reparse)
- Files reparsed
- Updated symbols count
- Elapsed time

**Examples:**
```
smart_update()
smart_update(force_full=true)
```

**When to use:** After editing files (10x faster than full rebuild)

### `index_auto_update`

Toggle file watcher for auto-updates.

**Parameters:**
- `enabled` (optional): True to enable, False to disable, None to query

**Examples:**
```
index_auto_update(enabled=true)
index_auto_update()  # Query current status
```

### `index_watcher`

Get file watcher status and configuration.

**Returns:**
- Auto-update enabled status
- Debounce settings
- Watched file extensions

**Example:**
```
index_watcher()
```

---

## Diagnostics

See `health_check` under Index Management.

---

## Metrics

### `metrics_report`

Efficiency metrics and patterns.

**Parameters:**
- `period` (default: "session"): "session", "today", "week", or "all"
- `detailed` (default: false): Include detailed breakdowns

**Returns:**
- Retrieval counts
- Usage patterns
- Efficiency suggestions

**Examples:**
```
metrics_report(period="session")
metrics_report(period="week", detailed=true)
```

### `metrics_status`

Metrics collection status.

**Returns:**
- Collection enabled status
- Storage path
- Session start time
- Commands this session

**Example:**
```
metrics_status()
```

### `metrics_clear`

Reset metrics data.

**Parameters:**
- `confirm` (default: false): Must be true to actually clear

**Example:**
```
metrics_clear(confirm=true)
```

---

## Summary Statistics

- **Total tools:** 51
- **Categories:** 11
- **Token savings:** 70-95% across workflows
- **Languages supported:** Python, JavaScript/TypeScript, Go, Markdown

---

## Next Steps

- **[Token Efficiency](Token-Efficiency)** - Understand the savings
- **[Quick Start](Quick-Start)** - See tools in action
- **[Advanced Analysis](Advanced-Analysis)** - Deep dive on Phase 4 features
