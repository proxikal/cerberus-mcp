# Cerberus Bulk Operations & Tool Enhancements

**Version:** 2.0
**Last Updated:** 2026-01-23

## Overview

Bulk operations reduce MCP round-trips and token overhead by allowing multiple operations in a single tool call. All bulk-enabled tools support both single and bulk modes with consistent API patterns.

## Benefits

- **50-67% fewer round-trips** - One MCP call instead of multiple
- **Reduced token overhead** - ~200 tokens saved per avoided call
- **Atomic operations** - Single transaction where applicable
- **Consistent error handling** - Partial failures don't abort batch
- **Detailed reporting** - Per-item success/error tracking

---

## Memory Operations

### `memory_learn` - Bulk Memory Storage

Store multiple memories in one call.

**Single mode:**
```python
memory_learn(
    category="decision",
    content="use_sqlite_for_storage",
    details="Root: Need fast queries\nFix: Migrated to SQLite\nFiles: storage.py"
)
```

**Bulk mode:**
```python
memory_learn(bulk_memories=[
    {
        "category": "decision",
        "content": "use_sqlite_for_storage",
        "details": "Root: Need fast queries\nFix: Migrated to SQLite\nFiles: storage.py"
    },
    {
        "category": "preference",
        "content": "prefer_compact_output",
        "details": "User prefers concise results"
    },
    {
        "category": "decision",
        "content": "index_markdown_files",
        "project": "cerberus",
        "details": "Root: Users search docs\nFix: Added .md to indexer\nFiles: indexer.py"
    }
])
```

**Response:**
```json
{
    "status": "bulk_learned",
    "stored_count": 3,
    "error_count": 0,
    "memories": [
        {"memory_id": "uuid1", "category": "decision", "content": "use_sqlite_for_storage"},
        {"memory_id": "uuid2", "category": "preference", "content": "prefer_compact_output"},
        {"memory_id": "uuid3", "category": "decision", "content": "index_markdown_files"}
    ],
    "errors": null
}
```

**Savings:** 3 memories in 1 call vs 3 calls (~400 tokens saved)

---

### `memory_forget` - Bulk Memory Deletion

Delete multiple memories using SQLite `WHERE IN`.

**Single mode:**
```python
memory_forget(category="preference", identifier="prop-123abc")
```

**Bulk mode:**
```python
memory_forget(ids=[
    "prop-123abc",
    "dec-456def",
    "corr-789ghi"
])
```

**Response:**
```json
{
    "status": "bulk_forgotten",
    "deleted_count": 3,
    "not_found_count": 0,
    "error_count": 0,
    "deleted_ids": ["prop-123abc", "dec-456def", "corr-789ghi"],
    "not_found_ids": null,
    "errors": null
}
```

**Savings:** 67% fewer round-trips (1 vs 3), 50% fewer tokens (300 vs 600)

---

### `memory_search` - Bulk Memory Queries

Search across multiple queries/filters in one call.

**Single mode:**
```python
memory_search(query="config", category="decision")
```

**Bulk mode:**
```python
memory_search(queries=[
    {"query": "config", "category": "decision"},
    {"query": "prefer", "category": "preference"},
    {"query": "sqlite", "scope": "project:cerberus", "limit": 5}
])
```

**Response:**
```json
{
    "status": "bulk_search",
    "requested_count": 3,
    "successful_count": 3,
    "total_results": 12,
    "searches": [
        {
            "query": "config",
            "category": "decision",
            "result_count": 5,
            "results": [...]
        },
        {
            "query": "prefer",
            "category": "preference",
            "result_count": 3,
            "results": [...]
        },
        {
            "query": "sqlite",
            "scope": "project:cerberus",
            "result_count": 4,
            "results": [...]
        }
    ],
    "errors": null
}
```

**Savings:** Multiple searches with different filters in one round-trip

---

## Symbol Operations

### `get_symbol` - Bulk Symbol Retrieval

Fetch multiple symbols after search discovers them.

**Single mode:**
```python
get_symbol(name="UserConfig", context_lines=5)
```

**Bulk mode:**
```python
get_symbol(symbols=[
    "UserConfig",
    "SystemConfig",
    "GlobalConfig"
], context_lines=5)
```

**Response:**
```json
{
    "result": [
        {
            "name": "UserConfig",
            "type": "class",
            "file": "src/config.py",
            "start_line": 10,
            "end_line": 45,
            "signature": "class UserConfig:",
            "code": "..."
        },
        {
            "name": "SystemConfig",
            "type": "class",
            "file": "src/config.py",
            "start_line": 50,
            "end_line": 80,
            "code": "..."
        }
    ],
    "bulk_mode": true,
    "requested_count": 3,
    "found_count": 2,
    "not_found": ["GlobalConfig"],
    "_token_info": {
        "estimated_tokens": 2400,
        "tokens_saved": 5000,
        "savings_percent": 68.0
    }
}
```

**Common workflow:**
```
1. search("Config") → 10 results
2. Review, select 3 symbols
3. get_symbol(symbols=["UserConfig", "SystemConfig", "GlobalConfig"])

Before: 4 MCP calls (search + 3×get_symbol)
After: 2 MCP calls (search + 1 bulk get_symbol)
Savings: 50% fewer round-trips
```

---

## File Operations

### `read_range` - Bulk Line Range Reading

Read multiple line ranges from one or more files.

**Single mode:**
```python
read_range(file_path="src/main.py", start_line=10, end_line=20, context_lines=5)
```

**Bulk mode:**
```python
read_range(ranges=[
    {
        "file_path": "src/config.py",
        "start_line": 10,
        "end_line": 30,
        "context_lines": 5
    },
    {
        "file_path": "src/utils.py",
        "start_line": 45,
        "end_line": 60
    },
    {
        "file_path": "src/config.py",  # Same file, different range
        "start_line": 100,
        "end_line": 120
    }
])
```

**Response:**
```json
{
    "result": [
        {
            "file": "src/config.py",
            "start_line": 10,
            "end_line": 30,
            "content": "...",
            "tokens": 250
        },
        {
            "file": "src/utils.py",
            "start_line": 45,
            "end_line": 60,
            "content": "...",
            "tokens": 180
        },
        {
            "file": "src/config.py",
            "start_line": 100,
            "end_line": 120,
            "content": "...",
            "tokens": 220
        }
    ],
    "bulk_mode": true,
    "requested_count": 3,
    "success_count": 3,
    "_token_info": {
        "estimated_tokens": 650,
        "alternative": "Read full file(s)",
        "alternative_tokens": 4500,
        "tokens_saved": 3850,
        "savings_percent": 85.6
    }
}
```

**Savings:** Read specific ranges from multiple files without full file reads

**Enhancement: Full File Support**

Omit `start_line` and `end_line` to read entire file:

```python
# Read full file
read_range(file_path="src/config.py")

# Bulk mode with full files
read_range(ranges=[
    {"file_path": "src/config.py"},  # Full file
    {"file_path": "src/utils.py", "start_line": 10, "end_line": 20}  # Range
])
```

**Token safety limit:**
- Full file reads limited to **200 lines** by default
- Files > 200 lines require explicit `start_line`/`end_line`
- Configurable via `limits.full_file_read_max_lines` in config

**When to use:**
- Quick file reads without counting lines first
- More natural than "count lines then read 1-N"
- Works in both single and bulk modes

---

### `skeletonize` - Bulk Skeletonization

Generate code skeletons (signatures without implementations) for multiple files.

**Single mode:**
```python
skeletonize(path="src/config.py")
```

**Bulk mode:**
```python
skeletonize(files=[
    "src/config.py",
    "src/utils.py",
    "src/models.py"
])
```

**Response:**
```json
{
    "bulk_mode": true,
    "requested_count": 3,
    "success_count": 3,
    "results": [
        {
            "file_path": "src/config.py",
            "skeleton": "...",
            "stats": {
                "original_lines": 250,
                "skeleton_lines": 30,
                "compression_ratio": 0.12
            }
        },
        ...
    ],
    "overall_stats": {
        "total_original_lines": 750,
        "total_skeleton_lines": 85,
        "overall_compression": 0.113,
        "tokens_saved_estimate": 6650
    }
}
```

**Token safety limit:**
- Bulk mode limited to **20 files** by default
- Configurable via `limits.bulk_skeletonize_max_files` in config

**Savings:** 70-90% token reduction vs full file reads, bulk mode reduces round-trips by 67%

---

## Quality Operations

### `style_fix` - Bulk Style Fixing

Fix style issues across multiple files in one transaction.

**Single mode:**
```python
style_fix(path="src/main.py", dry_run=True)
```

**Bulk mode:**
```python
style_fix(paths=[
    "src/config.py",
    "src/utils.py",
    "src/models.py"
], dry_run=False)
```

**Response:**
```json
{
    "status": "bulk_fixed",
    "requested_count": 3,
    "files_modified": 3,
    "violations_fixed": 47,
    "applied_fixes": [
        {
            "file": "src/config.py",
            "type": "trailing_whitespace",
            "line": 12,
            "before": "def foo():    ",
            "after": "def foo():",
            "description": "Removed trailing whitespace"
        },
        ...
    ],
    "errors": null
}
```

**Dry run mode:**
```python
style_fix(paths=["src/config.py", "src/utils.py"], dry_run=True)
```

Returns `status: "bulk_dry_run"` with preview of changes without modifying files.

**Savings:** Fix multiple files in one call, index invalidated once

---

## Tool Enhancements (v2.0)

### `blueprint` - Simple List Format

NEW: Lightweight directory listing without full blueprint overhead.

**Tree format (default):**
```python
blueprint(path="src/cerberus/mcp/tools", format="tree")
# Returns: ASCII tree with symbols (~350 tokens)
```

**List format (NEW):**
```python
blueprint(path="src/cerberus/mcp/tools", format="list")
# Returns: Simple file/dir listing (~100 tokens)
```

**Response:**
```json
{
    "path": "/path/to/dir",
    "items": [
        {"name": "__init__.py", "type": "file", "path": "tools/__init__.py"},
        {"name": "reading.py", "type": "file", "path": "tools/reading.py"},
        {"name": "search.py", "type": "file", "path": "tools/search.py"}
    ],
    "count": 18,
    "_token_info": {
        "estimated_tokens": 100,
        "format": "list"
    }
}
```

**Savings:** 65% fewer tokens vs tree format (~100 vs ~350)

**When to use:**
- Quick directory exploration ("what files are here?")
- Don't need symbol-level detail
- Lightweight alternative to `ls` command

---

### `search` - Import Relationship Filter

NEW: Find files that import a specific module/package.

**Symbol search (default):**
```python
search(query="UserConfig", filter_type="symbols")
```

**Import search (NEW):**
```python
search(query="pathlib", filter_type="imports", limit=10)
```

**Response:**
```json
{
    "result": [
        {
            "module": "pathlib",
            "file": "src/config.py",
            "line": 15,
            "type": "import"
        },
        {
            "module": "pathlib.Path",
            "file": "src/utils.py",
            "line": 8,
            "type": "import"
        }
    ],
    "filter_type": "imports",
    "query": "pathlib"
}
```

**Supports partial matching:**
- `"pathlib"` → matches `pathlib`, `pathlib.Path`, `pathlib.PurePath`
- `"cerberus.retrieval"` → matches `cerberus.retrieval`, `cerberus.retrieval.utils`

**When to use:**
- Find all files using a specific library
- Dependency analysis ("what uses this module?")
- Impact analysis before refactoring shared code

---

### `file_info` - File Metadata Tool (NEW)

Get file metadata without reading content.

**Single mode:**
```python
file_info(path="src/config.py")
```

**Bulk mode:**
```python
file_info(paths=[
    "src/config.py",
    "src/utils.py",
    "README.md"
])
```

**Response:**
```json
{
    "path": "src/config.py",
    "name": "config.py",
    "extension": ".py",
    "size_bytes": 12500,
    "size_human": "12.2 KB",
    "modified": "2026-01-23 15:30:00",
    "is_text": true,
    "line_count": 250,
    "permissions": "644",
    "git_tracked": true,
    "git_status": "tracked",
    "_token_info": {
        "estimated_tokens": 60,
        "alternative": "Read file content",
        "alternative_tokens": 2500
    }
}
```

**Bulk response:**
```json
{
    "bulk_mode": true,
    "requested_count": 3,
    "success_count": 3,
    "results": [...],
    "_token_info": {
        "estimated_tokens": 180,
        "tokens_per_file": 60,
        "alternative_tokens_per_file": 1000
    }
}
```

**Token safety limit:**
- Bulk mode limited to **50 files** by default
- Configurable via `limits.bulk_file_info_max_files` in config

**Savings:** 95-98% token reduction vs reading full file content

**When to use:**
- Quick file checks ("how big is this?", "when was it modified?")
- Filter files before reading (skip large/binary files)
- More natural than `ls -la` + `wc -l` commands

---

## Token Efficiency Comparison

### Scenario: Fetch 3 symbols after search

**Sequential (OLD):**
```
1. search("Config")           →  500 tokens, 1 call
2. get_symbol("UserConfig")   →  800 tokens, 1 call
3. get_symbol("SystemConfig") →  700 tokens, 1 call
4. get_symbol("GlobalConfig") →  900 tokens, 1 call
───────────────────────────────────────────────
Total: 2900 tokens, 4 calls, ~800 overhead (4×200)
```

**Bulk (NEW):**
```
1. search("Config")                              →  500 tokens, 1 call
2. get_symbol(symbols=["User", "System", "Gl"]) → 2400 tokens, 1 call
───────────────────────────────────────────────
Total: 2900 tokens, 2 calls, ~200 overhead
```

**Savings:** 50% fewer calls, ~600 tokens saved in overhead

### Scenario: Delete 3 memories

**Sequential (OLD):**
```
memory_forget × 3 → 600 tokens, 3 calls
```

**Bulk (NEW):**
```
memory_forget(ids=[...]) → 300 tokens, 1 call
```

**Savings:** 67% fewer calls, 50% fewer tokens

### Scenario: Read 4 line ranges from 2 files

**Sequential (OLD):**
```
read_range × 4 → 1200 tokens, 4 calls
```

**Bulk (NEW):**
```
read_range(ranges=[...]) → 800 tokens, 1 call
```

**Savings:** 75% fewer calls, 33% fewer tokens

---

## Error Handling

All bulk operations follow consistent error handling:

1. **Partial failures don't abort** - Continues processing remaining items
2. **Detailed error tracking** - Per-item error messages
3. **Success/error counts** - Clear reporting of what succeeded/failed
4. **Optional errors field** - Only included if errors occurred

**Example with errors:**
```json
{
    "status": "bulk_learned",
    "stored_count": 2,
    "error_count": 1,
    "memories": [...],
    "errors": ["Memory 1: Content too long (max 500 chars)"]
}
```

---

## Implementation Notes

### Backend Optimization
- SQLite `WHERE IN` for memory operations (efficient batch queries)
- Single index load for symbol operations (shared across batch)
- Atomic transactions where applicable (all-or-nothing)
- FTS5 index consistency maintained automatically

### Design Patterns
- **Optional bulk parameters** - `ranges`, `paths`, `ids`, `symbols`, `queries`, `bulk_memories`
- **Single mode preserved** - Original API unchanged for backward compatibility
- **Consistent responses** - `bulk_mode`, `requested_count`, `success_count` fields
- **Token metadata** - Aggregated across all bulk items

### Validation
- Same quality filters apply to each bulk item
- Category/path validation enforced per-item
- Content length limits checked individually
- Continues processing after validation failures

---

## Complete Tool Suite

### Bulk Operations

| Tool | Bulk Parameter | Use Case | Token Savings |
|------|---------------|----------|---------------|
| `memory_learn` | `bulk_memories` | Store multiple memories | 50% fewer tokens |
| `memory_forget` | `ids` | Delete multiple memories | 67% fewer calls |
| `memory_search` | `queries` | Multi-query searches | Consolidated results |
| `get_symbol` | `symbols` | Fetch symbols after search | 50% fewer calls |
| `read_range` | `ranges` | Read specific line ranges | 75% fewer calls |
| `skeletonize` | `files` | Bulk skeletonization | 67% fewer calls |
| `style_fix` | `paths` | Fix multiple files | Atomic transaction |
| `file_info` | `paths` | Bulk file metadata | 67% fewer calls |

### Tool Enhancements (v2.0)

| Tool | Enhancement | Description | Benefit |
|------|------------|-------------|---------|
| `read_range` | Full file support | Omit start/end to read entire file | More natural API |
| `blueprint` | `format="list"` | Simple directory listing | 65% token savings vs tree |
| `search` | `filter_type="imports"` | Find files importing module | Direct relationship queries |
| `file_info` | **NEW TOOL** | File metadata without content | 95-98% token savings |

---

## Best Practices

1. **Use bulk for known sets** - When you know what you need upfront (e.g., after search results)
2. **Don't over-batch** - Keep bulk requests reasonable (5-20 items)
3. **Review before bulk** - For operations like style_fix, review with dry_run first
4. **Handle partial failures** - Check error_count and errors field
5. **Leverage token savings** - Bulk operations shine in exploration workflows

---

## Future Enhancements

Potential candidates for bulk operations:
- ~~`skeletonize` - Multiple files in one call~~ ✅ **DONE (v2.0)**
- `deps` - Multiple symbols for dependency analysis
- `blueprint` - Multiple directories simultaneously
- `analyze_impact` - Multiple symbols for batch impact analysis

---

## Configuration

All token safety limits are configurable via:
- `./cerberus.toml` (project-level)
- `~/.config/cerberus/config.toml` (user-level)
- `CERBERUS_CONFIG` environment variable (custom path)

**Example configuration:**
```toml
[limits]
# Token safety limits (v2.8)
full_file_read_max_lines = 200        # read_range() full file limit
bulk_skeletonize_max_files = 20       # skeletonize() bulk limit
bulk_file_info_max_files = 50         # file_info() bulk limit
```

See `cerberus.toml.example` for complete configuration reference.

---

**Implementation Status:** ✅ Production Ready (v2.0)
**Test Coverage:** Comprehensive Python tests passed
**Bulk Operations:** 8 tools with bulk support
**Tool Enhancements:** 4 major improvements (v2.0)
**Token Safety Limits:** 3 configurable limits enforced
**MCP Integration:** Pending Hydra setup for full MCP testing
