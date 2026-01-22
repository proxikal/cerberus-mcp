# PHASE 10: AGENT SELF-LEARNING

## Objective
Agent detects success/failure patterns and proposes memories proactively.

---

## Implementation Location

**File:** `src/cerberus/memory/agent_learning.py`

---

## Data Structures

```python
@dataclass
class AgentObservation:
    """Single observation from agent's actions."""
    observation_type: str  # "success", "failure", "pattern", "reinforcement"
    action_taken: str  # What agent did
    user_response: str  # User's reaction (approval, rejection, correction)
    context: Dict[str, Any]  # File, function, tool used, etc.
    confidence: float
    timestamp: datetime

@dataclass
class AgentProposal:
    """Agent-generated memory proposal."""
    id: str
    category: str  # "preference", "rule", "pattern"
    scope: str  # "universal", "language:X", "project:Y"
    content: str  # The rule (terse, imperative)
    evidence: List[str]  # Supporting observations (terse)
    confidence: float
    priority: int
```

---

## Detection Patterns

### Pattern 1: Success Reinforcement

**Trigger:** Action repeated 3+ times, user approved all

```python
def detect_success_pattern(observations: List[AgentObservation]) -> Optional[AgentProposal]:
    # Group by action type
    by_action = {}
    for obs in observations:
        action = obs.action_taken
        if action not in by_action:
            by_action[action] = []
        by_action[action].append(obs)

    # Find repeated successful actions
    for action, obs_list in by_action.items():
        if len(obs_list) >= 3:
            # Check all approved
            approvals = [
                o for o in obs_list
                if "approved" in o.user_response.lower() or
                   "good" in o.user_response.lower() or
                   "perfect" in o.user_response.lower()
            ]

            if len(approvals) == len(obs_list):
                # All approved → propose rule
                return AgentProposal(
                    id=f"agent-{uuid.uuid4().hex[:8]}",
                    category="rule",
                    scope=_infer_scope(obs_list),
                    content=_extract_rule(action, obs_list),
                    evidence=[f"{o.action_taken} → approved" for o in approvals[:3]],
                    confidence=len(approvals) / 10.0,
                    priority=1
                )

    return None
```

**Examples:**

```python
# Example 1: File splitting
observations = [
    "split proxy.go into 3 files → user: 'perfect'",
    "split cli.go into 2 files → user: 'good'",
    "planned split for config.go → user: 'exactly'"
]
→ proposal: "Plan file splits before writing (200-line limit)"
→ scope: "universal"
→ confidence: 0.3

# Example 2: Summary style
observations = [
    "summary: 3 sentences → user: 'good'",
    "summary: 2 sentences → user: 'perfect'",
    "summary: 4 sentences → user: 'too long'",
    "summary: 2 sentences → user: 'exactly'"
]
→ proposal: "Keep summaries 2-3 sentences max"
→ scope: "universal"
→ confidence: 0.4
```

---

### Pattern 2: Failure Avoidance

**Trigger:** Action caused correction 2+ times

```python
def detect_failure_pattern(observations: List[AgentObservation]) -> Optional[AgentProposal]:
    # Group by action type
    by_action = {}
    for obs in observations:
        if obs.observation_type == "failure":
            action = obs.action_taken
            if action not in by_action:
                by_action[action] = []
            by_action[action].append(obs)

    # Find repeated failures
    for action, obs_list in by_action.items():
        if len(obs_list) >= 2:
            # Extract what NOT to do
            return AgentProposal(
                id=f"agent-{uuid.uuid4().hex[:8]}",
                category="correction",
                scope=_infer_scope(obs_list),
                content=f"Avoid: {_extract_anti_pattern(action)}",
                evidence=[f"{o.action_taken} → {o.user_response}" for o in obs_list[:3]],
                confidence=len(obs_list) / 5.0,
                priority=2
            )

    return None
```

**Examples:**

```python
# Example 1: Verbose output
observations = [
    "wrote 500-word explanation → user: 'keep it short'",
    "wrote detailed steps → user: 'terse output'"
]
→ proposal: "Avoid: Verbose explanations"
→ scope: "universal"
→ confidence: 0.4

# Example 2: Large files
observations = [
    "wrote 350-line file → user: 'never exceed 200 lines'",
    "wrote 280-line file → user: 'split this first'"
]
→ proposal: "Avoid: Writing files >200 lines without planning"
→ scope: "universal"
→ confidence: 0.4
```

---

### Pattern 3: Project Inference

**Trigger:** Consistent pattern in codebase, agent follows it 3+ times

```python
def detect_project_pattern(
    observations: List[AgentObservation],
    codebase_analysis: Dict
) -> Optional[AgentProposal]:
    # Analyze codebase patterns
    patterns = codebase_analysis.get("patterns", {})

    # Check if agent followed pattern consistently
    for pattern_name, pattern_data in patterns.items():
        matches = [
            o for o in observations
            if pattern_name in o.action_taken
        ]

        if len(matches) >= 3:
            # Agent consistently follows pattern → propose as rule
            return AgentProposal(
                id=f"agent-{uuid.uuid4().hex[:8]}",
                category="pattern",
                scope=f"project:{codebase_analysis['project']}",
                content=f"Project pattern: {pattern_data['description']}",
                evidence=[f"applied in {o.context['file']}" for o in matches[:3]],
                confidence=0.6,
                priority=3
            )

    return None
```

**Examples:**

```python
# Example 1: Error handling
codebase shows: 95% of functions have "if err != nil { logger.Error() }"
agent followed: 3 new functions added same pattern
→ proposal: "Project pattern: Log errors before returning"
→ scope: "project:hydra"
→ confidence: 0.6

# Example 2: Test structure
codebase shows: All tests use testify suite pattern
agent followed: 2 new test files used same pattern
→ proposal: "Project pattern: Use testify.Suite for tests"
→ scope: "project:hydra"
→ confidence: 0.4
```

---

### Pattern 4: Approach Reinforcement

**Trigger:** Specific approach praised explicitly

```python
def detect_approach_reinforcement(observations: List[AgentObservation]) -> Optional[AgentProposal]:
    # Look for explicit praise
    praise_keywords = ["perfect", "exactly", "great", "excellent", "correct"]

    for obs in observations:
        if any(kw in obs.user_response.lower() for kw in praise_keywords):
            # Extract what was praised
            return AgentProposal(
                id=f"agent-{uuid.uuid4().hex[:8]}",
                category="preference",
                scope=_infer_scope([obs]),
                content=_extract_praised_approach(obs),
                evidence=[f"{obs.action_taken} → '{obs.user_response}'"],
                confidence=0.9,  # Explicit praise = high confidence
                priority=1
            )

    return None
```

**Examples:**

```python
# Example 1: TDD approach
observation: "wrote test first → user: 'perfect, that's TDD'"
→ proposal: "Write tests before implementation"
→ scope: "universal"
→ confidence: 0.9

# Example 2: Planning approach
observation: "created plan doc before coding → user: 'exactly what I wanted'"
→ proposal: "Create design docs before implementation"
→ scope: "universal"
→ confidence: 0.9
```

---

## Helper Functions

```python
def _infer_scope(observations: List[AgentObservation]) -> str:
    """
    Infer scope from observation context.
    If all observations from same project → project scope
    If all observations same language → language scope
    Otherwise → universal
    """
    projects = set()
    languages = set()

    for obs in observations:
        ctx = obs.context
        if "project" in ctx:
            projects.add(ctx["project"])
        if "language" in ctx:
            languages.add(ctx["language"])
        # Infer from file extension
        if "file" in ctx:
            ext = Path(ctx["file"]).suffix
            lang_map = {".py": "python", ".go": "go", ".ts": "typescript", ".js": "javascript"}
            if ext in lang_map:
                languages.add(lang_map[ext])

    if len(projects) == 1:
        return f"project:{list(projects)[0]}"
    if len(languages) == 1:
        return f"language:{list(languages)[0]}"
    return "universal"


def _extract_rule(action: str, observations: List[AgentObservation]) -> str:
    """
    Extract a concise rule from action and observations.
    """
    # Common action patterns → rules
    action_lower = action.lower()

    if "split" in action_lower:
        return "Plan file splits before writing (200-line limit)"
    if "test" in action_lower and "first" in action_lower:
        return "Write tests before implementation"
    if "summary" in action_lower or "terse" in action_lower:
        return "Keep summaries 2-3 sentences max"
    if "plan" in action_lower or "design" in action_lower:
        return "Create plan/design before implementation"

    # Fallback: use action directly
    return f"Continue: {action[:50]}"


def _extract_anti_pattern(action: str) -> str:
    """
    Extract what NOT to do from failed action.
    """
    action_lower = action.lower()

    if "verbose" in action_lower or "long" in action_lower:
        return "Verbose explanations"
    if "200" in action or "line" in action_lower:
        return "Writing files >200 lines without splitting"
    if "wait" in action_lower or "delay" in action_lower:
        return "Waiting for confirmation on obvious fixes"

    # Fallback
    return action[:50]


def _extract_praised_approach(obs: AgentObservation) -> str:
    """
    Extract the approach that was praised.
    """
    action = obs.action_taken.lower()
    response = obs.user_response.lower()

    # TDD detection
    if "test" in action and ("tdd" in response or "first" in action):
        return "Write tests before implementation (TDD)"

    # Planning detection
    if "plan" in action or "design" in action:
        return "Create design docs before implementation"

    # Splitting detection
    if "split" in action:
        return "Split large files before they exceed limits"

    # Fallback: use action
    return f"Continue approach: {obs.action_taken[:40]}"
```

---

## Observation Collection

```python
class ObservationCollector:
    """
    Collects observations during session.
    """

    def __init__(self):
        self.observations: List[AgentObservation] = []

    def record(
        self,
        action: str,
        user_response: str,
        context: Dict,
        obs_type: str = "success"
    ):
        """
        Record single observation.
        Called after each user response.
        """
        # Classify observation type
        if any(kw in user_response.lower() for kw in ["don't", "never", "stop"]):
            obs_type = "failure"
        elif any(kw in user_response.lower() for kw in ["perfect", "good", "correct"]):
            obs_type = "success"

        obs = AgentObservation(
            observation_type=obs_type,
            action_taken=action,
            user_response=user_response,
            context=context,
            confidence=self._calculate_confidence(user_response),
            timestamp=datetime.now()
        )

        self.observations.append(obs)

    def _calculate_confidence(self, response: str) -> float:
        """
        Calculate confidence from user response.
        Explicit praise = 0.9
        Implicit approval = 0.7
        Neutral = 0.5
        Correction = 0.3
        """
        response_lower = response.lower()

        if any(kw in response_lower for kw in ["perfect", "exactly", "excellent"]):
            return 0.9
        if any(kw in response_lower for kw in ["good", "correct", "right"]):
            return 0.7
        if any(kw in response_lower for kw in ["don't", "never", "stop"]):
            return 0.3

        return 0.5
```

---

## Proposal Generation

```python
class AgentLearningEngine:
    """
    Main engine for agent self-learning.
    """

    def __init__(self):
        self.collector = ObservationCollector()
        self.max_proposals = 5

    def generate_proposals(self, project: Optional[str] = None) -> List[AgentProposal]:
        """
        Generate agent proposals from observations.
        """
        proposals = []

        # Pattern 1: Success reinforcement
        success_proposal = detect_success_pattern(self.collector.observations)
        if success_proposal:
            proposals.append(success_proposal)

        # Pattern 2: Failure avoidance
        failure_proposal = detect_failure_pattern(self.collector.observations)
        if failure_proposal:
            proposals.append(failure_proposal)

        # Pattern 3: Project inference (requires codebase analysis)
        if project:
            codebase_analysis = self._analyze_codebase(project)
            pattern_proposal = detect_project_pattern(
                self.collector.observations,
                codebase_analysis
            )
            if pattern_proposal:
                proposals.append(pattern_proposal)

        # Pattern 4: Approach reinforcement
        approach_proposal = detect_approach_reinforcement(self.collector.observations)
        if approach_proposal:
            proposals.append(approach_proposal)

        # Sort by confidence * priority
        proposals.sort(key=lambda p: p.confidence / p.priority, reverse=True)

        # Take top N
        return proposals[:self.max_proposals]

    def _analyze_codebase(self, project: str) -> Dict:
        """
        Analyze codebase for patterns.
        Detects common coding patterns from file analysis.
        """
        patterns = {}
        project_path = Path.cwd()

        # Pattern 1: Error handling style
        error_patterns = self._detect_error_handling(project_path)
        if error_patterns:
            patterns["error_handling"] = error_patterns

        # Pattern 2: Test framework usage
        test_patterns = self._detect_test_patterns(project_path)
        if test_patterns:
            patterns["testing"] = test_patterns

        # Pattern 3: Import organization
        import_patterns = self._detect_import_patterns(project_path)
        if import_patterns:
            patterns["imports"] = import_patterns

        return {"project": project, "patterns": patterns}

    def _detect_error_handling(self, path: Path) -> Optional[Dict]:
        """Detect error handling patterns in codebase."""
        patterns = []

        # Go error handling
        go_files = list(path.rglob("*.go"))
        if go_files:
            err_nil_count = 0
            logger_count = 0
            for f in go_files[:20]:  # Sample 20 files max
                try:
                    content = f.read_text()
                    err_nil_count += content.count("if err != nil")
                    logger_count += content.count("logger.Error") + content.count("log.Error")
                except:
                    pass

            if err_nil_count > 5 and logger_count > 3:
                return {
                    "description": "Log errors before returning (Go style)",
                    "confidence": min(logger_count / err_nil_count, 1.0)
                }

        # Python exception handling
        py_files = list(path.rglob("*.py"))
        if py_files:
            try_count = 0
            logging_count = 0
            for f in py_files[:20]:
                try:
                    content = f.read_text()
                    try_count += content.count("try:")
                    logging_count += content.count("logging.") + content.count("logger.")
                except:
                    pass

            if try_count > 5 and logging_count > 3:
                return {
                    "description": "Use logging in exception handlers",
                    "confidence": min(logging_count / max(try_count, 1), 1.0)
                }

        return None

    def _detect_test_patterns(self, path: Path) -> Optional[Dict]:
        """Detect testing patterns in codebase."""
        # Go: testify vs standard
        go_test_files = list(path.rglob("*_test.go"))
        if go_test_files:
            testify_count = 0
            for f in go_test_files[:10]:
                try:
                    content = f.read_text()
                    if "testify" in content or "suite.Suite" in content:
                        testify_count += 1
                except:
                    pass

            if testify_count >= 3:
                return {
                    "description": "Use testify.Suite for test organization",
                    "confidence": testify_count / len(go_test_files[:10])
                }

        # Python: pytest vs unittest
        py_test_files = list(path.rglob("test_*.py")) + list(path.rglob("*_test.py"))
        if py_test_files:
            pytest_count = 0
            for f in py_test_files[:10]:
                try:
                    content = f.read_text()
                    if "import pytest" in content or "@pytest" in content:
                        pytest_count += 1
                except:
                    pass

            if pytest_count >= 3:
                return {
                    "description": "Use pytest fixtures and parametrize",
                    "confidence": pytest_count / len(py_test_files[:10])
                }

        return None

    def _detect_import_patterns(self, path: Path) -> Optional[Dict]:
        """Detect import organization patterns."""
        py_files = list(path.rglob("*.py"))
        if py_files:
            sorted_imports = 0
            for f in py_files[:10]:
                try:
                    content = f.read_text()
                    # Check for isort-style grouping (stdlib, third-party, local)
                    if "from __future__" in content or "\n\nimport " in content:
                        sorted_imports += 1
                except:
                    pass

            if sorted_imports >= 5:
                return {
                    "description": "Group imports: stdlib, third-party, local",
                    "confidence": sorted_imports / len(py_files[:10])
                }

        return None
```

---

## LLM Refinement

```python
class ProposalRefiner:
    """
    Use LLM to refine agent proposals into canonical form.
    """

    def __init__(self, llm_provider: str = "ollama"):
        self.llm = LLMClient(llm_provider)

    def refine(self, proposal: AgentProposal) -> AgentProposal:
        """
        Refine proposal content to terse, imperative form.
        """
        prompt = f"""Refine this agent-learned rule to terse imperative form (max 10 words):

Action: {proposal.content}
Evidence: {chr(10).join(proposal.evidence)}

Output format: "Verb object (constraint)"
Examples:
- "Plan file splits before writing (200-line limit)"
- "Write tests before implementation"
- "Log errors before returning"

Terse rule:"""

        try:
            refined = self.llm.generate(prompt).strip()
            proposal.content = refined
        except:
            # Fallback: Keep original
            pass

        return proposal
```

---

## Integration with Phase 3

```python
# At session end (combined with user corrections)

def on_session_end():
    # User corrections (Phase 1-3)
    user_proposals = generate_user_proposals()  # From Phase 3

    # Agent learning (Phase 7)
    agent_engine = AgentLearningEngine()
    agent_proposals = agent_engine.generate_proposals(project=detect_project())

    # Refine agent proposals
    refiner = ProposalRefiner()
    agent_proposals = [refiner.refine(p) for p in agent_proposals]

    # Combine
    all_proposals = user_proposals + agent_proposals

    # Present to user
    print(f"\n{'='*60}")
    print(f"SESSION LEARNING SUMMARY")
    print(f"{'='*60}")
    print(f"You corrected: {len(user_proposals)} behaviors")
    print(f"I noticed: {len(agent_proposals)} patterns")
    print(f"Total proposals: {len(all_proposals)}\n")

    # Show all
    for i, prop in enumerate(all_proposals, 1):
        source = "USER" if hasattr(prop, 'source_variants') else "AGENT"
        print(f"[{i}] ({source}) {prop.content}")

    # Approval
    approved = get_user_approval(all_proposals)
    store_approved(all_proposals, approved)
```

---

## Storage Format (AI-Native)

**File:** `.cerberus/agent_observations.json`

```json
{
  "session_id": "20260122-133514",
  "observations": [
    {
      "type": "success",
      "action": "split_file:proxy.go:3",
      "user": "perfect",
      "ctx": {"files": 3, "lines": [175, 67, 64]},
      "conf": 0.9,
      "ts": "2026-01-22T13:35:14Z"
    },
    {
      "type": "failure",
      "action": "write:verbose_explanation:500w",
      "user": "keep it short",
      "ctx": {"words": 500},
      "conf": 0.3,
      "ts": "2026-01-22T13:36:20Z"
    }
  ],
  "proposals": [
    {
      "id": "agent-a1b2c3d4",
      "cat": "rule",
      "scope": "universal",
      "rule": "Plan splits before writing (200-line limit)",
      "evidence": ["split_file:proxy.go → approved", "split_file:cli.go → approved"],
      "conf": 0.3,
      "pri": 1
    }
  ]
}
```

**Codes:**
- `type`: success, failure, pattern, reinforcement
- `action`: verb:target:metric (e.g., split_file:proxy.go:3)
- `user`: extracted user response (terse)
- `ctx`: context dict (file, lines, words, etc.)
- `conf`: confidence 0.0-1.0
- `cat`: preference, rule, correction, pattern
- `pri`: priority 1-3

---

## Exit Criteria

```
✓ ObservationCollector class implemented
✓ 4 detection patterns working
✓ Proposal generation functional
✓ LLM refinement working (with fallback)
✓ Integration with Phase 3 complete
✓ AI-native storage format validated
✓ Token budget: 1000 tokens (5 proposals)
✓ Tests: 15 scenarios with expected proposals
```

---

## Test Scenarios

```python
# Scenario 1: Success reinforcement
observations = [
    "split file 3 times → all approved",
    "wrote terse summary 4 times → all approved"
]
→ expect: 2 proposals (file splitting, terse summaries)

# Scenario 2: Failure avoidance
observations = [
    "wrote verbose explanation → corrected 2 times"
]
→ expect: 1 proposal (avoid verbose)

# Scenario 3: Project pattern
codebase: 95% error handling present
agent: followed pattern 3 times
→ expect: 1 proposal (project error handling)

# Scenario 4: Approach reinforcement
observation: "wrote test first → 'perfect, that's TDD'"
→ expect: 1 proposal (TDD approach, confidence=0.9)

# Scenario 5: Low confidence filtered
observations = [
    "did X once → user neutral"
]
→ expect: 0 proposals (confidence too low, count too low)
```

---

## Dependencies

- Existing: Phase 1-3 components
- New: LLM client (Ollama or Claude API)
- Optional: Codebase analyzer (Cerberus tools)

---

## Token Budget

- Observation collection: 0 tokens (regex + keywords)
- Pattern detection: 0 tokens (local analysis)
- LLM refinement: ~150 tokens per proposal (5 proposals = 750 tokens)
- Total: 750-1000 tokens per session

---

## Performance

- Observation recording: O(1) per turn
- Pattern detection: O(n) for n observations (n < 100 typical)
- Proposal generation: < 1 second
- LLM refinement: < 2 seconds (5 calls)
