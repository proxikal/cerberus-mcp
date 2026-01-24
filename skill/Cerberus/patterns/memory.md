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

### ⚠️ Batch vs Real-Time Learning

**PRIMARY SYSTEM: Batch Processing (Session End)**
- Automatically runs when session ends via bash hook
- Analyzes ENTIRE conversation transcript
- Detects all 5 patterns: commands, repetition, post-action, multi-turn, preferences
- More accurate (full context, multi-turn patterns)
- **Use `memory_propose()` to manually trigger mid-session**

**SUPPLEMENTAL: Real-Time Learning (During Session)**
- Agent calls `memory_learn()` when user **explicitly states** preference
- Only for direct, clear statements like "I prefer X over Y"
- Cannot detect multi-turn patterns or delayed corrections
- **Don't overuse** - batch will catch everything at session end

### Core Memory

#### `memory_learn`
**Use:** Save preferences, decisions, or corrections. **Call immediately when user states a preference.**
**Params:**
- `category`: "preference", "decision", or "correction"
- `content`: Semantic code (compressed identifier)
- `details`: Structured explanation (Root/Fix/Files format) - RECOMMENDED
- `project`: Project name (auto-detected for decisions)
- `metadata`: Additional structured data
- `relevance_decay_days`: Auto-deprioritize after N days (default: 90)

**Hybrid Format (content + details):**
```
memory_learn(
    category="preference",
    content="prefer_snowflake_ids_over_uuids",
    details="Root: User prefers Discord-style Snowflake IDs\nFix: Use Snowflake IDs for all ID generation\nFiles: Generated IDs in database models"
)

memory_learn(
    category="decision",
    content="use_factory_pattern_for_handlers",
    details="Root: Needed consistent handler creation\nFix: Implemented Factory pattern\nFiles: src/handlers/factory.py"
)
```

**Quick format (legacy - still works):**
```
memory_learn(category="correction", content="Always validate input in controllers")
```

#### `memory_context`
**Use:** Generate context for current task. **Call at session start.**
**Params:**
- `project`: Project name (auto-detected)
- `compact`: Concise output (default: true)

```
memory_context(compact=true)
```

#### `memory_propose`
**Use:** Manually trigger session-end memory collection pipeline (batch processing).
**Params:**
- `interactive`: CLI approval (default: true) or auto-approve
- `batch_threshold`: Auto-approve confidence threshold (default: 0.9)

**When to use:**
- Mid-session memory collection (keep session open)
- Hook not working (manual recovery)
- Testing memory collection

```
memory_propose(interactive=True)  # CLI approval
memory_propose(interactive=False, batch_threshold=0.85)  # Auto-approve >= 0.85
```

**Process:**
1. Reads entire transcript
2. Saves session summary (semantic codes + structured details)
3. Detects corrections (5 patterns)
4. Clusters similar corrections
5. Generates proposals
6. User approves/rejects
7. Stores to database

#### `memory_show`
**Use:** View all stored memory.
**Params:**
- `category`: Filter by type (optional)
- `project`: Project name (optional)

```
memory_show()
memory_show(category="decisions", project="myapp")
```

#### `memory_search`
**Use:** FTS5 full-text search across all memories.
**Params:**
- `query`: Search terms
- `scope`: Filter by scope (optional)
- `category`: Filter by category (optional)
- `limit`: Max results (default: 10)

```
memory_search(query="error handling")
memory_search(query="prefer", category="preference", limit=5)
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

### Real-Time Learning (PROACTIVE)
**CRITICAL:** Detect and store user preferences IMMEDIATELY when stated, don't wait for session end.

**Trigger phrases to watch for:**
- "I prefer X over Y" → `memory_learn(category="preference", content="prefer_X_over_Y", details="...")`
- "I like using X" → `memory_learn(category="preference", content="use_X", details="...")`
- "Don't use X" → `memory_learn(category="correction", content="avoid_X", details="...")`
- "Always do X" → `memory_learn(category="correction", content="always_X", details="...")`
- "Never do Y" → `memory_learn(category="correction", content="never_Y", details="...")`

**Examples:**
```
User: "I prefer Snowflake IDs over UUIDs"
Agent: [Immediately calls memory_learn]
memory_learn(
    category="preference",
    content="prefer_snowflake_ids_over_uuids",
    details="Root: User stated preference for Discord-style Snowflake IDs\nFix: Use Snowflake IDs instead of random UUIDs\nContext: Discussed during ID generation implementation"
)
```

**Detection patterns (5 total):**
1. Direct commands: "don't X", "always Y"
2. Repetition: User says same thing 2+ times
3. Post-action: Correction after agent acts
4. Multi-turn: Correction spanning messages
5. **Preferences:** "I prefer X", "I like Y"

### During Work
- `memory_learn(category="decision", ...)` when establishing an architecture pattern **AND user explicitly states it**
- `memory_learn(category="correction", ...)` **ONLY when user explicitly says** "don't do X" or "always do Y"
- **Don't overuse** - most corrections will be caught automatically at session end

### Session End (AUTOMATIC)
- Bash hook automatically runs `memory_propose()`
- Analyzes full transcript for all patterns
- Saves session summary + detected memories
- **You don't need to do anything** - this happens automatically

### Manual Trigger (OPTIONAL)
- User asks: "propose memories" → Call `memory_propose(interactive=True)`
- Mid-session collection → `memory_propose()`
- Hook failed → Manually trigger as backup

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

---

## GATES & GUARDRAILS

### When to Call `memory_learn()` (Real-Time)
✅ **YES - Call immediately:**
- User explicitly says: "I prefer X over Y"
- User explicitly says: "Don't use X, use Y instead"
- User explicitly says: "Always do Z"
- **Clear, direct preference statement**

❌ **NO - Let batch process handle:**
- User asks a question about preferences
- You infer user might prefer something
- User corrects code (batch will catch at session end)
- Repetitive patterns (batch catches these)
- Multi-turn corrections (batch detects better with full context)
- Implied preferences (batch analyzes full conversation)

**Rule of thumb:** If the user's statement isn't a direct imperative or preference declaration, don't capture it real-time.

### When to Call `memory_propose()` (Batch Trigger)
✅ **YES - User requests it:**
- User explicitly asks: "propose memories from this session"
- User asks to collect memories mid-session
- Hook isn't working, manual recovery needed
- Testing memory collection without ending session

❌ **NO - Don't auto-trigger:**
- Don't call automatically at end of every task
- Don't call repeatedly (once per session max)
- Don't call as a "safety net" - hook handles this

### Storage Location
- **Database:** `~/.cerberus/memory.db` (SQLite)
- **Global:** Preferences/corrections (all projects)
- **Project-scoped:** Decisions (via `scope` field)
- **Session summaries:** `sessions` table (same DB)
