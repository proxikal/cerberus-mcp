# Config-Driven Architecture - Eliminating Documentation Duplication

**Created:** 2026-01-11
**Status:** Implementation In Progress
**Problem:** Cerberus commands duplicated in every project (maintenance nightmare)
**Solution:** Config file + Memory system + Canonical docs (single source of truth)

---

## THE PROBLEM

### Current State (Duplication):
```
Cerberus/
├── CERBERUS-COMMANDS.md (255 lines) ← ORIGINAL

XCalibr/
├── CLAUDE-CERBERUS.md (300 lines) ← DUPLICATE of Cerberus commands

AegisIO/
├── CLAUDE-CERBERUS.md (300 lines) ← DUPLICATE again

[Every project duplicates Cerberus documentation]
```

### Why This is Bad:
1. **Fix `cerberus search` bug** → Must update Cerberus + XCalibr + AegisIO + every project
2. **Add new command** → Must update everywhere
3. **User installs Cerberus** → Must manually sync docs to their projects
4. **Commands change** → Version skew across projects
5. **Maintenance nightmare** → Scales poorly (10 projects = 10 updates)

---

## THE SOLUTION

### Config-Driven Architecture:

```
┌─────────────────────────────────────────────────────┐
│ Cerberus Repository (Single Source of Truth)        │
│ ~/Desktop/Dev/Cerberus/                             │
├─────────────────────────────────────────────────────┤
│ • CERBERUS-COMMANDS.md - All commands (ONCE)        │
│ • CERBERUS-ARCHITECTURE.md - Internals (ONCE)       │
│ • Memory System - Cross-project patterns            │
│                                                      │
│ THIS IS THE ONLY PLACE COMMANDS ARE DOCUMENTED      │
└─────────────────────────────────────────────────────┘
                         ↓
                   (Referenced by)
                         ↓
┌─────────────────────────────────────────────────────┐
│ Project: XCalibr                                     │
├─────────────────────────────────────────────────────┤
│ .cerberus/config.json (20 lines)                    │
│ {                                                    │
│   "project_name": "XCalibr",                         │
│   "tech_stack": "Next.js 16 + PostgreSQL",           │
│   "vps": { "user": "ai_agent", ... }                 │
│ }                                                    │
│                                                      │
│ CLAUDE.md (200 lines - project rules only)          │
│ - NO Cerberus command duplication                   │
│ - References: cerberus memory context               │
│                                                      │
│ Memory: cerberus memory context --compact --json    │
│ - Returns: Commands, corrections, patterns          │
│ - Automatic cross-project learning                  │
└─────────────────────────────────────────────────────┘
```

---

## HOW IT WORKS

### 1. Static Config (Machine-Readable)

**File:** `.cerberus/config.json`
```json
{
  "project_name": "XCalibr",
  "local_dir": "/Users/proxikal/Desktop/Dev/Websites/XCalibr",
  "tech_stack": "Next.js 16 + PostgreSQL + Prisma + JWT",
  "vps": {
    "user": "ai_agent",
    "host": "74.208.73.163",
    "dir": "/home/deploy/apps/xcalibr"
  },
  "index_stats": {
    "files": 212,
    "symbols": 4090,
    "indexed_extensions": [".ts", ".tsx"]
  },
  "cerberus_install": "~/Desktop/Dev/Cerberus"
}
```

**Purpose:**
- Project metadata (name, paths, tech stack)
- Auto-discoverable (in `.cerberus/` directory)
- Machine-readable for tooling
- Version controlled with project

### 2. Dynamic Patterns (Memory System - Already Works!)

**Command:**
```bash
cerberus memory context --compact --json
```

**Returns:**
- **Commands:** "Use 'cerberus retrieval search' not 'cerberus search'"
- **Corrections:** Common mistakes across all projects
- **Patterns:** Service modules, auth patterns, build commands
- **Decisions:** Architectural choices specific to each project

**Key Insight:** Memory system is ALREADY cross-project! When you fix something in XCalibr, that correction appears for AegisIO agents too.

### 3. Canonical Docs (Cerberus Only)

**Files:**
- `~/Desktop/Dev/Cerberus/CERBERUS-COMMANDS.md` - All commands
- `~/Desktop/Dev/Cerberus/CERBERUS-ARCHITECTURE.md` - Internals
- `~/Desktop/Dev/Cerberus/CERBERUS-DEVELOPMENT.md` - Contributing

**Access:**
```bash
# Option A: Direct read (agents know Cerberus path)
Read ~/Desktop/Dev/Cerberus/CERBERUS-COMMANDS.md

# Option B: Cerberus command (future enhancement)
cerberus docs --commands
cerberus docs --architecture

# Option C: Memory includes critical commands (current)
cerberus memory context --compact --json
```

---

## WHAT GETS ELIMINATED

### ❌ DELETE from Every Project:
```
CLAUDE-CERBERUS.md (300+ lines of duplicated Cerberus commands)
```

### ✅ REPLACE with:
```
.cerberus/config.json (20 lines of project metadata)
cerberus memory context (automatic, cross-project, always fresh)
```

### ✅ KEEP in Projects:
```
CLAUDE.md (project rules, R1-R7, workflows - NO Cerberus duplication)
CLAUDE-LEADERSHIP.md (agent pushback - universal template)
CLAUDE-VPS-OPS.md (VPS deployment - project-specific)
HANDOFF.md (session tracking)
```

---

## AGENT WORKFLOW (Zero Duplication)

### Old Way (Duplication):
```bash
1. Read CLAUDE.md (project rules)
2. Read CLAUDE-CERBERUS.md (300 lines of Cerberus commands)
   ↑ THIS IS DUPLICATED IN EVERY PROJECT
3. Read HANDOFF.md (current state)
4. Start work
```

### New Way (Config-Driven):
```bash
1. Read CLAUDE.md (project rules - NO Cerberus commands inside)
2. Read HANDOFF.md (current state)
3. cerberus memory context --compact --json (MANDATORY)
   ↑ Returns: Commands, corrections, patterns (cross-project)
4. [Optional] If need full reference:
   Read ~/Desktop/Dev/Cerberus/CERBERUS-COMMANDS.md
5. Start work with full context
```

**Result:** Agent has everything it needs, zero duplication, always up-to-date.

---

## BENEFITS

### ✅ Single Source of Truth
- Fix `cerberus search` → `cerberus retrieval search` ONCE in Cerberus
- All projects benefit immediately via memory system
- No manual sync needed

### ✅ Zero Duplication
- Cerberus commands documented once (in Cerberus repo)
- Projects reference via config + memory
- 300 lines eliminated from every project

### ✅ Cross-Project Learning
- Memory system shares corrections across projects
- XCalibr patterns help AegisIO agents (and vice versa)
- Network effect: More projects = smarter memory

### ✅ Multi-User Ready
- Users install Cerberus once (~/Desktop/Dev/Cerberus/ or ~/.config/cerberus/)
- Projects include `.cerberus/config.json`
- Memory propagates updates automatically
- No manual doc sync needed

### ✅ Context Efficiency
- CLAUDE.md shrinks from 335 → 200 lines (no Cerberus duplication)
- Memory context <2KB compressed JSON (vs 300-line markdown)
- Agents load only what they need, when they need it

### ✅ Maintainability
- Update commands: 1 file (Cerberus repo)
- Update project metadata: 1 file (config.json)
- Update patterns: Memory system (automatic)

---

## IMPLEMENTATION PLAN

### Phase 1: Create Config File (XCalibr)
```bash
cd ~/Desktop/Dev/Websites/XCalibr

# Create .cerberus/config.json
cat > .cerberus/config.json << 'EOF'
{
  "project_name": "XCalibr",
  "local_dir": "/Users/proxikal/Desktop/Dev/Websites/XCalibr",
  "tech_stack": "Next.js 16 + PostgreSQL + Prisma + JWT",
  "vps": {
    "user": "ai_agent",
    "host": "74.208.73.163",
    "dir": "/home/deploy/apps/xcalibr"
  },
  "deployment": {
    "sync_source": "src",
    "build_command": "npm run build:fast",
    "restart_command": "pm2 restart xcalibr"
  },
  "index": {
    "database": ".cerberus/cerberus.db",
    "files": 212,
    "symbols": 4090,
    "extensions": [".ts", ".tsx"]
  },
  "cerberus_install": "~/Desktop/Dev/Cerberus"
}
EOF

git add .cerberus/config.json
git commit -m "Add Cerberus config - project metadata for config-driven architecture"
```

### Phase 2: Delete CLAUDE-CERBERUS.md (Zero Duplication)
```bash
# Remove 300+ line duplicated doc
git rm CLAUDE-CERBERUS.md
git commit -m "Remove CLAUDE-CERBERUS.md - replaced with config + memory system"
```

### Phase 3: Update CLAUDE.md (Reference Config + Memory)
```markdown
## QUICK START

**MANDATORY STARTUP SEQUENCE (DO NOT SKIP):**

1. **Read CLAUDE.md** (this file) - Learn rules and workflows
2. **Read HANDOFF.md** - Current state and active tasks
3. **⚠️ CRITICAL: Load Cerberus memory** - `cerberus memory context --compact --json`
   - Contains: Command syntax, corrections, patterns, cross-project learnings
   - Failure to load = missing critical context, repeating past mistakes
   - This step is REQUIRED, not optional
4. **[Optional] Read Cerberus config** - `.cerberus/config.json`
   - Project metadata: VPS, tech stack, deployment commands
   - Auto-discoverable, machine-readable
5. **Execute user request** following deployment workflow
6. **Update HANDOFF.md** when complete

---

## CERBERUS INTEGRATION

**Config Location:** `.cerberus/config.json`
**Index Location:** `.cerberus/cerberus.db`
**Commands:** Load via `cerberus memory context --compact --json` (mandatory step 3)
**Full Reference:** `~/Desktop/Dev/Cerberus/CERBERUS-COMMANDS.md` (if needed)

**Critical Commands (from memory):**
- `cerberus retrieval search "query"` - Find symbols (NOT `cerberus search`)
- `cerberus go <file>` - File symbols with line numbers
- `cerberus orient <dir>` - Directory overview

Memory system includes corrections, patterns, and command syntax. Always load memory first.
```

### Phase 4: Update .gitignore (Track Config)
```bash
# Ensure .cerberus/config.json is tracked
echo "# Cerberus" >> .gitignore
echo ".cerberus/cerberus.db*" >> .gitignore
echo "!.cerberus/config.json" >> .gitignore

git add .gitignore
git commit -m "Track Cerberus config, ignore index database"
```

### Phase 5: Test Agent Can Find Everything
```bash
# Spawn new agent session
# Give prompt:
# "Continue Phase 2 migration - Friends & Blocking feature"

# Agent should:
# 1. Read CLAUDE.md (no Cerberus commands inside)
# 2. Read HANDOFF.md (current state)
# 3. Load memory: cerberus memory context --compact --json
#    ↑ Gets command syntax, corrections, patterns
# 4. [Optional] Read config: .cerberus/config.json
# 5. Start work successfully

# Verify agent knows:
# - Correct command syntax (cerberus retrieval search)
# - Project patterns (service modules)
# - VPS deployment (from config or CLAUDE.md)
```

### Phase 6: Update Project Templates
```bash
cd ~/Desktop/Dev/Cerberus/project-templates

# Update README.md
# - Add step: "Create .cerberus/config.json"
# - Remove: PROJECT-CERBERUS.md template
# - Update: PROJECT-GUIDE.md to reference config + memory

# Create new template: .cerberus/config.json.template
{
  "project_name": "{{PROJECT_NAME}}",
  "local_dir": "{{LOCAL_DIR}}",
  "tech_stack": "{{TECH_STACK}}",
  "vps": {
    "user": "{{VPS_USER}}",
    "host": "{{VPS_HOST}}",
    "dir": "{{VPS_DIR}}"
  },
  "cerberus_install": "~/Desktop/Dev/Cerberus"
}
```

### Phase 7: Enhance Cerberus (Future - Optional)
```bash
cd ~/Desktop/Dev/Cerberus

# Add `cerberus docs` command
cerberus docs --commands      # Output CERBERUS-COMMANDS.md
cerberus docs --architecture  # Output CERBERUS-ARCHITECTURE.md
cerberus docs --quick         # Common commands only

# Add `cerberus config` command
cerberus config --show        # Display current project config
cerberus config --update      # Update index stats in config
cerberus config --validate    # Check config schema

# Enhance memory to include critical commands
# So even without reading docs, agents have essentials
```

---

## WHAT THIS LOOKS LIKE

### Before (Duplication - 335 + 300 = 635 lines):
```
XCalibr/
├── CLAUDE.md (335 lines)
│   ├── Project rules
│   ├── VPS deployment
│   └── Workflows
├── CLAUDE-CERBERUS.md (300 lines) ← DUPLICATE
│   ├── Command syntax
│   ├── Workflow patterns
│   └── Examples
├── CLAUDE-LEADERSHIP.md
└── HANDOFF.md

Cerberus/
├── CERBERUS-COMMANDS.md (255 lines) ← ORIGINAL
└── CERBERUS-ARCHITECTURE.md
```

### After (Config-Driven - 200 + 20 = 220 lines):
```
XCalibr/
├── CLAUDE.md (200 lines - 40% reduction)
│   ├── Project rules
│   ├── VPS deployment
│   ├── Workflows
│   └── References: config + memory (NO duplication)
├── .cerberus/
│   ├── cerberus.db (index - gitignored)
│   └── config.json (20 lines - NEW)
│       ├── Project metadata
│       ├── VPS config
│       └── Deployment commands
├── CLAUDE-LEADERSHIP.md (unchanged)
└── HANDOFF.md (unchanged)

Cerberus/
├── CERBERUS-COMMANDS.md (255 lines) ← SINGLE SOURCE
├── CERBERUS-ARCHITECTURE.md
└── Memory System (cross-project patterns)
```

**Savings per project:** 415 lines eliminated (65% reduction in Cerberus-related docs)
**Multiply by 10 projects:** 4,150 lines eliminated
**Multiply by 100 users:** 41,500 lines of duplication eliminated

---

## POTENTIAL ISSUES & SOLUTIONS

### Issue 1: Agent Doesn't Know Where Cerberus Docs Are

**Solution A: Config Points to Docs**
```json
{
  "cerberus_install": "~/Desktop/Dev/Cerberus"
}
```
Agent reads config, knows where to find CERBERUS-COMMANDS.md.

**Solution B: Auto-Discovery**
```bash
which cerberus
# Returns: /Users/proxikal/Desktop/Dev/Cerberus/bin/cerberus
# Agent infers: docs are in ~/Desktop/Dev/Cerberus/CERBERUS-COMMANDS.md
```

**Solution C: Memory Includes Critical Commands (Current)**
```bash
cerberus memory context --compact --json
# Already includes: "Use 'cerberus retrieval search' not 'cerberus search'"
# Could expand to include all common commands
```

**Recommendation:** Use Solution C (memory) as primary, Solution A (config) as fallback.

---

### Issue 2: Memory Doesn't Have ALL Commands

**Current State:**
- Memory has corrections, patterns, decisions
- Doesn't have full command reference

**Solution A: Expand Memory**
Add critical commands to memory:
```bash
cerberus memory learn --pattern "cerberus orient <dir> - Directory overview"
cerberus memory learn --pattern "cerberus go <file> - File symbols"
cerberus memory learn --pattern "cerberus retrieval search 'query' - Find symbols"
```

**Solution B: Add `cerberus docs --quick` Command**
```bash
cerberus docs --quick
# Outputs:
# COMMON COMMANDS:
# cerberus orient <dir> - Directory overview
# cerberus go <file> - File symbols with line numbers
# cerberus retrieval search "query" - Find symbols (NOT 'cerberus search')
# cerberus retrieval get-symbol <name> - Symbol details
#
# Full reference: cerberus docs --commands
```

**Recommendation:** Do both - expand memory + add docs command.

---

### Issue 3: Config Maintenance (Stats Go Stale)

**Problem:** Config has `"files": 212, "symbols": 4090` but index grows.

**Solution A: Make Stats Dynamic**
```bash
cerberus stats --json
# Queries .cerberus/cerberus.db directly
# Always current, no stale config
```

**Solution B: Auto-Update Config**
```bash
cerberus config --update
# Reads index, updates config.json with current stats
```

**Solution C: Remove Stats from Config**
```json
{
  "project_name": "XCalibr",
  "tech_stack": "Next.js 16 + PostgreSQL",
  // NO stats - query index dynamically
}
```

**Recommendation:** Solution C (remove stats) - keep config minimal and static.

---

### Issue 4: Multi-User Install Paths

**Your Setup:**
```
~/Desktop/Dev/Cerberus/  ← Works for you
```

**Other Users:**
```
~/.config/cerberus/      ← Standard XDG config
~/dev/cerberus/          ← Custom dev directory
/usr/local/lib/cerberus/ ← System install
```

**Solution: Auto-Discovery via PATH**
```bash
# Config doesn't hardcode path
{
  "cerberus_install": "auto"  // Discover via `which cerberus`
}

# Agent discovers:
which cerberus
# → /usr/local/bin/cerberus
# Infer docs: /usr/local/share/cerberus/docs/

# Or Cerberus provides:
cerberus info --install-dir
# → /usr/local/lib/cerberus
```

**Recommendation:** Use auto-discovery for multi-user, hardcode path for single-user.

---

## MIGRATION PATH

### Week 1: Prove It Works (XCalibr)
1. Create `.cerberus/config.json` ✓
2. Delete `CLAUDE-CERBERUS.md` ✓
3. Update `CLAUDE.md` to reference config + memory ✓
4. Test new agent can start and work successfully ✓

### Week 2: Template Update
1. Update `~/Desktop/Dev/Cerberus/project-templates/`
2. Add `config.json.template`
3. Remove `PROJECT-CERBERUS.md` template
4. Update `PROJECT-GUIDE.md` to explain config-driven approach

### Week 3: Apply to Other Projects
1. Replicate for AegisIO
2. Replicate for any other projects
3. Verify cross-project memory sharing works

### Week 4: Enhance Cerberus (Optional)
1. Add `cerberus docs` command
2. Add `cerberus config` command
3. Expand memory system to include critical commands
4. Document for external users

---

## SUCCESS CRITERIA

### ✅ Zero Duplication
- CLAUDE-CERBERUS.md eliminated from XCalibr
- Cerberus commands exist ONLY in Cerberus repo
- Projects reference via config + memory

### ✅ Agent Functionality Maintained
- New agents can start and work immediately
- Have access to all Cerberus commands
- Memory provides corrections and patterns
- No functionality lost vs old system

### ✅ Maintainability
- Fix `cerberus search` bug → Update ONCE (Cerberus repo)
- All projects benefit via memory system
- No manual sync needed

### ✅ Multi-User Ready
- Config-driven approach works for any install location
- Auto-discovery via PATH
- Template system for new projects

### ✅ Context Efficiency
- CLAUDE.md: 335 → 200 lines (40% reduction)
- Total Cerberus docs per project: 300 → 20 lines (93% reduction)
- Memory context: <2KB compressed JSON

---

## FINAL RECOMMENDATION

**Implement immediately.** This architecture:

1. **Solves the duplication problem** - One source of truth
2. **Uses existing systems** - Memory already works cross-project
3. **AI Agent friendly** - Config is machine-readable, memory is automatic
4. **Future-proof** - Scales to 100 projects, 1000 users
5. **Reduces maintenance** - Update once, benefit everywhere

**Start with XCalibr (Phases 1-5), prove it works, then replicate.**

---

## TECHNICAL NOTES

### Config Schema (v1.0):
```json
{
  "$schema": "cerberus-config-v1",
  "project_name": "string (required)",
  "local_dir": "string (absolute path, required)",
  "tech_stack": "string (optional)",
  "vps": {
    "user": "string (optional)",
    "host": "string (optional)",
    "dir": "string (optional)"
  },
  "deployment": {
    "sync_source": "string (optional)",
    "build_command": "string (optional)",
    "restart_command": "string (optional)"
  },
  "index": {
    "database": "string (optional, default: .cerberus/cerberus.db)",
    "extensions": "array<string> (optional)"
  },
  "cerberus_install": "string (optional, auto-discover if not set)"
}
```

### Memory System Enhancement:
```bash
# Current corrections in memory:
- "Use 'cerberus retrieval search' not 'cerberus search'"
- "Always log before rethrowing"
- "AI forgets to log errors"

# Propose adding to memory:
- Common commands (orient, go, retrieval search, get-symbol)
- Command patterns (--json, --index path)
- Workflow patterns (orient → go → Read → Edit)
```

### File Size Comparison:
```
CLAUDE-CERBERUS.md:     ~15 KB (300 lines × 50 chars/line)
.cerberus/config.json:  ~0.5 KB (20 lines × 25 chars/line)
Savings:                ~14.5 KB per project (97% reduction)
```

---

**Last Updated:** 2026-01-11T23:30:00Z
**Status:** Ready for Implementation
**Next Steps:** Execute Phases 1-5 for XCalibr
