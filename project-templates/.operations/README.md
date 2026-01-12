# {{PROJECT_NAME}} Operation Checklists

**Purpose:** Machine-readable operation checklists for AI agents
**Format:** YAML (structured, parseable, compact)
**Benefits:** 50-80% reduction in context vs prose documentation

---

## AVAILABLE CHECKLISTS

### deploy.yml
Complete deployment workflows:
- `deploy_full` - Full deployment (test → commit → deploy → build → verify)
- `quick_deploy` - One-liner for fast deploys
- `health_check` - Verify all services running
- `troubleshoot` - Common issue resolution

**Note:** This file is OPTIONAL - skip if your project doesn't require deployment workflows.

---

## USAGE

**For AI Agents:**
1. Load checklist: `cat .operations/deploy.yml`
2. Parse YAML structure
3. Execute steps in order
4. Verify expected results

**For Humans:**
- Checklists serve as quick reference
- Full commands in {{PROJECT_NAME}}-VPS-OPS.md (if applicable)
- YAML format is readable by both humans and machines

---

## ADDING NEW CHECKLISTS

```yaml
operation_name:
  description: "What this operation does"
  steps:
    - step: "step_identifier"
      command: "bash command here"
      note: "Additional context"
      expect: "Expected output/result"
```

---

## CONTEXT SAVINGS

**Before (prose):**
- Full documentation with explanations
- Agents load entire prose doc

**After (checklist):**
- Structured YAML, agent-parseable
- Agents extract only needed operations
- 50-80% reduction when loading specific operations

---

**Last Updated:** {{SETUP_DATE}}
