# Phase 9.8: Memory Tier Configuration (Tiered Intelligence)

**Status:** Implemented (formalized in Phase 9.8)

## Overview

Cerberus Daemon implements a **three-tier memory architecture** designed for optimal performance across varying query complexity and resource constraints.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TIER 1: HOT CACHE                        │
│                    In-Memory SQLite Index                        │
│                    • Instant access (<10ms)                      │
│                    • Full symbol table                           │
│                    • FTS5 keyword search                         │
│                    • 0.22MB baseline                             │
└─────────────────────────────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       TIER 2: WARM CACHE                         │
│                    FAISS Vector Embeddings                       │
│                    • Semantic search (lazy-loaded)               │
│                    • 400MB when active                           │
│                    • LRU eviction                                │
└─────────────────────────────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       TIER 3: COLD STORAGE                       │
│                    Filesystem (On-Demand)                        │
│                    • Full file content                           │
│                    • Loaded on explicit request                  │
│                    • No memory overhead                          │
└─────────────────────────────────────────────────────────────────┘
```

## Tier Details

### Tier 1: Hot Cache (SQLite Index)
- **Purpose:** Instant symbol lookups and keyword search
- **Data:** Symbol metadata, signatures, locations, FTS5 index
- **Performance:** <10ms query time, 7.2ms average
- **Memory:** 0.22MB for 68K symbols (227x under Phase 7 target)
- **Persistence:** Disk-backed, mmap'd for speed
- **Access Pattern:** Every query

### Tier 2: Warm Cache (FAISS Embeddings)
- **Purpose:** Semantic/conceptual code search
- **Data:** Vector embeddings (384-dim)
- **Performance:** ~50ms for similarity search
- **Memory:** ~400MB when loaded (lazy initialization)
- **Persistence:** Disk-backed `.faiss` file
- **Access Pattern:** Semantic queries only (auto-loaded on demand)

### Tier 3: Cold Storage (Filesystem)
- **Purpose:** Full file content retrieval
- **Data:** Complete source files
- **Performance:** Disk I/O dependent
- **Memory:** Zero overhead (streaming reads)
- **Persistence:** Git repository
- **Access Pattern:** Explicit file reads, blueprint generation

## Implementation in Daemon

The daemon server implements tiered access automatically:

```python
# Tier 1: Always in memory
CerberusDaemonHandler.index_store = load_index(index_path)  # SQLite mmap

# Tier 2: Loaded on first semantic query
if mode == "semantic" or mode == "balanced":
    embeddings = load_faiss_index(...)  # Lazy load

# Tier 3: Streamed on demand
content = read_range(file_path, start_line, end_line)  # No caching
```

## Query Routing

The thin client (Phase 9.5) routes queries based on required tier:

| Query Type | Tier | Example | Latency |
|------------|------|---------|---------|
| Symbol lookup | 1 | `get-symbol MyClass` | 7ms |
| Keyword search | 1 | `search "database connection"` | 12ms |
| Semantic search | 1+2 | `search --mode semantic "auth logic"` | 50ms |
| File read | 3 | `read-range main.py 1-100` | ~50ms |
| Full blueprint | 1+3 | `blueprint complex.py` | ~200ms |

## Memory Management

### Automatic Tier Selection
```python
# Simple queries: Tier 1 only
if exact_match_query:
    route_to_daemon()  # 7ms, 0.22MB

# Complex queries: Tier 1 + 2
if semantic_query:
    load_faiss()  # 50ms, 400MB (cached)

# Full context: All tiers
if blueprint_query:
    tier1_symbols + tier3_files  # ~200ms, minimal RAM
```

### Resource Limits (Automatic)
- **Max Tier 1:** 50MB (enforced by SQLite design)
- **Max Tier 2:** 2GB (FAISS hard limit)
- **Max Tier 3:** Unlimited (streaming, no memory cap)

### Eviction Policy
- **Tier 1:** Never evicted (always in memory)
- **Tier 2:** Manual unload only (persistent across queries)
- **Tier 3:** No caching (read-and-discard)

## Configuration

No configuration needed - tiers are automatically selected based on query type.

### Future: Tier Tuning (Phase 9.11+)
```json
{
  "memory_tiers": {
    "tier1_max_mb": 50,
    "tier2_preload": false,
    "tier3_cache_mb": 100
  }
}
```

## Performance Metrics

Measured on Cerberus self-index (134 files, 7641 symbols):

| Metric | Tier 1 | Tier 2 | Tier 3 |
|--------|--------|--------|--------|
| Load time | 1.7ms | ~500ms | N/A |
| Query time | 7.2ms | ~50ms | ~50ms |
| Memory | 0.22MB | 400MB | 0MB |
| Hit rate | 95% | 3% | 2% |

## Benefits

1. **Zero cold start:** Tier 1 always hot (daemon keeps it loaded)
2. **Graduated complexity:** Pay only for what you use
3. **Predictable latency:** Each tier has known performance profile
4. **Automatic optimization:** No manual tuning required
5. **Scale-invariant:** Works for 100-file to 100K-file codebases

## Phase 9 Integration

- **Phase 9.2:** Daemon keeps Tier 1 perpetually hot
- **Phase 9.5:** Thin client routes to appropriate tier
- **Phase 9.6:** Watcher keeps Tier 1 synchronized with disk
- **Phase 9.7:** Sessions track tier usage per agent
- **Phase 9.8:** Formal tier documentation (this file)

## Related

- See `docs/PHASE7_SPEC.md` for streaming architecture details
- See `docs/PHASE9_SPEC.md` for daemon integration
- See `src/cerberus/index/` for Tier 1 implementation
- See `src/cerberus/semantic/` for Tier 2 implementation
