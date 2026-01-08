"""
BM25 keyword search implementation.

Okapi BM25 algorithm for ranking documents by keyword relevance.
"""

import math
import re
from typing import List, Dict, Set
from collections import Counter
from loguru import logger

from ..schemas import CodeSymbol, SearchResult, CodeSnippet
from .config import BM25_CONFIG


# Tokenization regex (same as semantic search for consistency)
WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str) -> List[str]:
    """
    Tokenize text into words.

    Args:
        text: Text to tokenize

    Returns:
        List of lowercase tokens
    """
    return [m.group(0).lower() for m in WORD_RE.finditer(text)]


class BM25Index:
    """
    BM25 index for keyword search.
    """

    def __init__(
        self,
        documents: List[Dict],  # List of {symbol, snippet_text}
        k1: float = 1.5,
        b: float = 0.75,
    ):
        """
        Initialize BM25 index.

        Args:
            documents: List of documents to index
            k1: Term frequency saturation parameter
            b: Length normalization parameter
        """
        self.documents = documents
        self.k1 = k1
        self.b = b

        # Build index
        self.doc_count = len(documents)
        self.doc_lengths: List[int] = []
        self.doc_tokens: List[List[str]] = []
        self.term_doc_freq: Dict[str, int] = Counter()  # Term -> number of docs containing it
        self.idf_cache: Dict[str, float] = {}

        # Index documents
        total_length = 0
        for doc in documents:
            tokens = tokenize(doc["snippet_text"])
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))
            total_length += len(tokens)

            # Track term document frequency
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.term_doc_freq[token] += 1

        # Average document length
        self.avg_doc_length = total_length / self.doc_count if self.doc_count > 0 else 0

        # Precompute IDF scores
        for term, doc_freq in self.term_doc_freq.items():
            self.idf_cache[term] = self._compute_idf(doc_freq)

        logger.debug(
            f"BM25 index built: {self.doc_count} docs, "
            f"{len(self.term_doc_freq)} unique terms, "
            f"avg doc length: {self.avg_doc_length:.1f}"
        )

    def _compute_idf(self, doc_freq: int) -> float:
        """
        Compute IDF (Inverse Document Frequency) for a term.

        IDF = log((N - df + 0.5) / (df + 0.5) + 1)

        where N = total documents, df = documents containing term

        Args:
            doc_freq: Number of documents containing the term

        Returns:
            IDF score
        """
        numerator = self.doc_count - doc_freq + 0.5
        denominator = doc_freq + 0.5
        return math.log((numerator / denominator) + 1.0)

    def _compute_term_score(self, term: str, doc_idx: int) -> float:
        """
        Compute BM25 score for a term in a document.

        Score = IDF * (TF * (k1 + 1)) / (TF + k1 * (1 - b + b * (DL / avgDL)))

        where:
        - IDF = inverse document frequency
        - TF = term frequency in document
        - DL = document length
        - avgDL = average document length
        - k1, b = tuning parameters

        Args:
            term: Search term
            doc_idx: Document index

        Returns:
            BM25 score for term in document
        """
        # Get IDF (precomputed)
        if term not in self.idf_cache:
            return 0.0

        idf = self.idf_cache[term]

        # Get term frequency in document
        doc_tokens = self.doc_tokens[doc_idx]
        tf = doc_tokens.count(term)

        if tf == 0:
            return 0.0

        # Get document length
        doc_length = self.doc_lengths[doc_idx]

        # Compute length normalization
        length_norm = 1 - self.b + self.b * (doc_length / self.avg_doc_length)

        # Compute BM25 score
        numerator = tf * (self.k1 + 1)
        denominator = tf + self.k1 * length_norm
        score = idf * (numerator / denominator)

        return score

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Search using BM25.

        Args:
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of SearchResult objects sorted by score
        """
        # Tokenize query
        query_tokens = tokenize(query)

        if not query_tokens:
            logger.debug("Empty query after tokenization")
            return []

        # Score each document
        scores: List[tuple] = []  # (score, doc_idx)

        for doc_idx in range(self.doc_count):
            doc_score = 0.0

            # Sum BM25 scores for each query term
            for term in query_tokens:
                doc_score += self._compute_term_score(term, doc_idx)

            if doc_score > 0:
                scores.append((doc_score, doc_idx))

        # Sort by score (descending)
        scores.sort(reverse=True, key=lambda x: x[0])

        # Get top K results
        results: List[SearchResult] = []
        for score, doc_idx in scores[:top_k]:
            doc = self.documents[doc_idx]
            symbol = doc["symbol"]

            # Create code snippet
            snippet = CodeSnippet(
                file_path=symbol.file_path,
                start_line=symbol.start_line,
                end_line=symbol.end_line,
                content=doc["snippet_text"],
            )

            # Normalize score to 0-1 range (approximately)
            # BM25 scores can theoretically be unbounded, but typically < 100
            # We'll use a soft normalization
            normalized_score = min(score / 10.0, 1.0)

            result = SearchResult(
                symbol=symbol,
                score=normalized_score,
                snippet=snippet,
            )
            results.append(result)

        logger.info(f"BM25 search for '{query}' returned {len(results)} results")

        return results
