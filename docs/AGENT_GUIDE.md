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
cerberus deps --symbol "handle_request" --json
```

### 🔄 Incremental Updates
Use `update` to keep your index fresh without full reparse (10x faster).
```bash
# Update index based on git changes
cerberus update --index my_index.json --json

# Show what would be updated (dry-run)
cerberus update --index my_index.json --dry-run --json

# Update with detailed statistics
cerberus update --index my_index.json --stats --json

# Force full reparse if needed
cerberus update --index my_index.json --full --json
```

### 👁️ Background Watcher
Use `watcher` to auto-sync index with filesystem changes.
```bash
# Check watcher status
cerberus watcher status --json

# Start watcher daemon
cerberus watcher start --project ./my-project --index my_index.json --json

# Stop watcher daemon
cerberus watcher stop --json

# View watcher logs
cerberus watcher logs --follow
```

## Integration Instructions
1.  **Generate Manifest:** Run `cerberus generate-tools` to get a JSON description of these capabilities.
2.  **JSON Stream Logging:** Monitor `cerberus_agent.log` for structured error messages and performance data.
3.  **Deterministic Retrieval:** Always prefer `get-symbol` over reading files to minimize token usage and prevent context loss.
4.  **Automatic Synchronization:** In supported environments, the **Background Watcher (Invisible Assistant)** will automatically keep the index synchronized as you write code, ensuring that your next `get-symbol` or `search` query is always based on the latest state of the project.

**Note for Agents:** Cerberus is your context engine. It is designed to augment your capabilities (Claude, Codex, etc.) by serving deterministic, compacted code. Any mentions of "internal LLMs" or "Summarization" refer to optional background optimizations designed to save you tokens; your reasoning remains the primary driver of all project changes.
