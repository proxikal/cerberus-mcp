# PHASE 3: SESSION PROPOSAL

**Rollout Phase:** Alpha (Weeks 1-2)
**Status:** Implement after Phase 2

## Prerequisites

- ✅ Phase 1 complete (correction detection)
- ✅ Phase 2 complete (semantic clustering)

---

## Objective
Generate memory proposals from session corrections using template-based rules.

**LLM Status:** OPTIONAL enhancement only. System works 100% without Ollama.

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
    """
    Generate memory proposals from correction clusters.

    PRIMARY: Template-based rules (no dependencies, instant)
    OPTIONAL: LLM enhancement (if Ollama available AND enabled)
    """

    def __init__(self, use_llm: bool = False):
        """
        Args:
            use_llm: If True AND Ollama is available, use LLM for refinement.
                     Default is False - template-based works well.
        """
        self.use_llm = use_llm
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

        # Generate proposals using templates (PRIMARY)
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
        Create proposal using template-based rules.
        LLM only used for optional refinement if enabled.
        """
        # PRIMARY: Template-based proposal generation
        scope = self._infer_scope(cluster, project)
        category = self._infer_category(cluster)
        content = self._generate_content(cluster)
        rationale = self._generate_rationale(cluster)

        # OPTIONAL: LLM refinement
        if self.use_llm:
            refined = self._try_llm_refinement(content, cluster)
            if refined:
                content = refined

        return MemoryProposal(
            id=f"prop-{uuid.uuid4().hex[:8]}",
            category=category,
            scope=scope,
            content=content,
            rationale=rationale,
            source_variants=cluster.variants,
            confidence=cluster.confidence,
            priority=priority
        )

    def _infer_scope(self, cluster: CorrectionCluster, project: Optional[str]) -> str:
        """
        Infer scope from correction content.

        Hierarchy: project > language > universal
        """
        text_lower = cluster.canonical_text.lower()

        # Language detection keywords
        LANG_KEYWORDS = {
            "go": ["panic", "goroutine", "defer", "chan", "go func", "go mod"],
            "python": ["except", "async def", "import", "def ", "__init__", "pytest"],
            "typescript": ["interface", "type ", "async", "promise", "tsx", "tsx"],
            "javascript": ["const ", "let ", "function", "=>", "async"],
            "rust": ["unsafe", "unwrap", "borrow", "impl", "fn ", "mut"]
        }

        # Check for language-specific content
        for lang, keywords in LANG_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return f"language:{lang}"

        # Check for universal patterns (applies everywhere)
        UNIVERSAL_KEYWORDS = [
            "token", "file size", "line limit", "concise", "short",
            "verbose", "summary", "terse", "split", "200 lines",
            "ai", "agent", "llm", "context"
        ]
        if any(kw in text_lower for kw in UNIVERSAL_KEYWORDS):
            return "universal"

        # Project-specific if we have a project context
        if project:
            # Check if correction seems project-specific
            PROJECT_INDICATORS = ["this project", "here", "our", "we use", "portal", "component"]
            if any(ind in text_lower for ind in PROJECT_INDICATORS):
                return f"project:{project}"

        # Default to universal (safest)
        return "universal"

    def _infer_category(self, cluster: CorrectionCluster) -> str:
        """
        Infer category from correction type and content.
        """
        text_lower = cluster.canonical_text.lower()

        # Correction type mapping
        TYPE_MAP = {
            "behavior": "rule",
            "style": "preference",
            "rule": "rule",
            "preference": "preference"
        }

        base_category = TYPE_MAP.get(cluster.correction_type, "preference")

        # Override based on content
        if any(kw in text_lower for kw in ["never", "don't", "avoid", "stop"]):
            return "correction"  # Anti-pattern
        if any(kw in text_lower for kw in ["always", "must", "limit", "max"]):
            return "rule"  # Hard rule
        if any(kw in text_lower for kw in ["prefer", "like", "use", "keep"]):
            return "preference"  # Soft preference

        return base_category

    def _generate_content(self, cluster: CorrectionCluster) -> str:
        """
        Generate content from canonical text using templates.

        Transforms user correction into imperative form.
        """
        canonical = cluster.canonical_text.strip()
        words = canonical.lower().split()

        # Already in good form?
        GOOD_STARTERS = {'use', 'keep', 'avoid', 'never', 'always', 'prefer',
                         'write', 'split', 'plan', 'test', 'log', 'limit'}
        if words and words[0] in GOOD_STARTERS:
            return canonical

        # Transform common patterns
        TRANSFORMATIONS = [
            # "don't X" → "Avoid X"
            (r"^don'?t\s+", "Avoid "),
            # "stop X" → "Avoid X"
            (r"^stop\s+", "Avoid "),
            # "be X" → "Keep output X"
            (r"^be\s+(concise|terse|short|brief)", r"Keep output \1"),
            # "X is bad" → "Avoid X"
            (r"(.+)\s+is\s+bad", r"Avoid \1"),
            # "X is good" → "Prefer X"
            (r"(.+)\s+is\s+good", r"Prefer \1"),
            # "I want X" → "X"
            (r"^i\s+want\s+", ""),
            # "you should X" → "X"
            (r"^you\s+should\s+", ""),
        ]

        import re
        result = canonical
        for pattern, replacement in TRANSFORMATIONS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        # Capitalize first letter
        if result:
            result = result[0].upper() + result[1:]

        # Ensure reasonable length (max 20 words)
        words = result.split()
        if len(words) > 20:
            result = ' '.join(words[:20]) + '...'

        return result

    def _generate_rationale(self, cluster: CorrectionCluster) -> str:
        """
        Generate rationale from cluster data.
        """
        freq = cluster.frequency
        conf = cluster.confidence

        if freq >= 3:
            return f"User corrected this {freq} times (high priority)"
        elif freq == 2:
            return "User corrected this twice"
        elif conf >= 0.9:
            return "Explicit correction with high confidence"
        else:
            return "User indicated preference"

    def _try_llm_refinement(self, content: str, cluster: CorrectionCluster) -> Optional[str]:
        """
        OPTIONAL: Use Ollama for content refinement if available.
        Returns None if LLM unavailable or fails.
        """
        try:
            import requests

            prompt = f"""Refine this rule to terse imperative form (max 10 words):

Rule: {content}
Original: {cluster.variants[0] if cluster.variants else content}

Output ONLY the refined rule:"""

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.2:3b", "prompt": prompt, "stream": False},
                timeout=5
            )

            if response.status_code == 200:
                refined = response.json().get("response", "").strip()
                if 3 <= len(refined.split()) <= 15:
                    return refined

        except Exception:
            pass  # LLM unavailable - that's fine

        return None

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
✓ Template-based proposal generation functional (PRIMARY)
✓ Optional LLM refinement (if enabled)
✓ Scope inference working (universal/language/project)
✓ Category inference working (preference/rule/correction)
✓ Content transformation to imperative form
✓ ApprovalInterface working (CLI version)
✓ ProposalStorage integration with existing memory layers
✓ Session end hook implemented
✓ Tests: 5 scenarios with expected proposals
✓ System works 100% without Ollama
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
# No required dependencies beyond standard library
# pip install requests  # Only if using optional LLM refinement
```

**LLM is OPTIONAL.** System works 100% without Ollama.

---

## Token Budget

- Proposal generation (templates): 0 tokens (local processing)
- Optional LLM refinement: ~100 tokens per proposal (if enabled)
- User approval: 0 tokens (CLI interaction)
- Total per session: 0-500 tokens (depending on LLM usage)

---

## Performance

- Template-based: < 50ms (no network calls)
- Optional LLM: + ~500ms per proposal (if enabled)
- User interaction: 10-30 seconds approval time
