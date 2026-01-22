# PHASE 1: SESSION CORRECTION DETECTION

## Objective
Detect user corrections in real-time without manual `memory_learn()` calls.

---

## Implementation Location

**File:** `src/cerberus/memory/session_analyzer.py`

---

## Data Structures

```python
@dataclass
class CorrectionCandidate:
    turn_number: int
    user_message: str
    ai_response: str
    correction_type: str  # "style", "behavior", "rule", "preference"
    confidence: float
    context_before: List[str]  # Previous 3 turns
```

```python
@dataclass
class SessionCorrections:
    session_id: str
    timestamp: datetime
    candidates: List[CorrectionCandidate]
    project: Optional[str]
```

---

## Detection Patterns

### Pattern 1: Direct Negation
```
User: "don't write for humans"
AI: <does something>
User: "you did X again, I said Y"

→ confidence: 0.9
→ type: "behavior"
```

### Pattern 2: Repetition
```
User: "keep it short" (turn 5)
User: "be concise" (turn 12)
User: "terse output" (turn 18)

→ confidence: 0.8
→ type: "style"
```

### Pattern 3: Correction After Action
```
AI: <writes 300-line file>
User: "never exceed 200 lines"

→ confidence: 1.0
→ type: "rule"
```

### Pattern 4: Multi-Turn Correction
```
User: "fix the bug"
AI: <attempts fix>
User: "no, I meant do Y not X"
AI: <attempts Y>
User: "yes, always do Y for this case"

→ confidence: 0.95
→ type: "rule"
```

---

## Detection Algorithm

```python
class SessionAnalyzer:
    def __init__(self):
        self.conversation_buffer: List[Tuple[str, str]] = []  # (role, message)
        self.candidates: List[CorrectionCandidate] = []
        self.negation_words = {"don't", "never", "stop", "avoid", "not"}
        self.repetition_threshold = 2

    def analyze_turn(self, user_msg: str, ai_response: str) -> Optional[CorrectionCandidate]:
        self.conversation_buffer.append(("user", user_msg))
        self.conversation_buffer.append(("assistant", ai_response))

        # Pattern 1: Direct negation
        if any(neg in user_msg.lower() for neg in self.negation_words):
            if self._has_command_structure(user_msg):
                return CorrectionCandidate(
                    turn_number=len(self.conversation_buffer) // 2,
                    user_message=user_msg,
                    ai_response=ai_response,
                    correction_type="behavior",
                    confidence=0.9,
                    context_before=self._get_context(3)
                )

        # Pattern 2: Repetition detection
        similar = self._find_similar_messages(user_msg, threshold=0.7)
        if len(similar) >= self.repetition_threshold:
            return CorrectionCandidate(
                turn_number=len(self.conversation_buffer) // 2,
                user_message=user_msg,
                ai_response=ai_response,
                correction_type="style",
                confidence=0.8,
                context_before=similar
            )

        # Pattern 3: Post-action correction
        if self._is_correction_language(user_msg) and len(self.conversation_buffer) > 2:
            prev_ai = self.conversation_buffer[-3][1] if len(self.conversation_buffer) >= 3 else ""
            if self._ai_took_action(prev_ai):
                return CorrectionCandidate(
                    turn_number=len(self.conversation_buffer) // 2,
                    user_message=user_msg,
                    ai_response=ai_response,
                    correction_type="rule",
                    confidence=1.0,
                    context_before=self._get_context(2)
                )

        return None

    def _has_command_structure(self, msg: str) -> bool:
        # Check for imperative mood
        command_starters = ["don't", "never", "always", "stop", "keep", "make sure"]
        return any(msg.lower().startswith(cmd) for cmd in command_starters)

    def _find_similar_messages(self, msg: str, threshold: float) -> List[str]:
        # Semantic similarity (stub - implement with embeddings in Phase 2)
        similar = []
        keywords = set(msg.lower().split())
        for role, prev_msg in self.conversation_buffer[:-2]:
            if role == "user":
                prev_keywords = set(prev_msg.lower().split())
                overlap = len(keywords & prev_keywords) / len(keywords | prev_keywords)
                if overlap > threshold:
                    similar.append(prev_msg)
        return similar

    def _is_correction_language(self, msg: str) -> bool:
        indicators = ["you", "again", "told you", "said", "mentioned", "I asked"]
        return any(ind in msg.lower() for ind in indicators)

    def _ai_took_action(self, ai_msg: str) -> bool:
        # Check if AI used tools or wrote code
        action_markers = ["<invoke", "```", "I've", "I'll", "Let me"]
        return any(marker in ai_msg for marker in action_markers)

    def _get_context(self, n: int) -> List[str]:
        return [msg for role, msg in self.conversation_buffer[-n*2:] if role == "user"]
```

---

## Integration Point

**Hook Location:** Claude Code session hook or MCP server middleware

```python
# In MCP server request handler
session_analyzer = SessionAnalyzer()

def handle_message(user_msg: str) -> str:
    ai_response = generate_response(user_msg)

    # Analyze for corrections
    candidate = session_analyzer.analyze_turn(user_msg, ai_response)
    if candidate and candidate.confidence > 0.7:
        session_analyzer.candidates.append(candidate)

    return ai_response
```

---

## Storage

**File:** `.cerberus/session_corrections.json`

```json
{
  "session_id": "20260122-133514",
  "timestamp": "2026-01-22T13:35:14Z",
  "project": "cerberus",
  "candidates": [
    {
      "turn": 5,
      "user_message": "don't write for humans, write for AI agents",
      "correction_type": "behavior",
      "confidence": 0.9,
      "context": ["previous message 1", "previous message 2"]
    }
  ]
}
```

---

## Exit Criteria

```
✓ SessionAnalyzer class implemented
✓ 4 detection patterns working
✓ Candidates stored to .cerberus/session_corrections.json
✓ Confidence scoring functional
✓ Integration hook in place (MCP or Claude Code)
✓ Tests: 10 scenarios with expected detections
```

---

## Test Scenarios

```python
# Scenario 1: Direct negation
user: "don't write verbose explanations"
→ expect: CorrectionCandidate(confidence=0.9, type="behavior")

# Scenario 2: Repetition
user: "keep it short" (turn 1)
user: "be concise" (turn 4)
user: "terse output" (turn 7)
→ expect: CorrectionCandidate(confidence=0.8, type="style")

# Scenario 3: Post-action
AI: <writes 300-line file>
user: "never exceed 200 lines per file"
→ expect: CorrectionCandidate(confidence=1.0, type="rule")

# Scenario 4: False positive (should NOT detect)
user: "I don't know what to do"
→ expect: None (no correction detected)
```

---

## Dependencies

- None (pure Python)

---

## Token Budget

- Detection: 0 tokens (regex + keyword matching)
- Storage: ~100 tokens per candidate (lightweight JSON)
