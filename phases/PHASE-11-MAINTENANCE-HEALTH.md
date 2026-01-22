# PHASE 6: MAINTENANCE & HEALTH

## Objective
Auto-maintain memory health: archive stale rules, detect conflicts, promote patterns.

---

## Implementation Location

**File:** `src/cerberus/memory/maintenance.py`

---

## Data Structures

```python
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
```

---

## Stale Memory Detection

```python
class StaleMemoryDetector:
    """
    Detect and archive memories not used recently.
    """

    STALE_THRESHOLD_DAYS = 60
    ARCHIVE_THRESHOLD_DAYS = 180

    def __init__(self, hierarchy: MemoryHierarchy):
        self.hierarchy = hierarchy

    def detect_stale(self) -> List[Dict]:
        """
        Find memories not violated/referenced in 60+ days.
        """
        all_memories = self.hierarchy.retrieve()
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

    def _get_last_used(self, memory: Dict) -> Optional[datetime]:
        """
        Get last usage timestamp.
        For corrections: last_occurred
        For decisions: timestamp
        For preferences: None (always active)
        """
        if memory["category"] == "correction":
            last_occ = memory.get("last_occurred")
            if last_occ:
                return datetime.fromisoformat(last_occ)

        if memory["category"] == "decision":
            timestamp = memory.get("timestamp")
            if timestamp:
                return datetime.fromisoformat(timestamp)

        # Preferences are always active (never stale)
        return datetime.now()

    def archive_stale(self, stale_memories: List[Dict]):
        """
        Move stale memories to archive (don't delete).
        """
        archive_dir = self.hierarchy.base_path / "archive"
        archive_dir.mkdir(exist_ok=True)

        archive_file = archive_dir / f"archived-{datetime.now().strftime('%Y%m%d')}.json"

        archived = []
        for item in stale_memories:
            if item["should_archive"]:
                archived.append(item["memory"])
                # Remove from active storage
                self._remove_from_active(item["memory"])

        # Save to archive
        with open(archive_file, "w") as f:
            json.dump(archived, f, indent=2, default=str)

    def _remove_from_active(self, memory: Dict):
        """
        Remove memory from active storage.
        Implementation depends on category and scope.
        """
        # Stub: Implement removal based on scope
        pass
```

---

## Conflict Detection

```python
class ConflictDetector:
    """
    Detect contradictions and redundancies in memory.
    """

    def __init__(self, hierarchy: MemoryHierarchy):
        self.hierarchy = hierarchy
        self.embedder = EmbeddingEngine()  # From Phase 2

    def detect_conflicts(self) -> List[ConflictDetection]:
        """
        Find conflicting memories.
        """
        all_memories = self.hierarchy.retrieve()
        conflicts = []

        # Check for contradictions
        conflicts.extend(self._detect_contradictions(all_memories))

        # Check for redundancies
        conflicts.extend(self._detect_redundancies(all_memories))

        # Check for obsolete rules
        conflicts.extend(self._detect_obsolete(all_memories))

        return conflicts

    def _detect_contradictions(self, memories: List[Dict]) -> List[ConflictDetection]:
        """
        Find memories that contradict each other.
        Example: "Always use X" vs "Never use X"
        """
        contradictions = []

        # Group by scope (only check within same scope)
        by_scope = {}
        for mem in memories:
            scope = mem["scope"]
            if scope not in by_scope:
                by_scope[scope] = []
            by_scope[scope].append(mem)

        # Check each scope for contradictions
        for scope, scope_mems in by_scope.items():
            for i, mem1 in enumerate(scope_mems):
                for mem2 in scope_mems[i+1:]:
                    if self._is_contradiction(mem1["content"], mem2["content"]):
                        contradictions.append(ConflictDetection(
                            id=f"conflict-{uuid.uuid4().hex[:8]}",
                            memory1=mem1,
                            memory2=mem2,
                            conflict_type="contradiction",
                            severity="high",
                            suggestion=f"Remove one: '{mem1['content']}' contradicts '{mem2['content']}'"
                        ))

        return contradictions

    def _is_contradiction(self, text1: str, text2: str) -> bool:
        """
        Detect if two statements contradict.
        Uses keyword matching + semantic similarity.
        """
        # Extract subject (rough heuristic)
        def extract_subject(text: str) -> str:
            # Remove common starters
            text = text.lower()
            for starter in ["always", "never", "don't", "avoid", "use"]:
                text = text.replace(starter, "").strip()
            return text.split()[0] if text else ""

        subject1 = extract_subject(text1)
        subject2 = extract_subject(text2)

        # Same subject?
        if subject1 != subject2:
            return False

        # Opposite directives?
        positive_words = {"always", "use", "prefer", "do"}
        negative_words = {"never", "don't", "avoid", "not"}

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
        """
        redundancies = []

        # Group by scope
        by_scope = {}
        for mem in memories:
            scope = mem["scope"]
            if scope not in by_scope:
                by_scope[scope] = []
            by_scope[scope].append(mem)

        # Check each scope for redundancies
        for scope, scope_mems in by_scope.items():
            for i, mem1 in enumerate(scope_mems):
                for mem2 in scope_mems[i+1:]:
                    similarity = self.embedder.similarity(
                        mem1["content"],
                        mem2["content"]
                    )

                    if similarity > 0.85:  # 85% similar = redundant
                        redundancies.append(ConflictDetection(
                            id=f"redundancy-{uuid.uuid4().hex[:8]}",
                            memory1=mem1,
                            memory2=mem2,
                            conflict_type="redundancy",
                            severity="low",
                            suggestion=f"Merge: '{mem1['content']}' and '{mem2['content']}' are {similarity*100:.0f}% similar"
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
            # Add more as needed
        ]

        for mem in memories:
            content_lower = mem["content"].lower()
            for dep in deprecated:
                if dep in content_lower:
                    obsolete.append(ConflictDetection(
                        id=f"obsolete-{uuid.uuid4().hex[:8]}",
                        memory1=mem,
                        memory2={},  # No second memory
                        conflict_type="obsolete",
                        severity="medium",
                        suggestion=f"Update: '{mem['content']}' references deprecated '{dep}'"
                    ))

        return obsolete
```

---

## Cross-Project Promotion

```python
class PromotionDetector:
    """
    Detect patterns that should be promoted to higher scope.
    """

    def __init__(self, hierarchy: MemoryHierarchy):
        self.hierarchy = hierarchy

    def detect_candidates(self) -> List[PromotionCandidate]:
        """
        Find memories that appear in multiple projects.
        Suggest promotion to universal or language scope.
        """
        candidates = []

        # Get all project memories
        all_projects = self._get_all_project_memories()

        # Group by similarity
        clusters = self._cluster_similar(all_projects)

        # Detect patterns
        for cluster in clusters:
            if len(cluster["projects"]) >= 3:  # In 3+ projects
                # Suggest promotion
                scope = self._suggest_scope(cluster)
                candidates.append(PromotionCandidate(
                    memory=cluster["canonical"],
                    current_scope=cluster["projects"][0]["scope"],
                    suggested_scope=scope,
                    confidence=len(cluster["projects"]) / 10.0,  # More projects = higher confidence
                    reason=f"Pattern found in {len(cluster['projects'])} projects"
                ))

        return candidates

    def _get_all_project_memories(self) -> List[Dict]:
        """Get all memories from all projects."""
        proj_dir = self.hierarchy.base_path / "projects"
        memories = []

        if not proj_dir.exists():
            return []

        for proj_path in proj_dir.iterdir():
            if proj_path.is_dir():
                project = proj_path.name
                memories.extend(
                    self.hierarchy.retrieve(scope=f"project:{project}")
                )

        return memories

    def _cluster_similar(self, memories: List[Dict]) -> List[Dict]:
        """
        Cluster similar memories across projects.
        Returns list of clusters with canonical form.
        """
        if not memories:
            return []

        embedder = EmbeddingEngine()

        # Compute embeddings
        texts = [m["content"] for m in memories]
        embeddings = np.array([embedder.embed(t) for t in texts])

        # Compute similarity matrix
        similarity_matrix = embeddings @ embeddings.T

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
            projects = list(set(m["scope"] for m in cluster_mems))

            clusters.append({
                "canonical": cluster_mems[0],  # Use first as canonical
                "variants": cluster_mems,
                "projects": [{"scope": p} for p in projects]
            })

        return clusters

    def _suggest_scope(self, cluster: Dict) -> str:
        """
        Suggest promotion scope based on cluster content.
        """
        content = cluster["canonical"]["content"].lower()

        # Check for language keywords
        lang_keywords = {
            "go": ["panic", "goroutine", "defer"],
            "python": ["except", "import", "async"],
            "typescript": ["async", "interface", "type"],
            "rust": ["unsafe", "borrow", "lifetime"]
        }

        for lang, keywords in lang_keywords.items():
            if any(kw in content for kw in keywords):
                return f"language:{lang}"

        # Otherwise universal
        return "universal"
```

---

## Health Check System

```python
class MemoryHealthCheck:
    """
    Comprehensive health check for memory system.
    """

    def __init__(self, hierarchy: MemoryHierarchy):
        self.hierarchy = hierarchy
        self.stale_detector = StaleMemoryDetector(hierarchy)
        self.conflict_detector = ConflictDetector(hierarchy)
        self.promotion_detector = PromotionDetector(hierarchy)

    def run_health_check(self) -> MemoryHealth:
        """
        Run full health check and return report.
        """
        # Count total memories
        all_memories = self.hierarchy.retrieve()
        total = len(all_memories)

        # Detect issues
        stale = self.stale_detector.detect_stale()
        conflicts = self.conflict_detector.detect_conflicts()
        promotions = self.promotion_detector.detect_candidates()

        # Determine status
        status = "healthy"
        if len(conflicts) > 5 or len(stale) > total * 0.3:
            status = "needs_attention"
        if len(conflicts) > 20 or len(stale) > total * 0.5:
            status = "critical"

        return MemoryHealth(
            total_memories=total,
            stale_count=len(stale),
            conflict_count=len(conflicts),
            promotion_candidates=len(promotions),
            last_health_check=datetime.now(),
            status=status
        )

    def auto_maintain(self, approve_promotions: bool = False):
        """
        Automatic maintenance:
        - Archive stale memories (>180 days)
        - Report conflicts (don't auto-fix)
        - Optionally promote patterns
        """
        # Archive stale
        stale = self.stale_detector.detect_stale()
        to_archive = [s for s in stale if s["should_archive"]]
        if to_archive:
            self.stale_detector.archive_stale(stale)
            print(f"✓ Archived {len(to_archive)} stale memories")

        # Report conflicts
        conflicts = self.conflict_detector.detect_conflicts()
        if conflicts:
            print(f"\n⚠️  Found {len(conflicts)} conflicts:")
            for conf in conflicts[:5]:  # Show first 5
                print(f"  - {conf.conflict_type}: {conf.suggestion}")

        # Promotion
        if approve_promotions:
            promotions = self.promotion_detector.detect_candidates()
            if promotions:
                print(f"\n✓ Found {len(promotions)} promotion candidates")
                # Auto-promote high confidence (>0.5)
                for prom in promotions:
                    if prom.confidence > 0.5:
                        self._promote(prom)

    def _promote(self, candidate: PromotionCandidate):
        """Execute promotion."""
        self.hierarchy.store(
            candidate.memory["content"],
            candidate.memory["category"],
            candidate.suggested_scope
        )
        print(f"  ✓ Promoted to {candidate.suggested_scope}: {candidate.memory['content'][:50]}...")
```

---

## Scheduled Maintenance Hook

```python
def scheduled_maintenance():
    """
    Run weekly maintenance (cron job or session-based).
    """
    hierarchy = MemoryHierarchy(Path.home() / ".cerberus" / "memory")
    health_check = MemoryHealthCheck(hierarchy)

    print("Running memory system health check...")

    # Run check
    health = health_check.run_health_check()

    print(f"\nHealth Status: {health.status.upper()}")
    print(f"Total memories: {health.total_memories}")
    print(f"Stale: {health.stale_count}")
    print(f"Conflicts: {health.conflict_count}")
    print(f"Promotion candidates: {health.promotion_candidates}")

    # Auto-maintain
    if health.status != "healthy":
        print("\nRunning auto-maintenance...")
        health_check.auto_maintain(approve_promotions=False)
```

---

## Exit Criteria

```
✓ StaleMemoryDetector class implemented
✓ ConflictDetector class implemented
✓ PromotionDetector class implemented
✓ MemoryHealthCheck class implemented
✓ Auto-maintenance functional
✓ Archive system working
✓ Scheduled maintenance hook implemented
✓ Tests: 10 scenarios with expected health reports
```

---

## Test Scenarios

```python
# Scenario 1: Stale detection
memories with last_occurred > 60 days ago
→ expect: Flagged as stale

# Scenario 2: Archive old memories
memories with last_occurred > 180 days ago
→ expect: Moved to archive/

# Scenario 3: Contradiction detection
"Always use X" and "Never use X" in same scope
→ expect: ConflictDetection(type="contradiction", severity="high")

# Scenario 4: Redundancy detection
"Keep it short" and "Be concise" (85% similar)
→ expect: ConflictDetection(type="redundancy", severity="low")

# Scenario 5: Cross-project promotion
Same rule in 3+ projects
→ expect: PromotionCandidate(suggested_scope="universal")

# Scenario 6: Health status
20 conflicts, 50% stale
→ expect: MemoryHealth(status="critical")
```

---

## Dependencies

- sentence-transformers (from Phase 2)
- numpy

---

## Token Budget

- Health check: 0 tokens (local analysis)
- Conflict detection: 0 tokens (embeddings local)
- Promotion detection: 0 tokens (clustering local)
- Total: 0 tokens (fully offline)

---

## Performance

- Health check: O(n²) for n memories (similarity comparisons)
- Acceptable for n < 1000
- Run weekly or on-demand (not every session)
