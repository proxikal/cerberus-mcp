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
def _analyze_diff(before: str, after: str, file_path: str) -> DiffAnalysis:
    """
    Analyze differences between AI and user content using a 
    language-agnostic structural engine.

    Returns:
        DiffAnalysis object
    """
    import difflib

    before_lines = before.splitlines() if before else []
    after_lines = after.splitlines() if after else []

    # Line-level diff
    diff = list(difflib.unified_diff(before_lines, after_lines, lineterm=""))

    lines_added = len([line for line in diff if line.startswith("+") and not line.startswith("+++")])
    lines_removed = len([line for line in diff if line.startswith("-") and not line.startswith("---")])
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
    Works across Python, Go, TS, and Rust.
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
    """Detect if error handling was added using language-specific markers."""
    patterns = {
        "py": [r"try:", r"except\s+.*:"],
        "go": [r"if\s+err\s*!=\s*nil"],
        "ts": [r"try\s*\{", r"catch\s*\(.*\)\s*\{"],
        "js": [r"try\s*\{", r"catch\s*\(.*\)\s*\{"],
        "rs": [r"\.unwrap\(\)", r"match\s+.*\s*\{.*Err", r"\?"]
    }
    
    markers = patterns.get(ext, [r"try", r"catch", r"error"])
    
    before_count = sum(len(re.findall(p, before)) for p in markers)
    after_count = sum(len(re.findall(p, after)) for p in markers)
    
    return after_count > before_count

def _detect_identifier_renames(before: str, after: str) -> List[Tuple[str, str]]:
    """Detect potential identifier renames using set subtraction on words."""
    import re
    # Extract potential identifiers (alphanumeric starting with letter)
    ident_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
    
    before_idents = set(re.findall(ident_pattern, before))
    after_idents = set(re.findall(ident_pattern, after))
    
    # Removed from 'before', added to 'after'
    removed = before_idents - after_idents
    added = after_idents - before_idents
    
    # Filter common language keywords
    KEYWORDS = {"if", "else", "for", "while", "return", "def", "func", "function", "let", "const"}
    removed = {r for r in removed if r not in KEYWORDS}
    added = {a for r in added if a not in KEYWORDS}
    
    if len(removed) == 1 and len(added) == 1:
        return [(list(removed)[0], list(added)[0])]
    return []
```

---

## Pattern Extraction

```python
def _extract_pattern(diff_analysis: DiffAnalysis, file_path: str) -> str:
    """
    Extract high-level pattern from diff.
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
```

---

## Exit Criteria

```
✓ DiffAnalysis implemented using language-agnostic structural engine
✓ Identifier rename detection works for all alphanumeric languages
✓ Error handling detection supports Python, Go, TS, Rust, and JS
✓ Logic inversion detection implemented via conditional regex
✓ Integration with Phase 1 remains seamless
✓ Test suite covers 3+ languages (Python, Go, TS)
```

---

**Last Updated:** 2026-01-22
**Version:** 2.0 (Generalized for Polyglot Support - removed Python AST dependency)