# Dogfooding PAUSE Protocol

**Purpose:** When AI agents need functionality not yet in Cerberus, PAUSE and propose instead of silently falling back to standard tools.

**Status:** Enforced as of v0.7.0
**Updated:** 2026-01-09

---

## The PAUSE Protocol

When an AI agent needs to use `Grep`, `Read`, `Glob`, or other standard tools on an indexed codebase:

### ❌ OLD BEHAVIOR (Forbidden)
```
Agent: *silently uses Grep tool*
Agent: *continues with task*
User: *never knows Cerberus had a gap*
```

### ✅ NEW BEHAVIOR (Required)
```
Agent: *detects need for standard tool*
Agent: PAUSE ⏸️
Agent: "I need to search for files matching '**/*.test.py' but Cerberus doesn't have a
        glob/ls command yet.

        Options:
        1. I can implement 'cerberus ls <pattern>' now (5-10 min)
        2. I can use the standard Glob tool as a workaround

        Which would you prefer?"
User: *makes informed decision*
Agent: *proceeds based on user choice*
```

---

## Scenario Examples

### Scenario 1: Missing Command

**Task:** "Find all test files in the project"

**Agent detects:** Need to use `Glob(pattern="**/*.test.py")`

**Agent response:**
```
⏸️ PAUSE - Cerberus Enhancement Needed

I need to find all files matching a pattern, but Cerberus doesn't have a direct
equivalent to the Glob tool yet.

Gap identified: `cerberus ls <pattern>` or `cerberus glob <pattern>`

Options:
1. ✅ Implement `cerberus ls` command now (~10 min)
   - Adds: cerberus ls "**/*.py" --type f
   - Uses existing index for instant results
   - Maintains 100% dogfooding

2. ⚠️ Use standard Glob tool (workaround)
   - Faster to proceed (immediate)
   - Breaks dogfooding mandate
   - Misses opportunity to improve Cerberus

Which approach should I take?
```

**User chooses Option 1:** Agent implements the command, tests it, then continues.
**User chooses Option 2:** Agent uses workaround, documents gap, continues.

---

### Scenario 2: Command Exists, Wrong Syntax

**Task:** "Find files importing embeddings module"

**Agent tries:** `cerberus grep "from.*embeddings" --output-mode files`

**Result:** `Error: No such option: --output-mode`

**Agent response:**
```
⏸️ Command Failed - Checking Syntax

My command failed: cerberus grep "from.*embeddings" --output-mode files
Error: No such option: --output-mode

Let me check the correct syntax...
*runs: cerberus grep --help*

Found it! The correct flag is -l (not --output-mode).

Retrying with: cerberus grep "from.*embeddings" -l

[continues automatically - no user action needed]
```

---

### Scenario 3: Command Exists, Insufficient Features

**Task:** "Find all TODO comments with 10 lines of context"

**Agent tries:** `cerberus grep "TODO" -C 10`

**Result:** Works, but output is cluttered

**Agent response:**
```
⏸️ Enhancement Opportunity Identified

The command works but could be improved:

Current: cerberus grep "TODO" -C 10
Issue: Returns too much output, hard to parse

Potential enhancement: cerberus grep "TODO" --json -C 10
- Would provide structured output
- Easier for agents to process
- Better UX

Options:
1. Continue with current command (works but suboptimal)
2. I can add --json flag to grep command (~5 min)

The task can proceed either way. Should I enhance first or continue?
```

---

### Scenario 4: No Gap, Just Wrong Tool Choice

**Task:** "Read the first 50 lines of main.py"

**Agent considers:** Using `Read` tool

**Agent self-corrects:**
```
✅ Self-Correction

I was about to use the standard Read tool, but Cerberus has this:

  cerberus read src/cerberus/main.py --lines 1-50

Using Cerberus command instead. [continues immediately]
```

**No pause needed** - agent caught itself before violating mandate.

---

## Decision Tree

```
┌─────────────────────────────────────┐
│ Need to explore/read code?          │
└──────────────┬──────────────────────┘
               │
               ▼
        ┌──────────────┐
        │ Index exists? │
        └──────┬───────┘
               │
         ┌─────┴─────┐
         │           │
       YES          NO
         │           │
         │           └──→ Use standard tools (OK)
         │
         ▼
   ┌──────────────────────┐
   │ Cerberus cmd exists?  │
   └──────┬───────────────┘
          │
    ┌─────┴─────┐
    │           │
   YES          NO
    │           │
    │           └──→ PAUSE, propose enhancement
    │
    ▼
┌──────────────────┐
│ Try Cerberus cmd │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
  SUCCESS   FAIL
    │         │
    │         └──→ Check --help, retry
    │              If still fails → explain to user
    │
    └──→ Continue with task
```

---

## Implementation Checklist

When proposing a Cerberus enhancement, agent should:

### 1. Clearly State the Gap
```
Gap: Cerberus lacks [feature]
Current workaround: [standard tool]
Proposed: cerberus [new-command]
```

### 2. Provide Options
```
Option 1: Implement now (~X min)
  - Benefits: [list]
  - Effort: [estimate]

Option 2: Use workaround
  - Benefits: [list]
  - Tradeoffs: [list]
```

### 3. Estimate Effort Honestly
- Simple flag addition: ~5 min
- New command: ~10-15 min
- Complex feature: ~30 min+
- If unsure: "Unknown - would need to investigate architecture first"

### 4. Document Decision
```
User chose: [Option X]
Reason: [if provided]
Status: [proceeding/implementing]
```

---

## Benefits of PAUSE Protocol

### 1. **Continuous Improvement**
Every gap becomes an opportunity to make Cerberus better

### 2. **User Control**
User decides speed vs. quality tradeoff for each situation

### 3. **Transparency**
No silent fallbacks - user always knows what's happening

### 4. **Living Documentation**
Gaps are discovered and fixed organically through usage

### 5. **Workflow Continuity**
Agent doesn't fully stop - just pauses for decision

---

## Anti-Patterns (Don't Do This)

### ❌ Silent Fallback
```python
# Agent thinks: "cerberus grep failed, I'll just use Grep"
Grep(pattern="...")  # WRONG - user never knew
```

### ❌ Auto-Implement Without Asking
```python
# Agent thinks: "I'll just implement it without asking"
# *spends 20 minutes implementing*
# User: "I was in a hurry, just use the workaround!"
```

### ❌ Overly Verbose Explanations
```
"I need to use a tool and Cerberus doesn't have it and here's
a 500-word essay on why and the entire implementation plan..."
# User: "Just tell me the options!"
```

### ❌ False Dilemmas
```
"Should I implement cerberus ls or completely abandon this task?"
# WRONG - always offer the workaround option
```

---

## Edge Cases

### Case 1: Multiple Gaps in Quick Succession
**Scenario:** Task requires 3 standard tools

**Agent approach:**
```
⏸️ Multiple Gaps Detected

This task requires 3 features Cerberus lacks:
1. cerberus ls <pattern>
2. cerberus find --name <name>
3. cerberus tree --depth 2

Options:
1. Implement all 3 (~30 min total)
2. Use standard tools for this session
3. Implement just the most critical one (#1)

Which approach?
```

### Case 2: Emergency/Time-Sensitive Task
**User context:** "Quick! Production is down!"

**Agent approach:**
```
⏸️ Gap Detected (suggesting fast path)

Need standard tool for speed. Given urgency:

Recommending: Use Glob workaround now (30 seconds)
Future work: Implement cerberus ls later

Proceeding with workaround in 5 seconds unless you say stop...
```

### Case 3: User Disabled Index
**Scenario:** No cerberus.db exists

**Agent approach:**
```
No index detected - standard tools are OK.

Note: If you want dogfooding benefits (token savings, speed),
run: cerberus index .

For now, using standard tools.
```

---

## Metrics to Track

- **Gaps identified:** How many times agent hit PAUSE
- **User choices:** Option 1 vs Option 2 selection rate
- **Implementation time:** Actual vs estimated
- **Workaround frequency:** When user chooses speed over quality
- **Gap recurrence:** Same gap hit multiple times = high priority

---

## Future Enhancements

### 1. Auto-Track Gaps
```bash
cerberus doctor --show-gaps
# Lists all times standard tools were used
# Ranks by frequency
# Suggests high-impact additions
```

### 2. Priority Queue
```bash
cerberus gaps list
# Shows gaps sorted by:
# - Frequency of occurrence
# - User frustration signals
# - Implementation complexity
```

### 3. Quick Workaround Mode
```bash
cerberus config set dogfooding.strict false
# Allows standard tools without pausing
# But logs all usage for later review
```

---

## References

- [CERBERUS.md](../CERBERUS.md) - Updated enforcement rules
- [DOGFOODING_MANDATE.md](./DOGFOODING_MANDATE.md) - Full mandate details

---

**PAUSE Protocol Status:** ✅ **ACTIVE**
**Version:** v0.7.0+
**Last Updated:** 2026-01-09
