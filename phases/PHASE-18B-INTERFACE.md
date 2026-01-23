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
