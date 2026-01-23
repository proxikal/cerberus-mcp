"""
Phase 20: Silent Divergence Detection

Implements detection of silent code modifications - when users edit AI-generated
code without verbal correction. Captures 80% of corrections Phase 1 misses.

Phase 20A: Tool usage tracking and divergence detection
Phase 20B: Language-agnostic diff analysis

Architecture:
- track_tool_usage(): Record Edit/Write events during session
- detect_silent_divergences(): Find user modifications after AI responses
- _analyze_diff(): Language-agnostic structural diff analysis
- _extract_pattern(): Classify change type (bug_fix, rename, style, etc.)
- _generate_correction_from_divergence(): Create CorrectionCandidate
"""

import re
import uuid
import difflib
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple, Set
from enum import Enum


# ============================================================================
# Phase 20A: Data Structures
# ============================================================================

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
class DiffAnalysis:
    """Analysis of code differences."""
    lines_added: int
    lines_removed: int
    lines_modified: int
    change_type: str  # "minor", "moderate", "major"
    structural_changes: List[str] = field(default_factory=list)
    style_changes: List[str] = field(default_factory=list)


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
    correction_candidate: Optional[Any]  # CorrectionCandidate


# ============================================================================
# Phase 20A: Tool Usage Tracking
# ============================================================================

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


# ============================================================================
# Phase 20A: Silent Divergence Detection
# ============================================================================

def detect_silent_divergences(session_state: Any) -> List[SilentDivergence]:
    """
    Detect silent divergences from tool usage history.

    Strategy:
    1. Find Edit/Write events immediately after AI responses
    2. Compare AI-generated content vs user modification
    3. Analyze diff for patterns
    4. Generate correction candidates

    Args:
        session_state: SessionState object from Phase 17

    Returns:
        List of SilentDivergence objects
    """
    divergences = []
    tool_events = getattr(session_state, 'tool_usage_events', [])

    # Find potential divergences
    for event in tool_events:
        # Look for Edit/Write on same turn or turn+1 after AI response
        if event.tool in ["Edit", "Write"] and event.content_before and event.content_after:
            # AI generated content, user modified it
            if _is_significant_change(event.content_before, event.content_after):
                # Analyze diff
                diff_analysis = _analyze_diff(
                    event.content_before,
                    event.content_after,
                    event.file_path or ""
                )

                # Extract pattern
                pattern = _extract_pattern(diff_analysis, event.file_path or "")

                # Generate correction candidate
                candidate = _generate_correction_from_divergence(
                    event, diff_analysis, pattern
                )

                # Create diff summary
                diff_summary = _create_diff_summary(diff_analysis)

                # Calculate confidence
                confidence = _calculate_divergence_confidence(diff_analysis)

                divergence = SilentDivergence(
                    divergence_id=f"divergence-{uuid.uuid4().hex[:8]}",
                    turn_number=event.turn_number,
                    file_path=event.file_path or "",
                    ai_content=event.content_before,
                    user_content=event.content_after,
                    diff_summary=diff_summary,
                    pattern=pattern,
                    confidence=confidence,
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
    # Normalize whitespace
    before_normalized = " ".join(before.split())
    after_normalized = " ".join(after.split())

    if before_normalized == after_normalized:
        return False  # Only whitespace changes

    # Calculate similarity
    similarity = difflib.SequenceMatcher(None, before, after).ratio()

    # Significant if < 90% similar
    return similarity < 0.9


# ============================================================================
# Phase 20B: Diff Analysis (Language-Agnostic)
# ============================================================================

def _analyze_diff(before: str, after: str, file_path: str) -> DiffAnalysis:
    """
    Analyze differences between AI and user content using a
    language-agnostic structural engine.

    Args:
        before: AI-generated content
        after: User-modified content
        file_path: File path for language detection

    Returns:
        DiffAnalysis object
    """
    before_lines = before.splitlines() if before else []
    after_lines = after.splitlines() if after else []

    # Line-level diff
    diff = list(difflib.unified_diff(before_lines, after_lines, lineterm=""))

    lines_added = len([line for line in diff if line.startswith("+") and not line.startswith("+++")])
    lines_removed = len([line for line in diff if line.startswith("-") and not line.startswith("---")])
    lines_modified = min(lines_added, lines_removed)

    # Change magnitude
    total_lines = max(len(before_lines), len(after_lines), 1)
    change_ratio = (lines_added + lines_removed) / total_lines

    if change_ratio < 0.3:
        change_type = "minor"
    elif change_ratio < 0.6:
        change_type = "moderate"
    else:
        change_type = "major"

    # Structural analysis (Language-Agnostic)
    structural_changes = _detect_structural_changes(before, after, file_path)

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


def _detect_structural_changes(before: str, after: str, file_path: str) -> List[str]:
    """
    Detect structural code changes using Language Adapters.
    Works across Python, Go, TS, Rust, and JS.

    Args:
        before: AI-generated content
        after: User-modified content
        file_path: File path for extension detection

    Returns:
        List of detected structural changes
    """
    changes = []
    ext = file_path.split('.')[-1] if '.' in file_path else ""

    # Base indicators (Language Agnostic)
    if _detect_error_handling_addition(before, after, ext):
        changes.append("added error handling")

    if _detect_logic_inversion(before, after):
        changes.append("inverted logic/condition")

    # Rename detection (Cross-language regex)
    renames = _detect_identifier_renames(before, after)
    for old, new in renames:
        changes.append(f"renamed identifier: {old} → {new}")

    return changes


def _detect_error_handling_addition(before: str, after: str, ext: str) -> bool:
    """
    Detect if error handling was added using language-specific markers.

    Args:
        before: AI-generated content
        after: User-modified content
        ext: File extension

    Returns:
        True if error handling was added
    """
    patterns = {
        "py": [r"try:", r"except\s+"],
        "go": [r"if\s+err\s*!=\s*nil"],
        "ts": [r"try\s*\{", r"catch\s*\("],
        "js": [r"try\s*\{", r"catch\s*\("],
        "jsx": [r"try\s*\{", r"catch\s*\("],
        "tsx": [r"try\s*\{", r"catch\s*\("],
        "rs": [r"match\s+\w+", r"\bErr\b", r"Some\(", r"\?"]  # Rust error patterns
    }

    markers = patterns.get(ext, [r"try", r"catch", r"error"])

    before_count = sum(len(re.findall(p, before, re.IGNORECASE)) for p in markers)
    after_count = sum(len(re.findall(p, after, re.IGNORECASE)) for p in markers)

    return after_count > before_count


def _detect_logic_inversion(before: str, after: str) -> bool:
    """
    Detect if conditional logic was inverted.

    Args:
        before: AI-generated content
        after: User-modified content

    Returns:
        True if logic inversion detected
    """
    # Look for simple operator inversions
    operator_pairs = [
        ("==", "!="),
        ("<", ">"),
        ("<=", ">="),
    ]

    for op1, op2 in operator_pairs:
        # Check if operator changed from op1 to op2 or vice versa
        if op1 in before and op2 in after and op2 not in before:
            return True
        if op2 in before and op1 in after and op1 not in before:
            return True

    # Look for negation additions (simple string checks)
    if "if " in before and "if not " in after and "if not " not in before:
        return True
    if "if (" in before and "if (!" in after and "if (!" not in before:
        return True

    return False


def _detect_identifier_renames(before: str, after: str) -> List[Tuple[str, str]]:
    """
    Detect potential identifier renames using set subtraction on words.

    Args:
        before: AI-generated content
        after: User-modified content

    Returns:
        List of (old_name, new_name) tuples
    """
    # Extract potential identifiers (alphanumeric starting with letter)
    ident_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'

    before_idents = set(re.findall(ident_pattern, before))
    after_idents = set(re.findall(ident_pattern, after))

    # Removed from 'before', added to 'after'
    removed = before_idents - after_idents
    added = after_idents - before_idents

    # Filter common language keywords
    KEYWORDS = {
        "if", "else", "elif", "for", "while", "return", "def", "func", "function",
        "let", "const", "var", "class", "struct", "interface", "enum", "import",
        "from", "as", "try", "except", "catch", "finally", "throw", "raise",
        "true", "false", "null", "nil", "None", "this", "self", "super"
    }
    removed = {r for r in removed if r not in KEYWORDS}
    added = {a for a in added if a not in KEYWORDS}

    # Simple case: exactly one identifier removed and one added
    if len(removed) == 1 and len(added) == 1:
        return [(list(removed)[0], list(added)[0])]

    return []


def _detect_style_changes(before: str, after: str) -> List[str]:
    """
    Detect style-only changes.

    Args:
        before: AI-generated content
        after: User-modified content

    Returns:
        List of detected style changes
    """
    changes = []

    # Quote style change
    before_single = before.count("'")
    before_double = before.count('"')
    after_single = after.count("'")
    after_double = after.count('"')

    if before_single > before_double and after_double > after_single:
        changes.append("quote style: single → double")
    elif before_double > before_single and after_single > after_double:
        changes.append("quote style: double → single")

    # Indentation change
    before_tabs = before.count('\t')
    after_tabs = after.count('\t')
    if before_tabs == 0 and after_tabs > 0:
        changes.append("indentation: spaces → tabs")
    elif before_tabs > 0 and after_tabs == 0:
        changes.append("indentation: tabs → spaces")

    return changes


# ============================================================================
# Phase 20B: Pattern Extraction
# ============================================================================

def _extract_pattern(diff_analysis: DiffAnalysis, file_path: str) -> str:
    """
    Extract high-level pattern from diff.

    Args:
        diff_analysis: DiffAnalysis object
        file_path: File path

    Returns:
        Pattern name
    """
    structural = diff_analysis.structural_changes
    style = diff_analysis.style_changes

    if any("renamed" in change for change in structural):
        return "variable_rename"

    if any("error handling" in change for change in structural):
        return "error_handling"

    if any("logic" in change for change in structural):
        return "logic_fix"

    if style and not structural:
        return "style_change"

    return "refactor" if diff_analysis.change_type == "major" else "modification"


def _create_diff_summary(diff_analysis: DiffAnalysis) -> str:
    """
    Create human-readable diff summary.

    Args:
        diff_analysis: DiffAnalysis object

    Returns:
        Human-readable summary
    """
    parts = []

    # Lines changed
    parts.append(f"+{diff_analysis.lines_added} -{diff_analysis.lines_removed}")

    # Change type
    parts.append(f"({diff_analysis.change_type})")

    # Structural changes
    if diff_analysis.structural_changes:
        parts.append(", ".join(diff_analysis.structural_changes))

    # Style changes
    if diff_analysis.style_changes:
        parts.append(f"style: {', '.join(diff_analysis.style_changes)}")

    return " | ".join(parts)


def _calculate_divergence_confidence(diff_analysis: DiffAnalysis) -> float:
    """
    Calculate confidence score for divergence detection.

    Args:
        diff_analysis: DiffAnalysis object

    Returns:
        Confidence score (0.0-1.0)
    """
    # Base confidence from change magnitude
    if diff_analysis.change_type == "major":
        confidence = 0.9
    elif diff_analysis.change_type == "moderate":
        confidence = 0.7
    else:
        confidence = 0.5

    # Boost confidence if structural changes detected
    if diff_analysis.structural_changes:
        confidence = min(1.0, confidence + 0.1)

    # Reduce confidence if only style changes
    if diff_analysis.style_changes and not diff_analysis.structural_changes:
        confidence = max(0.3, confidence - 0.2)

    return confidence


def _generate_correction_from_divergence(
    event: ToolUsageEvent,
    diff_analysis: DiffAnalysis,
    pattern: str
) -> Optional[Any]:
    """
    Generate CorrectionCandidate from silent divergence.

    Args:
        event: ToolUsageEvent
        diff_analysis: DiffAnalysis object
        pattern: Extracted pattern

    Returns:
        CorrectionCandidate object or None
    """
    from cerberus.memory.session_analyzer import CorrectionCandidate

    # Generate user message based on pattern
    if pattern == "error_handling":
        user_message = "User added error handling silently"
    elif pattern == "variable_rename":
        # Extract renamed identifier from structural changes
        renames = [c for c in diff_analysis.structural_changes if "renamed" in c]
        if renames:
            user_message = f"User renamed variable: {renames[0]}"
        else:
            user_message = "User renamed variable to be more descriptive"
    elif pattern == "logic_fix":
        user_message = "User fixed conditional logic"
    elif pattern == "style_change":
        # Extract style preference from style changes
        if diff_analysis.style_changes:
            user_message = f"User changed code style: {diff_analysis.style_changes[0]}"
        else:
            user_message = "User changed code style"
    else:
        user_message = f"User modified generated code ({pattern})"

    # AI response is the content that was generated
    ai_response = f"Generated code in {event.file_path}"

    # Determine correction type
    if pattern in ["error_handling", "logic_fix"]:
        correction_type = "behavior"
    elif pattern == "style_change":
        correction_type = "style"
    elif pattern == "variable_rename":
        correction_type = "preference"
    else:
        correction_type = "rule"

    # Calculate confidence (silent corrections have lower initial confidence)
    confidence = _calculate_divergence_confidence(diff_analysis) * 0.8  # 80% of diff confidence

    return CorrectionCandidate(
        turn_number=event.turn_number,
        user_message=user_message,
        ai_response=ai_response,
        correction_type=correction_type,
        confidence=confidence,
        context_before=[]  # Silent divergences don't have conversation context
    )


# ============================================================================
# Phase 20: Integration with Phase 1
# ============================================================================

def combine_corrections(
    verbal_candidates: List[Any],
    silent_divergences: List[SilentDivergence]
) -> List[Any]:
    """
    Combine verbal corrections (Phase 1) with silent divergences (Phase 20).

    Args:
        verbal_candidates: List of CorrectionCandidate from Phase 1
        silent_divergences: List of SilentDivergence from Phase 20

    Returns:
        Combined list of CorrectionCandidate objects
    """
    combined = list(verbal_candidates)

    # Add silent divergence correction candidates
    for divergence in silent_divergences:
        if divergence.correction_candidate:
            combined.append(divergence.correction_candidate)

    return combined
