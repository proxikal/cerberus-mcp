# PHASE 10B: REFINEMENT

**Rollout Phase:** Gamma (Weeks 5-6)
**Status:** Implement after Phase 10A

## Prerequisites

- ✅ Phase 10A complete (detection patterns implemented)

---

## Proposal Refinement

```python
class ProposalRefiner:
    """
    Refine agent proposals into canonical form.

    PRIMARY: Rule-based refinement (no dependencies, instant)
    OPTIONAL: LLM enhancement (if Ollama available AND enabled)
    """

    def __init__(self, use_llm: bool = False):
        """
        Args:
            use_llm: If True AND Ollama is available, use LLM for refinement.
                     Default is False - rule-based works well.
        """
        self.use_llm = use_llm

    def refine(self, proposal: AgentProposal) -> AgentProposal:
        """
        Refine proposal content to terse, imperative form.
        """
        # PRIMARY: Rule-based refinement
        refined = self._refine_with_rules(proposal.content, proposal.evidence)

        # OPTIONAL: LLM enhancement
        if self.use_llm:
            llm_refined = self._try_llm_refinement(refined, proposal)
            if llm_refined:
                refined = llm_refined

        proposal.content = refined
        return proposal

    def _refine_with_rules(self, content: str, evidence: List[str]) -> str:
        """
        Refine content using rule-based transformations.
        """
        content_lower = content.lower()

        # Template mappings for common patterns
        REFINEMENT_TEMPLATES = {
            # File operations
            "split": "Plan file splits before writing (200-line limit)",
            "separate": "Plan file splits before writing (200-line limit)",

            # Testing
            "test first": "Write tests before implementation (TDD)",
            "tdd": "Write tests before implementation (TDD)",
            "test before": "Write tests before implementation (TDD)",

            # Output style
            "summary": "Keep summaries 2-3 sentences max",
            "terse": "Keep output terse and actionable",
            "concise": "Keep output concise",
            "short": "Keep explanations short",
            "verbose": "Avoid verbose explanations",

            # Planning
            "plan first": "Create plan before implementation",
            "design first": "Create design docs before coding",
            "plan before": "Create plan before implementation",

            # Error handling
            "log error": "Log errors before returning",
            "error handling": "Handle errors explicitly with logging",
        }

        # Check for template matches
        for keyword, template in REFINEMENT_TEMPLATES.items():
            if keyword in content_lower:
                return template

        # Fallback: Clean up the content
        return self._clean_content(content)

    def _clean_content(self, content: str) -> str:
        """
        Clean content into imperative form.
        """
        import re

        # Remove common filler phrases
        FILLER_PATTERNS = [
            r"^continue:?\s*",
            r"^always\s+",
            r"^you\s+should\s+",
            r"^make\s+sure\s+to\s+",
        ]

        result = content
        for pattern in FILLER_PATTERNS:
            result = re.sub(pattern, "", result, flags=re.IGNORECASE)

        # Capitalize first letter
        if result:
            result = result[0].upper() + result[1:]

        # Ensure max length
        words = result.split()
        if len(words) > 12:
            result = ' '.join(words[:12])

        return result

    def _try_llm_refinement(self, content: str, proposal: AgentProposal) -> Optional[str]:
        """
        OPTIONAL: Use Ollama for refinement if available.
        Returns None if LLM unavailable or fails.
        """
        try:
            import requests

            prompt = f"""Refine this rule to terse imperative form (max 10 words):

Rule: {content}
Evidence: {proposal.evidence[0] if proposal.evidence else ""}

Output ONLY the refined rule:"""

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.2:3b", "prompt": prompt, "stream": False},
                timeout=5
            )

            if response.status_code == 200:
                refined = response.json().get("response", "").strip()
                if 3 <= len(refined.split()) <= 12:
                    return refined

        except Exception:
            pass  # LLM unavailable - that's fine

        return None
```

---

## Integration with Phase 3

```python
# At session end (combined with user corrections)

def on_session_end(use_llm: bool = False):
    """
    Args:
        use_llm: If True AND Ollama available, use LLM for refinement.
                 Default is False - rule-based works well.
    """
    # User corrections (Phase 1-3)
    user_proposals = generate_user_proposals()  # From Phase 3

    # Agent learning (Phase 10)
    agent_engine = AgentLearningEngine()
    agent_proposals = agent_engine.generate_proposals(project=detect_project())

    # Refine agent proposals (rule-based PRIMARY, LLM optional)
    refiner = ProposalRefiner(use_llm=use_llm)
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

**In-Memory:** Agent observations buffered during session, written to global DB at end

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
✓ Rule-based refinement working (PRIMARY)
✓ Optional LLM refinement (if enabled)
✓ Integration with Phase 3 complete
✓ AI-native storage format validated
✓ System works 100% without Ollama
✓ Token budget: 0-500 tokens (LLM optional)
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
- Optional: `requests` (only if using LLM refinement)
- Optional: Ollama (only if LLM refinement enabled)

**LLM is OPTIONAL.** System works 100% without Ollama.

---

## Token Budget

- Observation collection: 0 tokens (regex + keywords)
- Pattern detection: 0 tokens (local analysis)
- Rule-based refinement: 0 tokens (local processing)
- Optional LLM refinement: ~100 tokens per proposal (if enabled)
- Total: 0-500 tokens per session (depending on LLM usage)

---

## Performance

- Observation recording: O(1) per turn
- Pattern detection: O(n) for n observations (n < 100 typical)
- Proposal generation: < 1 second
- LLM refinement: < 2 seconds (5 calls)
