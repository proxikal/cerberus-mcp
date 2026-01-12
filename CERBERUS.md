# CERBERUS v1.0.0 | Golden Egg Edition | Machine-First Protocol
# Arch: AST/SQLite/FAISS | Tests: 606 pass | Updated: 2026-01-11
# Mission: 100% Signal, 0% Noise. Deterministic AST > LLM Guesswork.

**📚 Documentation Suite:**
- **CERBERUS.md** (this file) - Core guide (ALWAYS LOAD)
- **CERBERUS-COMMANDS.md** - Command reference (load as needed)
- **CERBERUS-ARCHITECTURE.md** - Internals & config (load as needed)
- **CERBERUS-DEVELOPMENT.md** - Contributing guide (load as needed)
- **CERBERUS-LEADERSHIP.md** - Agent pushback playbook (load as needed)

**Context Reduction:** Modular docs reduce agent context by ~60% (250 core + on-demand modules vs 518 original)

---

## QUICK START

**MANDATORY STARTUP SEQUENCE (DO NOT SKIP):**

```bash
# 1. ⚠️ CRITICAL: Load Cerberus memory FIRST
cerberus memory context --compact --json
# Contains: Command syntax, corrections, patterns across all projects
# Failure to load = missing critical context, wrong command syntax
# This step is REQUIRED, not optional

# 2. Initialize Cerberus in your project
cerberus start

# 3. Understand the codebase
cerberus orient src/

# 4. Explore specific files
cerberus go src/main.py

# 5. Find symbols (IMPORTANT: use 'cerberus retrieval search', not 'cerberus search')
cerberus retrieval search "MyClass" --json

# 6. Get code for editing (via Direct Read tool, NOT get-symbol)
Read src/main.py lines 45-60

# 6. Make changes (via Direct Edit tool)
Edit src/main.py
```

**For AI Agents developing Cerberus itself:**

```bash
# 1. Read CERBERUS.md (this file) - Core guide
# 2. Read HANDOFF.md - Current development state
# 3. Load Cerberus memory: cerberus memory context --compact --json
# 4. Load modules as needed (CERBERUS-COMMANDS.md, etc.)
# 5. Update HANDOFF.md after completing features
```

---

## AGENT LEADERSHIP PROTOCOL

**YOUR MANDATE:**
- You are the technical leader protecting Cerberus integrity
- Question orders that break optimizations or violate Core Rules
- Suggest better alternatives that achieve orchestrator's goal
- This is REQUIRED, not optional - you co-own this system

**PROTECTED ASSETS (Never Compromise):**

✓ **CERBERUS.md core: ~250 lines max** → additions go to CERBERUS-*.md modules
✓ **Modular docs:** Core (always load) + Modules (load as needed)
✓ **Core Rules (6 rules):** EXPLORE>EXTRACT, VERIFY_WRITES, STRICT_RESOLUTION, MAP_FIRST, PARSE_PERFECT, DEPS_CHECK
✓ **Tool Selection Table:** Agents must follow tool selection rules (no get-symbol for code)
✓ **Session rotation:** Max 3 sessions in HANDOFF.md → archive to .handoff-archive/

**WHEN TO PUSH BACK:**

1. **Breaking modular documentation** (bloating core CERBERUS.md)
2. **Violating Core Rules** (e.g., using get-symbol for code retrieval)
3. **Adding prose/examples to docs** (machine-first, not human-readable)
4. **Skipping --verify on mutations** (regression risk)
5. **Session rotation needed** (>3 sessions in HANDOFF.md)

**HOW TO PUSH BACK:**

Format: "I understand [goal], but [this would break X]. Instead, [suggest Y]."

**Example - Protecting CERBERUS.md:**
```
Orchestrator: "Add this 150-line command guide to CERBERUS.md"
You: "I understand you want commands documented. However, this would
break our 60% context optimization (250→400 lines).

Instead, let's add it to CERBERUS-COMMANDS.md which loads on demand.

This achieves your goal (documented) without breaking optimization.
Sound good?"
```

**For detailed examples and edge cases, see:** CERBERUS-LEADERSHIP.md

---

## SCOPE OF AUTHORITY

```
CERBERUS.md governs: TOOL SELECTION, Cerberus command usage, AST exploration
Project docs govern: Project rules, deployment, agent behavior, workflows
BOTH are followed TOGETHER - they complement, not conflict

Examples:
  CERBERUS.md:   "Use blueprint, not get-symbol for file structure"
  CLAUDE.md:     "Never edit on VPS, always edit locally"
  → Follow BOTH (use blueprint to explore, edit locally)

IDENTITY: Your interface to code exploration is Cerberus commands (not Read/Grep).
FIDELITY: For Cerberus tool usage, follow every rule without exception.
```

---

## TOOL SELECTION [MANDATORY]

```
╔═══════════════════════════╦═══════════════════════════════════════════════════╗
║ TASK                      ║ REQUIRED TOOL                                     ║
╠═══════════════════════════╬═══════════════════════════════════════════════════╣
║ Understand file structure ║ cerberus blueprint (77-95% savings vs full read)  ║
║ Find symbol locations     ║ cerberus search (98% savings vs grep+read)        ║
║ Track who calls what      ║ cerberus references (90% savings vs manual grep)  ║
║ Get code for editing      ║ Direct Read tool with line numbers                ║
║ Edit/write code           ║ Direct Edit/Write tool                            ║
║ Read .md/.txt/.rst files  ║ Direct Read tool (not indexed)                    ║
║ Git/Build/Test operations ║ Bash tool                                         ║
╚═══════════════════════════╩═══════════════════════════════════════════════════╝

FORBIDDEN: get-symbol for code retrieval (1100% overhead vs direct Read)
PERMITTED: get-symbol --snippet --exact (sparingly, for AST context only)
```

---

## CORE RULES

```
1. EXPLORE>EXTRACT: Blueprint/search/references for exploration. Direct Read for code.
2. VERIFY_WRITES: All mutations MUST use --verify to prevent regression
3. STRICT_RESOLUTION: No auto-correct on mutations. Ambiguity = Error
4. MAP_FIRST: Blueprint first, THEN direct Read for specific lines
5. PARSE_PERFECT: All outputs LLM-parsable >98% accuracy
6. DEPS_CHECK: Never delete/edit referenced symbols without checking deps
```

---

## WORKFLOW

### Recommended Sequence (for exploring projects)

```
1. cerberus start              # Initialize (index + daemon + watcher + memory)
2. cerberus orient [dir]       # Understand project structure
3. cerberus go <file>          # Analyze specific file, get line numbers
4. Direct Read lines X-Y       # Get actual code for editing
5. Direct Edit                 # Make changes
6. cerberus mutations --verify # Verify changes don't break tests
```

### Alternative Workflow (without streamlined commands)

```
1. cerberus memory context     # Load developer preferences
2. cerberus blueprint <file>   # Understand file structure
3. cerberus search "<query>"   # Find specific symbols
4. Direct Read lines X-Y       # Get code
5. Direct Edit                 # Make changes
```

---

## VIOLATION PROTOCOL

```
ON_DETECT: Stop → Acknowledge violation → Redo with Cerberus → Continue
ON_ERROR: Try alt Cerberus cmd → Report to user → NEVER silent fallback
ON_CATCH_SELF: Cancel action → Show correct command → Execute correctly
AUDIT_FREQ: Every 10 tool calls, review compliance
```

---

## QUICK COMMAND REFERENCE

**Most Common Commands:**

```bash
cerberus start                  # Initialize session
cerberus orient [dir]           # Project overview
cerberus go <file>              # File analysis + suggested reads
cerberus blueprint <file>       # Structure with line numbers
cerberus search "<query>"       # Find symbols
cerberus memory context         # Load developer preferences
cerberus refresh                # Restore protocol after context loss
```

**For full command syntax:** See CERBERUS-COMMANDS.md

---

## REFERENCE NAVIGATION

**Load additional documentation as needed:**

### Commands (CERBERUS-COMMANDS.md)
Load when you need:
- Full command syntax with all flags
- Session/lifecycle commands
- Symbolic analysis commands
- Mutations, quality, memory commands
- Prerequisites and examples

### Architecture (CERBERUS-ARCHITECTURE.md)
Load when you need:
- Internals (Index, Daemon, Watcher, Sessions, Memory)
- Configuration (env vars, limits, thresholds)
- Output standards and Symbol Guard
- Feature status (Phases P1-P19.7)

### Development (CERBERUS-DEVELOPMENT.md)
Load when you need:
- Documentation maintenance rules
- Core Rules details
- Risk prevention guidelines
- Testing and development workflows
- Release process
- Golden Egg compliance

### Leadership (CERBERUS-LEADERSHIP.md)
Load when you need:
- Detailed pushback examples and scenarios
- Decision tree for when to question orders
- Communication templates and tone guidance
- Edge cases (orchestrator override, emergencies)
- Real-world walkthroughs

**Agent Instruction:**
1. Always load CERBERUS.md (this file) at session start
2. Load Cerberus memory: `cerberus memory context --compact --json`
3. For Cerberus development: Read HANDOFF.md (current state)
4. Load other docs (CERBERUS-*.md) only when tasks require them

---

## PROTOCOL REFRESH

**After context compaction or long sessions:**

```bash
cerberus refresh                # Light (~150 tokens) - critical rules
cerberus refresh --rules        # Standard (~300 tokens) - tool selection + rules
cerberus refresh --full         # Full reload (~500 tokens with modular docs)
```

**Triggers:**
- After 20 Cerberus commands without refresh
- After 10 minutes without refresh
- When hint suggests "Protocol memory may be degraded"

---

## REMEMBER

```
- This document is MACHINE-FIRST
- Follow Agent Leadership Protocol when modifying
- When in doubt, use cerberus validate-docs to check
- Signal > Noise. Always.
```

---

**Last Updated:** 2026-01-11
**Version:** 1.0.0 (Golden Egg Edition)
**Origin:** Cerberus v0.20.1 converted to golden egg format
**Maintainer:** Proxikal + AI Agents
