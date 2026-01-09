# AI Agent Guide for Cerberus

Cerberus is designed to be "Agent-Native." Every command supports a `--json` flag for machine integration.

## Core Toolbelt

### 🔍 Discovery
Use `scan` or `index` to understand the project landscape.
```bash
cerberus index ./src --json
```

### 🎯 Retrieval
Use `get-symbol` to fetch specific code blocks without reading whole files.
```bash
cerberus get-symbol "login_user" --padding 5 --json
```

### 🧠 Search
Use `search` for hybrid retrieval (BM25 keyword + vector semantic).
```bash
# Auto mode (detects query type automatically)
cerberus search "how is database auth handled?" --limit 3 --json

# Force keyword mode for exact matches
cerberus search "DatabaseConnection" --mode keyword --json

# Force semantic mode for conceptual searches
cerberus search "authentication logic" --mode semantic --json

# Balanced mode with custom weights
cerberus search "user login" --mode balanced --keyword-weight 0.7 --json
```

### 🕸️ Dependencies
Use `deps` to map relationships.
```bash
# Show callers for a symbol
cerberus deps --symbol "handle_request" --json

# Show imports for a file
cerberus deps --file src/auth.py --json

# Show imports with Phase 5 resolution results
cerberus deps --file src/auth.py --show-resolution --json
```

### 🧠 Phase 5: Symbolic Intelligence
Phase 5 adds deep code understanding through method call tracking, type resolution, and import linkage.

#### Query Method Calls
Find all method calls in the codebase (e.g., `optimizer.step()`).
```bash
# Find all calls to a specific method
cerberus calls --method step --json

# Find calls on a specific receiver
cerberus calls --receiver optimizer --json

# Find calls with resolved type information
cerberus calls --type Adam --method step --json

# Find all method calls in a file
cerberus calls --file src/train.py --json
```

#### Query Symbol References
Navigate instance→definition relationships resolved by type tracking.
```bash
# Find references from a source symbol
cerberus references --source optimizer --json

# Find references to a target symbol
cerberus references --target Adam --json

# Filter by reference type
cerberus references --type method_call --json

# Filter by confidence threshold
cerberus references --min-confidence 0.8 --json

# Find references in a specific file
cerberus references --source-file src/train.py --json
```

#### Resolution Statistics
Check Phase 5 health metrics and resolution quality.
```bash
# Get symbolic intelligence statistics
cerberus resolution-stats --json

# Output includes:
# - Import resolution rate (%)
# - Total/resolved/unresolved imports
# - Total method calls extracted
# - Total symbol references created
```

### 📁 File Operations
Use these commands for direct file exploration and pattern matching.

#### Read Files
```bash
# Read entire file
cerberus read src/auth.py --json

# Read specific line range
cerberus read src/auth.py --lines 10-50 --json

# Get skeleton view (signatures only)
cerberus read src/auth.py --skeleton --json
```

#### Inspect Files
```bash
# Quick overview: file stats + all symbols
cerberus inspect src/auth.py --json
```

#### Directory Structure
```bash
# Show directory tree
cerberus tree ./src --depth 3 --json

# Tree with symbol counts per file
cerberus tree ./src --symbols --json

# Filter by extensions
cerberus tree ./src --ext ".py,.js" --json
```

#### List Files
```bash
# List files in directory
cerberus ls ./src --json

# Recursive listing
cerberus ls ./src --recursive --json

# Filter by extensions
cerberus ls ./src --ext ".py" --json
```

#### Pattern Search
```bash
# Search for pattern in files
cerberus grep "class.*Auth" --json

# Search specific directory
cerberus grep "def login" --path ./src/auth --json

# Case-insensitive search
cerberus grep "todo" --ignore-case --json

# Filter by file extensions
cerberus grep "import.*jwt" --extensions ".py" --json
```

#### Enhanced Symbol Retrieval
```bash
# Fuzzy symbol search (substring matching)
cerberus get-symbol "login" --fuzzy --json

# Get all symbols in a file
cerberus get-symbol --file src/auth.py --json

# Filter by symbol type
cerberus get-symbol "User" --type class --json
```

### 🔄 Incremental Updates
Use `update` to keep your index fresh without full reparse (10x faster).
```bash
# Update index based on git changes
cerberus update --index project.db --json

# Show what would be updated (dry-run)
cerberus update --index project.db --dry-run --json

# Update with detailed statistics
cerberus update --index project.db --stats --json

# Force full reparse if needed
cerberus update --index project.db --full --json
```

### 👁️ Background Watcher
Use `watcher` to auto-sync index with filesystem changes.
```bash
# Check watcher status
cerberus watcher status --json

# Start watcher daemon
cerberus watcher start --project ./my-project --index project.db --json

# Stop watcher daemon
cerberus watcher stop --json
```

## Integration Instructions
1.  **Generate Manifest:** Run `cerberus generate-tools` to get a JSON description of these capabilities.
2.  **JSON Stream Logging:** Monitor `cerberus_agent.log` for structured error messages and performance data.
3.  **Deterministic Retrieval:** Always prefer `get-symbol` over reading files to minimize token usage and prevent context loss.
4.  **Aegis-Scale Reliability:** Cerberus uses a disk-first architecture (SQLite). This means searching and retrieving symbols is near-instant even in enterprise codebases, as the system only loads the specific code segments you request.
5.  **Automatic Synchronization:** In supported environments, the **Background Watcher (Invisible Assistant)** will automatically keep the index synchronized as you write code, ensuring that your next `get-symbol` or `search` query is always based on the latest state of the project.

**Note for Agents:** Cerberus is your context engine. It is designed to augment your capabilities (Claude, Codex, etc.) by serving deterministic, compacted code. Any mentions of "internal LLMs" or "Summarization" refer to optional background optimizations designed to save you tokens; your reasoning remains the primary driver of all project changes.
