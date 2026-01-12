# AI Agent Handoff Document

**Project:** {{PROJECT_NAME}}
**Last Updated:** {{LAST_UPDATED}}
**Updated By:** Claude Sonnet 4.5

**Cross-Reference:** See {{PROJECT_NAME}}.md for rules, workflows, architecture patterns

---

## AGENT UPDATE CHECKLIST

After completing work, update these sections:
1. **Current State** - Move completed items, update metrics
2. **Detailed Task List** - Mark completed, add new tasks if discovered
3. **Success Metrics** - Update progress percentages
4. **Recent Session Summary** - What changed, commits, issues resolved
5. **Timestamp** - Update "Last Updated" at top
6. **Session Rotation** - If > 3 sessions exist, rotate oldest to archive (see below)

---

## SESSION ROTATION PROTOCOL

**Trigger:** When HANDOFF.md contains > 3 "RECENT SESSION SUMMARY" sections
**Action:** Archive oldest sessions, keep newest 2-3
**Location:** `.handoff-archive/YYYY-MM-Wxx.md` (grouped by week)

**Rotation Steps:**
```bash
# 1. Count sessions in HANDOFF.md
grep -c "## RECENT SESSION SUMMARY" HANDOFF.md

# 2. If count > 3, extract oldest sessions:
# - Copy oldest session(s) to .handoff-archive/2026-01-W02.md
# - Remove from HANDOFF.md (keep newest 2-3)

# 3. Update .handoff-archive/README.md if needed
```

**Archive Format:**
- Week-based filenames: `2026-01-W02.md` (ISO week number)
- Compact format: Date, Commit, Feature, Progress
- See `.handoff-archive/README.md` for template

**Current Status:** [X] sessions (rotation [needed/not needed yet])

---

## CURRENT STATE

**[CUSTOMIZE THIS SECTION FOR YOUR PROJECT]**

**System Metrics:**
- [Key metric 1]: [value]
- [Key metric 2]: [value]
- [Progress metric]: X/Y complete ([%])

### Completed Features

**[CUSTOMIZE - list completed features/milestones]**
1. **[Feature Name]** ([details]) - Commit `[hash]`
2. **[Feature Name]** ([details]) - Commit `[hash]`

### Pending Features

**[CUSTOMIZE - list pending work]**
- [Feature/Task 1]
- [Feature/Task 2]

---

## DETAILED TASK LIST

**[CUSTOMIZE - track specific tasks]**

**Completed:**
- [Task 1] - `[commit hash]`
- [Task 2] - `[commit hash]`

**Next Priority: [Task Name]**

**Pending:**
- [Task 3]
- [Task 4]

---

## SUCCESS METRICS

**[CUSTOMIZE - define what "done" means]**

**Overall Progress: X/Y tasks ([%])**
- [Category 1]: X/Y ✅ or ⏳
- [Category 2]: X/Y ✅ or ⏳
- [Category 3]: X/Y ⏳

**Project Complete When:**
- [Success criterion 1]
- [Success criterion 2]
- [Success criterion 3]

---

## RECENT SESSION SUMMARY ({{SESSION_DATE}})

**What Changed:**
- ✅ [Change 1]
- ✅ [Change 2]
- ✅ [Change 3]

**Progress Update:**
- [Metric]: X/Y ([%], +[delta]% this session)

**Commits:**
- `[hash]` - [commit message]

**Next Task:** [What to work on next]

---

**END HANDOFF**
