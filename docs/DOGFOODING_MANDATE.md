# Cerberus 100% Dogfooding Mandate

**Status:** Enforced as of v0.7.0
**Date:** 2026-01-09
**Severity:** CRITICAL - Mission-critical compliance requirement

---

## The Problem

During Phase 7 implementation, the AI agent violated dogfooding by using standard Claude Code tools (`Grep`, `Read`, `Glob`) instead of Cerberus commands when exploring the codebase.

### Specific Violations

**Line 62635:** Attempted `cerberus grep` with wrong syntax (`--output-mode`)
```bash
cerberus grep "from.*embeddings import" --output-mode files_with_matches
# ERROR: No such option: --output-mode
```

**Line 62878:** Immediately fell back to standard `Grep` tool
```python
Grep(pattern: "from.*embeddings|embed_texts|get_model")
```

**Lines 63537+:** Used standard `Read` tool instead of `cerberus read`
```python
Read(file_path: "src/cerberus/semantic/embeddings.py")
```

### Root Causes

1. **Weak Mandate:** CERBERUS.md said "use commands" but didn't forbid standard tools
2. **No Error Recovery:** No guidance on checking `--help` before fallback
3. **Path of Least Resistance:** Standard tools are powerful and familiar
4. **Missing Examples:** No clear syntax examples for grep/read commands

---

## The Solution

### Updated CERBERUS.md with 3 Enforcement Layers

#### 1. Forbidden List (Line 30)
```
standard_tools_when_indexed → use cerberus grep/read/search NOT Grep/Read/Glob
```

#### 2. Decision Matrix Rule (@exploration - Line 54-58)
```
@exploration:
  REQUIRE: cerberus_commands_only WHEN: index_exists
  IF: uses_grep_read_glob_tools THEN: [STOP, "Use cerberus grep/read/search instead"]
  IF: cerberus_cmd_fails THEN: check_help_syntax NOT fallback_to_standard_tools
  PATTERN: 100%_dogfooding_mandate
```

#### 3. Exploration Protocol (Line 84-94)
```markdown
## EXPLORATION [PROTOCOL]
- Index Cerberus itself before exploration (REQUIRED for dogfooding).
- **MANDATORY:** Use Cerberus commands for ALL exploration:
  - Pattern search: `cerberus grep "pattern" [path] -l` (files) or `-C 3` (context)
  - Read files: `cerberus read <file> [--lines 1-100]`
  - Find symbols: `cerberus get-symbol <name> [--file path]`
  - Search code: `cerberus search "query" [--mode keyword]`
  - Dependencies: `cerberus deps <symbol>`
- **FORBIDDEN:** Direct use of Grep, Read, Glob tools when index exists.
- If command fails: Check `cerberus <cmd> --help`, adjust syntax, NEVER fallback.
```

#### 4. Quick Reference Examples (Line 96-108)
```bash
# Exploration (100% Dogfooding)
cerberus grep "def.*parse" src/ -l          # Find files with pattern
cerberus grep "import.*embeddings" . -C 2   # Pattern with context
cerberus read src/cerberus/main.py --lines 1-100  # Read file range
cerberus get-symbol SQLiteIndexStore        # Get symbol definition
cerberus search "fts5 implementation"       # Search code
cerberus deps hybrid_search                 # Symbol dependencies
cerberus smart-context <symbol>             # Full context assembly
```

---

## Correct Command Syntax

### Pattern Matching
```bash
# WRONG: Standard tool
Grep(pattern: "from.*embeddings", output_mode: "files_with_matches")

# CORRECT: Cerberus command
cerberus grep "from.*embeddings" -l  # Files only
cerberus grep "from.*embeddings" -C 3  # With 3 lines context
cerberus grep "from.*embeddings" src/ -l  # Specific directory
```

### File Reading
```bash
# WRONG: Standard tool
Read(file_path: "src/cerberus/semantic/embeddings.py")

# CORRECT: Cerberus command
cerberus read src/cerberus/semantic/embeddings.py
cerberus read src/cerberus/semantic/embeddings.py --lines 1-50
cerberus read src/cerberus/semantic/embeddings.py --skeleton
```

### Symbol Lookup
```bash
# WRONG: Reading entire file to find symbol
Read(file_path: "src/cerberus/storage/sqlite_store.py")

# CORRECT: Direct symbol retrieval
cerberus get-symbol SQLiteIndexStore
cerberus get-symbol fts5_search --file src/cerberus/storage/sqlite_store.py
```

### Code Search
```bash
# WRONG: Using Glob + Grep combination
Glob(pattern: "**/*.py")
Grep(pattern: "def.*search")

# CORRECT: Integrated search
cerberus search "search function" --mode keyword
cerberus grep "def.*search" src/ -l
```

---

## Command Reference

| Task | Standard Tool | Cerberus Command | Flags |
|------|---------------|------------------|-------|
| List matching files | `Grep(..., output_mode="files_with_matches")` | `cerberus grep "pattern" -l` | `-l` (files only) |
| Show matches with context | `Grep(..., -C=3)` | `cerberus grep "pattern" -C 3` | `-C N` (context lines) |
| Case-insensitive search | `Grep(..., -i=True)` | `cerberus grep "pattern" -i` | `-i` (ignore case) |
| Count matches | `Grep(..., output_mode="count")` | `cerberus grep "pattern" -c` | `-c` (count only) |
| Read full file | `Read(file_path)` | `cerberus read <file>` | None |
| Read file range | `Read(file_path, offset, limit)` | `cerberus read <file> --lines 10-50` | `--lines START-END` |
| Read skeleton | N/A | `cerberus read <file> --skeleton` | `--skeleton` |
| Find files | `Glob(pattern)` | `cerberus ls "pattern"` | Use grep instead |
| Get symbol | `Read(file) + manual search` | `cerberus get-symbol <name>` | None |
| Search codebase | Multiple tools | `cerberus search "query"` | `--mode keyword` |

---

## Error Recovery Protocol

When a Cerberus command fails:

### ❌ WRONG: Immediate fallback
```python
# Command fails
cerberus grep "pattern" --invalid-flag
# Agent immediately uses: Grep(pattern="pattern")
```

### ✅ CORRECT: Check help and retry
```python
# Command fails
cerberus grep "pattern" --invalid-flag

# Agent checks help
cerberus grep --help

# Agent identifies correct syntax
cerberus grep "pattern" -l  # Success!
```

---

## Benefits of 100% Dogfooding

### 1. **Token Savings**
- Standard tools return raw file contents (high tokens)
- Cerberus returns structured, indexed results (low tokens)
- Example: 90.4% token savings reported during Phase 7

### 2. **Speed**
- Cerberus queries SQLite index (milliseconds)
- Standard tools scan entire filesystem (seconds)

### 3. **Accuracy**
- Cerberus understands code structure (AST-aware)
- Standard tools use regex (fragile)

### 4. **Mission Alignment**
- Demonstrates Cerberus's value proposition
- Validates the tool works as designed
- Builds confidence in the product

### 5. **Index Coverage Validation**
- If Cerberus can't find it, the index needs improvement
- Exposes gaps in indexing/search capabilities

---

## Enforcement Strategy

### For AI Agents
1. **Always index first:** Run `cerberus index .` before exploration
2. **Check index exists:** If `cerberus.db` exists, standard tools are forbidden
3. **Command fails? Check help:** Never fallback without trying `--help`
4. **Report gaps:** If Cerberus can't do something, report as limitation

### For Code Reviewers
1. Check conversation logs for `Grep`, `Read`, `Glob` tool usage
2. Flag any usage when `cerberus.db` exists
3. Require refactor to use Cerberus commands

### For Testing
Add test that validates:
```python
def test_no_standard_tools_in_dogfooding():
    """Ensure Cerberus uses own commands for exploration."""
    # Parse conversation logs
    # Assert no Grep/Read/Glob when index exists
    pass
```

---

## Future Improvements

### 1. Add `cerberus glob` Command
Currently no direct equivalent to `Glob(pattern="**/*.py")`.

**Proposal:**
```bash
cerberus ls "**/*.py"  # List files matching pattern
cerberus ls "src/**/*.py" --type f  # Files only
```

### 2. Add Doctor Check
```bash
cerberus doctor
# Add validation: "Dogfooding compliance check"
# - Verify index exists
# - Check for standard tool usage in logs
# - Report compliance score
```

### 3. Streaming Output Mode
```bash
cerberus grep "pattern" --stream  # Yield results as found
cerberus read file.py --stream   # Stream file content
```

### 4. JSON Output Everywhere
```bash
cerberus grep "pattern" --json  # Already exists
cerberus read file.py --json    # Add this
cerberus ls "**/*.py" --json    # Add this
```

---

## Metrics

**Before Mandate:**
- 3 violations during Phase 7 (Grep, Read tools used)
- ~7,500 tokens unnecessarily consumed

**After Mandate:**
- 0 violations expected
- 90%+ token savings maintained
- Faster exploration (SQLite queries vs filesystem scans)

---

## References

- [CERBERUS.md](../CERBERUS.md) - Updated agent context (v0.7.0)
- [PHASE7_MEMORY_OPTIMIZATION_COMPLETE.md](./PHASE7_MEMORY_OPTIMIZATION_COMPLETE.md) - Where violation occurred
- [ROADMAP.md](./ROADMAP.md) - Phase overview

---

**Dogfooding Mandate Status:** ✅ **ENFORCED**
**Version:** v0.7.0+
**Last Updated:** 2026-01-09
