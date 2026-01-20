# Efficient Search and Symbol Retrieval

## Find a specific function quickly
```python
# 1) Targeted search (≈500 tokens)
results = search(query="parse_arguments", limit=5)
for r in results:
    print(f"{r['name']} -> {r['file']}:{r['start_line']}")

# 2) Deep dive on the right match (≈400 tokens)
details = get_symbol(name="parse_arguments", exact=True, context_lines=5)
print(details[0]["code"])
```

## Explore a module with minimal tokens
```python
# 1) Structure overview (≈350 tokens)
tree = blueprint(path="src/mypackage/module.py", format="tree")
print(tree)

# 2) Focused snippet (≈400 tokens)
symbol = get_symbol(name="process_request", exact=True, context_lines=5)
print(symbol[0]["code"])
```

## Programmatic use with compact JSON
```python
# Machine-friendly and token-light (≈40-60% of full JSON)
compact = blueprint(path="src/mypackage/module.py", format="json-compact")
# parse or stream without extra whitespace/metadata
```
