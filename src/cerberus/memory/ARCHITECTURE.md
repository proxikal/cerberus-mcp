# Memory System Architecture

**For AI Agents: Read this first to understand the module structure.**

---

## ⚠️ CRITICAL: How Memory Collection Works

### Batch Processing at Session End (PRIMARY SYSTEM)

**ALL memory collection happens at session end via the bash hook.**

When Claude Code exits:
```bash
cerberus memory propose --interactive  # Runs automatically
```

**This is the ONLY way memories are collected** because:
1. ✅ **Full conversation context** - Sees entire conversation flow
2. ✅ **Multi-turn patterns** - Detects "User asks → AI does X → User corrects with 'don't do X'"
3. ✅ **Tool results in context** - Sees tool calls AND their results together
4. ✅ **Delayed corrections** - Catches corrections 2-3 turns after AI action
5. ✅ **More accurate** - Can analyze relationships between messages

**Process:**
1. Reads entire transcript file (Claude Code conversation history)
2. Extracts semantic codes (done:, next:, impl:, etc.)
3. Detects correction patterns ("don't do X", "never Y")
4. Clusters similar corrections
5. Generates memory proposals
6. User approves/rejects via CLI
7. Stores to SQLite

### SessionContextCapture (OPTIONAL MANUAL TRACKING)

**This is NOT used for automatic memory collection.**

`SessionContextCapture` is for **manual structured work tracking** (like developer notes):
- Explicitly mark completed tasks: `capture.record_completion("finished auth")`
- Record decisions: `capture.record_decision("use SQLite for storage")`
- Note blockers: `capture.record_blocker("waiting on API docs")`

**Why NOT used for correction detection:**
- ❌ No conversation context
- ❌ Can't see multi-turn patterns
- ❌ Doesn't have tool results
- ❌ Real-time = misses delayed corrections

**When it's used:**
- Manual CLI: `cerberus memory session-start` (explicit user command)
- Tests
- Future features (if we add mid-session structured tracking)

**TL;DR:** Batch processing = automatic learning. SessionContextCapture = manual notes.

---

## Module Responsibilities

### 🎯 Core Layers (Session Management)

#### `session_cli.py` - CLI Interface Layer
**Purpose:** Public API for manual session operations
**Provides:**
- CLI commands: `cerberus memory session-start`, `session-end`, `session-status`
- Crash recovery: `list_crashed_sessions()`, `recover_crashed_session()`
- Activity tracking: `update_session_activity()`
- Public data class: `SessionState`

**When to use:** Building CLI tools or need public session API
**Dependencies:** → `session_continuity.py`

#### `session_continuity.py` - Core Implementation
**Purpose:** Session context injection and OPTIONAL manual tracking
**Provides:**
- `SessionContextCapture` - **OPTIONAL** manual structured tracking (not used for correction detection)
- `SessionContextInjector` - Injects previous session context at MCP startup
- `AutoCapture` - Experimental tool usage capture (not production)
- `detect_session_scope()` - Determines project vs global scope

**When to use:**
- Context injection at session start ✅
- Manual tracking via CLI commands (optional) ✅
- NOT for automatic correction detection ❌ (use batch processing instead)

**Storage:** `~/.cerberus/memory.db` (SQLite)

#### `session_analyzer.py` - Analytics & Extraction
**Purpose:** Session analysis, code extraction, and correction detection
**Provides:**
- `save_session_context_to_db()` - Saves hybrid work summary
- `extract_session_codes()` - Extracts semantic codes
- `extract_session_details()` - Extracts structured details (why/how/where)
- `analyze_session_from_transcript()` - Detects corrections from conversation
- `SessionAnalyzer`, `CorrectionCandidate` classes

**When to use:** Analyzing sessions or detecting corrections

---

### 🧠 Memory Pipeline (Proposal Generation)

#### `hooks.py` - Integration Orchestration
**Purpose:** Glue between components, session-end workflow
**Provides:**
- `propose_hook()` - End-of-session pipeline (detect → cluster → propose → store)
- `install_hooks()`, `uninstall_hooks()`, `verify_hooks()` - Hook management
- `detect_context()` - Detect project/language context

**Workflow:**
```
Session End → propose_hook()
  ├─> save_session_context_to_db() (analyzer)
  ├─> analyze_session_from_transcript() (analyzer)
  ├─> cluster_corrections() (semantic_analyzer)
  ├─> generate_proposals() (proposal_engine)
  ├─> ApprovalCLI.run() (approval_cli)
  └─> MemoryStorage.store_batch() (storage)
```

#### `semantic_analyzer.py` - Phase 2: Clustering
**Purpose:** Semantic deduplication and clustering
**Provides:**
- `SemanticAnalyzer` - TF-IDF clustering
- `CanonicalExtractor` - Canonical text extraction
- `CorrectionCluster` dataclass

#### `proposal_engine.py` - Phase 3: Proposal Generation
**Purpose:** Template-based proposal generation from clusters
**Provides:**
- `ProposalEngine` - Generates memory proposals
- `MemoryProposal` dataclass
- Scope/category inference

#### `approval_cli.py` - Phase 4/18: User Approval
**Purpose:** Interactive/batch approval of proposals
**Provides:**
- `ApprovalCLI` - Terminal UI for approval
- Batch mode with confidence threshold
- Phase 18 optimizations (grouping, deduplication)

#### `storage.py` - Phase 5: Persistence
**Purpose:** SQLite storage for approved memories
**Provides:**
- `MemoryStorage` - Store/retrieve memories
- Dynamic anchoring (Phase 14)
- Mode tagging (Phase 15)

---

### 🔍 Retrieval & Injection

#### `retrieval.py` - On-Demand Memory Retrieval
**Purpose:** Find relevant memories for queries
**Provides:**
- `MemoryRetrieval` - Query-based retrieval
- Relevance scoring with recency decay
- Scope filtering (universal/language/project)

#### `context_injector.py` - MCP Startup Injection (Deprecated?)
**Purpose:** Legacy context injection (consider using `session_continuity.SessionContextInjector` instead)
**Note:** May be superseded by `session_continuity.py`

---

### 📊 Advanced Features

#### `silent_divergence.py` - Phase 20: Silent Corrections
**Purpose:** Detect when users silently fix AI-generated code
**Provides:**
- `track_tool_usage()` - Record Edit/Write events
- `detect_silent_divergences()` - Find user modifications after AI responses
- Language-agnostic diff analysis

**Dependencies:** → `session_cli.update_session_activity()`

#### `indexing.py` - SQLite Schema Management
**Purpose:** Database schema and migrations
**Provides:**
- `MemoryIndexManager` - Schema initialization
- Migration from JSON to SQLite
- Table creation and integrity checks

#### `search.py` - FTS5 Full-Text Search
**Purpose:** Fast text search across memories
**Provides:**
- `MemorySearchEngine` - FTS5 search with ranking
- Query parsing and syntax support

---

## Dependency Graph

```
┌─────────────────────────────────────────────────┐
│                   CLI Layer                      │
│  cli.py → session_cli.py → session_continuity   │
└─────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│              Session End Pipeline                │
│  hooks.py → session_analyzer.py                 │
│           ↓                                      │
│  semantic_analyzer → proposal_engine             │
│           ↓                                      │
│  approval_cli → storage                          │
└─────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│                Storage Layer                     │
│  indexing.py (schema) ← storage.py              │
│  search.py (FTS5) ← retrieval.py                │
└─────────────────────────────────────────────────┘
```

---

## Storage Architecture

**All data in:** `~/.cerberus/memory.db` (SQLite)

### Tables:
- `memory_store` - Metadata (category, scope, confidence, anchors)
- `memory_fts` - FTS5 virtual table for full-text search
- `memory_content` - Actual memory content (normalized)
- `sessions` - Session records with context_data + summary_details
- `session_activity` - Session event tracking

**No temp files** - Everything in SQLite with WAL mode for concurrency.

---

## Common Operations

### Start a session (CLI)
```python
from cerberus.memory.session_cli import start_session
state = start_session(
    working_directory="/path/to/project",
    project_name="myproject",
    language="python"
)
```

### Auto-capture during session
```python
from cerberus.memory.session_continuity import SessionContextCapture
capture = SessionContextCapture()
capture.record_file_modified("src/main.py")
capture.record_decision("Use SQLite for storage")
```

### Session end (automatic via hook)
```bash
# Installed hook calls:
cerberus memory propose --interactive
```

### Query memories
```python
from cerberus.memory.retrieval import MemoryRetrieval
retrieval = MemoryRetrieval()
results = retrieval.query(
    query="error handling",
    scope_context={"project": "cerberus", "language": "python"}
)
```

---

## For AI Agents

**When building features:**
1. **CLI commands** → Use `session_cli.py` public API
2. **Session tracking** → Use `session_continuity.SessionContextCapture`
3. **Memory retrieval** → Use `retrieval.py` or `search.py`
4. **New proposals** → Extend `proposal_engine.py` templates
5. **Storage changes** → Update `indexing.py` schema

**Don't confuse:**
- `session_cli.py` ≠ session tracking (it's the CLI interface)
- `session_continuity.py` = actual session tracking implementation
- `context_injector.py` = legacy? (check if superseded by SessionContextInjector)

---

**Last Updated:** 2026-01-23 (Refactor: session_lifecycle → session_cli)
