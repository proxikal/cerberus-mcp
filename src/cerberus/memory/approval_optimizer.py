"""
Phase 18: Approval Optimization (A/B)

Reduce approval fatigue through smart batching, auto-approval thresholds, and
intelligent grouping. Make approval process fast and efficient.

Phase 18A: Algorithms (auto-approval, batching, theme extraction)
Phase 18B: Interface (optimized approval, batch mode, history learning)

Token cost: 0 tokens (all local TF-IDF and rule-based)
"""

import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
from collections import Counter
import numpy as np

# TF-IDF for batching
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering

from cerberus.memory.proposal_engine import MemoryProposal


# ============================================================================
# Data Structures
# ============================================================================


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
    auto_approved: List[str] = field(default_factory=list)  # Proposal IDs
    user_approved: List[str] = field(default_factory=list)
    user_rejected: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)


# ============================================================================
# Phase 18A: Auto-Approval Algorithm
# ============================================================================


def auto_approve_high_confidence(
    proposals: List[MemoryProposal],
    threshold: float = 0.9,
    skip_threshold: float = 0.5
) -> Tuple[List[str], List[MemoryProposal], List[MemoryProposal]]:
    """
    Auto-approve proposals above confidence threshold.

    Strategy:
    1. Filter proposals with confidence >= threshold
    2. Apply safety checks (no conflicts, valid scope)
    3. Auto-approve if safe
    4. Return auto-approved IDs + remaining + skipped proposals

    Args:
        proposals: All proposals
        threshold: Confidence threshold for auto-approval
        skip_threshold: Confidence threshold below which proposals are skipped

    Returns:
        (auto_approved_ids, remaining_proposals, skipped_proposals)
    """
    auto_approved = []
    remaining = []
    skipped = []

    for proposal in proposals:
        if proposal.confidence >= threshold:
            # Safety checks
            if _is_safe_to_auto_approve(proposal):
                auto_approved.append(proposal.id)
                print(f"✓ Auto-approved: {proposal.content[:60]}... (confidence: {proposal.confidence:.2f})")
            else:
                remaining.append(proposal)
        elif proposal.confidence >= skip_threshold:
            remaining.append(proposal)
        else:
            # Skip low-confidence proposals
            skipped.append(proposal)

    return auto_approved, remaining, skipped


def _is_safe_to_auto_approve(proposal: MemoryProposal) -> bool:
    """
    Safety checks for auto-approval.

    Reject if:
    - Conflicts with existing memory (handled separately)
    - Negation pattern ("never", "avoid") - higher risk
    - Scope is too broad (universal high-impact) - not implemented yet
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

    # Note: Conflict checking would require access to storage
    # For now, we rely on Phase 19 conflict resolution
    # If Phase 19 is available, integrate here

    return True


# ============================================================================
# Phase 18A: Batching Algorithm
# ============================================================================


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
    if len(proposals) <= 3:
        # Too few to batch
        return [ApprovalBatch(
            batch_id="batch-single",
            theme="General",
            proposals=proposals,
            avg_confidence=float(np.mean([p.confidence for p in proposals])),
            recommended_action="review"
        )]

    # Extract content for clustering
    contents = [p.content for p in proposals]

    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(max_features=50)
    vectors = vectorizer.fit_transform(contents)

    # Hierarchical clustering
    n_clusters = min(3, len(proposals) // 2)  # 2-3 proposals per batch
    clustering = AgglomerativeClustering(
        n_clusters=n_clusters,
        metric='cosine',
        linkage='average'
    )
    labels = clustering.fit_predict(vectors.toarray())

    # Group proposals by cluster
    batches_dict: Dict[int, List[MemoryProposal]] = {}
    for i, label in enumerate(labels):
        if label not in batches_dict:
            batches_dict[label] = []
        batches_dict[label].append(proposals[i])

    # Create batches
    batches = []
    for label, batch_proposals in batches_dict.items():
        theme = _extract_theme(batch_proposals)
        avg_conf = float(np.mean([p.confidence for p in batch_proposals]))

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


# ============================================================================
# Phase 18B: Optimized Approval Interface
# ============================================================================


def run_optimized_approval(
    proposals: List[MemoryProposal],
    strategy: Optional[ApprovalStrategy] = None,
    interactive: bool = True
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
        interactive: If False, use batch mode (auto-approve only)

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

    if not proposals:
        result.stats = {"total": 0, "auto": 0, "approved": 0, "rejected": 0, "skipped": 0}
        return result

    # Step 1: Auto-approve high-confidence
    auto_ids, remaining, auto_skipped = auto_approve_high_confidence(
        proposals,
        strategy.auto_approve_threshold,
        strategy.skip_threshold
    )
    result.auto_approved = auto_ids
    result.skipped = [p.id for p in auto_skipped]

    if auto_ids:
        print(f"\n{len(auto_ids)} high-confidence proposals auto-approved.\n")

    if auto_skipped:
        print(f"{len(auto_skipped)} low-confidence proposals skipped (< {strategy.skip_threshold}).\n")

    if not remaining:
        print("No proposals require review.")
        result.stats = {
            "total": len(proposals),
            "auto": len(auto_ids),
            "approved": 0,
            "rejected": 0,
            "skipped": len(auto_skipped)
        }
        return result

    # Non-interactive mode: skip remaining
    if not interactive:
        result.skipped.extend([p.id for p in remaining])
        result.stats = {
            "total": len(proposals),
            "auto": len(auto_ids),
            "approved": 0,
            "rejected": 0,
            "skipped": len(result.skipped)
        }
        print(f"Batch mode: {len(remaining)} additional proposals skipped (below threshold).")
        return result

    # Step 2: Filter by review threshold
    review_proposals = [p for p in remaining if p.confidence >= strategy.review_threshold]
    additional_skipped = [p for p in remaining if p.confidence < strategy.review_threshold]

    result.skipped.extend([p.id for p in additional_skipped])

    if additional_skipped:
        print(f"{len(additional_skipped)} additional low-confidence proposals skipped.\n")

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
        "skipped": len(result.skipped)
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

    Same as Phase 4 CLI approval (without optimization to avoid recursion).
    """
    from cerberus.memory.approval_cli import ApprovalCLI
    cli = ApprovalCLI()
    result = cli.run(proposals, optimize=False)  # Disable optimization to prevent recursion
    return result.approved_ids


# ============================================================================
# Phase 18B: Batch Mode (Non-Interactive)
# ============================================================================


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


# ============================================================================
# Phase 18B: Approval History & Learning
# ============================================================================


def learn_from_approval_history(
    db_path: Optional[Path] = None
) -> ApprovalStrategy:
    """
    Adjust approval strategy based on user history.

    Strategy:
    1. Load past 50 approval decisions
    2. Calculate user's actual approval rate per confidence level
    3. Adjust auto-approval threshold

    Example:
    - If user approves 95% of 0.85+ proposals → lower threshold to 0.85
    - If user rejects 50% of 0.9+ proposals → raise threshold to 0.95

    Args:
        db_path: Path to memory.db (default: ~/.cerberus/memory.db)

    Returns:
        Optimized ApprovalStrategy
    """
    if db_path is None:
        db_path = Path.home() / ".cerberus" / "memory.db"

    if not db_path.exists():
        return ApprovalStrategy()  # Defaults

    # TODO: Phase 19 integration - load approval history from storage
    # For now, return default strategy
    # Future implementation would query approval_history table

    return ApprovalStrategy()


# ============================================================================
# Helper Functions
# ============================================================================


def get_all_approved_ids(result: ApprovalResult) -> List[str]:
    """Get all approved proposal IDs (auto + user)."""
    return result.auto_approved + result.user_approved


def print_approval_summary(result: ApprovalResult) -> None:
    """Print summary of approval results."""
    print("\n" + "=" * 60)
    print("APPROVAL SUMMARY")
    print("=" * 60)
    print(f"Total proposals:     {result.stats.get('total', 0)}")
    print(f"Auto-approved:       {result.stats.get('auto', 0)}")
    print(f"User approved:       {result.stats.get('approved', 0)}")
    print(f"User rejected:       {result.stats.get('rejected', 0)}")
    print(f"Skipped:             {result.stats.get('skipped', 0)}")
    print("=" * 60)

    total_approved = result.stats.get('auto', 0) + result.stats.get('approved', 0)
    print(f"Total approved: {total_approved}/{result.stats.get('total', 0)}")
    print()
