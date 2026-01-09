# Cerberus Dogfooding Improvements

**Date:** 2026-01-09
**Context:** Phase 7 Track B - De-Monolithization
**Trigger:** Critical dogfooding mandate violation - agent abandoned Cerberus when bugs were encountered

---

## Critical Incident Report

### What Happened

During Phase 7 Track B refactoring work, the AI agent encountered a bug in `cerberus read` and **abandoned Cerberus entirely**, falling back to standard Unix tools (grep, cat, find) for the rest of the session.

### Violations Committed

1. **Silent fallback** - Switched to standard tools without reporting the bug
2. **No bug fix** - Did not attempt to fix cerberus when it failed
3. **No improvement proposal** - Did not propose missing features
4. **Violated dogfooding mandate** - Used Grep tool instead of cerberus grep
5. **Lost validation opportunity** - Never proved cerberus works on its own codebase

### Impact

- **Missed 2+ bugs** that would have been found through dogfooding
- **Lost improvement opportunities** for cerberus grep performance
- **Set bad precedent** for future AI agents
- **Failed mission-critical testing** - cerberus reading its own code

---

## Bugs Fixed

### 1. ✅ cerberus read - Rich Markup Escaping Bug

**Location:** `src/cerberus/main.py:408`

**Problem:**
```python
# Line 408 - BEFORE FIX
console.print(f"[dim]{i:5}[/dim] | {line}")
```

When file content contains Rich markup characters (like `[/]`, `[red]`, etc.), Rich tries to parse them as formatting tags, causing `MarkupError`.

**Root Cause:**
- Line 85 of main.py contains: `status_color = {"ok": "green", "warn": "yellow", "fail": "red"}.get(item["status"], "white")`
- The `[/]` in the dict was interpreted as a closing tag

**Fix:**
```python
# Import escape at top
from rich.markup import escape

# Line 408 - AFTER FIX
console.print(f"[dim]{i:5}[/dim] | {escape(line)}")

# Also fixed error messages (19 instances)
console.print(f"[red]Error: {escape(str(e))}[/red]")
```

**Test:**
```bash
cerberus read src/cerberus/main.py --lines 1-100
# ✅ Works perfectly now
```

---

## Features Added

### 2. ✅ cerberus grep -n Flag

**Missing Feature:** Line numbers in grep-compatible format

**What Agent Needed:**
```bash
# What agent used (VIOLATION)
grep -n "^def " src/cerberus/main.py

# What agent should have used (but couldn't)
cerberus grep "^def " src/cerberus/main.py -n  # ❌ Flag didn't exist
```

**Why It Was Missing:**
- cerberus grep had line numbers internally (stored in match data)
- But no `-n` flag to output in grep-compatible format (`file:line:content`)
- Agent needed this for systematic code analysis

**Implementation:**
```python
# Added parameter
line_numbers: bool = typer.Option(False, "-n", help="Show line numbers in grep format (file:line:content).")

# Added output format
elif line_numbers:
    # grep -n style: file:line:content
    for match in result["matches"]:
        typer.echo(f"{result['file']}:{match['line_number']}:{match['content']}")
```

**Test:**
```bash
cerberus grep "^def " src/cerberus/main.py -n | head -5
# Output:
# src/cerberus/main.py:32:def hello():
# src/cerberus/main.py:40:def version():
# src/cerberus/main.py:47:def doctor(
# ✅ Perfect grep -n compatible format!
```

---

## Mandate Enforcement Strengthened

### Updated CERBERUS.md

**Location:** `CERBERUS.md:55-67`

**Changes:**

```markdown
@exploration:
  REQUIRE: cerberus_commands_only ALWAYS  # Changed from "WHEN: index_exists"
  IF: uses_grep_read_glob_tools THEN: [STOP, propose_cerberus_command, explain_why, ask_to_implement_or_continue]
  IF: cerberus_cmd_missing THEN: [STOP, "Cerberus needs [command]. Implement? Or use workaround?", get_user_approval]
  IF: cerberus_cmd_fails THEN: [STOP, FIX_CERBERUS_BUG, NOT fallback_to_standard_tools]  # NEW!
  NEVER: silent_fallback_to_standard_tools  # NEW!
  PATTERN: 100%_dogfooding_mandate + continuous_improvement

  ENFORCEMENT [ZERO_TOLERANCE]:  # NEW SECTION!
    - cerberus command fails → STOP task, FIX bug, THEN continue
    - missing feature → STOP, propose implementation, get approval
    - standard tool usage → VIOLATION (Grep/Read/Glob/etc.)
    - every fallback MUST be explicit and user-approved
```

**Key Changes:**
1. **ALWAYS** use cerberus (not just when index exists)
2. **STOP and FIX** when cerberus fails (not fallback)
3. **NEVER** silent fallback to standard tools
4. **ZERO TOLERANCE** enforcement section added

---

## Remaining Limitations Found

### Performance Issues

**Observation:** Agent noted cerberus grep seemed slower than standard grep

**Evidence Needed:**
- Benchmark cerberus grep vs ripgrep on large codebase
- Profile to find bottlenecks
- Consider using ripgrep as backend (like Grep tool does)

**Status:** ⏸️ Needs investigation

### Potential Improvements

1. **cerberus grep performance**
   - Consider using ripgrep subprocess (like Claude's Grep tool)
   - Add caching for repeated searches
   - Optimize file scanning

2. **Output format options**
   - Add `--format` flag for customizable output
   - Support machine-readable formats (CSV, TSV)
   - Color coding options

3. **Error messages**
   - More helpful error messages when patterns fail
   - Suggest corrections for common mistakes
   - Show examples in help text

---

## Testing Checklist

- [x] cerberus read works on main.py (with Rich markup)
- [x] cerberus grep -n outputs grep-compatible format
- [x] All 19 error message escaping fixes applied
- [x] CERBERUS.md enforcement section updated
- [ ] Run full test suite (pending)
- [ ] cerberus can index itself (pending)
- [ ] Performance benchmark cerberus grep (pending)

---

## Lessons for AI Agents

### ❌ What Went Wrong

**Agent's Flawed Thought Process:**
> "Cerberus has a bug → I need to keep moving on refactoring → Let me use grep instead → I'll come back to this later"

**Why This Was Wrong:**
- Violated dogfooding mandate
- Lost validation opportunity
- Set bad precedent
- Failed the mission test

### ✅ Correct Workflow

**When cerberus fails:**
1. **STOP** the current task immediately
2. **REPORT** the bug to the user
3. **FIX** the bug in cerberus
4. **TEST** the fix
5. **CONTINUE** with cerberus (not workarounds)

**When cerberus lacks a feature:**
1. **PAUSE** and document what's needed
2. **PROPOSE** implementing it in cerberus
3. **GET PERMISSION** before any fallback
4. **IMPLEMENT** if approved
5. **DOCUMENT** the improvement

### 🎯 The Right Mindset

**Wrong:** "The task is to refactor main.py. Cerberus is just a tool to help."

**Right:** "The task is to DOGFOOD cerberus while refactoring. If cerberus fails, fixing cerberus IS the task."

---

## Next Steps

1. ✅ Commit these improvements
2. ⏸️ Re-do Phase 7 exploration using ONLY cerberus
3. ⏸️ Document every limitation found
4. ⏸️ Benchmark performance
5. ⏸️ Implement improvements

---

**Conclusion:** This incident revealed critical gaps in dogfooding enforcement. The fixes and stronger mandates ensure future AI agents will **stop, fix, and improve** Cerberus rather than abandoning it.
