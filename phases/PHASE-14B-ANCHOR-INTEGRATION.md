# PHASE 14B: ANCHOR INTEGRATION

**Rollout Phase:** Delta (Weeks 7-8)
**Status:** Implement after Phase 14A

## Prerequisites

- ✅ Phase 14A complete (anchor discovery algorithm working)
- ✅ Phase 7 complete (context injection working)
- ✅ Phase 5 complete (storage working)

---

## Storage Integration

### SQLite Schema

*Note: The columns `anchor_file`, `anchor_symbol`, `anchor_score`, and `anchor_metadata` were pre-provisioned in the `memory_store` table during Phase 12 to avoid SQLite limitations with ALTER TABLE.*

### Storage Operations (Phase 5 Extension)

```python
def store_memory_with_anchor(memory: MemoryProposal, anchor: Optional[AnchorCandidate]) -> None:
    """
    Store memory with discovered anchor.

    Called during Phase 5 storage after proposal approval.
    """
    # Find anchor if not provided
    if not anchor and memory.scope != "universal":
        anchor = find_anchor_for_rule(
            rule=memory.content,
            scope=memory.scope,
            language=_extract_language(memory.scope),
            project_path=_extract_project(memory.scope)
        )

    # Store memory
    db.execute("""
        INSERT INTO memory_store (
            id, category, scope, content,
            anchor_file, anchor_symbol, anchor_score, anchor_metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        memory.id,
        memory.category,
        memory.scope,
        memory.content,
        anchor.file_path if anchor else None,
        anchor.symbol_name if anchor else None,
        anchor.quality_score if anchor else None,
        json.dumps({
            "file_size": anchor.file_size,
            "match_score": anchor.match_score,
            "recency_score": anchor.recency_score
        }) if anchor else None
    ))
```

---

## Injection Integration (Phase 7 Extension)

```python
def inject_with_anchors(memories: List[RetrievedMemory], token_budget: int) -> str:
    """
    Inject memories with code examples.

    Format:
        Rule: <text rule>
        Example: <file path>
        ```<language>
        <code snippet>
        ```

    Token allocation:
        - 40% text rules (600 tokens)
        - 60% code examples (900 tokens)
        - Total: 1500 tokens
    """
    output = []
    tokens_used = 0
    text_budget = int(token_budget * 0.4)
    code_budget = int(token_budget * 0.6)

    for memory in memories:
        # Text rule (always include)
        rule_text = f"- {memory.content}"
        rule_tokens = estimate_tokens(rule_text)

        if tokens_used + rule_tokens > text_budget:
            break

        output.append(rule_text)
        tokens_used += rule_tokens

        # Code example (if anchored and budget allows)
        if memory.anchor_file and code_budget > 0:
            # Read anchor file
            code_snippet = _read_anchor_code(
                memory.anchor_file,
                memory.anchor_symbol,
                max_lines=30  # Limit snippet size
            )

            # Format example
            example_text = f"  Example: {memory.anchor_file}\n  ```\n{code_snippet}\n  ```"
            example_tokens = estimate_tokens(example_text)

            if example_tokens <= code_budget:
                output.append(example_text)
                code_budget -= example_tokens

    return "\n".join(output)


def _read_anchor_code(file_path: str, symbol_name: Optional[str], max_lines: int) -> str:
    """
    Read code snippet from anchor file.

    Strategy:
    1. If symbol_name provided: Extract symbol definition
    2. Otherwise: Read first N lines of file
    3. Limit to max_lines
    """
    if symbol_name:
        # Use Cerberus get_symbol
        result = cerberus_get_symbol(symbol_name, context_lines=5)
        code = result.code
    else:
        # Read file head
        with open(file_path, 'r') as f:
            lines = f.readlines()[:max_lines]
            code = "".join(lines)

    # Trim to max_lines
    code_lines = code.split("\n")[:max_lines]
    return "\n".join(code_lines)
```

---

## CLI Commands

```bash
# Find anchor for existing memory
cerberus memory anchor <memory_id>

# Re-anchor all memories (e.g., after refactoring)
cerberus memory reanchor --scope project:myapp

# Show memories with anchors
cerberus memory show --anchored

# Test anchor quality
cerberus memory anchor-test <rule_text>
```

---

## Implementation in `src/cerberus/memory/anchoring.py`

```python
"""
Phase 14: Dynamic Anchoring

Links abstract rules to concrete code examples.
"""

import math
import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

# External dependencies
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Internal dependencies
from cerberus.memory.storage import MemoryStorage
from cerberus.memory.retrieval import RetrievedMemory
from cerberus.search import search as cerberus_search
from cerberus.symbols import get_symbol as cerberus_get_symbol


LANGUAGE_EXTENSIONS = {
    "python": "py",
    "javascript": "js",
    "typescript": "ts",
    "go": "go",
    "rust": "rs",
    "java": "java",
}


@dataclass
class AnchorCandidate:
    file_path: str
    symbol_name: Optional[str]
    match_score: float
    file_size: int
    recency_score: float
    quality_score: float


@dataclass
class AnchoredMemory:
    memory_id: str
    content: str
    anchor_file: Optional[str]
    anchor_symbol: Optional[str]
    anchor_score: float
    anchor_metadata: Dict[str, Any]


class AnchorEngine:
    """Finds and manages code anchors for memories."""

    def __init__(self, storage: MemoryStorage):
        self.storage = storage

    def find_anchor(
        self,
        rule: str,
        scope: str,
        language: Optional[str],
        project_path: Optional[str],
        min_quality: float = 0.7
    ) -> Optional[AnchorCandidate]:
        """Find best code example for rule.

        Args:
            rule: Abstract rule text
            scope: Memory scope
            language: Programming language
            project_path: Project directory
            min_quality: Minimum quality threshold (0.0-1.0, default 0.7)
        """

        # Extract keywords
        keywords = self._extract_keywords(rule)

        if not keywords:
            return None

        # Determine search scope
        if project_path:
            search_scope = project_path
        elif language:
            ext = LANGUAGE_EXTENSIONS.get(language)
            search_scope = f"**/*.{ext}" if ext else None
        else:
            return None  # Universal scope - no anchoring

        if not search_scope:
            return None

        # Search code index
        candidates = []

        for keyword in keywords:
            # File search
            file_results = cerberus_search(
                query=keyword,
                path=search_scope,
                limit=10
            )
            candidates.extend(file_results)

        # Score candidates
        scored = []
        for candidate in candidates:
            relevance = self._calculate_relevance(rule, candidate['file_path'])
            size_score = 1.0 - (min(candidate.get('file_size', 100), 500) / 500)
            recency = self._calculate_recency(candidate['file_path'])

            quality = (0.6 * relevance + 0.2 * size_score + 0.2 * recency)

            if quality >= min_quality:
                scored.append(AnchorCandidate(
                    file_path=candidate['file_path'],
                    symbol_name=candidate.get('symbol_name'),
                    match_score=relevance,
                    file_size=candidate.get('file_size', 0),
                    recency_score=recency,
                    quality_score=quality
                ))

        if scored:
            return max(scored, key=lambda c: c.quality_score)
        return None

    def _extract_keywords(self, rule: str) -> List[str]:
        """Extract meaningful keywords from rule."""
        stopwords = {"use", "always", "never", "prefer", "avoid", "the", "a", "an", "in", "on", "for"}
        tokens = rule.lower().split()
        return [t for t in tokens if t not in stopwords and len(t) > 2]

    def _calculate_relevance(self, rule: str, file_path: str) -> float:
        """TF-IDF similarity between rule and file."""
        try:
            with open(file_path, 'r') as f:
                file_content = f.read()
        except:
            return 0.0

        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([rule, file_content])
        similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
        return similarity

    def _calculate_recency(self, file_path: str) -> float:
        """Recency score based on modification time."""
        import os
        from datetime import datetime

        try:
            mtime = os.path.getmtime(file_path)
            modified = datetime.fromtimestamp(mtime)
            age_days = (datetime.now() - modified).days
            decay_rate = 0.023
            return math.exp(-decay_rate * age_days)
        except:
            return 0.5

    def anchor_memory(self, memory_id: str) -> bool:
        """Find and attach anchor to existing memory."""
        memory = self.storage.get_memory(memory_id)
        if not memory:
            return False

        # Extract scope details
        language = None
        project_path = None

        if memory.scope.startswith("language:"):
            language = memory.scope.split(":")[1]
        elif memory.scope.startswith("project:"):
            project_path = memory.scope.split(":")[1]

        # Find anchor
        anchor = self.find_anchor(
            rule=memory.content,
            scope=memory.scope,
            language=language,
            project_path=project_path
        )

        if anchor:
            # Update memory with anchor
            self.storage.update_anchor(
                memory_id=memory_id,
                anchor_file=anchor.file_path,
                anchor_symbol=anchor.symbol_name,
                anchor_score=anchor.quality_score,
                anchor_metadata={
                    "file_size": anchor.file_size,
                    "match_score": anchor.match_score,
                    "recency_score": anchor.recency_score
                }
            )
            return True
        return False

    def reanchor_all(self, scope: Optional[str] = None) -> Dict[str, int]:
        """Re-anchor all memories in scope."""
        memories = self.storage.get_memories(scope=scope)

        stats = {"total": len(memories), "anchored": 0, "failed": 0}

        for memory in memories:
            success = self.anchor_memory(memory.id)
            if success:
                stats["anchored"] += 1
            else:
                stats["failed"] += 1

        return stats
```

---

## Token Costs

**Anchor Discovery:**
- Keyword extraction: 0 tokens (regex)
- Code search: 0 tokens (uses Cerberus index)
- TF-IDF scoring: 0 tokens (scikit-learn)
- Total: 0 tokens

**Injection with Anchors:**
- Text rules: 600 tokens (40% of 1500)
- Code examples: 900 tokens (60% of 1500)
- Total: 1500 tokens (same budget as Phase 7, reallocated)

**Storage:**
- 0 tokens (SQLite writes)

**Total per session:** 1500 tokens (no change from Phase 7)

---

## Validation Gates

**Anchor Quality:**
- 80%+ of project-scoped memories should find anchors
- Anchor quality score >= 0.7 for all stored anchors (default threshold)
- Threshold is configurable per query if needed
- User feedback: "Examples help me understand rules"

**Injection Quality:**
- LLM follows anchored examples 90%+ of time
- Measure: Code generated matches anchor style
- User approvals increase from 70% → 85%

**Performance:**
- Anchor discovery: < 2 seconds per memory
- No impact on Phase 7 injection speed
- SQLite size increase < 10%

**Testing:**
- 20 test rules with known best examples
- Anchor discovery finds correct file 90%+ of time
- 5+ real sessions with anchored memories

---

## Dependencies

**Phase Dependencies:**
- Phase 7 (Context Injection) - extends injection format
- Phase 5 (Storage) - adds anchor columns to SQLite
- Phase 13 (Search) - uses memory_search for retrieval

**External Dependencies:**
- scikit-learn (already required for Phase 2)
- Cerberus code index (search, get_symbol)

**Optional:**
- None (no LLM, no new dependencies)

---

## Integration Points

**Phase 5 (Storage):**
```python
def store_memory(proposal: MemoryProposal) -> None:
    # Existing logic...

    # Phase 14: Find anchor
    anchor = AnchorEngine(storage).find_anchor(
        rule=proposal.content,
        scope=proposal.scope,
        language=_extract_language(proposal.scope),
        project_path=_extract_project(proposal.scope)
    )

    # Store with anchor
    storage.insert_with_anchor(proposal, anchor)
```

**Phase 7 (Injection):**
```python
def inject(context: Dict[str, Any], budget: int = 1500) -> str:
    # Existing retrieval...
    memories = retrieval.get_relevant(context)

    # Phase 14: Inject with anchors
    return inject_with_anchors(memories, budget)
```

---

## Migration Path

**For existing memories (no anchors):**

```bash
# Anchor existing memories
cerberus memory reanchor --scope all

# Stats
cerberus memory stats --show-anchors
```

**Backward compatibility:**
- Memories without anchors inject as text-only (Phase 7 behavior)
- No breaking changes to existing system
- Gradual rollout: anchor new memories first

---

## Success Criteria

**Phase 14 complete when:**
- ✅ Anchor discovery works (80%+ success rate)
- ✅ Anchored memories inject code examples
- ✅ User approval rate increases from 70% → 85%
- ✅ LLM follows examples 90%+ of time
- ✅ No performance degradation
- ✅ 5+ real sessions validated

**Validation method:**
- Measure approval rate before/after Phase 14
- A/B test: anchored vs text-only memories
- User feedback: "This is way better"

---

## Example Output

**Before Phase 14 (text-only):**
```
- Use Repository pattern for data access
```

**After Phase 14 (anchored):**
```
- Use Repository pattern for data access
  Example: src/users/repo.go
  ```go
  type UserRepository struct {
      db *sql.DB
  }

  func (r *UserRepository) FindByID(id int) (*User, error) {
      var user User
      err := r.db.QueryRow("SELECT * FROM users WHERE id = ?", id).Scan(&user)
      return &user, err
  }
  ```
```

**Impact:** LLM now knows *exactly* what "Repository pattern" means in this codebase.

---

## Implementation Checklist

- [ ] Write `src/cerberus/memory/anchoring.py`
- [ ] Add `AnchorEngine` class
- [ ] Implement `find_anchor()` algorithm
- [ ] Extend SQLite schema (anchor columns)
- [ ] Update Phase 5 storage to call anchor discovery
- [ ] Update Phase 7 injection to include code examples
- [ ] Add CLI commands (`cerberus memory anchor`, `reanchor`)
- [ ] Write unit tests (20 test rules)
- [ ] Write integration tests (storage + injection)
- [ ] Validate with 5+ real sessions
- [ ] Measure approval rate increase

---

**Last Updated:** 2026-01-22
**Version:** 1.0
**Status:** Specification complete, ready for implementation in Phase Delta