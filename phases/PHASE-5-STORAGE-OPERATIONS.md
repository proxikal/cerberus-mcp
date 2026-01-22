# PHASE 5: STORAGE OPERATIONS

**Rollout Phase:** Alpha (JSON) → Beta (SQLite)
**Status:** Implemented in 2 stages

## Objective
Write approved proposals to hierarchical storage: Universal → Language → Project → Task.

## Implementation Strategy

**Phase Alpha (Weeks 1-2):**
- Implement JSON storage ONLY
- Validate learning pipeline works
- Simple, proven, easy to debug

**Phase Beta (Weeks 3-4):**
- Update to SQLite FTS5 writes
- Triggered after Phase 12 migration complete
- Keep JSON for backward compatibility

---

## Implementation Location

**File:** `src/cerberus/memory/storage.py`

**Version 1 (Alpha):** JSON writes
**Version 2 (Beta):** SQLite writes (Phase 13 integration)

---

## Directory Structure

```
~/.cerberus/memory/
├── profile.json              # Universal preferences
├── corrections.json          # Universal corrections
├── languages/
│   ├── go.json
│   ├── python.json
│   └── typescript.json
├── projects/
│   ├── {project}/
│   │   ├── decisions.json
│   │   └── tasks/
│   │       └── {task}.json
└── sessions/
    └── active-{session_id}.json
```

---

## Data Structures

```python
@dataclass
class StorageTarget:
    """Where to store a memory."""
    scope: str  # "universal", "language:go", "project:hydra", "project:hydra:task:coding"
    category: str  # "preference", "rule", "correction", "decision"
    file_path: Path
    data_key: str  # JSON key to append to ("preferences", "rules", etc.)
```

---

## Storage Router

```python
class MemoryStorage:
    """
    Routes approved proposals to correct storage location.
    """

    def __init__(self, base_path: Path):
        self.base_path = base_path / "memory"
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create subdirs
        (self.base_path / "languages").mkdir(exist_ok=True)
        (self.base_path / "projects").mkdir(exist_ok=True)
        (self.base_path / "sessions").mkdir(exist_ok=True)

    def store(self, proposal: Union[MemoryProposal, AgentProposal]):
        """
        Store approved proposal to correct location.
        """
        # Determine target
        target = self._route(proposal.scope, proposal.category)

        # Load existing data
        data = self._load_file(target.file_path)

        # Append to correct key
        if target.data_key not in data:
            data[target.data_key] = []

        data[target.data_key].append({
            "content": proposal.content,
            "timestamp": datetime.now().isoformat(),
            "confidence": proposal.confidence if hasattr(proposal, "confidence") else 1.0
        })

        # Save
        self._save_file(target.file_path, data)

    def _route(self, scope: str, category: str) -> StorageTarget:
        """
        Determine storage target from scope and category.
        """
        # Universal
        if scope == "universal":
            if category == "correction":
                return StorageTarget(
                    scope=scope,
                    category=category,
                    file_path=self.base_path / "corrections.json",
                    data_key="corrections"
                )
            else:
                return StorageTarget(
                    scope=scope,
                    category=category,
                    file_path=self.base_path / "profile.json",
                    data_key="general"
                )

        # Language
        if scope.startswith("language:"):
            lang = scope.split(":")[1]
            return StorageTarget(
                scope=scope,
                category=category,
                file_path=self.base_path / "languages" / f"{lang}.json",
                data_key="preferences"
            )

        # Project
        if scope.startswith("project:"):
            parts = scope.split(":")
            project = parts[1]

            # Task-specific
            if len(parts) >= 4 and parts[2] == "task":
                task = parts[3]
                proj_dir = self.base_path / "projects" / project / "tasks"
                proj_dir.mkdir(parents=True, exist_ok=True)
                return StorageTarget(
                    scope=scope,
                    category=category,
                    file_path=proj_dir / f"{task}.json",
                    data_key="rules"
                )

            # Project-level
            proj_dir = self.base_path / "projects" / project
            proj_dir.mkdir(parents=True, exist_ok=True)
            return StorageTarget(
                scope=scope,
                category=category,
                file_path=proj_dir / "decisions.json",
                data_key="decisions"
            )

        raise ValueError(f"Unknown scope: {scope}")

    def _load_file(self, path: Path) -> Dict:
        """Load JSON file, return empty dict if not exists."""
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}

    def _save_file(self, path: Path, data: Dict):
        """Save JSON file."""
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
```

---

## Batch Storage

```python
def store_batch(self, proposals: List[Union[MemoryProposal, AgentProposal]]):
    """
    Store multiple proposals efficiently.
    Groups by file, writes once per file.
    """
    # Group by target file
    by_file: Dict[Path, List] = {}

    for prop in proposals:
        target = self._route(prop.scope, prop.category)

        if target.file_path not in by_file:
            by_file[target.file_path] = []

        by_file[target.file_path].append((prop, target))

    # Write each file once
    for file_path, items in by_file.items():
        data = self._load_file(file_path)

        for prop, target in items:
            if target.data_key not in data:
                data[target.data_key] = []

            data[target.data_key].append({
                "content": prop.content,
                "timestamp": datetime.now().isoformat(),
                "confidence": prop.confidence if hasattr(prop, "confidence") else 1.0
            })

        self._save_file(file_path, data)
```

---

## Metadata Tracking

```python
class MetadataManager:
    """
    Track memory statistics.
    """

    def __init__(self, base_path: Path):
        self.meta_file = base_path / "memory" / "metadata.json"

    def increment(self, scope: str, category: str, count: int = 1):
        """
        Increment counter for scope/category.
        """
        data = self._load()

        # Update counters
        data["total"] = data.get("total", 0) + count

        if "by_scope" not in data:
            data["by_scope"] = {}
        data["by_scope"][scope] = data["by_scope"].get(scope, 0) + count

        if "by_category" not in data:
            data["by_category"] = {}
        data["by_category"][category] = data["by_category"].get(category, 0) + count

        data["last_updated"] = datetime.now().isoformat()

        self._save(data)

    def _load(self) -> Dict:
        if self.meta_file.exists():
            with open(self.meta_file) as f:
                return json.load(f)
        return {}

    def _save(self, data: Dict):
        self.meta_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.meta_file, "w") as f:
            json.dump(data, f, indent=2)
```

---

## Integration

```python
def on_session_end():
    # Proposals approved (Phase 4)
    approved_ids = tui.run(user_proposals, agent_proposals)

    # Filter approved
    all_proposals = user_proposals + agent_proposals
    approved = [p for p in all_proposals if p.id in approved_ids]

    # Storage (Phase 5)
    storage = MemoryStorage(Path.home() / ".cerberus")
    storage.store_batch(approved)

    # Update metadata
    metadata = MetadataManager(Path.home() / ".cerberus")
    for prop in approved:
        metadata.increment(prop.scope, prop.category)

    print(f"✓ Stored {len(approved)} memories")
```

---

## Exit Criteria

```
✓ MemoryStorage class implemented
✓ Scope routing working (universal, language, project, task)
✓ File creation/append working
✓ Batch storage optimization working
✓ Metadata tracking implemented
✓ Directory creation automatic
✓ Tests: 10 storage scenarios
```

---

## Test Scenarios

```python
# Scenario 1: Universal storage
proposal: scope="universal", category="preference"
→ expect: written to profile.json, general key

# Scenario 2: Language storage
proposal: scope="language:go", category="rule"
→ expect: written to languages/go.json, preferences key

# Scenario 3: Project storage
proposal: scope="project:hydra", category="decision"
→ expect: written to projects/hydra/decisions.json, decisions key

# Scenario 4: Task storage
proposal: scope="project:hydra:task:coding", category="rule"
→ expect: written to projects/hydra/tasks/coding.json, rules key

# Scenario 5: Batch storage
10 proposals, 3 files involved
→ expect: each file written once (not 10 times)

# Scenario 6: Metadata tracking
store 5 proposals (3 universal, 2 language:go)
→ expect: metadata.json updated with correct counts
```

---

## Dependencies

- None (pure Python, pathlib + json)

---

## Performance

- Single write: < 5ms
- Batch write (10 proposals): < 20ms (3 file writes)
- Metadata update: < 2ms
