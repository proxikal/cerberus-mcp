# PHASE 19: CONFLICT RESOLUTION

## Objective
Implement concrete algorithms for resolving memory conflicts. Go beyond detection (Phase 11) to automatic resolution and user-mediated conflict resolution.

---

## Implementation Location

**File:** `src/cerberus/memory/conflict_resolver.py`

---

## Phase Assignment

**Rollout:** Phase Epsilon (Post-Delta)

**Prerequisites:**
- ✅ Phase 11 complete (conflict detection working)
- ✅ Phase 5 complete (storage working)
- ✅ Phase 13 complete (memory search for conflict queries)

**Why Phase Epsilon:**
- Phase 11 detects conflicts, Phase 19 resolves them
- Requires proven storage and search
- Enhancement layer on proven system

---

## Conflict Types

```python
class ConflictType(Enum):
    CONTRADICTION = "contradiction"  # "Use X" vs "Avoid X"
    REDUNDANCY = "redundancy"        # Duplicate or near-duplicate
    OBSOLESCENCE = "obsolescence"    # Old rule superseded by new
    SCOPE_CONFLICT = "scope_conflict"  # Universal vs project-specific
```

---

## Data Structures

```python
@dataclass
class MemoryConflict:
    """Detected conflict between memories."""
    conflict_id: str
    conflict_type: ConflictType
    memory_a: RetrievedMemory
    memory_b: RetrievedMemory
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
```

---

## Conflict Detection Algorithm (Extended from Phase 11)

```python
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

    Returns:
        List of MemoryConflict objects
    """
    from cerberus.memory.retrieval import MemoryRetrieval
    retrieval = MemoryRetrieval()

    memories = retrieval.get_all(scope=scope)
    conflicts = []

    # Pairwise contradiction detection
    for i, mem_a in enumerate(memories):
        for mem_b in memories[i+1:]:
            # Check contradiction
            if _is_contradiction(mem_a, mem_b):
                conflicts.append(MemoryConflict(
                    conflict_id=f"conflict-{uuid.uuid4().hex[:8]}",
                    conflict_type=ConflictType.CONTRADICTION,
                    memory_a=mem_a,
                    memory_b=mem_b,
                    similarity=_calculate_similarity(mem_a.content, mem_b.content),
                    severity=_calculate_severity(mem_a, mem_b, ConflictType.CONTRADICTION),
                    auto_resolvable=_can_auto_resolve_contradiction(mem_a, mem_b),
                    recommended_resolution=_recommend_contradiction_resolution(mem_a, mem_b)
                ))

            # Check redundancy
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
    # NOTE: _detect_obsolescence() must use _calculate_severity() for consistency
    obsolete_conflicts = _detect_obsolescence(memories)
    conflicts.extend(obsolete_conflicts)

    return conflicts


def _is_contradiction(mem_a: RetrievedMemory, mem_b: RetrievedMemory) -> bool:
    """
    Detect if two memories contradict each other.

    Patterns:
    - "Use X" vs "Avoid X"
    - "Always Y" vs "Never Y"
    - "Prefer Z" vs "Don't use Z"
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


def _calculate_similarity(content_a: str, content_b: str) -> float:
    """TF-IDF cosine similarity (same as Phase 2)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([content_a, content_b])
    similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]

    return similarity


def _calculate_severity(
    mem_a: RetrievedMemory,
    mem_b: RetrievedMemory,
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
```

---

