# PHASE 15B: MODE INTEGRATION

**Rollout Phase:** Delta (Weeks 7-8)
**Status:** Implement after Phase 15A

## Prerequisites

- ✅ Phase 15A complete (mode detection algorithm working)
- ✅ Phase 7 complete (context injection working)
- ✅ Phase 5 complete (storage working)

---

## Memory Tagging

### Manual Tagging (CLI)

```bash
# Tag memory with modes
cerberus memory tag <memory_id> --modes prototype,production

# Tag with priority
cerberus memory tag <memory_id> --mode production:10 --mode prototype:3
```

### Auto-Tagging Algorithm

```python
def auto_tag_memory(memory: MemoryProposal) -> List[str]:
    """
    Automatically infer valid modes for memory.

    Rules:
    - "Always write tests" → production, refactor (NOT prototype, hotfix)
    - "Keep it short" → prototype, hotfix, exploration (ALL modes)
    - "Document public APIs" → production, refactor (NOT prototype)
    - "Use X pattern" → production, refactor (NOT hotfix)

    Strategy:
    1. Extract rule type (quality, speed, process)
    2. Map to mode compatibility
    """

    content_lower = memory.content.lower()

    # Universal rules (apply to all modes)
    universal_keywords = ["prefer", "avoid", "never", "always use"]
    if any(kw in content_lower for kw in universal_keywords):
        # Check if it's a quality rule
        quality_keywords = ["test", "doc", "comment", "error handling", "validation"]
        if any(kw in content_lower for kw in quality_keywords):
            # Quality rules: NOT for prototype/hotfix
            return ["production", "refactor"]

    # Speed rules (prototype, hotfix)
    speed_keywords = ["quick", "fast", "short", "concise", "minimal"]
    if any(kw in content_lower for kw in speed_keywords):
        return ["prototype", "hotfix", "exploration"]

    # Pattern rules (production, refactor)
    pattern_keywords = ["pattern", "architecture", "structure", "design"]
    if any(kw in content_lower for kw in pattern_keywords):
        return ["production", "refactor"]

    # Default: All modes except audit/exploration
    return ["prototype", "production", "hotfix", "refactor"]
```

---

## Storage Integration

### SQLite Schema

*Note: The columns `valid_modes` and `mode_priority` were pre-provisioned in the `memory_store` table during Phase 12 to avoid SQLite limitations with ALTER TABLE.*

### Storage Operations (Phase 5 Extension)

```python
def store_memory_with_modes(memory: MemoryProposal) -> None:
    """Store memory with mode tags."""

    # Auto-tag modes
    valid_modes = auto_tag_memory(memory)

    # Default priorities (all equal)
    mode_priority = {mode: 5 for mode in valid_modes}

    db.execute("""
        INSERT INTO memory_store (
            id, category, scope, content,
            valid_modes, mode_priority
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (
        memory.id,
        memory.category,
        memory.scope,
        memory.content,
        json.dumps(valid_modes),
        json.dumps(mode_priority)
    ))
```

---

## Injection Integration (Phase 7 Extension)

```python
def inject_mode_aware(
    context: Dict[str, Any],
    user_prompt: str,
    budget: int = 1500
) -> str:
    """
    Inject memories filtered by detected mode.

    Strategy:
    1. Detect mode from user prompt
    2. Retrieve memories
    3. Filter by valid_modes
    4. Prioritize by mode_priority
    5. Inject within budget
    """

    # Step 1: Detect mode
    mode_result = detect_mode(user_prompt, context)
    primary_mode = mode_result.primary_mode.mode

    # Step 2: Retrieve memories (Phase 6)
    all_memories = retrieval.get_relevant(context)

    # Step 3: Filter by mode
    mode_filtered = [
        m for m in all_memories
        if primary_mode in m.valid_modes
    ]

    # Step 4: Prioritize
    prioritized = sorted(
        mode_filtered,
        key=lambda m: m.mode_priority.get(primary_mode, 5),
        reverse=True
    )

    # Step 5: Inject within budget (existing Phase 7 logic)
    return _inject_memories(prioritized, budget)
```

---

## CLI Commands

```bash
# Detect mode from prompt
cerberus memory detect-mode "quick script to parse logs"
# Output: prototype (confidence: 0.85)

# Show mode-filtered memories
cerberus memory show --mode production

# Tag memory with modes
cerberus memory tag <memory_id> --modes production,refactor

# Auto-tag all memories
cerberus memory auto-tag-modes
```

---

## Implementation in `src/cerberus/memory/mode_detection.py`

```python
"""
Phase 15: Mode-Aware Context

Detects user intent mode and filters memory injection.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json


MODES = {
    "prototype": {
        "description": "Fast iteration, dirty code acceptable",
        "rigor": "low",
        "indicators": ["quick", "hack", "test", "try", "prototype", "poc"],
        "scope_indicators": ["single file", "< 100 lines"],
        "time_indicators": ["quick", "fast"],
    },
    "production": {
        "description": "Shipping to prod, high quality required",
        "rigor": "high",
        "indicators": ["production", "prod", "deploy", "release", "ship"],
        "scope_indicators": ["multiple files", "feature"],
        "time_indicators": ["proper", "complete"],
    },
    "hotfix": {
        "description": "Urgent bug fix, minimal changes",
        "rigor": "medium",
        "indicators": ["hotfix", "urgent", "critical", "bug", "broken"],
        "scope_indicators": ["specific function", "single issue"],
        "time_indicators": ["urgent", "now", "asap"],
    },
    "refactor": {
        "description": "Code cleanup, no new features",
        "rigor": "high",
        "indicators": ["refactor", "cleanup", "improve", "restructure"],
        "scope_indicators": ["existing code"],
        "time_indicators": ["careful"],
    },
    "audit": {
        "description": "Review existing code, no modifications",
        "rigor": "low",
        "indicators": ["review", "audit", "analyze", "understand"],
        "scope_indicators": ["read-only"],
        "time_indicators": [],
    },
    "exploration": {
        "description": "Learning codebase",
        "rigor": "low",
        "indicators": ["explore", "find", "search", "where is"],
        "scope_indicators": ["codebase"],
        "time_indicators": [],
    },
}


@dataclass
class IntentMode:
    mode: str
    confidence: float
    indicators: List[str]
    rigor_level: str


@dataclass
class ModeDetectionResult:
    primary_mode: IntentMode
    secondary_modes: List[IntentMode]
    context: Dict[str, Any]


class ModeDetector:
    """Detects user intent mode from prompt and context."""

    def detect(self, user_prompt: str, context: Dict[str, Any]) -> ModeDetectionResult:
        """Detect mode from prompt."""
        prompt_lower = user_prompt.lower()
        mode_scores = {}

        for mode_name, mode_config in MODES.items():
            score = 0.0

            # Indicator matching
            for indicator in mode_config["indicators"]:
                if indicator in prompt_lower:
                    score += 0.3

            # Scope matching
            scope_score = self._analyze_scope(prompt_lower, context, mode_config["scope_indicators"])
            score += scope_score * 0.3

            # Time matching
            time_score = self._analyze_urgency(prompt_lower, mode_config["time_indicators"])
            score += time_score * 0.2

            # Context signals
            context_score = self._analyze_context_signals(context, mode_name)
            score += context_score * 0.2

            mode_scores[mode_name] = min(score, 1.0)

        # Rank modes
        ranked = sorted(mode_scores.items(), key=lambda x: x[1], reverse=True)

        primary = ranked[0]
        primary_mode = IntentMode(
            mode=primary[0],
            confidence=primary[1],
            indicators=self._extract_matched_indicators(prompt_lower, MODES[primary[0]]),
            rigor_level=MODES[primary[0]]["rigor"]
        )

        secondary_modes = [
            IntentMode(
                mode=name,
                confidence=score,
                indicators=self._extract_matched_indicators(prompt_lower, MODES[name]),
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

    def _analyze_scope(self, prompt: str, context: Dict[str, Any], scope_indicators: List[str]) -> float:
        score = 0.0
        for indicator in scope_indicators:
            if indicator in prompt:
                score += 0.5

        file_count = len(context.get("modified_files", []))
        if file_count == 1 and "single file" in scope_indicators:
            score += 0.3
        elif file_count > 5 and "multiple files" in scope_indicators:
            score += 0.3

        return min(score, 1.0)

    def _analyze_urgency(self, prompt: str, time_indicators: List[str]) -> float:
        score = 0.0
        for indicator in time_indicators:
            if indicator in prompt:
                score += 0.5
        return min(score, 1.0)

    def _analyze_context_signals(self, context: Dict[str, Any], mode: str) -> float:
        score = 0.0
        tools_used = context.get("tools_used", [])

        if mode == "prototype" and "Write" in tools_used:
            score += 0.3
        elif mode == "refactor" and tools_used.count("Edit") > 3:
            score += 0.3
        elif mode == "production" and any("test" in f for f in context.get("modified_files", [])):
            score += 0.3

        return min(score, 1.0)

    def _extract_matched_indicators(self, prompt: str, mode_config: Dict[str, Any]) -> List[str]:
        matched = []
        for indicator in mode_config["indicators"]:
            if indicator in prompt:
                matched.append(indicator)
        return matched[:3]


class ModeTagging:
    """Auto-tag memories with valid modes."""

    def auto_tag(self, memory_content: str) -> List[str]:
        """Infer valid modes for memory."""
        content_lower = memory_content.lower()

        # Universal rules
        universal_keywords = ["prefer", "avoid", "never", "always use"]
        if any(kw in content_lower for kw in universal_keywords):
            quality_keywords = ["test", "doc", "comment", "error handling"]
            if any(kw in content_lower for kw in quality_keywords):
                return ["production", "refactor"]

        # Speed rules
        speed_keywords = ["quick", "fast", "short", "concise"]
        if any(kw in content_lower for kw in speed_keywords):
            return ["prototype", "hotfix", "exploration"]

        # Pattern rules
        pattern_keywords = ["pattern", "architecture", "structure"]
        if any(kw in content_lower for kw in pattern_keywords):
            return ["production", "refactor"]

        return ["prototype", "production", "hotfix", "refactor"]
```

---

## Token Costs

**Mode Detection:**
- Keyword matching: 0 tokens (regex)
- Scoring algorithm: 0 tokens (Python)
- Total: 0 tokens

**Injection (no change from Phase 7):**
- Mode filtering happens before injection
- Same 1500 token budget
- Just smarter selection

**Storage:**
- 0 tokens (SQLite writes)

**Total per session:** 0 tokens added (filtering is free)

---

## Validation Gates

**Detection Accuracy:**
- 85%+ correct mode detection on 20 test prompts
- User feedback: "Yes, that's what I meant"

**Filtering Quality:**
- Prototype mode: No "Always write tests" rules injected
- Production mode: All quality rules injected
- User satisfaction: "System finally gets my intent"

**Performance:**
- Mode detection: < 50ms per prompt
- No impact on injection speed

**Testing:**
- 20 test prompts with known correct modes
- 5+ real sessions with mode-aware filtering
- A/B test: mode-aware vs mode-agnostic

---

## Dependencies

**Phase Dependencies:**
- Phase 7 (Context Injection) - extends filtering
- Phase 5 (Storage) - adds mode columns
- Phase 13 (Search) - uses mode filters

**External Dependencies:**
- None (pure Python, no new dependencies)

---

## Integration Points

**Phase 7 (Injection):**
```python
def inject(context: Dict[str, Any], user_prompt: str, budget: int = 1500) -> str:
    # Phase 15: Detect mode
    mode_result = ModeDetector().detect(user_prompt, context)

    # Existing retrieval...
    memories = retrieval.get_relevant(context)

    # Phase 15: Filter by mode
    filtered = [m for m in memories if mode_result.primary_mode.mode in m.valid_modes]

    # Existing injection...
    return inject_memories(filtered, budget)
```

**Phase 5 (Storage):**
```python
def store_memory(proposal: MemoryProposal) -> None:
    # Phase 15: Auto-tag modes
    valid_modes = ModeTagging().auto_tag(proposal.content)
    mode_priority = {mode: 5 for mode in valid_modes}

    # Store with modes
    storage.insert_with_modes(proposal, valid_modes, mode_priority)
```

---

## Migration Path

**For existing memories (no mode tags):**

```bash
# Auto-tag all existing memories
cerberus memory auto-tag-modes

# Verify tagging
cerberus memory stats --show-modes
```

**Backward compatibility:**
- Memories without mode tags default to all modes
- No breaking changes
- Gradual rollout

---

## Success Criteria

**Phase 15 complete when:**
- ✅ Mode detection works (85%+ accuracy)
- ✅ Memories are mode-tagged (auto or manual)
- ✅ Injection respects mode filtering
- ✅ User satisfaction: "System gets my intent"
- ✅ No performance degradation
- ✅ 5+ real sessions validated

**Validation method:**
- Test 20 prompts with known correct modes
- Measure: Does system inject appropriate memories?
- User feedback: "This is way smarter now"

---

## Example Scenarios

**Scenario 1: Prototype Mode**
```
User: "quick script to parse logs"
Detected: prototype (confidence: 0.85)
Injected:
  - Keep it short
  - Use X library for parsing
NOT injected:
  - Always write tests
  - Document public APIs
```

**Scenario 2: Production Mode**
```
User: "implement user authentication for production release"
Detected: production (confidence: 0.95)
Injected:
  - Always write tests
  - Document public APIs
  - Use X pattern for auth
  - Error handling required
NOT injected:
  - Keep it short (conflicts with quality requirements)
```

**Scenario 3: Hotfix Mode**
```
User: "urgent bug fix - login broken in prod"
Detected: hotfix (confidence: 0.9)
Injected:
  - Minimal changes only
  - Add logging for debugging
NOT injected:
  - Always write tests (too slow for hotfix)
  - Refactor surrounding code (scope creep)
```

---

## Implementation Checklist

- [ ] Write `src/cerberus/memory/mode_detection.py`
- [ ] Add `ModeDetector` class
- [ ] Implement `detect()` algorithm
- [ ] Add `ModeTagging` class
- [ ] Implement `auto_tag()` algorithm
- [ ] Extend SQLite schema (mode columns)
- [ ] Update Phase 5 storage to tag modes
- [ ] Update Phase 7 injection to filter by mode
- [ ] Add CLI commands (`detect-mode`, `tag`, `auto-tag-modes`)
- [ ] Write unit tests (20 test prompts)
- [ ] Write integration tests (detection + injection)
- [ ] Validate with 5+ real sessions
- [ ] Measure user satisfaction

---

**Last Updated:** 2026-01-22
**Version:** 1.0
**Status:** Specification complete, ready for implementation in Phase Delta