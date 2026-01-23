# PHASE 15: MODE-AWARE CONTEXT

## Objective
Detect user intent mode (prototype/production/hotfix/audit) and filter memory injection based on mode appropriateness.

---

## Implementation Location

**File:** `src/cerberus/memory/mode_detection.py`

---

## Phase Assignment

**Rollout:** Phase Delta (Post-Gamma)

**Prerequisites:**
- ✅ Phase Beta complete (SQLite stable)
- ✅ Phase 7 complete (context injection working)
- ✅ Phase 13 complete (memory search with filtering)

**Why Phase Delta:**
- Core memory system must work first
- Mode detection is enhancement layer
- Requires proven injection pipeline
- Can be added incrementally

---

## Problem Statement

**Current behavior:**
User has rule: "Always write tests"
- Prototype mode (hacking together a script): Rule is annoying
- Production mode (shipping to prod): Rule is critical
- Hotfix mode (urgent bug fix): Rule blocks fast action

**Desired behavior:**
Rules are tagged with valid modes. Injection filters based on detected mode.

---

## Data Structures

```python
@dataclass
class IntentMode:
    """Detected user intent mode."""
    mode: str  # "prototype", "production", "hotfix", "audit", "exploration"
    confidence: float  # 0.0-1.0
    indicators: List[str]  # Evidence (e.g., ["urgent keyword", "small scope"])
    rigor_level: str  # "low", "medium", "high"

@dataclass
class ModeTaggedMemory:
    """Memory with mode applicability tags."""
    memory_id: str
    content: str
    valid_modes: List[str]  # Modes where this rule applies
    mode_priority: Dict[str, int]  # Priority per mode (1-10)

@dataclass
class ModeDetectionResult:
    """Result of mode detection."""
    primary_mode: IntentMode
    secondary_modes: List[IntentMode]  # Fallbacks
    context: Dict[str, Any]  # Raw context used for detection
```

---

## Mode Definitions

```python
MODES = {
    "prototype": {
        "description": "Fast iteration, dirty code acceptable, no tests required",
        "rigor": "low",
        "indicators": [
            "quick", "hack", "test", "try", "prototype", "poc", "draft",
            "experiment", "see if", "just want to"
        ],
        "scope_indicators": ["single file", "< 100 lines", "temporary"],
        "time_indicators": ["5 min", "quick", "fast"],
    },
    "production": {
        "description": "Shipping to prod, high quality, tests required, docs required",
        "rigor": "high",
        "indicators": [
            "production", "prod", "deploy", "release", "ship", "launch",
            "production-ready", "stable", "customer-facing"
        ],
        "scope_indicators": ["multiple files", "feature", "system"],
        "time_indicators": ["proper", "complete", "thorough"],
    },
    "hotfix": {
        "description": "Urgent bug fix, minimal changes, fast action",
        "rigor": "medium",
        "indicators": [
            "hotfix", "urgent", "critical", "bug", "fix", "broken", "down",
            "asap", "immediately", "emergency"
        ],
        "scope_indicators": ["specific function", "single issue", "targeted"],
        "time_indicators": ["urgent", "now", "asap", "immediately"],
    },
    "refactor": {
        "description": "Code cleanup, no new features, maintain behavior",
        "rigor": "high",
        "indicators": [
            "refactor", "cleanup", "improve", "restructure", "organize",
            "simplify", "optimize", "technical debt"
        ],
        "scope_indicators": ["existing code", "no new features"],
        "time_indicators": ["careful", "thorough"],
    },
    "audit": {
        "description": "Review existing code, no modifications",
        "rigor": "low",
        "indicators": [
            "review", "audit", "analyze", "understand", "explain",
            "how does", "what does", "walk me through"
        ],
        "scope_indicators": ["read-only", "no changes"],
        "time_indicators": [],
    },
    "exploration": {
        "description": "Learning codebase, no specific goal",
        "rigor": "low",
        "indicators": [
            "explore", "find", "search", "locate", "where is",
            "show me", "list", "what files"
        ],
        "scope_indicators": ["codebase", "project structure"],
        "time_indicators": [],
    },
}
```

---

## Core Algorithm: Mode Detection

```python
def detect_mode(user_prompt: str, context: Dict[str, Any]) -> ModeDetectionResult:
    """
    Detect user intent mode from prompt and context.

    Strategy:
    1. Extract indicators from user prompt
    2. Analyze scope (file count, LOC, complexity)
    3. Detect urgency keywords
    4. Score each mode
    5. Return primary + secondary modes

    Args:
        user_prompt: Current user message
        context: Session context (files, tools used, history)

    Returns:
        ModeDetectionResult with primary and secondary modes
    """

    # Step 1: Normalize prompt
    prompt_lower = user_prompt.lower()

    # Step 2: Score each mode
    mode_scores = {}

    for mode_name, mode_config in MODES.items():
        score = 0.0

        # Indicator matching
        for indicator in mode_config["indicators"]:
            if indicator in prompt_lower:
                score += 0.3

        # Scope matching
        scope_score = _analyze_scope(prompt_lower, context, mode_config["scope_indicators"])
        score += scope_score * 0.3

        # Time/urgency matching
        time_score = _analyze_urgency(prompt_lower, mode_config["time_indicators"])
        score += time_score * 0.2

        # Context signals (e.g., file count, tool usage)
        context_score = _analyze_context_signals(context, mode_name)
        score += context_score * 0.2

        mode_scores[mode_name] = min(score, 1.0)

    # Step 3: Rank modes
    ranked = sorted(mode_scores.items(), key=lambda x: x[1], reverse=True)

    # Step 4: Build result
    primary = ranked[0]
    primary_mode = IntentMode(
        mode=primary[0],
        confidence=primary[1],
        indicators=_extract_matched_indicators(prompt_lower, MODES[primary[0]]),
        rigor_level=MODES[primary[0]]["rigor"]
    )

    # Secondary modes (confidence > 0.3)
    secondary_modes = [
        IntentMode(
            mode=name,
            confidence=score,
            indicators=_extract_matched_indicators(prompt_lower, MODES[name]),
            rigor_level=MODES[name]["rigor"]
        )
        for name, score in ranked[1:4]
        if score > 0.3
    ]

    return ModeDetectionResult(
        primary_mode=primary_mode,
        secondary_modes=secondary_modes,
        context=context
    )


def _analyze_scope(prompt: str, context: Dict[str, Any], scope_indicators: List[str]) -> float:
    """
    Analyze scope from prompt and context.

    Signals:
    - "single file" vs "multiple files"
    - "< 100 lines" vs "entire system"
    - File count in context
    """
    score = 0.0

    # Prompt indicators
    for indicator in scope_indicators:
        if indicator in prompt:
            score += 0.5

    # Context signals
    file_count = len(context.get("modified_files", []))
    if file_count == 1:
        # Single file = prototype/hotfix more likely
        if "single file" in scope_indicators:
            score += 0.3
    elif file_count > 5:
        # Multiple files = production/refactor more likely
        if "multiple files" in scope_indicators:
            score += 0.3

    return min(score, 1.0)


def _analyze_urgency(prompt: str, time_indicators: List[str]) -> float:
    """
    Analyze urgency/time constraints.

    Signals:
    - "urgent", "asap", "now" = hotfix
    - "quick", "fast" = prototype
    - "proper", "thorough" = production
    """
    score = 0.0

    for indicator in time_indicators:
        if indicator in prompt:
            score += 0.5

    return min(score, 1.0)


def _analyze_context_signals(context: Dict[str, Any], mode: str) -> float:
    """
    Analyze context signals for mode.

    Signals:
    - Tool usage (Write = prototype, Edit = refactor)
    - File patterns (test files = production)
    - Session history (repeated corrections = refactor)
    """
    score = 0.0

    # Tool usage
    tools_used = context.get("tools_used", [])

    if mode == "prototype":
        if "Write" in tools_used:
            score += 0.3
    elif mode == "refactor":
        if "Edit" in tools_used and tools_used.count("Edit") > 3:
            score += 0.3
    elif mode == "production":
        if any("test" in f for f in context.get("modified_files", [])):
            score += 0.3

    return min(score, 1.0)


def _extract_matched_indicators(prompt: str, mode_config: Dict[str, Any]) -> List[str]:
    """Extract which indicators matched."""
    matched = []
    for indicator in mode_config["indicators"]:
        if indicator in prompt:
            matched.append(indicator)
    return matched[:3]  # Top 3 only
```

---

