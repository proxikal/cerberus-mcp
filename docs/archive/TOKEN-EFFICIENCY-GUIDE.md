# Cerberus Token Efficiency Guide

## Overview

Cerberus is designed to minimize token usage while providing comprehensive code intelligence. This guide shows how to get the most out of Cerberus without wasting tokens.

## Token Costs by Operation

### Search
| Operation | Typical Cost | Notes |
|-----------|--------------|-------|
| `search(query, limit=5)` | ~500 tokens | Recommended default |
| `search(query, limit=10)` | ~1,000 tokens | Broader search |
| `search(query, limit=20)` | ~2,000 tokens | Use cautiously |

**Best practice:** Start with limit=5; increase only if needed.

### Symbol Retrieval
| Operation | Typical Cost | Notes |
|-----------|--------------|-------|
| `get_symbol(..., context_lines=0)` | ~300 tokens | Minimal |
| `get_symbol(..., context_lines=5)` | ~400 tokens | Recommended |
| `get_symbol(..., context_lines=20)` | ~700 tokens | Detailed context |

**Best practice:** Use context_lines=5 for most cases.

### Blueprint
| Operation | Typical Cost | Notes |
|-----------|--------------|-------|
| `blueprint(..., format="tree")` | ~350 tokens | Most efficient |
| `blueprint(..., format="flat")` | ~200 tokens | Symbol list |
| `blueprint(..., format="json-compact")` | ~800-900 tokens | Machine-parseable, trimmed fields |
| `blueprint(..., format="json")` | ~1,800 tokens | 5x more expensive |
| `tree + show_deps` | ~1,200 tokens | Adds dependencies |
| `tree + show_deps + show_meta` | ~1,500 tokens | Full analysis |

**Best practice:** Prefer `format="tree"` without metadata; use `json-compact` when you need structured data; enable deps/meta only when necessary.

### Other Ops
| Operation | Typical Cost | Notes |
|-----------|--------------|-------|
| `skeletonize(path)` | ~300 tokens | 70–90% savings vs full file |
| `call_graph(depth=1)` | ~400 tokens | Bounded to 100 nodes |
| `related_changes()` | ~500 tokens | Max 5 suggestions |

## Token-Saving Strategies

1) **Use skeletonize for large files**  
   - Skeleton first (~300 tokens), then `get_symbol` for specifics.

2) **Tree first, JSON only if needed**  
   - `format="tree"` for exploration; `json` only for programmatic parsing.

3) **Keep search limits low**  
   - Start at limit=5; avoid high limits unless justified.

4) **Disable metadata unless needed**  
   - `show_deps/show_meta` can 4x cost; add only when required.

## Recommended Workflows

**Code exploration (~1,250 tokens):**  
`search(limit=5)` → `get_symbol(context_lines=5)` → `blueprint(format="tree")`

**Understand a function (~800 tokens):**  
`get_symbol(context_lines=5)` → `call_graph(depth=1, direction="callers")`

**File analysis (~1,050 tokens):**  
`skeletonize` → `blueprint(tree)` → `get_symbol`

## Anti-Patterns (Avoid)
- Always using JSON format for blueprint (5x cost).
- High search limits by default.
- Always enabling deps/meta.
- Reading whole files instead of skeletons.

## Quick Reference
| Task | Tool | Typical Cost |
|------|------|--------------|
| Find a symbol | `search(limit=5)` | ~500 |
| View symbol code | `get_symbol` | ~400 |
| Structure view | `blueprint(tree)` | ~350 |
| Large file overview | `skeletonize` | ~300 |
| Callers/callees | `call_graph(depth=1)` | ~400 |

## Monitor Usage
- If a call exceeds ~2,000 tokens, consider narrowing scope (limit, context_lines, format).
- Compare actual usage to these estimates and adjust parameters accordingly.
