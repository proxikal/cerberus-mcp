# PROTOCOL: MEMORY

**OBJECTIVE:** Store learned context to avoid repetitive analysis.

## DUAL-LAYER MEMORY SYSTEM

**CRITICAL CONCEPT:** Memory has TWO storage layers with different scopes:

### 🌍 Global Memory (~/.cerberus/memory/)
Applies to **ALL projects** across your system:
- **Preferences** → Your coding style, tool choices, general patterns
- **Corrections** → Mistakes to avoid globally

### 📁 Project Memory (.cerberus/memory/)
Applies **ONLY to current project**:
- **Decisions** → Architecture choices, tech stack, project-specific conventions

**Example:**
```
Session 1 (ProjectA): memory_learn(category="preference", content="Use async/await")  # Global
Session 1 (ProjectA): memory_learn(category="decision", content="PostgreSQL + Prisma")  # Project
Session 2 (ProjectA): memory_context() → "async/await" + "PostgreSQL + Prisma"
Session 3 (ProjectB): memory_context() → "async/await" only (global carries over)
```

## MCP TOOLS

### Core Memory

#### `memory_learn`
**Use:** Save preferences, decisions, or corrections.
**Params:**
- `category`: "preference", "decision", or "correction"
- `content`: What to remember
- `project`: Project name (auto-detected for decisions)
- `metadata`: Additional structured data

**Examples:**
```
memory_learn(category="decision", content="Use Factory pattern for handlers")
memory_learn(category="correction", content="Always validate input in controllers")
memory_learn(category="preference", content="Prefer early returns over nested ifs")
```

#### `memory_context`
**Use:** Generate context for current task. **Call at session start.**
**Params:**
- `project`: Project name (auto-detected)
- `compact`: Concise output (default: true)

```
memory_context(compact=true)
```

#### `memory_show`
**Use:** View all stored memory.
**Params:**
- `category`: Filter by type (optional)
- `project`: Project name (optional)

```
memory_show()
memory_show(category="decisions", project="myapp")
```

#### `memory_stats`
**Use:** Storage statistics.

```
memory_stats()
```

#### `memory_forget`
**Use:** Remove specific entry.
**Params:**
- `category`: Entry type
- `identifier`: Content to remove
- `project`: For decisions

```
memory_forget(category="preference", identifier="outdated rule")
```

### Backup & Sync

#### `memory_export`
**Use:** Export all memory for backup or sharing.
**Params:**
- `output_path`: Export file path (default: cerberus-memory-export-YYYYMMDD.json)

```
memory_export()
memory_export(output_path="/path/to/backup.json")
```

#### `memory_import`
**Use:** Import memory from backup.
**Params:**
- `input_path`: Path to export JSON file
- `merge`: Merge with existing (default: true) or replace

```
memory_import(input_path="/path/to/backup.json")
memory_import(input_path="/path/to/backup.json", merge=false)  # Replace all
```

### Auto-Learning

#### `memory_extract`
**Use:** Extract patterns from git history automatically.
**Params:**
- `path`: Path to git repository (default: current directory)
- `lookback_days`: Days of history to analyze (default: 30)

```
memory_extract()
memory_extract(lookback_days=60)
```

**Returns:** Learned patterns and statistics from commit history.

## STRATEGY

### Session Start (MANDATORY)
```
memory_context()  # Load project + global constraints
```

### During Work
- `memory_learn(category="decision", ...)` when establishing a pattern
- `memory_learn(category="correction", ...)` when fixing a repeated mistake

### Session End
- `memory_learn()` if new pattern/decision worth remembering

### Maintenance
- `memory_show()` to review what's stored
- `memory_forget()` to remove outdated entries
- `memory_export()` to backup before major changes
- `memory_extract()` to auto-learn from recent commits

## CATEGORY GUIDE

| Category | Scope | Use For |
|----------|-------|---------|
| `preference` | Global (all projects) | Coding style, tool preferences |
| `decision` | Project-specific | Architecture choices, patterns |
| `correction` | Global (all projects) | Common mistakes to avoid |
