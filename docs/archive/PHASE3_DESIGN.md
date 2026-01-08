# Phase 3: Operational Excellence - Design Document

## Overview
Phase 3 transforms Cerberus from a batch-processing tool into a **real-time, intelligent assistant** that seamlessly integrates into development workflows. It builds on Phase 1's dependency intelligence and Phase 2's context synthesis to deliver operational excellence through incremental updates, background synchronization, and optimized retrieval.

## Goals
1. **Git-Native Incrementalism:** Use `git diff` to identify modified lines and surgically update the index (re-parsing only changed symbols) ✅ **CORE FEATURE**
2. **Background Watcher (Invisible Assistant):** A lightweight daemon process that automatically starts when an agent initiates a scan or query if not already active. It keeps the index synchronized with the filesystem in real-time without user intervention. ✅ **CORE FEATURE**
3. **Hybrid Retrieval Optimization:** Fine-tune the balance between BM25 keyword matching and Vector semantic search for precise AND broad queries. ✅ **CORE FEATURE**

**Philosophy:** Cerberus should be **invisible yet always ready** - like a Unix daemon that "just works" without manual intervention.

## Architecture Design

### 1. New Packages (Self-Similarity Mandate)

#### `cerberus/incremental/`
Git-aware incremental index updates.

**Files:**
- `facade.py` - Public API for incremental operations
- `git_diff.py` - Git diff parsing and change detection
- `change_analyzer.py` - Determine which symbols need re-parsing
- `surgical_update.py` - Precision index updates
- `config.py` - Incremental update configuration
- `__init__.py` - Public exports

**API:**
```python
from cerberus.incremental import detect_changes, update_index_incrementally

# Detect changes since last index
changes = detect_changes(project_path, index_path)
# Returns: FileChange(added=[], modified=[], deleted=[])

# Update index surgically
result = update_index_incrementally(
    index_path="project.json",
    changes=changes,
    reparse_affected_callers=True
)
# Returns: IncrementalUpdateResult(updated_symbols=[], removed_symbols=[], elapsed_time=0.5)
```

#### `cerberus/watcher/`
Background filesystem watcher daemon.

**Files:**
- `facade.py` - Public API for watcher operations
- `daemon.py` - Daemon lifecycle management (start, stop, status)
- `filesystem_monitor.py` - Filesystem event monitoring (uses watchdog)
- `event_handler.py` - Process file change events and trigger updates
- `ipc.py` - Inter-process communication (daemon ↔ CLI)
- `config.py` - Watcher configuration
- `__init__.py` - Public exports

**API:**
```python
from cerberus.watcher import start_watcher, stop_watcher, watcher_status

# Start background watcher (auto-starts if not running)
pid = start_watcher(
    project_path="/path/to/project",
    index_path="project.json",
    debounce_delay=2.0  # Wait 2s after last change before updating
)

# Check watcher status
status = watcher_status()
# Returns: WatcherStatus(running=True, pid=12345, watching="/path/to/project", uptime=3600)

# Stop watcher
stop_watcher()
```

#### `cerberus/retrieval/` (Enhanced)
Hybrid BM25 + Vector search with ranking fusion.

**Files:**
- `facade.py` - Public API for retrieval operations (ALREADY EXISTS - will enhance)
- `bm25_search.py` - BM25 keyword search implementation (NEW)
- `vector_search.py` - Vector semantic search (refactor from existing)
- `hybrid_ranker.py` - Fusion ranking (combine BM25 + Vector scores) (NEW)
- `config.py` - Retrieval configuration (NEW)
- `__init__.py` - Public exports

**API:**
```python
from cerberus.retrieval import hybrid_search

# Hybrid search (automatically balances BM25 + Vector)
results = hybrid_search(
    query="database connection pooling",
    index=index,
    mode="balanced",  # "keyword", "semantic", "balanced", "auto"
    top_k=10
)
# Returns: List[SearchResult] with combined scores
```

### 2. New Schemas

#### `FileChange`
Represents detected changes from git diff.

```python
class FileChange(BaseModel):
    """Changes detected from git diff or filesystem monitoring."""
    added: List[str]  # New files
    modified: List[ModifiedFile]  # Changed files with line ranges
    deleted: List[str]  # Removed files
    timestamp: float  # When changes were detected

class ModifiedFile(BaseModel):
    """Details of a modified file."""
    path: str
    changed_lines: List[LineRange]  # Which lines changed
    affected_symbols: List[str]  # Symbols that need re-parsing

class LineRange(BaseModel):
    """Range of modified lines."""
    start: int
    end: int
    change_type: Literal["added", "modified", "deleted"]
```

#### `IncrementalUpdateResult`
Result of a surgical index update.

```python
class IncrementalUpdateResult(BaseModel):
    """Result of incremental index update."""
    updated_symbols: List[CodeSymbol]  # Symbols that were updated
    removed_symbols: List[str]  # Symbols that were removed
    affected_callers: List[str]  # Callers that were re-analyzed
    files_reparsed: int
    elapsed_time: float
    strategy: Literal["full_reparse", "surgical", "incremental"]
```

#### `WatcherStatus`
Status of the background watcher daemon.

```python
class WatcherStatus(BaseModel):
    """Status of the background watcher daemon."""
    running: bool
    pid: Optional[int]
    watching: Optional[str]  # Project path being watched
    index_path: Optional[str]
    uptime: Optional[float]  # Seconds since start
    last_update: Optional[float]  # Timestamp of last index update
    events_processed: int  # Total filesystem events handled
    updates_triggered: int  # Number of index updates triggered
```

#### `HybridSearchResult`
Search result with hybrid ranking.

```python
class HybridSearchResult(BaseModel):
    """Search result with hybrid BM25 + Vector ranking."""
    symbol: CodeSymbol
    bm25_score: float  # Keyword relevance (0-1)
    vector_score: float  # Semantic similarity (0-1)
    hybrid_score: float  # Combined score (0-1)
    rank: int  # Final ranking position
    match_type: Literal["keyword", "semantic", "both"]
```

### 3. Implementation Strategy

#### 3.1 Git-Native Incrementalism

**Git Diff Parsing:**
- Use `git diff HEAD <index_commit>` to get changes since last index
- Parse unified diff format to extract changed line ranges
- Store last indexed commit hash in index metadata

**Change Analysis Algorithm:**
1. **File-Level Changes:** Identify added/modified/deleted files
2. **Symbol-Level Changes:** Map changed line ranges to affected symbols
3. **Caller Analysis:** Use Phase 1 call graph to find symbols that call modified symbols
4. **Smart Re-parsing:** Only re-parse affected symbols and their immediate callers

**Surgical Update Strategy:**
```
IF file is NEW:
    - Full parse, add all symbols to index
IF file is DELETED:
    - Remove all symbols from index
IF file is MODIFIED:
    - Parse changed line ranges to identify affected symbols
    - Re-parse affected symbols only
    - Update call graph edges for affected symbols
    - Re-parse direct callers if signature changed
```

**Example:**
```python
# Function foo() at lines 10-20 is modified
# Git diff shows: @@ -15,3 +15,5 @@

# Strategy:
1. Identify symbol at lines 10-20: foo()
2. Re-parse foo() only
3. Check if signature changed (return type, parameters)
4. If signature changed: re-parse all callers of foo()
5. Update index with new foo() data
6. Preserve all other symbols unchanged
```

#### 3.2 Background Watcher (Invisible Assistant)

**Daemon Architecture:**
- **Process Model:** Separate daemon process (not a thread)
- **Lifecycle:** Auto-start on first query, graceful shutdown, auto-restart on crash
- **Communication:** Unix socket or named pipe for IPC

**Filesystem Monitoring:**
- Use `watchdog` library for cross-platform file monitoring
- Watch for: file modifications, creations, deletions, renames
- Debounce events: wait N seconds after last change before updating
- Respect `.gitignore` and cerberus ignore patterns

**Event Processing Pipeline:**
```
Filesystem Event → Debounce (2s) → Change Detection → Incremental Update → Index Write
```

**Auto-Start Logic:**
```python
# When CLI command runs (e.g., cerberus search)
def execute_command():
    if not watcher_is_running():
        start_watcher_background()  # Spawn daemon if not running

    # Execute command (watcher will keep index fresh)
    result = perform_search(...)
    return result
```

**Daemon Safety:**
- **PID File:** `/tmp/cerberus_watcher_{project_hash}.pid`
- **Log File:** `{project}/.cerberus/watcher.log`
- **Lock File:** Prevent multiple daemons for same project
- **Graceful Shutdown:** Handle SIGTERM, SIGINT properly

**User Experience:**
```bash
# User runs any command - watcher auto-starts
$ cerberus search "auth logic"
⚙️  Starting background watcher... (PID: 12345)
[search results]

# Watcher keeps running in background

# Check watcher status
$ cerberus watcher status
✅ Watcher running (PID: 12345)
   Watching: /Users/dev/my-project
   Uptime: 2h 34m
   Last update: 45s ago

# Manually stop watcher
$ cerberus watcher stop
✅ Watcher stopped (PID: 12345)
```

#### 3.3 Hybrid Retrieval Optimization

**BM25 Implementation:**
- Use Okapi BM25 algorithm for keyword relevance
- Index symbol names, docstrings, comments
- Parameters: k1=1.5, b=0.75 (tunable)

**Vector Search Enhancement:**
- Keep existing sentence-transformers embedding
- Add support for custom embedding models
- Cache embeddings for faster startup

**Ranking Fusion:**
- **Reciprocal Rank Fusion (RRF):** Combine rankings from BM25 and Vector
- **Weighted Scoring:** `hybrid_score = α * bm25_score + (1-α) * vector_score`
- **Auto Mode:** Detect query type (keyword vs semantic) and adjust weights

**Query Type Detection:**
```python
def detect_query_type(query: str) -> str:
    # Heuristics for query type
    if is_camelcase(query) or is_snake_case(query):
        return "keyword"  # Searching for specific symbol

    if len(query.split()) <= 2:
        return "keyword"  # Short query, likely a symbol name

    if contains_technical_keywords(query):
        return "balanced"  # Mix of keyword and semantic

    return "semantic"  # Natural language query
```

**Retrieval Modes:**
- **keyword:** BM25 only (for exact symbol matches)
- **semantic:** Vector only (for conceptual queries)
- **balanced:** 50/50 fusion (default)
- **auto:** Automatically choose based on query

**Example:**
```bash
# Keyword query (auto-detected)
$ cerberus search "DatabaseConnection"
Mode: keyword (exact match prioritized)

# Semantic query (auto-detected)
$ cerberus search "code that handles user authentication"
Mode: semantic (conceptual matching)

# Force mode
$ cerberus search "auth" --mode balanced
```

### 4. CLI Integration

#### New Commands

**`cerberus watcher`**
```bash
# Start watcher (usually auto-starts, but can be manual)
cerberus watcher start --project . --index project.json

# Stop watcher
cerberus watcher stop

# Check watcher status
cerberus watcher status --json

# View watcher logs
cerberus watcher logs --follow

# Restart watcher
cerberus watcher restart
```

**`cerberus update`**
```bash
# Incrementally update index (respects git diff)
cerberus update --index project.json

# Force full re-index
cerberus update --index project.json --full

# Show what would be updated (dry-run)
cerberus update --index project.json --dry-run

# Update and show statistics
cerberus update --index project.json --stats
```

#### Enhanced Existing Commands

**`cerberus search`**
```bash
# Hybrid search (auto mode)
cerberus search "database connection logic"

# Force keyword mode
cerberus search "DatabaseConnection" --mode keyword

# Force semantic mode
cerberus search "authentication" --mode semantic

# Balanced mode with custom weights
cerberus search "auth" --mode balanced --keyword-weight 0.7
```

**`cerberus index`**
```bash
# Create index and auto-start watcher
cerberus index ./project -o project.json --watch

# Create index without watcher
cerberus index ./project -o project.json --no-watch
```

**`cerberus stats`**
```bash
# Show stats including incremental update info
cerberus stats --index project.json

# Output:
# Last indexed: 2026-01-08 14:30:00
# Last git commit: abc123de
# Incremental updates: 15 (since initial index)
# Symbols: 1,234 (45 updated incrementally)
# Watcher: Running (PID: 12345)
```

### 5. Configuration

**`incremental/config.py`**
```python
INCREMENTAL_CONFIG = {
    "enable_git_integration": True,
    "reparse_callers_on_signature_change": True,
    "max_affected_callers_to_reparse": 50,  # Limit for large graphs
    "store_git_commit_in_index": True,
    "fallback_to_full_reparse_threshold": 0.3,  # If >30% files changed, do full reparse
}

GIT_CONFIG = {
    "respect_gitignore": True,
    "compare_against": "HEAD",  # or "last_index_commit"
    "include_untracked": True,
}
```

**`watcher/config.py`**
```python
WATCHER_CONFIG = {
    "auto_start": True,  # Auto-start watcher on CLI commands
    "debounce_delay": 2.0,  # Seconds to wait after last change
    "event_batch_size": 10,  # Process events in batches
    "max_events_per_update": 100,  # Limit events per update cycle
    "shutdown_idle_timeout": 3600,  # Shutdown after 1 hour of inactivity (0 = never)
}

MONITORING_CONFIG = {
    "watch_patterns": ["**/*.py", "**/*.ts", "**/*.js", "**/*.go"],
    "ignore_patterns": [
        "**/__pycache__/**",
        "**/node_modules/**",
        "**/.venv/**",
        "**/build/**",
        "**/dist/**",
    ],
    "recursive": True,
}

IPC_CONFIG = {
    "socket_path": "/tmp/cerberus_watcher_{project_hash}.sock",
    "pid_file": "/tmp/cerberus_watcher_{project_hash}.pid",
    "log_file": "{project}/.cerberus/watcher.log",
}
```

**`retrieval/config.py`**
```python
HYBRID_SEARCH_CONFIG = {
    "default_mode": "auto",  # "keyword", "semantic", "balanced", "auto"
    "keyword_weight": 0.5,  # For balanced mode
    "semantic_weight": 0.5,
    "top_k_per_method": 20,  # Retrieve top 20 from each method before fusion
    "final_top_k": 10,  # Return top 10 after fusion
}

BM25_CONFIG = {
    "k1": 1.5,  # Term frequency saturation
    "b": 0.75,  # Length normalization
    "min_doc_freq": 1,  # Minimum document frequency
    "max_doc_freq_ratio": 0.9,  # Ignore terms in >90% of docs
}

VECTOR_CONFIG = {
    "model": "all-MiniLM-L6-v2",  # Default embedding model
    "batch_size": 32,
    "normalize_embeddings": True,
    "cache_embeddings": True,
}
```

### 6. Testing Strategy

**Unit Tests (`tests/test_phase3.py`):**
```python
class TestGitDiffParsing:
    def test_parse_unified_diff()
    def test_identify_changed_lines()
    def test_map_lines_to_symbols()

class TestChangeAnalysis:
    def test_detect_added_files()
    def test_detect_modified_files()
    def test_detect_deleted_files()
    def test_identify_affected_symbols()

class TestSurgicalUpdate:
    def test_update_single_symbol()
    def test_update_with_signature_change()
    def test_reparse_affected_callers()
    def test_fallback_to_full_reparse()

class TestWatcherDaemon:
    def test_daemon_start_stop()
    def test_filesystem_event_detection()
    def test_debounce_logic()
    def test_auto_start_on_cli_command()

class TestHybridSearch:
    def test_bm25_search()
    def test_vector_search()
    def test_ranking_fusion()
    def test_query_type_detection()
    def test_search_mode_keyword()
    def test_search_mode_semantic()
    def test_search_mode_balanced()
```

**Integration Tests (`tests/test_phase3_integration.py`):**
- Full incremental update workflow
- Watcher + incremental update pipeline
- Hybrid search with real index
- CLI command integration

**Test Data:**
- `tests/fixtures/git_diffs/` - Sample git diff files
- `tests/fixtures/watcher_events/` - Simulated filesystem events

### 7. Dependencies

**New Dependencies:**
```
watchdog>=3.0.0  # Cross-platform filesystem monitoring
rank-bm25>=0.2.2  # BM25 implementation
psutil>=5.9.0  # Process management for daemon
```

**Update `requirements.txt`:**
```bash
# Phase 3: Operational Excellence
watchdog>=3.0.0
rank-bm25>=0.2.2
psutil>=5.9.0
```

### 8. Rollout Plan

#### Milestone 3.1: Git-Native Incrementalism
- [ ] Implement git diff parsing
- [ ] Build change analysis engine
- [ ] Implement surgical update logic
- [ ] CLI command: `cerberus update`
- [ ] Unit tests for incremental updates
- [ ] Integration tests with real git repos

#### Milestone 3.2: Background Watcher
- [ ] Implement daemon lifecycle management
- [ ] Add filesystem monitoring with watchdog
- [ ] Build event processing pipeline
- [ ] Implement IPC for CLI ↔ daemon communication
- [ ] Add auto-start logic to CLI commands
- [ ] CLI command: `cerberus watcher`
- [ ] Unit tests for watcher
- [ ] Integration tests for daemon operations

#### Milestone 3.3: Hybrid Retrieval
- [ ] Implement BM25 keyword search
- [ ] Refactor vector search into separate module
- [ ] Build ranking fusion engine
- [ ] Add query type detection
- [ ] Enhance `cerberus search` with hybrid modes
- [ ] Unit tests for hybrid search
- [ ] Integration tests with real queries

### 9. Success Criteria

Phase 3 is complete when:
1. ✅ Incremental updates are 10x faster than full re-indexing for <20% file changes
2. ✅ Watcher daemon auto-starts and keeps index synchronized in real-time
3. ✅ Watcher runs stably for 24+ hours without crashes
4. ✅ Hybrid search combines BM25 and Vector effectively
5. ✅ Search mode auto-detection works correctly for different query types
6. ✅ All new commands support `--json` output
7. ✅ Comprehensive tests pass (unit + integration)
8. ✅ Documentation is complete
9. ✅ Cerberus can incrementally update its own index (dogfooding)

### 10. Aegis Robustness Compliance

**Logging:**
- Structured logs for incremental updates (what was changed, why)
- Daemon logs in `{project}/.cerberus/watcher.log`
- Performance tracing for surgical updates
- Agent-friendly JSON logs in `cerberus_agent.log`

**Error Handling:**
- `IncrementalUpdateError` - Surgical update failures
- `WatcherError` - Daemon lifecycle issues
- `GitIntegrationError` - Git diff parsing failures
- `HybridSearchError` - Ranking fusion issues

**Doctor Integration:**
```bash
# Check git integration
cerberus doctor --check-git

# Check watcher daemon status
cerberus doctor --check-watcher

# Validate incremental update capability
cerberus doctor --check-incremental

# Check BM25 index health
cerberus doctor --check-search
```

### 11. Performance Targets

**Incremental Updates:**
- **Small Changes (<5% files):** <1 second
- **Medium Changes (5-20% files):** 1-5 seconds
- **Large Changes (>20% files):** Fallback to full reparse (with warning)

**Watcher Daemon:**
- **Memory Footprint:** <50 MB
- **CPU Usage (Idle):** <1%
- **Event Processing:** <100ms per event batch
- **Debounce Latency:** 2 seconds (configurable)

**Hybrid Search:**
- **BM25 Search:** <50ms for 1000 symbols
- **Vector Search:** <100ms for 1000 symbols (with cached embeddings)
- **Ranking Fusion:** <10ms
- **Total Query Time:** <200ms

### 12. User Experience Goals

**Invisibility:**
- Watcher should "just work" without user thinking about it
- Auto-start should be seamless and fast (<500ms)
- Updates should happen in background without blocking CLI

**Transparency:**
- Clear status messages when watcher starts/stops
- `cerberus watcher status` provides detailed diagnostics
- `cerberus update --dry-run` shows what would be updated

**Speed:**
- Incremental updates should feel instantaneous (<1s)
- No waiting for full re-indexing after small code changes
- Search should be fast enough for interactive use (<200ms)

---

**Date:** 2026-01-08
**Status:** Design Complete, Ready for Implementation
**Next Step:** Milestone 3.1 - Git-Native Incrementalism

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Commands (Typer)                     │
│  index | search | get-symbol | watcher | update | doctor    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Background Watcher                        │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │ Daemon      │   │ Filesystem   │   │ Event Handler   │  │
│  │ Manager     │◀─▶│ Monitor      │──▶│ (Incremental    │  │
│  │             │   │ (watchdog)   │   │  Updates)       │  │
│  └─────────────┘   └──────────────┘   └─────────────────┘  │
│         │                                       │            │
│         ▼                                       ▼            │
│   [IPC Socket]                         [Index Updates]      │
└─────────────────────────────────────────────────────────────┘
                     │                             │
                     ▼                             ▼
┌─────────────────────────────────────────────────────────────┐
│              Incremental Update Engine                       │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐ │
│  │ Git Diff     │──▶│ Change       │──▶│ Surgical        │ │
│  │ Parser       │   │ Analyzer     │   │ Updater         │ │
│  └──────────────┘   └──────────────┘   └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                    Hybrid Retrieval                          │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐ │
│  │ BM25         │   │ Vector       │   │ Ranking         │ │
│  │ Search       │──▶│ Search       │──▶│ Fusion (RRF)    │ │
│  └──────────────┘   └──────────────┘   └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                   Index Store (JSON)                         │
│  Symbols | Types | Call Graph | Embeddings | Metadata       │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Design Principles

1. **Invisibility First:** The watcher should be invisible to users - auto-start, auto-stop, zero configuration
2. **Speed Matters:** Incremental updates must feel instant; no waiting for full re-indexing
3. **Deterministic Core:** Git-based change detection is deterministic and reliable
4. **Graceful Degradation:** If incremental update fails, fall back to full reparse
5. **Cross-Platform:** Watcher must work on macOS, Linux, Windows
6. **Process Isolation:** Watcher runs as separate process, not thread (crash isolation)
7. **Smart Defaults:** Auto mode for search should "just work" for 90% of queries

---

**Ready to begin Phase 3 implementation.**
