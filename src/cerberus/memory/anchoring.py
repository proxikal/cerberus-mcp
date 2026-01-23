"""
Phase 14: Dynamic Anchoring

Links abstract rules to concrete code examples for precise pattern replication.

Zero token cost for anchor discovery (uses Cerberus index).
"""

import math
import json
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime

# External dependencies
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Language file extensions
LANGUAGE_EXTENSIONS = {
    "python": "py",
    "javascript": "js",
    "typescript": "ts",
    "go": "go",
    "rust": "rs",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "csharp": "cs",
    "ruby": "rb",
    "php": "php",
    "swift": "swift",
    "kotlin": "kt",
}


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
class AnchoredMemory:
    """Memory with code example anchor."""
    memory_id: str
    content: str  # Abstract rule
    anchor_file: Optional[str]  # Example file path
    anchor_symbol: Optional[str]  # Symbol name
    anchor_score: float  # Quality score (0.0-1.0)
    anchor_metadata: Dict[str, Any] = field(default_factory=dict)


class AnchorEngine:
    """
    Finds and manages code anchors for memories.

    Uses Cerberus code index to discover concrete code examples
    that illustrate abstract rules.
    """

    def __init__(self, project_path: Optional[Path] = None):
        """
        Args:
            project_path: Optional project root directory
        """
        self.project_path = project_path or Path.cwd()

    def find_anchor(
        self,
        rule: str,
        scope: str,
        language: Optional[str] = None,
        project_path: Optional[Path] = None,
        min_quality: float = 0.7
    ) -> Optional[AnchorCandidate]:
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
            project_path: Project directory
            min_quality: Minimum quality threshold (0.0-1.0, default 0.7)

        Returns:
            AnchorCandidate if found, None otherwise
        """
        # Universal scope - no anchoring
        if scope == "universal":
            return None

        # Extract keywords from rule
        keywords = self._extract_keywords(rule)
        if not keywords:
            return None

        # Determine search scope
        search_path = project_path or self.project_path

        # Collect candidates
        candidates = self._search_code(keywords, search_path, language)

        if not candidates:
            return None

        # Score candidates
        scored = []
        for candidate in candidates:
            try:
                # Relevance: TF-IDF similarity between rule and file content
                relevance = self._calculate_relevance(rule, candidate['file_path'])

                # Size penalty: Prefer concise examples (< 500 lines)
                file_size = candidate.get('file_size', self._get_file_size(candidate['file_path']))
                size_score = 1.0 - (min(file_size, 500) / 500)

                # Recency: Prefer recently modified files
                recency = self._calculate_recency(candidate['file_path'])

                # Combined score: weighted average
                quality = (
                    0.6 * relevance +
                    0.2 * size_score +
                    0.2 * recency
                )

                if quality >= min_quality:
                    scored.append(AnchorCandidate(
                        file_path=candidate['file_path'],
                        symbol_name=candidate.get('name'),
                        match_score=relevance,
                        file_size=file_size,
                        recency_score=recency,
                        quality_score=quality
                    ))
            except Exception:
                # Skip candidates that fail scoring
                continue

        # Return best match
        if scored:
            return max(scored, key=lambda c: c.quality_score)
        return None

    def _extract_keywords(self, rule: str) -> List[str]:
        """
        Extract meaningful keywords from rule text.

        Examples:
            "Use Repository pattern" → ["repository", "pattern"]
            "Always validate input" → ["validate", "input"]
            "Prefer async/await" → ["async", "await"]
        """
        # Common stopwords
        stopwords = {
            "use", "always", "never", "prefer", "avoid", "the", "a", "an",
            "in", "on", "for", "with", "should", "must", "can", "will",
            "be", "to", "of", "and", "or", "is", "are", "was", "were"
        }

        # Tokenize: split on whitespace and forward slash
        text = rule.lower().replace("/", " ")
        tokens = text.split()
        keywords = [t for t in tokens if t not in stopwords and len(t) > 2]

        return keywords[:5]  # Limit to top 5 keywords

    def _search_code(
        self,
        keywords: List[str],
        search_path: Path,
        language: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Search code index for matching files/symbols.

        Uses Cerberus index manager for efficient search.
        """
        candidates = []

        try:
            # Import here to avoid circular dependency
            from cerberus.mcp.index_manager import get_index_manager
            from cerberus.retrieval import hybrid_search

            manager = get_index_manager()
            index_path = manager._index_path or manager._discover_index_path()

            if not index_path:
                return []

            # Search for each keyword
            for keyword in keywords:
                results = hybrid_search(
                    query=keyword,
                    index_path=index_path,
                    mode="keyword",  # Use keyword mode for anchoring
                    top_k=10
                )

                for result in results:
                    candidate = {
                        'file_path': result.symbol.file_path,
                        'name': result.symbol.name,
                        'type': result.symbol.type,
                        'start_line': result.symbol.start_line,
                        'end_line': result.symbol.end_line,
                        'score': result.hybrid_score
                    }

                    # Filter by language if specified
                    if language:
                        ext = LANGUAGE_EXTENSIONS.get(language)
                        if ext and not candidate['file_path'].endswith(f".{ext}"):
                            continue

                    candidates.append(candidate)

        except Exception:
            # Fallback: glob search if Cerberus index unavailable
            return []

        # Deduplicate by file path
        seen = set()
        unique_candidates = []
        for candidate in candidates:
            if candidate['file_path'] not in seen:
                seen.add(candidate['file_path'])
                unique_candidates.append(candidate)

        return unique_candidates[:20]  # Limit to top 20

    def _calculate_relevance(self, rule: str, file_path: str) -> float:
        """
        TF-IDF similarity between rule and file content.

        Uses scikit-learn TfidfVectorizer (same as Phase 2).
        """
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_content = f.read()

            # Limit file content to first 5000 chars for efficiency
            file_content = file_content[:5000]

            # Vectorize
            vectorizer = TfidfVectorizer(max_features=100)
            vectors = vectorizer.fit_transform([rule, file_content])

            # Cosine similarity
            similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]

            return similarity

        except Exception:
            return 0.0

    def _calculate_recency(self, file_path: str) -> float:
        """
        Recency score based on last modification time.

        Recently modified files are better examples (more likely current patterns).

        Uses exponential decay: 1.0 at 0 days, 0.5 at 30 days, 0.1 at 180 days
        """
        try:
            mtime = os.path.getmtime(file_path)
            modified = datetime.fromtimestamp(mtime)
            age_days = (datetime.now() - modified).days

            # Exponential decay
            decay_rate = 0.023  # ln(0.5) / 30
            recency = math.exp(-decay_rate * age_days)

            return recency

        except Exception:
            return 0.5  # Default middle score

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in lines of code."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return sum(1 for _ in f)
        except Exception:
            return 100  # Default estimate

    def anchor_memory(
        self,
        memory_id: str,
        content: str,
        scope: str
    ) -> Optional[AnchorCandidate]:
        """
        Find and return anchor for a memory.

        Args:
            memory_id: Memory ID
            content: Rule text
            scope: Memory scope

        Returns:
            AnchorCandidate if found, None otherwise
        """
        # Extract scope details
        language = None
        project_path = None

        if scope.startswith("language:"):
            language = scope.split(":", 1)[1]
        elif scope.startswith("project:"):
            # Extract project name (could be path or name)
            project_name = scope.split(":", 1)[1]
            # Try to use as path if it exists
            possible_path = Path(project_name)
            if possible_path.exists():
                project_path = possible_path

        # Find anchor
        return self.find_anchor(
            rule=content,
            scope=scope,
            language=language,
            project_path=project_path
        )

    def read_anchor_code(
        self,
        file_path: str,
        symbol_name: Optional[str] = None,
        max_lines: int = 30
    ) -> str:
        """
        Read code snippet from anchor file.

        Strategy:
        1. If symbol_name provided: Extract symbol definition (if possible)
        2. Otherwise: Read first N lines of file
        3. Limit to max_lines

        Args:
            file_path: Path to anchor file
            symbol_name: Optional symbol name to extract
            max_lines: Maximum lines to include

        Returns:
            Code snippet as string
        """
        try:
            # Read file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # If symbol_name provided, try to find it
            if symbol_name:
                # Simple heuristic: find line with symbol definition
                for i, line in enumerate(lines):
                    if symbol_name in line and any(kw in line for kw in ['def ', 'function ', 'class ', 'type ', 'interface ', 'func ']):
                        # Extract from this line forward
                        snippet_lines = lines[i:min(i + max_lines, len(lines))]
                        return ''.join(snippet_lines)

            # Fallback: return first max_lines
            snippet_lines = lines[:max_lines]
            return ''.join(snippet_lines)

        except Exception:
            return f"// Could not read file: {file_path}"


def extract_language_from_scope(scope: str) -> Optional[str]:
    """Extract language from scope string."""
    if scope.startswith("language:"):
        return scope.split(":", 1)[1]
    return None


def extract_project_from_scope(scope: str) -> Optional[str]:
    """Extract project from scope string."""
    if scope.startswith("project:"):
        return scope.split(":", 1)[1]
    return None
