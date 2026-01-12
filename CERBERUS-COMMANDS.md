# CERBERUS - COMMAND REFERENCE

**Module Type:** On-Demand (load when you need command syntax)
**Core Reference:** See CERBERUS.md for tool selection rules and workflows
**Purpose:** Complete command syntax reference for all Cerberus commands

---

## SESSION & LIFECYCLE

```bash
cerberus start                              # Initialize session (index + daemon + watcher + memory)
cerberus start --json                       # Machine-parsable status
cerberus update                             # Reindex changed files
cerberus clean --preserve-index             # Clean cache, keep index
cerberus validate-docs                      # Validate CERBERUS.md sync
cerberus validate-docs --json --strict      # Machine output, strict mode
```

---

## ORIENTATION & EXPLORATION

### Quick Orientation

```bash
cerberus orient [dir]                       # Project overview, hot spots, recent changes
cerberus orient --json                      # Machine-parsable
cerberus go <file>                          # Blueprint + suggested read commands
cerberus go <file> --threshold 50           # Custom "heavy" symbol threshold (default: 30)
cerberus go <file> --json                   # Machine output with quick_reads array
```

### Blueprint - Structure Analysis

```bash
# Base command
cerberus blueprint <file>                   # Base structure with line numbers

# Overlays (add metadata)
cerberus blueprint <file> --deps            # + Dependencies with confidence scores
cerberus blueprint <file> --meta            # + Complexity metrics
cerberus blueprint <file> --churn           # + Git history (edits/authors)
cerberus blueprint <file> --coverage        # + Test coverage (needs coverage.json)
cerberus blueprint <file> --stability       # + Risk score
cerberus blueprint <file> --cycles          # + Circular dependency detection
cerberus blueprint <file> --hydrate         # + Auto-include heavy deps
cerberus blueprint <file> --diff HEAD~1     # Structural diff vs git ref
cerberus blueprint <file> --with-memory     # Include developer context

# Aggregation
cerberus blueprint <dir> --aggregate        # Package-level view

# Output control
cerberus blueprint <file> --format tree     # Tree format (default)
cerberus blueprint <file> --format json     # JSON format
cerberus blueprint <file> --no-cache        # Skip cache
cerberus blueprint <file> --fast            # Speed over completeness
cerberus blueprint <file> --max-width N     # Limit output width
cerberus blueprint <file> --collapse-private # Hide private symbols
```

### Search

```bash
cerberus search "<query>"                   # Semantic/hybrid search (default)
cerberus search "<query>" --mode keyword    # Keyword-only search
cerberus search "<query>" --mode semantic   # Embedding-based search
cerberus search "<query>" --mode balanced   # Hybrid (default)
```

### Symbol Lookup (USE SPARINGLY)

```bash
cerberus get-symbol <name> --snippet --exact  # Raw code only, exact match (recommended)
cerberus get-symbol <name>                    # Full context (1100% overhead vs Read)

# Optional flags (use sparingly)
cerberus get-symbol <name> --context N        # Lines of context
cerberus get-symbol <name> --limit N          # Max results
cerberus get-symbol <name> --show-callers     # Show who calls this symbol
```

### File Tree

```bash
cerberus dogfood tree --depth N             # Directory structure
cerberus dogfood ls <path>                  # List files
cerberus dogfood grep "<pattern>" <path>    # Search in files
```

---

## SYMBOLIC ANALYSIS

```bash
cerberus symbolic deps <symbol>             # What does this symbol call?
cerberus symbolic references <symbol>       # What calls this symbol?
cerberus symbolic calls <symbol>            # Outgoing calls
cerberus symbolic inherit-tree <class>      # Inheritance hierarchy
cerberus symbolic descendants <class>       # Child classes
cerberus symbolic overrides <method>        # Override chain
cerberus symbolic call-graph <symbol>       # Full call graph
cerberus symbolic smart-context <symbol>    # Contextual information
cerberus symbolic trace-path <from> <to>    # Path between symbols
cerberus symbolic resolution-stats          # Type resolution statistics
```

---

## MUTATIONS

### Batch Operations (Preferred)

```bash
cerberus mutations batch-edit ops.json --verify "pytest" --preview

# ops.json format:
# [{"op":"edit","file":"...","symbol":"...","code":"..."}]
```

### Single Mutations

```bash
cerberus mutations edit <file> --symbol <name> --code "..."
cerberus mutations edit <file> --symbol <name> --code "..." --check-corrections
cerberus mutations delete <file> --symbol <name>
cerberus mutations delete <file> --symbol <name> --force  # Override HIGH RISK
cerberus mutations insert <file> --after <symbol> --code "..."
cerberus mutations undo                     # Revert last batch
cerberus mutations stats                    # Mutation statistics
```

---

## QUALITY

### Style Checking

```bash
cerberus quality style-check <file>
cerberus quality style-check <dir> --recursive
cerberus quality style-fix <file>
cerberus quality style-fix <file> --preview
cerberus quality style-fix <file> --force
cerberus quality style-fix <file> --verify "pytest"
```

### Predictions

```bash
cerberus quality related-changes <symbol>
cerberus quality related-changes <symbol> --file <path> --verbose --json
cerberus quality prediction-stats
cerberus quality prediction-stats --window 600 --limit 50 --json
```

---

## MEMORY

### Learn Preferences

```bash
cerberus memory learn "prefer early returns"             # Style preference
cerberus memory learn -d "chose SQLite for portability"  # Decision (--decision)
cerberus memory learn -c "always log before throw"       # Correction (--correction)
cerberus memory learn --prompt "security" -t code-review # Prompt template
```

### View Memory

```bash
cerberus memory show                        # Show all
cerberus memory show profile                # Preferences only
cerberus memory show decisions -p <project> # Project decisions
cerberus memory stats                       # Storage statistics
```

### Generate Context

```bash
cerberus memory context                     # Full context
cerberus memory context --compact           # Minimal version
cerberus memory context -p <project> -t <task-type>
```

### Manage

```bash
cerberus memory edit profile                # Open in editor
cerberus memory forget "<key>"              # Remove preference
cerberus memory export -o backup.json       # Backup
cerberus memory import backup.json          # Restore
cerberus memory extract --from-git          # Extract from git history
```

---

## PROTOCOL REFRESH (AI Memory Restoration)

```bash
cerberus refresh                            # Light refresh (~150 tokens) - critical rules
cerberus refresh --rules                    # Standard refresh (~300 tokens) - tool selection + rules
cerberus refresh --full                     # Full CERBERUS.md reload (~1500+ tokens)
cerberus refresh --status                   # Check protocol tracking state
cerberus refresh --json                     # Machine-parsable output
```

**When to Use:**
- After context compaction (agent memory summarized)
- When hint suggests "Protocol memory may be degraded"
- Before complex multi-file operations
- If unsure which cerberus command to use

---

## WATCHER

```bash
cerberus watcher status                     # Check if watcher running
cerberus watcher start                      # Start file watcher
cerberus watcher stop                       # Stop watcher
cerberus watcher health --json              # Health metrics (log size, CPU)
```

---

## METRICS

```bash
cerberus metrics report                     # Last 7 days efficiency report
cerberus metrics report --days 30           # Custom period
cerberus metrics report --json              # Machine-parsable
cerberus metrics status                     # Collection status
cerberus metrics status --json              # Machine-parsable
cerberus metrics clear --yes                # Delete all metrics
```

---

## COMMAND PREREQUISITES

```
--deps/--hydrate/--cycles: Requires symbol_references (run: cerberus index .)
--coverage: Requires coverage.json (run: pytest --cov=src --cov-report=json)
--churn/--diff: Requires git repository
--stability: Requires at least one of --meta, --churn, or --coverage
```

---

**Version:** 1.0 (2026-01-11)
**Origin:** Extracted from CERBERUS.md v0.20.1
**Purpose:** On-demand command syntax reference (40% context reduction vs monolithic doc)
