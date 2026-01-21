# PROTOCOL: EXPLORE

**OBJECTIVE:** Map codebase structure without reading file content.

## MCP TOOLS

### 1. `blueprint`
**Use:** Structural view of file or directory.
**Cost:** Low (format-dependent).
**Params:**
- `path`: File or directory path
- `show_deps`: Include dependencies (default: false)
- `format`: "tree", "json", "json-compact", or "flat"

**Format costs:**
| Format | Tokens | Use Case |
|--------|--------|----------|
| `flat` | ~200 | Symbol list only |
| `tree` | ~350 | **Default** - exploration |
| `json-compact` | ~800 | Machine-parseable, minimal fields |
| `json` | ~1,800 | Full metadata (avoid unless needed) |

**Examples:**
```
blueprint(path="src/", format="tree")
blueprint(path="src/core/module.py", show_deps=true, format="json-compact")
```

### 2. `skeletonize`
**Use:** Code skeleton - signatures without implementation.
**Cost:** Low. Token savings: 70-90%.
**Params:**
- `path`: File path
- `preserve_symbols`: Keep full implementation for these symbols
- `format`: "code" or "json"

**Examples:**
```
skeletonize(path="src/auth.py")
skeletonize(path="src/handlers.py", preserve_symbols=["critical_handler"])
```

### 3. `skeletonize_directory`
**Use:** Skeleton view of entire module/package.
**Cost:** Low-Medium.
**Params:**
- `path`: Directory path
- `pattern`: Glob pattern (default: "**/*.py")
- `format`: "summary" or "combined"

**Examples:**
```
skeletonize_directory(path="src/core/", format="summary")
```

### 4. `index_status`
**Use:** Check index health and stats.
**Cost:** Very Low.

```
index_status()
```

### 5. `smart_update`
**Use:** Update index after code changes (git-aware, surgical).
**Cost:** Low (10x faster than full rebuild).
**Params:**
- `force_full`: Force full reparse (default: false)

```
smart_update()
```

**When to use:** After editing files, before searching again. Avoids full `index_build`.

### 6. `project_summary`
**Use:** 80/20 overview of new codebase.
**Cost:** Medium-High (~2,000-3,000 tokens, but 80%+ savings vs full exploration).
**Params:**
- `path`: Project root (default: current directory)
- `focus`: Optional focus area ("architecture", "patterns", "tech_stack")

**Examples:**
```
project_summary()
project_summary(path=".", focus="architecture")
```

**Returns:** High-level summary: structure, key components, patterns, tech stack.

**When to use:** First time exploring a new codebase. Replaces 10+ manual blueprint/search/read calls.

## STRATEGY

### New Codebase (First Time)
1. **OVERVIEW:** `project_summary()` for 80/20 high-level view (~2,500T vs ~25,000T full exploration)
2. **DRILL:** `blueprint(path="src/")` to explore specific areas
3. **SKELETON:** `skeletonize(path="src/key_module.py")` for lightweight file view

### Familiar Codebase
1. **INIT:** `blueprint(path=".")` to see root structure
2. **DRILL:** `blueprint(path="src/")` to refine
3. **SKELETON:** `skeletonize(path="src/module.py")` for lightweight file view
4. **MAP:** `blueprint(path="src/core/", show_deps=true)` to see relationships
5. **VERIFY:** `index_status()` if results seem stale
6. **UPDATE:** `smart_update()` after editing code (not full `index_build`)

## FORMAT SELECTION

- **Exploring?** → `format="tree"` (default, efficient)
- **Need structured data?** → `format="json-compact"` (50% cheaper than json)
- **Symbol list only?** → `format="flat"` (minimal)
- **Full metadata for tools?** → `format="json"` (use sparingly)
