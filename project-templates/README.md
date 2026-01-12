# Cerberus Project Templates - "Golden Egg" Documentation System

**Purpose:** Portable, optimized documentation system for AI agent collaboration
**Origin:** Refined through XCalibr project (60% context reduction, agent leadership protocol)
**Reference Implementation:** See `/Users/proxikal/Desktop/Dev/Websites/XCalibr/CLAUDE*.md`

---

## WHAT IS THIS?

This is a **proven template system** for setting up AI agent workflows in any project. It gives you:

✅ **Modular Documentation** - Core guide + on-demand modules (60%+ context reduction)
✅ **Agent Leadership Protocol** - Agents protect optimizations through intelligent pushback
✅ **Session Rotation System** - Prevents documentation bloat via automatic archiving
✅ **Cerberus Integration** - AST-based exploration + pattern memory from day 1
✅ **Operation Checklists** - Machine-readable YAML workflows (.operations/)

**Proven Results (from XCalibr):**
- 849 lines → 336 core lines (60.4% reduction)
- Agents load only what they need (on-demand modules)
- Protected optimizations (agent leadership prevents "drunk orders")
- Seamless session handoffs (HANDOFF.md + rotation protocol)
- Pattern memory (Cerberus --decision flag for project knowledge)

---

## QUICK START FOR NEW PROJECT

**When starting a new project, tell your AI agent:**

> "Let's use Cerberus for this project. Set up the golden egg documentation system."

**What the agent will do:**

```bash
# 1. Navigate to your new project directory
cd /path/to/your/new/project

# 2. Copy templates from Cerberus repo
cp -r ~/Desktop/Dev/Cerberus/project-templates/* .

# 3. Rename templates with your project name (e.g., "MyApp")
mv PROJECT-GUIDE.md MYAPP.md
mv PROJECT-LEADERSHIP.md MYAPP-LEADERSHIP.md
mv PROJECT-HANDOFF.md HANDOFF.md  # Keep this name
mv PROJECT-VPS-OPS.md MYAPP-VPS-OPS.md  # Optional: skip if no VPS
mv PROJECT-WORKFLOWS.md MYAPP-WORKFLOWS.md
mv .operations/deploy.yml.template .operations/deploy.yml  # Optional

# 4. Replace placeholders in all files
# {{PROJECT_NAME}} → MyApp
# {{LOCAL_DIR}} → /Users/proxikal/Desktop/Dev/MyApp
# {{VPS_USER}} → deploy (if applicable)
# {{VPS_HOST}} → 1.2.3.4 (if applicable)
# {{VPS_DIR}} → /home/deploy/apps/myapp (if applicable)
# {{TECH_STACK}} → "Next.js 15 + PostgreSQL" (your stack)

# 5. Initialize Cerberus index
cerberus index . --ext .ts,.js,.py --json
# Creates .cerberus/cerberus.db with AST symbols

# 6. Create session archive directory
mkdir -p .handoff-archive

# 7. Record project setup in Cerberus memory
cerberus memory learn --decision "Project: MyApp uses golden egg doc system" \
  --rationale "Modular docs (core + modules), agent leadership, session rotation, Cerberus-first exploration"

# 8. Add to .gitignore
cat >> .gitignore <<EOF

# Golden Egg Documentation System
# (Exception: Track MYAPP*.md and HANDOFF.md)
.cerberus/
EOF
```

**Setup time:** ~2 minutes automated, ~5 minutes if manual customization needed

---

## TEMPLATES INCLUDED

### Core Templates (Required)

**PROJECT-GUIDE.md** → `{PROJECTNAME}.md`
- Core operational guide (always loaded by agents)
- Quick Start, Agent Leadership Protocol, Critical Rules
- System Configuration, Reference Navigation
- ~300-400 lines (optimized for context efficiency)

**PROJECT-LEADERSHIP.md** → `{PROJECTNAME}-LEADERSHIP.md`
- Agent leadership & intelligent pushback playbook
- Universal (no customization needed - copy verbatim)
- Decision tree, templates, scenarios, edge cases
- ~480 lines (load on demand)

**PROJECT-HANDOFF.md** → `HANDOFF.md`
- Session tracking and state management
- Current progress, detailed tasks, recent sessions
- Session rotation protocol (>3 sessions → archive)
- ~150-200 lines active (older sessions archived)

### Optional Templates (Use as needed)

**PROJECT-VPS-OPS.md** → `{PROJECTNAME}-VPS-OPS.md`
- VPS operations reference (deploy, build, logs, etc.)
- Skip if project has no VPS/server component
- ~90 lines (load when doing DevOps)

**PROJECT-WORKFLOWS.md** → `{PROJECTNAME}-WORKFLOWS.md`
- Development workflows, architecture patterns, code patterns
- Customize for your project's tech stack
- ~200 lines (load when coding)

**.operations/deploy.yml.template** → `.operations/deploy.yml`
- Machine-readable YAML operation checklists
- Skip if no deployment workflow
- Customize for your deployment process

---

## CUSTOMIZATION GUIDE

### Step 1: Replace Placeholders

**Global Placeholders (in all files):**
- `{{PROJECT_NAME}}` → Your project name (e.g., "MyApp", "DataPipeline", "CLITool")
- `{{LOCAL_DIR}}` → Absolute path to project on your machine

**VPS Placeholders (PROJECT-VPS-OPS.md, deploy.yml only):**
- `{{VPS_USER}}` → SSH username (e.g., "deploy", "ai_agent")
- `{{VPS_HOST}}` → IP or domain (e.g., "1.2.3.4", "myapp.com")
- `{{VPS_DIR}}` → Project directory on VPS (e.g., "/home/deploy/apps/myapp")
- `{{VPS_DOMAIN}}` → Public URL (e.g., "https://myapp.com")

**Tech Stack Placeholders (PROJECT-GUIDE.md, PROJECT-WORKFLOWS.md):**
- `{{TECH_STACK}}` → Your stack (e.g., "Next.js 15 + PostgreSQL + Prisma")
- `{{BUILD_COMMAND}}` → Build command (e.g., "npm run build", "cargo build --release")
- `{{TEST_COMMAND}}` → Test command (e.g., "npm test", "pytest")
- `{{DEV_COMMAND}}` → Dev server command (e.g., "npm run dev", "python manage.py runserver")

### Step 2: Customize Critical Rules

**PROJECT-GUIDE.md has generic Critical Rules (R1-R7).**

Adapt to your project:
- **Web projects:** Keep R1-R7 (VPS, local dev, deployment workflow)
- **CLI tools:** Remove VPS rules, add rules for versioning, distribution
- **Python projects:** Adapt build commands, add virtual env rules
- **Mobile apps:** Add app store deployment rules

### Step 3: Add Project-Specific Sections

**In PROJECT-GUIDE.md, add sections like:**
- Database schema (if applicable)
- API endpoints (if applicable)
- Key dependencies and why you chose them
- Known issues and workarounds

**In PROJECT-WORKFLOWS.md, add:**
- Code patterns specific to your stack
- Testing strategies
- CI/CD workflows (if applicable)

---

## FILE STRUCTURE AFTER SETUP

```
your-project/
├── MYAPP.md                    ← Core guide (always load)
├── MYAPP-LEADERSHIP.md         ← Agent leadership (load as needed)
├── MYAPP-VPS-OPS.md           ← VPS operations (load as needed, optional)
├── MYAPP-WORKFLOWS.md         ← Dev workflows (load as needed)
├── HANDOFF.md                  ← Current state & sessions
├── .handoff-archive/           ← Archived sessions
│   └── README.md               ← Archive format guide
├── .operations/                ← Machine-readable checklists
│   ├── README.md               ← Operations guide
│   └── deploy.yml              ← Deployment checklist (optional)
├── .cerberus/                  ← Cerberus index (not committed)
│   └── cerberus.db             ← AST symbol index
├── .gitignore                  ← Updated to track docs, ignore .cerberus
└── (your project files)
```

---

## AGENT WORKFLOW (Post-Setup)

**Every agent session starts with:**

```bash
# 1. Load core guide
Read MYAPP.md  # ~300-400 lines, always loaded

# 2. Load Cerberus memory
cerberus memory context --compact --json
# Returns: Project patterns, decisions, corrections

# 3. Check current state
Read HANDOFF.md  # Current progress, active tasks

# 4. Load modules as needed
Read MYAPP-VPS-OPS.md      # If deploying
Read MYAPP-WORKFLOWS.md    # If coding
Read MYAPP-LEADERSHIP.md   # If confused about pushback
```

**Agent behavior:**
- Cerberus-first for exploration (orient, go, search)
- Autonomous execution (don't ask permission for clear tasks)
- Intelligent pushback (protect optimizations via leadership protocol)
- Update HANDOFF.md after completing features
- Rotate sessions when >3 exist

---

## MAINTENANCE

### Adding New Modules

Create `MYAPP-NEWMODULE.md` and add to Reference Navigation in `MYAPP.md`:

```markdown
### New Module (MYAPP-NEWMODULE.md)
Load when you need:
- Feature X
- Workflow Y
```

### Session Rotation

When HANDOFF.md exceeds 3 sessions:
```bash
# 1. Extract oldest sessions
# 2. Move to .handoff-archive/YYYY-MM-Wxx.md (week-based)
# 3. Keep only newest 2-3 sessions in HANDOFF.md
```

See `.handoff-archive/README.md` for archive format.

### Updating Templates

If you improve the system in one project:
1. Extract the improvement
2. Generalize it (add placeholders)
3. Update templates in `~/Desktop/Dev/Cerberus/project-templates/`
4. Apply to other projects as needed

---

## WHY THIS WORKS

**Context Efficiency:**
- Agents load ~400 lines core vs 800-1000 monolithic doc (50-60% reduction)
- On-demand modules loaded only when task requires them
- Operation checklists use structured YAML (parseable, compact)

**Knowledge Transfer:**
- Cerberus memory preserves patterns across sessions
- HANDOFF.md provides current state for new agents
- Session archives preserve historical context

**Quality Protection:**
- Agent Leadership Protocol prevents optimization degradation
- Protected assets (core doc size, memory limits, critical rules)
- Intelligent pushback catches "drunk orders"

**Scalability:**
- System works for 1-person solo projects to multi-agent teams
- Works for web apps, CLI tools, Python scripts, mobile apps
- Proven in production (XCalibr: 102 routes, 16 services, 42/144 migration complete)

---

## EXAMPLES

### Example 1: Next.js Web App (with VPS)
```bash
# Use all templates
MYAPP.md (core), MYAPP-LEADERSHIP.md (universal),
MYAPP-VPS-OPS.md (deployment), MYAPP-WORKFLOWS.md (dev),
.operations/deploy.yml (5-step deployment)
```

### Example 2: Python CLI Tool (local only)
```bash
# Skip VPS templates
MYAPP.md (core, no VPS rules), MYAPP-LEADERSHIP.md (universal),
MYAPP-WORKFLOWS.md (dev patterns: click, typer, packaging)
```

### Example 3: Mobile App (iOS/Android)
```bash
# Adapt VPS templates for app stores
MYAPP.md (core, add app store rules), MYAPP-LEADERSHIP.md (universal),
MYAPP-WORKFLOWS.md (dev patterns: React Native, Expo, TestFlight),
.operations/release.yml (app store deployment checklist)
```

---

## REFERENCE IMPLEMENTATION

**See XCalibr for working example:**
- Path: `/Users/proxikal/Desktop/Dev/Websites/XCalibr/`
- Files: `CLAUDE.md`, `CLAUDE-LEADERSHIP.md`, `CLAUDE-VPS-OPS.md`, `CLAUDE-WORKFLOWS.md`, `HANDOFF.md`
- Stats: 336 core lines (60% reduction), 102 routes deployed, agent leadership active

**Key Files to Study:**
- `CLAUDE.md:28-111` - Agent Leadership Protocol (copy to all projects)
- `HANDOFF.md:23-46` - Session Rotation Protocol (copy to all projects)
- `.operations/deploy.yml` - YAML checklist format (adapt to your deployment)

---

## TROUBLESHOOTING

**Q: Agent not using Cerberus?**
A: Add to core guide under "Agent Behavior" → "EXPLORATION" → "Cerberus First" section

**Q: Core guide too long (>400 lines)?**
A: Extract content to new module (e.g., MYAPP-DATABASE.md), update Reference Navigation

**Q: Sessions not rotating?**
A: Check HANDOFF.md has Session Rotation Protocol section (lines 23-46 in template)

**Q: Agent ignoring leadership protocol?**
A: Ensure MYAPP.md includes Agent Leadership Protocol section (lines 28-111 in template)

**Q: Placeholders not replaced?**
A: Search for `{{` in all files, replace manually or use sed:
```bash
find . -name "MYAPP*.md" -exec sed -i '' 's/{{PROJECT_NAME}}/MyApp/g' {} \;
```

---

## CONTRIBUTING IMPROVEMENTS

If you enhance the template system:
1. Test in a real project (ensure it works)
2. Generalize (add placeholders, remove project-specific details)
3. Update templates in `~/Desktop/Dev/Cerberus/project-templates/`
4. Document in this README
5. Commit to Cerberus repo

**Template Evolution:**
- Version 1.0 (2026-01-11): Initial system from XCalibr
- Future versions: Add support for new project types, workflows

---

**Last Updated:** 2026-01-11
**Origin:** XCalibr project optimization (commit 585fac8)
**Maintained By:** Proxikal + AI Agents
