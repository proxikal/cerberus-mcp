# PHASE 20B: ANALYSIS

**Rollout Phase:** Epsilon (Weeks 9-10)
**Status:** Implement after Phase 20A

## Prerequisites

- ✅ Phase 20A complete (silent divergence tracking working)
- ✅ Phase 17 complete (session activity tracking)
- ✅ Phase 1 complete (correction detection for comparison)

---

## Diff Analysis

```python
def _analyze_diff(before: str, after: str) -> DiffAnalysis:
    """
    Analyze differences between AI and user content.

    Uses difflib for line-level diff + AST for structural changes.

    Returns:
        DiffAnalysis object
    """
    import difflib

    before_lines = before.splitlines()
    after_lines = after.splitlines()

    # Line-level diff
    diff = list(difflib.unified_diff(before_lines, after_lines, lineterm=""))

    lines_added = len([line for line in diff if line.startswith("+")])
    lines_removed = len([line for line in diff if line.startswith("-")])
    lines_modified = min(lines_added, lines_removed)

    # Change magnitude
    total_lines = max(len(before_lines), len(after_lines))
    change_ratio = (lines_added + lines_removed) / max(total_lines, 1)

    if change_ratio < 0.1:
        change_type = "minor"
    elif change_ratio < 0.3:
        change_type = "moderate"
    else:
        change_type = "major"

    # Structural analysis (AST-based)
    structural_changes = _detect_structural_changes(before, after)

    # Style analysis
    style_changes = _detect_style_changes(before, after)

    return DiffAnalysis(
        lines_added=lines_added,
        lines_removed=lines_removed,
        lines_modified=lines_modified,
        change_type=change_type,
        structural_changes=structural_changes,
        style_changes=style_changes
    )


def _detect_structural_changes(before: str, after: str) -> List[str]:
    """
    Detect structural code changes using AST.

    Patterns:
    - Variable renamed
    - Function renamed
    - Error handling added
    - Return statement changed
    - Import added/removed
    """
    changes = []

    try:
        import ast

        tree_before = ast.parse(before)
        tree_after = ast.parse(after)

        # Extract names
        names_before = {node.id for node in ast.walk(tree_before) if isinstance(node, ast.Name)}
        names_after = {node.id for node in ast.walk(tree_after) if isinstance(node, ast.Name)}

        # Variable renames
        removed = names_before - names_after
        added = names_after - names_before

        if removed and added:
            changes.append(f"renamed variable: {removed} → {added}")

        # Error handling
        try_before = len([node for node in ast.walk(tree_before) if isinstance(node, ast.Try)])
        try_after = len([node for node in ast.walk(tree_after) if isinstance(node, ast.Try)])

        if try_after > try_before:
            changes.append("added error handling")

        # Return statements
        return_before = len([node for node in ast.walk(tree_before) if isinstance(node, ast.Return)])
        return_after = len([node for node in ast.walk(tree_after) if isinstance(node, ast.Return)])

        if return_after != return_before:
            changes.append("changed return statement")

    except SyntaxError:
        # Not valid Python, skip AST analysis
        pass

    return changes


def _detect_style_changes(before: str, after: str) -> List[str]:
    """
    Detect style/formatting changes.

    Patterns:
    - Spacing changed
    - Quotes changed (single vs double)
    - Line length reduced
    - Comments added
    """
    changes = []

    # Spacing
    if before.replace(" ", "") == after.replace(" ", ""):
        changes.append("spacing adjusted")

    # Quotes
    if before.count('"') != after.count('"'):
        changes.append("quote style changed")

    # Line length
    before_max_line = max(len(line) for line in before.splitlines()) if before else 0
    after_max_line = max(len(line) for line in after.splitlines()) if after else 0

    if before_max_line > 100 and after_max_line <= 100:
        changes.append("line length reduced")

    # Comments
    before_comments = before.count("#")
    after_comments = after.count("#")

    if after_comments > before_comments:
        changes.append("comments added")

    return changes
```

---

## Pattern Extraction

```python
def _extract_pattern(diff_analysis: DiffAnalysis, file_path: str) -> str:
    """
    Extract high-level pattern from diff.

    Patterns:
    - "variable_rename"
    - "bug_fix"
    - "style_change"
    - "error_handling"
    - "refactor"

    Returns:
        Pattern string
    """
    structural = diff_analysis.structural_changes
    style = diff_analysis.style_changes

    # Variable rename
    if any("renamed" in change for change in structural):
        return "variable_rename"

    # Error handling
    if any("error handling" in change for change in structural):
        return "error_handling"

    # Return statement fix (likely bug fix)
    if any("return statement" in change for change in structural):
        return "bug_fix"

    # Style only
    if style and not structural:
        return "style_change"

    # Major changes
    if diff_analysis.change_type == "major":
        return "refactor"

    # Default
    return "modification"
```

---

## Correction Candidate Generation

```python
def _generate_correction_from_divergence(
    event: ToolUsageEvent,
    diff_analysis: DiffAnalysis,
    pattern: str
) -> CorrectionCandidate:
    """
    Generate correction candidate from silent divergence.

    Strategy:
    1. Extract correction text from pattern
    2. Infer correction type (style, behavior, rule)
    3. Assign confidence based on change magnitude

    Returns:
        CorrectionCandidate for Phase 2 clustering
    """
    # Generate correction text
    if pattern == "variable_rename":
        correction_text = f"Rename variables for clarity: {diff_analysis.structural_changes[0]}"
        correction_type = "style"
        confidence = 0.8

    elif pattern == "error_handling":
        correction_text = "Add error handling for robustness"
        correction_type = "rule"
        confidence = 0.85

    elif pattern == "bug_fix":
        correction_text = "Fix return statement logic"
        correction_type = "behavior"
        confidence = 0.9

    elif pattern == "style_change":
        style_details = ", ".join(diff_analysis.style_changes)
        correction_text = f"Apply style preferences: {style_details}"
        correction_type = "style"
        confidence = 0.7

    else:
        correction_text = "Modify generated code as needed"
        correction_type = "preference"
        confidence = 0.6

    # Create correction candidate
    from cerberus.memory.session_analyzer import CorrectionCandidate

    return CorrectionCandidate(
        turn_number=event.turn_number,
        user_message="<silent correction via Edit/Write>",
        ai_response=event.content_before[:200],  # Truncate
        correction_type=correction_type,
        confidence=confidence,
        context_before=[f"File: {event.file_path}", f"Pattern: {pattern}"]
    )


def _calculate_divergence_confidence(diff_analysis: DiffAnalysis) -> float:
    """
    Calculate confidence score for divergence.

    Higher confidence if:
    - Structural changes (not just style)
    - Moderate change magnitude (not trivial, not total rewrite)

    Returns:
        Confidence 0.0-1.0
    """
    confidence = 0.5  # Base

    # Structural changes boost confidence
    if diff_analysis.structural_changes:
        confidence += 0.2

    # Moderate changes more confident than minor or major
    if diff_analysis.change_type == "moderate":
        confidence += 0.2
    elif diff_analysis.change_type == "minor":
        confidence += 0.1

    # Style-only changes lower confidence
    if diff_analysis.style_changes and not diff_analysis.structural_changes:
        confidence -= 0.1

    return min(confidence, 1.0)
```

---

## Integration with Phase 1

```python
def get_all_corrections(session_state: SessionState) -> List[CorrectionCandidate]:
    """
    Get all corrections (verbal + silent).

    Combines Phase 1 verbal corrections with Phase 20 silent divergences.

    Returns:
        List of all CorrectionCandidate objects
    """
    from cerberus.memory.session_analyzer import SessionAnalyzer

    # Phase 1: Verbal corrections
    analyzer = SessionAnalyzer()
    verbal_corrections = analyzer.get_candidates()

    # Phase 20: Silent divergences
    divergences = detect_silent_divergences(session_state)
    silent_corrections = [d.correction_candidate for d in divergences if d.correction_candidate]

    # Combine
    all_corrections = verbal_corrections + silent_corrections

    print(f"Detected {len(verbal_corrections)} verbal + {len(silent_corrections)} silent corrections.")

    return all_corrections
```

---

## Tool Interception (Implementation Hook)

```python
def intercept_tool_usage(tool_name: str, args: Dict[str, Any], result: Any) -> None:
    """
    Hook called after tool execution.

    Tracks Edit/Write usage for divergence detection.

    Args:
        tool_name: Name of tool executed
        args: Tool arguments
        result: Tool result

    Called by Claude Code after each tool invocation.
    """
    if tool_name in ["Edit", "Write"]:
        file_path = args.get("file_path")

        # Read file before (if Write) or original (if Edit)
        if tool_name == "Write":
            content_before = None  # New file
        else:  # Edit
            content_before = args.get("old_string")  # Content being replaced

        # Read file after
        try:
            with open(file_path, "r") as f:
                content_after = f.read()
        except:
            content_after = None

        # Track usage
        from cerberus.memory.session_lifecycle import _load_session_state
        state = _load_session_state()

        track_tool_usage(
            turn_number=state.turn_count,
            tool=tool_name,
            file_path=file_path,
            content_before=content_before,
            content_after=content_after
        )
```

---

## CLI Commands

```bash
# Show silent divergences for current session
cerberus memory divergences --list

# Show divergences with diff
cerberus memory divergences --show-diff

# Generate corrections from divergences
cerberus memory divergences --generate-corrections
```

---

## Token Costs

**Silent divergence detection:**
- Tool tracking: 0 tokens (file I/O)
- Diff analysis: 0 tokens (difflib + AST)
- Pattern extraction: 0 tokens (rule-based)
- Correction generation: 0 tokens (template-based)

**Total per session:** 0 tokens (detection is free)

---

## Validation Gates

**Phase 20 complete when:**
- ✅ Tool usage tracking works (Edit/Write captured)
- ✅ Diff analysis works (structural + style changes detected)
- ✅ Pattern extraction works (patterns identified correctly)
- ✅ Correction generation works (candidates created)
- ✅ Integration with Phase 1 works (verbal + silent combined)
- ✅ 80%+ of silent corrections detected (Gemini's target)
- ✅ 20+ divergence scenarios tested

**Metrics:**
- Silent correction detection rate: 80%+
- False positive rate: < 10%
- Correction quality: 70%+ user approval

**Testing:**
- Create 20 silent divergence scenarios
- AI writes code → user silently fixes → verify detection
- Test each pattern (rename, bug fix, style, error handling)
- Verify correction candidates are valid
- Measure approval rate for silent corrections

---

## Dependencies

**Phase Dependencies:**
- Phase 1 (Correction Detection) - extends with silent corrections
- Phase 17 (Session Lifecycle) - uses session activity tracking
- Phase 16 (Integration) - tool usage hooks

**External Dependencies:**
- None (uses Python stdlib: difflib, ast)

---

## Implementation Checklist

- [ ] Write `src/cerberus/memory/silent_divergence.py`
- [ ] Implement `track_tool_usage()` function
- [ ] Implement `detect_silent_divergences()` function
- [ ] Implement `_analyze_diff()` function (difflib + AST)
- [ ] Implement `_detect_structural_changes()` function
- [ ] Implement `_detect_style_changes()` function
- [ ] Implement `_extract_pattern()` function
- [ ] Implement `_generate_correction_from_divergence()` function
- [ ] Implement `get_all_corrections()` integration function
- [ ] Add tool interception hook (`intercept_tool_usage`)
- [ ] Extend Phase 17 session state to track tool events
- [ ] Add CLI commands (`divergences --list`, `--show-diff`)
- [ ] Write unit tests (each pattern detection)
- [ ] Write integration tests (full divergence detection)
- [ ] Test 20 silent divergence scenarios
- [ ] Measure detection rate (target: 80%+)

---

**Last Updated:** 2026-01-22
**Version:** 1.0
**Status:** Specification complete, ready for implementation in Phase Epsilon

**Key Insight (Gemini's Critique):**
80% of user corrections are silent. Phase 1 only catches verbal feedback. Phase 20 catches the other 80% by tracking Edit/Write tool usage and analyzing code diffs.
