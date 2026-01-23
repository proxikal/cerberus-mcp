"""
PHASE 11: MAINTENANCE & HEALTH

Auto-maintain memory health: archive stale rules, detect conflicts, promote patterns.

Zero token cost (fully offline).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
import json
import uuid

from .semantic_analyzer import SemanticAnalyzer


@dataclass
class MemoryHealth:
    """Overall memory system health metrics."""
    total_memories: int
    stale_count: int  # Not used in 60+ days
    conflict_count: int
    promotion_candidates: int
    last_health_check: datetime
    status: str  # "healthy", "needs_attention", "critical"


@dataclass
class ConflictDetection:
    """Detected conflict between two memories."""
    id: str
    memory1: Dict
    memory2: Dict
    conflict_type: str  # "contradiction", "redundancy", "obsolete"
    severity: str  # "low", "medium", "high"
    suggestion: str


@dataclass
class PromotionCandidate:
    """Memory that should be promoted to higher scope."""
    memory: Dict
    current_scope: str
    suggested_scope: str
    confidence: float
    reason: str


class StaleMemoryDetector:
    """
    Detect and archive memories not used recently.

    Thresholds:
    - Stale: 60+ days unused (flagged but not archived)
    - Archive: 180+ days unused (moved to archive)
    """

    STALE_THRESHOLD_DAYS = 60
    ARCHIVE_THRESHOLD_DAYS = 180

    def __init__(self, base_path: Path):
        """
        Initialize stale memory detector.

        Args:
            base_path: Base directory for memory storage (e.g., ~/.cerberus/memory)
        """
        self.base_path = base_path

    def detect_stale(self) -> List[Dict]:
        """
        Find memories not violated/referenced in 60+ days.

        Returns:
            List of dicts with keys: memory, days_stale, should_archive
        """
        all_memories = self._load_all_memories()
        stale = []

        for mem in all_memories:
            last_used = self._get_last_used(mem)

            if last_used:
                days_ago = (datetime.now() - last_used).days

                if days_ago > self.STALE_THRESHOLD_DAYS:
                    stale.append({
                        "memory": mem,
                        "days_stale": days_ago,
                        "should_archive": days_ago > self.ARCHIVE_THRESHOLD_DAYS
                    })

        return stale

    def _load_all_memories(self) -> List[Dict]:
        """Load all memories from JSON storage."""
        memories = []

        # Universal memories
        for filename in ["profile.json", "corrections.json"]:
            file_path = self.base_path / filename
            if file_path.exists():
                with open(file_path) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        memories.extend(data)

        # Language memories
        lang_dir = self.base_path / "languages"
        if lang_dir.exists():
            for lang_file in lang_dir.glob("*.json"):
                with open(lang_file) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        memories.extend(data)

        # Project memories
        proj_dir = self.base_path / "projects"
        if proj_dir.exists():
            for proj_path in proj_dir.iterdir():
                if proj_path.is_dir():
                    decisions_file = proj_path / "decisions.json"
                    if decisions_file.exists():
                        with open(decisions_file) as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                memories.extend(data)

        return memories

    def _get_last_used(self, memory: Dict) -> Optional[datetime]:
        """
        Get last usage timestamp.

        Rules:
        - Corrections: last_occurred (if present)
        - Decisions: timestamp
        - Preferences: Always active (return now)
        """
        category = memory.get("category", "")

        if category == "correction":
            last_occ = memory.get("last_occurred")
            if last_occ:
                return datetime.fromisoformat(last_occ)

        if category == "decision":
            timestamp = memory.get("timestamp")
            if timestamp:
                return datetime.fromisoformat(timestamp)

        # Preferences are always active (never stale)
        return datetime.now()

    def archive_stale(self, stale_memories: List[Dict]) -> int:
        """
        Move stale memories to archive (don't delete).

        Args:
            stale_memories: List of dicts from detect_stale()

        Returns:
            Count of archived memories
        """
        archive_dir = self.base_path / "archive"
        archive_dir.mkdir(exist_ok=True)

        archive_file = archive_dir / f"archived-{datetime.now().strftime('%Y%m%d')}.json"

        archived = []
        for item in stale_memories:
            if item["should_archive"]:
                archived.append(item["memory"])
                # Remove from active storage
                self._remove_from_active(item["memory"])

        # Save to archive
        if archived:
            with open(archive_file, "w") as f:
                json.dump(archived, f, indent=2, default=str)

        return len(archived)

    def _remove_from_active(self, memory: Dict):
        """
        Remove memory from active storage.

        Implementation depends on category and scope.
        """
        scope = memory.get("scope", "universal")
        category = memory.get("category", "")
        mem_id = memory.get("id")

        # Determine target file
        target_file = None

        if scope == "universal":
            if category == "correction":
                target_file = self.base_path / "corrections.json"
            else:
                target_file = self.base_path / "profile.json"
        elif scope.startswith("language:"):
            lang = scope.split(":")[1]
            target_file = self.base_path / "languages" / f"{lang}.json"
        elif scope.startswith("project:"):
            project = scope.split(":")[1]
            target_file = self.base_path / "projects" / project / "decisions.json"

        if not target_file or not target_file.exists():
            return

        # Load, filter, save
        with open(target_file) as f:
            data = json.load(f)

        if isinstance(data, list):
            data = [m for m in data if m.get("id") != mem_id]
            with open(target_file, "w") as f:
                json.dump(data, f, indent=2, default=str)


class ConflictDetector:
    """
    Detect contradictions and redundancies in memory.

    Types:
    - Contradiction: "Always X" vs "Never X"
    - Redundancy: Duplicate or near-duplicate (85%+ similar)
    - Obsolete: References deprecated tools/patterns
    """

    def __init__(self, base_path: Path):
        """
        Initialize conflict detector.

        Args:
            base_path: Base directory for memory storage
        """
        self.base_path = base_path
        self.semantic_analyzer = SemanticAnalyzer(similarity_threshold=0.85)

    def detect_conflicts(self) -> List[ConflictDetection]:
        """
        Find conflicting memories.

        Returns:
            List of ConflictDetection objects
        """
        all_memories = self._load_all_memories()
        conflicts = []

        # Check for contradictions
        conflicts.extend(self._detect_contradictions(all_memories))

        # Check for redundancies
        conflicts.extend(self._detect_redundancies(all_memories))

        # Check for obsolete rules
        conflicts.extend(self._detect_obsolete(all_memories))

        return conflicts

    def _load_all_memories(self) -> List[Dict]:
        """Load all memories from JSON storage."""
        detector = StaleMemoryDetector(self.base_path)
        return detector._load_all_memories()

    def _detect_contradictions(self, memories: List[Dict]) -> List[ConflictDetection]:
        """
        Find memories that contradict each other.

        Example: "Always use X" vs "Never use X"
        """
        contradictions = []

        # Group by scope (only check within same scope)
        by_scope = {}
        for mem in memories:
            scope = mem.get("scope", "universal")
            if scope not in by_scope:
                by_scope[scope] = []
            by_scope[scope].append(mem)

        # Check each scope for contradictions
        for scope, scope_mems in by_scope.items():
            for i, mem1 in enumerate(scope_mems):
                for mem2 in scope_mems[i+1:]:
                    if self._is_contradiction(mem1.get("content", ""), mem2.get("content", "")):
                        contradictions.append(ConflictDetection(
                            id=f"conflict-{uuid.uuid4().hex[:8]}",
                            memory1=mem1,
                            memory2=mem2,
                            conflict_type="contradiction",
                            severity="high",
                            suggestion=f"Remove one: '{mem1.get('content', '')}' contradicts '{mem2.get('content', '')}'"
                        ))

        return contradictions

    def _is_contradiction(self, text1: str, text2: str) -> bool:
        """
        Detect if two statements contradict.

        Uses keyword matching + semantic similarity.
        """
        if not text1 or not text2:
            return False

        # Extract subject (rough heuristic)
        def extract_subject(text: str) -> str:
            import re
            text = text.lower()
            for starter in ["always", "never", "don't", "avoid", "use", "prefer"]:
                text = text.replace(starter, "").strip()
            tokens = text.split()
            if tokens:
                # Strip punctuation from first token
                return re.sub(r'[^\w]', '', tokens[0])
            return ""

        subject1 = extract_subject(text1)
        subject2 = extract_subject(text2)

        # Same subject?
        if not subject1 or not subject2 or subject1 != subject2:
            return False

        # Opposite directives?
        positive_words = {"always", "use", "prefer", "do", "must"}
        negative_words = {"never", "don't", "avoid", "not", "shouldn't"}

        text1_lower = text1.lower()
        text2_lower = text2.lower()

        has_pos1 = any(w in text1_lower for w in positive_words)
        has_neg1 = any(w in text1_lower for w in negative_words)

        has_pos2 = any(w in text2_lower for w in positive_words)
        has_neg2 = any(w in text2_lower for w in negative_words)

        # Contradiction if one positive, one negative
        return (has_pos1 and has_neg2) or (has_neg1 and has_pos2)

    def _detect_redundancies(self, memories: List[Dict]) -> List[ConflictDetection]:
        """
        Find duplicate or near-duplicate memories.

        Uses TF-IDF similarity from Phase 2.
        """
        redundancies = []

        # Group by scope
        by_scope = {}
        for mem in memories:
            scope = mem.get("scope", "universal")
            if scope not in by_scope:
                by_scope[scope] = []
            by_scope[scope].append(mem)

        # Check each scope for redundancies
        for scope, scope_mems in by_scope.items():
            if len(scope_mems) < 2:
                continue

            # Extract texts
            texts = [m.get("content", "") for m in scope_mems]

            # Compute similarity matrix
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(3, 5))
            try:
                tfidf = vectorizer.fit_transform(texts)
                similarity_matrix = cosine_similarity(tfidf)
            except ValueError:
                continue

            # Find redundancies
            for i in range(len(scope_mems)):
                for j in range(i + 1, len(scope_mems)):
                    similarity = similarity_matrix[i, j]

                    if similarity > 0.80:  # 80% similar = redundant
                        redundancies.append(ConflictDetection(
                            id=f"redundancy-{uuid.uuid4().hex[:8]}",
                            memory1=scope_mems[i],
                            memory2=scope_mems[j],
                            conflict_type="redundancy",
                            severity="low",
                            suggestion=f"Merge: '{scope_mems[i].get('content', '')}' and '{scope_mems[j].get('content', '')}' are {similarity*100:.0f}% similar"
                        ))

        return redundancies

    def _detect_obsolete(self, memories: List[Dict]) -> List[ConflictDetection]:
        """
        Find memories that reference deprecated tools/patterns.
        """
        obsolete = []

        # Deprecated keywords
        deprecated = [
            "python2",
            "jquery",
            "bower",
            "gulp",
            "coffeescript",
            "angularjs",
        ]

        for mem in memories:
            content_lower = mem.get("content", "").lower()
            for dep in deprecated:
                if dep in content_lower:
                    obsolete.append(ConflictDetection(
                        id=f"obsolete-{uuid.uuid4().hex[:8]}",
                        memory1=mem,
                        memory2={},  # No second memory
                        conflict_type="obsolete",
                        severity="medium",
                        suggestion=f"Update: '{mem.get('content', '')}' references deprecated '{dep}'"
                    ))

        return obsolete


class PromotionDetector:
    """
    Detect patterns that should be promoted to higher scope.

    Rule: If a memory appears in 3+ projects, suggest promotion to universal or language scope.
    """

    def __init__(self, base_path: Path):
        """
        Initialize promotion detector.

        Args:
            base_path: Base directory for memory storage
        """
        self.base_path = base_path
        self.semantic_analyzer = SemanticAnalyzer(similarity_threshold=0.75)

    def detect_candidates(self) -> List[PromotionCandidate]:
        """
        Find memories that appear in multiple projects.

        Suggest promotion to universal or language scope.
        """
        candidates = []

        # Get all project memories
        all_projects = self._get_all_project_memories()

        if not all_projects:
            return []

        # Group by similarity
        clusters = self._cluster_similar(all_projects)

        # Detect patterns
        for cluster in clusters:
            if len(cluster["projects"]) >= 3:  # In 3+ projects
                # Suggest promotion
                scope = self._suggest_scope(cluster)
                candidates.append(PromotionCandidate(
                    memory=cluster["canonical"],
                    current_scope=cluster["projects"][0],
                    suggested_scope=scope,
                    confidence=min(len(cluster["projects"]) / 10.0, 1.0),  # Cap at 1.0
                    reason=f"Pattern found in {len(cluster['projects'])} projects"
                ))

        return candidates

    def _get_all_project_memories(self) -> List[Dict]:
        """Get all memories from all projects."""
        proj_dir = self.base_path / "projects"
        memories = []

        if not proj_dir.exists():
            return []

        for proj_path in proj_dir.iterdir():
            if proj_path.is_dir():
                decisions_file = proj_path / "decisions.json"
                if decisions_file.exists():
                    with open(decisions_file) as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            memories.extend(data)

        return memories

    def _cluster_similar(self, memories: List[Dict]) -> List[Dict]:
        """
        Cluster similar memories across projects.

        Returns:
            List of clusters with canonical form
        """
        if not memories:
            return []

        # Extract texts
        texts = [m.get("content", "") for m in memories]

        # Compute similarity matrix using TF-IDF
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(3, 5))
        try:
            tfidf = vectorizer.fit_transform(texts)
            similarity_matrix = cosine_similarity(tfidf)
        except ValueError:
            return []

        # Cluster (threshold = 0.75)
        clusters = []
        visited = set()

        for i in range(len(memories)):
            if i in visited:
                continue

            # Start cluster
            cluster_indices = [i]
            visited.add(i)

            for j in range(i + 1, len(memories)):
                if j not in visited and similarity_matrix[i, j] > 0.75:
                    cluster_indices.append(j)
                    visited.add(j)

            # Create cluster
            cluster_mems = [memories[idx] for idx in cluster_indices]
            projects = list(set(m.get("scope", "").split(":")[-1] for m in cluster_mems if m.get("scope", "").startswith("project:")))

            clusters.append({
                "canonical": cluster_mems[0],  # Use first as canonical
                "variants": cluster_mems,
                "projects": projects
            })

        return clusters

    def _suggest_scope(self, cluster: Dict) -> str:
        """
        Suggest promotion scope based on cluster content.

        Checks for language-specific keywords.
        """
        content = cluster["canonical"].get("content", "").lower()

        # Check for language keywords
        lang_keywords = {
            "go": ["panic", "goroutine", "defer", "golang"],
            "python": ["except", "import", "async", "pip"],
            "typescript": ["async", "interface", "type", "npm"],
            "rust": ["unsafe", "borrow", "lifetime", "cargo"],
            "javascript": ["promise", "callback", "node"],
        }

        for lang, keywords in lang_keywords.items():
            if any(kw in content for kw in keywords):
                return f"language:{lang}"

        # Otherwise universal
        return "universal"


class MemoryHealthCheck:
    """
    Comprehensive health check for memory system.

    Orchestrates:
    - Stale detection
    - Conflict detection
    - Promotion detection
    """

    def __init__(self, base_path: Path):
        """
        Initialize memory health check.

        Args:
            base_path: Base directory for memory storage
        """
        self.base_path = base_path
        self.stale_detector = StaleMemoryDetector(base_path)
        self.conflict_detector = ConflictDetector(base_path)
        self.promotion_detector = PromotionDetector(base_path)

    def run_health_check(self) -> MemoryHealth:
        """
        Run full health check and return report.

        Status levels:
        - healthy: < 5 conflicts, < 30% stale
        - needs_attention: 5-20 conflicts OR 30-50% stale
        - critical: > 20 conflicts OR > 50% stale
        """
        # Count total memories
        all_memories = self.stale_detector._load_all_memories()
        total = len(all_memories)

        # Detect issues
        stale = self.stale_detector.detect_stale()
        conflicts = self.conflict_detector.detect_conflicts()
        promotions = self.promotion_detector.detect_candidates()

        # Determine status
        status = "healthy"
        if len(conflicts) > 5 or (total > 0 and len(stale) > total * 0.3):
            status = "needs_attention"
        if len(conflicts) > 20 or (total > 0 and len(stale) > total * 0.5):
            status = "critical"

        return MemoryHealth(
            total_memories=total,
            stale_count=len(stale),
            conflict_count=len(conflicts),
            promotion_candidates=len(promotions),
            last_health_check=datetime.now(),
            status=status
        )

    def auto_maintain(self, approve_promotions: bool = False) -> Dict[str, int]:
        """
        Automatic maintenance.

        Actions:
        - Archive stale memories (>180 days)
        - Report conflicts (don't auto-fix)
        - Optionally promote patterns

        Args:
            approve_promotions: If True, auto-promote high confidence patterns

        Returns:
            Dict with counts: archived, conflicts, promotions
        """
        results = {
            "archived": 0,
            "conflicts": 0,
            "promotions": 0
        }

        # Archive stale
        stale = self.stale_detector.detect_stale()
        archived_count = self.stale_detector.archive_stale(stale)
        results["archived"] = archived_count

        # Count conflicts (don't auto-fix)
        conflicts = self.conflict_detector.detect_conflicts()
        results["conflicts"] = len(conflicts)

        # Promotion
        if approve_promotions:
            promotions = self.promotion_detector.detect_candidates()
            for prom in promotions:
                if prom.confidence > 0.5:
                    self._promote(prom)
                    results["promotions"] += 1

        return results

    def _promote(self, candidate: PromotionCandidate):
        """
        Execute promotion.

        Writes memory to new scope file.
        """
        scope = candidate.suggested_scope
        memory = candidate.memory

        # Determine target file
        target_file = None

        if scope == "universal":
            category = memory.get("category", "")
            if category == "correction":
                target_file = self.base_path / "corrections.json"
            else:
                target_file = self.base_path / "profile.json"
        elif scope.startswith("language:"):
            lang = scope.split(":")[1]
            lang_dir = self.base_path / "languages"
            lang_dir.mkdir(exist_ok=True)
            target_file = lang_dir / f"{lang}.json"

        if not target_file:
            return

        # Load existing
        if target_file.exists():
            with open(target_file) as f:
                data = json.load(f)
        else:
            data = []

        # Update scope
        promoted_mem = memory.copy()
        promoted_mem["scope"] = scope

        # Add to target
        data.append(promoted_mem)

        # Save
        with open(target_file, "w") as f:
            json.dump(data, f, indent=2, default=str)


def scheduled_maintenance(base_path: Path = None, approve_promotions: bool = False) -> MemoryHealth:
    """
    Run weekly maintenance (cron job or session-based).

    Args:
        base_path: Base directory for memory storage (default: ~/.cerberus/memory)
        approve_promotions: If True, auto-promote high confidence patterns

    Returns:
        MemoryHealth report
    """
    if base_path is None:
        base_path = Path.home() / ".cerberus" / "memory"

    health_check = MemoryHealthCheck(base_path)

    # Run check
    health = health_check.run_health_check()

    # Auto-maintain if not healthy
    if health.status != "healthy":
        health_check.auto_maintain(approve_promotions=approve_promotions)

    return health
