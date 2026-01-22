# PHASE 18: APPROVAL OPTIMIZATION

## Objective
Reduce approval fatigue through smart batching, auto-approval thresholds, and intelligent grouping. Make approval process fast and efficient.

---

## Implementation Location

**File:** `src/cerberus/memory/approval_optimizer.py`

---

## Phase Assignment

**Rollout:** Phase Epsilon (Post-Delta)

**Prerequisites:**
- ✅ Phase 4 complete (CLI approval interface working)
- ✅ Phase 3 complete (proposals generated with confidence scores)

**Why Phase Epsilon:**
- Basic approval must work first (Phase 4)
- Can measure actual approval fatigue empirically
- Enhancement layer on proven system

---

## Problem Statement

**Current Phase 4 behavior:**
- User sees ALL proposals (10+ per session)
- Each proposal requires individual decision
- High-confidence obvious proposals (0.95+) still require manual approval
- Similar proposals shown separately

**Result:** Approval fatigue, user skips all or blindly approves

**Desired behavior:**
- Auto-approve high-confidence proposals (0.9+)
- Batch similar proposals ("these 5 are all about spacing")
- Skip low-value proposals (< 0.5 confidence)
- Show summary, allow drill-down

---

## Data Structures

```python
@dataclass
class ApprovalBatch:
    """Grouped proposals for batch approval."""
    batch_id: str
    theme: str  # Human-readable grouping ("Code style", "Error handling")
    proposals: List[MemoryProposal]
    avg_confidence: float
    recommended_action: str  # "approve_all", "review", "skip"

@dataclass
class ApprovalStrategy:
    """Approval thresholds and behavior."""
    auto_approve_threshold: float = 0.9  # Auto-approve >= 0.9
    review_threshold: float = 0.6        # Show for review >= 0.6
    skip_threshold: float = 0.5          # Skip < 0.5
    batch_similar: bool = True           # Group similar proposals
    max_proposals_shown: int = 10        # Hard limit on proposals shown

@dataclass
class ApprovalResult:
    """Result of approval process."""
    auto_approved: List[str]  # Proposal IDs
    user_approved: List[str]
    user_rejected: List[str]
    skipped: List[str]
    stats: Dict[str, int]  # {"total": 15, "auto": 5, "approved": 7, "rejected": 2, "skipped": 1}
```

---

## Auto-Approval Algorithm

```python
def auto_approve_high_confidence(
    proposals: List[MemoryProposal],
    threshold: float = 0.9
) -> Tuple[List[str], List[MemoryProposal]]:
    """
    Auto-approve proposals above confidence threshold.

    Strategy:
    1. Filter proposals with confidence >= threshold
    2. Apply safety checks (no conflicts, valid scope)
    3. Auto-approve if safe
    4. Return auto-approved IDs + remaining proposals

    Args:
        proposals: All proposals
        threshold: Confidence threshold for auto-approval

    Returns:
        (auto_approved_ids, remaining_proposals)
    """
    auto_approved = []
    remaining = []

    for proposal in proposals:
        if proposal.confidence >= threshold:
            # Safety checks
            if _is_safe_to_auto_approve(proposal):
                auto_approved.append(proposal.id)
                print(f"✓ Auto-approved: {proposal.content[:60]}... (confidence: {proposal.confidence:.2f})")
            else:
                remaining.append(proposal)
        elif proposal.confidence >= 0.5:
            remaining.append(proposal)
        # else: skip (< 0.5 confidence)

    return auto_approved, remaining


def _is_safe_to_auto_approve(proposal: MemoryProposal) -> bool:
    """
    Safety checks for auto-approval.

    Reject if:
    - Conflicts with existing memory
    - Negation pattern ("never", "avoid")
    - Scope is too broad (universal high-impact)
    - Content is too long (> 200 chars)

    Returns:
        True if safe to auto-approve
    """
    content_lower = proposal.content.lower()

    # Check for negations (higher risk)
    negation_keywords = ["never", "avoid", "don't", "do not"]
    if any(kw in content_lower for kw in negation_keywords):
        return False  # Negations require review

    # Check content length
    if len(proposal.content) > 200:
        return False  # Long rules require review

    # Check for conflicts
    from cerberus.memory.storage import MemoryStorage
    storage = MemoryStorage()

    existing = storage.search_similar(proposal.content, threshold=0.8)
    if existing:
        return False  # Potential conflict, require review

    return True
```

---

## Batching Algorithm

```python
def batch_similar_proposals(proposals: List[MemoryProposal]) -> List[ApprovalBatch]:
    """
    Group similar proposals into batches.

    Strategy:
    1. Extract themes from proposals (keywords)
    2. Group by theme similarity (TF-IDF)
    3. Create batches with avg confidence
    4. Sort batches by confidence (high first)

    Returns:
        List of ApprovalBatch objects
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import AgglomerativeClustering
    import numpy as np

    if len(proposals) <= 3:
        # Too few to batch
        return [ApprovalBatch(
            batch_id="batch-single",
            theme="General",
            proposals=proposals,
            avg_confidence=np.mean([p.confidence for p in proposals]),
            recommended_action="review"
        )]

    # Extract content for clustering
    contents = [p.content for p in proposals]

    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(max_features=50)
    vectors = vectorizer.fit_transform(contents)

    # Hierarchical clustering
    clustering = AgglomerativeClustering(
        n_clusters=min(3, len(proposals) // 2),  # 2-3 proposals per batch
        metric='cosine',
        linkage='average'
    )
    labels = clustering.fit_predict(vectors.toarray())

    # Group proposals by cluster
    batches_dict = {}
    for i, label in enumerate(labels):
        if label not in batches_dict:
            batches_dict[label] = []
        batches_dict[label].append(proposals[i])

    # Create batches
    batches = []
    for label, batch_proposals in batches_dict.items():
        theme = _extract_theme(batch_proposals)
        avg_conf = np.mean([p.confidence for p in batch_proposals])

        # Recommended action
        if avg_conf >= 0.85:
            action = "approve_all"
        elif avg_conf >= 0.6:
            action = "review"
        else:
            action = "skip"

        batches.append(ApprovalBatch(
            batch_id=f"batch-{label}",
            theme=theme,
            proposals=batch_proposals,
            avg_confidence=avg_conf,
            recommended_action=action
        ))

    # Sort by confidence (high first)
    batches.sort(key=lambda b: b.avg_confidence, reverse=True)

    return batches


def _extract_theme(proposals: List[MemoryProposal]) -> str:
    """
    Extract common theme from proposals.

    Strategy:
    1. Count keywords across proposals
    2. Return most common keyword as theme

    Returns:
        Theme string (e.g., "Code style", "Error handling")
    """
    from collections import Counter

    # Predefined theme keywords
    THEME_KEYWORDS = {
        "style": "Code style",
        "format": "Code style",
        "spacing": "Code style",
        "indent": "Code style",
        "test": "Testing",
        "error": "Error handling",
        "exception": "Error handling",
        "validation": "Validation",
        "check": "Validation",
        "pattern": "Architecture",
        "structure": "Architecture",
        "doc": "Documentation",
        "comment": "Documentation",
    }

    # Count keywords
    keyword_counts = Counter()
    for proposal in proposals:
        content_lower = proposal.content.lower()
        for keyword in THEME_KEYWORDS.keys():
            if keyword in content_lower:
                keyword_counts[keyword] += 1

    # Most common keyword
    if keyword_counts:
        most_common_keyword = keyword_counts.most_common(1)[0][0]
        return THEME_KEYWORDS[most_common_keyword]

    return "General"
```

---

## Optimized Approval Interface

```python
def run_optimized_approval(
    proposals: List[MemoryProposal],
    strategy: Optional[ApprovalStrategy] = None
) -> ApprovalResult:
    """
    Optimized approval process with auto-approval and batching.

    Strategy:
    1. Auto-approve high-confidence proposals
    2. Skip low-confidence proposals
    3. Batch remaining proposals
    4. Show batches for user approval
    5. Allow drill-down to individual proposals

    Args:
        proposals: All proposals
        strategy: Approval strategy (uses defaults if None)

    Returns:
        ApprovalResult with all decisions
    """
    if strategy is None:
        strategy = ApprovalStrategy()

    result = ApprovalResult(
        auto_approved=[],
        user_approved=[],
        user_rejected=[],
        skipped=[],
        stats={}
    )

    # Step 1: Auto-approve high-confidence
    auto_ids, remaining = auto_approve_high_confidence(
        proposals,
        strategy.auto_approve_threshold
    )
    result.auto_approved = auto_ids

    print(f"\n{len(auto_ids)} high-confidence proposals auto-approved.\n")

    if not remaining:
        print("No proposals require review.")
        result.stats = {
            "total": len(proposals),
            "auto": len(auto_ids),
            "approved": 0,
            "rejected": 0,
            "skipped": 0
        }
        return result

    # Step 2: Skip low-confidence
    review_proposals = [p for p in remaining if p.confidence >= strategy.review_threshold]
    skipped_proposals = [p for p in remaining if p.confidence < strategy.review_threshold]

    result.skipped = [p.id for p in skipped_proposals]

    if skipped_proposals:
        print(f"{len(skipped_proposals)} low-confidence proposals skipped.\n")

    if not review_proposals:
        print("No proposals require review.")
        result.stats = {
            "total": len(proposals),
            "auto": len(auto_ids),
            "approved": 0,
            "rejected": 0,
            "skipped": len(skipped_proposals)
        }
        return result

    # Step 3: Batch similar proposals
    if strategy.batch_similar and len(review_proposals) > 3:
        batches = batch_similar_proposals(review_proposals)
        user_ids = _show_batched_approval(batches)
    else:
        # Fall back to individual approval
        user_ids = _show_individual_approval(review_proposals)

    result.user_approved = user_ids
    result.user_rejected = [
        p.id for p in review_proposals
        if p.id not in user_ids
    ]

    # Step 4: Compile stats
    result.stats = {
        "total": len(proposals),
        "auto": len(auto_ids),
        "approved": len(user_ids),
        "rejected": len(result.user_rejected),
        "skipped": len(skipped_proposals)
    }

    return result


def _show_batched_approval(batches: List[ApprovalBatch]) -> List[str]:
    """
    Show batches for user approval.

    Interface:
    - Show batch theme and proposal count
    - Allow batch actions (all, none, drill-down)
    - Drill-down shows individual proposals

    Returns:
        List of approved proposal IDs
    """
    approved_ids = []

    print(f"\n{len(batches)} batch(es) to review:\n")

    for i, batch in enumerate(batches, 1):
        print(f"{i}. {batch.theme} ({len(batch.proposals)} proposals, avg confidence: {batch.avg_confidence:.2f})")
        print(f"   Recommended: {batch.recommended_action}")

        # Show first proposal as preview
        preview = batch.proposals[0].content[:80]
        print(f"   Preview: {preview}...")

        # Batch actions
        action = input(f"\n   [a]pprove all, [s]kip all, [d]rill-down, [n]ext: ").strip().lower()

        if action == "a":
            # Approve all in batch
            approved_ids.extend([p.id for p in batch.proposals])
            print(f"   ✓ Approved all {len(batch.proposals)} proposals in batch.\n")

        elif action == "d":
            # Drill-down to individual proposals
            batch_approved = _show_individual_approval(batch.proposals)
            approved_ids.extend(batch_approved)

        elif action == "s":
            print(f"   Skipped batch.\n")

        # else: next batch

    return approved_ids


def _show_individual_approval(proposals: List[MemoryProposal]) -> List[str]:
    """
    Show individual proposals (fallback or drill-down).

    Same as Phase 4 CLI approval.
    """
    from cerberus.memory.approval_cli import ApprovalCLI
    cli = ApprovalCLI()
    return cli.run(proposals)
```

---

## Batch Mode (Non-Interactive)

```python
def batch_mode_approval(
    proposals: List[MemoryProposal],
    threshold: float = 0.85
) -> List[str]:
    """
    Non-interactive batch approval.

    Auto-approves proposals >= threshold, skips rest.

    Used for:
    - CI/CD pipelines
    - Automated workflows
    - High-volume sessions

    Args:
        proposals: All proposals
        threshold: Auto-approval threshold

    Returns:
        List of auto-approved proposal IDs
    """
    auto_approved = []

    for proposal in proposals:
        if proposal.confidence >= threshold and _is_safe_to_auto_approve(proposal):
            auto_approved.append(proposal.id)

    print(f"Batch mode: Auto-approved {len(auto_approved)}/{len(proposals)} proposals.")

    return auto_approved
```

---

## Approval History & Learning

```python
def learn_from_approval_history() -> ApprovalStrategy:
    """
    Adjust approval strategy based on user history.

    Strategy:
    1. Load past 50 approval decisions
    2. Calculate user's actual approval rate per confidence level
    3. Adjust auto-approval threshold

    Example:
    - If user approves 95% of 0.85+ proposals → lower threshold to 0.85
    - If user rejects 50% of 0.9+ proposals → raise threshold to 0.95

    Returns:
        Optimized ApprovalStrategy
    """
    from cerberus.memory.storage import MemoryStorage
    storage = MemoryStorage()

    # Load approval history
    history = storage.get_approval_history(limit=50)

    if not history:
        return ApprovalStrategy()  # Defaults

    # Analyze approval rate by confidence bucket
    buckets = {
        0.95: [],
        0.9: [],
        0.85: [],
        0.8: [],
    }

    for record in history:
        conf = record["confidence"]
        approved = record["approved"]

        for threshold in buckets.keys():
            if conf >= threshold:
                buckets[threshold].append(approved)

    # Find optimal threshold (95%+ approval rate)
    optimal_threshold = 0.9  # Default

    for threshold in sorted(buckets.keys(), reverse=True):
        decisions = buckets[threshold]
        if len(decisions) >= 10:  # Need at least 10 samples
            approval_rate = sum(decisions) / len(decisions)
            if approval_rate >= 0.95:
                optimal_threshold = threshold
                break

    return ApprovalStrategy(
        auto_approve_threshold=optimal_threshold,
        review_threshold=0.6,
        skip_threshold=0.5,
        batch_similar=True,
        max_proposals_shown=10
    )
```

---

## CLI Commands

```bash
# Optimized approval (default)
cerberus memory propose --interactive

# Batch mode (auto-approve high-confidence)
cerberus memory propose --batch --threshold 0.85

# Custom thresholds
cerberus memory propose --auto-threshold 0.9 --skip-threshold 0.5

# Disable batching
cerberus memory propose --no-batch

# Show approval history
cerberus memory approval-history --limit 50

# Learn optimal thresholds from history
cerberus memory optimize-thresholds
```

---

## Token Costs

**Approval optimization:**
- Auto-approval: 0 tokens (confidence check)
- Batching: 0 tokens (TF-IDF clustering)
- History learning: 0 tokens (database query)

**Total per session:** 0 tokens (optimization is free)

---

## Validation Gates

**Phase 18 complete when:**
- ✅ Auto-approval works (high-confidence proposals stored automatically)
- ✅ Batching works (similar proposals grouped)
- ✅ Skip low-confidence works (< 0.5 not shown)
- ✅ Batch mode works (non-interactive auto-approval)
- ✅ History learning works (thresholds adjust based on user)
- ✅ User satisfaction: "Approval is way faster now"
- ✅ 10+ sessions tested with optimization

**Metrics:**
- Approval time reduced from 60 seconds → 15 seconds
- Auto-approval rate: 30-40% of proposals
- User rejects < 5% of shown proposals (batching filters noise)

**Testing:**
- 20 test proposals with varying confidence
- Measure approval time before/after optimization
- Test batch mode (should approve high-confidence only)
- Test history learning (verify threshold adjustment)

---

## Dependencies

**Phase Dependencies:**
- Phase 4 (CLI Approval) - extends approval interface
- Phase 3 (Proposals) - uses confidence scores

**External Dependencies:**
- scikit-learn (already required for Phase 2 TF-IDF)

---

## Integration Points

**Phase 4 (Approval CLI) Extension:**
```python
# Old Phase 4 behavior
def run_approval(proposals: List[MemoryProposal]) -> List[str]:
    # Show all proposals, require individual decisions
    ...

# New Phase 18 behavior (backward compatible)
def run_approval(
    proposals: List[MemoryProposal],
    optimize: bool = True  # New parameter
) -> List[str]:
    if optimize:
        # Use optimized approval
        result = run_optimized_approval(proposals)
        return result.auto_approved + result.user_approved
    else:
        # Fall back to Phase 4 behavior
        return _original_approval(proposals)
```

**Phase 16 (Hooks) Integration:**
```bash
# Hooks use optimized approval by default
cerberus memory propose --interactive  # Uses Phase 18

# Disable optimization if needed
cerberus memory propose --no-optimize  # Falls back to Phase 4
```

---

## Implementation Checklist

- [ ] Write `src/cerberus/memory/approval_optimizer.py`
- [ ] Implement `auto_approve_high_confidence()` function
- [ ] Implement `batch_similar_proposals()` function
- [ ] Implement `run_optimized_approval()` function
- [ ] Implement `_show_batched_approval()` function
- [ ] Implement `batch_mode_approval()` function
- [ ] Implement `learn_from_approval_history()` function
- [ ] Extend Phase 4 CLI with optimization flag
- [ ] Add approval history tracking to Phase 5 (storage)
- [ ] Add CLI commands (`--batch`, `--auto-threshold`, `optimize-thresholds`)
- [ ] Write unit tests (auto-approval, batching, history learning)
- [ ] Write integration tests (full approval with optimization)
- [ ] Measure approval time before/after
- [ ] Test with 20+ proposals (verify batching)
- [ ] Test history learning (verify threshold adjustment)

---

**Last Updated:** 2026-01-22
**Version:** 1.0
**Status:** Specification complete, ready for implementation in Phase Epsilon
