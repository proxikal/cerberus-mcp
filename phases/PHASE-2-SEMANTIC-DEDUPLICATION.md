# PHASE 2: SEMANTIC DEDUPLICATION

## Objective
Group similar corrections semantically to prevent duplicates and extract canonical form.

---

## Implementation Location

**File:** `src/cerberus/memory/semantic_analyzer.py`

---

## Data Structures

```python
@dataclass
class CorrectionCluster:
    canonical_text: str  # "Keep output concise"
    variants: List[str]  # ["keep it short", "be terse", "concise output"]
    correction_type: str
    frequency: int
    confidence: float
    first_seen: datetime
    last_seen: datetime
```

```python
@dataclass
class AnalyzedCorrections:
    clusters: List[CorrectionCluster]
    outliers: List[CorrectionCandidate]  # Low confidence, needs review
    total_raw: int
    total_clustered: int
    compression_ratio: float
```

---

## Text Similarity Engine (TF-IDF)

**Library:** `scikit-learn` (lightweight, no model download)

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class SimilarityEngine:
    """
    TF-IDF based text similarity.
    Lightweight: ~1MB dependency, no model downloads.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            ngram_range=(1, 2),  # Unigrams and bigrams
            max_features=1000
        )

    def compute_similarity_matrix(self, texts: List[str]) -> np.ndarray:
        """
        Compute pairwise cosine similarity between texts.
        """
        if len(texts) < 2:
            return np.array([[1.0]])

        # Fit and transform
        tfidf_matrix = self.vectorizer.fit_transform(texts)

        # Compute cosine similarity
        return cosine_similarity(tfidf_matrix)

    def similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts.
        """
        matrix = self.compute_similarity_matrix([text1, text2])
        return matrix[0, 1]
```

---

## Clustering Algorithm

```python
class SemanticAnalyzer:
    def __init__(self):
        self.similarity_engine = SimilarityEngine()
        self.similarity_threshold = 0.65  # 65% TF-IDF similarity = same cluster

    def cluster_corrections(
        self,
        candidates: List[CorrectionCandidate]
    ) -> AnalyzedCorrections:
        if not candidates:
            return AnalyzedCorrections([], [], 0, 0, 0.0)

        # Extract messages
        messages = [c.user_message for c in candidates]

        # Compute similarity matrix
        similarity_matrix = self.similarity_engine.compute_similarity_matrix(messages)

        # Cluster using threshold-based grouping
        clusters = self._threshold_clustering(
            messages,
            similarity_matrix,
            candidates
        )

        # Extract canonical form for each cluster
        canonical_clusters = [
            self._extract_canonical(cluster, candidates)
            for cluster in clusters
        ]

        return AnalyzedCorrections(
            clusters=canonical_clusters,
            outliers=self._find_outliers(candidates, canonical_clusters),
            total_raw=len(candidates),
            total_clustered=len(canonical_clusters),
            compression_ratio=len(canonical_clusters) / len(candidates) if candidates else 0.0
        )

    def _threshold_clustering(
        self,
        messages: List[str],
        similarity_matrix: np.ndarray,
        candidates: List[CorrectionCandidate]
    ) -> List[List[int]]:
        """
        Cluster messages where similarity > threshold.
        Returns list of clusters (each cluster = list of indices).
        """
        n = len(messages)
        visited = [False] * n
        clusters = []

        for i in range(n):
            if visited[i]:
                continue

            # Start new cluster
            cluster = [i]
            visited[i] = True

            # Find all similar messages
            for j in range(i + 1, n):
                if not visited[j] and similarity_matrix[i, j] > self.similarity_threshold:
                    cluster.append(j)
                    visited[j] = True

            clusters.append(cluster)

        return clusters

    def _extract_canonical(
        self,
        cluster_indices: List[int],
        candidates: List[CorrectionCandidate]
    ) -> CorrectionCluster:
        """
        Extract canonical form from cluster.
        Strategy: Pick clearest variant (shortest that's >5 words, or shortest overall).
        """
        variants = [candidates[i].user_message for i in cluster_indices]
        correction_types = [candidates[i].correction_type for i in cluster_indices]
        confidences = [candidates[i].confidence for i in cluster_indices]

        # Strategy: prefer medium-length variants (not too short, not too long)
        def quality_score(text: str) -> float:
            words = len(text.split())
            if words < 3:
                return 0.5  # Too short, might lose meaning
            elif words > 15:
                return 0.7  # Too long
            else:
                return 1.0  # Good length

        canonical = max(variants, key=lambda v: (quality_score(v), -len(v)))

        # Use most common correction type
        correction_type = max(set(correction_types), key=correction_types.count)

        return CorrectionCluster(
            canonical_text=canonical,
            variants=variants,
            correction_type=correction_type,
            frequency=len(variants),
            confidence=sum(confidences) / len(confidences),
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )

    def _find_outliers(
        self,
        candidates: List[CorrectionCandidate],
        clusters: List[CorrectionCluster]
    ) -> List[CorrectionCandidate]:
        """Find corrections not in any cluster (confidence too low)."""
        clustered_texts = set()
        for cluster in clusters:
            clustered_texts.update(cluster.variants)

        return [c for c in candidates if c.user_message not in clustered_texts]
```

---

## Canonical Form Extraction

```python
class CanonicalExtractor:
    """
    Extract canonical form from variant corrections.

    PRIMARY: Rule-based selection (no dependencies, instant)
    OPTIONAL: LLM enhancement (if Ollama available)
    """

    def __init__(self, use_llm: bool = False):
        """
        Args:
            use_llm: If True AND Ollama is available, use LLM for refinement.
                     Default is False - rule-based selection works well.
        """
        self.use_llm = use_llm

    def extract(self, variants: List[str]) -> str:
        """
        Extract canonical form from variants.

        Always uses rule-based selection first.
        LLM only used if explicitly enabled AND available.
        """
        if len(variants) == 1:
            return variants[0]

        # PRIMARY: Rule-based selection (always works, no dependencies)
        canonical = self._select_best_variant(variants)

        # OPTIONAL: LLM refinement (only if explicitly enabled)
        if self.use_llm:
            refined = self._try_llm_refinement(canonical, variants)
            if refined:
                canonical = refined

        return canonical

    def _select_best_variant(self, variants: List[str]) -> str:
        """
        Select best variant using quality scoring.

        Scoring criteria:
        1. Starts with imperative verb (+3)
        2. Optimal length 5-12 words (+2)
        3. Contains actionable keywords (+1)
        4. Shorter preferred among equals
        """
        IMPERATIVE_VERBS = {
            'use', 'keep', 'avoid', 'never', 'always', 'prefer',
            'write', 'add', 'remove', 'check', 'ensure', 'follow',
            'split', 'plan', 'test', 'log', 'handle', 'return'
        }

        ACTION_KEYWORDS = {
            'before', 'after', 'instead', 'when', 'always', 'never',
            'must', 'should', 'limit', 'max', 'min'
        }

        def score(text: str) -> tuple:
            words = text.split()
            word_count = len(words)
            text_lower = text.lower()

            # Score 1: Starts with imperative verb (highest priority)
            starts_verb = words[0].lower() in IMPERATIVE_VERBS if words else False
            verb_score = 3 if starts_verb else 0

            # Score 2: Optimal length (5-12 words)
            if 5 <= word_count <= 12:
                length_score = 2
            elif 3 <= word_count <= 15:
                length_score = 1
            else:
                length_score = 0

            # Score 3: Contains actionable keywords
            action_score = sum(1 for kw in ACTION_KEYWORDS if kw in text_lower)

            # Tiebreaker: shorter is better
            return (verb_score, length_score, action_score, -len(text))

        return max(variants, key=score)

    def _try_llm_refinement(self, canonical: str, variants: List[str]) -> Optional[str]:
        """
        OPTIONAL: Use Ollama for refinement if available.
        Returns None if LLM unavailable or fails.
        """
        try:
            import requests

            prompt = f"""Refine this rule to canonical form (max 10 words, imperative mood):

Current: {canonical}
Variants: {', '.join(variants[:3])}

Output ONLY the refined rule:"""

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.2:3b", "prompt": prompt, "stream": False},
                timeout=5
            )

            if response.status_code == 200:
                refined = response.json().get("response", "").strip()
                # Validate: must be reasonable length
                if 3 <= len(refined.split()) <= 15:
                    return refined

        except Exception:
            pass  # LLM unavailable or failed - that's fine

        return None
```

---

## Integration with Phase 1

```python
# At end of session
session_analyzer = SessionAnalyzer()
semantic_analyzer = SemanticAnalyzer()

# Get raw candidates from Phase 1
raw_candidates = session_analyzer.candidates

# Deduplicate and cluster
analyzed = semantic_analyzer.cluster_corrections(raw_candidates)

# Store clusters (not raw candidates)
store_clusters(analyzed.clusters)
```

---

## Storage

**File:** `.cerberus/clustered_corrections.json`

```json
{
  "session_id": "20260122-133514",
  "timestamp": "2026-01-22T13:35:14Z",
  "clusters": [
    {
      "canonical": "Keep output concise",
      "variants": [
        "keep it short",
        "be terse",
        "concise output please"
      ],
      "type": "style",
      "frequency": 3,
      "confidence": 0.85
    },
    {
      "canonical": "Never exceed 200 lines per file",
      "variants": [
        "don't write files over 200 lines",
        "file size limit is 200 lines"
      ],
      "type": "rule",
      "frequency": 2,
      "confidence": 0.95
    }
  ],
  "compression_ratio": 0.4
}
```

---

## Exit Criteria

```
✓ SimilarityEngine (TF-IDF) implemented
✓ SemanticAnalyzer clustering functional
✓ Similarity threshold tuning (test with 50+ examples)
✓ Canonical extraction working (rule-based + optional LLM)
✓ Integration with Phase 1 complete
✓ Storage format validated
✓ Compression ratio > 0.6 (60% reduction in duplicates)
```

---

## Test Scenarios

```python
# Scenario 1: Clear duplicates
variants = [
    "keep summaries short",
    "be concise in summaries",
    "summaries should be brief"
]
→ expect: 1 cluster, canonical="keep summaries short"

# Scenario 2: Different topics (should NOT cluster)
variants = [
    "keep summaries short",
    "never exceed 200 lines"
]
→ expect: 2 clusters (similarity < 0.65)

# Scenario 3: Partial similarity
variants = [
    "keep summaries short and informative",
    "keep code short and maintainable"
]
→ expect: depends on overlap; may cluster if threshold met
```

---

## Dependencies

```bash
pip install scikit-learn numpy  # Required
# pip install requests  # Only if using optional LLM refinement
```

**No model download required.** TF-IDF is computed on-the-fly.

**Optional:** Ollama for LLM refinement (not required, rule-based works well)

---

## Token Budget

- TF-IDF: 0 tokens (local computation)
- LLM canonical extraction: 0 tokens (optional, local Ollama only)
- Total per session: 0 tokens

---

## Performance

- TF-IDF vectorization: ~10ms for 100 texts
- Similarity matrix: ~5ms for 100×100
- Clustering: O(n²) for n candidates (acceptable for n < 100)
- Session end processing: < 500ms for typical session

---

## Why TF-IDF over Embeddings

| Aspect | TF-IDF | sentence-transformers |
|--------|--------|----------------------|
| Dependency size | ~1MB | ~80MB + 400MB model |
| Model download | None | Required (first run) |
| Inference speed | ~10ms | ~50ms |
| Accuracy | Good for short text | Better for complex semantics |
| Memory usage | ~10MB | ~500MB |

**TF-IDF is sufficient** for deduplicating short correction phrases. The phrases are typically:
- Short (5-15 words)
- Use similar vocabulary ("keep", "concise", "short")
- Don't require deep semantic understanding

Embeddings add complexity without proportional benefit for this use case.
