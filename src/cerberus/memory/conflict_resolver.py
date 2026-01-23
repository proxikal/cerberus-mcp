"""
Phase 19: Conflict Resolution

Implements conflict detection and resolution for memory system.

Phase 19A: Extended conflict detection (contradiction, redundancy, obsolescence)
Phase 19B: Automatic and user-mediated conflict resolution

Architecture:
- detect_conflicts(): Find conflicts between memories
- resolve_*(): Automatic resolution algorithms
- resolve_conflict_interactive(): User-mediated resolution
- execute_resolution(): Apply resolution to storage
- run_conflict_resolution(): Full workflow
"""

import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Set


class ConflictType(Enum):
    """Types of memory conflicts."""
    CONTRADICTION = "contradiction"  # "Use X" vs "Avoid X"
    REDUNDANCY = "redundancy"        # Duplicate or near-duplicate
    OBSOLESCENCE = "obsolescence"    # Old rule superseded by new
    SCOPE_CONFLICT = "scope_conflict"  # Universal vs project-specific


@dataclass
class MemoryConflict:
    """Detected conflict between memories."""
    conflict_id: str
    conflict_type: ConflictType
    memory_a: Any  # RetrievedMemory
    memory_b: Any  # RetrievedMemory
    similarity: float  # 0.0-1.0
    severity: str  # "low", "medium", "high", "critical"
    auto_resolvable: bool
    recommended_resolution: str  # "keep_a", "keep_b", "keep_both", "merge", "ask_user"


@dataclass
class ConflictResolution:
    """Resolution decision for conflict."""
    conflict_id: str
    resolution_type: str  # "keep_a", "keep_b", "keep_both", "merge", "delete_both"
    merged_content: Optional[str]  # If resolution_type == "merge"
    rationale: str  # Why this resolution


@dataclass
class ConflictResolutionResult:
    """Result of conflict resolution."""
    conflicts_resolved: int
    auto_resolved: int
    user_resolved: int
    actions_taken: List[Dict[str, Any]]  # [{"action": "delete", "memory_id": "..."}]


# ============================================================================
# Phase 19A: Conflict Detection
# ============================================================================

def detect_conflicts(
    scope: Optional[str] = None
) -> List[MemoryConflict]:
    """
    Detect conflicts in stored memories.

    Strategy:
    1. Load memories in scope
    2. Pairwise comparison for contradictions
    3. Similarity clustering for redundancies
    4. Recency check for obsolescence
    5. Scope hierarchy check for scope conflicts

    Args:
        scope: Optional scope filter (None = all memories)

    Returns:
        List of MemoryConflict objects
    """
    from cerberus.memory.retrieval import MemoryRetrieval
    retrieval = MemoryRetrieval()

    memories = retrieval.get_all(scope=scope)
    conflicts = []

    # Pairwise contradiction and redundancy detection
    for i, mem_a in enumerate(memories):
        for mem_b in memories[i+1:]:
            # Check contradiction
            if _is_contradiction(mem_a, mem_b):
                similarity = _calculate_similarity(mem_a.content, mem_b.content)
                conflicts.append(MemoryConflict(
                    conflict_id=f"conflict-{uuid.uuid4().hex[:8]}",
                    conflict_type=ConflictType.CONTRADICTION,
                    memory_a=mem_a,
                    memory_b=mem_b,
                    similarity=similarity,
                    severity=_calculate_severity(mem_a, mem_b, ConflictType.CONTRADICTION),
                    auto_resolvable=_can_auto_resolve_contradiction(mem_a, mem_b),
                    recommended_resolution=_recommend_contradiction_resolution(mem_a, mem_b)
                ))

            # Check redundancy (high similarity)
            else:
                similarity = _calculate_similarity(mem_a.content, mem_b.content)
                if similarity > 0.85:  # High similarity = redundant
                    conflicts.append(MemoryConflict(
                        conflict_id=f"conflict-{uuid.uuid4().hex[:8]}",
                        conflict_type=ConflictType.REDUNDANCY,
                        memory_a=mem_a,
                        memory_b=mem_b,
                        similarity=similarity,
                        severity=_calculate_severity(mem_a, mem_b, ConflictType.REDUNDANCY),
                        auto_resolvable=True,
                        recommended_resolution="keep_newer"
                    ))

    # Obsolescence detection (separate pass)
    obsolete_conflicts = _detect_obsolescence(memories)
    conflicts.extend(obsolete_conflicts)

    return conflicts


def _is_contradiction(mem_a: Any, mem_b: Any) -> bool:
    """
    Detect if two memories contradict each other.

    Patterns:
    - "Use X" vs "Avoid X"
    - "Always Y" vs "Never Y"
    - "Prefer Z" vs "Don't use Z"

    Args:
        mem_a: First memory
        mem_b: Second memory

    Returns:
        True if memories contradict, False otherwise
    """
    content_a = mem_a.content.lower()
    content_b = mem_b.content.lower()

    # Extract keywords
    keywords_a = set(_extract_keywords(content_a))
    keywords_b = set(_extract_keywords(content_b))

    # Check keyword overlap
    overlap = keywords_a & keywords_b

    if not overlap:
        return False  # No common topic

    # Check opposing sentiment
    affirmative_a = any(kw in content_a for kw in ["use", "prefer", "always", "do"])
    negative_a = any(kw in content_a for kw in ["avoid", "never", "don't", "do not"])

    affirmative_b = any(kw in content_b for kw in ["use", "prefer", "always", "do"])
    negative_b = any(kw in content_b for kw in ["avoid", "never", "don't", "do not"])

    # Contradiction: one affirmative, one negative, same topic
    if (affirmative_a and negative_b) or (negative_a and affirmative_b):
        return True

    return False


def _extract_keywords(text: str) -> List[str]:
    """
    Extract keywords from text (simple tokenization).

    Args:
        text: Input text

    Returns:
        List of keywords
    """
    # Simple keyword extraction: split on whitespace, remove stopwords
    stopwords = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "should", "could", "may", "might", "must", "can", "to", "of",
        "in", "on", "at", "for", "with", "by", "from", "as", "and",
        "or", "but", "if", "when", "where", "why", "how"
    }

    words = text.lower().split()
    keywords = [w.strip(".,!?;:") for w in words if w not in stopwords and len(w) > 2]

    return keywords


def _calculate_similarity(content_a: str, content_b: str) -> float:
    """
    Calculate TF-IDF cosine similarity (same as Phase 2).

    Args:
        content_a: First text
        content_b: Second text

    Returns:
        Similarity score (0.0-1.0)
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([content_a, content_b])
        similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]

        return float(similarity)
    except Exception:
        # Fallback: simple word overlap
        words_a = set(_extract_keywords(content_a))
        words_b = set(_extract_keywords(content_b))

        if not words_a or not words_b:
            return 0.0

        overlap = len(words_a & words_b)
        total = len(words_a | words_b)

        return overlap / total if total > 0 else 0.0


def _calculate_severity(
    mem_a: Any,
    mem_b: Any,
    conflict_type: ConflictType
) -> str:
    """
    Calculate conflict severity based on standardized scoring.

    Scoring factors:
    - Scope (+3): Universal conflicts more severe than project-specific
    - Recency (+2): Both memories recent (< 7 days) increases urgency
    - Confidence (+2): High confidence (> 0.9) increases severity
    - Type (+2/+1/+0): Conflict type inherent severity
      - CONTRADICTION: +2 (opposing rules)
      - OBSOLESCENCE: +1 (superseded rules)
      - REDUNDANCY: +0 (duplicates, least severe)

    Severity mapping:
    - score >= 7: critical
    - score >= 5: high
    - score >= 3: medium
    - score < 3: low

    Args:
        mem_a: First memory
        mem_b: Second memory
        conflict_type: Type of conflict

    Returns:
        "low", "medium", "high", or "critical"
    """
    score = 0

    # Scope factor (+3)
    if mem_a.scope == "universal" or mem_b.scope == "universal":
        score += 3

    # Recency factor (+2)
    age_a_days = (datetime.now() - mem_a.created_at).days
    age_b_days = (datetime.now() - mem_b.created_at).days

    if age_a_days < 7 and age_b_days < 7:
        score += 2

    # Confidence factor (+2)
    if mem_a.confidence > 0.9 or mem_b.confidence > 0.9:
        score += 2

    # Conflict type severity (+2/+1/+0)
    if conflict_type == ConflictType.CONTRADICTION:
        score += 2  # Most severe
    elif conflict_type == ConflictType.OBSOLESCENCE:
        score += 1  # Medium severity
    elif conflict_type == ConflictType.REDUNDANCY:
        score += 0  # Least severe

    # Map score to severity level
    if score >= 7:
        return "critical"
    elif score >= 5:
        return "high"
    elif score >= 3:
        return "medium"
    else:
        return "low"


def _detect_obsolescence(memories: List[Any]) -> List[MemoryConflict]:
    """
    Detect obsolescence conflicts.

    Strategy: If two memories have high similarity (> 0.75) and one is
    significantly newer (> 30 days), mark older as obsolete.

    Args:
        memories: List of memories to check

    Returns:
        List of obsolescence conflicts
    """
    conflicts = []

    for i, mem_a in enumerate(memories):
        for mem_b in memories[i+1:]:
            similarity = _calculate_similarity(mem_a.content, mem_b.content)

            if similarity > 0.75:  # Similar enough to be same rule
                age_diff_days = abs((mem_a.created_at - mem_b.created_at).days)

                if age_diff_days > 30:  # Significant age difference
                    conflicts.append(MemoryConflict(
                        conflict_id=f"conflict-{uuid.uuid4().hex[:8]}",
                        conflict_type=ConflictType.OBSOLESCENCE,
                        memory_a=mem_a,
                        memory_b=mem_b,
                        similarity=similarity,
                        severity=_calculate_severity(mem_a, mem_b, ConflictType.OBSOLESCENCE),
                        auto_resolvable=True,
                        recommended_resolution="keep_newer"
                    ))

    return conflicts


# ============================================================================
# Phase 19B: Conflict Resolution
# ============================================================================

def _can_auto_resolve_contradiction(
    mem_a: Any,
    mem_b: Any
) -> bool:
    """
    Check if contradiction can be auto-resolved.

    Auto-resolvable if:
    - One memory is significantly newer (> 30 days difference)
    - One memory has much higher confidence (> 0.2 difference)

    Otherwise: Requires user decision

    Args:
        mem_a: First memory
        mem_b: Second memory

    Returns:
        True if auto-resolvable, False if requires user input
    """
    age_diff = abs((mem_a.created_at - mem_b.created_at).days)
    conf_diff = abs(mem_a.confidence - mem_b.confidence)

    if age_diff > 30:
        return True  # Newer wins

    if conf_diff > 0.2:
        return True  # Higher confidence wins

    return False  # Ambiguous, ask user


def _recommend_contradiction_resolution(
    mem_a: Any,
    mem_b: Any
) -> str:
    """
    Recommend resolution for contradiction.

    Args:
        mem_a: First memory
        mem_b: Second memory

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


def resolve_redundancy(conflict: MemoryConflict) -> ConflictResolution:
    """
    Automatically resolve redundancy conflict.

    Strategy: Keep newer, delete older.

    Args:
        conflict: Redundancy conflict

    Returns:
        ConflictResolution with resolution decision
    """
    mem_a = conflict.memory_a
    mem_b = conflict.memory_b

    # Keep newer
    if mem_a.created_at > mem_b.created_at:
        keep = mem_a
        delete = mem_b
        resolution_type = "keep_a"
    else:
        keep = mem_b
        delete = mem_a
        resolution_type = "keep_b"

    return ConflictResolution(
        conflict_id=conflict.conflict_id,
        resolution_type=resolution_type,
        merged_content=None,
        rationale=f"Kept newer memory ({keep.id}), deleted redundant older memory ({delete.id})"
    )


def resolve_obsolescence(conflict: MemoryConflict) -> ConflictResolution:
    """
    Automatically resolve obsolescence conflict.

    Strategy: Delete older, keep newer.

    Args:
        conflict: Obsolescence conflict

    Returns:
        ConflictResolution with resolution decision
    """
    mem_a = conflict.memory_a
    mem_b = conflict.memory_b

    # Keep newer (explicit supersession)
    if mem_a.created_at > mem_b.created_at:
        keep = mem_a
        delete = mem_b
        resolution_type = "keep_a"
    else:
        keep = mem_b
        delete = mem_a
        resolution_type = "keep_b"

    return ConflictResolution(
        conflict_id=conflict.conflict_id,
        resolution_type=resolution_type,
        merged_content=None,
        rationale=f"Newer memory ({keep.id}) supersedes older ({delete.id})"
    )


def resolve_contradiction_auto(conflict: MemoryConflict) -> Optional[ConflictResolution]:
    """
    Automatically resolve contradiction if possible.

    Args:
        conflict: Contradiction conflict

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


def resolve_conflict_interactive(conflict: MemoryConflict) -> ConflictResolution:
    """
    Ask user to resolve conflict.

    Shows:
    - Both memories
    - Conflict type
    - Recommended resolution
    - Options: keep A, keep B, keep both, merge, delete both

    Args:
        conflict: Conflict to resolve

    Returns:
        ConflictResolution based on user choice
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
        resolved = resolve_contradiction_auto(conflict)
        if resolved:
            return resolved

        # Fallback: keep both
        return ConflictResolution(
            conflict_id=conflict.conflict_id,
            resolution_type="keep_both",
            merged_content=None,
            rationale="Deferred resolution (kept both)"
        )


def execute_resolution(resolution: ConflictResolution, conflict: MemoryConflict) -> None:
    """
    Execute conflict resolution action.

    Modifies storage based on resolution decision.

    Args:
        resolution: Resolution decision
        conflict: Original conflict
    """
    from cerberus.memory.storage import MemoryStorage
    from cerberus.memory.proposal_engine import MemoryProposal

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
