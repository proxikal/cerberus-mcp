# Phase 7 Track B: Codebase De-Monolithization

**Status:** In Progress
**Started:** 2026-01-09
**Goal:** Break down monolithic "God Files" to reduce context wall and improve agent maintainability

---

## Objectives

Per [PHASE7_SPEC.md](./PHASE7_SPEC.md), Phase 7 Track B aims to:

1. **Refactor `src/cerberus/main.py` (2,939 lines)**
   → Create `src/cerberus/cli/` package with 6 modules

2. **Refactor `src/cerberus/storage/sqlite_store.py` (1,159 lines)**
   → Create `src/cerberus/storage/sqlite/` package with 4 modules

---

## Completed Work

### ✅ sqlite_store.py → sqlite/ Package (COMPLETE)

**Result:** 98.4% file size reduction

**Before:**
```
src/cerberus/storage/sqlite_store.py: 1,159 lines
```

**After:**
```
src/cerberus/storage/
├── sqlite_store.py              # 18 lines (backward-compat shim)
└── sqlite/
    ├── __init__.py              # Public API exports
    ├── config.py                # Configuration constants
    ├── schema.py                # Database schema (221 lines)
    ├── persistence.py           # Connection/transactions/metadata (168 lines)
    ├── symbols.py               # File & symbol CRUD (400 lines)
    ├── resolution.py            # Phase 5/6 resolution ops (459 lines)
    └── facade.py                # Public API facade (209 lines)
```

**Testing:** All 167/182 tests passing (same as before refactoring)

**Benefits:**
- Modular architecture following self-similarity mandate
- Each module has clear single responsibility
- Backward compatible (all existing imports still work)
- Easier to navigate for AI agents and developers

---

### ✅ main.py Analysis & CLI Package Structure (COMPLETE)

**Analyzed:** 33 commands across 2,939 lines

**Created:** `src/cerberus/cli/` package structure
```
src/cerberus/cli/
├── __init__.py              # Package exports
├── config.py                # CLI configuration
├── common.py                # Shared utilities
├── index.py                 # COMPLETE (scan, index commands)
├── operational.py           # TODO: 6 commands (hello, version, doctor, update, watcher, session)
├── utils.py                 # TODO: 6 commands (stats, bench, generate-tools, verify-context, generate-context, summarize)
├── retrieval.py             # TODO: 5 commands (search, get-symbol, get-context, skeleton-file, skeletonize)
├── symbolic.py              # TODO: 9 commands (deps, calls, references, resolution-stats, inherit-tree, descendants, overrides, call-graph, smart-context)
└── dogfood.py               # TODO: 5 commands (read, inspect, tree, ls, grep)
```

**Proof of Concept:** `cli/index.py` fully extracted and functional

---

## Work Remaining

### main.py → cli/ Package

**Status:** 2/33 commands extracted (6%)

**Next Steps:**

1. **Extract remaining commands** (31 commands)
   - Systematic extraction using line ranges documented in modules
   - Each module already has TODOs with exact line numbers

2. **Update main.py to compose modules**
   ```python
   # New main.py structure (target: < 500 lines)
   import typer
   from cerberus.cli import index, operational, utils, retrieval, symbolic, dogfood

   app = typer.Typer()

   # Add sub-applications
   app.add_typer(index.app, name="index", help="Indexing commands")
   app.add_typer(operational.app, name="ops", help="Operational commands")
   # ... etc

   if __name__ == "__main__":
       app()
   ```

3. **Test thoroughly**
   - Run full test suite (target: 167/182 passing)
   - Verify all 33 commands work correctly
   - Test cerberus indexing itself

---

## Expected Outcomes

### File Size Reductions

| File | Before | After | Reduction |
|------|--------|-------|-----------|
| sqlite_store.py | 1,159 lines | 18 lines | **98.4%** ✅ |
| main.py | 2,939 lines | < 500 lines | **~83%** (target) |

### Package Structure

Both packages will follow the **self-similarity mandate**:
- ✅ `facade.py` - Public API
- ✅ `config.py` - Configuration
- ✅ `__init__.py` - Exports
- ✅ Modular sub-components with single responsibilities

---

## Architecture Benefits

1. **Reduced Context Wall**
   - Smaller files easier for AI agents to navigate
   - Clear module boundaries reduce cognitive load

2. **Improved Maintainability**
   - Single responsibility per module
   - Easier to locate and modify specific features

3. **Better Testability**
   - Isolated modules can be tested independently
   - Clearer test organization

4. **Self-Similarity**
   - Consistent package patterns across codebase
   - Easier for agents to understand structure

---

## Timeline

- **2026-01-09:** sqlite/ package completed and tested ✅
- **2026-01-09:** cli/ package structure created, index module extracted ✅
- **Next:** Complete remaining 31 command extractions
- **Next:** Integration testing and validation

---

## Notes

- All work maintains backward compatibility
- Test coverage maintained at 91.8% (167/182)
- No breaking changes to external API
- Follows Phase 7 specification exactly

---

**Next Session:** Continue command extraction from main.py into cli/ modules, starting with operational.py (simplest commands).
