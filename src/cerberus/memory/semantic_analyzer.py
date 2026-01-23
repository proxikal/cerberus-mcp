"""
Phase 2: Semantic Deduplication

Clusters similar corrections using TF-IDF to prevent duplicates and extract canonical forms.
Target: 60%+ compression ratio (10 corrections → 4 clusters).

Zero token cost - local TF-IDF computation, no model downloads.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class CorrectionCluster:
    """Represents a cluster of semantically similar corrections."""
    canonical_text: str  # "Keep output concise"
    variants: List[str] = field(default_factory=list)  # All similar corrections
    correction_type: str = "behavior"  # style, behavior, rule, preference
    frequency: int = 1
    confidence: float = 0.0
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "canonical": self.canonical_text,
            "variants": self.variants,
            "type": self.correction_type,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat()
        }


@dataclass
class AnalyzedCorrections:
    """Result of semantic analysis and clustering."""
    clusters: List[CorrectionCluster] = field(default_factory=list)
    outliers: List = field(default_factory=list)  # CorrectionCandidate
    total_raw: int = 0
    total_clustered: int = 0
    compression_ratio: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "clusters": [c.to_dict() for c in self.clusters],
            "outliers": [o.to_dict() for o in self.outliers],
            "total_raw": self.total_raw,
            "total_clustered": self.total_clustered,
            "compression_ratio": self.compression_ratio
        }


class SimilarityEngine:
    """
    TF-IDF based text similarity.

    Lightweight: ~1MB dependency, no model downloads.
    Good for short correction phrases (5-15 words).
    """

    def __init__(self):
        """Initialize TF-IDF vectorizer optimized for short correction phrases."""
        # Use character n-grams for short text - works better than word tokens
        # Character 3-5 grams capture partial word matches and typos
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            analyzer='char',  # Character-level instead of word-level
            ngram_range=(3, 5),  # Character 3-5 grams
            max_features=1000,
            min_df=1,
            # Use sublinear TF scaling for better normalization
            sublinear_tf=True
        )

    def compute_similarity_matrix(self, texts: List[str]) -> np.ndarray:
        """
        Compute pairwise cosine similarity between texts.

        Args:
            texts: List of text strings

        Returns:
            Square matrix of similarities (n x n)
        """
        if len(texts) < 2:
            return np.array([[1.0]])

        # Fit and transform texts to TF-IDF vectors
        tfidf_matrix = self.vectorizer.fit_transform(texts)

        # Compute cosine similarity
        similarity_matrix = cosine_similarity(tfidf_matrix)

        return similarity_matrix

    def similarity(self, text1: str, text2: str) -> float:
        """
        Compute similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0-1.0)
        """
        matrix = self.compute_similarity_matrix([text1, text2])
        return float(matrix[0, 1])


class CanonicalExtractor:
    """
    Extract canonical form from variant corrections.

    PRIMARY: Rule-based selection (no dependencies, instant)
    OPTIONAL: LLM enhancement (if Ollama available AND enabled)
    """

    # Imperative verbs for scoring
    IMPERATIVE_VERBS = {
        'use', 'keep', 'avoid', 'never', 'always', 'prefer',
        'write', 'add', 'remove', 'check', 'ensure', 'follow',
        'split', 'plan', 'test', 'log', 'handle', 'return',
        'make', 'set', 'get', 'put', 'create', 'delete',
        'stop', 'start', 'limit', 'validate', 'verify'
    }

    # Action keywords for scoring
    ACTION_KEYWORDS = {
        'before', 'after', 'instead', 'when', 'always', 'never',
        'must', 'should', 'limit', 'max', 'min', 'only', 'all'
    }

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

        Args:
            variants: List of correction text variants

        Returns:
            Canonical form (best representative)
        """
        if not variants:
            return ""

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
        def score(text: str) -> Tuple[int, int, int, int]:
            words = text.split()
            word_count = len(words)
            text_lower = text.lower()

            # Score 1: Starts with imperative verb (highest priority)
            starts_verb = words[0].lower() in self.IMPERATIVE_VERBS if words else False
            verb_score = 3 if starts_verb else 0

            # Score 2: Optimal length (5-12 words)
            if 5 <= word_count <= 12:
                length_score = 2
            elif 3 <= word_count <= 15:
                length_score = 1
            else:
                length_score = 0

            # Score 3: Contains actionable keywords
            action_score = sum(1 for kw in self.ACTION_KEYWORDS if kw in text_lower)

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


class SemanticAnalyzer:
    """
    Semantic analysis and clustering of corrections.

    Uses TF-IDF similarity with threshold-based clustering.
    Target: 60%+ compression ratio (10 corrections → 4 clusters).
    """

    def __init__(
        self,
        similarity_threshold: float = 0.45,
        use_llm: bool = False
    ):
        """
        Args:
            similarity_threshold: Minimum similarity to group corrections (default: 0.45)
                                 Lower threshold for short correction phrases
            use_llm: Enable optional LLM refinement for canonical extraction
        """
        self.similarity_engine = SimilarityEngine()
        self.canonical_extractor = CanonicalExtractor(use_llm=use_llm)
        self.similarity_threshold = similarity_threshold

    def cluster_corrections(self, candidates: List) -> AnalyzedCorrections:
        """
        Cluster corrections and extract canonical forms.

        Args:
            candidates: List of CorrectionCandidate from Phase 1

        Returns:
            AnalyzedCorrections with clusters and statistics
        """
        if not candidates:
            return AnalyzedCorrections(
                clusters=[],
                outliers=[],
                total_raw=0,
                total_clustered=0,
                compression_ratio=0.0
            )

        # Extract messages
        messages = [c.user_message for c in candidates]

        # Compute similarity matrix
        similarity_matrix = self.similarity_engine.compute_similarity_matrix(messages)

        # Cluster using threshold-based grouping
        cluster_indices = self._threshold_clustering(similarity_matrix)

        # Extract canonical form for each cluster
        canonical_clusters = [
            self._extract_canonical(indices, candidates)
            for indices in cluster_indices
        ]

        # Calculate compression ratio
        compression_ratio = (
            len(canonical_clusters) / len(candidates)
            if candidates else 0.0
        )

        return AnalyzedCorrections(
            clusters=canonical_clusters,
            outliers=[],  # All corrections are clustered
            total_raw=len(candidates),
            total_clustered=len(canonical_clusters),
            compression_ratio=compression_ratio
        )

    def _threshold_clustering(self, similarity_matrix: np.ndarray) -> List[List[int]]:
        """
        Cluster indices where similarity > threshold.

        Uses greedy clustering: each item joins the first cluster
        where similarity exceeds threshold.

        Args:
            similarity_matrix: Pairwise similarity matrix (n x n)

        Returns:
            List of clusters, where each cluster is a list of indices
        """
        n = similarity_matrix.shape[0]
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
        candidates: List
    ) -> CorrectionCluster:
        """
        Extract canonical form from cluster.

        Args:
            cluster_indices: Indices of candidates in this cluster
            candidates: All correction candidates

        Returns:
            CorrectionCluster with canonical form and metadata
        """
        variants = [candidates[i].user_message for i in cluster_indices]
        correction_types = [candidates[i].correction_type for i in cluster_indices]
        confidences = [candidates[i].confidence for i in cluster_indices]

        # Extract canonical using rule-based selection (+ optional LLM)
        canonical = self.canonical_extractor.extract(variants)

        # Use most common correction type
        correction_type = max(set(correction_types), key=correction_types.count)

        # Average confidence
        avg_confidence = sum(confidences) / len(confidences)

        return CorrectionCluster(
            canonical_text=canonical,
            variants=variants,
            correction_type=correction_type,
            frequency=len(variants),
            confidence=avg_confidence,
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )


# Module-level convenience functions

def cluster_corrections(
    candidates: List,
    similarity_threshold: float = 0.45,
    use_llm: bool = False
) -> AnalyzedCorrections:
    """
    Convenience function to cluster corrections.

    Args:
        candidates: List of CorrectionCandidate from Phase 1
        similarity_threshold: Minimum similarity to group (default: 0.45)
        use_llm: Enable optional LLM refinement

    Returns:
        AnalyzedCorrections with clusters and statistics
    """
    analyzer = SemanticAnalyzer(
        similarity_threshold=similarity_threshold,
        use_llm=use_llm
    )
    return analyzer.cluster_corrections(candidates)


def create_test_data():
    """
    Create test data for validation.

    Returns:
        List of test scenarios with expected cluster counts
    """
    return [
        # Scenario 1: Clear duplicates (should cluster to 1)
        {
            "corrections": [
                "keep summaries short",
                "be concise in summaries",
                "summaries should be brief"
            ],
            "expected_clusters": 1,
            "description": "Clear semantic duplicates"
        },

        # Scenario 2: Different topics (should NOT cluster)
        {
            "corrections": [
                "keep summaries short",
                "never exceed 200 lines"
            ],
            "expected_clusters": 2,
            "description": "Different topics, low similarity"
        },

        # Scenario 3: Mixed clustering
        {
            "corrections": [
                "keep code concise",
                "write concise code",
                "never use global variables",
                "avoid globals",
                "add error handling",
                "handle errors properly"
            ],
            "expected_clusters": 3,  # 2 for concise, 2 for globals, 2 for errors
            "description": "Multiple topic clusters"
        },
    ]
