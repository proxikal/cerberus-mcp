# PHASE 3: END-OF-SESSION PROPOSAL

## Objective
Summarize session corrections with LLM, propose memories for user approval.

---

## Implementation Location

**File:** `src/cerberus/memory/proposal_engine.py`

---

## Data Structures

```python
@dataclass
class MemoryProposal:
    id: str  # "prop-001"
    category: str  # "preference", "rule", "correction"
    scope: str  # "universal", "language:go", "project:cerberus"
    content: str  # The actual memory text
    rationale: str  # Why this should be stored
    source_variants: List[str]  # Original corrections
    confidence: float
    priority: int  # 1=critical, 2=high, 3=medium

@dataclass
class SessionSummary:
    session_id: str
    timestamp: datetime
    project: Optional[str]
    proposals: List[MemoryProposal]
    total_corrections: int
    total_proposed: int
```

---

## Proposal Generation

```python
class ProposalEngine:
    def __init__(self, llm_provider: str = "ollama"):
        self.llm = LLMClient(llm_provider)
        self.max_proposals = 5  # Don't overwhelm user

    def generate_proposals(
        self,
        clusters: List[CorrectionCluster],
        project: Optional[str] = None
    ) -> SessionSummary:
        """
        Generate memory proposals from correction clusters.
        """
        if not clusters:
            return SessionSummary(
                session_id=self._gen_session_id(),
                timestamp=datetime.now(),
                project=project,
                proposals=[],
                total_corrections=0,
                total_proposed=0
            )

        # Sort clusters by priority (frequency * confidence)
        sorted_clusters = sorted(
            clusters,
            key=lambda c: c.frequency * c.confidence,
            reverse=True
        )

        # Take top N clusters
        top_clusters = sorted_clusters[:self.max_proposals]

        # Generate proposals using LLM
        proposals = []
        for i, cluster in enumerate(top_clusters):
            proposal = self._create_proposal(cluster, project, priority=i+1)
            if proposal:
                proposals.append(proposal)

        return SessionSummary(
            session_id=self._gen_session_id(),
            timestamp=datetime.now(),
            project=project,
            proposals=proposals,
            total_corrections=sum(c.frequency for c in clusters),
            total_proposed=len(proposals)
        )

    def _create_proposal(
        self,
        cluster: CorrectionCluster,
        project: Optional[str],
        priority: int
    ) -> Optional[MemoryProposal]:
        """
        Use LLM to create structured proposal from cluster.
        """
        prompt = f"""Analyze this correction and create a memory rule:

Correction variants:
{chr(10).join(f"- {v}" for v in cluster.variants)}

Type: {cluster.correction_type}
Frequency: {cluster.frequency}

Output JSON:
{{
  "category": "preference|rule|correction",
  "scope": "universal|language:X|project:Y",
  "content": "imperative rule (max 15 words)",
  "rationale": "why store this (max 20 words)"
}}

Rules:
- "universal" = applies to ALL projects (e.g., token efficiency, file size limits)
- "language:X" = language-specific (e.g., Go panic handling)
- "project:Y" = project-specific (e.g., XCalibr UI patterns)
- content = actionable, imperative mood
- rationale = value proposition"""

        try:
            response = self.llm.generate(prompt, json_mode=True)
            data = json.loads(response)

            # Validate scope
            scope = data["scope"]
            if scope.startswith("project:") and not project:
                # Correction about non-project context → universal
                scope = "universal"
            elif scope.startswith("project:") and project:
                # Use detected project name
                scope = f"project:{project}"

            return MemoryProposal(
                id=f"prop-{uuid.uuid4().hex[:8]}",
                category=data["category"],
                scope=scope,
                content=data["content"],
                rationale=data["rationale"],
                source_variants=cluster.variants,
                confidence=cluster.confidence,
                priority=priority
            )
        except Exception as e:
            # Fallback: Create proposal from canonical text
            return MemoryProposal(
                id=f"prop-{uuid.uuid4().hex[:8]}",
                category=cluster.correction_type,
                scope=self._infer_scope(cluster, project),
                content=cluster.canonical_text,
                rationale="User corrected this behavior multiple times",
                source_variants=cluster.variants,
                confidence=cluster.confidence,
                priority=priority
            )

    def _infer_scope(self, cluster: CorrectionCluster, project: Optional[str]) -> str:
        """Fallback scope inference without LLM."""
        text_lower = cluster.canonical_text.lower()

        # Check for language keywords
        lang_keywords = {
            "go": ["panic", "goroutine", "defer"],
            "python": ["except", "async", "import"],
            "typescript": ["async", "promise", "interface"],
            "rust": ["unsafe", "unwrap", "borrow"]
        }

        for lang, keywords in lang_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return f"language:{lang}"

        # Check for universal patterns
        universal_keywords = ["token", "file size", "line limit", "concise", "short"]
        if any(kw in text_lower for kw in universal_keywords):
            return "universal"

        # Default to project if available
        return f"project:{project}" if project else "universal"

    def _gen_session_id(self) -> str:
        return datetime.now().strftime("%Y%m%d-%H%M%S")
```

---

## User Approval Interface

```python
class ApprovalInterface:
    """
    Present proposals to user and collect approvals.
    """

    def present_proposals(self, summary: SessionSummary) -> List[str]:
        """
        Show proposals to user, return list of approved IDs.
        """
        if not summary.proposals:
            return []

        print(f"\n{'='*60}")
        print(f"SESSION MEMORY PROPOSALS")
        print(f"{'='*60}")
        print(f"Session: {summary.session_id}")
        print(f"Detected {summary.total_corrections} corrections")
        print(f"Proposing {summary.total_proposed} memories\n")

        for i, prop in enumerate(summary.proposals, 1):
            self._display_proposal(i, prop)

        # Collect approvals
        approved = []
        response = input("\nApprove: (1,2,3 or 'all' or 'none'): ").strip().lower()

        if response == "all":
            approved = [p.id for p in summary.proposals]
        elif response == "none":
            approved = []
        else:
            # Parse comma-separated indices
            try:
                indices = [int(x.strip()) for x in response.split(",")]
                approved = [
                    summary.proposals[i-1].id
                    for i in indices
                    if 0 < i <= len(summary.proposals)
                ]
            except:
                print("Invalid input, skipping all.")

        return approved

    def _display_proposal(self, num: int, prop: MemoryProposal):
        """Display single proposal."""
        priority_icons = {1: "🔴", 2: "🟠", 3: "🟡"}
        icon = priority_icons.get(prop.priority, "⚪")

        print(f"{icon} [{num}] {prop.category.upper()} ({prop.scope})")
        print(f"    Rule: {prop.content}")
        print(f"    Why: {prop.rationale}")
        print(f"    Source: {prop.source_variants[0]}")
        if len(prop.source_variants) > 1:
            print(f"    (+{len(prop.source_variants)-1} similar)")
        print()
```

---

## Storage Integration

```python
class ProposalStorage:
    """
    Store approved proposals to appropriate memory locations.
    """

    def __init__(self, memory_store: MemoryStore):
        self.store = memory_store
        self.profile_mgr = ProfileManager(memory_store)
        self.decision_mgr = DecisionManager(memory_store)
        self.correction_mgr = CorrectionManager(memory_store)

    def store_approved(
        self,
        proposals: List[MemoryProposal],
        approved_ids: List[str]
    ):
        """
        Store approved proposals to correct memory layer.
        """
        for prop in proposals:
            if prop.id not in approved_ids:
                continue

            if prop.scope == "universal":
                self._store_universal(prop)
            elif prop.scope.startswith("language:"):
                self._store_language(prop)
            elif prop.scope.startswith("project:"):
                self._store_project(prop)

    def _store_universal(self, prop: MemoryProposal):
        """Store to global preferences."""
        if prop.category == "correction":
            self.correction_mgr.add_correction(
                pattern=prop.content,
                note=prop.rationale,
                frequency=1
            )
        else:
            # Add to profile general
            profile = self.profile_mgr.load_profile()
            if not profile.general:
                profile.general = []
            profile.general.append(prop.content)
            self.profile_mgr.save_profile(profile)

    def _store_language(self, prop: MemoryProposal):
        """Store to language-specific preferences."""
        lang = prop.scope.split(":")[1]
        profile = self.profile_mgr.load_profile()
        if not profile.languages:
            profile.languages = {}
        if lang not in profile.languages:
            profile.languages[lang] = []
        profile.languages[lang].append(prop.content)
        self.profile_mgr.save_profile(profile)

    def _store_project(self, prop: MemoryProposal):
        """Store to project-specific decisions."""
        project = prop.scope.split(":")[1]
        self.decision_mgr.add_decision(
            project=project,
            decision=prop.content,
            rationale=prop.rationale
        )
```

---

## Session End Hook

```python
def on_session_end():
    """
    Triggered when session ends (user exits, inactivity timeout, or explicit command).
    """
    # Phase 1: Get raw candidates
    session_analyzer = get_session_analyzer()
    raw_candidates = session_analyzer.candidates

    if not raw_candidates:
        return  # No corrections this session

    # Phase 2: Cluster and deduplicate
    semantic_analyzer = SemanticAnalyzer()
    analyzed = semantic_analyzer.cluster_corrections(raw_candidates)

    if not analyzed.clusters:
        return  # Nothing to propose

    # Phase 3: Generate proposals
    proposal_engine = ProposalEngine()
    summary = proposal_engine.generate_proposals(
        analyzed.clusters,
        project=detect_project_name()
    )

    # Present to user
    approval_ui = ApprovalInterface()
    approved_ids = approval_ui.present_proposals(summary)

    if not approved_ids:
        print("No memories stored.")
        return

    # Store approved
    storage = ProposalStorage(get_memory_store())
    storage.store_approved(summary.proposals, approved_ids)

    print(f"\n✓ Stored {len(approved_ids)} memories")
```

---

## Exit Criteria

```
✓ ProposalEngine class implemented
✓ LLM-based proposal generation functional
✓ Fallback proposal generation (no LLM) functional
✓ ApprovalInterface working (CLI version)
✓ ProposalStorage integration with existing memory layers
✓ Session end hook implemented
✓ Tests: 5 scenarios with expected proposals
```

---

## Test Scenarios

```python
# Scenario 1: Universal rule
clusters = [
    CorrectionCluster(
        canonical="Keep summaries concise",
        variants=["keep it short", "be terse"],
        correction_type="style",
        frequency=3,
        confidence=0.9
    )
]
→ expect: Proposal(scope="universal", category="preference")

# Scenario 2: Language-specific
clusters = [
    CorrectionCluster(
        canonical="Never use panic in production Go code",
        variants=["don't panic", "avoid panic()"],
        correction_type="rule",
        frequency=2,
        confidence=0.95
    )
]
→ expect: Proposal(scope="language:go", category="rule")

# Scenario 3: Project-specific
clusters = [
    CorrectionCluster(
        canonical="Use PortalTabs for all portal pages",
        variants=["add tabs", "use portal tabs"],
        correction_type="rule",
        frequency=2,
        confidence=0.8
    )
]
project = "xcalibr"
→ expect: Proposal(scope="project:xcalibr", category="rule")
```

---

## Dependencies

```bash
pip install ollama-python  # Or anthropic SDK for Claude API
```

---

## Token Budget

- Proposal generation: ~150 tokens per cluster (5 clusters max = 750 tokens)
- User approval: 0 tokens (CLI interaction)
- Total per session: 750-1000 tokens

---

## Performance

- LLM calls: 5 calls per session (one per proposal)
- Total time: < 5 seconds for typical session
- User interaction: 10-30 seconds approval time
