# PHASE 14: DYNAMIC ANCHORING

## Objective
Link abstract rules to concrete code examples. Inject example files alongside text rules for exact pattern replication.

---

## Implementation Location

**File:** `src/cerberus/memory/anchoring.py`

---

## Phase Assignment

**Rollout:** Phase Delta (Post-Gamma)

**Prerequisites:**
- ✅ Phase Beta complete (SQLite stable)
- ✅ Phase 7 complete (context injection working)
- ✅ Phase 13 complete (memory search operational)

**Why Phase Delta:**
- Core memory system must be proven first
- Requires stable code indexing (Cerberus index)
- Enhancement layer on top of working injection
- Can be added incrementally without risk

---

## Data Structures

```python
@dataclass
class AnchoredMemory:
    """Memory with code example anchor."""
    memory_id: str
    content: str  # Abstract rule (e.g., "Use Repository pattern")
    anchor_file: Optional[str]  # Example file path (e.g., "src/users/repo.go")
    anchor_symbol: Optional[str]  # Symbol name (e.g., "UserRepository")
    anchor_score: float  # Quality score (0.0-1.0)
    anchor_metadata: Dict[str, Any]  # Lines, LOC, last_modified

@dataclass
class AnchorCandidate:
    """Candidate file for anchoring."""
    file_path: str
    symbol_name: Optional[str]
    match_score: float  # How well it matches the rule
    file_size: int  # Lines of code
    recency_score: float  # How recently modified
    quality_score: float  # Combined score

@dataclass
class AnchorSearchQuery:
    """Search parameters for finding anchor files."""
    rule_text: str  # The rule to find example for
    scope: str  # "universal", "language:X", "project:Y"
    language: Optional[str]
    project_path: Optional[str]
    max_file_size: int = 500  # Max lines to consider
    min_quality: float = 0.7  # Minimum quality threshold
```

---

## Core Algorithm: Anchor Discovery

```python
def find_anchor_for_rule(rule: str, scope: str, language: str, project_path: Optional[str], min_quality: float = 0.7) -> Optional[AnchorCandidate]:
    """
    Find best code example for abstract rule.

    Strategy:
    1. Extract keywords from rule text
    2. Search code index for matching files/symbols
    3. Score candidates by relevance, size, recency
    4. Return top match if above quality threshold

    Args:
        rule: Abstract rule text (e.g., "Use Repository pattern")
        scope: Memory scope
        language: Programming language
        project_path: Project directory (if project-scoped)
        min_quality: Minimum quality score (0.0-1.0, default 0.7)

    Returns:
        AnchorCandidate if found, None otherwise
    """

    # Step 1: Extract keywords from rule
    keywords = _extract_keywords(rule)
    # "Use Repository pattern" → ["repository", "pattern"]

    # Step 2: Build search query
    if project_path:
        search_scope = project_path
    elif language:
        search_scope = f"**/*.{LANGUAGE_EXTENSIONS[language]}"
    else:
        search_scope = None  # Universal - no anchor

    if not search_scope:
        return None

    # Step 3: Search code index (uses Cerberus)
    candidates = []

    # Search by filename keywords
    for keyword in keywords:
        results = cerberus_search(
            query=keyword,
            scope=search_scope,
            limit=10
        )
        candidates.extend(results)

    # Search by symbol names
    for keyword in keywords:
        results = cerberus_symbol_search(
            query=keyword,
            scope=search_scope,
            limit=10
        )
        candidates.extend(results)

    # Step 4: Score candidates
    scored = []
    for candidate in candidates:
        # Relevance: TF-IDF similarity between rule and file content
        relevance = _calculate_relevance(rule, candidate.file_path)

        # Size penalty: Prefer concise examples
        size_score = 1.0 - (min(candidate.file_size, 500) / 500)

        # Recency: Prefer recently modified files
        recency = _calculate_recency(candidate.file_path)

        # Combined score: weighted average
        quality = (
            0.6 * relevance +
            0.2 * size_score +
            0.2 * recency
        )

        if quality >= min_quality:  # Configurable threshold
            scored.append(AnchorCandidate(
                file_path=candidate.file_path,
                symbol_name=candidate.symbol_name,
                match_score=relevance,
                file_size=candidate.file_size,
                recency_score=recency,
                quality_score=quality
            ))

    # Step 5: Return best match
    if scored:
        best = max(scored, key=lambda c: c.quality_score)
        return best
    return None


def _extract_keywords(rule: str) -> List[str]:
    """
    Extract meaningful keywords from rule text.

    Examples:
        "Use Repository pattern" → ["repository", "pattern"]
        "Always validate input" → ["validate", "input"]
        "Prefer async/await" → ["async", "await"]
    """
    # Remove common words
    stopwords = {"use", "always", "never", "prefer", "avoid", "the", "a", "an"}

    # Tokenize
    tokens = rule.lower().split()

    # Filter stopwords, keep meaningful terms
    keywords = [t for t in tokens if t not in stopwords and len(t) > 2]

    return keywords


def _calculate_relevance(rule: str, file_path: str) -> float:
    """
    TF-IDF similarity between rule and file content.

    Uses scikit-learn TfidfVectorizer (same as Phase 2).
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    # Read file content
    with open(file_path, 'r') as f:
        file_content = f.read()

    # Vectorize
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([rule, file_content])

    # Cosine similarity
    from sklearn.metrics.pairwise import cosine_similarity
    similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]

    return similarity


def _calculate_recency(file_path: str) -> float:
    """
    Recency score based on last modification time.

    Recently modified files are better examples (more likely to be current patterns).

    NOTE: This uses exponential decay for FILE modification times, which is
    different from the step-function decay used for memory timestamps in
    Phase 6/7. File recency needs smooth decay because file modification
    patterns are more continuous, while memory relevance has discrete tiers.
    """
    import os
    from datetime import datetime, timedelta

    mtime = os.path.getmtime(file_path)
    modified = datetime.fromtimestamp(mtime)
    age_days = (datetime.now() - modified).days

    # Exponential decay: 1.0 at 0 days, 0.5 at 30 days, 0.1 at 180 days
    decay_rate = 0.023  # ln(0.5) / 30
    recency = math.exp(-decay_rate * age_days)

    return recency
```

---

