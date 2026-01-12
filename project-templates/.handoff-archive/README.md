# HANDOFF Session Archive

**Purpose:** Historical session summaries from HANDOFF.md
**Rotation:** Automatic when HANDOFF.md exceeds 3 sessions

---

## ARCHIVE FORMAT

Files are organized by date:
- `2026-01-W02.md` - Week 2 of January 2026
- `2026-01-W03.md` - Week 3 of January 2026
- etc.

---

## ROTATION TRIGGER

When HANDOFF.md contains > 3 session summaries:
1. Extract oldest sessions (keep newest 2-3)
2. Group by week
3. Append to appropriate archive file
4. Update HANDOFF.md to keep only newest 2-3 sessions

---

## MANUAL ROTATION

```bash
# Future: May be automated
# For now: Manual rotation when HANDOFF.md gets too long
# Copy sessions to weekly archive file, remove from HANDOFF.md
```

---

## ARCHIVE FILE FORMAT

```markdown
# HANDOFF Archive - 2026-01-W02

## SESSION: 2026-01-11T21:45:00Z
**Commit:** abc1234
**Feature:** [Feature Name] ([details])
**Progress:** X/Y items ([%])

[Compact summary of what changed]

## SESSION: 2026-01-11T23:05:00Z
**Commit:** def5678
**Feature:** [Feature Name] ([details])
**Progress:** X/Y items ([%])

[Compact summary of what changed]
```

---

**Last Updated:** {{SETUP_DATE}}
