# CERBERUS - DEVELOPMENT & CONTRIBUTING

**Module Type:** On-Demand (load when contributing to Cerberus)
**Core Reference:** See CERBERUS.md for tool selection and workflows
**Purpose:** Development guidelines, documentation rules, risk prevention

---

## DOCUMENTATION MAINTENANCE

### Document Rules

```
PURPOSE: Govern how AI agents maintain CERBERUS.md and modules.
         Violation degrades documentation for all future agents.

STRUCTURE:
  1. NO_DUPLICATION: Never add info that exists elsewhere
  2. NO_PROSE: Use structured formats (tables, code blocks, lists)
  3. NO_EXAMPLES_OUTPUT: Only command syntax, not sample outputs
  4. MACHINE_FIRST: Optimize for LLM parsing, not human readability
  5. CONSOLIDATE: New features go in existing sections, not new sections

ADDING_CONTENT:
  - New command? → Add to CERBERUS-COMMANDS.md under correct category
  - New env var? → Add to CERBERUS-ARCHITECTURE.md Configuration section
  - New rule? → Add to CERBERUS.md Core Rules (check if exists first)
  - New phase? → Add single line to CERBERUS-ARCHITECTURE.md Feature Status
  - NEVER create new top-level sections without explicit user approval

FORBIDDEN_ADDITIONS:
  - Human-readable output examples (wastes tokens)
  - Explanatory prose (use terse rules instead)
  - Duplicate information (search document first)
  - Emoji descriptions (use symbols: ✓ ✗ only)
  - Marketing language or feature descriptions

BEFORE_EDITING:
  1. Read ENTIRE relevant module first
  2. Search for existing coverage of your topic
  3. Identify the ONE correct location for new content
  4. Add minimally - fewest tokens that convey the information

VERSIONING:
  - Increment patch version (X.Y.Z) for any content change
  - Update test count in header if tests added
  - Update date in header on every edit
```

### Module Organization

```
CERBERUS.md                  Core guide (always load)
CERBERUS-COMMANDS.md         Command reference (load when need syntax)
CERBERUS-ARCHITECTURE.md     Internals & config (load when debugging)
CERBERUS-DEVELOPMENT.md      Contributing guide (load when developing)
CERBERUS-LEADERSHIP.md       Agent pushback playbook (load when confused)
HANDOFF.md                   Development state (load at session start)
```

---

## CORE RULES

### Tool Selection

```
EXPLORE>EXTRACT: Blueprint/search/references for exploration. Direct Read for code.
VERIFY_WRITES: All mutations MUST use --verify to prevent regression
STRICT_RESOLUTION: No auto-correct on mutations. Ambiguity = Error
MAP_FIRST: Blueprint first, THEN direct Read for specific lines
PARSE_PERFECT: All outputs LLM-parsable >98% accuracy
DEPS_CHECK: Never delete/edit referenced symbols without checking deps
```

### Violation Protocol

```
ON_DETECT: Stop → Acknowledge violation → Redo with Cerberus → Continue
ON_ERROR: Try alt Cerberus cmd → Report to user → NEVER silent fallback
ON_CATCH_SELF: Cancel action → Show correct command → Execute correctly
AUDIT_FREQ: Every 10 tool calls, review compliance
```

---

## RISK PREVENTION [AGENT PRE-FLIGHT]

**Before implementing features, warn developer if:**

```
1. FILE_LOGGING: Adding always-on file logging or disk writes
2. UNBOUNDED_STORAGE: Caching/storage without size limits or rotation
3. IMPORT_SIDE_EFFECTS: Code that runs on every import (not lazy)
4. BACKGROUND_PROCESSES: Daemons/watchers without auto-shutdown
5. ROOT_FILE_CREATION: Creating files outside .cerberus/ directory
6. LARGE_DEFAULTS: Default values >1MB or >1000 items
```

**Warning Format (context-light):**

```
⚠️ RISK: [CATEGORY] - [1-line description]
IMPACT: [potential consequence]
SAFER: [alternative approach]
PROCEED? [wait for user confirmation]
```

**Historical Issues (learn from past):**

```
- Phase 17: Logging on import → 3.3GB bloat
- Always validate: rotation limits, retention policies, lazy init
```

---

## TESTING

### Test Requirements

```
All new features MUST have tests
Mutation changes MUST use --verify to run existing tests
Style fixes MUST use --verify to prevent regression
Minimum coverage: 80% for new code
```

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest tests/test_mutations.py

# With coverage
pytest --cov=src --cov-report=json
pytest --cov=src --cov-report=html
```

---

## DEVELOPMENT WORKFLOW

### Adding New Commands

```
1. Implement command in src/cerberus/cli/<category>.py
2. Add tests in tests/test_<category>.py
3. Run: pytest --verify
4. Add to CERBERUS-COMMANDS.md under correct category
5. Update version in CERBERUS.md header
6. Commit with descriptive message
```

### Adding New Features

```
1. Discuss approach in issue/PR
2. Implement with tests
3. Update relevant docs:
   - CERBERUS-COMMANDS.md (if new commands)
   - CERBERUS-ARCHITECTURE.md (if new config/components)
   - HANDOFF.md (progress update)
4. Run: cerberus validate-docs --strict
5. Commit with Co-Authored-By if applicable
```

### Fixing Bugs

```
1. Add failing test that reproduces bug
2. Fix bug
3. Verify test passes
4. Update HANDOFF.md if significant
5. Commit
```

---

## RELEASE PROCESS

### Version Numbering

```
X.Y.Z format (semantic versioning)
X = Major (breaking changes)
Y = Minor (new features, backward-compatible)
Z = Patch (bug fixes, doc updates)
```

### Release Checklist

```
1. Update version in:
   - CERBERUS.md header
   - src/cerberus/protocol/content.py (PROTOCOL_VERSION)
   - setup.py or pyproject.toml
2. Update HANDOFF.md with release notes
3. Run: pytest (all tests must pass)
4. Run: cerberus validate-docs --strict
5. Tag: git tag -a vX.Y.Z -m "Release X.Y.Z"
6. Push: git push && git push --tags
```

---

## CODE STYLE

### General Principles

```
- Terse, functional, machine-first
- Prefer tables/lists over prose
- JSON output for all commands (--json flag)
- No verbose logging (use silent by default)
- Lazy initialization (don't run code on import)
```

### Python Style

```
- Black formatter (run: black .)
- Type hints required
- Docstrings for public APIs
- No print() statements (use logging or console.print)
```

---

## PERFORMANCE

### Token Efficiency

```
Goal: Minimize context for AI agents
- Cerberus.md core: ~250 lines (always load)
- Modules: ~150-250 lines each (load on demand)
- Total reduction: 60% vs monolithic 518-line doc
```

### Command Performance

```
blueprint: <100ms typical, <500ms with all overlays
search: <200ms for keyword, <1s for semantic
get-symbol: <50ms for snippet, <200ms for full context
mutations: <100ms for validation, depends on --verify command
```

---

## GOLDEN EGG COMPLIANCE

**Cerberus uses the golden egg documentation system:**

```
✓ Modular docs (core + on-demand modules)
✓ Agent Leadership Protocol (protect optimizations)
✓ Session rotation (HANDOFF.md → .handoff-archive/)
✓ Cerberus-first exploration (dogfood our own tool)
✓ Context efficiency (60% reduction vs monolithic)
```

**When developing Cerberus:**

```
1. Load CERBERUS.md (core) at session start
2. Load HANDOFF.md (current development state)
3. Load relevant modules as needed:
   - CERBERUS-COMMANDS.md (when adding commands)
   - CERBERUS-ARCHITECTURE.md (when changing internals)
   - CERBERUS-DEVELOPMENT.md (this file, when contributing)
4. Update HANDOFF.md after completing features
5. Rotate sessions when >3 exist in HANDOFF.md
```

---

## CONTRIBUTING

### Getting Started

```bash
# Clone repo
git clone https://github.com/yourusername/cerberus
cd cerberus

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Check docs
cerberus validate-docs --strict
```

### Pull Request Guidelines

```
1. Create feature branch: git checkout -b feature/your-feature
2. Make changes with tests
3. Update documentation (CERBERUS-*.md)
4. Run: pytest && cerberus validate-docs --strict
5. Commit with descriptive message
6. Push and create PR
7. Address review feedback
```

### Commit Message Format

```
<type>: <subject>

<body>

Co-Authored-By: <name> <email>  # If pair programming/AI collaboration
```

**Types:** feat, fix, docs, refactor, test, perf, chore

---

**Version:** 1.0 (2026-01-11)
**Origin:** Extracted from CERBERUS.md v0.20.1 + golden egg system
**Purpose:** Development guidelines for contributors
**Maintainer:** Proxikal + AI Agents
