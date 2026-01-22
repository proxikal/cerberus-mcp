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

## Embedding Model

**Library:** `sentence-transformers`

```python
from sentence_transformers import SentenceTransformer

class EmbeddingEngine:
    def __init__(self):
        # Use lightweight model for local execution (no API calls)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        # Model size: ~80MB, inference: ~50ms per sentence

    def embed(self, text: str) -> np.ndarray:
        return self.model.encode(text, convert_to_numpy=True)

    def similarity(self, text1: str, text2: str) -> float:
        emb1 = self.embed(text1)
        emb2 = self.embed(text2)
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
```

---

## Clustering Algorithm

```python
class SemanticAnalyzer:
    def __init__(self):
        self.embedder = EmbeddingEngine()
        self.similarity_threshold = 0.75  # 75% semantic similarity = same cluster

    def cluster_corrections(
        self,
        candidates: List[CorrectionCandidate]
    ) -> AnalyzedCorrections:
        if not candidates:
            return AnalyzedCorrections([], [], 0, 0, 0.0)

        # Extract messages
        messages = [c.user_message for c in candidates]

        # Compute embeddings
        embeddings = np.array([self.embedder.embed(msg) for msg in messages])

        # Compute similarity matrix
        similarity_matrix = self._compute_similarity_matrix(embeddings)

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
            compression_ratio=len(canonical_clusters) / len(candidates)
        )

    def _compute_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        # Cosine similarity matrix
        norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norm
        return normalized @ normalized.T

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
        Strategy: Use LLM to synthesize or pick shortest clear variant.
        """
        variants = [candidates[i].user_message for i in cluster_indices]
        correction_types = [candidates[i].correction_type for i in cluster_indices]
        confidences = [candidates[i].confidence for i in cluster_indices]

        # Simple strategy: pick shortest variant (LLM synthesis in Phase 3)
        canonical = min(variants, key=len)

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

## Canonical Form Extraction (LLM-based)

```python
class CanonicalExtractor:
    """
    Uses local LLM (Ollama) to extract canonical form.
    Fallback: Use shortest variant if LLM unavailable.
    """

    def __init__(self, llm_available: bool = True):
        self.llm_available = llm_available

    def extract(self, variants: List[str]) -> str:
        if not self.llm_available or len(variants) == 1:
            return variants[0]

        # LLM prompt
        prompt = f"""Extract canonical rule from these similar corrections:

{chr(10).join(f"- {v}" for v in variants)}

Return ONLY the canonical form (10 words max, imperative mood):"""

        # Call local Ollama (or fallback)
        try:
            canonical = self._call_ollama(prompt)
            return canonical.strip()
        except:
            return min(variants, key=len)

    def _call_ollama(self, prompt: str) -> str:
        import requests
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.2:3b", "prompt": prompt, "stream": False}
        )
        return response.json()["response"]
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
✓ EmbeddingEngine class implemented
✓ SemanticAnalyzer clustering functional
✓ Similarity threshold tuning (test with 50+ examples)
✓ Canonical extraction working (LLM-based + fallback)
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
→ expect: 1 cluster, canonical="Keep summaries concise"

# Scenario 2: Different topics (should NOT cluster)
variants = [
    "keep summaries short",
    "never exceed 200 lines"
]
→ expect: 2 clusters (similarity < 0.75)

# Scenario 3: Partial similarity
variants = [
    "keep summaries short and informative",
    "keep code short and maintainable"
]
→ expect: 2 clusters (different contexts)
```

---

## Dependencies

```bash
pip install sentence-transformers numpy
```

**Model download:** First run downloads ~80MB model

---

## Token Budget

- Embedding: 0 tokens (local model)
- LLM canonical extraction: ~50 tokens per cluster (optional, only if Ollama available)
- Total per session: 50-200 tokens (5-10 clusters typical)

---

## Performance

- Embedding: ~50ms per sentence
- Clustering: O(n²) for n candidates (acceptable for n < 100)
- Session end processing: < 2 seconds for typical session
