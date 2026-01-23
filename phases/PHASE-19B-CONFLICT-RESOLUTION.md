## Automatic Resolution Algorithms

### Redundancy Resolution

```python
def resolve_redundancy(conflict: MemoryConflict) -> ConflictResolution:
    """
    Automatically resolve redundancy conflict.

    Strategy: Keep newer, delete older.
    """
    mem_a = conflict.memory_a
    mem_b = conflict.memory_b

    # Keep newer
    if mem_a.created_at > mem_b.created_at:
        keep = mem_a
        delete = mem_b
    else:
        keep = mem_b
        delete = mem_a

    return ConflictResolution(
        conflict_id=conflict.conflict_id,
        resolution_type="keep_newer",
        merged_content=None,
        rationale=f"Kept newer memory ({keep.id}), deleted redundant older memory ({delete.id})"
    )
```

### Obsolescence Resolution

```python
def resolve_obsolescence(conflict: MemoryConflict) -> ConflictResolution:
    """
    Automatically resolve obsolescence conflict.

    Strategy: Delete older, keep newer.
    """
    mem_a = conflict.memory_a
    mem_b = conflict.memory_b

    # Keep newer (explicit supersession)
    if mem_a.created_at > mem_b.created_at:
        keep = mem_a
        delete = mem_b
    else:
        keep = mem_b
        delete = mem_a

    return ConflictResolution(
        conflict_id=conflict.conflict_id,
        resolution_type="keep_newer",
        merged_content=None,
        rationale=f"Newer memory ({keep.id}) supersedes older ({delete.id})"
    )
```

### Contradiction Resolution (Recency-Based)

```python
def _can_auto_resolve_contradiction(
    mem_a: RetrievedMemory,
    mem_b: RetrievedMemory
) -> bool:
    """
    Check if contradiction can be auto-resolved.

    Auto-resolvable if:
    - One memory is significantly newer (> 30 days difference)
    - One memory has much higher confidence (> 0.2 difference)

    Otherwise: Requires user decision
    """
    age_diff = abs((mem_a.created_at - mem_b.created_at).days)
    conf_diff = abs(mem_a.confidence - mem_b.confidence)

    if age_diff > 30:
        return True  # Newer wins

    if conf_diff > 0.2:
        return True  # Higher confidence wins

    return False  # Ambiguous, ask user


def _recommend_contradiction_resolution(
    mem_a: RetrievedMemory,
    mem_b: RetrievedMemory
) -> str:
    """
    Recommend resolution for contradiction.

    Returns:
        "keep_a", "keep_b", or "ask_user"
    """
    age_diff_days = (mem_a.created_at - mem_b.created_at).days

    # Newer memory wins (if significant age difference)
    if age_diff_days > 30:
        return "keep_a"
    elif age_diff_days < -30:
        return "keep_b"

    # Higher confidence wins (if significant confidence difference)
    conf_diff = mem_a.confidence - mem_b.confidence
    if conf_diff > 0.2:
        return "keep_a"
    elif conf_diff < -0.2:
        return "keep_b"

    # Ambiguous
    return "ask_user"


def resolve_contradiction_auto(conflict: MemoryConflict) -> Optional[ConflictResolution]:
    """
    Automatically resolve contradiction if possible.

    Returns:
        ConflictResolution if auto-resolvable, None otherwise
    """
    if not conflict.auto_resolvable:
        return None

    recommendation = conflict.recommended_resolution

    if recommendation == "keep_a":
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            resolution_type="keep_a",
            merged_content=None,
            rationale=f"Kept memory {conflict.memory_a.id} (newer/higher confidence)"
        )
    elif recommendation == "keep_b":
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            resolution_type="keep_b",
            merged_content=None,
            rationale=f"Kept memory {conflict.memory_b.id} (newer/higher confidence)"
        )

    return None
```

---

## User-Mediated Resolution

```python
def resolve_conflict_interactive(conflict: MemoryConflict) -> ConflictResolution:
    """
    Ask user to resolve conflict.

    Shows:
    - Both memories
    - Conflict type
    - Recommended resolution
    - Options: keep A, keep B, keep both, merge, delete both
    """
    print(f"\n{'='*70}")
    print(f"CONFLICT DETECTED: {conflict.conflict_type.value}")
    print(f"Severity: {conflict.severity}")
    print(f"{'='*70}\n")

    print(f"Memory A ({conflict.memory_a.id}):")
    print(f"  Content: {conflict.memory_a.content}")
    print(f"  Scope: {conflict.memory_a.scope}")
    print(f"  Created: {conflict.memory_a.created_at.strftime('%Y-%m-%d')}")
    print(f"  Confidence: {conflict.memory_a.confidence:.2f}\n")

    print(f"Memory B ({conflict.memory_b.id}):")
    print(f"  Content: {conflict.memory_b.content}")
    print(f"  Scope: {conflict.memory_b.scope}")
    print(f"  Created: {conflict.memory_b.created_at.strftime('%Y-%m-%d')}")
    print(f"  Confidence: {conflict.memory_b.confidence:.2f}\n")

    print(f"Recommended: {conflict.recommended_resolution}\n")

    # Get user decision
    choice = input("Resolution: [a] keep A, [b] keep B, [B]oth, [m]erge, [d]elete both: ").strip().lower()

    if choice == "a":
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            resolution_type="keep_a",
            merged_content=None,
            rationale="User chose to keep memory A"
        )
    elif choice == "b":
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            resolution_type="keep_b",
            merged_content=None,
            rationale="User chose to keep memory B"
        )
    elif choice == "B":  # Capital B for "both"
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            resolution_type="keep_both",
            merged_content=None,
            rationale="User chose to keep both memories"
        )
    elif choice == "m":
        # Merge: ask user for merged content
        print("\nEnter merged content:")
        merged = input("> ").strip()

        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            resolution_type="merge",
            merged_content=merged,
            rationale="User provided merged content"
        )
    elif choice == "d":
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            resolution_type="delete_both",
            merged_content=None,
            rationale="User chose to delete both memories"
        )
    else:
        # Default: recommended resolution
        print(f"Invalid choice. Using recommended: {conflict.recommended_resolution}")
        return resolve_contradiction_auto(conflict) or ConflictResolution(
            conflict_id=conflict.conflict_id,
            resolution_type="ask_user",
            merged_content=None,
            rationale="Deferred resolution"
        )
```

---

## Resolution Execution

```python
def execute_resolution(resolution: ConflictResolution, conflict: MemoryConflict) -> None:
    """
    Execute conflict resolution action.

    Modifies storage based on resolution decision.
    """
    from cerberus.memory.storage import MemoryStorage
    storage = MemoryStorage()

    if resolution.resolution_type == "keep_a":
        # Delete memory B
        storage.delete_memory(conflict.memory_b.id)
        print(f"✓ Deleted memory {conflict.memory_b.id}")

    elif resolution.resolution_type == "keep_b":
        # Delete memory A
        storage.delete_memory(conflict.memory_a.id)
        print(f"✓ Deleted memory {conflict.memory_a.id}")

    elif resolution.resolution_type == "keep_both":
        # No action (both remain)
        print(f"✓ Kept both memories")

    elif resolution.resolution_type == "merge":
        # Delete both, create merged memory
        storage.delete_memory(conflict.memory_a.id)
        storage.delete_memory(conflict.memory_b.id)

        # Create merged memory
        merged_memory = MemoryProposal(
            id=f"merged-{uuid.uuid4().hex[:8]}",
            category=conflict.memory_a.category,
            scope=conflict.memory_a.scope,
            content=resolution.merged_content,
            confidence=max(conflict.memory_a.confidence, conflict.memory_b.confidence),
            priority=max(conflict.memory_a.priority, conflict.memory_b.priority)
        )

        storage.store(merged_memory)
        print(f"✓ Created merged memory: {merged_memory.id}")

    elif resolution.resolution_type == "delete_both":
        # Delete both
        storage.delete_memory(conflict.memory_a.id)
        storage.delete_memory(conflict.memory_b.id)
        print(f"✓ Deleted both memories")
```

---

## Full Conflict Resolution Workflow

```python
def run_conflict_resolution(
    scope: Optional[str] = None,
    auto_resolve: bool = True,
    interactive: bool = True
) -> ConflictResolutionResult:
    """
    Full conflict resolution workflow.

    Strategy:
    1. Detect all conflicts
    2. Auto-resolve where possible
    3. Ask user for ambiguous conflicts (if interactive)
    4. Execute resolutions
    5. Return result

    Args:
        scope: Scope to check (None = all)
        auto_resolve: Enable automatic resolution
        interactive: Enable user prompts for ambiguous conflicts

    Returns:
        ConflictResolutionResult
    """
    # Step 1: Detect conflicts
    conflicts = detect_conflicts(scope)

    if not conflicts:
        print("No conflicts detected.")
        return ConflictResolutionResult(
            conflicts_resolved=0,
            auto_resolved=0,
            user_resolved=0,
            actions_taken=[]
        )

    print(f"\nFound {len(conflicts)} conflict(s).\n")

    result = ConflictResolutionResult(
        conflicts_resolved=0,
        auto_resolved=0,
        user_resolved=0,
        actions_taken=[]
    )

    # Step 2: Process each conflict
    for conflict in conflicts:
        resolution = None

        # Try auto-resolution
        if auto_resolve:
            if conflict.conflict_type == ConflictType.REDUNDANCY:
                resolution = resolve_redundancy(conflict)
                result.auto_resolved += 1

            elif conflict.conflict_type == ConflictType.OBSOLESCENCE:
                resolution = resolve_obsolescence(conflict)
                result.auto_resolved += 1

            elif conflict.conflict_type == ConflictType.CONTRADICTION and conflict.auto_resolvable:
                resolution = resolve_contradiction_auto(conflict)
                if resolution:
                    result.auto_resolved += 1

        # User-mediated resolution (if not auto-resolved)
        if not resolution and interactive:
            resolution = resolve_conflict_interactive(conflict)
            result.user_resolved += 1

        # Execute resolution
        if resolution:
            execute_resolution(resolution, conflict)
            result.conflicts_resolved += 1
            result.actions_taken.append({
                "conflict_id": conflict.conflict_id,
                "conflict_type": conflict.conflict_type.value,
                "resolution_type": resolution.resolution_type,
                "rationale": resolution.rationale
            })

    print(f"\n✓ Resolved {result.conflicts_resolved} conflict(s).")
    print(f"  Auto-resolved: {result.auto_resolved}")
    print(f"  User-resolved: {result.user_resolved}")

    return result
```

---

## CLI Commands

```bash
# Detect conflicts (no resolution)
cerberus memory conflicts --list

# Resolve conflicts (auto + interactive)
cerberus memory conflicts --resolve

# Resolve conflicts (auto only, no prompts)
cerberus memory conflicts --resolve --auto-only

# Resolve conflicts in specific scope
cerberus memory conflicts --resolve --scope project:myapp

# Show conflict report
cerberus memory conflicts --report
```

---

## Token Costs

**Conflict resolution:**
- Detection: 0 tokens (TF-IDF similarity)
- Auto-resolution: 0 tokens (rule-based logic)
- User-mediated: 0 tokens (CLI prompts)
- Execution: 0 tokens (storage operations)

**Total per session:** 0 tokens (resolution is free)

---

## Validation Gates

**Phase 19 complete when:**
- ✅ Redundancy auto-resolution works (newer kept, older deleted)
- ✅ Obsolescence auto-resolution works (newer kept)
- ✅ Contradiction auto-resolution works (recency/confidence-based)
- ✅ User-mediated resolution works (ambiguous conflicts)
- ✅ Merge resolution works (user provides merged content)
- ✅ Execution works (storage updated correctly)
- ✅ 10+ conflict scenarios tested

**Metrics:**
- Auto-resolution rate: 60-70% of conflicts
- User resolution time: < 30 seconds per conflict
- Zero data loss (no accidental deletions)

**Testing:**
- Create 20 test conflicts (each type)
- Verify auto-resolution logic
- Test user prompts (all resolution options)
- Verify storage updates (memories deleted/merged)

---

## Dependencies

**Phase Dependencies:**
- Phase 11 (Maintenance) - uses conflict detection
- Phase 5 (Storage) - modifies memories
- Phase 13 (Search) - queries for similar memories

**External Dependencies:**
- scikit-learn (already required for Phase 2)

---

## Implementation Checklist

- [ ] Write `src/cerberus/memory/conflict_resolver.py`
- [ ] Implement `detect_conflicts()` function
- [ ] Implement `_is_contradiction()` algorithm
- [ ] Implement `resolve_redundancy()` function
- [ ] Implement `resolve_obsolescence()` function
- [ ] Implement `resolve_contradiction_auto()` function
- [ ] Implement `resolve_conflict_interactive()` function
- [ ] Implement `execute_resolution()` function
- [ ] Implement `run_conflict_resolution()` workflow
- [ ] Add CLI commands (`conflicts --list`, `--resolve`)
- [ ] Extend Phase 5 storage with `delete_memory()` method
- [ ] Write unit tests (each conflict type + resolution)
- [ ] Write integration tests (full workflow)
- [ ] Test 20 conflict scenarios
- [ ] Verify no data loss

---

**Last Updated:** 2026-01-22
**Version:** 1.0
**Status:** Specification complete, ready for implementation in Phase Epsilon
