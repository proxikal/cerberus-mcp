# Cerberus MCP Transformation

## Executive Summary

Transform Cerberus from a CLI tool to a native MCP (Model Context Protocol) server, enabling direct integration with Claude Code and other MCP clients.

**Key Decisions:**
- Full CLI replacement (MCP is the only interface)
- Python + FastMCP (direct core library integration)
- 24 core tools covering search, memory, editing, and analysis
- Zero-config auto-discovery with optional config file

## Phase Overview

| Phase | Focus | Tools Added | Effort |
|-------|-------|-------------|--------|
| **1** | MCP skeleton | 3 (search, get_symbol, read_range) | Small |
| **2** | Index manager | 2 (index_build, index_status) | Medium |
| **3** | Memory system | 8 (memory_*) + 1 (blueprint) | Medium |
| **4** | Editing | 5 (edit, insert, delete, undo, history) | Medium |
| **5** | Quality + Metrics | 6 (style_*, metrics_*, deps, call_graph) | Medium |
| **6** | Cleanup | 0 (removal only) | Small |
| **7** | Testing + Docs | 0 (tests and docs) | Medium |

## Tool Summary (24 Total)

### Read Tools (5)
- `search` - Hybrid keyword + semantic search
- `get_symbol` - Symbol lookup with code
- `read_range` - Read file lines
- `blueprint` - File structure view
- `index_status` - Index health

### Memory Tools (8)
- `memory_learn` - Teach preferences/decisions
- `memory_show` - View memory
- `memory_context` - Generate context
- `memory_extract` - Git pattern extraction
- `memory_forget` - Remove entry
- `memory_stats` - Storage stats
- `memory_export` - Backup
- `memory_import` - Restore

### Edit Tools (5)
- `edit_symbol` - Surgical code edit
- `insert_code` - Add code
- `delete_symbol` - Remove code
- `undo` - Revert change
- `undo_history` - View undo stack

### Analysis Tools (3)
- `deps` - Dependencies
- `call_graph` - Execution paths
- `index_build` - Create/rebuild index

### Quality Tools (3)
- `style_check` - Check violations
- `style_fix` - Auto-fix
- `related_changes` - Suggest related

### Metrics Tools (3 - counted in Quality)
- `metrics_report` - Efficiency report
- `metrics_clear` - Reset
- `metrics_status` - Status

## Architecture

```
┌─────────────────┐
│   Claude Code   │
└────────┬────────┘
         │ MCP Protocol
┌────────▼────────┐
│  FastMCP Server │
│   (server.py)   │
└────────┬────────┘
         │ Direct Python calls
┌────────▼────────┐
│  Index Manager  │
│  (lazy + watch) │
└────────┬────────┘
         │
┌────────▼────────────────────────┐
│         Core Library            │
├─────────┬─────────┬─────────────┤
│ parser/ │storage/ │ retrieval/  │
│mutation/│ memory/ │ blueprint/  │
│quality/ │metrics/ │ resolution/ │
└─────────┴─────────┴─────────────┘
```

## File Structure After Transformation

```
src/cerberus/
├── mcp/                    # NEW: MCP server
│   ├── __init__.py
│   ├── server.py
│   ├── config.py
│   ├── index_manager.py
│   ├── validation.py
│   └── tools/
│       ├── search.py
│       ├── symbols.py
│       ├── reading.py
│       ├── indexing.py
│       ├── memory.py
│       ├── structure.py
│       ├── editing.py
│       ├── quality.py
│       ├── metrics.py
│       └── analysis.py
│
├── cli/                    # REMOVED
├── daemon/                 # REMOVED
│
├── parser/                 # Kept
├── storage/                # Kept
├── retrieval/              # Kept
├── mutation/               # Kept
├── memory/                 # Kept
├── blueprint/              # Kept
├── quality/                # Kept
├── metrics/                # Kept
├── resolution/             # Kept
├── watcher/                # Kept (repurposed)
└── ...
```

## Implementation Order

```
Phase 1 ──▶ Phase 2 ──▶ Phase 3 ──▶ Phase 4 ──▶ Phase 5 ──▶ Phase 6 ──▶ Phase 7
  │           │           │           │           │           │           │
  ▼           ▼           ▼           ▼           ▼           ▼           ▼
Skeleton   IndexMgr    Memory     Editing    Quality    Cleanup    Testing
 3 tools   +watching   8 tools    5 tools    6 tools   -CLI/daemon  +docs
```

Each phase is independently deployable - you can stop after any phase and have a working (if incomplete) MCP server.

## Success Criteria

After Phase 7:
- [ ] Claude Code connects and uses all tools
- [ ] Memory persists across sessions
- [ ] Edits are safe (syntax validation, backups, undo)
- [ ] No CLI or daemon code remains
- [ ] All tests pass
- [ ] Documentation complete

## Quick Reference

**Start MCP server:**
```bash
cerberus-mcp
# or
python -m cerberus.mcp
```

**Claude Code config:**
```json
{
  "mcpServers": {
    "cerberus": {
      "command": "cerberus-mcp"
    }
  }
}
```

**Phase documents:**
- [Phase 1: MCP Skeleton](./mcp-phase-1.md)
- [Phase 2: Index Manager](./mcp-phase-2.md)
- [Phase 3: Memory System](./mcp-phase-3.md)
- [Phase 4: Editing Tools](./mcp-phase-4.md)
- [Phase 5: Quality + Metrics](./mcp-phase-5.md)
- [Phase 6: CLI/Daemon Removal](./mcp-phase-6.md)
- [Phase 7: Testing + Docs](./mcp-phase-7.md)
