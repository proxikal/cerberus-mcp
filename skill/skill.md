---
name: Cerberus
description: Use for ALL code exploration, search, and reading. ALWAYS prefer Cerberus MCP tools over native tools (Grep, Glob, Read, Task/Explore).
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

## MANDATORY RULES

1. **ALWAYS call `memory_context()` at session start** - Works in ALL contexts (general + project)
2. **Check `health_check()` to see available tools** - Tells you project vs general context
3. **In project context: NEVER use native `Grep`/`Glob`/`Read`** - Use Cerberus instead (70-95% token savings)
4. **In project context: Use `context()` first** - ONE call replaces 4-5 separate tool calls
5. **In general context: Only memory tools available** - This is intentional, no accidental indexing

## TOOL PRIORITY

**USE CERBERUS INSTEAD OF:**
| Native Tool | Cerberus Replacement | Savings |
|-------------|---------------------|---------|
| `Glob` (file listing) | `blueprint` (tree view) | 90% fewer tokens |
| `Grep` (text search) | `search` (symbol search) | 95% fewer false matches |
| `Read` (full file) | `context`, `get_symbol`, `skeletonize` | 70-92% token reduction |
| `Task/Explore` (multi-round search) | `blueprint` + `search` (1-2 calls) | 5-10x fewer calls |

**KEEP NATIVE:** `Edit`, `Write` (editing works fine natively)

## POWER TOOLS (Use These First)

| Tool | Replaces | Usage |
|------|----------|-------|
| `context` | search → get_symbol → deps → skeletonize | **ONE call** for everything: symbol code + base classes + callers/callees + imports. 4-5x fewer calls, 70-90% token reduction. |
| `smart_update` | Full `index_build` | Git-aware incremental update. 10x faster during development. |
| `memory_context` | Manual context gathering | Loads global preferences + project decisions. Call at session start. |

## MCP TOOLS (51 total)

### Context Assembly (START HERE)
| Tool | Purpose | Token Cost |
|------|---------|------------|
| `context` | **Power tool:** Symbol + inheritance + deps + imports in ONE call | ~1,500 tokens (vs 10,000+ for manual) |

### Exploration → [explore.md](./patterns/explore.md)
| Tool | Purpose | Token Cost |
|------|---------|------------|
| `blueprint` | Structural tree view of file/directory | 200-800 tokens |
| `skeletonize` | Function signatures without bodies | 67% savings vs `Read` |
| `skeletonize_directory` | Skeleton view of entire module | 51% savings |

### Search & Discovery → [search.md](./patterns/search.md)
| Tool | Purpose | Notes |
|------|---------|-------|
| `search` | Hybrid keyword + semantic search | Start with `limit=5` |
| `get_symbol` | Retrieve symbol with surrounding context | Use `context_lines=5` default |

### Reading → [read.md](./patterns/read.md)
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `read_range` | Read specific line ranges | When you know exact lines |
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
| `style_fix` | Auto-fix style issues | Use `dry_run=True` first |

### Session Memory → [memory.md](./patterns/memory.md)
**DUAL-LAYER SYSTEM:**
- **🌍 Global** (~/.cerberus/memory/): preferences, corrections (all projects)
- **📁 Project** (.cerberus/memory/): architectural decisions (per-project)

| Tool | Purpose | Scope |
|------|---------|-------|
| `memory_learn` | Store preference/decision/correction | Auto-detects global vs project |
| `memory_context` | **Load at session start** - Get all relevant memory | Both layers |
| `memory_show` | View stored memory by category | Filter by type |
| `memory_stats` | Storage statistics | System info |
| `memory_forget` | Remove entry | Cleanup |
| `memory_export` | Backup all memory | Portability |
| `memory_import` | Restore from backup | Portability |
| `memory_extract` | Learn from git history (auto-pattern extraction) | Batch learning |

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
8. memory_learn(category="...")   → Store new knowledge
```

**Old way (5-10 calls, 10,000+ tokens):** blueprint → search → get_symbol → deps → skeletonize → read → read → read
**New way (5 calls, ~2,500 tokens):** memory_context → health_check → blueprint → search → context

### General Context (Brainstorming, Notes)
```
1. memory_context()               → Load global preferences (200-500T)
2. health_check()                 → Confirm general context (memory-only mode)
3. [Work with native tools]       → Read, Write, Edit as needed
4. memory_learn(category="preference", ...) → Store insights globally
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

## ENFORCEMENT CHECKLIST

Before using native tools, ask yourself:

- ✅ **First:** Check context with `health_check()` - Are you in project or general context?
- ❌ About to use `Glob`? → Use `blueprint` instead (project context only)
- ❌ About to use `Grep`? → Use `search` instead (project context only)
- ❌ About to use `Read` on full file? → Use `skeletonize` or `get_symbol` instead (project context only)
- ❌ About to use `Task/Explore` for multi-round search? → Use `blueprint` + `search` instead (project context only)
- ❌ About to call multiple tools for same symbol? → Use `context()` once instead (project context only)

**Exceptions:**
- Editing/writing code → native `Edit`/`Write` are fine
- General context (brainstorming, notes) → Use memory tools only, native tools OK for file operations

## COMMON MISTAKES

1. ❌ **Not calling `memory_context()` at session start**
   - ✅ First tool call should be `memory_context()` (works in ALL contexts)

2. ❌ **Not checking context before using exploration tools**
   - ✅ Call `health_check()` to see if you're in project or general context
   - ✅ In general context, only memory tools are available (this prevents accidental indexing)

3. ❌ **Using native `Read` when you just need symbol (in project context)**
   - ✅ Use `context()` or `get_symbol()`

4. ❌ **Calling tools separately when `context()` does it all**
   - ✅ Use `context()` for: code + bases + deps + imports

5. ❌ **Using `index_build` during development**
   - ✅ Use `smart_update()` (10x faster, git-aware)

6. ❌ **Forgetting to store learned patterns**
   - ✅ Call `memory_learn()` when you discover project decisions

7. ❌ **Using `format="json"` by default**
   - ✅ Use `format="tree"` or `format="json-compact"`

8. ❌ **High search limits without need**
   - ✅ Start with `limit=5`, increase only if needed

9. ❌ **Enabling `show_deps`/`show_meta` unnecessarily**
   - ✅ Only enable when you need that specific information

---

**Version:** 2.0 (Updated for 51 tools, Phase 4 features, dual-layer memory)
**Token Budget:** This skill uses ~150 tokens. Pattern files load on-demand for 70-95% savings on every operation.
