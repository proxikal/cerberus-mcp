# PROTOCOL: SEARCH

**OBJECTIVE:** Locate structure (symbols, files, headings).

**CRITICAL RULE: ALWAYS use search() for finding files and symbols. NEVER use Grep/Glob.**

## What search() Indexes (USE SEARCH FOR THESE)

✅ **Symbol names** (classes, functions, interfaces, methods, etc.)
✅ **File names and paths** (README.md, facade.py, config.json)
✅ **Markdown/RST headings** (## Installation, ### Usage)
✅ **Config file keys** (JSON, YAML, TOML properties)

## What search() Does NOT Index (USE GREP FOR THESE)

❌ **Code body text** (comments, string literals, function bodies)
❌ **Text content INSIDE files** (TODO comments, error messages)

**For text content search:** Use native `Grep -pattern "TODO:"` ONLY for searching INSIDE file contents.

## When to Use What

| Task | ✅ Use | ❌ Don't Use | Example |
|------|--------|--------------|---------|
| Find file by name | `search("facade.py")` | Grep/Glob | `search("facade")` finds all facade files |
| Find symbol | `search("UserConfig")` | Grep/Glob | `search("Config")` finds Config classes |
| Find TODO comments | `Grep -pattern "TODO:"` | search() | Grep searches text INSIDE files |
| Find string literal | `Grep -pattern "error"` | search() | Grep for content, not structure |

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
**Use:** Retrieve symbol by EXACT name with code context.
**Cost:** Low (~400 tokens).
**Params:**
- `name`: Exact symbol name
- `context_lines`: Lines of context (default: 5)

**Examples:**
```
get_symbol(name="parse_config")
get_symbol(name="authenticate", context_lines=10)
```

**Note:** For fuzzy discovery, use `search()` first, then `get_symbol()` for exact retrieval.

## STRATEGY

**EFFICIENT WORKFLOW (Map → Discover → Decide → Retrieve):**

### When exploring unfamiliar code:
1. **Map:** Use `blueprint(path="src/", format="tree")` → See structure (~350 tokens)
2. **Discover:** Use `search(query="auth", limit=5)` → Get metadata (~500 tokens)
3. **Decide:** Review results, pick what you need
4. **Retrieve:** Use `get_symbol(name="authenticate")` → Get exact code (~400 tokens)

### When code is familiar:
1. **Discover:** Use `search(query="auth", limit=5)` → Get metadata (~500 tokens)
2. **Decide:** Review results, pick what you need
3. **Retrieve:** Use `get_symbol(name="authenticate")` → Get exact code (~400 tokens)

## ANTI-PATTERNS (NEVER DO THESE)

❌ **Using Grep to find files:**
```
# WRONG
Grep -pattern "facade.py"
Glob -pattern "**/facade.py"

# RIGHT
search("facade.py")
search("facade")
```

❌ **Using Grep to find symbols:**
```
# WRONG
Grep -pattern "class UserConfig"

# RIGHT
search("UserConfig")
```

❌ **Blindly retrieving everything:**
Don't retrieve all search results - discover first, then retrieve only what you need.
