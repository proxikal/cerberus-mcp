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

