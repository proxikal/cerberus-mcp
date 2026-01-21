# PROTOCOL: SEARCH

**OBJECTIVE:** Locate specific symbols or text patterns.

## MCP TOOLS

### 1. `search`
**Use:** Semantic/hybrid symbol search (Best for "where is logic for X?").
**Cost:** Low.
**Params:**
- `query`: Search query (keyword or natural language)
- `limit`: Max results (default: 10)
- `mode`: "auto", "keyword", "semantic", "balanced"

**Examples:**
```
search(query="authentication handler", limit=5)
search(query="parse_config", mode="keyword")
```

### 2. `get_symbol`
**Use:** Find and retrieve specific symbol by name.
**Cost:** Low.
**Params:**
- `name`: Symbol name
- `exact`: Exact match only (default: true)
- `context_lines`: Lines of context (default: 5)

**Examples:**
```
get_symbol(name="parse_config", exact=true)
get_symbol(name="auth", exact=false, context_lines=10)
```

## STRATEGY

1. **UNKNOWN LOCATION:** Use `search` to find relevant files.
2. **KNOWN SYMBOL:** Use `get_symbol` for direct lookup.
3. **EXACT TEXT:** Use `search(mode="keyword")` for literal matches.
