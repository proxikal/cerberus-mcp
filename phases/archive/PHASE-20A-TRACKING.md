# PHASE 20: SILENT DIVERGENCE DETECTION

## Objective
Detect when user silently fixes or modifies AI-generated code without verbal correction. Capture 80% of corrections that Phase 1 misses.

---

## Implementation Location

**File:** `src/cerberus/memory/silent_divergence.py`

---

## Phase Assignment

**Rollout:** Phase Epsilon (Post-Delta)

**Prerequisites:**
- ✅ Phase 1 complete (correction detection for verbal feedback)
- ✅ Phase 17 complete (session activity tracking)
- ✅ Phase 16 complete (tool usage tracking in session state)

**Why Phase Epsilon:**
- Addresses Gemini's #1 critique (80% of corrections are silent)
- Requires session activity tracking (Phase 17)
- Enhancement layer on Phase 1

---

## Problem Statement

**Current Phase 1 behavior:**
- Only detects verbal corrections ("don't do X", "you did Y again")
- Misses silent fixes (user edits code without saying anything)

**Reality:**
```
AI: <writes function with bug>
User: <edits file to fix bug>  # No verbal feedback
User: "ok run the tests"

→ Phase 1 detection: MISSED (no verbal correction)
→ Silent divergence: User fixed AI's code without comment
```

**Desired behavior:**
- Detect Edit/Write tool usage immediately after AI generates code
- Compare AI output vs user modification
- Extract pattern ("AI did X, user changed to Y")
- Generate correction candidate

---

## Data Structures

```python
@dataclass
class ToolUsageEvent:
    """Tool usage tracking event."""
    turn_number: int
    tool: str  # "Edit", "Write", "Read", "Bash"
    file_path: Optional[str]
    content_before: Optional[str]  # AI-generated content
    content_after: Optional[str]   # User-modified content
    timestamp: datetime

@dataclass
class SilentDivergence:
    """Detected silent divergence."""
    divergence_id: str
    turn_number: int
    file_path: str
    ai_content: str
    user_content: str
    diff_summary: str  # Human-readable diff
    pattern: str  # "variable_rename", "bug_fix", "style_change", "refactor"
    confidence: float  # 0.0-1.0
    correction_candidate: Optional[CorrectionCandidate]

@dataclass
class DiffAnalysis:
    """Analysis of code differences."""
    lines_added: int
    lines_removed: int
    lines_modified: int
    change_type: str  # "minor", "moderate", "major"
    structural_changes: List[str]  # ["renamed variable", "added error handling"]
    style_changes: List[str]  # ["spacing", "quotes"]
```

---

## Tool Usage Tracking

```python
def track_tool_usage(
    turn_number: int,
    tool: str,
    file_path: Optional[str],
    content_before: Optional[str],
    content_after: Optional[str]
) -> None:
    """
    Track tool usage during session.

    Called by Phase 16 hooks after each tool invocation.

    Args:
        turn_number: Current turn number
        tool: Tool name
        file_path: File being modified (if applicable)
        content_before: Content before modification
        content_after: Content after modification
    """
    event = ToolUsageEvent(
        turn_number=turn_number,
        tool=tool,
        file_path=file_path,
        content_before=content_before,
        content_after=content_after,
        timestamp=datetime.now()
    )

    # Append to session state
    from cerberus.memory.session_cli import update_session_activity
    update_session_activity("tool_use", {"tool": tool, "event": event})
```

---

## Silent Divergence Detection Algorithm

```python
def detect_silent_divergences(session_state: SessionState) -> List[SilentDivergence]:
    """
    Detect silent divergences from tool usage history.

    Strategy:
    1. Find Edit/Write events immediately after AI responses
    2. Compare AI-generated content vs user modification
    3. Analyze diff for patterns
    4. Generate correction candidates

    Returns:
        List of SilentDivergence objects
    """
    divergences = []
    tool_events = session_state.tools_used

    # Find potential divergences
    for i, event in enumerate(tool_events):
        # Look for Edit/Write on same turn or turn+1 after AI response
        if event.tool in ["Edit", "Write"] and event.content_before:
            # AI generated content, user modified it
            if _is_significant_change(event.content_before, event.content_after):
                # Analyze diff
                diff_analysis = _analyze_diff(event.content_before, event.content_after)

                # Extract pattern
                pattern = _extract_pattern(diff_analysis, event.file_path)

                # Generate correction candidate
                candidate = _generate_correction_from_divergence(
                    event, diff_analysis, pattern
                )

                divergence = SilentDivergence(
                    divergence_id=f"divergence-{uuid.uuid4().hex[:8]}",
                    turn_number=event.turn_number,
                    file_path=event.file_path,
                    ai_content=event.content_before,
                    user_content=event.content_after,
                    diff_summary=_create_diff_summary(diff_analysis),
                    pattern=pattern,
                    confidence=_calculate_divergence_confidence(diff_analysis),
                    correction_candidate=candidate
                )

                divergences.append(divergence)

    return divergences


def _is_significant_change(before: str, after: str) -> bool:
    """
    Check if change is significant (not just whitespace).

    Returns:
        True if significant change detected
    """
    import difflib

    # Normalize whitespace
    before_normalized = " ".join(before.split())
    after_normalized = " ".join(after.split())

    if before_normalized == after_normalized:
        return False  # Only whitespace changes

    # Calculate similarity
    similarity = difflib.SequenceMatcher(None, before, after).ratio()

    # Significant if < 90% similar
    return similarity < 0.9
```

---

