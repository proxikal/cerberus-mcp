# {{PROJECT_NAME}} - DEVELOPMENT WORKFLOWS & PATTERNS

**Module Type:** On-Demand (load when coding/architecting)
**Core Reference:** See {{PROJECT_NAME}}.md for Critical Rules
**Purpose:** Development workflows, architecture patterns, code templates

---

## DEVELOPMENT WORKFLOW

### Feature Development

```bash
# 1. Explore codebase with Cerberus
cerberus orient {{SOURCE_DIR}}/ --json
cerberus go {{SOURCE_DIR}}/{{FEATURE_FILE}} --index .cerberus/cerberus.db --json

# 2. Read relevant files
Read {{SOURCE_DIR}}/{{FEATURE_FILE}}

# 3. Make changes locally
Edit {{SOURCE_DIR}}/{{FEATURE_FILE}}

# 4. Test locally
{{TEST_COMMAND}}

# 5. Build (if applicable)
{{BUILD_COMMAND}}

# 6. Commit
git add . && git commit -m "Add {{FEATURE_NAME}}: {{DESCRIPTION}}"

# 7. Deploy (if applicable)
[See {{PROJECT_NAME}}-VPS-OPS.md or .operations/deploy.yml]

# 8. Verify
{{VERIFY_COMMAND}}

# 9. Update HANDOFF.md
# - Mark feature complete
# - Update metrics
# - Add session summary
```

### Bug Fix Workflow

```bash
# 1. Reproduce bug locally
{{DEV_COMMAND}}
# [Steps to reproduce]

# 2. Find bug location with Cerberus
cerberus retrieval search "{{ERROR_MESSAGE}}" --index .cerberus/cerberus.db --json

# 3. Read code
Read {{FILE_PATH}}

# 4. Fix bug
Edit {{FILE_PATH}}

# 5. Test fix
{{TEST_COMMAND}}

# 6. Commit
git add . && git commit -m "Fix: {{BUG_DESCRIPTION}}"

# 7. Deploy and verify
[See deployment workflow]
```

### Refactoring Workflow

```bash
# 1. Understand current implementation
cerberus retrieval blueprint {{SOURCE_DIR}}/{{MODULE}} --json
cerberus retrieval skeletonize {{SOURCE_DIR}}/{{FILE}} --json

# 2. Read full implementation
Read {{SOURCE_DIR}}/{{FILE}}

# 3. Make changes incrementally
Edit {{SOURCE_DIR}}/{{FILE}}

# 4. Test after each change
{{TEST_COMMAND}}

# 5. Commit frequently
git add . && git commit -m "Refactor: {{DESCRIPTION}}"

# 6. Final verification
{{BUILD_COMMAND}}
{{TEST_COMMAND}}
```

---

## ARCHITECTURE PATTERNS

### [CUSTOMIZE] Project Structure

```
{{LOCAL_DIR}}/
├── {{SOURCE_DIR}}/              ← [Description]
│   ├── {{SUBDIRS}}/             ← [Description]
│   └── {{FILES}}                ← [Description]
├── {{TEST_DIR}}/                ← [Description]
├── {{CONFIG_FILES}}             ← [Description]
└── {{OTHER_DIRS}}/              ← [Description]
```

### [CUSTOMIZE] Module Pattern

**Example for object-oriented languages:**
```[language]
// [Description of your module pattern]
[Your code template]
```

**Example for functional languages:**
```[language]
// [Description of your module pattern]
[Your code template]
```

---

## CODE PATTERNS

### [CUSTOMIZE] Naming Conventions

**Files:**
- `[pattern]` - [Description]
- `[pattern]` - [Description]

**Functions/Methods:**
- `[pattern]` - [Description]
- `[pattern]` - [Description]

**Variables:**
- `[pattern]` - [Description]
- `[pattern]` - [Description]

**Constants:**
- `[pattern]` - [Description]

### [CUSTOMIZE] Code Templates

**Template 1: [Name]**
```[language]
// [Description]
[Code template]
```

**Template 2: [Name]**
```[language]
// [Description]
[Code template]
```

---

## TESTING STRATEGY

### Test Structure

```
{{TEST_DIR}}/
├── unit/                ← [Description]
├── integration/         ← [Description]
└── e2e/                 ← [Description]
```

### Running Tests

```bash
# All tests
{{TEST_COMMAND}}

# Specific test file
{{TEST_SINGLE_COMMAND}}

# With coverage
{{TEST_COVERAGE_COMMAND}}

# Watch mode
{{TEST_WATCH_COMMAND}}
```

### Test Patterns

**[CUSTOMIZE] Unit Test Template:**
```[language]
[Your test template]
```

**[CUSTOMIZE] Integration Test Template:**
```[language]
[Your test template]
```

---

## DATABASE PATTERNS (if applicable)

### [CUSTOMIZE] Schema

```sql
-- [Describe your schema]
[SQL or schema definition]
```

### [CUSTOMIZE] Migrations

```bash
# Create migration
{{MIGRATION_CREATE_COMMAND}}

# Run migrations
{{MIGRATION_RUN_COMMAND}}

# Rollback migration
{{MIGRATION_ROLLBACK_COMMAND}}
```

### [CUSTOMIZE] Query Patterns

**Pattern 1: [Name]**
```[language/SQL]
[Query template]
```

**Pattern 2: [Name]**
```[language/SQL]
[Query template]
```

---

## API PATTERNS (if applicable)

### [CUSTOMIZE] Endpoint Structure

```
{{API_BASE_URL}}/
├── /{{RESOURCE}}/           GET, POST
├── /{{RESOURCE}}/{{ID}}     GET, PATCH, DELETE
└── /{{NESTED}}/             [Description]
```

### [CUSTOMIZE] Request/Response Format

**Request:**
```json
{
  "field": "value"
}
```

**Response:**
```json
{
  "status": "ok",
  "data": {}
}
```

### [CUSTOMIZE] Error Handling

**Error Response:**
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": {}
}
```

---

## DEPENDENCY MANAGEMENT

### Adding Dependencies

```bash
# [CUSTOMIZE FOR YOUR PACKAGE MANAGER]

# Example: npm
npm install {{PACKAGE_NAME}}

# Example: pip
pip install {{PACKAGE_NAME}}
echo "{{PACKAGE_NAME}}" >> requirements.txt

# Example: cargo
cargo add {{PACKAGE_NAME}}

# Example: go
go get {{PACKAGE_NAME}}
```

### Updating Dependencies

```bash
# [CUSTOMIZE]

# Example: npm
npm update
npm audit fix

# Example: pip
pip install --upgrade {{PACKAGE_NAME}}

# Example: cargo
cargo update
```

---

## BUILD & DEPLOYMENT

### Build Process

```bash
# [CUSTOMIZE FOR YOUR BUILD SYSTEM]

# Development build
{{DEV_BUILD_COMMAND}}

# Production build
{{PROD_BUILD_COMMAND}}

# Build with optimizations
{{OPTIMIZED_BUILD_COMMAND}}
```

### Environment Variables

```bash
# [CUSTOMIZE]

# Required environment variables:
export {{VAR_NAME}}={{VALUE}}
export {{VAR_NAME}}={{VALUE}}

# Optional:
export {{VAR_NAME}}={{VALUE}}
```

### Configuration Files

**[CUSTOMIZE] - List important config files and their purpose:**
- `{{CONFIG_FILE_1}}` - [Description]
- `{{CONFIG_FILE_2}}` - [Description]

---

## KNOWN ISSUES & WORKAROUNDS

### [CUSTOMIZE] Issue 1: [Description]

```bash
# ❌ WRONG
[What doesn't work]

# ✅ CORRECT
[What does work]

# Reason: [Explanation]
```

### [CUSTOMIZE] Issue 2: [Description]

```bash
# Problem: [Description]

# Workaround:
[Solution steps]
```

---

## PERFORMANCE OPTIMIZATION

### [CUSTOMIZE] Profiling

```bash
# [Commands to profile your app]
{{PROFILE_COMMAND}}
```

### [CUSTOMIZE] Common Optimizations

1. **[Optimization Name]:**
   - Before: [metric]
   - After: [metric]
   - How: [description]

2. **[Optimization Name]:**
   - [Details]

---

## DEBUGGING

### [CUSTOMIZE] Debugging Tools

```bash
# Tool 1: [Name]
{{DEBUG_COMMAND_1}}

# Tool 2: [Name]
{{DEBUG_COMMAND_2}}
```

### [CUSTOMIZE] Common Debugging Scenarios

**Scenario 1: [Description]**
```bash
# Steps:
1. [Step]
2. [Step]
3. [Step]
```

**Scenario 2: [Description]**
```bash
# Steps:
[...]
```

---

## CODE REVIEW CHECKLIST

**Before Committing:**
- [ ] Code follows naming conventions
- [ ] Tests added/updated
- [ ] No commented-out code
- [ ] No debug logging left in
- [ ] Documentation updated (if needed)
- [ ] [Add project-specific checks]

**Before Deploying:**
- [ ] All tests pass
- [ ] Build succeeds
- [ ] Environment variables configured
- [ ] Migrations run (if applicable)
- [ ] [Add project-specific checks]

---

## TECH STACK REFERENCE

**[CUSTOMIZE]**

### Core Technologies
- **{{TECH_1}}** - [Version] - [Purpose]
- **{{TECH_2}}** - [Version] - [Purpose]
- **{{TECH_3}}** - [Version] - [Purpose]

### Development Tools
- **{{TOOL_1}}** - [Purpose]
- **{{TOOL_2}}** - [Purpose]

### Key Libraries
- **{{LIB_1}}** - [Purpose]
- **{{LIB_2}}** - [Purpose]

---

**Template Version:** 1.0 (2026-01-11)
**Origin:** XCalibr CLAUDE-WORKFLOWS.md
**Customize:** Replace all {{PLACEHOLDERS}} and add project-specific workflows
