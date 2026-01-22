# Test Fixtures

## memories/

Sample memory files for testing Phase 1-3, 5-7.

- `universal.json` - Universal preferences and corrections
- `language-go.json` - Go-specific rules
- `project-hydra.json` - Hydra project decisions

## sessions/

Sample session context files for testing Phase 4.

- `active-hydra.json` - Active session with codes

## Expected Behavior

### Phase 1 (Storage)
```python
memory_learn("Use goroutines for concurrent I/O", "preference", "language:go")
→ Written to language-go.json, preferences key
```

### Phase 2 (Retrieval)
```python
query(context={"language": "go", "project": "hydra"})
→ Returns: universal + language:go + project:hydra memories
→ Sorted by relevance (project > language > universal)
```

### Phase 3 (Injection)
```python
inject(context={"language": "go", "project": "hydra"})
→ Returns <1500 tokens of formatted memories
→ Budget: 700 universal + 500 language + 300 project
```

### Phase 4 (Session)
```python
session_load("hydra")
→ Returns codes from active-hydra.json
→ Format: newline-separated verb:target codes
```

### Phase 7 (Search)
```python
memory_search("concurrent")
→ Returns: "Use goroutines for concurrent I/O"
→ Relevance score from FTS5 rank
```

## Token Estimates

| Fixture | Estimated Tokens |
|---------|------------------|
| universal.json | ~150 tokens |
| language-go.json | ~120 tokens |
| project-hydra.json | ~100 tokens |
| active-hydra.json | ~80 tokens |
| Total injection | ~450 tokens (under 2500 budget) |
