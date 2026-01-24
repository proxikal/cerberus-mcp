# PROTOCOL: READ

**OBJECTIVE:** Ingest code context efficiently.
**CONSTRAINT:** NEVER read full files unless size < 2KB or explicitly required.

## POWER TOOL (USE FIRST)

### `context` ⭐
**Use:** Get EVERYTHING about a symbol in ONE call.
**Efficiency:** Replaces 4-5 tool calls. 70-90% token savings vs full files.
**Returns:** Target code + skeletonized base classes + callers/callees + imports.
**Params:**
- `symbol_name`: Symbol to understand
- `file_path`: Optional disambiguation
- `include_bases`: Include inheritance chain (default: true)
- `include_deps`: Include callers/callees (default: true)

```
context(symbol_name="AuthHandler")
context(symbol_name="parse_config", include_deps=true)
```

**When to use:** Understanding/modifying any class or function. Start here.

## TARGETED TOOLS

Use these when `context` is overkill or you need specific data.

### `blueprint`
**Use:** Read structure (signatures, types) WITHOUT implementation.
**Efficiency:** ~95% token reduction vs full file.
**Params:**
- `path`: File path
- `format`: "tree" or "json"

```
blueprint(path="src/core/auth.py", format="json")
```

### `get_symbol`
**Use:** Read ONLY the specific function/class implementation needed.
**Efficiency:** High.
**Params:**
- `name`: Symbol name
- `context_lines`: Surrounding context (default: 5)

```
get_symbol(name="authenticate_user", context_lines=3)
```

### `read_range`
**Use:** Read specific line range from file.
**Efficiency:** High (when line numbers known).
**Params:**
- `file_path`: Path to file
- `start_line`: Starting line (1-indexed)
- `end_line`: Ending line
- `context_lines`: Additional context (default: 0)

```
read_range(file_path="src/auth.py", start_line=45, end_line=60)
```

### `deps`
**Use:** Understand what a symbol calls and what calls it.
**Params:**
- `symbol_name`: Symbol to analyze
- `file_path`: Optional disambiguation

```
deps(symbol_name="parse_config")
```

### `call_graph`
**Use:** Build recursive dependency graph.
**Params:**
- `symbol_name`: Starting symbol
- `direction`: "callers", "callees", or "both"
- `depth`: Recursion depth (default: 2)

```
call_graph(symbol_name="handle_request", direction="callees", depth=3)
```

## STRATEGY

1. **CONTEXT** for complete understanding of a symbol (preferred).
2. **BLUEPRINT** when you just need structure overview.
3. **GET_SYMBOL** when you only need the implementation, not relationships.
4. **READ_RANGE** when you have specific line numbers (from search results).
5. **DEPS** or **CALL_GRAPH** for deep relationship analysis beyond what `context` provides.
