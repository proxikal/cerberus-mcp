---
name: Cerberus
description: Specialized codebase navigation - indexes structure (symbols, files, headings), assembles context, traces dependencies. Use Grep for text content search.
---

# CERBERUS AGENT SKILL

**ROLE:** Codebase Navigator (MCP-powered)
**GOAL:** Maximize token efficiency. Eliminate unnecessary file reads.

## CONTEXT-AWARE OPERATION

Cerberus adapts based on your working directory:

### 🌍 General Context (brainstorming, notes, non-code directories)
- ✅ **Memory tools ALWAYS available** - preferences, corrections, learning
- ❌ **Index/search tools skipped** - no project markers detected (.git, go.mod, package.json, etc.)
- **Use for:** brainstorming, note-taking, concept work, image generation

### 📁 Project Context (has .git, go.mod, package.json, pyproject.toml, Cargo.toml, etc.)
- ✅ **Full Cerberus toolset** - memory + exploration + search + analysis
- ✅ **Index automatically available** or can be built
- **Use for:** code development, refactoring, architecture work

**Check context:** `health_check()` tells you which mode you're in and what's available.

### 📦 Indexed File Types (Project Context)
**Code:** `.py`, `.ts`, `.js`, `.go`, `.tsx`, `.jsx`
**Docs:** `.md`, `.txt`, `.rst` (phase files, notes, documentation)
**Configs:** `.json`, `.yaml`, `.yml`, `.toml`, `.ini`
**Scripts:** `.sh`, `.bash`

All these file types are indexed and searchable by filename, symbols, and headings.

## MANDATORY RULES

1. **ALWAYS call `memory_context()` at session start** - Loads preferences + project decisions
2. **ONLY call `memory_learn()` for EXPLICIT user preference statements** ("I prefer X", "don't use Y")
   - Batch processing (session end) catches everything else automatically
   - See [memory.md](./patterns/memory.md) for gates/guardrails
3. **Check `health_check()`** - Tells you project vs general context and available tools
4. **Use specialized tools for their purpose:**
   - `search()` for structure (symbols, files, headings)
   - `context()` for symbol assembly (code + deps + inheritance)
   - `deps()`/`call_graph()` for relationships (callers/callees)
   - `Grep` for text content (TODO, string literals, regex patterns)
5. **Use `context()` instead of multi-step workflows** - ONE call replaces 4-5 separate tool calls
6. **Follow discover → decide → retrieve** - Search metadata first, then retrieve only what you need
7. **Use `blueprint()` before search in unfamiliar code** - Maps structure first, prevents wasted searches

## MCP SERVER DEVELOPMENT RULES

**CRITICAL: When working on Cerberus or any MCP server code:**

### ❌ NEVER Manually Restart MCP Servers
- **DON'T use:** `pkill -f cerberus`, `killall`, manual process killing
- **WHY:** Kills the entire Claude Code session, loses all context
- **Hydra exists to prevent this** - it supervises MCP servers and restarts them gracefully

### ✅ ALWAYS Use Hydra Tools Instead

Hydra is supervising Cerberus MCP. When you make code changes, use these tools:

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `hydra_restart` | Graceful restart of MCP server | After code changes to Cerberus |
| `hydra_force_restart` | Force restart if server stuck | If graceful restart fails |
| `hydra_status` | Check server health | Verify MCP server is running |
| `hydra_logs` | View recent server logs | Debug MCP issues |

**Example workflow:**
```
1. Edit Cerberus code (memory.py, symbols.py, etc.)
2. Call hydra_restart(server="cerberus")  ← This picks up changes
3. Continue working (session stays alive)
```

**Why this matters:**
- Hydra maintains the MCP protocol connection
- Session context preserved
- No need to restart Claude Code
- Changes picked up automatically

**If Hydra tools aren't available:**
- You're likely not in a Hydra-managed session
- Fall back to Python testing: `python3 -c "from cerberus.mcp.tools..."`
- Inform user that Hydra integration may need setup

## TOOL SPECIALIZATION (Intentional Architecture)

**Cerberus uses specialized tools for different tasks. Each tool does what it does best:**

| Task | Tool | Why This Tool | Example |
|------|------|---------------|---------|
| **Find structure** | `search()` | Indexes symbols, files, headings | `search("Config")` |
| **Get full context** | `context()` | Assembles symbol + deps + inheritance | `context("UserService")` |
| **Find relationships** | `deps()` / `call_graph()` | Traces callers/callees | `deps("login")` |
| **Search text content** | Native `Grep` | Regex through code bodies | `Grep -pattern "TODO:"` |

### `search()` - Structure Discovery
**What it indexes:** Symbol names, filenames, signatures, headings
**Use for:**
- Filenames: `search("main.go")`, `search("cli.py")`
- Symbols: `search("Config")`, `search("UserService")`
- Headings: `search("Installation")`

**IMPORTANT - Query Guidelines:**
✅ **GOOD (Specific terms):**
- `search("config.py")` - filename
- `search("UserConfig")` - class name
- `search("CerberusPaths")` - exact symbol
- `search("get_user_config")` - function name

❌ **BAD (Natural language):**
- `search("config path directory")` - too generic, returns empty
- `search("where is configuration")` - natural language fails
- `search("find the settings")` - use specific terms instead

**If search returns empty:** Try breaking query into specific terms (filenames, class names, function names).

### `context()` - Full Symbol Assembly
**What it does:** ONE call gets symbol code + base classes + callers/callees + imports
**Use for:**
- Getting complete understanding of a symbol
- Replacing multi-step workflows (search → get_symbol → deps → skeletonize)

### `deps()` / `call_graph()` - Relationship Tracing
**What it does:** Finds what calls this symbol (callers) and what this symbol calls (callees)
**Use for:**
- Understanding dependencies
- Impact analysis before refactoring

### Native `Grep` - Text Content Search
**What it does:** Regex search through actual code bodies
**Use for:**
- Comment markers: `TODO`, `FIXME`, `XXX`
- String literals: `Grep -pattern "error message"`
- Function calls: `Grep -pattern "fmt.Println"`
- Any text pattern in code bodies

**Why this design:** FTS5 excels at structured data (symbols), Grep excels at regex content search. Using each for its strength = faster, more precise, lower tokens.

## TOOL PRIORITY

**CRITICAL RULE: ALWAYS use Cerberus search() for finding files and symbols. NEVER use Grep/Glob for this.**

**When to use what:**

| Your Goal | ✅ USE THIS | ❌ NEVER USE | Why |
|-----------|------------|-------------|-----|
| Find files by name | `search("main.go")` or `search("facade")` | Grep/Glob | Cerberus indexes filenames in FTS5 - instant, accurate results |
| Find symbols (classes/functions) | `search("Config")` | Grep/Glob | Indexed symbols, 95% fewer false matches |
| Get symbol with full context | `context("UserService")` | Read | ONE call vs 4-5 native tool calls |
| Map codebase structure | `blueprint()` | ls/tree | Tree view, 70% token savings vs Read |
| Find relationships (who calls what) | `deps()`, `call_graph()` | Grep | Indexed call graph |
| Search text INSIDE code bodies | `Grep -pattern "TODO:"` | search() | Grep for regex content, search() for structure |
| Edit/write files | `Edit`, `Write` | - | Native tools work perfectly |

**Key principle:**
- **Cerberus `search()`** for WHAT exists (files, symbols, headings)
- **Grep** for WHERE text appears (content INSIDE files)
- **deps()** for HOW things relate (relationships)

**Search Query Tips:**
- ✅ Use specific terms: `"cli.py"`, `"UserConfig"`, `"get_config"`
- ❌ Avoid natural language: `"config path directory"`, `"where is the config"`
- If empty results → try specific filenames or symbol names

## POWER TOOLS (Use These First)

| Tool | Replaces | Usage |
|------|----------|-------|
| `context` | search → get_symbol → deps → skeletonize | **ONE call** for everything: symbol code + base classes + callers/callees + imports. 4-5x fewer calls, 70-90% token reduction. |
| `smart_update` | Full `index_build` | Git-aware incremental update. 10x faster during development. |
| `memory_context` | Manual context gathering | Loads global preferences + project decisions. Call at session start. |

## BULK OPERATIONS (50-67% Fewer Round-Trips)

**8 tools support bulk mode** - Multiple operations in ONE MCP call. Use when you know what you need upfront.

| Tool | Bulk Parameter | Example Use Case |
|------|---------------|------------------|
| `get_symbol` | `symbols=[...]` | Fetch 3 symbols after search → 2 calls instead of 4 |
| `read_range` | `ranges=[...]` | Read line ranges from multiple files → 1 call vs many |
| `skeletonize` | `files=[...]` | Bulk skeletonization → 67% fewer calls |
| `memory_learn` | `bulk_memories=[...]` | Store multiple memories → 3 in 1 call |
| `memory_forget` | `ids=[...]` | Delete multiple memories → 67% fewer calls |
| `memory_search` | `queries=[...]` | Multi-query with different filters → consolidated |
| `style_fix` | `paths=[...]` | Fix multiple files → atomic transaction |
| `file_info` | `paths=[...]` | Bulk file metadata → 95% token savings vs Read |

**See:** `BULK-OPERATIONS.md` in project root for complete API reference, examples, and token savings analysis.

## MCP TOOLS (52 total)

### Context Assembly (START HERE)
| Tool | Purpose | Token Cost |
|------|---------|------------|
| `context` | **Power tool:** Symbol + inheritance + deps + imports in ONE call | ~1,500 tokens (vs 10,000+ for manual) |

### Exploration → [explore.md](./patterns/explore.md)
| Tool | Purpose | Token Cost |
|------|---------|------------|
| `blueprint` | Structural tree view of file/directory. **Enhancement:** `format="list"` for simple listing (~100 tokens) | 200-800 tokens |
| `skeletonize` | Function signatures without bodies. **Bulk:** `files=[...]` (20 file limit) | 67% savings vs `Read` |
| `skeletonize_directory` | Skeleton view of entire module | 51% savings |

**Note:** `blueprint` handles both absolute and relative paths (fixed: database path inconsistency handling).

### Search & Discovery → [search.md](./patterns/search.md)
| Tool | Purpose | Notes |
|------|---------|-------|
| `search` | Find files + symbols (code, markdown headings). **Enhancement:** `filter_type="imports"` finds import relationships | `search("README")` → finds README.md |
| `get_symbol` | Retrieve symbol with surrounding context | Use `context_lines=5` default. **Bulk:** `symbols=[...]` |

### Reading → [read.md](./patterns/read.md)
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `read_range` | Read specific line ranges. **Enhancement:** Omit start/end for full file (200 line limit) | When you know exact lines. **Bulk:** `ranges=[...]` |
| `file_info` | File metadata without content (size, lines, git status) | Quick file checks. **Bulk:** `paths=[...]` (50 file limit) |
| `deps` | Get callers + callees for symbol | Quick dependency check |
| `call_graph` | Recursive dependency graph | Multi-level tracing (use `depth=1-2`) |

### Advanced Analysis → [advanced-analysis.md](./patterns/advanced-analysis.md)
| Tool | Purpose | Use Case |
|------|---------|----------|
| `analyze_impact` | What breaks if you change this symbol? | Before refactoring |
| `test_coverage` | Which tests cover this code? | Safety check before changes |
| `find_circular_deps` | Detect import cycles | Architecture validation |
| `diff_branches` | Symbol-level diff between branches | PR review, merge prep |
| `diff_branches_multi` | Compare multiple branches to base | Feature comparison |
| `check_pattern` | Verify code follows project conventions | Code quality |
| `validate_architecture` | Enforce structural rules | Architecture compliance |
| `project_summary` | 80/20 overview of new codebase | Session startup for new projects |
| `related_changes` | Predict what else needs updating | After modifying code |

### Quality & Style → [quality.md](./patterns/quality.md)
| Tool | Purpose | Notes |
|------|---------|-------|
| `style_check` | Detect style violations | Use `fix_preview=True` to see fixes |
| `style_fix` | Auto-fix style issues | Use `dry_run=True` first. **Bulk:** `paths=[...]` |

### Session Memory → [memory.md](./patterns/memory.md)
**Batch (PRIMARY) at session end + Real-time (SUPPLEMENTAL) for explicit statements**

| Tool | Purpose |
|------|---------|
| `memory_learn` | Store preference/decision/correction. **Bulk:** `bulk_memories=[...]` |
| `memory_propose` | Manually trigger batch memory collection |
| `memory_context` | **Load at session start** (MANDATORY) |
| `memory_show` | View stored memories |
| `memory_search` | FTS5 search across memories. **Bulk:** `queries=[...]` |
| `memory_stats` | Storage statistics |
| `memory_forget` | Remove entry. **Bulk:** `ids=[...]` |
| `memory_export` / `memory_import` | Backup/restore |
| `memory_extract` | Learn from git history |

See [memory.md](./patterns/memory.md) for gates/guardrails and detailed usage.

### Index & Diagnostics
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `health_check` | MCP server + index status | If tools fail or slow |
| `index_status` | Index health stats | Verify index is current |
| `index_build` | Rebuild entire index | First time or corruption |
| `smart_update` | Git-aware incremental update | **Use this during development** (10x faster) |
| `index_auto_update` | Toggle file watcher | Enable for active development |
| `index_watcher` | Watcher status | Check if auto-update working |

### Metrics
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `metrics_report` | Efficiency metrics + patterns | Optimize workflow |
| `metrics_status` | Metrics collection status | Verify tracking |
| `metrics_clear` | Reset metrics data | Fresh start |

## PROTOCOLS

1. **[EXPLORE](./patterns/explore.md)** → `blueprint`, `skeletonize`
2. **[SEARCH](./patterns/search.md)** → `search`, `get_symbol`
3. **[READ](./patterns/read.md)** → `context`, `get_symbol`, `read_range`, `deps`
4. **[MEMORY](./patterns/memory.md)** → `memory_*` tools
5. **[QUALITY](./patterns/quality.md)** → `style_check`, `style_fix`, `related_changes`
6. **[ADVANCED ANALYSIS](./patterns/advanced-analysis.md)** → `analyze_impact`, `test_coverage`, `diff_branches`, etc.

## CORE LOOP (Token-Optimized Workflow)

### Project Context (Code Development)
```
1. memory_context()               → Load preferences + decisions (200-500T)
2. health_check()                 → Verify project context + index status
3. blueprint(path=".", format="tree") → Map structure (350T)
4. search(query="...", limit=5)   → Locate target (400-500T)
5. context(symbol_name="...")     → Get EVERYTHING in ONE call (1,500T)
   ↳ Replaces: skeletonize → get_symbol → deps → read bases
6. [Native] Edit/Write            → Modify code
7. smart_update()                 → Update index incrementally
8. [Real-time] memory_learn()     → IMMEDIATELY when user states preference/correction
```

**Old way (5-10 calls, 10,000+ tokens):** blueprint → search → get_symbol → deps → skeletonize → read → read → read
**New way (5 calls, ~2,500 tokens):** memory_context → health_check → blueprint → search → context

**Memory learning happens automatically at session end via bash hook** - you don't need to do anything.

### General Context (Brainstorming, Notes)
```
1. memory_context()               → Load global preferences (200-500T)
2. health_check()                 → Confirm general context (memory-only mode)
3. [Work with native tools]       → Read, Write, Edit as needed
4. [Real-time] memory_learn()     → IMMEDIATELY when user states preference
```

**No accidental indexing** - Index tools gracefully skipped in general context

## TOKEN EFFICIENCY RULES

### Blueprint Format Costs
| Format | Tokens | Use Case |
|--------|--------|----------|
| `flat` | ~200 | Symbol names only |
| `tree` | ~350 | **Default** - best balance |
| `json-compact` | ~800 | Need structured data |
| `json` | ~1,800 | **Avoid** - use json-compact instead |

### Search Best Practices
- **Finds:** filenames (`README`), symbols (`parse_file`), markdown headings (`## Installation`)
- Start with `limit=5` (400-500 tokens)
- `limit=10` → 800-1,000 tokens
- `limit=20` → 1,600-2,000 tokens
- Each result ≈ 80-100 tokens

### Context Assembly
- `context()` with defaults → ~1,500 tokens (includes everything)
- vs manual workflow → 10,000+ tokens
- **Always use context() first**

### Flags That Increase Cost
- `show_deps=True` → +1,000 tokens
- `show_meta=True` → +1,000 tokens
- Both together → 2-3x cost increase
- **Only enable when explicitly needed**

### Call Graph Depth
- `depth=1` → 100-500 tokens (immediate deps)
- `depth=2` → 500-2,000 tokens (transitive deps)
- `depth=3+` → **Exponential growth, avoid**

## TOOL SELECTION GUIDE

**Before picking a tool, identify your task:**

| What I Need | First Choice | Why |
|-------------|-------------|-----|
| Check if project has index | `health_check()` | Shows context + available tools |
| Find where symbol is defined | `search("SymbolName")` | Indexed symbols, fast |
| Understand a symbol completely | `context("SymbolName")` | ONE call gets everything |
| See file/directory structure | `blueprint()` | Tree view, efficient |
| Find who calls a function | `deps("functionName")` | Indexed call graph |
| Search for text in code | `Grep -pattern "text"` | Regex content search |
| Modify code | `Edit` or `Write` | Standard file operations |

**Quick decision tree:**
1. Searching for structure (files/symbols/headings)? → `search()`
2. Need full symbol context? → `context()`
3. Tracing dependencies? → `deps()` or `call_graph()`
4. Searching text content in code bodies? → `Grep`
5. Editing/writing? → `Edit` / `Write`

## CORE WORKFLOW DISCIPLINE

**Every code exploration follows this sequence:**

1. **DISCOVER** what exists → `search()` returns metadata only
2. **DECIDE** which one(s) you actually need → Review and select
3. **RETRIEVE** only what you need → `get_symbol()` or `context()`

**Why this matters:**
- Blindly retrieving everything wastes 5-10x tokens
- Metadata discovery is cheap (~100 tokens/result)
- Full code retrieval is expensive (~1-3k tokens/symbol)
- **Always discover before retrieving**

**Example - Finding authentication:**
```
❌ WRONG (anti-pattern - no longer possible):
   Blindly retrieve all fuzzy matches without reviewing
   → Would have been 10,000+ tokens for symbols you don't need

✅ RIGHT (efficient workflow):
   1. search("auth", limit=10) → 10 results × 100 = 1,000 tokens
   2. [Review: pick authenticate() and authorize()]
   3. get_symbol("authenticate") + get_symbol("authorize") = 800 tokens
   Total: 1,800 tokens vs 10,000+ (5.5x more efficient)
```

**This is non-negotiable.** Cerberus exists to prevent token bloat - don't defeat its purpose.

## COMMON MISTAKES

1. ❌ **Not calling `memory_context()` at session start**
   - ✅ First tool call should be `memory_context()` (works in ALL contexts)

2. ❌ **Not checking context before using exploration tools**
   - ✅ Call `health_check()` to see if you're in project or general context
   - ✅ In general context, only memory tools are available (this prevents accidental indexing)

3. ❌ **Searching without mapping structure first**
   - ✅ Use `blueprint()` when exploring unfamiliar modules or directories
   - ✅ Maps layout before search, prevents wasted queries

4. ❌ **Reading full files when you only need signatures**
   - ✅ Use `skeletonize()` to see structure without implementation (67% token savings)
   - ✅ Then `get_symbol()` or `context()` only for what you need

5. ❌ **Using native `Read` when you just need symbol (in project context)**
   - ✅ Use `context()` or `get_symbol()`

6. ❌ **Calling tools separately when `context()` does it all**
   - ✅ Use `context()` for: code + bases + deps + imports

7. ❌ **Using `index_build` during development**
   - ✅ Use `smart_update()` (10x faster, git-aware)

8. ❌ **Not capturing preferences in real-time**
   - ✅ When user says "I prefer X", "I like Y" → IMMEDIATELY call `memory_learn()`
   - ✅ Don't wait for session end - capture as preferences emerge
   - ✅ Use hybrid format: `content="semantic_code"` + `details="Root/Fix/Files"`

9. ❌ **Using `format="json"` by default**
   - ✅ Use `format="tree"` or `format="json-compact"`

10. ❌ **High search limits without need**
    - ✅ Start with `limit=5`, increase only if needed

11. ❌ **Enabling `show_deps`/`show_meta` unnecessarily**
    - ✅ Only enable when you need that specific information

12. ❌ **Over-using real-time `memory_learn()` instead of letting batch process**
    - ✅ Only call for EXPLICIT user statements ("I prefer X")
    - ✅ Don't try to "help" by capturing implied preferences
    - ✅ Trust batch processing to catch everything at session end

13. ❌ **Using Grep or Glob to find files instead of Cerberus search()**
    - ✅ Finding files by name: `search("facade.py")` or `search("facade")`
    - ✅ Finding symbols: `search("UserConfig")`
    - ❌ NEVER use `Grep -pattern "facade.py"` or `Glob -pattern "**/facade.py"` for finding files
    - ✅ ONLY use Grep for searching text INSIDE file contents

14. ❌ **Manually restarting MCP servers when developing Cerberus**
    - ❌ NEVER use `pkill -f cerberus` or manual process killing
    - ✅ Use `hydra_restart(server="cerberus")` instead
    - ✅ Hydra manages restarts without killing the session
    - See **MCP SERVER DEVELOPMENT RULES** section above

---


**Version:** 2.8 (Tool Enhancements)
**Token Budget:** This skill uses ~295 tokens. Pattern files load on-demand for 70-95% savings on every operation.

**Changelog 2.8:**
- **Enhanced:** 8 bulk tools (was 6) - added `skeletonize(files=[])`, `file_info(paths=[])`
- **NEW:** `file_info()` tool - file metadata without content (95% token savings vs Read)
- **Enhanced:** `blueprint(format="list")` - simple listing (~100 tokens vs ~350)
- **Enhanced:** `search(filter_type="imports")` - find import relationships
- **Enhanced:** `read_range()` - omit start/end for full file support (200 line limit)
- **Token safety limits:** Configurable limits prevent excessive usage (see cerberus.toml.example)
- **Reference:** BULK-OPERATIONS.md v2.0 with complete enhancement docs

**Changelog 2.7:**
- **NEW:** BULK OPERATIONS section - 6 tools support bulk mode (50-67% fewer round-trips)
- **Added bulk parameter notes:** get_symbol, read_range, style_fix, memory_learn/forget/search
- **Reference doc:** BULK-OPERATIONS.md for complete API reference and token savings analysis
- **Token savings:** ~200-600 tokens per bulk operation vs sequential calls
- **Backward compatible:** Single mode unchanged, bulk is optional enhancement

**Changelog 2.6:**
- **CRITICAL:** Added MCP SERVER DEVELOPMENT RULES section
- **Hydra integration:** NEVER manually restart MCP servers, use Hydra tools instead
- **Added Hydra tools table:** hydra_restart, hydra_force_restart, hydra_status, hydra_logs
- **Added Common Mistake #14:** Manually restarting MCP servers
- **Workflow preservation:** Hydra keeps session alive during MCP server restarts

**Changelog 2.5:**
- **CRITICAL:** Explicit enforcement: ALWAYS use search() for files/symbols, NEVER Grep/Glob
- **Added NEVER column** to TOOL PRIORITY table for clarity
- **Added Common Mistake #13:** Using Grep/Glob instead of search() for finding files
- **Updated search.md:** Clear rules on when to use search() vs Grep, with anti-patterns
- **Enhanced examples:** Explicit "WRONG" vs "RIGHT" patterns for file/symbol finding

**Changelog 2.4:**
- **Clarified batch vs real-time:** Batch processing is PRIMARY (session end), real-time is SUPPLEMENTAL (explicit statements only)
- **Added `memory_propose()`:** Manually trigger batch processing mid-session
- **Added `memory_search()`:** FTS5 full-text search across memories
- **Fixed `blueprint`:** Handles absolute/relative path inconsistencies
- **Hybrid memory format:** All memories now support semantic code + structured details
- **5 detection patterns:** Commands, repetition, post-action, multi-turn, preferences
- **Updated storage:** ~/.cerberus/memory.db (SQLite with sessions + memory_store tables)
- **Added gates:** Clear rules for when to use real-time vs batch, prevent duplication
